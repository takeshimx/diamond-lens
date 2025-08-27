"""
選手基本情報および詳細データの取得に関するサービス
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
    DIM_PLAYERS_TABLE_ID,
    BATTING_STATS_TABLE_ID,
    PITCHING_STATS_TABLE_ID,
    BATTER_SPLIT_STATS_TABLE_ID
)


# @lru_cache(maxsize=128)
# def get_player_details(player_id: int) -> Optional[PlayerDetailsResponse]:
#     """
#     指定されたplayer_id (idfgを想定) に基づいて、選手の詳細情報、年度別打撃成績、年度別投球成績を取得します。
#     """
#     player_basic_info = None
#     batting_stats = []
#     pitching_stats = []
#     batter_split_stats = []
#     batter_career_stats = []  # 新たに追加された変数
#     pitcher_career_stats = []  # 新たに追加された変数

#     # 1. 選手基本情報を取得
#     try:
#         player_info_query = f"""
#             SELECT
#                 mlb_id,
#                 bbref_id,
#                 fangraphs_id,
#                 first_name,
#                 last_name,
#                 mlb_debut_year,
#                 mlb_last_year
#             FROM
#                 `{PROJECT_ID}.{DATASET_ID}.{DIM_PLAYERS_TABLE_ID}`
#             WHERE
#                 fangraphs_id = @player_id OR mlb_id = @player_id 
#             LIMIT 1
#         """
#         job_config_player = bigquery.QueryJobConfig(
#             query_parameters=[
#                 bigquery.ScalarQueryParameter("player_id", "INT64", player_id),
#             ]
#         )
#         player_df = client.query(player_info_query, job_config=job_config_player).to_dataframe()

#         if not player_df.empty:
#             player_info_data = player_df.iloc[0].to_dict()
#             player_info_data['full_name'] = f"{player_info_data.get('first_name', '')} {player_info_data.get('last_name', '')}".strip()
#             player_basic_info = PlayerBasicInfo(**player_info_data) # Unpacking the dictionary into the Pydantic model
#             logger.debug(f"Fetched player basic info: {player_basic_info.model_dump_json()}")
#         else:
#             logger.debug(f"Player not found for ID (idfg): {player_id}. Returning None for player details.")
#             return None # 選手基本情報がない場合はここでNoneを返す
#     except GoogleCloudError as e:
#         logger.error(f"BigQuery query for player info failed for ID {player_id}: {e}", exc_info=True)
#         return None # エラー時もNoneを返す
#     except Exception as e:
#         logger.error(f"An unexpected error occurred while fetching player info for ID {player_id}: {e}", exc_info=True)
#         return None # エラー時もNoneを返す

#     # 上記のtry-exceptブロックでNoneを返すようになったため、このチェックは冗長になるが、念のため
#     if player_basic_info is None:
#         logger.error(f"player_basic_info is None after fetching. This should not happen. Returning None.")
#         return None
    
#     # 2. 年度別打撃成績を取得
#     try:
#         batting_query = f"""
#             SELECT
#                 idfg,
#                 season,
#                 name,
#                 team,
#                 league,
#                 g,
#                 ab,
#                 pa,
#                 r,
#                 h,
#                 `1b`,
#                 `2b`,
#                 `3b`,
#                 hr,
#                 rbi,
#                 sb,
#                 bb,
#                 so,
#                 sf,
#                 sh,
#                 hbp,
#                 avg,
#                 obp,
#                 slg,
#                 ops,
#                 iso,
#                 babip,
#                 wrcplus,
#                 woba,
#                 war,
#                 wpa,
#                 wpa_li,
#                 hardhitpct,
#                 barrelpct,
#                 hits_at_risp,
#                 singles_at_risp,
#                 doubles_at_risp,
#                 triples_at_risp,
#                 home_runs_at_risp,
#                 at_bats_at_risp,
#                 batting_average_at_risp,
#                 slugging_percentage_at_risp
#             FROM
#                 `{PROJECT_ID}.{DATASET_ID}.{BATTING_STATS_TABLE_ID}`
#             WHERE
#                 idfg = @player_id
#             ORDER BY
#                 season DESC
#         """
#         job_config_batting = bigquery.QueryJobConfig(
#             query_parameters=[
#                 bigquery.ScalarQueryParameter("player_id", "INT64", player_id),
#             ]
#         )
#         batting_df = client.query(batting_query, job_config=job_config_batting).to_dataframe()

