"""
Stats Service for MLB Analytics Dashboard
This service provides various statistics related to MLB players and teams.
"""
from typing import Optional, List, Dict, Any
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError
import pandas as pd
import numpy as np
from functools import lru_cache
from backend.app.api.schemas import (
    PlayerMonthlyOffensiveStats,
    PlayerBatterPerformanceAtRISPMonthly,
    PlayerMonthlyBattingStats,
    PlayerBattingSeasonStats
)
from .base import (
    get_bq_client, client, logger,
    PROJECT_ID, DATASET_ID,
    BATTING_STATS_TABLE_ID,
    BATTING_OFFENSIVE_STATS_TABLE_ID,
    BAT_PERFORMANCE_SC_TABLE_ID,
    BAT_PERFORMANCE_RISP_TABLE_ID,
    BATTER_PERFORMANCE_FLAGS_7DAYS_TABLE_ID,
    BATTER_PERFORMANCE_FLAGS_15DAYS_TABLE_ID,
    PITCHING_PERFORMANCE_BY_INNING_TABLE_ID,
)


@lru_cache(maxsize=128)
def get_season_batting_stats(
    player_id: int,
    season: int,
    metrics: List[str]
) -> Optional[List[PlayerBattingSeasonStats]]:
    """
    指定された選手、シーズン、打撃シーズン統計を取得します。
    """

    selected_metrics = f"{', '.join(metrics)}" if metrics else "*"

    query = f"""
        SELECT
            mlbid,
            season,
            name,
            team,
            league,
            g,
            ab,
            pa,
            {selected_metrics}
        FROM
            `{PROJECT_ID}.{DATASET_ID}.{BATTING_STATS_TABLE_ID}`
        WHERE
            mlbid = @player_id
            AND season = @season
        ORDER BY
            season ASC
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("player_id", "INT64", player_id),
            bigquery.ScalarQueryParameter("season", "INT64", season)
        ]
    )

    # ★★★ デバッグログの追加 ★★★
    logger.debug(f"Executing BigQuery query for season batting stats:")
    logger.debug(f"Query: {query}")
    logger.debug(f"Parameters: {job_config.query_parameters}")
    # ★★★ デバッグログの追加ここまで ★★★

    try:
        df = client.query(query, job_config=job_config).to_dataframe()

        # ★★★ デバッグログの追加: データフレームの内容を確認 ★★★
        logger.debug(f"DataFrame fetched. Shape: {df.shape}")
        if not df.empty:
            logger.debug(f"DataFrame head:\n{df.head().to_string()}")
        # ★★★ デバッグログの追加ここまで ★★★

        if df.empty:
            print(f"DEBUG: No batting leaderboard data found for player {player_id}, season {season}")
            return []
        
        results: List[PlayerBattingSeasonStats] = [] # PlayerBattingSeasonStatsのリストとして初期化
        for _, row in df.iterrows():
            results.append(PlayerBattingSeasonStats(**row.to_dict()))
        return results

    except GoogleCloudError as e:
        print(f"ERROR: BigQuery query for batting leaderboard failed for player {player_id}, season {season}: {e}")
        return None
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while fetching batting leaderboard for player {player_id}, season {season}: {e}")
        return None


# function to get batter monthly offensive stats
@lru_cache(maxsize=128)
def get_monthly_batting_stats(
    player_id: int,
    season: int, 
    month: Optional[int],
    metric: Optional[str] = None
) -> Optional[List[PlayerMonthlyBattingStats]]:
    """
    指定された選手名とシーズンに基づいて、選手の月別打撃成績を取得します。
    """
    available_metrics = ["hits", "homeruns", "doubles", "triples", "singles", "rbi", 
                         "bb_hbp", "ab", "avg", "obp", "slg", "ops", "hard_hit_rate", "barrels_rate", "strikeout_rate"]
    if not metric or metric not in available_metrics:
        logger.warning(f"Invalid or no metric provided: {metric}.")
        return []

    query = f"""
        SELECT
            game_year,
            game_month,
            batter_name,
            batter_id,
            {metric}
        FROM
            `{PROJECT_ID}.{DATASET_ID}.tbl_batting_stats_monthly`
        WHERE
            batter_id = @player_id
            AND game_year = @season
        ORDER BY
            game_year ASC, game_month ASC
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("player_id", "INT64", player_id),
            bigquery.ScalarQueryParameter("season", "INT64", season),
        ]
    )

    # Debugging
    logger.debug(f"Executing BigQuery query for batter monthly batting stats: {query}")

    try:
        df = client.query(query, job_config=job_config).to_dataframe()

        # Debugging
        logger.debug(f"Batter Monthly Batting Stats DataFrame fetched. Shape: {df.shape} First row: {df.iloc[0] if not df.empty else 'N/A'}")

        if df.empty:
            logger.debug(f"No monthly offensive stats found for player {player_id} in season {season}")
            return []

        results: List[PlayerMonthlyBattingStats] = []  # PlayerMonthlyOffensiveStatsのリストとして初期化
        for _, row in df.iterrows():
            stat_data = {
                "game_year": row['game_year'],
                "game_month": row['game_month'],
                "batter_name": row['batter_name'],
                "batter_id": row['batter_id']
            }
            # Add metric value
            stat_data[metric] = row[metric]

            # Generate Pydantic model
            results.append(PlayerMonthlyBattingStats(**stat_data))

        return results
    except GoogleCloudError as e:
        print(f"ERROR: BigQuery query for batter monthly batting stats failed for player {player_id} in season {season}: {e}")
        return None


