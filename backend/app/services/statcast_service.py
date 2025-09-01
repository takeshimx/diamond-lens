"""
Statcast Service Module
"""
from typing import Optional, List, Dict, Any
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError
import pandas as pd
import numpy as np
from functools import lru_cache
from backend.app.api.schemas import * 
from .base import (
    get_bq_client, client, logger,
    PROJECT_ID, DATASET_ID,
)
from .query_parts import CORE_SPLITS_METRICS_QUERY


# # Function to get Statcast data for a pitcher
# @lru_cache(maxsize=128)
# def get_pitcher_statcast_data(pitcher_id: int, season: int) -> Optional[PlayerStatcastData]:
#     """
#     指定されたpitcher_idに基づいて、選手のStatcastデータを取得します。
#     Note: pitcher_id and batter_id are MLB ID, not idfg.
#     """
#     query = f"""
#         SELECT
#             pitch_type,
#             game_date,
#             pitcher_name,
#             batter_id,
#             pitcher_id,
#             batter_name,
#             game_year,
#             events,
#             game_type,
#             hit_location,
#             balls,
#             strikes,
#             release_speed,
#             release_pos_x,
#             release_pos_z,
#             pfx_x,
#             pfx_z,
#             plate_x,
#             plate_z,
#             description,
#             type,
#             inning,
#             zone,
#             on_1b,
#             on_2b,
#             on_3b,
#             hit_distance_sc,
#             launch_speed,
#             launch_angle,
#             woba_value,
#             launch_speed_angle,
#             pitch_number,
#             at_bat_number
#         FROM
#             `{PROJECT_ID}.{DATASET_ID}.tbl_statcast_2021_2025_master`
#         WHERE
#             pitcher_id = @pitcher_id
#             AND events IS NOT NULL
#         ORDER BY
#             game_year DESC, game_date DESC
#     """
#     job_config = bigquery.QueryJobConfig(
#         query_parameters=[
#             bigquery.ScalarQueryParameter("pitcher_id", "INT64", pitcher_id),
#             bigquery.ScalarQueryParameter("season", "INT64", season)
#         ]
#     )

#     try:
#         df = client.query(query, job_config=job_config).to_dataframe()
#         if df.empty:
#             print(f"DEBUG: No Statcast data found for pitcher ID {pitcher_id}")
#             return None
        
#         results: List[PlayerStatcastData] = []  # PlayerStatcastDataのリストとして初期化
#         for _, row in df.iterrows():
#             results.append(PlayerStatcastData(
#                 pitch_type=row['pitch_type'],
#                 game_date=row['game_date'],
#                 pitcher_name=row['pitcher_name'],
#                 batter_id=row['batter_id'],
#                 pitcher_id=row['pitcher_id'],
#                 batter_name=row['batter_name'],
#                 game_year=row['game_year'],
#                 events=row['events'],
#                 game_type=row['game_type'],
#                 hit_location=row['hit_location'],
#                 balls=row['balls'],
#                 strikes=row['strikes'],
#                 release_speed=row['release_speed'],
#                 release_pos_x=row['release_pos_x'],
#                 release_pos_z=row['release_pos_z'],
#                 pfx_x=row['pfx_x'],
#                 pfx_z=row['pfx_z'],
#                 plate_x=row['plate_x'],
#                 plate_z=row['plate_z'],
#                 description=row['description'],
#                 type=row['type'],
#                 inning=row['inning'],
#                 zone=row['zone'],
#                 on_1b=row['on_1b'],
#                 on_2b=row['on_2b'],
#                 on_3b=row['on_3b'],
#                 hit_distance_sc=row['hit_distance_sc'],
#                 launch_speed=row['launch_speed'],
#                 launch_angle=row['launch_angle'],
#                 woba_value=row['woba_value'],
#                 launch_speed_angle=row['launch_speed_angle'],
#                 pitch_number=row['pitch_number'],
#                 at_bat_number=row['at_bat_number']
#             ))
#         return results
#     except GoogleCloudError as e:
#         print(f"ERROR: BigQuery query for player Statcast data failed for pitcher ID {pitcher_id}: {e}")
#         return None