#         if not batting_df.empty:
#             # NaNをNoneに変換する処理
#             for col in batting_df.columns: # 全カラムに対してNaNをNoneに変換
#                 if batting_df[col].dtype == 'object':
#                     batting_df[col] = batting_df[col].replace({pd.NA: None, float('nan'): None})
#                 elif pd.api.types.is_numeric_dtype(batting_df[col]):
#                     batting_df[col] = batting_df[col].replace({float('nan'): None}) # 数値型のNaNもNoneに


#             for col in ['avg', 'obp', 'slg', 'ops',
#                         'iso', 'bbpcnt', 'woba', 'wpa', 'hardhitpct', 'barrelpct',
#                         'batting_average_at_risp', 'slugging_percentage_at_risp']:
#                 if col in batting_df.columns:
#                     batting_df[col] = batting_df[col].round(3)
            
#             batting_stats = [PlayerBattingSeasonStats(**row) for row in batting_df.to_dict('records')]
#             logger.debug(f"Fetched {len(batting_stats)} batting season stats.")
#             # ★★★ デバッグログの追加 ★★★
#             if batting_stats:
#                 logger.debug(f"get_player_details (Batting): First PlayerBattingSeasonStats item (dict form): {batting_stats[0].model_dump()}")
#             # ★★★ ここまで ★★★

#     except GoogleCloudError as e:
#         print(f"ERROR: BigQuery query for batting stats failed for ID {player_id}: {e}")
#     except Exception as e:
#         print(f"ERROR: An unexpected error occurred while fetching batting stats for ID {player_id}: {e}")

#     # 3. 年度別投球成績を取得
#     try:
#         pitching_query = f"""
#             SELECT
#                 idfg,
#                 season,
#                 name,
#                 team,
#                 league,
#                 w,
#                 l,
#                 sv,
#                 g,
#                 gs,
#                 ip,
#                 h,
#                 r,
#                 er,
#                 hr,
#                 bb,
#                 so,
#                 whip,
#                 era,
#                 fip,
#                 k_9,
#                 bb_9,
#                 k_bb,
#                 avg,
#                 war,
#                 wpa,
#                 swstrpct,
#                 gbpct,
#                 lobpct,
#                 hr_9,
#                 barrelpct,
#                 hardhitpct
#             FROM
#                 `{PROJECT_ID}.{DATASET_ID}.{PITCHING_STATS_TABLE_ID}`
#             WHERE
#                 idfg = @player_id
#             ORDER BY
#                 season DESC
#         """
#         job_config_pitching = bigquery.QueryJobConfig(
#             query_parameters=[
#                 bigquery.ScalarQueryParameter("player_id", "INT64", player_id),
#             ]
#         )
#         pitching_df = client.query(pitching_query, job_config=job_config_pitching).to_dataframe()

#         if not pitching_df.empty:
#             # NaNをNoneに変換する処理
#             for col in pitching_df.columns: # 全カラムに対してNaNをNoneに変換
#                 if pitching_df[col].dtype == 'object':
#                     pitching_df[col] = pitching_df[col].replace({pd.NA: None, float('nan'): None})
#                 elif pd.api.types.is_numeric_dtype(pitching_df[col]):
#                     pitching_df[col] = pitching_df[col].replace({float('nan'): None})
            

#             for col in ['era', 'whip', 'fip', 'k_9', 'bb_9', 'k_bb', 'hr_9',
#                         'barrelpct', 'hardhitpct', 'swstrpct', 'gbpct', 'lobpct']:
#                 if col in pitching_df.columns:
#                     pitching_df[col] = pitching_df[col].round(2)
            
#             pitching_stats = [PlayerPitchingSeasonStats(**row) for row in pitching_df.to_dict('records')]
#             logger.debug(f"Fetched {len(pitching_stats)} pitching season stats.")
#             # ★★★ デバッグログの追加 ★★★
#             if pitching_stats:
#                 logger.debug(f"get_player_details (Pitching): First PlayerPitchingSeasonStats item (dict form): {pitching_stats[0].model_dump()}")
#             # ★★★ ここまで ★★★