# NOTE: This will be deprecated
# function to get batter monthly offensive stats
@lru_cache(maxsize=128)
def get_batter_monthly_offensive_stats(
    player_id: int,
    season: int, 
    month: Optional[int],
    metric: Optional[str] = None
) -> Optional[List[PlayerMonthlyOffensiveStats]]:
    """
    指定された選手名とシーズンに基づいて、選手の月別打撃成績を取得します。
    """
    available_metrics = ["hits", "home_runs", "doubles", "triples", "singles", "walks_and_hbp", "at_bats", "batting_average", "on_base_percentage", "slugging_percentage", "on_base_plus_slugging"]
    if not metric or metric not in available_metrics:
        logger.warning(f"Invalid or no metric provided: {metric}.")
        return []
    # selected_metric = metric if metric in available_metrics else None


    query = f"""
        SELECT
            game_year,
            game_month,
            batter_name,
            batter_id,
            {metric}
        FROM
            `{PROJECT_ID}.{DATASET_ID}.{BATTING_OFFENSIVE_STATS_TABLE_ID}`
        WHERE
            batter_id = @player_id
            AND game_year = @season
        ORDER BY
            game_year ASC, game_month ASC
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("player_id", "INT64", player_id),
            bigquery.ScalarQueryParameter("season", "INT64", season),
        ]
    )

    try:
        df = client.query(query, job_config=job_config).to_dataframe()
        if df.empty:
            print(f"DEBUG: No monthly offensive stats found for player {player_id} in season {season}")
            return []

        results: List[PlayerMonthlyOffensiveStats] = []  # PlayerMonthlyOffensiveStatsのリストとして初期化
        for _, row in df.iterrows():
            stat_data = {
                "game_year": row['game_year'],
                "game_month": row['game_month'],
                "batter_name": row['batter_name'],
                "batter_id": row['batter_id']
            }
            # Add metric value
            stat_data[metric] = row[metric]

            # Generate Pydantic model
            results.append(PlayerMonthlyOffensiveStats(**stat_data))

        return results
    except GoogleCloudError as e:
        print(f"ERROR: BigQuery query for batter monthly offensive stats failed for player {player_id} in season {season}: {e}")
        return None


# # Function to get batter performance by strike count
# @lru_cache(maxsize=128)
# def get_batter_performance_by_strike_count(player_id: int, season: int) -> Optional[List[PlayerBatterPerformanceByStrikeCount]]:
#     """
#     指定された選手名とシーズンに基づいて、選手の打者のストライクカウント別パフォーマンスを取得します。
#     """

