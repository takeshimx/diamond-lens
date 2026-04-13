"""
選手プロフィールページ用データ取得サービス
Bio情報（dim_players_master + dim_teams）と
現シーズンKPI（fact_batting_stats_with_risp / fact_pitching_stats_master）を返す
"""
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
    PITCHER_RISP_PERFORMANCE_TABLE_ID,
    PITCHER_TTO_VELO_SPIN_TABLE_ID,
)


def _clean_row(df) -> dict:
    """DataFrameの先頭行をdictに変換し、NaN/NaT を None に置換する"""
    if df.empty:
        return {}
    row = df.iloc[0].to_dict()
    return {
        k: (None if (isinstance(v, float) and np.isnan(v)) else v)
        for k, v in row.items()
    }


def get_player_profile(mlbid: int, season: Optional[int] = None) -> Optional[PlayerProfileResponse]:
    """
    mlbid（MLB ID）を受け取り、選手プロフィール情報を返す。
    season を指定した場合はそのシーズンのデータを、省略時は最新シーズンを返す。
    Bio: dim_players_master LEFT JOIN dim_teams
    打者KPI: fact_batting_stats_with_risp
    投手KPI: fact_pitching_stats (idfg経由でJOIN)
    """
    client = get_bq_client()

    # Bio クエリ（シーズン非依存）
    bio_params = [bigquery.ScalarQueryParameter("mlbid", "INT64", mlbid)]
    bio_job_config = bigquery.QueryJobConfig(query_parameters=bio_params)

    # ------------------------------------------------------------------
    # 1. Bio
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # 2. 打者KPI（RANK付き）
    # PA閾値: 2025以前=350, 2026=30
    # ------------------------------------------------------------------
    _BAT_TABLE = f"`{PROJECT_ID}.{DATASET_ID}.{BATTING_STATS_TABLE_ID}`"

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

    # ------------------------------------------------------------------
    # bio を先に実行して idfg を取得（batting/pitching は idfg で検索）
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # 2. 打者KPI（idfg 使用）
    # PA閾値: 2025以前=350, 2026=30
    # ------------------------------------------------------------------
    batting_kpi = None
    batting_data: dict = {}
    if idfg and idfg > 0:
        if season:
            min_pa = 350 if season <= 2025 else 30
            batting_params = [
                bigquery.ScalarQueryParameter("idfg",   "INT64", idfg),
                bigquery.ScalarQueryParameter("season", "INT64", season),
                bigquery.ScalarQueryParameter("min_pa", "INT64", min_pa),
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
                    WHERE b.season = l.s
                      AND b.pa >= CASE WHEN l.s <= 2025 THEN 350 ELSE 30 END
                )
                SELECT * FROM ranked WHERE idfg = @idfg LIMIT 1
            """
        batting_job_config = bigquery.QueryJobConfig(query_parameters=batting_params)
        try:
            batting_df = client.query(batting_query, job_config=batting_job_config).to_dataframe()
            batting_data = _clean_row(batting_df)
            batting_kpi = PlayerBattingKPI(**batting_data) if batting_data else None
        except Exception as e:
            logger.warning(f"batting_kpi query failed for idfg={idfg}: {e}")

    # ------------------------------------------------------------------
    # 3. 投手KPI（fact_pitching_stats / idfg 使用）
    # IP閾値: 2025以前=100, 2026=6
    # ------------------------------------------------------------------
    _PIT_TABLE = f"`{PROJECT_ID}.{DATASET_ID}.{PITCHING_STATS_TABLE_ID}`"

    def _pit_rank_cols(p: str = "") -> str:
        return f"""
            RANK() OVER (ORDER BY {p}era        ASC)  AS era_rank,
            RANK() OVER (ORDER BY {p}whip       ASC)  AS whip_rank,
            RANK() OVER (ORDER BY {p}fip        ASC)  AS fip_rank,
            RANK() OVER (ORDER BY {p}k_9        DESC) AS k_9_rank,
            RANK() OVER (ORDER BY {p}bb_9       ASC)  AS bb_9_rank,
            RANK() OVER (ORDER BY {p}war        DESC) AS war_rank,
            RANK() OVER (ORDER BY {p}so         DESC) AS so_rank,
            RANK() OVER (ORDER BY {p}hardhitpct ASC)  AS hardhitpct_rank,
            RANK() OVER (ORDER BY {p}barrelpct  ASC)  AS barrelpct_rank,
            RANK() OVER (ORDER BY {p}swstrpct   DESC) AS swstrpct_rank
        """

    pitching_kpi = None
    pitching_data: dict = {}
    if idfg and idfg > 0:
        if season:
            min_ip = 100.0 if season <= 2025 else 6.0
            pitching_params = [
                bigquery.ScalarQueryParameter("idfg",   "INT64",   idfg),
                bigquery.ScalarQueryParameter("season", "INT64",   season),
                bigquery.ScalarQueryParameter("min_ip", "FLOAT64", min_ip),
            ]
            pitching_query = f"""
                WITH ranked AS (
                    SELECT
                        idfg, season, team, g, gs, w, l, sv, ip,
                        era, whip, so, bb, fip, war,
                        k_9, bb_9, hardhitpct, barrelpct, swstrpct,
                        {_pit_rank_cols()}
                    FROM {_PIT_TABLE}
                    WHERE season = @season AND ip >= @min_ip
                )
                SELECT * FROM ranked WHERE idfg = @idfg LIMIT 1
            """
        else:
            pitching_params = [bigquery.ScalarQueryParameter("idfg", "INT64", idfg)]
            pitching_query = f"""
                WITH latest AS (
                    SELECT MAX(season) AS s FROM {_PIT_TABLE} WHERE idfg = @idfg
                ),
                ranked AS (
                    SELECT
                        p.idfg, p.season, p.team, p.g, p.gs, p.w, p.l, p.sv, p.ip,
                        p.era, p.whip, p.so, p.bb, p.fip, p.war,
                        p.k_9, p.bb_9, p.hardhitpct, p.barrelpct, p.swstrpct,
                        {_pit_rank_cols("p.")}
                    FROM {_PIT_TABLE} p
                    CROSS JOIN latest l
                    WHERE p.season = l.s
                      AND p.ip >= CASE WHEN l.s <= 2025 THEN 100 ELSE 6 END
                )
                SELECT * FROM ranked WHERE idfg = @idfg LIMIT 1
            """
        pitching_job_config = bigquery.QueryJobConfig(query_parameters=pitching_params)
        try:
            pitching_df = client.query(pitching_query, job_config=pitching_job_config).to_dataframe()
            pitching_data = _clean_row(pitching_df)
            pitching_kpi = PlayerPitchingKPI(**pitching_data) if pitching_data else None
        except Exception as e:
            logger.warning(f"pitching_kpi query failed for idfg={idfg}: {e}")

    # ------------------------------------------------------------------
    # 4. 月別打撃成績
    # ------------------------------------------------------------------
    monthly_offensive_stats = None
    if mlbid:
        resolved_season = season or (batting_data.get("season") if batting_data else None)
        if resolved_season is None and pitching_data:
            resolved_season = pitching_data.get("season")

        if resolved_season:
            monthly_params = [
                bigquery.ScalarQueryParameter("mlbid", "INT64", int(mlbid)),
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
                    monthly_offensive_stats = [
                        PlayerMonthlyRow(**_clean_row(monthly_df.iloc[[i]]))
                        for i in range(len(monthly_df))
                    ]
            except Exception as e:
                logger.warning(f"monthly_offensive_stats query failed for mlbid={mlbid}: {e}")

    # ------------------------------------------------------------------
    # 5. RISP シーズン別集計（2021〜）
    # ------------------------------------------------------------------
    risp_stats = None
    if mlbid:
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
                risp_stats = [
                    PlayerRISPSeasonRow(**_clean_row(risp_df.iloc[[i]]))
                    for i in range(len(risp_df))
                ]
        except Exception as e:
            logger.warning(f"risp_stats query failed for mlbid={mlbid}: {e}")

    # ------------------------------------------------------------------
    # 6. RISP 月別（Single Season 表示用）
    # ------------------------------------------------------------------
    risp_monthly_stats = None
    if mlbid:
        resolved_season = season or (batting_data.get("season") if batting_data else None)
        if resolved_season is None and pitching_data:
            resolved_season = pitching_data.get("season")

        if resolved_season:
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
                    risp_monthly_stats = [
                        PlayerRISPMonthlyRow(**_clean_row(risp_m_df.iloc[[i]]))
                        for i in range(len(risp_m_df))
                    ]
            except Exception as e:
                logger.warning(f"risp_monthly_stats query failed for mlbid={mlbid}: {e}")

    # ------------------------------------------------------------------
    # 7. イニング別投球成績（pitcher_id = mlbid + resolved_season）
    # ------------------------------------------------------------------
    inning_stats = None
    if mlbid:
        resolved_season = season or (pitching_data.get("season") if pitching_data else None)
        if resolved_season is None and batting_data:
            resolved_season = batting_data.get("season")

        if resolved_season:
            inning_params = [
                bigquery.ScalarQueryParameter("mlbid",  "INT64", int(mlbid)),
                bigquery.ScalarQueryParameter("season", "INT64", int(resolved_season)),
            ]
            inning_job_config = bigquery.QueryJobConfig(query_parameters=inning_params)
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
            try:
                inning_df = client.query(inning_query, job_config=inning_job_config).to_dataframe()
                if not inning_df.empty:
                    inning_stats = [
                        PlayerInningRow(**_clean_row(inning_df.iloc[[i]]))
                        for i in range(len(inning_df))
                    ]
            except Exception as e:
                logger.warning(f"inning_stats query failed for mlbid={mlbid}: {e}")

    # ── Query 8: Statcast pitches (投手のみ) ──────────────────────────────────
    statcast_pitches = None
    if mlbid and resolved_season and pitching_kpi is not None:
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
                statcast_pitches = [
                    StatcastPitchRow(**_clean_row(sc_df.iloc[[i]]))
                    for i in range(len(sc_df))
                ]
        except Exception as e:
            logger.warning(f"statcast_pitches query failed for mlbid={mlbid}: {e}")

    # ── Query 9: Pitch Performance xBA & Whiff% (投手のみ) ───────────────────
    pitch_performance = None
    if mlbid and resolved_season and pitching_kpi is not None:
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
                pitch_performance = [
                    PitchPerformanceRow(**_clean_row(pp_df.iloc[[i]]))
                    for i in range(len(pp_df))
                ]
        except Exception as e:
            logger.warning(f"pitch_performance query failed for mlbid={mlbid}: {e}")

    # ── Query 10: Hit Location & Type Distribution (打者のみ) ────────────────
    hit_location = None
    if mlbid and resolved_season and batting_kpi is not None:
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
                hit_location = [
                    HitLocationRow(**_clean_row(hl_df.iloc[[i]]))
                    for i in range(len(hl_df))
                ]
        except Exception as e:
            logger.warning(f"hit_location query failed for mlbid={mlbid}: {e}")

    # ── Query 11: Whiff Zone Heatmap (投手のみ) ──────────────────────────────
    whiff_heatmap = None
    if mlbid and resolved_season and pitching_kpi is not None:
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
                whiff_heatmap = [
                    WhiffHeatmapRow(**_clean_row(wh_df.iloc[[i]]))
                    for i in range(len(wh_df))
                ]
        except Exception as e:
            logger.warning(f"whiff_heatmap query failed for mlbid={mlbid}: {e}")

    # ── Query 12: Count State wOBA Matrix（打者のみ） ────────────────────────
    count_state_woba = None
    if mlbid and resolved_season and batting_kpi is not None:
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
                count_state_woba = [
                    CountStateWobaRow(**_clean_row(cs_df.iloc[[i]]))
                    for i in range(len(cs_df))
                ]
        except Exception as e:
            logger.warning(f"count_state_woba query failed for mlbid={mlbid}: {e}")

    # ── Query 13: xwOBA Zone Heatmap（打者のみ） ─────────────────────────────
    xwoba_zone = None
    if mlbid and resolved_season and batting_kpi is not None:
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
                xwoba_zone = [
                    XwobaZoneRow(**_clean_row(xz_df.iloc[[i]]))
                    for i in range(len(xz_df))
                ]
        except Exception as e:
            logger.warning(f"xwoba_zone query failed for mlbid={mlbid}: {e}")

    # ── Query 14: Clutch Stats（打者のみ、全シーズン） ────────────────────────
    clutch_stats = None
    if mlbid and batting_kpi is not None:
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
                clutch_stats = [
                    BatterClutchRow(**_clean_row(clutch_df.iloc[[i]]))
                    for i in range(len(clutch_df))
                ]
        except Exception as e:
            logger.warning(f"clutch_stats query failed for mlbid={mlbid}: {e}")

    # ── Query 15: Pitcher RISP Performance（投手のみ） ────────────────────────
    pitcher_risp_performance = None
    if mlbid and resolved_season and pitching_kpi is not None:
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
                pitcher_risp_performance = [
                    PitcherRispRow(**_clean_row(pr_df.iloc[[i]]))
                    for i in range(len(pr_df))
                ]
        except Exception as e:
            logger.warning(f"pitcher_risp_performance query failed for mlbid={mlbid}: {e}")

    # ── Query 16: Pitcher TTO Velo & Spin（投手のみ） ────────────────────────
    pitcher_tto = None
    if mlbid and resolved_season and pitching_kpi is not None:
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
                pitcher_tto = [
                    PitcherTtoRow(**_clean_row(tto_df.iloc[[i]]))
                    for i in range(len(tto_df))
                ]
        except Exception as e:
            logger.warning(f"pitcher_tto query failed for mlbid={mlbid}: {e}")

    return PlayerProfileResponse(
        idfg=idfg,
        mlbid=mlbid,
        bio=bio,
        batting_kpi=batting_kpi,
        pitching_kpi=pitching_kpi,
        monthly_offensive_stats=monthly_offensive_stats,
        risp_stats=risp_stats,
        risp_monthly_stats=risp_monthly_stats,
        inning_stats=inning_stats,
        statcast_pitches=statcast_pitches,
        pitch_performance=pitch_performance,
        hit_location=hit_location,
        whiff_heatmap=whiff_heatmap,
        count_state_woba=count_state_woba,
        xwoba_zone=xwoba_zone,
        clutch_stats=clutch_stats,
        pitcher_risp_performance=pitcher_risp_performance,
        pitcher_tto=pitcher_tto,
    )