#     except GoogleCloudError as e:
#         print(f"ERROR: BigQuery query for pitching stats failed for ID {player_id}: {e}")
#     except Exception as e:
#         print(f"ERROR: An unexpected error occurred while fetching pitching stats for ID {player_id}: {e}")

#     # 4. Fetch batter split stats
#     try:
#         batter_split_stats_query = f"""
#             SELECT
#                 idfg,
#                 mlb_id,
#                 batter_name,
#                 game_year,
#                 team,
#                 league,
#                 pa,
#                 hits_at_risp,
#                 homeruns_at_risp,
#                 triples_at_risp,
#                 doubles_at_risp,
#                 singles_at_risp,
#                 bb_hbp_at_risp,
#                 so_at_risp,
#                 ab_at_risp,
#                 avg_at_risp,
#                 obp_at_risp,
#                 slg_at_risp,
#                 ops_at_risp,
#                 hits_at_bases_loaded,
#                 grandslam,
#                 doubles_at_bases_loaded,
#                 triples_at_bases_loaded,
#                 singles_at_bases_loaded,
#                 bb_hbp_at_bases_loaded,
#                 so_at_bases_loaded,
#                 ab_at_bases_loaded,
#                 avg_at_bases_loaded,
#                 obp_at_bases_loaded,
#                 slg_at_bases_loaded,
#                 ops_at_bases_loaded,
#                 hits_at_runner_on_1b,
#                 homeruns_at_runner_on_1b,
#                 triples_at_runner_on_1b,
#                 doubles_at_runner_on_1b,
#                 singles_at_runner_on_1b,
#                 bb_hbp_at_runner_on_1b,
#                 so_at_runner_on_1b,
#                 ab_at_runner_on_1b,
#                 avg_at_runner_on_1b,
#                 obp_at_runner_on_1b,
#                 slg_at_runner_on_1b,
#                 ops_at_runner_on_1b
#             FROM
#                 `{PROJECT_ID}.{DATASET_ID}.{BATTER_SPLIT_STATS_TABLE_ID}`
#             WHERE
#                 idfg = @player_id
#             ORDER BY
#                 game_year DESC
#         """
#         job_config_batter_split = bigquery.QueryJobConfig(
#             query_parameters=[
#                 bigquery.ScalarQueryParameter("player_id", "INT64", player_id),
#             ]
#         )
#         batter_split_stats_df = client.query(batter_split_stats_query, job_config=job_config_batter_split).to_dataframe()

#         if not batter_split_stats_df.empty:
#             batter_split_stats = [PlayerBattingSplitStats(**row) for row in batter_split_stats_df.to_dict('records')]

#     except GoogleCloudError as e:
#         print(f"ERROR: BigQuery query for batter split stats failed for ID {player_id}: {e}")
#     except Exception as e:
#         print(f"ERROR: An unexpected error occurred while fetching batter split stats for ID {player_id}: {e}")
    
#     # 5. Fetch pitcher split stats