#     season_where_clause = ""
#     if season is not None:
#         season_where_clause = "AND game_year = @season"
    
#     query = f"""
#         SELECT
#             game_year,
#             batter_name,
#             batter_id,
#             strike_count,
#             total_hits,
#             total_at_bats,
#             total_plate_appearances_for_obp,
#             batting_average_at_strike_count,
#             on_base_percentage_at_strike_count,
#             slugging_percentage_at_strike_count,
#             total_bases_for_slugging,
#             total_home_runs,
#             total_singles,
#             total_doubles,
#             total_triples,
#             total_extra_base_hits
#         FROM
#             `{PROJECT_ID}.{DATASET_ID}.{BAT_PERFORMANCE_SC_TABLE_ID}`
#         WHERE
#             batter_id = @player_id
#             {season_where_clause}
#         ORDER BY
#             game_year ASC, strike_count ASC
#     """
#     job_config = bigquery.QueryJobConfig(
#         query_parameters=[
#             bigquery.ScalarQueryParameter("player_id", "INT64", player_id),
#             *([] if season is None else [bigquery.ScalarQueryParameter("season", "INT64", season)])
#         ]
#     )

#     # # ★★★ デバッグログの追加 ★★★
#     # logger.debug(f"Executing BigQuery query for strike count performance:")
#     # logger.debug(f"Query: {query}")
#     # logger.debug(f"Parameters: {job_config.query_parameters}")
#     # # ★★★ ここまで ★★★

#     try:
#         df = client.query(query, job_config=job_config).to_dataframe()

#         # # ★★★ デバッグログの追加: データフレームの内容を確認 ★★★
#         # logger.debug(f"Strike Count DataFrame fetched. Shape: {df.shape}")
#         # if not df.empty:
#         #     logger.debug(f"Strike Count DataFrame head:\n{df.head().to_string()}")
#         # # ★★★ ここまで ★★★

#         if df.empty:
#             print(f"DEBUG: No batter performance by strike count found for batter {player_id} in season {season}")
#             return []
        
#         results: List[PlayerBatterPerformanceByStrikeCount] = []  # PlayerBatterPerformanceByStrikeCountのリストとして初期化
#         for _, row in df.iterrows():
#             results.append(PlayerBatterPerformanceByStrikeCount(
#                 game_year=row['game_year'],
#                 batter_name=row['batter_name'],
#                 batter_id=row['batter_id'],
#                 strike_count=row['strike_count'],
#                 total_hits=row['total_hits'],
#                 total_at_bats=row['total_at_bats'],
#                 total_plate_appearances_for_obp=row['total_plate_appearances_for_obp'],
#                 batting_average_at_strike_count=row['batting_average_at_strike_count'],
#                 on_base_percentage_at_strike_count=row['on_base_percentage_at_strike_count'],
#                 slugging_percentage_at_strike_count=row['slugging_percentage_at_strike_count'],
#                 total_bases_for_slugging=row['total_bases_for_slugging'],
#                 total_home_runs=row['total_home_runs'],
#                 total_singles=row['total_singles'],
#                 total_doubles=row['total_doubles'],
#                 total_triples=row['total_triples'],
#                 total_extra_base_hits=row['total_extra_base_hits']
#             ))
#         return results
#     except GoogleCloudError as e:
#         print(f"ERROR: BigQuery query for batter performance by strike count failed for batter {player_id} in season {season}: {e}")
#         return None


