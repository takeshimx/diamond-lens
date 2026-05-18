"""
対戦戦略レポート専用エンドポイント。

新規タブ「対戦戦略レポート」用。チャット (/qa/agentic-stats) とは独立した経路。
構造化入力（打者名・投手名・シーズン）を受け取り、StrategyAgent.run_structured で
6セクションのレポートを生成して返す。
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.app.api.rate_limit import limiter
from backend.app.config.settings import get_settings
from backend.app.utils.structured_logger import get_logger
from backend.app.services.token_budget_service import get_token_budget_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
structured_logger = get_logger("strategy-report")

router = APIRouter(tags=["strategy"])


class StrategyReportRequest(BaseModel):
    batter_name: str = Field(..., description="打者のフルネーム（例: 'Shohei Ohtani'）", min_length=2)
    pitcher_name: str = Field(..., description="投手のフルネーム（例: 'Yu Darvish'）", min_length=2)
    season: Optional[int] = Field(None, description="対象シーズン（例: 2026）。省略時は最新シーズン。", ge=2015, le=2030)


def _strategy_report_limit() -> str:
    return f"{get_settings().rate_limit_agent_chat_per_minute}/minute"


@router.post(
    "/strategy-report",
    response_model=Dict[str, Any],
    summary="対戦戦略レポート生成（構造化入力）",
    description="打者・投手・シーズンを受け取り、StrategyAgent で6セクションの戦略レポートを生成します。",
)
@limiter.limit(_strategy_report_limit)
async def generate_strategy_report_endpoint(
    request: Request,
    body: StrategyReportRequest,
) -> Dict[str, Any]:
    request_id = str(uuid4())

    token_budget = get_token_budget_service()
    if token_budget.is_budget_exceeded("report"):
        return {
            "request_id": request_id,
            "final_answer": "本日のAI分析サービスの利用上限に達しました。明日以降に再度お試しください。",
            "isStrategyReport": False,
            "isMatchupCard": False,
            "matchupData": None,
            "service_at_capacity": True,
        }

    start_time = time.time()
    structured_logger.info(
        "Strategy report request",
        request_id=request_id,
        batter=body.batter_name,
        pitcher=body.pitcher_name,
        season=body.season,
    )

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        import os

        from backend.app.services.agents.strategy_agent import StrategyAgent
        from backend.app.services.llm_gateway_service import LangchainUsageCallback

        model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GEMINI_API_KEY_V2"),
            temperature=0,
            callbacks=[LangchainUsageCallback(feature="strategy_report", model="gemini-2.5-flash", pool="report")],
        )
        agent = StrategyAgent(model=model)
        result = agent.run_structured(
            batter_name=body.batter_name.strip(),
            pitcher_name=body.pitcher_name.strip(),
            season=body.season,
        )

        elapsed = time.time() - start_time
        structured_logger.info(
            "Strategy report completed",
            request_id=request_id,
            elapsed_sec=round(elapsed, 2),
            answer_length=len(result.get("final_answer", "")),
        )

        return {
            "request_id": request_id,
            "elapsed_sec": round(elapsed, 2),
            "final_answer": result.get("final_answer", ""),
            "isStrategyReport": result.get("isStrategyReport", True),
            "isMatchupCard": result.get("isMatchupCard", False),
            "matchupData": result.get("matchupData", None),
            "strategyData": result.get("strategyData", {}),
        }

    except Exception as e:
        elapsed = time.time() - start_time
        structured_logger.error(
            "Strategy report failed",
            request_id=request_id,
            error=str(e),
            elapsed_sec=round(elapsed, 2),
        )
        raise HTTPException(
            status_code=500,
            detail=f"戦略レポート生成中にエラーが発生しました: {str(e)}",
        ) from e


# ============================================================
# サブセクション API: Hero / Sample Size Strip
# ============================================================
# Strategy report 画面の最上段（PA/AB/H/HR/BB/K/HISTORICAL OPS/CONFIDENCE）を
# データから直接表示するための集計エンドポイント。LLM は介在しない。
#
# 内部では既存の mlb_matchup_analytics_tool（view_matchup_pitch_analytics）を
# 呼び、球種別行を SUM して打席ベースの集計に戻す。
# ============================================================


def _safe_int(v) -> int:
    try:
        return int(v) if v is not None else 0
    except (TypeError, ValueError):
        return 0


def _safe_float(v):
    """None / NaN を安全に弾いて float を返す（NaN や None のときは None）"""
    try:
        if v is None:
            return None
        f = float(v)
        return f if f == f else None  # NaN guard
    except (TypeError, ValueError):
        return None


def _confidence_label(pa: int) -> str:
    if pa >= 20:
        return "HIGH"
    if pa >= 10:
        return "MED"
    return "LOW"


_AB_EXCLUDE_EVENTS = {
    "walk", "intent_walk", "hit_by_pitch",
    "sac_fly", "sac_fly_double_play",
    "sac_bunt", "sac_bunt_double_play",
    "catcher_interf", "batter_interference",
}
_HIT_EVENTS = {"single", "double", "triple", "home_run"}
_BB_EVENTS = {"walk", "intent_walk"}
_K_EVENTS = {"strikeout", "strikeout_double_play"}
_SF_EVENTS = {"sac_fly", "sac_fly_double_play"}


@router.get(
    "/strategy-report/sample-size",
    response_model=Dict[str, Any],
    summary="対戦サンプル集計（Hero strip 用、LLM 不使用）",
    description="statcast_master を batter/pitcher (mlbid) で直接集計し PA/AB/H/HR/BB/K/HISTORICAL_OPS/CONFIDENCE を返します。",
)
async def get_matchup_sample_size_endpoint(
    batter_id: int = Query(..., description="打者 MLB ID"),
    pitcher_id: int = Query(..., description="投手 MLB ID"),
) -> Dict[str, Any]:
    """
    Statcast 生テーブル `statcast_master` を直接 COUNTIF で集計する。
    実カラム名:
      - batter  (INT64)  — 打者 MLB ID
      - pitcher (INT64)  — 投手 MLB ID
      - events  (STRING) — 打席終了時の結果（pitch-level のため打席終了球以外は NULL）

    docs/statcast_cols.csv 参照。
    """
    from google.cloud.bigquery import (
        ArrayQueryParameter, QueryJobConfig, ScalarQueryParameter,
    )
    from backend.app.services.bigquery_service import client
    from backend.app.config.settings import get_settings

    statcast_table = get_settings().get_table_full_name("statcast_master")

    sql = f"""
    SELECT
      COUNTIF(events IS NOT NULL) AS pa,
      COUNTIF(events IS NOT NULL AND events NOT IN UNNEST(@ab_exclude)) AS ab,
      COUNTIF(events = 'single')   AS singles,
      COUNTIF(events = 'double')   AS doubles,
      COUNTIF(events = 'triple')   AS triples,
      COUNTIF(events = 'home_run') AS hr,
      COUNTIF(events IN ('walk','intent_walk')) AS bb,
      COUNTIF(events = 'hit_by_pitch') AS hbp,
      COUNTIF(events IN ('strikeout','strikeout_double_play')) AS k,
      COUNTIF(events IN ('sac_fly','sac_fly_double_play')) AS sf
    FROM `{statcast_table}`
    WHERE batter = @batter_id
      AND pitcher = @pitcher_id
      AND game_type = 'R'
    """

    job_config = QueryJobConfig(query_parameters=[
        ScalarQueryParameter("batter_id",  "INT64", batter_id),
        ScalarQueryParameter("pitcher_id", "INT64", pitcher_id),
        ArrayQueryParameter("ab_exclude",  "STRING", list(_AB_EXCLUDE_EVENTS)),
    ])

    import asyncio
    try:
        df = await asyncio.to_thread(
            lambda: client.query(sql, job_config=job_config).to_dataframe()
        )
    except Exception as e:
        structured_logger.error(
            "matchup sample-size: BQ query failed",
            error=str(e), batter_id=batter_id, pitcher_id=pitcher_id,
        )
        raise HTTPException(status_code=500, detail=f"BQ query failed: {e}") from e

    if df.empty:
        row = {"pa": 0, "ab": 0, "singles": 0, "doubles": 0, "triples": 0,
               "hr": 0, "bb": 0, "hbp": 0, "k": 0, "sf": 0}
    else:
        row = {k: _safe_int(df.iloc[0].get(k)) for k in df.columns}

    pa, ab = row["pa"], row["ab"]
    singles, doubles, triples = row["singles"], row["doubles"], row["triples"]
    hr, bb, hbp, k, sf = row["hr"], row["bb"], row["hbp"], row["k"], row["sf"]
    h = singles + doubles + triples + hr

    # OPS = OBP + SLG
    obp_denom = ab + bb + hbp + sf
    obp = (h + bb + hbp) / obp_denom if obp_denom > 0 else 0.0
    tb = singles + 2 * doubles + 3 * triples + 4 * hr
    slg = tb / ab if ab > 0 else 0.0
    ops = round(obp + slg, 3)

    return {
        "batter_id": batter_id,
        "pitcher_id": pitcher_id,
        "sample": {
            "pa": pa, "ab": ab, "h": h, "hr": hr, "bb": bb, "k": k,
        },
        "historical_ops": ops,
        "confidence": _confidence_label(pa),
    }


# ============================================================
# KPI Band エンドポイント（xwOBA / xBA / K% / BB% / HardHit% / SwStr%）
# 打者シーズン KPI + リーグ平均 + 対戦予測 xBA をまとめて返す
# ============================================================


@router.get(
    "/strategy-report/kpi-band",
    response_model=Dict[str, Any],
    summary="戦略レポート KPI バンド（打者シーズン6項目 + 比較値）",
    description="シーズン KPI は player_profile から、対戦予測 xBA とリーグ平均は statcast_master を直集計します。",
)
async def get_kpi_band_endpoint(
    batter_id: int = Query(..., description="打者 MLB ID"),
    pitcher_id: int = Query(..., description="投手 MLB ID（対戦予測 xBA 用）"),
    season: int = Query(2026, ge=2015, le=2030, description="対象シーズン"),
) -> Dict[str, Any]:
    """
    4 つの独立した BQ クエリを asyncio.gather で **並列実行** する。
    各クエリは独立しているので最遅クエリの時間 ≒ 全体時間になる。
    旧実装は直列で 25秒前後かかっていた。
    """
    import asyncio
    from google.cloud.bigquery import (
        ArrayQueryParameter, QueryJobConfig, ScalarQueryParameter,
    )
    from backend.app.services.bigquery_service import client
    from backend.app.config.settings import get_settings

    settings = get_settings()
    statcast_table = settings.get_table_full_name("statcast_master")
    mart_batter_table = settings.get_table_full_name(
        settings.bigquery_mart_batter_season_stats_table_id
        if hasattr(settings, "bigquery_mart_batter_season_stats_table_id")
        else "mart_batter_season_stats"
    )

    def _run_query(sql: str, params: list):
        """BQ 同期クエリ実行（asyncio.to_thread で並列化用）"""
        return client.query(
            sql, job_config=QueryJobConfig(query_parameters=params)
        ).to_dataframe()

    # ---- Q1. シーズン KPI（mart_batter_season_stats を直接集計）----
    # 対戦戦略タブは Player Profile から独立。mart は 2015年以降の全シーズンを持つので
    # シーズンに関係なく直接叩く。
    season_kpi_sql = f"""
    SELECT xwoba, xba, k_pct, bb_pct, hardhitpct, swstrpct, team
    FROM `{mart_batter_table}`
    WHERE batter = @batter_id AND season = @season
    LIMIT 1
    """
    season_kpi_params = [
        ScalarQueryParameter("batter_id", "INT64", batter_id),
        ScalarQueryParameter("season",    "INT64", season),
    ]

    # ---- Q2. 対戦相手 xBA（過去全シーズン累積） ----
    matchup_xba_sql = f"""
    WITH ab_pa AS (
      SELECT estimated_ba_using_speedangle, events
      FROM `{statcast_table}`
      WHERE batter = @batter_id
        AND pitcher = @pitcher_id
        AND game_type = 'R'
        AND events IS NOT NULL
        AND events NOT IN UNNEST(@ab_exclude)
    )
    SELECT
      ROUND(SAFE_DIVIDE(
        SUM(COALESCE(estimated_ba_using_speedangle, 0)),
        COUNT(*)
      ), 3) AS matchup_xba,
      COUNT(*) AS ab
    FROM ab_pa
    """
    matchup_xba_params = [
        ScalarQueryParameter("batter_id", "INT64", batter_id),
        ScalarQueryParameter("pitcher_id", "INT64", pitcher_id),
        ArrayQueryParameter("ab_exclude", "STRING", list(_AB_EXCLUDE_EVENTS)),
    ]

    # ---- Q3. 投手 throws ----
    throws_sql = f"""
    SELECT MAX(p_throws) AS p_throws
    FROM `{statcast_table}`
    WHERE pitcher = @pitcher_id AND game_type = 'R'
    """
    throws_params = [ScalarQueryParameter("pitcher_id", "INT64", pitcher_id)]

    # ---- Q4. リーグ平均（season + 投手 throws 別） ----
    # p_throws を Q3 の結果に依存するため、Q3 とは並列にできない。
    # 代わりに p_throws='L' / 'R' の両方を1クエリで取得し、Q3 の結果で選ぶ。
    league_sql = f"""
    WITH pa AS (
      SELECT p_throws, events, woba_value, woba_denom, estimated_woba_using_speedangle
      FROM `{statcast_table}`
      WHERE game_type = 'R'
        AND game_year = @season
        AND p_throws IN ('L', 'R')
        AND events IS NOT NULL
    )
    SELECT
      p_throws,
      ROUND(SAFE_DIVIDE(
        SUM(COALESCE(estimated_woba_using_speedangle, woba_value)),
        SUM(woba_denom)
      ), 3) AS lg_xwoba,
      ROUND(SAFE_DIVIDE(
        COUNTIF(events IN ('strikeout','strikeout_double_play')),
        COUNT(*)
      ), 3) AS lg_k_pct
    FROM pa
    GROUP BY p_throws
    """
    league_params = [ScalarQueryParameter("season", "INT64", season)]

    # ---- 4 クエリを並列実行 ----
    async def _safe(label: str, sql: str, params: list):
        try:
            return await asyncio.to_thread(_run_query, sql, params)
        except Exception as e:
            structured_logger.warning(f"kpi-band: {label} failed", error=str(e))
            return None

    season_df, matchup_df, throws_df, league_df = await asyncio.gather(
        _safe("season_kpi",  season_kpi_sql,  season_kpi_params),
        _safe("matchup_xba", matchup_xba_sql, matchup_xba_params),
        _safe("p_throws",    throws_sql,      throws_params),
        _safe("league_avg",  league_sql,      league_params),
    )

    # ---- 集約 ----
    season_kpi = {"xwoba": None, "xba": None, "k_pct": None,
                  "bb_pct": None, "hardhit": None, "swstr": None,
                  "team": None}
    if season_df is not None and not season_df.empty:
        import pandas as _pd
        r = season_df.iloc[0]
        team_v = r.get("team")
        team_str = None
        try:
            if team_v is not None and not _pd.isna(team_v):
                team_str = str(team_v)
        except (TypeError, ValueError):
            team_str = None
        season_kpi = {
            "xwoba":   _safe_float(r.get("xwoba")),
            "xba":     _safe_float(r.get("xba")),
            "k_pct":   _safe_float(r.get("k_pct")),
            "bb_pct":  _safe_float(r.get("bb_pct")),
            "hardhit": _safe_float(r.get("hardhitpct")),
            "swstr":   _safe_float(r.get("swstrpct")),
            "team":    team_str,
        }

    matchup_xba = None
    matchup_bbe = 0
    if matchup_df is not None and not matchup_df.empty:
        v_float = _safe_float(matchup_df.iloc[0].get("matchup_xba"))
        matchup_xba = round(v_float, 3) if v_float is not None else None
        matchup_bbe = _safe_int(matchup_df.iloc[0].get("ab"))

    p_throws = None
    if throws_df is not None and not throws_df.empty:
        v = throws_df.iloc[0].get("p_throws")
        p_throws = str(v) if v else None

    league_avg = {"xwoba": None, "k_pct": None, "p_throws": p_throws}
    if league_df is not None and not league_df.empty and p_throws in ("L", "R"):
        match = league_df[league_df["p_throws"] == p_throws]
        if not match.empty:
            v_xw = match.iloc[0].get("lg_xwoba")
            v_k  = match.iloc[0].get("lg_k_pct")
            league_avg["xwoba"] = float(v_xw) if v_xw is not None and v_xw == v_xw else None
            league_avg["k_pct"] = float(v_k)  if v_k  is not None and v_k  == v_k  else None

    return {
        "batter_id": batter_id,
        "pitcher_id": pitcher_id,
        "season": season,
        "season_kpi": season_kpi,
        "matchup_xba": matchup_xba,
        "matchup_bbe": matchup_bbe,
        "league_avg": league_avg,
    }


# ============================================================
# Heat Zone エンドポイント（5x5 ゾーン別 xwOBA）
# 打者のシーズン別「狙いゾーン / 避けるゾーン」を可視化するためのデータ
# ============================================================


@router.get(
    "/strategy-report/heat-zone",
    response_model=Dict[str, Any],
    summary="打者 5x5 ゾーン別 xwOBA",
    description="plate_x / plate_z を 5x5 にビン分けし、各セルの xwOBA を返します。",
)
async def get_heat_zone_endpoint(
    batter_id: int = Query(..., description="打者 MLB ID"),
    season: int = Query(2026, ge=2015, le=2030, description="対象シーズン"),
) -> Dict[str, Any]:
    """
    Returns:
        {
          "batter_id": int,
          "season": int,
          "zone": [[xwoba x5], ...] 5x5 配列（行 0=最上段）,
          "counts": [[N x5], ...]  対応サンプル数,
          "total_pa": int
        }

    plate_x / plate_z はフィート単位。中央 3x3 がストライクゾーン相当。
    """
    from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter
    from backend.app.services.bigquery_service import client
    from backend.app.config.settings import get_settings

    statcast_table = get_settings().get_table_full_name("statcast_master")

    sql = f"""
    WITH zoned AS (
      SELECT
        CASE
          WHEN plate_x < -0.6 THEN 0
          WHEN plate_x < -0.2 THEN 1
          WHEN plate_x <  0.2 THEN 2
          WHEN plate_x <  0.6 THEN 3
          ELSE                     4
        END AS col,
        CASE
          WHEN plate_z >= 3.5 THEN 0
          WHEN plate_z >= 3.0 THEN 1
          WHEN plate_z >= 2.5 THEN 2
          WHEN plate_z >= 2.0 THEN 3
          ELSE                     4
        END AS row_idx,
        estimated_woba_using_speedangle,
        woba_value,
        woba_denom
      FROM `{statcast_table}`
      WHERE batter = @batter_id
        AND game_year = @season
        AND game_type = 'R'
        AND plate_x IS NOT NULL
        AND plate_z IS NOT NULL
        AND woba_denom > 0
    )
    SELECT
      row_idx,
      col,
      ROUND(SAFE_DIVIDE(
        SUM(COALESCE(estimated_woba_using_speedangle, woba_value)),
        SUM(woba_denom)
      ), 3) AS xwoba,
      COUNT(*) AS n
    FROM zoned
    GROUP BY row_idx, col
    """

    import asyncio as _asyncio
    try:
        df = await _asyncio.to_thread(
            lambda: client.query(
                sql,
                job_config=QueryJobConfig(query_parameters=[
                    ScalarQueryParameter("batter_id", "INT64", batter_id),
                    ScalarQueryParameter("season",    "INT64", season),
                ]),
            ).to_dataframe()
        )
    except Exception as e:
        structured_logger.error(
            "heat-zone: BQ query failed",
            error=str(e), batter_id=batter_id, season=season,
        )
        raise HTTPException(status_code=500, detail=f"BQ query failed: {e}") from e

    # 5x5 grid を初期化（None で）
    zone: list[list[Any]] = [[None] * 5 for _ in range(5)]
    counts: list[list[int]] = [[0] * 5 for _ in range(5)]
    total_pa = 0

    if not df.empty:
        for _, r in df.iterrows():
            ri = _safe_int(r.get("row_idx"))
            ci = _safe_int(r.get("col"))
            if 0 <= ri < 5 and 0 <= ci < 5:
                v = r.get("xwoba")
                xw = float(v) if v is not None and v == v else None
                n = _safe_int(r.get("n"))
                zone[ri][ci] = xw
                counts[ri][ci] = n
                total_pa += n

    return {
        "batter_id": batter_id,
        "season": season,
        "zone": zone,
        "counts": counts,
        "total_pa": total_pa,
    }


# ============================================================
# Pitch Arsenal エンドポイント（投手の球種別シーズン成績、vs 全打者）
# ============================================================

# 球種コードのカテゴリ別マッピング（カードヘッダの code 表示と整合）
_PITCH_CODE_LABEL: Dict[str, str] = {
    "FF": "4-Seam",
    "FT": "2-Seam",
    "SI": "Sinker",
    "FC": "Cutter",
    "FS": "Splitter",
    "FO": "Forkball",
    "SL": "Slider",
    "ST": "Sweeper",
    "SV": "Slurve",
    "CU": "Curve",
    "KC": "Knuckle Curve",
    "CS": "Slow Curve",
    "CH": "Changeup",
    "SC": "Screwball",
    "EP": "Eephus",
    "KN": "Knuckle Ball",
}

# Whiff の分母（スイングと判定される description）
_SWING_DESCRIPTIONS = {
    "swinging_strike", "swinging_strike_blocked",
    "foul", "foul_tip", "foul_bunt",
    "hit_into_play", "hit_into_play_no_out",
    "missed_bunt",
}

# CSW の分子（called strike + swinging strike）
_CSW_DESCRIPTIONS = {
    "called_strike",
    "swinging_strike", "swinging_strike_blocked",
}


def _strategy_tag(xwoba: Optional[float], whiff: Optional[float], use_pct: Optional[float]):
    """
    投手側のシーズン成績だけから簡易タグを決める。
    打者弱点との掛け合わせは将来フェーズで強化。
      - AVOID:   xwOBA >= .360（被打率高、回避推奨）
      - PRIMARY: whiff% >= 35（決め球候補）
      - STEAL:   USE% < 10 かつ whiff% >= 25（隠し球で空振り誘発）
      - MIX:     それ以外
    """
    if xwoba is not None and xwoba >= 0.360:
        return "AVOID", "neg"
    if whiff is not None and whiff >= 0.35:
        return "PRIMARY", "amber"
    if use_pct is not None and whiff is not None and use_pct < 0.10 and whiff >= 0.25:
        return "STEAL", "amber"
    return "MIX", "pos"


@router.get(
    "/strategy-report/pitch-arsenal",
    response_model=Dict[str, Any],
    summary="投手の球種別シーズン成績（vs 全打者）",
    description="pitch_type ごとに VEL / USE% / xwOBA / Whiff% / CSW% を集計し、Strategy Tag を付与します。",
)
async def get_pitch_arsenal_endpoint(
    pitcher_id: int = Query(..., description="投手 MLB ID"),
    season: int = Query(2026, ge=2015, le=2030, description="対象シーズン"),
) -> Dict[str, Any]:
    """
    投手の対象シーズン全ピッチ（vs 全打者）から球種別に成績を集計する。
    打者フィルタなし。WHERE は pitcher = @pitcher_id AND game_year = @season のみ。
    """
    from google.cloud.bigquery import (
        ArrayQueryParameter, QueryJobConfig, ScalarQueryParameter,
    )
    from backend.app.services.bigquery_service import client
    from backend.app.config.settings import get_settings

    statcast_table = get_settings().get_table_full_name("statcast_master")

    # ハイブリッド集計（並列）:
    #   - mart_pitch_performance_xba_whiff: usage_pct / whiff_pct / xba / avg_speed / avg_spin_rate
    #     （事前集計済み・高速。player_profile_service._fetch_pitch_performance と同じロジック）
    #   - statcast_master: xwOBA / CSW% / pfx_x / pfx_z（mart に存在しない列のみ）
    # pitch_type をキーに Python 側で merge する。
    import asyncio
    settings = get_settings()
    mart_pitch_table = settings.get_table_full_name(
        "mart_pitch_performance_xba_whiff"
    )

    mart_sql = f"""
    SELECT
      pitch_type   AS code,
      pitch_name   AS name,
      pitch_count,
      usage_pct,
      whiff_pct,
      xba,
      avg_speed,
      avg_spin_rate
    FROM `{mart_pitch_table}`
    WHERE pitcher   = @pitcher_id
      AND game_year = @season
    ORDER BY usage_pct DESC
    """
    mart_params = [
        ScalarQueryParameter("pitcher_id", "INT64", pitcher_id),
        ScalarQueryParameter("season",     "INT64", season),
    ]

    extra_sql = f"""
    SELECT
      pitch_type AS code,
      ROUND(AVG(pfx_x) * 12, 1) AS mov_h,
      ROUND(AVG(pfx_z) * 12, 1) AS mov_v,
      SAFE_DIVIDE(
        SUM(COALESCE(estimated_woba_using_speedangle, woba_value)),
        SUM(woba_denom)
      ) AS xwoba,
      SAFE_DIVIDE(
        COUNTIF(description IN UNNEST(@csw_desc)),
        COUNT(*)
      ) AS csw
    FROM `{statcast_table}`
    WHERE pitcher   = @pitcher_id
      AND game_year = @season
      AND game_type = 'R'
      AND pitch_type IS NOT NULL
      AND pitch_type != ''
    GROUP BY pitch_type
    """
    extra_params = [
        ScalarQueryParameter("pitcher_id", "INT64", pitcher_id),
        ScalarQueryParameter("season",     "INT64", season),
        ArrayQueryParameter("csw_desc",    "STRING", list(_CSW_DESCRIPTIONS)),
    ]

    # ---- Q3. 結果分布（K / BB / GB / LD / FB）+ 打球品質（HardHit% / 平均打球速度）----
    # events / bb_type / launch_speed を球種別に集計。
    # 母数は events IS NOT NULL（= 打席終了球）。BB+HBP は events ベース、
    # GB/LD/FB は bb_type ベース。残り（sac_bunt 等）は表示しない。
    # HardHit% は launch_speed >= 95mph の BIP 比率。
    outcome_sql = f"""
    SELECT
      pitch_type AS code,
      COUNTIF(events IS NOT NULL) AS pa,
      COUNTIF(events IN ('strikeout','strikeout_double_play')) AS k,
      COUNTIF(events IN ('walk','intent_walk','hit_by_pitch'))  AS bb_hbp,
      COUNTIF(bb_type = 'ground_ball')                          AS gb,
      COUNTIF(bb_type = 'line_drive')                           AS ld,
      COUNTIF(bb_type IN ('fly_ball','popup'))                  AS fb,
      COUNTIF(launch_speed IS NOT NULL)                         AS bbe,
      ROUND(AVG(launch_speed), 1)                               AS avg_launch_speed,
      SAFE_DIVIDE(
        COUNTIF(launch_speed >= 95),
        COUNTIF(launch_speed IS NOT NULL)
      ) AS hardhit_pct
    FROM `{statcast_table}`
    WHERE pitcher   = @pitcher_id
      AND game_year = @season
      AND game_type = 'R'
      AND pitch_type IS NOT NULL
      AND pitch_type != ''
    GROUP BY pitch_type
    """
    outcome_params = [
        ScalarQueryParameter("pitcher_id", "INT64", pitcher_id),
        ScalarQueryParameter("season",     "INT64", season),
    ]

    def _run(sql: str, params: list):
        return client.query(
            sql, job_config=QueryJobConfig(query_parameters=params)
        ).to_dataframe()

    async def _safe(label: str, sql: str, params: list):
        try:
            return await asyncio.to_thread(_run, sql, params)
        except Exception as e:
            structured_logger.warning(f"pitch-arsenal: {label} failed", error=str(e))
            return None

    mart_df, extra_df, outcome_df = await asyncio.gather(
        _safe("mart",    mart_sql,    mart_params),
        _safe("extra",   extra_sql,   extra_params),
        _safe("outcome", outcome_sql, outcome_params),
    )

    if mart_df is None:
        raise HTTPException(status_code=500, detail="pitch-arsenal: mart fetch failed")

    # extra_df を pitch_type コード → 補足列 にマップ
    extras: Dict[str, Dict[str, Any]] = {}
    if extra_df is not None and not extra_df.empty:
        for _, r in extra_df.iterrows():
            code = str(r.get("code") or "").upper()
            extras[code] = {
                "mov_h": _safe_float(r.get("mov_h")),
                "mov_v": _safe_float(r.get("mov_v")),
                "xwoba": _safe_float(r.get("xwoba")),
                "csw":   _safe_float(r.get("csw")),
            }

    # outcome_df を pitch_type コード → 結果分布・打球品質 にマップ
    outcomes: Dict[str, Dict[str, Any]] = {}
    if outcome_df is not None and not outcome_df.empty:
        for _, r in outcome_df.iterrows():
            code = str(r.get("code") or "").upper()
            outcomes[code] = {
                "pa":     _safe_int(r.get("pa")),
                "k":      _safe_int(r.get("k")),
                "bb":     _safe_int(r.get("bb_hbp")),
                "gb":     _safe_int(r.get("gb")),
                "ld":     _safe_int(r.get("ld")),
                "fb":     _safe_int(r.get("fb")),
                "bbe":    _safe_int(r.get("bbe")),
                "avgEv":  _safe_float(r.get("avg_launch_speed")),
                "hardHit": _safe_float(r.get("hardhit_pct")),
            }

    arsenal = []
    total_pitches = 0
    if not mart_df.empty:
        for _, r in mart_df.iterrows():
            code = str(r.get("code") or "").upper()
            name = str(r.get("name") or _PITCH_CODE_LABEL.get(code, code))
            pitch_count = _safe_int(r.get("pitch_count"))
            total_pitches += pitch_count

            use_pct = _safe_float(r.get("usage_pct"))   # mart の値域 (0-1 想定)
            whiff   = _safe_float(r.get("whiff_pct"))
            xba     = _safe_float(r.get("xba"))
            ex      = extras.get(code, {})
            xwoba   = ex.get("xwoba")
            csw     = ex.get("csw")
            oc      = outcomes.get(code, {})

            # 結果分布を %（0-100, 1桁）に整形。母数は pa。
            pa = _safe_int(oc.get("pa"))
            def _pct(n):
                return round(n / pa * 100, 1) if pa > 0 and n is not None else None
            outcome_mix = {
                "pa": pa,
                "k_pct":  _pct(oc.get("k")),
                "bb_pct": _pct(oc.get("bb")),
                "gb_pct": _pct(oc.get("gb")),
                "ld_pct": _pct(oc.get("ld")),
                "fb_pct": _pct(oc.get("fb")),
            }
            quality = {
                "bbe":     _safe_int(oc.get("bbe")),
                "avgEv":   oc.get("avgEv"),
                "hardHit": round(oc["hardHit"] * 100, 1)
                            if oc.get("hardHit") is not None else None,
            }

            rec, color = _strategy_tag(xwoba, whiff, use_pct)
            arsenal.append({
                "code": code,
                "name": name,
                "vel":  _safe_float(r.get("avg_speed")),
                "use":  round(use_pct * 100, 1) if use_pct is not None else None,
                "spin": _safe_int(r.get("avg_spin_rate")),
                "mov": {
                    "h": ex.get("mov_h"),
                    "v": ex.get("mov_v"),
                },
                "batXba":   xba,
                "batXwoba": xwoba,
                "swStr":    round(whiff * 100, 1) if whiff is not None else None,
                "csw":      round(csw   * 100, 1) if csw   is not None else None,
                "rec":      rec,
                "recColor": color,
                "outcomes": outcome_mix,
                "quality":  quality,
            })

    return {
        "pitcher_id": pitcher_id,
        "season": season,
        "arsenal": arsenal,
        "total_pitches": total_pitches,
    }


# ============================================================
# Spray Chart エンドポイント（打者の打球方向分布 + 方向別 SLG）
# ============================================================


@router.get(
    "/strategy-report/spray",
    response_model=Dict[str, Any],
    summary="打者の打球方向分布（Pull / Center / Oppo）",
    description="hc_x と stand から Pull/Center/Oppo を判定し、各方向の打球比率と方向別 SLG を返します。",
)
async def get_spray_endpoint(
    batter_id: int = Query(..., description="打者 MLB ID"),
    season: int = Query(2026, ge=2015, le=2030, description="対象シーズン"),
) -> Dict[str, Any]:
    """
    境界値は既存 mart_batter_performance_hit_loc_quality.sql に準拠:
      - hc_x < 100   → Left
      - 100..155     → Center
      - hc_x > 155   → Right
    Pull/Oppo は stand で反転:
      - 右打者: Pull = Left, Oppo = Right
      - 左打者: Pull = Right, Oppo = Left

    SLG（方向別）= 各方向の打球の総塁打数 / 各方向の打球数
    """
    from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter
    from backend.app.services.bigquery_service import client
    from backend.app.config.settings import get_settings

    statcast_table = get_settings().get_table_full_name("statcast_master")

    sql = f"""
    WITH bip AS (
      SELECT
        stand,
        hc_x,
        events
      FROM `{statcast_table}`
      WHERE batter   = @batter_id
        AND game_year = @season
        AND game_type = 'R'
        AND hc_x IS NOT NULL
        AND bb_type IS NOT NULL
    ),
    classified AS (
      SELECT
        CASE
          WHEN (stand = 'R' AND hc_x < 100) OR (stand = 'L' AND hc_x > 155) THEN 'PULL'
          WHEN hc_x BETWEEN 100 AND 155                                      THEN 'CENTER'
          ELSE                                                                    'OPPO'
        END AS spray_zone,
        events
      FROM bip
    )
    SELECT
      spray_zone,
      COUNT(*) AS bip,
      SUM(
        CASE
          WHEN events = 'single'   THEN 1
          WHEN events = 'double'   THEN 2
          WHEN events = 'triple'   THEN 3
          WHEN events = 'home_run' THEN 4
          ELSE 0
        END
      ) AS tb
    FROM classified
    GROUP BY spray_zone
    """

    import asyncio as _asyncio
    try:
        df = await _asyncio.to_thread(
            lambda: client.query(
                sql,
                job_config=QueryJobConfig(query_parameters=[
                    ScalarQueryParameter("batter_id", "INT64", batter_id),
                    ScalarQueryParameter("season",    "INT64", season),
                ]),
            ).to_dataframe()
        )
    except Exception as e:
        structured_logger.error(
            "spray: BQ query failed",
            error=str(e), batter_id=batter_id, season=season,
        )
        raise HTTPException(status_code=500, detail=f"BQ query failed: {e}") from e

    # 集計: zone -> {bip, tb}
    by_zone: Dict[str, Dict[str, int]] = {}
    total_bip = 0
    if not df.empty:
        for _, r in df.iterrows():
            z = str(r.get("spray_zone") or "").upper()
            n = _safe_int(r.get("bip"))
            tb = _safe_int(r.get("tb"))
            by_zone[z] = {"bip": n, "tb": tb}
            total_bip += n

    # design 互換のため PULL → CENTER → OPPO の固定順
    spray = []
    for z, label in [("PULL", "RIGHT"), ("CENTER", "MID"), ("OPPO", "LEFT")]:
        d = by_zone.get(z, {"bip": 0, "tb": 0})
        n  = d["bip"]
        tb = d["tb"]
        pct = round(n / total_bip * 100, 1) if total_bip > 0 else 0.0
        slg = round(tb / n, 3) if n > 0 else 0.0
        spray.append({
            "zone":  z,
            "label": label,
            "pct":   pct,
            "slg":   slg,
        })

    return {
        "batter_id": batter_id,
        "season":    season,
        "spray":     spray,
        "total_bip": total_bip,
    }


# ============================================================
# Count-State Call Matrix エンドポイント（12 カウント × 投手の最頻球種）
# ユースケース: 打者が「対戦投手のカウント別配球傾向」を確認するための参考情報。
# 対戦ペアでは絞らず、投手のシーズン全球（vs 全打者）から集計する。
# 打者は関与しない（xwOBA 等も使わない）。
# ============================================================


def _count_conf_label(pitch_pct: Optional[float]) -> str:
    """
    カウント別マトリクス用の信頼度ラベル。
    最頻球種の使用率（0-100）で判定する。
      - >= 50%: HIGH（このカウントは半分以上その球で占められており、狙い球として頼れる）
      - >= 35%: MED（傾向あり）
      - <  35%: LOW（散らばっており狙いにくい）
    サンプル数は別途 pitches で示し、ラベル判定には使わない（傾向の明確さ ≠ サンプル量）。
    """
    if pitch_pct is None:
        return "LOW"
    if pitch_pct >= 50.0:
        return "HIGH"
    if pitch_pct >= 35.0:
        return "MED"
    return "LOW"


@router.get(
    "/strategy-report/count-matrix",
    response_model=Dict[str, Any],
    summary="投手のカウント別最頻球種マトリクス（12 カウント × pitch_type）",
    description=(
        "対象投手のシーズン全球から、各カウント (balls, strikes) において最も多投された球種を返します。"
        " 打者やペア対戦では絞らず、純粋な投手の配球傾向のみ。"
    ),
)
async def get_count_matrix_endpoint(
    pitcher_id: int = Query(..., description="投手 MLB ID"),
    season: int = Query(2026, ge=2015, le=2030, description="対象シーズン"),
) -> Dict[str, Any]:
    """
    Returns:
        {
          "pitcher_id": int, "season": int,
          "counts": [
            {"c": "0-0", "call": "FF", "conf": "HIGH",
             "pitches": 312, "pitchPct": 48.5},
            ...
          ]
        }

    pitchPct は最頻球種がそのカウント内で占める割合（0-100）。
    pitches は各カウントの総球数（信頼度判定の母数）。
    """
    from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter
    from backend.app.services.bigquery_service import client
    from backend.app.config.settings import get_settings

    statcast_table = get_settings().get_table_full_name("statcast_master")

    sql = f"""
    WITH base AS (
      SELECT balls, strikes, pitch_type
      FROM `{statcast_table}`
      WHERE pitcher    = @pitcher_id
        AND game_year  = @season
        AND game_type  = 'R'
        AND balls   BETWEEN 0 AND 3
        AND strikes BETWEEN 0 AND 2
        AND pitch_type IS NOT NULL
        AND pitch_type != ''
    ),
    agg AS (
      SELECT balls, strikes, pitch_type, COUNT(*) AS pitch_count
      FROM base
      GROUP BY balls, strikes, pitch_type
    ),
    cell_total AS (
      SELECT balls, strikes, SUM(pitch_count) AS total_pitches
      FROM agg
      GROUP BY balls, strikes
    ),
    ranked AS (
      SELECT
        a.balls,
        a.strikes,
        a.pitch_type,
        a.pitch_count,
        c.total_pitches,
        ROW_NUMBER() OVER (
          PARTITION BY a.balls, a.strikes
          ORDER BY a.pitch_count DESC, a.pitch_type
        ) AS rn
      FROM agg a
      JOIN cell_total c USING (balls, strikes)
    )
    SELECT balls, strikes, pitch_type, pitch_count, total_pitches
    FROM ranked
    WHERE rn = 1
    ORDER BY balls, strikes
    """

    import asyncio as _asyncio
    try:
        df = await _asyncio.to_thread(
            lambda: client.query(
                sql,
                job_config=QueryJobConfig(query_parameters=[
                    ScalarQueryParameter("pitcher_id", "INT64", pitcher_id),
                    ScalarQueryParameter("season",     "INT64", season),
                ]),
            ).to_dataframe()
        )
    except Exception as e:
        structured_logger.error(
            "count-matrix: BQ query failed",
            error=str(e), pitcher_id=pitcher_id, season=season,
        )
        raise HTTPException(status_code=500, detail=f"BQ query failed: {e}") from e

    by_cell: Dict[str, Dict[str, Any]] = {}
    if not df.empty:
        for _, r in df.iterrows():
            b = _safe_int(r.get("balls"))
            s = _safe_int(r.get("strikes"))
            code = str(r.get("pitch_type") or "").upper()
            pitch_count = _safe_int(r.get("pitch_count"))
            total = _safe_int(r.get("total_pitches"))

            pitch_pct = round(pitch_count / total * 100, 1) if total > 0 else None
            by_cell[f"{b}-{s}"] = {
                "c": f"{b}-{s}",
                "call":     code or None,
                "conf":     _count_conf_label(pitch_pct),
                "pitches":  total,
                "pitchPct": pitch_pct,
            }

    counts: list = []
    for b in range(0, 4):
        for s in range(0, 3):
            key = f"{b}-{s}"
            counts.append(by_cell.get(key, {
                "c": key, "call": None, "conf": "LOW",
                "pitches": 0, "pitchPct": None,
            }))

    return {
        "pitcher_id": pitcher_id,
        "season":     season,
        "counts":     counts,
    }


# ============================================================
# Recent PA エンドポイント（直近対戦・通算）
# 当該打者×投手の打席終了球を game_date DESC で最新 N 打席返す。
# シーズン縛りなし（サンプルを稼ぐため通算）。
# ============================================================


_EVENTS_TO_PA_LABEL: Dict[str, str] = {
    "single":   "1B",
    "double":   "2B",
    "triple":   "3B",
    "home_run": "HR",
    "walk":         "BB",
    "intent_walk":  "BB",
    "hit_by_pitch": "HBP",
    "strikeout":              "K",
    "strikeout_double_play":  "K",
    "sac_fly":              "SAC",
    "sac_fly_double_play":  "SAC",
    "sac_bunt":             "SAC",
    "sac_bunt_double_play": "SAC",
    "field_error": "ERR",
}

_BB_TYPE_JP = {
    "ground_ball": "ゴロ",
    "line_drive": "ライナー",
    "fly_ball":   "フライ",
    "popup":      "ポップ",
}


def _pa_label(events: Optional[str]) -> str:
    """events 値を打席結果ラベルに変換。マップに無いものは OUT。"""
    if not events:
        return "OUT"
    return _EVENTS_TO_PA_LABEL.get(events, "OUT")


def _pa_note(events: Optional[str], description: Optional[str],
             pitch_type: Optional[str], bb_type: Optional[str],
             launch_speed: Optional[float]) -> str:
    """打席結果の補足注釈（球種 + 結果）を組み立てる。"""
    pt = (pitch_type or "").strip()
    if events in ("strikeout", "strikeout_double_play"):
        if description == "swinging_strike" or description == "swinging_strike_blocked":
            return f"{pt} 空振り三振".strip()
        if description == "called_strike":
            return f"{pt} 見逃し三振".strip()
        return f"{pt} 三振".strip()
    if events in ("walk", "intent_walk"):
        return "四球"
    if events == "hit_by_pitch":
        return "死球"
    if events in ("single", "double", "triple", "home_run"):
        bb = _BB_TYPE_JP.get(bb_type or "", "")
        ev = f" {round(launch_speed)}mph" if launch_speed else ""
        body = f"{pt} {bb}{ev}".strip()
        return body or _pa_label(events)
    if bb_type:
        bb = _BB_TYPE_JP.get(bb_type, "")
        return f"{pt} {bb}".strip()
    return pt or _pa_label(events)


@router.get(
    "/strategy-report/recent-pa",
    response_model=Dict[str, Any],
    summary="直近対戦（打者×投手の最新N打席・通算）",
    description=(
        "statcast_master から当該打者×投手の打席終了球（events IS NOT NULL）を "
        "game_date 降順で最新 N 件返します。シーズン縛りなし（通算）。"
    ),
)
async def get_recent_pa_endpoint(
    batter_id: int = Query(..., description="打者 MLB ID"),
    pitcher_id: int = Query(..., description="投手 MLB ID"),
    limit: int = Query(10, ge=1, le=30, description="取得件数（最大 30）"),
) -> Dict[str, Any]:
    """
    Returns:
      {
        "batter_id": int, "pitcher_id": int, "limit": int, "total": int,
        "recent": [
          {"d": "08/02", "pa": "K", "note": "FS 空振り三振",
           "date": "2025-08-02", "events": "strikeout",
           "pitch_type": "FS", "bb_type": null, "ev": null},
          ...
        ]
      }
    """
    from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter
    from backend.app.services.bigquery_service import client
    from backend.app.config.settings import get_settings

    statcast_table = get_settings().get_table_full_name("statcast_master")

    sql = f"""
    SELECT
      game_date,
      at_bat_number,
      events,
      description,
      pitch_type,
      bb_type,
      launch_speed
    FROM `{statcast_table}`
    WHERE batter   = @batter_id
      AND pitcher  = @pitcher_id
      AND game_type = 'R'
      AND events IS NOT NULL
    ORDER BY game_date DESC, at_bat_number DESC
    LIMIT @limit
    """

    import asyncio as _asyncio
    try:
        df = await _asyncio.to_thread(
            lambda: client.query(
                sql,
                job_config=QueryJobConfig(query_parameters=[
                    ScalarQueryParameter("batter_id",  "INT64", batter_id),
                    ScalarQueryParameter("pitcher_id", "INT64", pitcher_id),
                    ScalarQueryParameter("limit",      "INT64", limit),
                ]),
            ).to_dataframe()
        )
    except Exception as e:
        structured_logger.error(
            "recent-pa: BQ query failed",
            error=str(e), batter_id=batter_id, pitcher_id=pitcher_id,
        )
        raise HTTPException(status_code=500, detail=f"BQ query failed: {e}") from e

    recent: list = []
    if not df.empty:
        for _, r in df.iterrows():
            events = r.get("events")
            events = str(events) if events is not None else None
            description = r.get("description")
            description = str(description) if description is not None else None
            pitch_type = r.get("pitch_type")
            pitch_type = str(pitch_type).upper() if pitch_type else None
            bb_type = r.get("bb_type")
            bb_type = str(bb_type) if bb_type is not None else None
            ls = _safe_float(r.get("launch_speed"))

            game_date = r.get("game_date")
            # game_date は date / Timestamp 型。短縮表示 "MM/DD" と ISO 文字列の両方を返す。
            try:
                date_obj = game_date if game_date is None else (
                    game_date.date() if hasattr(game_date, "date") else game_date
                )
                date_iso = date_obj.isoformat() if date_obj is not None else None
                short = date_obj.strftime("%m/%d") if date_obj is not None else ""
            except Exception:
                date_iso = str(game_date) if game_date is not None else None
                short = ""

            recent.append({
                "d":          short,
                "date":       date_iso,
                "pa":         _pa_label(events),
                "note":       _pa_note(events, description, pitch_type, bb_type, ls),
                "events":     events,
                "pitch_type": pitch_type,
                "bb_type":    bb_type,
                "ev":         round(ls, 1) if ls is not None else None,
            })

    return {
        "batter_id":  batter_id,
        "pitcher_id": pitcher_id,
        "limit":      limit,
        "total":      len(recent),
        "recent":     recent,
    }


# ============================================================
# Tactics エンドポイント（AI 生成・LLM 使用）
# 対戦戦略タブの既存7セクションのデータをコンテキストに、
# 打者または投手の戦術カードを 4〜6 個生成する。
# 数値捏造防止のため、出力に含まれる数値が context に存在するか軽量検証する。
# ============================================================


_TACTIC_TIERS_BATTER = ["SIT_ON", "TAKE", "PROTECT", "COUNT", "OFFENSIVE"]
_TACTIC_TIERS_PITCHER = ["WEAPON", "AVOID", "DEFENSE", "SETUP"]
_TACTIC_ICONS = ["target", "alert", "users", "bolt", "shield", "crosshair"]


def _failure_tactics_card(reason: str) -> list:
    """LLM 失敗時のフォールバックカード。"""
    return [{
        "tier":   "ALERT",
        "title":  "AI生成失敗",
        "detail": f"戦術の自動生成に失敗しました（{reason}）。時間をおいて再度お試しください。",
        "icon":   "alert",
    }]


def _extract_numbers(text: str) -> list:
    """detail/title から数値表記を抽出（捏造検証用）。
    対応形式: .184 / 0.184 / 96.1 / 78 / 78% / xwOBA .184 等
    """
    import re
    patterns = [
        r"\.\d{3}\b",            # .184
        r"\b\d+\.\d+\b",         # 96.1, 38.5
        r"\b\d+%",               # 78%
        r"\b\d+mph\b",           # 95mph
    ]
    found: list = []
    for pat in patterns:
        found.extend(re.findall(pat, text, flags=re.IGNORECASE))
    return found


def _verify_tactic_numbers(tactic: dict, context_str: str) -> list:
    """tactic.detail/title から数値を抽出し、context に含まれない数値リストを返す。
    空リストなら検証 OK。
    """
    text = f"{tactic.get('title','')} {tactic.get('detail','')}"
    numbers = _extract_numbers(text)
    return [n for n in numbers if n not in context_str]


@router.get(
    "/strategy-report/tactics",
    response_model=Dict[str, Any],
    summary="戦術カード生成（LLM・対戦戦略タブ内データのみ参照）",
    description=(
        "side=batter または pitcher を受け、対戦戦略タブの既存 7 セクションのデータを"
        "コンテキストとして Gemini 2.5 Flash に渡し、4〜6 件の戦術カードを返します。"
    ),
)
async def get_tactics_endpoint(
    batter_id: int = Query(..., description="打者 MLB ID"),
    pitcher_id: int = Query(..., description="投手 MLB ID"),
    season: int = Query(2026, ge=2015, le=2030),
    side: str = Query(..., pattern="^(batter|pitcher)$",
                      description="batter: 打者戦術 / pitcher: 投手戦術"),
) -> Dict[str, Any]:
    import asyncio
    import json
    import os
    from langchain_google_genai import ChatGoogleGenerativeAI
    from pydantic import BaseModel, Field
    from typing import List, Literal

    request_id = str(uuid4())

    # Token budget
    token_budget = get_token_budget_service()
    if token_budget.is_budget_exceeded("report"):
        return {
            "request_id":   request_id,
            "side":         side,
            "tactics":      _failure_tactics_card("本日のAI利用上限に達しました"),
            "verified":     False,
            "service_at_capacity": True,
        }

    structured_logger.info(
        "tactics request",
        request_id=request_id, batter_id=batter_id, pitcher_id=pitcher_id,
        season=season, side=side,
    )

    # ---- 1. 7 セクションのデータを並列取得 ----
    async def _safe_call(label: str, coro):
        try:
            return await coro
        except Exception as e:
            structured_logger.warning(
                f"tactics: {label} fetch failed", error=str(e),
            )
            return None

    sample_task = _safe_call("sample-size",
        get_matchup_sample_size_endpoint(batter_id=batter_id, pitcher_id=pitcher_id))
    kpi_task = _safe_call("kpi-band",
        get_kpi_band_endpoint(batter_id=batter_id, pitcher_id=pitcher_id, season=season))
    heat_task = _safe_call("heat-zone",
        get_heat_zone_endpoint(batter_id=batter_id, season=season))
    arsenal_task = _safe_call("pitch-arsenal",
        get_pitch_arsenal_endpoint(pitcher_id=pitcher_id, season=season))
    spray_task = _safe_call("spray",
        get_spray_endpoint(batter_id=batter_id, season=season))
    count_task = _safe_call("count-matrix",
        get_count_matrix_endpoint(pitcher_id=pitcher_id, season=season))
    recent_task = _safe_call("recent-pa",
        get_recent_pa_endpoint(batter_id=batter_id, pitcher_id=pitcher_id, limit=10))

    sample, kpi, heat, arsenal, spray, count_matrix, recent = await asyncio.gather(
        sample_task, kpi_task, heat_task, arsenal_task, spray_task, count_task, recent_task
    )

    # ---- 2. コンテキスト pack 構築（LLM が読みやすい形に整形） ----
    # heat zone は xwOBA top-3 ホットスポット / cold-3 だけ抽出してトークン節約
    hot_cells: list = []
    cold_cells: list = []
    if heat and heat.get("zone"):
        flat = []
        for ri, row in enumerate(heat["zone"]):
            for ci, v in enumerate(row):
                if v is not None:
                    flat.append({"row": ri, "col": ci, "xwoba": round(float(v), 3)})
        flat.sort(key=lambda x: x["xwoba"], reverse=True)
        hot_cells = flat[:3]
        cold_cells = sorted(flat, key=lambda x: x["xwoba"])[:3]

    context = {
        "side": side,
        "matchup_sample": (sample or {}).get("sample"),
        "historical_ops": (sample or {}).get("historical_ops"),
        "confidence":     (sample or {}).get("confidence"),
        "batter_kpi":     (kpi or {}).get("season_kpi"),
        "matchup_xba":    (kpi or {}).get("matchup_xba"),
        "league_avg":     (kpi or {}).get("league_avg"),
        "heat_zone": {
            "hot":  hot_cells,
            "cold": cold_cells,
            "total_pa": (heat or {}).get("total_pa"),
            "note": "row 0=高め/4=低め, col 0=外角L基準/4=内角L基準. xwOBA はサンプル付きセルのみ抽出",
        },
        "pitcher_arsenal": [
            {
                "code": p.get("code"),
                "name": p.get("name"),
                "vel":  p.get("vel"),
                "use":  p.get("use"),
                "xwoba":   p.get("batXwoba"),
                "swStr":   p.get("swStr"),
                "csw":     p.get("csw"),
                "rec":     p.get("rec"),
                "outcomes": p.get("outcomes"),
                "quality":  p.get("quality"),
            }
            for p in (arsenal or {}).get("arsenal", [])
        ],
        "spray": (spray or {}).get("spray"),
        "count_matrix": (count_matrix or {}).get("counts"),
        "recent_pa": [
            {"d": r.get("d"), "pa": r.get("pa"), "note": r.get("note")}
            for r in (recent or {}).get("recent", [])[:10]
        ],
    }
    context_json = json.dumps(context, ensure_ascii=False, indent=2)

    # ---- 3. プロンプト構築 ----
    if side == "batter":
        side_label = "打者"
        tier_list = ", ".join(_TACTIC_TIERS_BATTER)
        side_role = "打者がこの投手を攻略するための戦術"
    else:
        side_label = "投手"
        tier_list = ", ".join(_TACTIC_TIERS_PITCHER)
        side_role = "投手がこの打者を抑えるための戦術"

    system_prompt = f"""あなたはMLBのスカウティング担当です。