#     # 6. Fetch batter career stats
#     try:
#         batter_career_stats_query = f"""
#             SELECT
#                 idfg,
#                 mlbid AS mlb_id,
#                 name,
#                 SUM(g) AS g,
#                 SUM(ab) AS ab,
#                 SUM(pa) AS pa,
#                 SUM(h) AS h,
#                 SUM(hr) AS hr,
#                 SUM(r) AS r,
#                 SUM(rbi) AS rbi,
#                 SUM(sb) AS sb,
#                 SUM(bb) AS bb,
#                 SUM(so) AS so,
#                 SUM(sf) AS sf,
#                 SUM(sh) AS sh,
#                 SUM(hbp) AS hbp,
#                 SUM(war) AS war,
#                 ROUND(SAFE_DIVIDE(SUM(h), SUM(ab)), 3) AS avg,
#                 -- OBP
#                 ROUND(SAFE_DIVIDE(SUM(h) + SUM(bb) + SUM(hbp),
#                     SUM(ab) + SUM(bb) + SUM(hbp)), 3) AS obp,
#                 -- SLG
#                 ROUND(SAFE_DIVIDE(
#                     SUM(h) + (SUM(hr) * 4) + (SUM(`2b`) * 2) + (SUM(`3b`) * 3),
#                     SUM(ab)), 3) AS slg,
#                 -- OPS
#                 ROUND(SAFE_DIVIDE(SUM(h) + SUM(bb) + SUM(hbp),
#                     SUM(ab) + SUM(bb) + SUM(hbp)), 3) +
#                 ROUND(SAFE_DIVIDE(
#                     SUM(h) + (SUM(hr) * 4) + (SUM(`2b`) * 2) + (SUM(`3b`) * 3),
#                     SUM(ab)), 3) AS ops
#             FROM 
#                 `{PROJECT_ID}.{DATASET_ID}.{BATTING_STATS_TABLE_ID}`
#             WHERE 
#                 idfg IS NOT NULL
#                 AND mlbid IS NOT NULL
#                 AND idfg = @player_id
#             GROUP BY 
#                 idfg, mlbid, name
#             ORDER BY 
#                 name ASC, idfg ASC
#         """

#         job_config_batter_career = bigquery.QueryJobConfig(
#             query_parameters=[
#                 bigquery.ScalarQueryParameter("player_id", "INT64", player_id),
#             ]
#         )
#         batter_career_stats_df = client.query(batter_career_stats_query, job_config=job_config_batter_career).to_dataframe()

#         if not batter_career_stats_df.empty:
#             # NaNをNoneに変換する処理
#             for col in batter_career_stats_df.columns: # 全カラムに対してNaNをNoneに変換
#                 if batter_career_stats_df[col].dtype == 'object':
#                     batter_career_stats_df[col] = batter_career_stats_df[col].replace({pd.NA: None, float('nan'): None})
#                 elif pd.api.types.is_numeric_dtype(batter_career_stats_df[col]):
#                     batter_career_stats_df[col] = batter_career_stats_df[col].replace({float('nan'): None})

#             # 小数点以下の桁数を調整
#             for col in ['avg', 'obp', 'slg', 'ops']:
#                 if col in batter_career_stats_df.columns:
#                     batter_career_stats_df[col] = batter_career_stats_df[col].round(3)

#         if not batter_career_stats_df.empty:
#             batter_career_stats = [PlayerBattingSeasonStats(**row) for row in batter_career_stats_df.to_dict('records')]

#     except GoogleCloudError as e:
#         print(f"ERROR: BigQuery query for batter career stats failed for ID {player_id}: {e}")
#     except Exception as e:
#         print(f"ERROR: An unexpected error occurred while fetching batter career stats for ID {player_id}: {e}")

#     # 7. Fetch pitcher career stats
#     try:
#         pitcher_career_stats_query = f"""
#             SELECT
#                 idfg,
#                 name,
#                 SUM(w) AS w,
#                 SUM(l) AS l,
#                 SUM(sv) AS sv,
#                 SUM(g) AS g,
#                 SUM(gs) AS gs,
#                 SUM(ip) AS ip,
#                 SUM(h) AS h,
#                 SUM(hr) AS hr,
#                 SUM(r) AS r,
#                 SUM(er) AS er,
#                 SUM(bb) AS bb,
#                 SUM(so) AS so,
#                 SUM(hbp) AS hbp,
#                 SUM(war) AS war,
#                 -- ERA
#                 ROUND((SUM(er) / SUM(ip)) * 9, 2) AS era,
#                 -- WHIP
#                 ROUND(SAFE_DIVIDE(SUM(h) + SUM(bb), SUM(ip)), 3) AS whip,
#                 -- K/9
#                 ROUND((SUM(so) / SUM(ip)) * 9, 3) AS k_9,
#                 -- BB/9
#                 ROUND((SUM(bb) / SUM(ip)) * 9, 3) AS bb_9,
#                 -- K/BB
#                 ROUND(SAFE_DIVIDE(SUM(so), SUM(bb)), 3) AS k_bb,
#                 -- FIP
#                 ROUND(SAFE_DIVIDE(
#                     (SUM(hr) * 13) + ((SUM(bb) + SUM(hbp)) * 3) + (SUM(so) * 3) - (SUM(so) * 2),
#                     SUM(ip)), 3) AS fip
#             FROM 
#                 `{PROJECT_ID}.{DATASET_ID}.{PITCHING_STATS_TABLE_ID}`
#             WHERE 
#                 idfg IS NOT NULL
#                 AND idfg = @player_id
#             GROUP BY 
#                 idfg, name
#             ORDER BY 
#                 name ASC, idfg ASC     
#         """