# Function to get batter performance at RISP
@lru_cache(maxsize=128)
def get_batter_performance_at_risp(
    player_id: int, 
    season: int,
    metric: Optional[str] = None
) -> Optional[PlayerBatterPerformanceAtRISPMonthly]:
    """
    指定された選手IDとシーズンに基づいて、選手のRISP（得点圏）でのパフォーマンスを取得します。
    """
    available_metrics = ["hits_at_risp", "home_runs_at_risp", "doubles_at_risp", "triples_at_risp", "singles_at_risp", "at_bats_at_risp", "batting_average_at_risp", "slugging_percentage_at_risp"]

    if metric and metric not in available_metrics:
        print(f"DEBUG: Invalid metric '{metric}' specified for batter performance at RISP.")
        return []

    season_where_clause = ""
    if season is not None:
        season_where_clause = "AND game_year = @season"
    
    query = f"""
        SELECT
            game_year,
            game_month,
            batter_name,
            batter_id,
            {metric}
        FROM
            `{PROJECT_ID}.{DATASET_ID}.{BAT_PERFORMANCE_RISP_TABLE_ID}`
        WHERE
            batter_id = @player_id
            {season_where_clause}
        ORDER BY
            game_year ASC, game_month ASC
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("player_id", "INT64", player_id),
            *([] if season is None else [bigquery.ScalarQueryParameter("season", "INT64", season)])
        ]
    )

    # # ★★★ デバッグログの追加 ★★★
    # logger.debug(f"Executing BigQuery query for RISP performance:")
    # logger.debug(f"Query: {query}")
    # logger.debug(f"Parameters: {job_config.query_parameters}")
    # # ★★★ デバッグログの追加ここまで ★★★

    try:
        df = client.query(query, job_config=job_config).to_dataframe()

        # # ★★★ デバッグログの追加: データフレームの内容を確認 ★★★
        # logger.debug(f"RISP DataFrame fetched. Shape: {df.shape}")
        # if not df.empty:
        #     logger.debug(f"RISP DataFrame head:\n{df.head().to_string()}")
        # # ★★★ デバッグログの追加ここまで ★★★

        if df.empty:
            print(f"DEBUG: No batter performance at RISP found for player ID {player_id} in season {season}")
            return None
        
        results: List[PlayerBatterPerformanceAtRISPMonthly] = []  # PlayerBatterPerformanceAtRISPMonthlyのリストとして初期化
        for _, row in df.iterrows():
            stat_data = {
                "game_year": row['game_year'],
                "game_month": row['game_month'],
                "batter_name": row['batter_name'],
                "batter_id": row['batter_id']
            }

            stat_data[metric] = row[metric]

            results.append(PlayerBatterPerformanceAtRISPMonthly(**stat_data))

        return results
    except GoogleCloudError as e:
        print(f"ERROR: BigQuery query for batter performance at RISP failed for player ID {player_id} in season {season}: {e}")
        return None


# # Function to get batter performance flags by comparing rolling and season stats
# @lru_cache(maxsize=128)
# def get_batter_performance_flags(query_date: str, days: int) -> Optional[List[PlayerBatterPerformanceFlags]]:
#     """
#     指定された日付と日数に基づいて、打者のパフォーマンスフラグを取得します。
#     """

#     if days == 7:
#         table_id = BATTER_PERFORMANCE_FLAGS_7DAYS_TABLE_ID
#     elif days == 15:
#         table_id = BATTER_PERFORMANCE_FLAGS_15DAYS_TABLE_ID
    

#     query = f"""
#         SELECT  
#             game_date,
#             batter_name,
#             batter_id,
#             team,
#             age,
#             hrs_{days}days,
#             abs_per_hr_{days}days,
#             is_red_hot_hr_{days}days,
#             is_slump_hr_{days}days,
#             ba_{days}days,
#             is_red_hot_ba_{days}days,
#             is_slump_ba_{days}days,
#             ops_{days}days,
#             is_red_hot_ops_{days}days,
#             is_slump_ops_{days}days,
#             barrels_percentage_{days}days,
#             is_red_hot_barrels_{days}days,
#             is_slump_barrels_{days}days,
#             hard_hit_percentage_{days}days,
#             is_red_hot_hard_hit_{days}days,
#             is_slump_hard_hit_{days}days
#         FROM
#             `{PROJECT_ID}.{DATASET_ID}.{table_id}`
#         WHERE
#             game_date = @query_date
#         ORDER BY
#             game_date ASC
#     """


#     job_config = bigquery.QueryJobConfig(
#         query_parameters=[
#             bigquery.ScalarQueryParameter("query_date", "DATE", query_date)
#         ]
#     )

#     # Debugging: log the query and parameters
#     logger.debug(f"Executing BigQuery query for batter performance flags for {days} days.")
#     logger.debug(f"Query: {query}")
#     logger.debug(f"Parameters: {job_config.query_parameters}")


