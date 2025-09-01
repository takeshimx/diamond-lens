"""
Leaderboard service for fetching player and team statistics for various leaderboards.
"""
from typing import Optional, List, Dict, Any
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError
from functools import lru_cache
from app.api.schemas import * # For Development, add backend. path
from .base import (
    get_bq_client, client, logger,
    PROJECT_ID, DATASET_ID,
    BATTING_STATS_TABLE_ID,
    PITCHING_STATS_TABLE_ID,
    BATTER_SPLIT_STATS_TABLE_ID,
    TEAM_BATTING_STATS_TABLE_ID,
    TEAM_PITCHING_STATS_TABLE_ID
)


@lru_cache(maxsize=128)
def get_batting_leaderboard(season: int, league: str, min_pa: int, metric_order: str) -> Optional[List[PlayerBattingSeasonStats]]:
    """
    指定されたシーズン、リーグ、および最小打席数に基づいて、打撃リーダーボードを取得します。
    """

    # 2025年の場合は最小PAを280に調整するロジックをサービス層で持つ (As of Jul 8, 2025)
    adjusted_min_pa = 280 if season == 2025 else min_pa
    
    processed_league = league.lower()
    if processed_league == 'mlb':
        league_filtered_clause = "AND league IN ('al', 'nl')" # If MLB is selected, filter by AL and NL
    elif processed_league == 'al' or processed_league == 'nl':
        league_filtered_clause = "AND league = @league" # If AL or NL is selected, filter by that league

    query = f"""
        SELECT
            idfg,
            mlbid,
            season,
            name,
            team,
            league,
            g,
            ab,
            pa,
            r,
            h,
            hr,
            rbi,
            sb,
            bb,
            so,
            avg,
            obp,
            slg,
            ops,
            iso,
            wrcplus,
            woba,
            war,
            hardhitpct,
            barrelpct,
            batting_average_at_risp,
            slugging_percentage_at_risp,
            home_runs_at_risp
        FROM
            `{PROJECT_ID}.{DATASET_ID}.{BATTING_STATS_TABLE_ID}`
        WHERE
            season = @season
            AND pa >= @min_pa
            {league_filtered_clause}
        ORDER BY
            CASE @metric_order -- Dynamic ORDER BY
                WHEN 'avg' THEN avg
                WHEN 'obp' THEN obp
                WHEN 'slg' THEN slg
                WHEN 'ops' THEN ops
                WHEN 'wrcplus' THEN wrcplus
                WHEN 'woba' THEN woba
                WHEN 'war' THEN war
                WHEN 'hr' THEN hr
                WHEN 'rbi' THEN rbi
                WHEN 'h' THEN h
                WHEN 'r' THEN r
                WHEN 'iso' THEN iso
                WHEN 'sb' THEN sb
                WHEN 'bb' THEN bb
                WHEN 'so' THEN so
                WHEN 'hardhitpct' THEN hardhitpct
                WHEN 'barrelpct' THEN barrelpct
                WHEN 'batting_average_at_risp' THEN batting_average_at_risp
                WHEN 'slugging_percentage_at_risp' THEN slugging_percentage_at_risp
                WHEN 'home_runs_at_risp' THEN home_runs_at_risp
                ELSE ops -- sort by OPS as default
            END DESC
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("season", "INT64", season),
            # bigquery.ScalarQueryParameter("league", "STRING", processed_league),
            *([] if processed_league == 'mlb' else [bigquery.ScalarQueryParameter("league", "STRING", processed_league)]),
            bigquery.ScalarQueryParameter("min_pa", "INT64", adjusted_min_pa),  # 最小打席数のパラメータ
            bigquery.ScalarQueryParameter("metric_order", "STRING", metric_order)  # 動的なORDER BYのためのパラメータ
        ]
    )

    # # ★★★ デバッグログの追加 ★★★
    # logger.debug(f"Executing BigQuery query for batting leaderboard:")
    # logger.debug(f"Query: {query}")
    # logger.debug(f"Parameters: {job_config.query_parameters}")
    # # ★★★ デバッグログの追加ここまで ★★★

    try:
        df = client.query(query, job_config=job_config).to_dataframe()

        # # ★★★ デバッグログの追加: データフレームの内容を確認 ★★★
        # logger.debug(f"DataFrame fetched. Shape: {df.shape}")
        # if not df.empty:
        #     logger.debug(f"DataFrame head:\n{df.head().to_string()}")
        # # ★★★ デバッグログの追加ここまで ★★★

        if df.empty:
            print(f"DEBUG: No batting leaderboard data found for season {season}, league {processed_league}, min_pa {adjusted_min_pa}")
            return []
        
        results: List[PlayerBattingSeasonStats] = [] # PlayerBattingSeasonStatsのリストとして初期化
        for _, row in df.iterrows():
            results.append(PlayerBattingSeasonStats(**row.to_dict()))
        return results

    except GoogleCloudError as e:
        print(f"ERROR: BigQuery query for batting leaderboard failed for season {season}, league {processed_league}, min_pa {adjusted_min_pa}: {e}")
        return None
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while fetching batting leaderboard for season {season}, league {processed_league}, min_pa {adjusted_min_pa}: {e}")
        return None


# @lru_cache(maxsize=128)
# def get_batter_split_stats_leaderboard(season: int, league: str, min_pa: int, split_type: str) -> Optional[List[PlayerBattingSplitStats]]:
#     """
#     指定されたシーズン、リーグ、および最小打席数に基づいて、バッターのスプリット統計リーダーボードを取得します。
#     """