#         job_config_pitcher_career = bigquery.QueryJobConfig(
#             query_parameters=[
#                 bigquery.ScalarQueryParameter("player_id", "INT64", player_id),
#             ]
#         )
#         pitcher_career_stats_df = client.query(pitcher_career_stats_query, job_config=job_config_pitcher_career).to_dataframe()

#         if not pitcher_career_stats_df.empty:
#             # NaNをNoneに変換する処理
#             for col in pitcher_career_stats_df.columns: # 全カラムに対してNaNをNoneに変換
#                 if pitcher_career_stats_df[col].dtype == 'object':
#                     pitcher_career_stats_df[col] = pitcher_career_stats_df[col].replace({pd.NA: None, float('nan'): None})
#                 elif pd.api.types.is_numeric_dtype(pitcher_career_stats_df[col]):
#                     pitcher_career_stats_df[col] = pitcher_career_stats_df[col].replace({float('nan'): None})

#             # 小数点以下の桁数を調整
#             for col in ['era', 'whip', 'k_9', 'bb_9', 'k_bb', 'fip']:
#                 if col in pitcher_career_stats_df.columns:
#                     pitcher_career_stats_df[col] = pitcher_career_stats_df[col].round(3)

#         if not pitcher_career_stats_df.empty:
#             pitcher_career_stats = [PlayerPitchingSeasonStats(**row) for row in pitcher_career_stats_df.to_dict('records')]
        
#     except GoogleCloudError as e:
#         print(f"ERROR: BigQuery query for pitcher career stats failed for ID {player_id}: {e}")
#     except Exception as e:
#         print(f"ERROR: An unexpected error occurred while fetching pitcher career stats for ID {player_id}: {e}")

#     # 最終的なPlayerDetailsResponseを構築
#     if player_basic_info:
#         return PlayerDetailsResponse(
#             player_info=player_basic_info,
#             batting_season_stats=batting_stats,
#             pitching_season_stats=pitching_stats,
#             batter_split_stats=batter_split_stats,
#             batter_career_stats=batter_career_stats,
#             pitcher_career_stats=pitcher_career_stats
#         )
#     return None