#     try:
#         df = client.query(query, job_config=job_config).to_dataframe()

#         # Debugging: log the DataFrame shape and columns
#         logger.debug(f"DEBUG: Fetched batter performance flags DataFrame shape: {df.shape}, columns: {df.columns.tolist()}")
#         logger.debug(f"DEBUG: First few rows of the DataFrame:\n{df.head()}")

#         # Convert NaN to None
#         if not df.empty:
#             for col in df.columns:  # 全カラムに対してNaNをNoneに変換
#                 if df[col].dtype == 'object':
#                     df[col] = df[col].replace({pd.NA: None, float('nan'): None})
#                 elif pd.api.types.is_numeric_dtype(df[col]):
#                     df[col] = df[col].replace({float('nan'): None})

#         # Debugging: Make sure Nans are handled correctly
#         logger.debug(f"DEBUG: After converting NaN to None, DataFrame shape: {df.shape}, columns: {df.columns.tolist()}")
#         logger.debug(f"DEBUG: First few rows after NaN conversion:\n{df.head()}")

#         if df.empty:
#             logger.debug(f"DEBUG: No batter performance flags found")
#             return []
        
#         results: List[PlayerBatterPerformanceFlags] = []  # PlayerBatterPerformanceFlagsのリストとして初期化
#         for _, row in df.iterrows():
#             player_data = {
#                 "game_date": row['game_date'],
#                 "batter_name": row['batter_name'],
#                 "batter_id": row['batter_id'],
#                 "team": row['team'],
#                 "age": row['age']
#             }
#             # Dynamically add fields based on the days parameter
#             for stat_prefix in [
#                 "hrs", "abs_per_hr", "is_red_hot_hr", "is_slump_hr",
#                 "ba", "is_red_hot_ba", "is_slump_ba",
#                 "ops", "is_red_hot_ops", "is_slump_ops",
#                 "barrels_percentage", "is_red_hot_barrels", "is_slump_barrels",
#                 "hard_hit_percentage", "is_red_hot_hard_hit", "is_slump_hard_hit"
#             ]:
#                 player_data[f"{stat_prefix}_{days}days"] = row[f"{stat_prefix}_{days}days"]
            
#             results.append(PlayerBatterPerformanceFlags(**player_data))

#         return results
#     except GoogleCloudError as e:
#         print(f"ERROR: BigQuery query for batter performance flags failed: {e}")
#         return None


# # Function to get pitcher performance by inning
# @lru_cache(maxsize=128)
# def get_pitcher_performance_by_inning(player_id: int, season: int) -> Optional[List[PlayerPitcherPerformanceByInning]]:
#     """ 指定された選手IDとシーズンに基づいて、選手のイニング別投手パフォーマンスを取得します。 """
#     query = f"""
#         SELECT
#             game_year,
#             pitcher_name,
#             pitcher_id,
#             inning,
#             hits_allowed,
#             outs_recorded,
#             batting_average_against,
#             obp_numerator,
#             obp_denominator,
#             slg_numerator,
#             slg_denominator,
#             ops_against,
#             home_runs_allowed,
#             non_home_run_hits_allowed,
#             free_passes
#         FROM
#             `{PROJECT_ID}.{DATASET_ID}.{PITCHING_PERFORMANCE_BY_INNING_TABLE_ID}`
#         WHERE
#             pitcher_id = @player_id
#             AND game_year = @season
#         ORDER BY
#             game_year ASC, inning ASC
#     """
#     job_config = bigquery.QueryJobConfig(
#         query_parameters=[
#             bigquery.ScalarQueryParameter("player_id", "INT64", player_id),
#             bigquery.ScalarQueryParameter("season", "INT64", season),
#         ]
#     )

#     try:
#         df = client.query(query, job_config=job_config).to_dataframe()
#         if df.empty:
#             print(f"DEBUG: No pitcher performance by inning found for player ID {player_id} in season {season}")
#             return []
        
