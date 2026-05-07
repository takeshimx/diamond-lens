"""
選手名オートコンプリートサービス（Vol.1 実装）

メモリ常駐の Trie + ContextFilter + PrefixCache で
4 系統の選手検索 API を 1 本に統合する。

関連ドキュメント: docs/plan_docs/SEARCH_AUTOCOMPLETE_PLAN_VOL1.md

リクエスト処理フロー:
    Cache → Trie → ContextFilter → popularity_score 降順 → 上位 N 件
"""
import logging
import math
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pandas as pd

from backend.app.services.base import (
    client,
    PROJECT_ID,
    DATASET_ID,
    DIM_PLAYERS_MASTER_TABLE_ID,
    BATTING_STATS_TABLE_ID,
    PITCHING_STATS_MASTER_TABLE_ID,
    STATCAST_MASTER_TABLE_ID,
    MART_BATTER_SEASON_STATS_TABLE_ID,
    MART_PITCHER_SEASON_STATS_TABLE_ID,
)
from backend.app.utils.structured_logger import get_logger

logger = logging.getLogger(__name__)
structured_logger = get_logger("diamond-lens")


# =============================================================================
# (1) PlayerEntry — Trie のリーフに格納する選手 1 人分の DTO
# =============================================================================
@dataclass
class PlayerEntry:
    mlbid: int
    full_name: str
    team: Optional[str]
    primary_position: Optional[str]
    bat_side: Optional[str]
    pitch_hand: Optional[str]
    active: bool

    statcast_pitcher_seasons: frozenset = field(default_factory=frozenset)
    statcast_batter_seasons: frozenset = field(default_factory=frozenset)
    stuffplus_seasons: frozenset = field(default_factory=frozenset)

    total_pa_recent3y: int = 0
    total_ip_recent3y: float = 0.0

    popularity_score: float = 0.0


# =============================================================================
# (2) Trie — プレフィックス木
# =============================================================================
class Trie:
    """選手名のプレフィックス検索用データ構造。

    name は first_name + last_name の小文字結合と
    last_name 単独の 2 通りで insert される（呼び出し側で）。
    検索結果に同一 mlbid が混じる可能性があるため、
    search_prefix 内で mlbid 単位の dedup を行う。
    """

    _ENTRIES_KEY = "__entries__"

    def __init__(self) -> None:
        self._root: Dict = {}

    def insert(self, name: str, entry: PlayerEntry) -> None:
        node = self._root
        for ch in name:
            if ch not in node:
                node[ch] = {}
            node = node[ch]
        node.setdefault(self._ENTRIES_KEY, []).append(entry)

    def search_prefix(self, prefix: str) -> List[PlayerEntry]:
        node = self._root
        for ch in prefix:
            if ch not in node:
                return []
            node = node[ch]

        # 直下のサブツリーを DFS で走査し、全 PlayerEntry を mlbid 単位で dedup
        results: List[PlayerEntry] = []
        seen: set = set()
        stack: List[Dict] = [node]
        while stack:
            cur = stack.pop()
            for k, v in cur.items():
                if k == self._ENTRIES_KEY:
                    for e in v:
                        if e.mlbid not in seen:
                            seen.add(e.mlbid)
                            results.append(e)
                else:
                    stack.append(v)
        return results


# =============================================================================
# (3) ContextFilter — Trie の結果を context × season で絞り込む
# =============================================================================
class ContextFilter:
    """候補リストをリクエストの context / season で絞り込む。"""

    def apply(
        self,
        entries: List[PlayerEntry],
        context: str,
        season: Optional[int],
    ) -> List[PlayerEntry]:
        if context == "all":
            return entries
        if season is None:
            # context!=all なのに season が無いのは API 層でエラーにする想定だが、
            # 万一来た場合は安全側でフィルタ無しとする。
            return entries
        if context == "statcast_pitcher":
            return [e for e in entries if season in e.statcast_pitcher_seasons]
        if context == "statcast_batter":
            return [e for e in entries if season in e.statcast_batter_seasons]
        if context == "stuffplus":
            return [e for e in entries if season in e.stuffplus_seasons]
        return entries