@lru_cache(maxsize=128)
def get_players_by_name(player_name: str) -> Optional[List[PlayerSearchItem]]: # 戻り値の型を修正
    """
    選手名に基づいて選手情報を検索します。
    All active player from 2021 to 2025 are returned.
    """

    # ★★★ 修正箇所: player_name が空文字列の場合のWHERE句の挙動を調整 ★★★
    where_clause_parts = []
    query_parameters = []

    if player_name: # player_name が空文字列でない場合のみフィルタリング
        where_clause_parts.append("""
                (CONCAT(first_name, ' ', last_name) LIKE @player_name_pattern
                OR first_name LIKE @player_name_pattern
                OR last_name LIKE @player_name_pattern)
        """)
        query_parameters.append(
            bigquery.ScalarQueryParameter("player_name_pattern", "STRING", f"%{player_name}%")
        )

    # Filter for active players from 2021 to 2025
    where_clause_parts.append("""
            (mlb_debut_year <= @end_year AND mlb_last_year >= @start_year)
    """)
    query_parameters.append(bigquery.ScalarQueryParameter("start_year", "INT64", 2021))
    query_parameters.append(bigquery.ScalarQueryParameter("end_year", "INT64", 2025))

    final_where_clause = "WHERE " + " AND ".join(where_clause_parts) if where_clause_parts else ""

    query = f"""
        SELECT
            mlb_id,
            fangraphs_id AS idfg,
            first_name,
            last_name,
            mlb_debut_year,
            mlb_last_year,
            team,
            league
        FROM
            `{PROJECT_ID}.{DATASET_ID}.{DIM_PLAYERS_TABLE_ID}`
        {final_where_clause}
        ORDER BY
            last_name ASC, first_name ASC
        LIMIT 10000
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=query_parameters
    )
    

    try:
        df = client.query(query, job_config=job_config).to_dataframe()

        # ★★★ 修正箇所: idfgとmlb_idのNaN値をNoneに変換 ★★★
        # PydanticのOptional[int]がNoneを期待するため
        if 'idfg' in df.columns:
            df['idfg'] = df['idfg'].replace({pd.NA: None, float('nan'): None}).astype(object) # object型にしてNoneを保持
        if 'mlb_id' in df.columns:
            df['mlb_id'] = df['mlb_id'].replace({pd.NA: None, float('nan'): None}).astype(object) # object型にしてNoneを保持

        if df.empty:
            logger.debug(f"No players found for name: {player_name} in 2021-2025 season.")
            return []
        
        results: List[PlayerSearchItem] = [] # PlayerSearchItemのリストとして初期化
        for _, row in df.iterrows():
            full_name = f"{row['first_name']} {row['last_name']}".strip()
            results.append(PlayerSearchItem(
                idfg=row['idfg'],
                mlb_id=row.get('mlb_id'), # Optionalなので .get() を使用
                player_name=full_name,
                team=row.get('team'),  # Add team field
                league=row.get('league')  # Add league field
            ))
        return results

    except GoogleCloudError as e:
        print(f"ERROR: BigQuery player name search failed for '{player_name}': {e}")
        return None
    except Exception as e:
        print(f"ERROR: An unexpected error occurred during player name search for '{player_name}': {e}")
        return None


# ★★★ 修正箇所: player_id から player_name を取得する関数を追加 ★★★
def get_player_name_by_id(player_id: int) -> Optional[str]:
    """
    FanGraphs ID (idfg) または MLB ID を使用して選手のフルネームを取得します。
    """
    client = get_bq_client()
    query = f"""
        SELECT CONCAT(first_name, ' ', last_name) AS full_name
        FROM `{PROJECT_ID}.{DATASET_ID}.{DIM_PLAYERS_TABLE_ID}`
        WHERE fangraphs_id = @player_id OR mlb_id = @player_id
        LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("player_id", "INT64", player_id),
        ]
    )
    try:
        query_job = client.query(query, job_config=job_config)
        result = query_job.result()
        for row in result:
            return row["full_name"]
    except Exception as e:
        logger.error(f"Error fetching player name for ID {player_id}: {e}", exc_info=True)
        return None
    return None


# # Function to get Shohei Ohtani's two-way player stats
# @lru_cache(maxsize=128)
# def get_ohtani_two_way_stats(season: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
#     """
#     Shohei Ohtaniの二刀流選手としての打撃成績と投球成績を取得します。
#     seasonが指定されていない場合は、最新のシーズンのデータを取得します。
#     """
#     client = get_bq_client() 

#     # season_where_clause = ""
#     # if season is not None:
#     #     season_where_clause = "AND EXTRACT(YEAR FROM pitching_game_batting_date) = @season"
    
#     season_filter_sql = ""
#     query_params = []
#     if season is not None:
#         season_filter_sql = "AND EXTRACT(YEAR FROM pitching_game_batting_date) = @season"
#         query_params.append(bigquery.ScalarQueryParameter("season", "INT64", season))
    