#     # 2025年の場合は最小PAを280に調整するロジックをサービス層で持つ (As of Jul 8, 2025)
#     adjusted_min_pa = 280 if season == 2025 else min_pa
    
#     processed_league = league.lower()
#     if processed_league == 'mlb':
#         league_filtered_clause = "AND league IN ('al', 'nl')" # If MLB is selected, filter by AL and NL
#     elif processed_league == 'al' or processed_league == 'nl':
#         league_filtered_clause = "AND league = @league" # If AL or NL is selected, filter by that league
    
#     if split_type == "RISP":
#         # Query for RISP (Runners In Scoring Position) stats
#         select_clause = """
#             hits_at_risp, homeruns_at_risp, triples_at_risp, doubles_at_risp, singles_at_risp,
#             bb_hbp_at_risp, so_at_risp, ab_at_risp, avg_at_risp, obp_at_risp, slg_at_risp, ops_at_risp
#         """
#     elif split_type == "Bases Loaded":
#         # Query for Bases Loaded stats
#         select_clause = """
#             hits_at_bases_loaded, grandslam, doubles_at_bases_loaded, triples_at_bases_loaded,
#             singles_at_bases_loaded, bb_hbp_at_bases_loaded, so_at_bases_loaded, ab_at_bases_loaded,
#             avg_at_bases_loaded, obp_at_bases_loaded, slg_at_bases_loaded, ops_at_bases_loaded
#         """
#     elif split_type == "Runner on 1B":
#         # Query for Runner on 1B stats
#         select_clause = """
#             hits_at_runner_on_1b, homeruns_at_runner_on_1b, triples_at_runner_on_1b,
#             doubles_at_runner_on_1b, singles_at_runner_on_1b, bb_hbp_at_runner_on_1b,
#             so_at_runner_on_1b, ab_at_runner_on_1b, avg_at_runner_on_1b, obp_at_runner_on_1b,
#             slg_at_runner_on_1b, ops_at_runner_on_1b
#         """
#     else:
#         raise ValueError(f"Invalid split_type: {split_type}. Must be one of 'RISP', 'Bases Loaded', or 'Runner on 1B'.")
    
#     query = f"""
#         SELECT
#             idfg,
#             mlb_id,
#             batter_name,
#             game_year,
#             team,
#             league,
#             pa, -- not only clutch situations, but all plate appearances in a season
#             {select_clause}
#         FROM
#         `{PROJECT_ID}.{DATASET_ID}.{BATTER_SPLIT_STATS_TABLE_ID}`
#         WHERE
#             game_year = @season
#             AND pa >= @min_pa
#             {league_filtered_clause}
#         ORDER BY
#             CASE @split_type -- Dynamic ORDER BY based on split type
#                 WHEN 'RISP' THEN avg_at_risp
#                 WHEN 'Bases Loaded' THEN avg_at_bases_loaded
#                 WHEN 'Runner on 1B' THEN ops_at_runner_on_1b
#                 ELSE avg_at_risp -- Default to RISP if split_type is not recognized
#             END DESC
#         -- LIMIT 20
#     """
#     job_config = bigquery.QueryJobConfig(
#         query_parameters=[
#             bigquery.ScalarQueryParameter("season", "INT64", season),
#             *([] if processed_league == 'mlb' else [bigquery.ScalarQueryParameter("league", "STRING", processed_league)]),
#             bigquery.ScalarQueryParameter("min_pa", "INT64", adjusted_min_pa),  # 最小打席数のパラメータ
#             bigquery.ScalarQueryParameter("split_type", "STRING", split_type),  # スプリットタイプのパラメータ
#             # bigquery.ScalarQueryParameter("metric_order", "STRING", metric_order)  # 動的なORDER BYのためのパラメータ
#         ]
#     )