# =============================================================================
# (4) PrefixCache — (context, season, prefix) 単位の LRU キャッシュ
# =============================================================================
class PrefixCache:
    """直近の問い合わせ結果を保持する LRU。

    キー: (context, season, prefix.lower())
    値:   List[PlayerEntry]
    最大: 4,096 entries / TTL なし（プロセス寿命と一致）。
    """

    def __init__(self, max_size: int = 4096) -> None:
        self._max_size: int = max_size
        self._store: "OrderedDict[Tuple[str, Optional[int], str], List[PlayerEntry]]" = OrderedDict()

    def get(self, key: Tuple[str, Optional[int], str]) -> Optional[List[PlayerEntry]]:
        if key not in self._store:
            return None
        self._store.move_to_end(key)
        return self._store[key]

    def put(self, key: Tuple[str, Optional[int], str], value: List[PlayerEntry]) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = value
        if len(self._store) > self._max_size:
            self._store.popitem(last=False)


# =============================================================================
# (5) AutocompleteService — 外向きの窓口
# =============================================================================
class AutocompleteService:
    """4 系統の選手検索を統合したオートコンプリート窓口。"""

    # Trie に挿入する文字種を制限（plan §5 Step 5: 英字小文字 + ハイフン + アポストロフィ + スペース）
    _ALLOWED_CHARS = set("abcdefghijklmnopqrstuvwxyz '-")

    def __init__(self) -> None:
        self.trie: Trie = Trie()
        self.filter: ContextFilter = ContextFilter()
        self.cache: PrefixCache = PrefixCache()
        self.ready: bool = False

    # -------------------------------------------------------------------------
    # 起動時 1 回呼ぶ: BigQuery から全選手を取得し Trie を構築する
    # -------------------------------------------------------------------------
    def build(self) -> None:
        sql = self._build_load_sql()
        started = time.monotonic()
        df = client.query(sql).to_dataframe()
        elapsed_query = time.monotonic() - started

        loaded = 0
        for _, row in df.iterrows():
            entry = self._row_to_entry(row)
            if entry is None:
                continue

            full_name_key = self._normalize(entry.full_name)
            last_name_key = self._normalize(self._extract_last_name(entry.full_name))

            if full_name_key:
                self.trie.insert(full_name_key, entry)
            if last_name_key and last_name_key != full_name_key:
                self.trie.insert(last_name_key, entry)
            loaded += 1

        elapsed_total = time.monotonic() - started
        self.ready = True
        structured_logger.info(
            "autocomplete_build_completed",
            entries_loaded=loaded,
            elapsed_query_ms=int(elapsed_query * 1000),
            elapsed_total_ms=int(elapsed_total * 1000),
        )

    # -------------------------------------------------------------------------
    # クエリ時に呼ぶ: Cache → Trie → ContextFilter → 上位 N 件
    # -------------------------------------------------------------------------
    def query(
        self,
        prefix: str,
        context: str = "all",
        season: Optional[int] = None,
        limit: int = 10,
    ) -> Tuple[List[PlayerEntry], str]:
        """検索結果と served_from（"cache" / "trie"）のタプルを返す。"""
        normalized = self._normalize(prefix)
        if not normalized:
            return [], "trie"

        cache_key: Tuple[str, Optional[int], str] = (context, season, normalized)

        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached[:limit], "cache"

        candidates = self.trie.search_prefix(normalized)
        filtered = self.filter.apply(candidates, context, season)
        ranked = sorted(filtered, key=lambda e: e.popularity_score, reverse=True)

        self.cache.put(cache_key, ranked)
        return ranked[:limit], "trie"

    # -------------------------------------------------------------------------
    # ヘルパー
    # -------------------------------------------------------------------------
    @classmethod
    def _normalize(cls, text: Optional[str]) -> str:
        """Trie 用に文字列を正規化する。許容文字以外は除去。"""
        if not text:
            return ""
        lowered = text.lower()
        return "".join(ch for ch in lowered if ch in cls._ALLOWED_CHARS).strip()

    @staticmethod
    def _extract_last_name(full_name: str) -> str:
        if not full_name:
            return ""
        parts = full_name.strip().split()
        return parts[-1] if parts else ""

    @staticmethod
    def _compute_popularity_score(pa: int, ip: float, active: bool) -> float:
        """plan §3.4 の式: log(1 + PA + IP*3) + (active なら +1.0)"""
        base = math.log(1.0 + float(pa) + float(ip) * 3.0)
        return base + (1.0 if active else 0.0)

    @staticmethod
    def _safe_int(value, default: int = 0) -> int:
        if value is None or pd.isna(value):
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_float(value, default: float = 0.0) -> float:
        if value is None or pd.isna(value):
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_bool(value, default: bool = False) -> bool:
        if value is None or pd.isna(value):
            return default
        return bool(value)

    @staticmethod
    def _safe_str(value) -> Optional[str]:
        if value is None or pd.isna(value):
            return None
        s = str(value).strip()
        return s if s else None

    @staticmethod
    def _safe_seasons(value) -> frozenset:
        """ARRAY_AGG 結果（list / numpy array / NA）を frozenset[int] に揃える。"""
        if value is None:
            return frozenset()
        # pd.isna は配列に対しては配列を返すので、スカラーかどうかで分岐
        try:
            if pd.isna(value):
                return frozenset()
        except (TypeError, ValueError):
            pass  # 配列なので isna は使えない → そのまま処理
        try:
            return frozenset(int(x) for x in value if x is not None and not pd.isna(x))
        except TypeError:
            return frozenset()

    @classmethod
    def _row_to_entry(cls, row) -> Optional[PlayerEntry]:
        mlbid = cls._safe_int(row.get("mlbid"), default=-1)
        if mlbid <= 0:
            return None

        pa = cls._safe_int(row.get("total_pa_recent3y"))
        ip = cls._safe_float(row.get("total_ip_recent3y"))
        active = cls._safe_bool(row.get("active"))
        full_name = cls._safe_str(row.get("full_name")) or ""

        return PlayerEntry(
            mlbid=mlbid,
            full_name=full_name,
            team=cls._safe_str(row.get("team")),
            primary_position=cls._safe_str(row.get("primary_position")),
            bat_side=cls._safe_str(row.get("bat_side")),
            pitch_hand=cls._safe_str(row.get("pitch_hand")),
            active=active,
            statcast_pitcher_seasons=cls._safe_seasons(row.get("statcast_pitcher_seasons")),
            statcast_batter_seasons=cls._safe_seasons(row.get("statcast_batter_seasons")),
            stuffplus_seasons=cls._safe_seasons(row.get("stuffplus_seasons")),
            total_pa_recent3y=pa,
            total_ip_recent3y=ip,
            popularity_score=cls._compute_popularity_score(pa, ip, active),
        )

    @staticmethod
    def _build_load_sql() -> str:
        """起動時ロード SQL。直近 3 シーズン (2024〜2026) を対象とする。

        2024〜2025: fact 層（fact_batting_stats_with_risp / fact_pitching_stats_master）
        2026〜:     mart 層（mart_batter_season_stats / mart_pitcher_season_stats）
        """
        dpm = f"`{PROJECT_ID}.{DATASET_ID}.{DIM_PLAYERS_MASTER_TABLE_ID}`"
        teams = f"`{PROJECT_ID}.{DATASET_ID}.dim_teams`"
        statcast = f"`{PROJECT_ID}.{DATASET_ID}.{STATCAST_MASTER_TABLE_ID}`"
        stuffplus = f"`{PROJECT_ID}.{DATASET_ID}.stuff_plus_rankings`"
        fact_bat = f"`{PROJECT_ID}.{DATASET_ID}.{BATTING_STATS_TABLE_ID}`"
        fact_pit = f"`{PROJECT_ID}.{DATASET_ID}.{PITCHING_STATS_MASTER_TABLE_ID}`"
        mart_bat = f"`{PROJECT_ID}.{DATASET_ID}.{MART_BATTER_SEASON_STATS_TABLE_ID}`"
        mart_pit = f"`{PROJECT_ID}.{DATASET_ID}.{MART_PITCHER_SEASON_STATS_TABLE_ID}`"

        return f"""
WITH
players_base AS (
  SELECT
    mlbid, full_name, first_name, last_name,
    primary_position, bat_side, pitch_hand, active,
    current_team_id, mlb_debut_year, mlb_last_year
  FROM {dpm}
  WHERE (mlb_debut_year >= 2000 OR mlb_last_year >= 2000)
    AND mlbid IS NOT NULL
),
teams AS (
  SELECT team_id, abbreviation AS team_abbr FROM {teams}
),
statcast_pitcher_years AS (
  SELECT pitcher AS mlbid,
         ARRAY_AGG(DISTINCT game_year ORDER BY game_year) AS statcast_pitcher_seasons
  FROM {statcast}
  WHERE pitch_type IS NOT NULL
  GROUP BY pitcher
),
statcast_batter_years AS (
  SELECT batter AS mlbid,
         ARRAY_AGG(DISTINCT game_year ORDER BY game_year) AS statcast_batter_seasons
  FROM {statcast}
  WHERE pitch_type IS NOT NULL
  GROUP BY batter
),
stuffplus_years AS (
  SELECT pitcher AS mlbid,
         ARRAY_AGG(DISTINCT season ORDER BY season) AS stuffplus_seasons
  FROM {stuffplus}
  WHERE model_type = 'stuff_plus'
  GROUP BY pitcher
),
batter_pa_recent AS (
  SELECT mlbid, SUM(pa) AS total_pa_recent3y
  FROM (
    SELECT mlbId AS mlbid, pa
    FROM {fact_bat}
    WHERE season BETWEEN 2024 AND 2025
    UNION ALL
    SELECT batter AS mlbid, pa
    FROM {mart_bat}
    WHERE season >= 2026
  )
  WHERE mlbid IS NOT NULL
  GROUP BY mlbid
),
pitcher_ip_recent AS (
  SELECT mlbid, SUM(ip) AS total_ip_recent3y
  FROM (
    SELECT mlbid, ip
    FROM {fact_pit}
    WHERE season BETWEEN 2024 AND 2025
    UNION ALL
    SELECT pitcher AS mlbid, ip
    FROM {mart_pit}
    WHERE season >= 2026
  )
  WHERE mlbid IS NOT NULL
  GROUP BY mlbid
)
SELECT
  p.mlbid,
  p.full_name,
  p.first_name,
  p.last_name,
  p.primary_position,
  p.bat_side,
  p.pitch_hand,
  p.active,
  t.team_abbr AS team,
  IFNULL(spy.statcast_pitcher_seasons, []) AS statcast_pitcher_seasons,
  IFNULL(sby.statcast_batter_seasons, [])  AS statcast_batter_seasons,
  IFNULL(sfy.stuffplus_seasons, [])        AS stuffplus_seasons,
  IFNULL(bpa.total_pa_recent3y, 0)         AS total_pa_recent3y,
  IFNULL(pip.total_ip_recent3y, 0)         AS total_ip_recent3y
FROM players_base p
LEFT JOIN teams                  t   ON p.current_team_id = t.team_id
LEFT JOIN statcast_pitcher_years spy ON p.mlbid = spy.mlbid
LEFT JOIN statcast_batter_years  sby ON p.mlbid = sby.mlbid
LEFT JOIN stuffplus_years        sfy ON p.mlbid = sfy.mlbid
LEFT JOIN batter_pa_recent       bpa ON p.mlbid = bpa.mlbid
LEFT JOIN pitcher_ip_recent      pip ON p.mlbid = pip.mlbid
"""