#     query = f"""
#         SELECT
#             batter_mlb_id,
#             EXTRACT(YEAR FROM pitching_game_batting_date) AS season,
#             -- when he pitched
#             SUM(hits) AS total_hits_sp,
#             SUM(home_runs) AS total_home_runs_sp,
#             SUM(triples) AS total_triples_sp,
#             SUM(doubles) AS total_doubles_sp,
#             SUM(singles) AS total_singles_sp,
#             SUM(walks_and_hbp) AS total_walks_and_hbp_sp,
#             SUM(at_bats) AS total_at_bats_sp,
#             SUM(numerator_for_obp) AS total_numerator_for_obp_sp,
#             SUM(denominator_for_obp) AS total_denominator_for_obp_sp,
#             ROUND(SAFE_DIVIDE(SUM(hits), SUM(at_bats)), 3) AS batting_average_sp,
#             ROUND(
#                 SAFE_DIVIDE(SUM(numerator_for_obp), SUM(denominator_for_obp))
#                 , 3) AS on_base_percentage_sp,
#             ROUND(SAFE_DIVIDE(
#                 ((SUM(home_runs) * 4) + (SUM(triples) * 3) + (SUM(doubles) * 2) + (SUM(singles) * 1)), 
#                 (SUM(at_bats))
#             ), 3) AS slugging_percentage_sp,
#             ROUND(
#                 SAFE_DIVIDE(SUM(numerator_for_obp), SUM(denominator_for_obp)) +
#                 SAFE_DIVIDE(
#                 ((SUM(home_runs) * 4) + (SUM(triples) * 3) + (SUM(doubles) * 2) + (SUM(singles) * 1)), 
#                 (SUM(at_bats))
#             ), 3) AS on_base_plus_slugging_sp,
#             -- on the following game after he pitched
#             SUM(next_game_hits) AS total_hits_next_game,
#             SUM(next_game_home_runs) AS total_home_runs_next_game,
#             SUM(next_game_triples) AS total_triples_next_game,
#             SUM(next_game_doubles) AS total_doubles_next_game,
#             SUM(next_game_singles) AS total_singles_next_game,
#             SUM(next_game_walks_and_hbp) AS total_walks_and_hbp_next_game,
#             SUM(next_game_at_bats) AS total_at_bats_next_game,
#             SUM(next_game_numerator_for_obp) AS total_numerator_for_obp_next_game,
#             SUM(next_game_denominator_for_obp) AS total_denominator_for_obp_next_game,
#             ROUND(SAFE_DIVIDE(SUM(next_game_hits), SUM(next_game_at_bats)), 3) AS batting_average_next_game,
#             ROUND(
#                 SAFE_DIVIDE(SUM(next_game_numerator_for_obp), SUM(next_game_denominator_for_obp))
#                 , 3) AS on_base_percentage_next_game,
#             ROUND(SAFE_DIVIDE(
#                 ((SUM(next_game_home_runs) * 4) + (SUM(next_game_triples) * 3) + (SUM(next_game_doubles) * 2) + (SUM(next_game_singles) * 1)), 
#                 (SUM(next_game_at_bats))
#             ), 3) AS slugging_percentage_next_game,
#             ROUND(
#                 SAFE_DIVIDE(SUM(next_game_numerator_for_obp), SUM(next_game_denominator_for_obp)) +
#                 SAFE_DIVIDE(
#                 ((SUM(next_game_home_runs) * 4) + (SUM(next_game_triples) * 3) + (SUM(next_game_doubles) * 2) + (SUM(next_game_singles) * 1)), 
#                 (SUM(next_game_at_bats))
#             ), 3) AS on_base_plus_slugging_next_game
#         FROM
#             `{PROJECT_ID}.{DATASET_ID}.tbl_shohei_ohtani_two_way`
#         WHERE
#             1=1
#             {season_filter_sql}
#         GROUP BY
#             batter_mlb_id, season
#         ORDER BY
#             season ASC
#     """

#     # job_config = bigquery.QueryJobConfig(
#     #     query_parameters=[
#     #         bigquery.ScalarQueryParameter("season", "INT64", season) if season is not None else []
#     #     ]
#     # )

#     # ★★★ 変更点2: query_parametersにquery_paramsを直接渡す ★★★
#     job_config = bigquery.QueryJobConfig(
#         query_parameters=query_params # query_paramsが空リストの場合も正しく処理される
#     )

#     # Debugging: log the query and parameters
#     logger.debug(f"Executing query for Shohei Ohtani two-way stats: {query}")
#     logger.debug(f"Parameters: {job_config.query_parameters}")
    
    
#     try:
#         df = client.query(query, job_config=job_config).to_dataframe()
#         if df.empty:
#             logger.debug(f"No Shohei Ohtani two-way stats found for season {season}")
#             return None
        
