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
    if token_budget.is_budget_exceeded():
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

        model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GEMINI_API_KEY_V2"),
            temperature=0,
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

    try:
        df = client.query(sql, job_config=job_config).to_dataframe()
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

    # ---- Q1. シーズン KPI（mart から必要列のみ。RANK 計算なしで軽量） ----
    season_kpi_sql = f"""
    SELECT xwoba, xba, k_pct, bb_pct, hardhitpct, swstrpct
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
                  "bb_pct": None, "hardhit": None, "swstr": None}
    if season_df is not None and not season_df.empty:
        r = season_df.iloc[0]
        season_kpi = {
            "xwoba":   _safe_float(r.get("xwoba")),
            "xba":     _safe_float(r.get("xba")),
            "k_pct":   _safe_float(r.get("k_pct")),
            "bb_pct":  _safe_float(r.get("bb_pct")),
            "hardhit": _safe_float(r.get("hardhitpct")),
            "swstr":   _safe_float(r.get("swstrpct")),
        }

    matchup_xba = None
    matchup_bbe = 0
    if matchup_df is not None and not matchup_df.empty:
        v = matchup_df.iloc[0].get("matchup_xba")
        matchup_xba = round(float(v), 3) if v is not None and v == v else None
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

    try:
        df = client.query(
            sql,
            job_config=QueryJobConfig(query_parameters=[
                ScalarQueryParameter("batter_id", "INT64", batter_id),
                ScalarQueryParameter("season",    "INT64", season),
            ]),
        ).to_dataframe()
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