#     # # ★★★ デバッグログの追加 ★★★
#     # print(f"DEBUG: Executing BigQuery query for batting splits leaderboard:")
#     # print(f"DEBUG: Query: {query}")
#     # print(f"DEBUG: Parameters: {job_config.query_parameters}")
#     # # ★★★ デバッグログの追加ここまで ★★★

#     try:
#         df = client.query(query, job_config=job_config).to_dataframe()

#         # # ★★★ デバッグログの追加: データフレームの内容を確認 ★★★
#         # logger.debug(f"DataFrame fetched. Shape: {df.shape}")
#         # if not df.empty:
#         #     logger.debug(f"DataFrame head:\n{df.head().to_string()}")
#         # # ★★★ デバッグログの追加ここまで ★★★
        
#         if df.empty:
#             print(f"DEBUG: No batting split stats leaderboard data found for season {season}, league {processed_league}, min_pa {adjusted_min_pa}")
#             return []
        
#         results: List[PlayerBattingSplitStats] = [] # PlayerBattingSplitStatsのリストとして初期化
#         for _, row in df.iterrows():
#             results.append(PlayerBattingSplitStats(**row.to_dict()))
#         return results

#     except GoogleCloudError as e:
#         print(f"ERROR: BigQuery query for batting split stats leaderboard failed for season {season}, league {processed_league}, min_pa {adjusted_min_pa}: {e}")
#         return None
#     except Exception as e:
#         print(f"ERROR: An unexpected error occurred while fetching batting split stats leaderboard for season {season}, league {processed_league}, min_pa {adjusted_min_pa}: {e}")
#         return None