#         # Debugging: log the DataFrame shape and columns and first few rows
#         logger.debug(f"Fetched Shohei Ohtani two-way stats DataFrame shape: {df.shape}, columns: {df.columns.tolist()}")
#         logger.debug(f"First few rows of the DataFrame:\n{df.head()}")

#         df = df.where(pd.notnull(df), None)

#         ohtani_stats_list = df.to_dict(orient='records')
        
#         logger.debug(f"Successfully fetched Ohtani two-way stats for season {season}.")
#         return ohtani_stats_list # 辞書のリストを返す
    
#         # # NaNをNoneに変換する処理
#         # for col in df.columns: # 全カラムに対してNaNをNoneに変換
#         #     if df[col].dtype == 'object':
#         #         df[col] = df[col].replace({pd.NA: None, float('nan'): None})
#         #     elif pd.api.types.is_numeric_dtype(df[col]):
#         #         df[col] = df[col].replace({float('nan'): None})

#         # # 小数点以下の桁数を調整
#         # for col in ['batting_average_sp', 'on_base_percentage_sp', 'slugging_percentage_sp', 'on_base_plus_slugging_sp',
#         #             'batting_average_next_game', 'on_base_percentage_next_game', 
#         #             'slugging_percentage_next_game', 'on_base_plus_slugging_next_game']:
#         #     if col in df.columns:
#         #         df[col] = df[col].round(3)
        
#         # results: List[ShoheiOhtaniTwoWayStats] = []  # ShoheiOhtaniTwoWayStatsのリストとして初期化
#         # for _, row in df.iterrows():
#         #     results.append(ShoheiOhtaniTwoWayStats(
#         #         batter_mlb_id=row['batter_mlb_id'],
#         #         season=row['season'],
#         #         total_hits_sp=row['total_hits_sp'],
#         #         total_home_runs_sp=row['total_home_runs_sp'],
#         #         total_triples_sp=row['total_triples_sp'],
#         #         total_doubles_sp=row['total_doubles_sp'],
#         #         total_singles_sp=row['total_singles_sp'],
#         #         total_walks_and_hbp_sp=row['total_walks_and_hbp_sp'],
#         #         total_at_bats_sp=row['total_at_bats_sp'],
#         #         total_numerator_for_obp_sp=row['total_numerator_for_obp_sp'],
#         #         total_denominator_for_obp_sp=row['total_denominator_for_obp_sp'],
#         #         batting_average_sp=row['batting_average_sp'],
#         #         on_base_percentage_sp=row['on_base_percentage_sp'],
#         #         slugging_percentage_sp=row['slugging_percentage_sp'],
#         #         on_base_plus_slugging_sp=row['on_base_plus_slugging_sp'],
#         #         total_hits_next_game=row['total_hits_next_game'],
#         #         total_home_next_game=row['total_home_next_game'],
#         #         total_triples_next_game=row['total_triples_next_game'],
#         #         total_doubles_next_game=row['total_doubles_next_game'],
#         #         total_singles_next_game=row['total_singles_next_game'],
#         #         total_walks_and_hbp_next_game=row['total_walks_and_hbp_next_game'],
#         #         total_at_bats_next_game=row['total_at_bats_next_game'],
#         #         total_numerator_for_obp_next_game=row['total_numerator_for_obp_next_game'],
#         #         total_denominator_for_obp_next_game=row['total_denominator_for_obp_next_game'],
#         #         batting_average_next_game=row['batting_average_next_game'],
#         #         on_base_percentage_next_game=row['on_base_percentage_next_game'],
#         #         slugging_percentage_next_game=row['slugging_percentage_next_game'],
#         #         on_base_plus_slugging_next_game=row['on_base_plus_slugging_next_game']
#         #     ))
#         # return results
#     except GoogleCloudError as e:
#         print(f"ERROR: BigQuery query for Shohei Ohtani two-way stats failed for season {season}: {e}")
#         return None
#     except Exception as e:
#         print(f"ERROR: An unexpected error occurred while fetching Shohei Ohtani two-way stats for season {season}: {e}")
#         return None

