"""
選手プロフィールページ用データ取得サービス
Bio情報（dim_players_master + dim_teams）と
現シーズンKPI（fact_batting_stats_with_risp / fact_pitching_stats_master）を返す

パフォーマンス最適化（並列実行）:
- Phase 1: Bio クエリ（idfg 取得のため先行実行）
- Phase 2: 打者KPI / 投手KPI / RISP season を並列実行
- Phase 3: 残り全クエリを並列実行
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
import numpy as np
from google.cloud import bigquery

from backend.app.api.schemas import (
    PlayerProfileResponse,
    PlayerBio,
    PlayerBattingKPI,
    PlayerPitchingKPI,
    PlayerMonthlyRow,
    PlayerRISPSeasonRow,
    PlayerRISPMonthlyRow,
    PlayerInningRow,
    StatcastPitchRow,
    PitchPerformanceRow,
    HitLocationRow,
    WhiffHeatmapRow,
    CountStateWobaRow,
    XwobaZoneRow,
    BatterClutchRow,
    PitcherRispRow,
    PitcherTtoRow,
)
from .base import (
    get_bq_client,
    logger,
    PROJECT_ID,
    DATASET_ID,
    BATTING_STATS_TABLE_ID,
    BATTING_OFFENSIVE_STATS_TABLE_ID,
    BAT_PERFORMANCE_RISP_TABLE_ID,
    DIM_PLAYERS_MASTER_TABLE_ID,
    PITCHING_STATS_TABLE_ID,
    PITCHING_PERFORMANCE_BY_INNING_TABLE_ID,
    STATCAST_MASTER_TABLE_ID,
    PITCH_PERFORMANCE_XBA_WHIFF_TABLE_ID,
    BATTER_HIT_LOC_QUALITY_TABLE_ID,
    PITCH_WHIFF_HEATMAP_TABLE_ID,
    BATTER_COUNT_STATE_WOBA_TABLE_ID,
    BATTER_XWOBA_ZONE_TABLE_ID,
    MART_BATTER_CLUTCH_TABLE_ID,
    MART_BATTER_SEASON_STATS_TABLE_ID,
    PITCHER_RISP_PERFORMANCE_TABLE_ID,
    PITCHER_TTO_VELO_SPIN_TABLE_ID,
    MART_PITCHER_ERA_BY_INNING_TABLE_ID,
    MART_PITCHER_SEASON_STATS_TABLE_ID,
)


def _nan_to_none(v):
    """単一値のNaN を None に変換する"""
    try:
        if isinstance(v, (float, np.floating)) and np.isnan(v):
            return None
    except (TypeError, ValueError):
        pass
    return v


def _clean_row(df) -> dict:
    """DataFrameの先頭行をdictに変換し、NaN/NaT を None に置換する"""
    if df.empty:
        return {}
    row = df.iloc[0].to_dict()
    return {k: _nan_to_none(v) for k, v in row.items()}


def _bat_rank_cols(p: str = "") -> str:
    """p='b.' のようなプレフィックスを付けてRANKカラム列を生成する"""
    return f"""
        RANK() OVER (ORDER BY {p}avg        DESC) AS avg_rank,
        RANK() OVER (ORDER BY {p}obp        DESC) AS obp_rank,
        RANK() OVER (ORDER BY {p}slg        DESC) AS slg_rank,
        RANK() OVER (ORDER BY {p}ops        DESC) AS ops_rank,
        RANK() OVER (ORDER BY {p}hr         DESC) AS hr_rank,
        RANK() OVER (ORDER BY {p}rbi        DESC) AS rbi_rank,
        RANK() OVER (ORDER BY {p}sb         DESC) AS sb_rank,
        RANK() OVER (ORDER BY {p}bb         DESC) AS bb_rank,
        RANK() OVER (ORDER BY {p}so         ASC)  AS so_rank,
        RANK() OVER (ORDER BY {p}woba       DESC) AS woba_rank,
        RANK() OVER (ORDER BY {p}wrcplus    DESC) AS wrcplus_rank,
        RANK() OVER (ORDER BY {p}war        DESC) AS war_rank,
        RANK() OVER (ORDER BY {p}hardhitpct DESC) AS hardhitpct_rank,
        RANK() OVER (ORDER BY {p}barrelpct  DESC) AS barrelpct_rank,
        RANK() OVER (ORDER BY {p}swstrpct   ASC)  AS swstrpct_rank
    """


def _bat_rank_cols_mart(p: str = "") -> str:
    """mart_batter_season_stats 用 RANK カラム（wrcplus / war は算出不可のため NULL）"""
    return f"""
        RANK() OVER (ORDER BY {p}avg        DESC) AS avg_rank,
        RANK() OVER (ORDER BY {p}obp        DESC) AS obp_rank,
        RANK() OVER (ORDER BY {p}slg        DESC) AS slg_rank,
        RANK() OVER (ORDER BY {p}ops        DESC) AS ops_rank,
        RANK() OVER (ORDER BY {p}hr         DESC) AS hr_rank,
        RANK() OVER (ORDER BY {p}rbi        DESC) AS rbi_rank,
        RANK() OVER (ORDER BY {p}bb         DESC) AS bb_rank,
        RANK() OVER (ORDER BY {p}so         ASC)  AS so_rank,
        RANK() OVER (ORDER BY {p}woba       DESC) AS woba_rank,
        CAST(NULL AS INT64)                        AS wrcplus_rank,
        CAST(NULL AS INT64)                        AS war_rank,
        CAST(NULL AS INT64)                        AS sb_rank,
        RANK() OVER (ORDER BY {p}hardhitpct DESC) AS hardhitpct_rank,
        RANK() OVER (ORDER BY {p}barrelpct  DESC) AS barrelpct_rank,
        RANK() OVER (ORDER BY {p}swstrpct   ASC)  AS swstrpct_rank
    """


def _pit_rank_cols_mart(p: str = "") -> str:
    """mart_pitcher_season_stats 用 RANK カラム（WAR は算出不可のため NULL）"""
    return f"""
        RANK() OVER (ORDER BY {p}era        ASC)  AS era_rank,
        RANK() OVER (ORDER BY {p}whip       ASC)  AS whip_rank,
        RANK() OVER (ORDER BY {p}fip        ASC)  AS fip_rank,
        RANK() OVER (ORDER BY {p}k_9        DESC) AS k_9_rank,
        RANK() OVER (ORDER BY {p}bb_9       ASC)  AS bb_9_rank,
        CAST(NULL AS INT64)                        AS war_rank,
        RANK() OVER (ORDER BY {p}so         DESC) AS so_rank,
        RANK() OVER (ORDER BY {p}ip         DESC) AS ip_rank,
        RANK() OVER (ORDER BY {p}bb         ASC)  AS bb_rank,
        RANK() OVER (ORDER BY {p}hardhitpct ASC)  AS hardhitpct_rank,
        RANK() OVER (ORDER BY {p}barrelpct  ASC)  AS barrelpct_rank,
        RANK() OVER (ORDER BY {p}swstrpct   DESC) AS swstrpct_rank
    """


def _pit_rank_cols(p: str = "") -> str:
    return f"""
        RANK() OVER (ORDER BY {p}era        ASC)  AS era_rank,
        RANK() OVER (ORDER BY {p}whip       ASC)  AS whip_rank,
        RANK() OVER (ORDER BY {p}fip        ASC)  AS fip_rank,
        RANK() OVER (ORDER BY {p}k_9        DESC) AS k_9_rank,
        RANK() OVER (ORDER BY {p}bb_9       ASC)  AS bb_9_rank,
        RANK() OVER (ORDER BY {p}war        DESC) AS war_rank,
        RANK() OVER (ORDER BY {p}so         DESC) AS so_rank,
        RANK() OVER (ORDER BY {p}ip         DESC) AS ip_rank,
        RANK() OVER (ORDER BY {p}bb         ASC)  AS bb_rank,
        RANK() OVER (ORDER BY {p}hardhitpct ASC)  AS hardhitpct_rank,
        RANK() OVER (ORDER BY {p}barrelpct  ASC)  AS barrelpct_rank,
        RANK() OVER (ORDER BY {p}swstrpct   DESC) AS swstrpct_rank
    """


def get_player_profile(mlbid: int, season: Optional[int] = None) -> Optional[PlayerProfileResponse]:
    """
    mlbid（MLB ID）を受け取り、選手プロフィール情報を返す。
    season を指定した場合はそのシーズンのデータを、省略時は最新シーズンを返す。
    Bio: dim_players_master LEFT JOIN dim_teams
    打者KPI: fact_batting_stats_with_risp
    投手KPI: fact_pitching_stats (idfg経由でJOIN)
    """
    client = get_bq_client()

    # ── Phase 1: Bio（idfg 取得のため必須・先行実行）────────────────────────
    bio_params = [bigquery.ScalarQueryParameter("mlbid", "INT64", mlbid)]
    bio_job_config = bigquery.QueryJobConfig(query_parameters=bio_params)
    bio_query = f"""
        SELECT
            p.mlbid,
            p.idfg,
            p.full_name,
            p.primary_position,
            p.bat_side,
            p.pitch_hand,
            CAST(p.birth_date AS STRING)      AS birth_date,
            p.current_age,
            p.height,
            p.weight,
            CAST(p.mlb_debut_date AS STRING)  AS mlb_debut_date,
            t.team_name,
            t.abbreviation                    AS team_abbreviation,
            t.league,
            t.division
        FROM `{PROJECT_ID}.{DATASET_ID}.{DIM_PLAYERS_MASTER_TABLE_ID}` p
        LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.dim_teams` t
            ON p.current_team_id = t.team_id
        WHERE p.mlbid = @mlbid
        LIMIT 1
    """
    try:
        bio_df = client.query(bio_query, job_config=bio_job_config).to_dataframe()
    except Exception as e:
        logger.error(f"player_profile bio query failed for mlbid={mlbid}: {e}", exc_info=True)
        return None

    if bio_df.empty:
        logger.warning(f"No player found for mlbid={mlbid}")
        return None

    bio_data = _clean_row(bio_df)
    idfg = bio_data.pop("idfg", None)
    bio_data.pop("mlbid", None)
    bio = PlayerBio(**bio_data)

    _BAT_TABLE      = f"`{PROJECT_ID}.{DATASET_ID}.{BATTING_STATS_TABLE_ID}`"
    _PIT_TABLE      = f"`{PROJECT_ID}.{DATASET_ID}.{PITCHING_STATS_TABLE_ID}`"
    _MART_BAT_TABLE = f"`{PROJECT_ID}.{DATASET_ID}.{MART_BATTER_SEASON_STATS_TABLE_ID}`"
    _MART_PIT_TABLE = f"`{PROJECT_ID}.{DATASET_ID}.{MART_PITCHER_SEASON_STATS_TABLE_ID}`"

    # ── Phase 2 ヘルパー関数 ──────────────────────────────────────────────────

    def _fetch_batting_kpi():
        # 2026年以降: Statcast ベースの mart テーブルを使用（mlbid キー）
        # 2025年以前: Fangraphs ベースの既存テーブルを使用（idfg キー）
        use_mart = (season is not None and season >= 2026) or (season is None)

        if use_mart:
            # -- mart_batter_season_stats（2026年以降）--
            min_pa = 10
            if season is not None:
                mart_params = [
                    bigquery.ScalarQueryParameter("mlbid",  "INT64", mlbid),
                    bigquery.ScalarQueryParameter("season", "INT64", season),
                    bigquery.ScalarQueryParameter("min_pa", "INT64", min_pa),
                ]
                mart_query = f"""
                    WITH ranked AS (
                        SELECT
                            batter,
                            season, team,
                            g, pa, hr, rbi, bb, so,
                            avg, obp, slg, ops, woba,
                            hardhitpct, barrelpct, swstrpct,
                            CAST(NULL AS FLOAT64) AS war,
                            CAST(NULL AS INT64)   AS wrcplus,
                            {_bat_rank_cols_mart()}
                        FROM {_MART_BAT_TABLE}
                        WHERE season = @season AND pa >= @min_pa
                    )
                    SELECT * EXCEPT(batter) FROM ranked WHERE batter = @mlbid LIMIT 1
                """
            else:
                # season 未指定: mart の最新シーズンを動的に取得
                mart_params = [
                    bigquery.ScalarQueryParameter("mlbid",  "INT64", mlbid),
                    bigquery.ScalarQueryParameter("min_pa", "INT64", min_pa),
                ]
                mart_query = f"""
                    WITH latest AS (
                        SELECT MAX(season) AS s
                        FROM {_MART_BAT_TABLE}
                        WHERE batter = @mlbid AND pa >= @min_pa
                    ),
                    ranked AS (
                        SELECT
                            m.batter,
                            m.season, m.team,
                            m.g, m.pa, m.hr, m.rbi, m.bb, m.so,
                            m.avg, m.obp, m.slg, m.ops, m.woba,
                            m.hardhitpct, m.barrelpct, m.swstrpct,
                            CAST(NULL AS FLOAT64) AS war,
                            CAST(NULL AS INT64)   AS wrcplus,
                            {_bat_rank_cols_mart("m.")}
                        FROM {_MART_BAT_TABLE} m
                        CROSS JOIN latest l
                        WHERE m.season = l.s AND m.pa >= @min_pa
                    )
                    SELECT * EXCEPT(batter) FROM ranked WHERE batter = @mlbid LIMIT 1
                """
            mart_job_config = bigquery.QueryJobConfig(query_parameters=mart_params)
            try:
                mart_df = client.query(mart_query, job_config=mart_job_config).to_dataframe()
                data = _clean_row(mart_df)
                kpi = PlayerBattingKPI(**data) if data else None
                return {"kpi": kpi, "data": data}
            except Exception as e:
                logger.warning(f"batting_kpi (mart) query failed for mlbid={mlbid}: {e}")
                return {"kpi": None, "data": {}}

        # -- fact_batting_stats_with_risp（2025年以前）--
        if not (idfg and idfg > 0):
            return {"kpi": None, "data": {}}
        if season:
            batting_params = [
                bigquery.ScalarQueryParameter("idfg",   "INT64", idfg),
                bigquery.ScalarQueryParameter("season", "INT64", season),
                bigquery.ScalarQueryParameter("min_pa", "INT64", 350),
            ]
            batting_query = f"""
                WITH ranked AS (
                    SELECT
                        idfg, season, team, g, pa, hr, rbi, sb, bb, so,
                        avg, obp, slg, ops, woba, war, wrcplus,
                        hardhitpct, barrelpct, swstrpct,
                        {_bat_rank_cols()}
                    FROM {_BAT_TABLE}
                    WHERE season = @season AND pa >= @min_pa
                )
                SELECT * FROM ranked WHERE idfg = @idfg LIMIT 1
            """
        else:
            batting_params = [bigquery.ScalarQueryParameter("idfg", "INT64", idfg)]
            batting_query = f"""
                WITH latest AS (
                    SELECT MAX(season) AS s FROM {_BAT_TABLE} WHERE idfg = @idfg
                ),
                ranked AS (
                    SELECT
                        b.idfg, b.season, b.team, b.g, b.pa, b.hr, b.rbi, b.sb, b.bb, b.so,
                        b.avg, b.obp, b.slg, b.ops, b.woba, b.war, b.wrcplus,
                        b.hardhitpct, b.barrelpct, b.swstrpct,
                        {_bat_rank_cols("b.")}
                    FROM {_BAT_TABLE} b
                    CROSS JOIN latest l
                    WHERE b.season = l.s AND b.pa >= 350
                )
                SELECT * FROM ranked WHERE idfg = @idfg LIMIT 1
            """
        batting_job_config = bigquery.QueryJobConfig(query_parameters=batting_params)
        try:
            batting_df = client.query(batting_query, job_config=batting_job_config).to_dataframe()
            data = _clean_row(batting_df)
            kpi = PlayerBattingKPI(**data) if data else None
            return {"kpi": kpi, "data": data}
        except Exception as e:
            logger.warning(f"batting_kpi query failed for idfg={idfg}: {e}")
            return {"kpi": None, "data": {}}

    def _fetch_pitching_kpi():
        # 2026年以降: Statcast ベースの mart テーブルを使用（mlbid キー）
        # 2025年以前: Fangraphs ベースの既存テーブルを使用（idfg キー）
        use_mart = (season is not None and season >= 2026) or (season is None)

        if use_mart:
            min_ip  = 6.0
            min_gs  = 3   # ランク計算は SP（gs >= 3）のみ対象
            if season is not None:
                mart_params = [
                    bigquery.ScalarQueryParameter("mlbid",  "INT64",   mlbid),
                    bigquery.ScalarQueryParameter("season", "INT64",   season),
                    bigquery.ScalarQueryParameter("min_ip", "FLOAT64", min_ip),
                    bigquery.ScalarQueryParameter("min_gs", "INT64",   min_gs),
                ]
                mart_query = f"""
                    WITH pool AS (
                        -- ランク計算プール: SP のみ（gs >= @min_gs）
                        SELECT pitcher, {_pit_rank_cols_mart()}
                        FROM {_MART_PIT_TABLE}
                        WHERE season = @season AND ip >= @min_ip AND gs >= @min_gs
                    ),
                    target AS (
                        SELECT
                            pitcher, season, team, g, gs, ip,
                            so, bb, hbp, hr,
                            era, fip, whip, k_9, bb_9,
                            hardhitpct, barrelpct, swstrpct,
                            CAST(NULL AS FLOAT64) AS war,
                            CAST(NULL AS INT64)   AS w,
                            CAST(NULL AS INT64)   AS l,
                            CAST(NULL AS INT64)   AS sv
                        FROM {_MART_PIT_TABLE}
                        WHERE season = @season AND pitcher = @mlbid
                        LIMIT 1
                    )
                    SELECT t.* EXCEPT(pitcher), p.* EXCEPT(pitcher)
                    FROM target t
                    LEFT JOIN pool p ON t.pitcher = p.pitcher
                """
            else:
                mart_params = [
                    bigquery.ScalarQueryParameter("mlbid",  "INT64",   mlbid),
                    bigquery.ScalarQueryParameter("min_ip", "FLOAT64", min_ip),
                    bigquery.ScalarQueryParameter("min_gs", "INT64",   min_gs),
                ]
                mart_query = f"""
                    WITH latest AS (
                        SELECT MAX(season) AS s
                        FROM {_MART_PIT_TABLE}
                        WHERE pitcher = @mlbid
                    ),
                    pool AS (
                        -- ランク計算プール: SP のみ（gs >= @min_gs）
                        SELECT m.pitcher, {_pit_rank_cols_mart("m.")}
                        FROM {_MART_PIT_TABLE} m
                        CROSS JOIN latest l
                        WHERE m.season = l.s AND m.ip >= @min_ip AND m.gs >= @min_gs
                    ),
                    target AS (
                        SELECT
                            m.pitcher, m.season, m.team, m.g, m.gs, m.ip,
                            m.so, m.bb, m.hbp, m.hr,
                            m.era, m.fip, m.whip, m.k_9, m.bb_9,
                            m.hardhitpct, m.barrelpct, m.swstrpct,
                            CAST(NULL AS FLOAT64) AS war,
                            CAST(NULL AS INT64)   AS w,
                            CAST(NULL AS INT64)   AS l,
                            CAST(NULL AS INT64)   AS sv
                        FROM {_MART_PIT_TABLE} m
                        CROSS JOIN latest l
                        WHERE m.season = l.s AND m.pitcher = @mlbid
                        LIMIT 1
                    )
                    SELECT t.* EXCEPT(pitcher), p.* EXCEPT(pitcher)
                    FROM target t
                    LEFT JOIN pool p ON t.pitcher = p.pitcher
                """
            mart_job_config = bigquery.QueryJobConfig(query_parameters=mart_params)
            try:
                mart_df = client.query(mart_query, job_config=mart_job_config).to_dataframe()
                data = _clean_row(mart_df)
                kpi = PlayerPitchingKPI(**data) if data else None
                return {"kpi": kpi, "data": data}
            except Exception as e:
                logger.warning(f"pitching_kpi (mart) query failed for mlbid={mlbid}: {e}")
                return {"kpi": None, "data": {}}

        if not (idfg and idfg > 0):
            return {"kpi": None, "data": {}}
        if season:
            min_ip = 100.0 if season <= 2025 else 6.0
            pitching_params = [
                bigquery.ScalarQueryParameter("idfg",   "INT64",   idfg),
                bigquery.ScalarQueryParameter("season", "INT64",   season),
                bigquery.ScalarQueryParameter("min_ip", "FLOAT64", min_ip),
            ]
            pitching_query = f"""
                WITH pool AS (
                    SELECT idfg, {_pit_rank_cols()}
                    FROM {_PIT_TABLE}
                    WHERE season = @season AND ip >= @min_ip
                ),
                target AS (
                    SELECT idfg, season, team, g, gs, w, l, sv, ip,
                        era, whip, so, bb, fip, war,
                        k_9, bb_9, hardhitpct, barrelpct, swstrpct
                    FROM {_PIT_TABLE}
                    WHERE season = @season AND idfg = @idfg
                    LIMIT 1
                )
                SELECT
                    t.*,
                    p.era_rank, p.whip_rank, p.fip_rank, p.k_9_rank, p.bb_9_rank,
                    p.war_rank, p.so_rank, p.hardhitpct_rank, p.barrelpct_rank, p.swstrpct_rank
                FROM target t
                LEFT JOIN pool p ON t.idfg = p.idfg
            """
        else:
            pitching_params = [bigquery.ScalarQueryParameter("idfg", "INT64", idfg)]
            pitching_query = f"""
                WITH latest AS (
                    SELECT MAX(season) AS s FROM {_PIT_TABLE} WHERE idfg = @idfg
                ),
                pool AS (
                    SELECT p.idfg, {_pit_rank_cols("p.")}
                    FROM {_PIT_TABLE} p
                    CROSS JOIN latest l
                    WHERE p.season = l.s
                      AND p.ip >= CASE WHEN l.s <= 2025 THEN 100 ELSE 6 END
                ),
                target AS (
                    SELECT p.idfg, p.season, p.team, p.g, p.gs, p.w, p.l, p.sv, p.ip,
                        p.era, p.whip, p.so, p.bb, p.fip, p.war,
                        p.k_9, p.bb_9, p.hardhitpct, p.barrelpct, p.swstrpct
                    FROM {_PIT_TABLE} p
                    CROSS JOIN latest l
                    WHERE p.season = l.s AND p.idfg = @idfg
                    LIMIT 1
                )
                SELECT
                    t.*,
                    p.era_rank, p.whip_rank, p.fip_rank, p.k_9_rank, p.bb_9_rank,
                    p.war_rank, p.so_rank, p.hardhitpct_rank, p.barrelpct_rank, p.swstrpct_rank
                FROM target t
                LEFT JOIN pool p ON t.idfg = p.idfg
            """
        pitching_job_config = bigquery.QueryJobConfig(query_parameters=pitching_params)
        try:
            pitching_df = client.query(pitching_query, job_config=pitching_job_config).to_dataframe()
            data = _clean_row(pitching_df)
            kpi = PlayerPitchingKPI(**data) if data else None
            return {"kpi": kpi, "data": data}
        except Exception as e:
            logger.warning(f"pitching_kpi query failed for idfg={idfg}: {e}")
            return {"kpi": None, "data": {}}

    def _fetch_risp_season():
        risp_params = [bigquery.ScalarQueryParameter("mlbid", "INT64", int(mlbid))]
        risp_job_config = bigquery.QueryJobConfig(query_parameters=risp_params)
        risp_query = f"""
            SELECT
                game_year                                                              AS season,
                SUM(singles_at_risp)                                                   AS singles,
                SUM(doubles_at_risp)                                                   AS doubles,
                SUM(triples_at_risp)                                                   AS triples,
                SUM(home_runs_at_risp)                                                 AS home_runs,
                SUM(hits_at_risp)                                                      AS hits,
                SUM(at_bats_at_risp)                                                   AS at_bats,
                SAFE_DIVIDE(SUM(hits_at_risp), SUM(at_bats_at_risp))                  AS batting_average,
                SAFE_DIVIDE(
                    SUM(singles_at_risp)
                    + 2 * SUM(doubles_at_risp)
                    + 3 * SUM(triples_at_risp)
                    + 4 * SUM(home_runs_at_risp),
                    SUM(at_bats_at_risp)
                )                                                                      AS slugging_percentage
            FROM `{PROJECT_ID}.{DATASET_ID}.{BAT_PERFORMANCE_RISP_TABLE_ID}`
            WHERE batter_id = @mlbid
              AND game_year >= 2021
            GROUP BY game_year
            ORDER BY game_year ASC
        """
        try:
            risp_df = client.query(risp_query, job_config=risp_job_config).to_dataframe()
            if not risp_df.empty:
                return [
                    PlayerRISPSeasonRow(**_clean_row(risp_df.iloc[[i]]))
                    for i in range(len(risp_df))
                ]
        except Exception as e:
            logger.warning(f"risp_stats query failed for mlbid={mlbid}: {e}")
        return None

    # ── Phase 2: 並列実行（打者KPI / 投手KPI / RISP season）────────────────
    with ThreadPoolExecutor(max_workers=3) as executor:
        fut_bat    = executor.submit(_fetch_batting_kpi)
        fut_pit    = executor.submit(_fetch_pitching_kpi)
        fut_risp_s = executor.submit(_fetch_risp_season)

        bat_result  = fut_bat.result()
        pit_result  = fut_pit.result()
        risp_stats  = fut_risp_s.result()

    batting_kpi   = bat_result["kpi"]
    batting_data  = bat_result["data"]
    pitching_kpi  = pit_result["kpi"]
    pitching_data = pit_result["data"]

    # resolved_season 決定
    resolved_season = season or (batting_data.get("season") if batting_data else None)
    if resolved_season is None and pitching_data:
        resolved_season = pitching_data.get("season")

    # ── Phase 3 ヘルパー関数 ──────────────────────────────────────────────────

    def _fetch_monthly():
        if not resolved_season:
            return None
        monthly_params = [
            bigquery.ScalarQueryParameter("mlbid",  "INT64", int(mlbid)),
            bigquery.ScalarQueryParameter("season", "INT64", int(resolved_season)),
        ]
        monthly_job_config = bigquery.QueryJobConfig(query_parameters=monthly_params)
        monthly_query = f"""
            SELECT
                game_month,
                home_runs,
                on_base_percentage,
                slugging_percentage,
                on_base_plus_slugging
            FROM `{PROJECT_ID}.{DATASET_ID}.{BATTING_OFFENSIVE_STATS_TABLE_ID}`
            WHERE batter_id = @mlbid
              AND game_year  = @season
            ORDER BY game_month ASC
        """
        try:
            monthly_df = client.query(monthly_query, job_config=monthly_job_config).to_dataframe()
            if not monthly_df.empty:
                return [
                    PlayerMonthlyRow(**_clean_row(monthly_df.iloc[[i]]))
                    for i in range(len(monthly_df))
                ]
        except Exception as e:
            logger.warning(f"monthly_offensive_stats query failed for mlbid={mlbid}: {e}")
        return None

    def _fetch_risp_monthly():
        if not resolved_season:
            return None
        risp_m_params = [
            bigquery.ScalarQueryParameter("mlbid",  "INT64", int(mlbid)),
            bigquery.ScalarQueryParameter("season", "INT64", int(resolved_season)),
        ]
        risp_m_job_config = bigquery.QueryJobConfig(query_parameters=risp_m_params)
        risp_monthly_query = f"""
            SELECT
                game_month                                                              AS month,
                SUM(singles_at_risp)                                                   AS singles,
                SUM(doubles_at_risp)                                                   AS doubles,
                SUM(triples_at_risp)                                                   AS triples,
                SUM(home_runs_at_risp)                                                 AS home_runs,
                SUM(hits_at_risp)                                                      AS hits,
                SUM(at_bats_at_risp)                                                   AS at_bats,
                SAFE_DIVIDE(SUM(hits_at_risp), SUM(at_bats_at_risp))                  AS batting_average,
                SAFE_DIVIDE(
                    SUM(singles_at_risp)
                    + 2 * SUM(doubles_at_risp)
                    + 3 * SUM(triples_at_risp)
                    + 4 * SUM(home_runs_at_risp),
                    SUM(at_bats_at_risp)
                )                                                                      AS slugging_percentage
            FROM `{PROJECT_ID}.{DATASET_ID}.{BAT_PERFORMANCE_RISP_TABLE_ID}`
            WHERE batter_id = @mlbid
              AND game_year  = @season
            GROUP BY game_month
            ORDER BY game_month ASC
        """
        try:
            risp_m_df = client.query(risp_monthly_query, job_config=risp_m_job_config).to_dataframe()
            if not risp_m_df.empty:
                return [
                    PlayerRISPMonthlyRow(**_clean_row(risp_m_df.iloc[[i]]))
                    for i in range(len(risp_m_df))
                ]
        except Exception as e:
            logger.warning(f"risp_monthly_stats query failed for mlbid={mlbid}: {e}")
        return None

    def _fetch_inning_and_era():
        """inning stats と ERA by inning を並列取得してマージして返す"""
        if not resolved_season:
            return None
        params = [
            bigquery.ScalarQueryParameter("mlbid",  "INT64", int(mlbid)),
            bigquery.ScalarQueryParameter("season", "INT64", int(resolved_season)),
        ]
        inning_query = f"""
            SELECT
                inning,
                SUM(hits_allowed)                                                       AS hits_allowed,
                SUM(home_runs_allowed)                                                  AS home_runs_allowed,
                SUM(free_passes)                                                        AS free_passes,
                SUM(outs_recorded)                                                      AS outs_recorded,
                SAFE_DIVIDE(SUM(obp_numerator), SUM(obp_denominator))                  AS obp_against,
                SAFE_DIVIDE(SUM(slg_numerator), SUM(slg_denominator))                  AS slg_against,
                SAFE_DIVIDE(
                    SUM(obp_numerator) + SUM(slg_numerator),
                    SUM(obp_denominator) + SUM(slg_denominator)
                )                                                                       AS ops_against,
                SAFE_DIVIDE(
                    SUM(hits_allowed),
                    SUM(obp_denominator) - SUM(free_passes)
                )                                                                       AS baa
            FROM `{PROJECT_ID}.{DATASET_ID}.{PITCHING_PERFORMANCE_BY_INNING_TABLE_ID}`
            WHERE pitcher_id = @mlbid
              AND game_year  = @season
            GROUP BY inning
            ORDER BY inning ASC
        """
        era_query = f"""
            SELECT
                inning,
                innings_pitched,
                earned_runs,
                era_by_inning AS era
            FROM `{PROJECT_ID}.{DATASET_ID}.{MART_PITCHER_ERA_BY_INNING_TABLE_ID}`
            WHERE pitcher    = @mlbid
              AND game_year  = @season
            ORDER BY inning ASC
        """
        # inning と ERA を並列取得
        with ThreadPoolExecutor(max_workers=2) as ex:
            fut_inning = ex.submit(
                lambda: client.query(
                    inning_query,
                    job_config=bigquery.QueryJobConfig(query_parameters=params)
                ).to_dataframe()
            )
            fut_era = ex.submit(
                lambda: client.query(
                    era_query,
                    job_config=bigquery.QueryJobConfig(query_parameters=params)
                ).to_dataframe()
            )
            try:
                inning_df = fut_inning.result()
            except Exception as e:
                logger.warning(f"inning_stats query failed for mlbid={mlbid}: {e}")
                return None
            try:
                era_df = fut_era.result()
            except Exception as e:
                logger.warning(f"era_by_inning query failed for mlbid={mlbid}: {e}")
                era_df = None

        if inning_df.empty:
            return None

        inning_stats = [
            PlayerInningRow(**_clean_row(inning_df.iloc[[i]]))
            for i in range(len(inning_df))
        ]

        if era_df is not None and not era_df.empty:
            era_by_inning = {int(r["inning"]): r for _, r in era_df.iterrows()}
            merged = []
            for stat_row in inning_stats:
                row_dict = (
                    stat_row.model_dump()
                    if hasattr(stat_row, "model_dump")
                    else stat_row.dict()
                )
                if stat_row.inning in era_by_inning:
                    er = era_by_inning[stat_row.inning]
                    row_dict["era"] = _nan_to_none(er.get("era"))
                    er_val = _nan_to_none(er.get("earned_runs"))
                    row_dict["earned_runs"] = int(er_val) if er_val is not None else None
                    row_dict["innings_pitched"] = _nan_to_none(er.get("innings_pitched"))
                merged.append(PlayerInningRow(**row_dict))
            return merged

        return inning_stats

    def _fetch_statcast():
        if not (resolved_season and pitching_kpi is not None):
            return None
        sc_params = [
            bigquery.ScalarQueryParameter("mlbid",  "INT64", int(mlbid)),
            bigquery.ScalarQueryParameter("season", "INT64", int(resolved_season)),
        ]
        sc_job_config = bigquery.QueryJobConfig(query_parameters=sc_params)
        sc_query = f"""
            SELECT
                pitch_type,
                pitch_name,
                ROUND(pfx_x,         3) AS pfx_x,
                ROUND(pfx_z,         3) AS pfx_z,
                ROUND(plate_x,       3) AS plate_x,
                ROUND(plate_z,       3) AS plate_z,
                ROUND(release_speed, 1) AS release_speed,
                `type`                  AS result
            FROM `{PROJECT_ID}.{DATASET_ID}.{STATCAST_MASTER_TABLE_ID}`
            WHERE pitcher    = @mlbid
              AND game_year  = @season
              AND pitch_type IS NOT NULL
              AND pfx_x      IS NOT NULL
              AND pfx_z      IS NOT NULL
              AND plate_x    IS NOT NULL
              AND plate_z    IS NOT NULL
            ORDER BY RAND()
            LIMIT 3000
        """
        try:
            sc_df = client.query(sc_query, job_config=sc_job_config).to_dataframe()
            if not sc_df.empty:
                return [
                    StatcastPitchRow(**_clean_row(sc_df.iloc[[i]]))
                    for i in range(len(sc_df))
                ]
        except Exception as e:
            logger.warning(f"statcast_pitches query failed for mlbid={mlbid}: {e}")
        return None

    def _fetch_pitch_performance():
        if not (resolved_season and pitching_kpi is not None):
            return None
        pp_params = [
            bigquery.ScalarQueryParameter("mlbid",  "INT64", int(mlbid)),
            bigquery.ScalarQueryParameter("season", "INT64", int(resolved_season)),
        ]
        pp_job_config = bigquery.QueryJobConfig(query_parameters=pp_params)
        pp_query = f"""
            SELECT
                pitch_type,
                pitch_name,
                pitch_count,
                usage_pct,
                whiff_pct,
                xba,
                avg_speed,
                avg_spin_rate
            FROM `{PROJECT_ID}.{DATASET_ID}.{PITCH_PERFORMANCE_XBA_WHIFF_TABLE_ID}`
            WHERE pitcher   = @mlbid
              AND game_year = @season
            ORDER BY usage_pct DESC
        """
        try:
            pp_df = client.query(pp_query, job_config=pp_job_config).to_dataframe()
            if not pp_df.empty:
                return [
                    PitchPerformanceRow(**_clean_row(pp_df.iloc[[i]]))
                    for i in range(len(pp_df))
                ]
        except Exception as e:
            logger.warning(f"pitch_performance query failed for mlbid={mlbid}: {e}")
        return None

    def _fetch_hit_location():
        if not (resolved_season and batting_kpi is not None):
            return None
        hl_params = [
            bigquery.ScalarQueryParameter("mlbid",  "INT64", int(mlbid)),
            bigquery.ScalarQueryParameter("season", "INT64", int(resolved_season)),
        ]
        hl_job_config = bigquery.QueryJobConfig(query_parameters=hl_params)
        hl_query = f"""
            SELECT
                hit_direction,
                bb_type,
                p_throws,
                stand,
                hit_count,
                avg_exit_velocity,
                avg_xba,
                total_bip,
                type_pct_in_dir,
                pull_pct,
                center_pct,
                oppo_pct
            FROM `{PROJECT_ID}.{DATASET_ID}.{BATTER_HIT_LOC_QUALITY_TABLE_ID}`
            WHERE batter    = @mlbid
              AND game_year = @season
            ORDER BY hit_direction, bb_type, p_throws
        """
        try:
            hl_df = client.query(hl_query, job_config=hl_job_config).to_dataframe()
            if not hl_df.empty:
                return [
                    HitLocationRow(**_clean_row(hl_df.iloc[[i]]))
                    for i in range(len(hl_df))
                ]
        except Exception as e:
            logger.warning(f"hit_location query failed for mlbid={mlbid}: {e}")
        return None

    def _fetch_whiff_heatmap():
        if not (resolved_season and pitching_kpi is not None):
            return None
        wh_params = [
            bigquery.ScalarQueryParameter("mlbid",  "INT64", int(mlbid)),
            bigquery.ScalarQueryParameter("season", "INT64", int(resolved_season)),
        ]
        wh_job_config = bigquery.QueryJobConfig(query_parameters=wh_params)
        wh_query = f"""
            SELECT
                pitch_type,
                pitch_name,
                stand,
                zone_x,
                zone_z,
                total_pitches,
                whiff_count,
                swing_count,
                whiff_pct
            FROM `{PROJECT_ID}.{DATASET_ID}.{PITCH_WHIFF_HEATMAP_TABLE_ID}`
            WHERE pitcher   = @mlbid
              AND game_year = @season
            ORDER BY pitch_type, stand, zone_z DESC, zone_x ASC
        """
        try:
            wh_df = client.query(wh_query, job_config=wh_job_config).to_dataframe()
            if not wh_df.empty:
                return [
                    WhiffHeatmapRow(**_clean_row(wh_df.iloc[[i]]))
                    for i in range(len(wh_df))
                ]
        except Exception as e:
            logger.warning(f"whiff_heatmap query failed for mlbid={mlbid}: {e}")
        return None

    def _fetch_count_state_woba():
        if not (resolved_season and batting_kpi is not None):
            return None
        cs_params = [
            bigquery.ScalarQueryParameter("mlbid",  "INT64", int(mlbid)),
            bigquery.ScalarQueryParameter("season", "INT64", int(resolved_season)),
        ]
        cs_job_config = bigquery.QueryJobConfig(query_parameters=cs_params)
        cs_query = f"""
            SELECT
                balls,
                strikes,
                is_risp,
                pa_count,
                woba,
                xwoba_contact
            FROM `{PROJECT_ID}.{DATASET_ID}.{BATTER_COUNT_STATE_WOBA_TABLE_ID}`
            WHERE batter    = @mlbid
              AND game_year = @season
            ORDER BY is_risp ASC, balls ASC, strikes ASC
        """
        try:
            cs_df = client.query(cs_query, job_config=cs_job_config).to_dataframe()
            if not cs_df.empty:
                return [
                    CountStateWobaRow(**_clean_row(cs_df.iloc[[i]]))
                    for i in range(len(cs_df))
                ]
        except Exception as e:
            logger.warning(f"count_state_woba query failed for mlbid={mlbid}: {e}")
        return None

    def _fetch_xwoba_zone():
        if not (resolved_season and batting_kpi is not None):
            return None
        xz_params = [
            bigquery.ScalarQueryParameter("mlbid",  "INT64", int(mlbid)),
            bigquery.ScalarQueryParameter("season", "INT64", int(resolved_season)),
        ]
        xz_job_config = bigquery.QueryJobConfig(query_parameters=xz_params)
        xz_query = f"""
            SELECT
                p_throws,
                stand,
                zone_x,
                zone_z,
                is_risp,
                pa_count,
                woba,
                xwoba_contact,
                contact_count
            FROM `{PROJECT_ID}.{DATASET_ID}.{BATTER_XWOBA_ZONE_TABLE_ID}`
            WHERE batter    = @mlbid
              AND game_year = @season
            ORDER BY is_risp ASC, p_throws, zone_z DESC, zone_x ASC
        """
        try:
            xz_df = client.query(xz_query, job_config=xz_job_config).to_dataframe()
            if not xz_df.empty:
                return [
                    XwobaZoneRow(**_clean_row(xz_df.iloc[[i]]))
                    for i in range(len(xz_df))
                ]
        except Exception as e:
            logger.warning(f"xwoba_zone query failed for mlbid={mlbid}: {e}")
        return None

    def _fetch_clutch():
        if batting_kpi is None:
            return None
        clutch_params = [bigquery.ScalarQueryParameter("mlbid", "INT64", int(mlbid))]
        clutch_job_config = bigquery.QueryJobConfig(query_parameters=clutch_params)
        clutch_query = f"""
            SELECT
                game_year,
                situation_type,
                pa,
                ab,
                hits,
                homeruns,
                doubles,
                triples,
                singles,
                bb_hbp,
                so,
                avg,
                obp,
                slg,
                ops,
                woba,
                xwoba,
                bb_rate,
                hitting_events,
                avg_exit_velocity,
                avg_bat_speed,
                hard_hit_rate,
                barrels_rate,
                strikeout_rate,
                swinging_strike_rate
            FROM `{PROJECT_ID}.{DATASET_ID}.{MART_BATTER_CLUTCH_TABLE_ID}`
            WHERE batter_id = @mlbid
            ORDER BY game_year ASC, situation_type
        """
        try:
            clutch_df = client.query(clutch_query, job_config=clutch_job_config).to_dataframe()
            if not clutch_df.empty:
                return [
                    BatterClutchRow(**_clean_row(clutch_df.iloc[[i]]))
                    for i in range(len(clutch_df))
                ]
        except Exception as e:
            logger.warning(f"clutch_stats query failed for mlbid={mlbid}: {e}")
        return None

    def _fetch_pitcher_risp():
        if not (resolved_season and pitching_kpi is not None):
            return None
        pr_params = [
            bigquery.ScalarQueryParameter("mlbid",  "INT64", int(mlbid)),
            bigquery.ScalarQueryParameter("season", "INT64", int(resolved_season)),
        ]
        pr_job_config = bigquery.QueryJobConfig(query_parameters=pr_params)
        pr_query = f"""
            SELECT
                situation,
                pa,
                hits,
                home_runs,
                baa,
                xwoba,
                k_pct,
                bb_pct,
                hard_hit_pct
            FROM `{PROJECT_ID}.{DATASET_ID}.{PITCHER_RISP_PERFORMANCE_TABLE_ID}`
            WHERE pitcher = @mlbid
              AND season  = @season
            ORDER BY situation ASC
        """
        try:
            pr_df = client.query(pr_query, job_config=pr_job_config).to_dataframe()
            if not pr_df.empty:
                return [
                    PitcherRispRow(**_clean_row(pr_df.iloc[[i]]))
                    for i in range(len(pr_df))
                ]
        except Exception as e:
            logger.warning(f"pitcher_risp_performance query failed for mlbid={mlbid}: {e}")
        return None

    def _fetch_pitcher_tto():
        if not (resolved_season and pitching_kpi is not None):
            return None
        tto_params = [
            bigquery.ScalarQueryParameter("mlbid",  "INT64", int(mlbid)),
            bigquery.ScalarQueryParameter("season", "INT64", int(resolved_season)),
        ]
        tto_job_config = bigquery.QueryJobConfig(query_parameters=tto_params)
        tto_query = f"""
            SELECT tto, pa, hits, baa, xwoba_against, pitch_count, avg_velo, avg_spin
            FROM `{PROJECT_ID}.{DATASET_ID}.{PITCHER_TTO_VELO_SPIN_TABLE_ID}`
            WHERE pitcher = @mlbid
              AND season  = @season
            ORDER BY tto ASC
        """
        try:
            tto_df = client.query(tto_query, job_config=tto_job_config).to_dataframe()
            if not tto_df.empty:
                return [
                    PitcherTtoRow(**_clean_row(tto_df.iloc[[i]]))
                    for i in range(len(tto_df))
                ]
        except Exception as e:
            logger.warning(f"pitcher_tto query failed for mlbid={mlbid}: {e}")
        return None

    # ── Phase 3: 並列実行（残り全クエリ）────────────────────────────────────
    phase3_funcs = {
        "monthly":           _fetch_monthly,
        "risp_monthly":      _fetch_risp_monthly,
        "inning":            _fetch_inning_and_era,
        "statcast":          _fetch_statcast,
        "pitch_performance": _fetch_pitch_performance,
        "hit_location":      _fetch_hit_location,
        "whiff_heatmap":     _fetch_whiff_heatmap,
        "count_state_woba":  _fetch_count_state_woba,
        "xwoba_zone":        _fetch_xwoba_zone,
        "clutch":            _fetch_clutch,
        "pitcher_risp":      _fetch_pitcher_risp,
        "pitcher_tto":       _fetch_pitcher_tto,
    }

    phase3_results: dict = {}
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures_map = {executor.submit(fn): key for key, fn in phase3_funcs.items()}
        for future in as_completed(futures_map):
            key = futures_map[future]
            try:
                phase3_results[key] = future.result()
            except Exception as e:
                logger.warning(f"Phase3 '{key}' failed: {e}")
                phase3_results[key] = None

    return PlayerProfileResponse(
        idfg=idfg,
        mlbid=mlbid,
        bio=bio,
        batting_kpi=batting_kpi,
        pitching_kpi=pitching_kpi,
        monthly_offensive_stats=phase3_results.get("monthly"),
        risp_stats=risp_stats,
        risp_monthly_stats=phase3_results.get("risp_monthly"),
        inning_stats=phase3_results.get("inning"),
        statcast_pitches=phase3_results.get("statcast"),
        pitch_performance=phase3_results.get("pitch_performance"),
        hit_location=phase3_results.get("hit_location"),
        whiff_heatmap=phase3_results.get("whiff_heatmap"),
        count_state_woba=phase3_results.get("count_state_woba"),
        xwoba_zone=phase3_results.get("xwoba_zone"),
        clutch_stats=phase3_results.get("clutch"),
        pitcher_risp_performance=phase3_results.get("pitcher_risp"),
        pitcher_tto=phase3_results.get("pitcher_tto"),
    )