@lru_cache(maxsize=128)
def get_pitching_leaderboard(season: int, league: str, min_ip: int, metric_order: str) -> Optional[List[PlayerPitchingSeasonStats]]:
    """
    指定されたシーズン、リーグ、および最小投球回数に基づいて、投球リーダーボードを取得します。
    """
    # 2025年の場合は最小IPを75に調整するロジックをサービス層で持つ (As of Jul 8, 2025)
    adjusted_min_ip = 75 if season == 2025 else min_ip
    
    processed_league = league.lower()
    if processed_league == 'mlb':
        league_filtered_clause = "AND league IN ('al', 'nl')" # If MLB is selected, filter by AL and NL
    elif processed_league == 'al' or processed_league == 'nl':
        league_filtered_clause = "AND league = @league" # If AL or NL is selected, filter by that league

    query = f"""
        SELECT
            idfg,
            mlbid,
            season,
            name,
            team,
            league,
            w,
            l,
            sv,
            g,
            gs,
            h,
            r,
            er,
            era,
            so,
            k_9,
            fip,
            war,
            whip,
            ip,
            bb,
            bb_9,
            k_bb,
            hr,
            hr_9,
            avg,
            barrelpct,
            hardhitpct
        FROM
            `{PROJECT_ID}.{DATASET_ID}.fact_pitching_stats_master`
        WHERE
            season = @season
            AND ip >= @min_ip
            {league_filtered_clause}
        ORDER BY
            CASE 
                -- For ASC metrics (lower is better)
                WHEN @metric_order IN ('era', 'whip', 'fip', 'bb_9', 'hr_9', 'avg', 'barrelpct', 'hardhitpct') THEN
                    CASE @metric_order
                        WHEN 'era' THEN era
                        WHEN 'whip' THEN whip
                        WHEN 'fip' THEN fip
                        WHEN 'bb_9' THEN bb_9
                        WHEN 'hr_9' THEN hr_9
                        WHEN 'avg' THEN avg
                        WHEN 'barrelpct' THEN barrelpct
                        WHEN 'hardhitpct' THEN hardhitpct
                        ELSE era
                    END
                -- For DESC metrics (higher is better), use negative values to reverse sort
                ELSE
                    -CASE @metric_order
                        WHEN 'w' THEN w
                        WHEN 'so' THEN so
                        WHEN 'k_9' THEN k_9
                        WHEN 'war' THEN war
                        WHEN 'ip' THEN ip
                        WHEN 'k_bb' THEN k_bb
                        WHEN 'sv' THEN sv
                        WHEN 'l' THEN l -- for losses, we want fewer (smaller values), so negative makes it work
                        WHEN 'g' THEN g
                        WHEN 'gs' THEN gs
                        ELSE era -- default to era for unknown metrics
                    END
            END ASC
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("season", "INT64", season),
            # bigquery.ScalarQueryParameter("league", "STRING", processed_league),
            *([] if processed_league == 'mlb' else [bigquery.ScalarQueryParameter("league", "STRING", processed_league)]),
            bigquery.ScalarQueryParameter("min_ip", "INT64", adjusted_min_ip),
            bigquery.ScalarQueryParameter("metric_order", "STRING", metric_order)  # 動的なORDER BYのためのパラメータ
        ]
    )

    # # ★★★ デバッグログの追加 ★★★
    # print(f"DEBUG: Executing BigQuery query for pitching leaderboard:")
    # print(f"DEBUG: Query: {query}")
    # print(f"DEBUG: Parameters: {job_config.query_parameters}")
    # # ★★★ デバッグログの追加ここまで ★★★

    try:
        df = client.query(query, job_config=job_config).to_dataframe()
        if df.empty:
            print(f"DEBUG: No pitching leaderboard data found for season {season}, league {processed_league}, min_ip {adjusted_min_ip}")
            return []
        
        results: List[PlayerPitchingSeasonStats] = [] # PlayerPitchingSeasonStatsのリストとして初期化
        for _, row in df.iterrows():
            results.append(PlayerPitchingSeasonStats(**row.to_dict()))
        return results

    except GoogleCloudError as e:
        print(f"ERROR: BigQuery query for pitching leaderboard failed for season {season}, league {processed_league}, min_ip {adjusted_min_ip}: {e}")
        return None
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while fetching pitching leaderboard for season {season}, league {processed_league}, min_ip {adjusted_min_ip}: {e}")
        return None


# # Service function to get team batting stats leaderboard
# @lru_cache(maxsize=128)
# def get_team_batting_stats_leaderboard(
#         season: int, 
#         league: str,
#         metric_order: str
#     ) -> Optional[List[TeamBattingStatsLeaderboard]]:
#     """
#     指定されたシーズン、リーグ、および最小打席数に基づいて、チーム打撃リーダーボードを取得します。
#     """
#     if league == 'MLB':
#         league_filtered_clause = "AND league IN ('AL', 'NL')" # If MLB is selected, filter by AL and NL
#     else:
#         league_filtered_clause = "AND league = @league" # If AL or NL is selected, filter by that league
    
#     # Query to get team batting stats
#     query = f"""
#         SELECT
#             season,
#             team,
#             league,
#             hr,
#             h,
#             rbi,
#             r,
#             bb,
#             so,
#             sb,
#             avg,
#             obp,
#             slg,
#             ops,
#             war,
#             wrcplus,
#             barrelpct,
#             hardhitpct,
#             woba
#         FROM
#             `{PROJECT_ID}.{DATASET_ID}.{TEAM_BATTING_STATS_TABLE_ID}`
#         WHERE
#             season = @season
#             {league_filtered_clause}
#         ORDER BY
#             CASE @metric_order -- Dynamic ORDER BY
#                 WHEN 'hr' THEN hr
#                 WHEN 'h' THEN h
#                 WHEN 'rbi' THEN rbi
#                 WHEN 'r' THEN r
#                 WHEN 'bb' THEN bb
#                 WHEN 'so' THEN so
#                 WHEN 'sb' THEN sb
#                 WHEN 'avg' THEN avg
#                 WHEN 'obp' THEN obp
#                 WHEN 'slg' THEN slg
#                 WHEN 'ops' THEN ops
#                 WHEN 'war' THEN war
#                 WHEN 'wrcplus' THEN wrcplus
#                 WHEN 'barrelpct' THEN barrelpct
#                 WHEN 'hardhitpct' THEN hardhitpct
#                 WHEN 'woba' THEN woba
#                 ELSE ops -- sort by OPS as default
#             END DESC
#     """