#         results: List[PlayerPitcherPerformanceByInning] = []  # PlayerPitcherPerformanceByInningのリストとして初期化
#         for _, row in df.iterrows():
#             results.append(PlayerPitcherPerformanceByInning(
#                 game_year=row['game_year'],
#                 pitcher_name=row['pitcher_name'],
#                 pitcher_id=row['pitcher_id'],
#                 inning=row['inning'],
#                 hits_allowed=row['hits_allowed'],
#                 outs_recorded=row['outs_recorded'],
#                 batting_average_against=row['batting_average_against'],
#                 obp_numerator=row['obp_numerator'],
#                 obp_denominator=row['obp_denominator'],
#                 slg_numerator=row['slg_numerator'],
#                 slg_denominator=row['slg_denominator'],
#                 ops_against=row['ops_against'],
#                 home_runs_allowed=row['home_runs_allowed'],
#                 non_home_run_hits_allowed=row['non_home_run_hits_allowed'],
#                 free_passes=row['free_passes']
#             ))
#         return results
#     except GoogleCloudError as e:
#         print(f"ERROR: BigQuery query for pitcher performance by inning failed for player ID {player_id} in season {season}: {e}")
#         return None


# # Function to get the latest game date
# @lru_cache(maxsize=1)
# def get_latest_game_date() -> Optional[str]:
#     """
#     最新のゲーム日付を取得します。
#     """
#     query = f"""
#         SELECT
#             MAX(game_date) AS latest_game_date
#         FROM
#             `{PROJECT_ID}.{DATASET_ID}.{BATTER_PERFORMANCE_FLAGS_7DAYS_TABLE_ID}`
#     """
    
#     try:
#         df = client.query(query).to_dataframe()

#         # Debugging: log the DataFrame shape and columns
#         logger.debug(f"DEBUG: Fetched latest game date DataFrame shape: {df.shape}, columns: {df.columns.tolist()}")
#         logger.debug(f"DEBUG: First few rows of the DataFrame:\n{df.head()}")

#         if df.empty or 'latest_game_date' not in df.columns:
#             print("DEBUG: No game dates found.")
#             return None
        
#         latest_date = df['latest_game_date'].iloc[0]
#         if pd.isna(latest_date):
#             print("DEBUG: Latest game date is NaN.")
#             return None
        
#         return latest_date.strftime('%Y-%m-%d')  # 日付を文字列に変換して返す
#     except GoogleCloudError as e:
#         print(f"ERROR: BigQuery query for latest game date failed: {e}")
#         return None


# def get_batting_stats_by_inning(batter_id: Optional[int] = None, season: Optional[int] = None) -> Optional[List[PlayerBattingStatsByInning]]:
#     """
#     指定された打者のイニングごとの打率データを取得します。
#     """
#     client = get_bq_client()

#     season_where_clause = ""
#     if season is not None:
#         season_where_clause = "AND game_year = @season"

#     query = f"""
#         SELECT
#             *
#         FROM `{PROJECT_ID}.{DATASET_ID}.tbl_batter_inning_stats`
#         WHERE batter_id = @batter_id
#         {season_where_clause}
#     """

#     job_config = bigquery.QueryJobConfig(
#         query_parameters=[
#             bigquery.ScalarQueryParameter("batter_id", "INT64", batter_id),
#             *([] if season is None else [bigquery.ScalarQueryParameter("season", "INT64", season)])
#         ]
#     )

#     try:
#         df = client.query(query, job_config=job_config).to_dataframe()
#         if df.empty:
#             logger.debug(f"No batting stats by inning found for batter ID {batter_id}, season {season}.")
#             return None
        
#         results: List[PlayerBattingStatsByInning] = []
#         for _, row in df.iterrows():
#             results.append(PlayerBattingStatsByInning(**row.to_dict()))
#         return results
    
#     except GoogleCloudError as e:
#         logger.error(f"BigQuery query for batting stats by inning failed for batter ID {batter_id}: {e}", exc_info=True)
#         return None
#     except Exception as e:
#         logger.error(f"An unexpected error occurred while fetching batting stats by inning for batter ID {batter_id}: {e}", exc_info=True)
#         return None