以下のJSONコンテキストに基づき、{side_role}を 4〜6 個生成してください。

絶対遵守:
- 与えられたJSONコンテキストに含まれる数値・球種コード・カウントのみを根拠とする
- コンテキストに無い情報（過去シーズン、別の投手・打者の比較、リーグ全体の一般論、推測）は使用禁止
- 数値を引用する際はコンテキストの値を改変せず転記すること（例: .184 / 78% / 96.1mph）
- title は 14 文字以内（必須）
- detail は 80 文字以内、必ず数値根拠を含めること（必須）
- 出力言語は日本語

利用可能な tier（必ずいずれかから選ぶ）:
{tier_list}

利用可能な icon（必ずいずれかから選ぶ）:
target, alert, users, bolt, shield, crosshair
"""

    user_prompt = f"""対戦データ（JSONコンテキスト）:
{context_json}

上記のみを根拠に、{side_label}向けの戦術カードを 4〜6 個生成してください。"""

    # ---- 4. Structured Output で LLM 呼び出し ----
    if side == "batter":
        TierLiteral = Literal["SIT_ON", "TAKE", "PROTECT", "COUNT", "OFFENSIVE"]
    else:
        TierLiteral = Literal["WEAPON", "AVOID", "DEFENSE", "SETUP"]

    class Tactic(BaseModel):
        tier:   TierLiteral
        title:  str = Field(..., max_length=20)
        detail: str = Field(..., max_length=120)
        icon:   Literal["target", "alert", "users", "bolt", "shield", "crosshair"]

    class TacticsResponse(BaseModel):
        tactics: List[Tactic] = Field(..., min_length=3, max_length=6)

    try:
        api_key = os.getenv("GEMINI_API_KEY_V2")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY_V2 が設定されていません")
        from backend.app.services.llm_gateway_service import LangchainUsageCallback
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0,
            callbacks=[LangchainUsageCallback(feature="strategy_tactics", model="gemini-2.5-flash", pool="report")],
        )
        structured_llm = llm.with_structured_output(TacticsResponse)

        result = await asyncio.to_thread(
            structured_llm.invoke,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
        )
        # Pydantic モデル → dict
        tactics_raw = [t.model_dump() if hasattr(t, "model_dump") else dict(t)
                       for t in result.tactics]

    except Exception as e:
        structured_logger.error(
            "tactics: LLM call failed",
            request_id=request_id, error=str(e), side=side,
        )
        return {
            "request_id": request_id,
            "side":       side,
            "tactics":    _failure_tactics_card(f"LLM呼び出しエラー"),
            "verified":   False,
        }

    # ---- 5. 数値捏造の軽量検証 ----
    all_verified = True
    verified_tactics: list = []
    for t in tactics_raw:
        unverified = _verify_tactic_numbers(t, context_json)
        if unverified:
            all_verified = False
            structured_logger.warning(
                "tactics: number not in context",
                request_id=request_id, side=side,
                title=t.get("title"), unverified_numbers=unverified,
            )
        verified_tactics.append(t)

    return {
        "request_id": request_id,
        "side":       side,
        "tactics":    verified_tactics,
        "verified":   all_verified,
    }