#     # Set job configuration
#     job_config = bigquery.QueryJobConfig(
#         query_parameters=[
#             bigquery.ScalarQueryParameter("season", "INT64", season),
#             *([] if league == 'MLB' else [bigquery.ScalarQueryParameter("league", "STRING", league)]),
#             bigquery.ScalarQueryParameter("metric_order", "STRING", metric_order)
#         ]
#     )

#     # create dataframe from query result and return results with Pydantic model
#     try:
#         df = client.query(query, job_config=job_config).to_dataframe()

#         if df.empty:
#             print(f"DEBUG: No team batting stats leaderboard data found for season {season}, league {league}")
#             return []
        
#         results: List[TeamBattingStatsLeaderboard] = []
#         for _, row in df.iterrows():
#             results.append(TeamBattingStatsLeaderboard(**row.to_dict()))
#         return results

#     except GoogleCloudError as e:
#         print(f"ERROR: BigQuery query for team batting stats leaderboard failed for season {season}, league {league}: {e}")
#         return None
#     except Exception as e:
#         print(f"ERROR: An unexpected error occurred while fetching team batting stats leaderboard for season {season}, league {league}: {e}")
#         return None

# # Service function to get team pitching stats leaderboard
# @lru_cache(maxsize=128)
# def get_team_pitching_stats_leaderboard(
#         season: int, 
#         league: str,
#         metric_order: str
#     ) -> Optional[List[TeamPitchingStatsLeaderboard]]:
#     """
#     指定されたシーズン、リーグ、および最小投球回数に基づいて、チーム投球リーダーボードを取得します。
#     """

#     if league == 'MLB':
#         league_filtered_clause = "AND league IN ('AL', 'NL')" # If MLB is selected, filter by AL and NL
#     else:
#         league_filtered_clause = "AND league = @league" # If AL or NL is selected, filter by that league
    
#     # Query to get team pitching stats
#     query = f"""
#         SELECT
#             season,
#             team,
#             league,
#             era,
#             w,
#             l,
#             so,
#             h,
#             r,
#             er,
#             bb,
#             fip,
#             war,
#             whip,
#             k_9,
#             bb_9,
#             k_bb,
#             hr_9,
#             avg,
#             hr,
#             lobpct
#         FROM
#             `{PROJECT_ID}.{DATASET_ID}.{TEAM_PITCHING_STATS_TABLE_ID}`
#         WHERE
#             season = @season
#             {league_filtered_clause}
#         ORDER BY
#             CASE @metric_order -- Dynamic ORDER BY
#                 WHEN 'era' THEN era
#                 WHEN 'w' THEN w
#                 WHEN 'l' THEN l
#                 WHEN 'so' THEN so
#                 WHEN 'h' THEN h
#                 WHEN 'r' THEN r
#                 WHEN 'er' THEN er
#                 WHEN 'bb' THEN bb
#                 WHEN 'fip' THEN fip
#                 WHEN 'war' THEN war
#                 WHEN 'whip' THEN whip
#                 WHEN 'k_9' THEN k_9
#                 WHEN 'bb_9' THEN bb_9
#                 WHEN 'k_bb' THEN k_bb
#                 WHEN 'hr_9' THEN hr_9
#                 WHEN 'avg' THEN avg
#                 WHEN 'hr' THEN hr
#                 WHEN 'lobpct' THEN lobpct
#                 ELSE era -- sort by ERA as default
#             END ASC
#     """

#     # Set job configuration
#     job_config = bigquery.QueryJobConfig(
#         query_parameters=[
#             bigquery.ScalarQueryParameter("season", "INT64", season),
#             *([] if league == 'MLB' else [bigquery.ScalarQueryParameter("league", "STRING", league)]),
#             bigquery.ScalarQueryParameter("metric_order", "STRING", metric_order)
#         ]
#     )