# Function to get Statcast data for a batter
@lru_cache(maxsize=128)
def get_batter_splits_stats_advanced(
    batter_id: int, 
    season: Optional[int],
    innings: Optional[List[int]],
    strikes: Optional[int],
    balls: Optional[int],
    p_throws: Optional[str],
    runners: Optional[List[str]],
    pitch_types: Optional[List[str]],
    is_career: Optional[bool] = False # career stats flag
) -> Optional[List[PlayerStatcastData]]:
    """
    指定されたbatter_idに基づいて、選手のStatcastデータを取得します。
    Note: pitcher_id and batter_id are MLB ID, not idfg.
    """

    # dynamic base select and group by clause
    if is_career and season is None:
        base_select_clause = "batter_id, batter_name"
        group_by_clause = "GROUP BY batter_id, batter_name"
        order_by_clause = "ORDER BY batter_name"
    else:
        base_select_clause = "batter_id, batter_name, game_year"
        group_by_clause = "GROUP BY batter_id, batter_name, game_year"
        order_by_clause = "ORDER BY game_year ASC"

    metrics_for_select_clause = CORE_SPLITS_METRICS_QUERY

    season_where_clause = ""
    if season is not None:
        season_where_clause = "AND game_year = @season"
    
    innings_where_clause = ""
    if innings is not None and len(innings) > 0:
        innings_str = f"({', '.join(map(str, innings))})" # Convert list of ints to string for SQL IN clause e.g. "(1, 2, 3)"
        innings_where_clause = f"AND inning IN {innings_str}"
    
    strikes_where_clause = ""
    if strikes is not None:
        strikes_where_clause = "AND strikes = @strikes"

    balls_where_clause = ""
    if balls is not None:
        balls_where_clause = "AND balls = @balls"

    p_throws_where_clause = ""
    if p_throws is not None:
        p_throws_where_clause = "AND p_throws = @p_throws"

    runners_where_clause = ""
    if runners is not None and len(runners) > 0:
        if "risp" in runners:
            runners_where_clause = "AND (on_2b != 0 OR on_3b != 0)"
        elif 'bases_loaded' in runners:
            runners_where_clause = "AND (on_1b != 0 AND on_2b != 0 AND on_3b != 0)"
        elif None in runners:
            runners_where_clause = "AND (on_1b = 0 AND on_2b = 0 AND on_3b = 0)"
        elif '1b' in runners and len(runners) == 1:
            runners_where_clause = "AND (on_1b != 0 AND on_2b = 0 AND on_3b = 0)"
        elif '2b' in runners and len(runners) == 1:
            runners_where_clause = "AND (on_1b = 0 AND on_2b != 0 AND on_3b = 0)"
        elif '3b' in runners and len(runners) == 1:
            runners_where_clause = "AND (on_1b = 0 AND on_2b = 0 AND on_3b != 0)"
        elif '1b' in runners and '2b' in runners and len(runners) == 2:
            runners_where_clause = "AND (on_1b != 0 AND on_2b != 0 AND on_3b = 0)"
        elif '1b' in runners and '3b' in runners and len(runners) == 2:
            runners_where_clause = "AND (on_1b != 0 AND on_2b = 0 AND on_3b != 0)"
        elif '2b' in runners and '3b' in runners and len(runners) == 2:
            runners_where_clause = "AND (on_1b = 0 AND on_2b != 0 AND on_3b != 0)"
    
    pitch_types_where_clause = ""
    if pitch_types is not None and len(pitch_types) > 0:
        quated_pitch_type = [f"'{pt}'" for pt in pitch_types]
        pitch_types_str = f"({'. '.join(quated_pitch_type)})"
        pitch_types_where_clause = f"AND pitch_type IN {pitch_types_str}"
    

    query = f"""
        SELECT
            {base_select_clause},
            {metrics_for_select_clause}
        FROM
            `{PROJECT_ID}.{DATASET_ID}.tbl_statcast_2021_2025_master`
        WHERE
            batter_id = @batter_id
            {season_where_clause}
            {innings_where_clause}
            {strikes_where_clause}
            {balls_where_clause}
            {p_throws_where_clause}
            {runners_where_clause}
            {pitch_types_where_clause}
            AND events IS NOT NULL
            AND game_type = 'R'
            AND batter_id IS NOT NULL AND batter_name IS NOT NULL
            AND pitch_type IS NOT NULL
        {group_by_clause}
        {order_by_clause}
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("batter_id", "INT64", batter_id),
            *([] if season is None else [bigquery.ScalarQueryParameter("season", "INT64", season)]),
            *([] if innings is None else [bigquery.ArrayQueryParameter("innings", "INT64", innings)]),
            *([] if strikes is None else [bigquery.ScalarQueryParameter("strikes", "INT64", strikes)]),
            *([] if balls is None else [bigquery.ScalarQueryParameter("balls", "INT64", balls)]),
            *([] if p_throws is None else [bigquery.ScalarQueryParameter("p_throws", "STRING", p_throws)]),
            *([] if runners is None else [bigquery.ArrayQueryParameter("runners", "STRING", runners)]),
            *([] if pitch_types is None else [bigquery.ArrayQueryParameter("pitch_types", "STRING", pitch_types)]),
        ]
    )

    # # print() デバッグログはそのまま残す
    # print(f"DEBUG: Executing BigQuery query for get_batter_statcast_data (player_service):")
    # print(f"DEBUG: Query: {query}")
    # print(f"DEBUG: Parameters: {job_config.query_parameters}")

    # # ★★★ 強制デバッグエラーの追加（BigQueryクエリ実行直前） ★★★
    # # This line is for temporary debugging. Remove it after the issue is resolved.
    # raise Exception(f"DEBUG: About to execute BigQuery query for batter_id={batter_id}, season={season}")
    # # ★★★ ここまで ★★★

    try:
        df = client.query(query, job_config=job_config).to_dataframe()

        # # ★★★ 修正箇所: logger.debug を print() に一時的に置き換え ★★★
        # print(f"DEBUG: Statcast DataFrame fetched for batter_id {batter_id}, season {season}. Shape: {df.shape}")
        # if not df.empty:
        #     print(f"DEBUG: Statcast DataFrame head:\n{df.head().to_string()}")
        #     if 'game_year' in df.columns:
        #         print(f"DEBUG: Unique game_years in Statcast DataFrame: {df['game_year'].dropna().unique().tolist()}")
        #         print(f"DEBUG: game_year dtype: {df['game_year'].dtype}")
        # # ★★★ ここまで ★★★

        if df.empty:
            logger.debug(f"DEBUG: No Statcast data found for batter ID {batter_id}, season {season}. Returning None.")
            return None
        
        results: List[PlayerStatcastData] = []  # PlayerStatcastDataのリストとして初期化
        for _, row in df.iterrows():
            results.append(PlayerStatcastData(
                batter_id=row['batter_id'],
                batter_name=row['batter_name'],
                game_year=row['game_year'] if not is_career else None,
                hits=row['hits'],
                homeruns=row['homeruns'],
                doubles=row['doubles'],
                triples=row['triples'],
                singles=row['singles'],
                bb_hbp=row['bb_hbp'],
                so=row['so'],
                ab=row['ab'],
                avg=row['avg'],
                obp=row['obp'],
                slg=row['slg'],
                ops=row['ops'],
                hitting_events=row['hitting_events'],
                launch_angle=row['launch_angle'],
                exit_velocity=row['exit_velocity'],
                bat_speed=row['bat_speed'],
                swing_length=row['swing_length'],
                hard_hit_count=row['hard_hit_count'],
                denominator_for_hard_hit_rate=row['denominator_for_hard_hit_rate'],
                hard_hit_rate=row['hard_hit_rate'],
                barrels_count=row['barrels_count'],
                total_batted_balls=row['total_batted_balls'],
                barrels_rate=row['barrels_rate'],
                strikeout_rate=row['strikeout_rate'],
                swinging_strike_count=row['swinging_strike_count'],
                swinging_strike_rate=row['swinging_strike_rate'],
                rbi=row['rbi']
            ))
        logger.debug(f"Successfully fetched {len(results)} Statcast data entries for batter_id {batter_id}, season {season}.")
        return results
    except GoogleCloudError as e:
        logger.error(f"ERROR: BigQuery query for player Statcast data failed for batter ID {batter_id}: {e}")
        return None

