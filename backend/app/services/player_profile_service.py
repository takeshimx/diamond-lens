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
    PITCHING_STATS_MASTER_TABLE_ID,
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


def get_player_profile(idfg: int, season: Optional[int] = None) -> Optional[PlayerProfileResponse]:
    """
    idfg（FanGraphs ID）を受け取り、選手プロフィール情報を返す。
    season を指定した場合はそのシーズンのデータを、省略時は最新シーズンを返す。
    Bio: dim_players_master LEFT JOIN dim_teams
    打者KPI: fact_batting_stats_with_risp
    投手KPI: fact_pitching_stats_master
    """
    client = get_bq_client()

    # Bio クエリ（シーズン非依存）
    bio_params = [bigquery.ScalarQueryParameter("idfg", "INT64", idfg)]
    bio_job_config = bigquery.QueryJobConfig(query_parameters=bio_params)

    # ------------------------------------------------------------------
    # 1. Bio
    # ------------------------------------------------------------------
    bio_query = f"""
        SELECT
            p.mlbid,
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
        WHERE p.idfg = @idfg
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

    # ------------------------------------------------------------------
    # 3. 投手KPI（RANK付き）
    # IP閾値: 2025以前=100, 2026=6
    # ------------------------------------------------------------------
    _PIT_TABLE = f"`{PROJECT_ID}.{DATASET_ID}.{PITCHING_STATS_MASTER_TABLE_ID}`"

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
        bio_df      = client.query(bio_query,      job_config=bio_job_config).to_dataframe()
        batting_df  = client.query(batting_query,  job_config=batting_job_config).to_dataframe()
        pitching_df = client.query(pitching_query, job_config=pitching_job_config).to_dataframe()
    except Exception as e:
        logger.error(f"player_profile BQ query failed for idfg={idfg}: {e}", exc_info=True)
        return None

    if bio_df.empty:
        logger.warning(f"No player found for idfg={idfg}")
        return None

    # Bio
    bio_data = _clean_row(bio_df)
    mlbid = bio_data.pop("mlbid", None)
    bio = PlayerBio(**bio_data)

    # 打者KPI
    batting_data = _clean_row(batting_df)
    batting_kpi = PlayerBattingKPI(**batting_data) if batting_data else None

    # 投手KPI
    pitching_data = _clean_row(pitching_df)
    pitching_kpi = PlayerPitchingKPI(**pitching_data) if pitching_data else None

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

    return PlayerProfileResponse(
        idfg=idfg,
        mlbid=mlbid,
        bio=bio,
        batting_kpi=batting_kpi,
        pitching_kpi=pitching_kpi,
        monthly_offensive_stats=monthly_offensive_stats,
        risp_stats=risp_stats,
        risp_monthly_stats=risp_monthly_stats,
    )