#     # create dataframe from query result and return results with Pydantic model
#     try:
#         df = client.query(query, job_config=job_config).to_dataframe()

#         if df.empty:
#             print(f"DEBUG: No team pitching stats leaderboard data found for season {season}, league {league}")
#             return []
        
#         results: List[TeamPitchingStatsLeaderboard] = []
#         for _, row in df.iterrows():
#             results.append(TeamPitchingStatsLeaderboard(**row.to_dict()))
#         return results

#     except GoogleCloudError as e:
#         print(f"ERROR: BigQuery query for team pitching stats leaderboard failed for season {season}, league {league}: {e}")
#         return None
#     except Exception as e:
#         print(f"ERROR: An unexpected error occurred while fetching team pitching stats leaderboard for season {season}, league {league}: {e}")
#         return None
 

# Funtion to get number of eligible players for ranking
@lru_cache(maxsize=128)
def get_total_eligible_players(
    season: int,
    league: Optional[str] = None, # 'al', 'nl', or 'mlb'
    table_type: str = 'batting', # 'batting' or 'pitching'
    min_pa: Optional[int] = None, # 打者の最小打席数 (打撃ランキングの場合)
    min_ip: Optional[int] = None # 投手の最小投球回 (投球ランキングの場合)
) -> int:
    """
    指定されたシーズン、リーグ、およびテーブルタイプに基づいて、ランキング対象の選手数を取得します。
    """
    client = get_bq_client()

    # Create league filter clause based on league input
    processed_league = league.lower()
    league_filter_clause = ""
    if processed_league == 'mlb':
        league_filter_clause = "AND TRIM(league) IN ('al', 'nl')"
    elif processed_league == 'al' or processed_league == 'nl':
        league_filter_clause = "AND TRIM(league) = @league"

    # Create minimum threshold clause based on table type
    if table_type == 'batting':
        if min_pa is None:
            min_threshold_clause = f"AND pa >= @min_pa"
        else: # set default minimum PA if not provided
            if season <= 2024:
                min_threshold_clause = "AND pa >= 350"
            elif season == 2025:
                min_threshold_clause = "AND pa >= 150" # TODO: Need to confirm this value for 2025 season
        table_id = BATTING_STATS_TABLE_ID
    elif table_type == 'pitching':
        if min_ip is None:
            min_threshold_clause = f"AND ip >= @min_ip"
        else: # set default minimum IP if not provided
            if season <= 2024:
                min_threshold_clause = "AND ip >= 100"
            elif season == 2025:
                min_threshold_clause = "AND ip >= 50" # TODO: Need to confirm this value for 2025 season
        table_id = PITCHING_STATS_TABLE_ID
    else:
        logger.error(f"Invalid table_type: {table_type}. Must be 'batting' or 'pitching'.")
        return 0
    
    query = f"""
        SELECT COUNT(DISTINCT idfg) as total_players
        FROM `{PROJECT_ID}.{DATASET_ID}.{table_id}`
        WHERE season = @season
            {league_filter_clause}
            {min_threshold_clause}
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("season", "INT64", season),
            *([] if processed_league == 'mlb' else [bigquery.ScalarQueryParameter("league", "STRING", processed_league)]),
            *([] if min_pa is None else [bigquery.ScalarQueryParameter("min_pa", "INT64", min_pa)]),
            *([] if min_ip is None else [bigquery.ScalarQueryParameter("min_ip", "INT64", min_ip)])
        ]
    )

    # logger.debug(f"Executing BigQuery query for total eligible players: {query}")
    # logger.debug(f"Parameters: {job_config.query_parameters}")

    try:
        df = client.query(query, job_config=job_config).to_dataframe()

        # # ★★★ デバッグログの追加 ★★★
        # logger.debug(f"Total Eligible Players DataFrame fetched. Shape: {df.shape}")
        # if not df.empty:
        #     logger.debug(f"Total Eligible Players DataFrame head:\n{df.head().to_string()}")
        # # ★★★ ここまで ★★★

        if not df.empty and 'total_players' in df.columns:
            return int(df['total_players'].iloc[0])
        return 0
    except Exception as e:
        logger.error(f"Error fetching total eligible players for season {season}, league {league}, table {table_type}: {e}", exc_info=True)
        return 0
 