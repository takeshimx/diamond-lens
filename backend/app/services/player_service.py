from typing import Optional, List, Dict, Any
from google.cloud import bigquery
from google.oauth2 import service_account
from google.cloud.exceptions import GoogleCloudError
import pandas as pd
import os
import json
import numpy as np
import requests
from dotenv import load_dotenv
from functools import lru_cache
from .bigquery_service import client  # BigQueryクライアントをインポート
# 定義したPydanticスキーマをインポート
from backend.app.api.schemas import *
import logging
# from backend.app.services.ranking_queries import get_player_ranking_batch

# ロガーの設定
# DEBUGレベルのログをすべて出力するように設定
# 既存のハンドラをクリアし、StreamHandlerを明示的に追加してコンソール出力が確実になるようにする
logging.getLogger().handlers = [] # 既存のハンドラをクリア - 追加された行
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()] # コンソールへの出力が確実になるようにStreamHandlerを追加 - 変更された行
)
logger = logging.getLogger(__name__)

dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "tksm-dash-test-25")
DATASET_ID = os.getenv("BIGQUERY_DATASET_ID", "mlb_analytics_dash_25")
BATTING_STATS_TABLE_ID = os.getenv("BIGQUERY_BATTING_STATS_TABLE_ID", "fact_batting_stats_with_risp")
PITCHING_STATS_TABLE_ID = os.getenv("BIGQUERY_PITCHING_STATS_TABLE_ID", "fact_pitching_stats")
DIM_PLAYERS_TABLE_ID = os.getenv("BIGQUERY_DIM_PLAYERS_TABLE_ID", "dim_players")
BATTING_OFFENSIVE_STATS_TABLE_ID = os.getenv("BIGQUERY_BATTER_OFFENSIVE_STATS_TABLE_ID", "tbl_batter_offensive_stats_monthly")
BAT_PERFORMANCE_SC_TABLE_ID = os.getenv("BIGQUERY_BATTER_PERFORMANCE_BY_STRIKE_COUNT_TABLE_ID", "tbl_batter_performance_by_strike_count")
BAT_PERFORMANCE_RISP_TABLE_ID = os.getenv("BIGQUERY_BATTER_PERFORMANCE_AT_RISP_TABLE_ID", "tbl_batter_performance_risp_monthly")
PITCHING_PERFORMANCE_BY_INNING_TABLE_ID = os.getenv("BIGQUERY_PITCHER_PERFORMANCE_BY_INNING_TABLE_ID", "tbl_pitching_performance_by_inning")
TEAM_BATTING_STATS_TABLE_ID = os.getenv("BIGQUERY_TEAM_BATTING_STATS_TABLE_ID", "fact_team_batting_stats_master")
TEAM_PITCHING_STATS_TABLE_ID = os.getenv("BIGQUERY_TEAM_PITCHING_STATS_TABLE_ID", "fact_team_pitching_stats_master")
BATTER_SPLIT_STATS_TABLE_ID = os.getenv("BIGQUERY_BATTER_SPLIT_STATS_TABLE_ID", "tbl_batter_split_stats")
BATTER_PERFORMANCE_FLAGS_7DAYS_TABLE_ID = os.getenv("BIGQUERY_BATTER_PERFORMANCE_FLAGS_7days_TABLE_ID", "view_tbl_batter_rolling_vs_season_stats_7_days")
BATTER_PERFORMANCE_FLAGS_15DAYS_TABLE_ID = os.getenv("BIGQUERY_BATTER_PERFORMANCE_FLAGS_15days_TABLE_ID", "view_tbl_batter_rolling_vs_season_stats_15_days")

# Manage Google cloud alient with singleton pattern
SERVICE_ACCOUNT_KEY_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

_bq_client = None

def get_bq_client():
    """
    BigQueryクライアントのシングルトンインスタンスを返します。
    """
    global _bq_client
    if _bq_client is None:
        try:
            if SERVICE_ACCOUNT_KEY_PATH and os.path.exists(SERVICE_ACCOUNT_KEY_PATH):
                credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_KEY_PATH)
                _bq_client = bigquery.Client(credentials=credentials, project=PROJECT_ID)
                logger.info("BigQuery client initialized using service account credentials.")
            else:
                _bq_client = bigquery.Client(project=PROJECT_ID) # 環境変数またはgcloud auth loginを使用
                logger.info("BigQuery client initialized using default credentials.")
        except Exception as e:
            logger.error(f"Failed to initialize BigQuery client: {e}", exc_info=True)
            raise # クライアント初期化失敗時は例外を再スロー
    return _bq_client


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
            wpa,
            wpa_li,
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
                WHEN 'wpa' THEN wpa
                -- WHEN 'wpa_li' THEN wpa_li
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
        -- LIMIT 20
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


@lru_cache(maxsize=128)
def get_batter_split_stats_leaderboard(season: int, league: str, min_pa: int, split_type: str) -> Optional[List[PlayerBattingSplitStats]]:
    """
    指定されたシーズン、リーグ、および最小打席数に基づいて、バッターのスプリット統計リーダーボードを取得します。
    """

    # 2025年の場合は最小PAを280に調整するロジックをサービス層で持つ (As of Jul 8, 2025)
    adjusted_min_pa = 280 if season == 2025 else min_pa
    
    processed_league = league.lower()
    if processed_league == 'mlb':
        league_filtered_clause = "AND league IN ('al', 'nl')" # If MLB is selected, filter by AL and NL
    elif processed_league == 'al' or processed_league == 'nl':
        league_filtered_clause = "AND league = @league" # If AL or NL is selected, filter by that league
    
    if split_type == "RISP":
        # Query for RISP (Runners In Scoring Position) stats
        select_clause = """
            hits_at_risp, homeruns_at_risp, triples_at_risp, doubles_at_risp, singles_at_risp,
            bb_hbp_at_risp, so_at_risp, ab_at_risp, avg_at_risp, obp_at_risp, slg_at_risp, ops_at_risp
        """
    elif split_type == "Bases Loaded":
        # Query for Bases Loaded stats
        select_clause = """
            hits_at_bases_loaded, grandslam, doubles_at_bases_loaded, triples_at_bases_loaded,
            singles_at_bases_loaded, bb_hbp_at_bases_loaded, so_at_bases_loaded, ab_at_bases_loaded,
            avg_at_bases_loaded, obp_at_bases_loaded, slg_at_bases_loaded, ops_at_bases_loaded
        """
    elif split_type == "Runner on 1B":
        # Query for Runner on 1B stats
        select_clause = """
            hits_at_runner_on_1b, homeruns_at_runner_on_1b, triples_at_runner_on_1b,
            doubles_at_runner_on_1b, singles_at_runner_on_1b, bb_hbp_at_runner_on_1b,
            so_at_runner_on_1b, ab_at_runner_on_1b, avg_at_runner_on_1b, obp_at_runner_on_1b,
            slg_at_runner_on_1b, ops_at_runner_on_1b
        """
    else:
        raise ValueError(f"Invalid split_type: {split_type}. Must be one of 'RISP', 'Bases Loaded', or 'Runner on 1B'.")
    
    query = f"""
        SELECT
            idfg,
            mlb_id,
            batter_name,
            game_year,
            team,
            league,
            pa, -- not only clutch situations, but all plate appearances in a season
            {select_clause}
        FROM
        `{PROJECT_ID}.{DATASET_ID}.{BATTER_SPLIT_STATS_TABLE_ID}`
        WHERE
            game_year = @season
            AND pa >= @min_pa
            {league_filtered_clause}
        ORDER BY
            CASE @split_type -- Dynamic ORDER BY based on split type
                WHEN 'RISP' THEN avg_at_risp
                WHEN 'Bases Loaded' THEN avg_at_bases_loaded
                WHEN 'Runner on 1B' THEN ops_at_runner_on_1b
                ELSE avg_at_risp -- Default to RISP if split_type is not recognized
            END DESC
        -- LIMIT 20
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("season", "INT64", season),
            *([] if processed_league == 'mlb' else [bigquery.ScalarQueryParameter("league", "STRING", processed_league)]),
            bigquery.ScalarQueryParameter("min_pa", "INT64", adjusted_min_pa),  # 最小打席数のパラメータ
            bigquery.ScalarQueryParameter("split_type", "STRING", split_type),  # スプリットタイプのパラメータ
            # bigquery.ScalarQueryParameter("metric_order", "STRING", metric_order)  # 動的なORDER BYのためのパラメータ
        ]
    )

    # # ★★★ デバッグログの追加 ★★★
    # print(f"DEBUG: Executing BigQuery query for batting splits leaderboard:")
    # print(f"DEBUG: Query: {query}")
    # print(f"DEBUG: Parameters: {job_config.query_parameters}")
    # # ★★★ デバッグログの追加ここまで ★★★

    try:
        df = client.query(query, job_config=job_config).to_dataframe()

        # # ★★★ デバッグログの追加: データフレームの内容を確認 ★★★
        # logger.debug(f"DataFrame fetched. Shape: {df.shape}")
        # if not df.empty:
        #     logger.debug(f"DataFrame head:\n{df.head().to_string()}")
        # # ★★★ デバッグログの追加ここまで ★★★
        
        if df.empty:
            print(f"DEBUG: No batting split stats leaderboard data found for season {season}, league {processed_league}, min_pa {adjusted_min_pa}")
            return []
        
        results: List[PlayerBattingSplitStats] = [] # PlayerBattingSplitStatsのリストとして初期化
        for _, row in df.iterrows():
            results.append(PlayerBattingSplitStats(**row.to_dict()))
        return results

    except GoogleCloudError as e:
        print(f"ERROR: BigQuery query for batting split stats leaderboard failed for season {season}, league {processed_league}, min_pa {adjusted_min_pa}: {e}")
        return None
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while fetching batting split stats leaderboard for season {season}, league {processed_league}, min_pa {adjusted_min_pa}: {e}")
        return None


@lru_cache(maxsize=128)
def get_ohtani_two_way_stats(season: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
    """
    Shohei Ohtaniの二刀流選手としての打撃成績と投球成績を取得します。
    seasonが指定されていない場合は、最新のシーズンのデータを取得します。
    """
    client = get_bq_client() 

    # season_where_clause = ""
    # if season is not None:
    #     season_where_clause = "AND EXTRACT(YEAR FROM pitching_game_batting_date) = @season"
    
    season_filter_sql = ""
    query_params = []
    if season is not None:
        season_filter_sql = "AND EXTRACT(YEAR FROM pitching_game_batting_date) = @season"
        query_params.append(bigquery.ScalarQueryParameter("season", "INT64", season))
    
    query = f"""
        SELECT
            batter_mlb_id,
            EXTRACT(YEAR FROM pitching_game_batting_date) AS season,
            -- when he pitched
            SUM(hits) AS total_hits_sp,
            SUM(home_runs) AS total_home_runs_sp,
            SUM(triples) AS total_triples_sp,
            SUM(doubles) AS total_doubles_sp,
            SUM(singles) AS total_singles_sp,
            SUM(walks_and_hbp) AS total_walks_and_hbp_sp,
            SUM(at_bats) AS total_at_bats_sp,
            SUM(numerator_for_obp) AS total_numerator_for_obp_sp,
            SUM(denominator_for_obp) AS total_denominator_for_obp_sp,
            ROUND(SAFE_DIVIDE(SUM(hits), SUM(at_bats)), 3) AS batting_average_sp,
            ROUND(
                SAFE_DIVIDE(SUM(numerator_for_obp), SUM(denominator_for_obp))
                , 3) AS on_base_percentage_sp,
            ROUND(SAFE_DIVIDE(
                ((SUM(home_runs) * 4) + (SUM(triples) * 3) + (SUM(doubles) * 2) + (SUM(singles) * 1)), 
                (SUM(at_bats))
            ), 3) AS slugging_percentage_sp,
            ROUND(
                SAFE_DIVIDE(SUM(numerator_for_obp), SUM(denominator_for_obp)) +
                SAFE_DIVIDE(
                ((SUM(home_runs) * 4) + (SUM(triples) * 3) + (SUM(doubles) * 2) + (SUM(singles) * 1)), 
                (SUM(at_bats))
            ), 3) AS on_base_plus_slugging_sp,
            -- on the following game after he pitched
            SUM(next_game_hits) AS total_hits_next_game,
            SUM(next_game_home_runs) AS total_home_runs_next_game,
            SUM(next_game_triples) AS total_triples_next_game,
            SUM(next_game_doubles) AS total_doubles_next_game,
            SUM(next_game_singles) AS total_singles_next_game,
            SUM(next_game_walks_and_hbp) AS total_walks_and_hbp_next_game,
            SUM(next_game_at_bats) AS total_at_bats_next_game,
            SUM(next_game_numerator_for_obp) AS total_numerator_for_obp_next_game,
            SUM(next_game_denominator_for_obp) AS total_denominator_for_obp_next_game,
            ROUND(SAFE_DIVIDE(SUM(next_game_hits), SUM(next_game_at_bats)), 3) AS batting_average_next_game,
            ROUND(
                SAFE_DIVIDE(SUM(next_game_numerator_for_obp), SUM(next_game_denominator_for_obp))
                , 3) AS on_base_percentage_next_game,
            ROUND(SAFE_DIVIDE(
                ((SUM(next_game_home_runs) * 4) + (SUM(next_game_triples) * 3) + (SUM(next_game_doubles) * 2) + (SUM(next_game_singles) * 1)), 
                (SUM(next_game_at_bats))
            ), 3) AS slugging_percentage_next_game,
            ROUND(
                SAFE_DIVIDE(SUM(next_game_numerator_for_obp), SUM(next_game_denominator_for_obp)) +
                SAFE_DIVIDE(
                ((SUM(next_game_home_runs) * 4) + (SUM(next_game_triples) * 3) + (SUM(next_game_doubles) * 2) + (SUM(next_game_singles) * 1)), 
                (SUM(next_game_at_bats))
            ), 3) AS on_base_plus_slugging_next_game
        FROM
            `{PROJECT_ID}.{DATASET_ID}.tbl_shohei_ohtani_two_way`
        WHERE
            1=1
            {season_filter_sql}
        GROUP BY
            batter_mlb_id, season
        ORDER BY
            season ASC
    """

    # job_config = bigquery.QueryJobConfig(
    #     query_parameters=[
    #         bigquery.ScalarQueryParameter("season", "INT64", season) if season is not None else []
    #     ]
    # )

    # ★★★ 変更点2: query_parametersにquery_paramsを直接渡す ★★★
    job_config = bigquery.QueryJobConfig(
        query_parameters=query_params # query_paramsが空リストの場合も正しく処理される
    )

    # Debugging: log the query and parameters
    logger.debug(f"Executing query for Shohei Ohtani two-way stats: {query}")
    logger.debug(f"Parameters: {job_config.query_parameters}")
    
    
    try:
        df = client.query(query, job_config=job_config).to_dataframe()
        if df.empty:
            logger.debug(f"No Shohei Ohtani two-way stats found for season {season}")
            return None
        
        # Debugging: log the DataFrame shape and columns and first few rows
        logger.debug(f"Fetched Shohei Ohtani two-way stats DataFrame shape: {df.shape}, columns: {df.columns.tolist()}")
        logger.debug(f"First few rows of the DataFrame:\n{df.head()}")

        df = df.where(pd.notnull(df), None)

        ohtani_stats_list = df.to_dict(orient='records')
        
        logger.debug(f"Successfully fetched Ohtani two-way stats for season {season}.")
        return ohtani_stats_list # 辞書のリストを返す
    
    except GoogleCloudError as e:
        print(f"ERROR: BigQuery query for Shohei Ohtani two-way stats failed for season {season}: {e}")
        return None
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while fetching Shohei Ohtani two-way stats for season {season}: {e}")
        return None


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
            season,
            name,
            team,
            league,
            -- w,
            l,
            sv,
            g,
            gs,
            h,
            r,
            er,
            era,
            w,
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
            `{PROJECT_ID}.{DATASET_ID}.{PITCHING_STATS_TABLE_ID}`
        WHERE
            season = @season
            AND ip >= @min_ip
            {league_filtered_clause}
        ORDER BY
            CASE @metric_order -- Dynamic ORDER BY
                WHEN 'era' THEN era
                -- WHEN 'w' THEN w
                WHEN 'so' THEN so
                WHEN 'k_9' THEN k_9
                WHEN 'fip' THEN fip
                WHEN 'war' THEN war
                WHEN 'whip' THEN whip
                WHEN 'ip' THEN ip
                WHEN 'bb' THEN bb
                WHEN 'bb_9' THEN bb_9
                WHEN 'k_bb' THEN k_bb
                WHEN 'hr' THEN hr
                WHEN 'hr_9' THEN hr_9
                WHEN 'avg' THEN avg
                WHEN 'barrelpct' THEN barrelpct
                WHEN 'hardhitpct' THEN hardhitpct
                ELSE era -- sort by ERA as default
            END ASC
        -- LIMIT 20
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




def get_ai_response_for_qna(query: str, season: Optional[int] = None) -> Optional[str]:
    """
    ユーザーの自然言語クエリに基づいて、打者・投手のリーダーボードデータを取得し、
    LLMが回答を生成します。
    ここではシンプルに、特定のシーズン（または最新シーズン）の打者・投手リーダーボードをLLMに渡します。
    """
    client = get_bq_client()

    current_year = datetime.now().year
    
    # # LLMに渡す格納するリスト
    # all_batting_leaderboards_for_llm = []
    # all_pitching_leaderboards_for_llm = []
    # risp_batting_splits_leaderboards_for_llm = []
    # bases_loaded_batting_splits_leaderboards_for_llm = []
    # runner_on_first_batting_splits_leaderboards_for_llm = []
    # ohtani_two_way_stats_for_llm = []

    # LLMに渡すデータを格納する辞書
    data_for_llm = {}

    # どのリーダーボードが必要かを判断
    fetch_batting_leaderboard = False
    fetch_pitching_leaderboard = False
    fetch_risp_splits = False
    fetch_bases_loaded_splits = False
    fetch_runner_on_1b_splits = False
    fetch_ohtani_two_way = True

    query_lower = query.lower()

    if "打者" in query_lower or "ホームラン" in query_lower or "打率" in query_lower or "ops" in query_lower or "rbi" in query_lower or "sb" in query_lower:
        fetch_batting_leaderboard = True
    if "投手" in query_lower or "era" in query_lower or "奪三振" in query_lower or "whip" in query_lower or "fip" in query_lower:
        fetch_pitching_leaderboard = True
    if "risp" in query_lower or "得点圏" in query_lower or "チャンス" in query_lower:
        fetch_risp_splits = True
        fetch_batting_leaderboard = True # RISPなら打者も必要
    if "満塁" in query_lower or "bases loaded" in query_lower or "チャンス" in query_lower:
        fetch_bases_loaded_splits = True
        fetch_batting_leaderboard = True # 満塁なら打者も必要
    if "1塁" in query_lower or "runner on 1b" in query_lower:
        fetch_runner_on_1b_splits = True
        fetch_batting_leaderboard = True # 1塁なら打者も必要
    # if ("Shohei Ohtani" in query_lower or "大谷翔平" in query_lower) and ("二刀流" in query_lower or "登板日" in query_lower or "翌試合" in query_lower):
    #     fetch_ohtani_two_way = True

    # # ★★★ 変更点1: seasonがNoneの場合、過去数年分のリーダーボードデータを取得 ★★★
    # # 目的: LLMが複数年の質問に答えられるように、関連する複数年のデータを提供する
    # seasons_to_fetch = []
    # if season is None: # 「全シーズン」が選択された場合
    #     # 例として、過去5年分のデータを取得
    #     seasons_to_fetch = list(range(current_year, current_year - 5, -1))
    # else: # 特定のシーズンが選択された場合
    #     seasons_to_fetch = [season]

    # ★★★ 変更点2: 必要なデータのみをフェッチし、data_for_llmに格納 ★★★
    seasons_to_fetch_for_leaderboards = []
    if season is None: # 「全シーズン」が選択された場合
        seasons_to_fetch_for_leaderboards = list(range(current_year, current_year - 5, -1)) # 過去5年分
    else:
        seasons_to_fetch_for_leaderboards = [season]

    # ========================== Season Batting and Pitching Leaderboards ==========================
    if fetch_batting_leaderboard:
        all_batting_leaderboards_for_llm = []
        for s in seasons_to_fetch_for_leaderboards:
    # for s in seasons_to_fetch:
            # 打者リーダーボードの取得
            batting_leaderboard = get_batting_leaderboard(
                season=s,
                league="MLB",
                min_pa=280, 
                metric_order="ops"
            )
            if batting_leaderboard:
                for player in batting_leaderboard:
                    all_batting_leaderboards_for_llm.append({
                        "name": player.name,
                        "team": player.team,
                        "season": player.season,
                        "ops": player.ops,
                        "hr": player.hr,
                        "h": player.h,
                        "r": player.r,
                        "sb": player.sb,
                        "bb": player.bb,
                        "so": player.so,
                        "avg": player.avg,
                        "rbi": player.rbi,
                        "wrcplus": player.wrcplus,
                        "war": player.war,
                        "woba": player.woba,
                        "obp": player.obp,
                        "slg": player.slg,
                        "iso": player.iso,
                        "batting_average_at_risp": player.batting_average_at_risp,
                        "slugging_percentage_at_risp": player.slugging_percentage_at_risp,
                        "home_runs_at_risp": player.home_runs_at_risp
                    })
        data_for_llm["batting_leaderboard"] = all_batting_leaderboards_for_llm

    if fetch_pitching_leaderboard:
        all_pitching_leaderboards_for_llm = []
        for s in seasons_to_fetch_for_leaderboards:
            # 投手リーダーボードの取得
            pitching_leaderboard = get_pitching_leaderboard(
                season=s,
                league="MLB",
                min_ip=50,
                metric_order="era"
            )
            if pitching_leaderboard:
                for player in pitching_leaderboard:
                    all_pitching_leaderboards_for_llm.append({
                        "name": player.name,
                        "team": player.team,
                        "season": player.season,
                        "era": player.era,
                        "so": player.so,
                        "whip": player.whip,
                        "fip": player.fip,
                        "k_9": player.k_9,
                        "bb_9": player.bb_9,
                        "k_bb": player.k_bb,
                        "avg": player.avg,
                        "war": player.war,
                        "ip": player.ip,
                        "hr": player.hr,
                        "bb": player.bb,
                        "sv": player.sv,
                        "r": player.r,
                        "w": player.w,
                        "l": player.l,
                        "h": player.h
                    })
        data_for_llm["pitching_leaderboard"] = all_pitching_leaderboards_for_llm

    # batting_leaderboard_str = "打者リーダーボードデータはありません。"
    # if all_batting_leaderboards_for_llm:
    #     batting_leaderboard_str = f"打者リーダーボード:\n{json.dumps(all_batting_leaderboards_for_llm, indent=2, ensure_ascii=False)}"

    # pitching_leaderboard_str = "投手リーダーボードデータはありません。"
    # if all_pitching_leaderboards_for_llm:
    #     pitching_leaderboard_str = f"投手リーダーボード:\n{json.dumps(all_pitching_leaderboards_for_llm, indent=2, ensure_ascii=False)}"
    
    # ========================== Batting Splits Leaderboards [RISP] ===========================
    if fetch_risp_splits:
        risp_batting_splits_leaderboards_for_llm = []
        for s in seasons_to_fetch_for_leaderboards:
    # for s in seasons_to_fetch:
            # 打者のスプリットデータを取得
            batting_splits_leaderboards_risp = get_batter_split_stats_leaderboard(
                season=s,
                league="MLB",
                min_pa=280,  # 最低打席数を設定
                split_type="RISP"  # RISPスプリットを取得
            )
            if batting_splits_leaderboards_risp:
                for player in batting_splits_leaderboards_risp:
                    risp_batting_splits_leaderboards_for_llm.append({
                        "batter_name": player.batter_name,
                        "game_year": player.game_year,
                        "team": player.team,
                        "league": player.league,
                        "homeruns_at_risp": player.homeruns_at_risp,
                        "triples_at_risp": player.triples_at_risp,
                        "doubles_at_risp": player.doubles_at_risp,
                        "singles_at_risp": player.singles_at_risp,
                        "hits_at_risp": player.hits_at_risp,
                        "bb_hbp_at_risp": player.bb_hbp_at_risp,
                        "avg_at_risp": player.avg_at_risp,
                        "obp_at_risp": player.obp_at_risp,
                        "slg_at_risp": player.slg_at_risp,
                        "ops_at_risp": player.ops_at_risp
                    })
        data_for_llm["risp_batting_splits_leaderboard"] = risp_batting_splits_leaderboards_for_llm
                
    # batting_splits_leaderboard_risp_str = " No RISP batting splits leaderboard data available."
    # if risp_batting_splits_leaderboards_for_llm:
    #     batting_splits_leaderboard_risp_str = f"RISP打者スプリットリーダーボード:\n{json.dumps(risp_batting_splits_leaderboards_for_llm, indent=2, ensure_ascii=False)}"

    # ========================== Batting Splits Leaderboards [Bases Loaded] ===========================
    if fetch_bases_loaded_splits:
        bases_loaded_batting_splits_leaderboards_for_llm = []
        for s in seasons_to_fetch_for_leaderboards:
    # for s in seasons_to_fetch:
            # 打者のスプリットデータを取得
            batting_splits_leaderboards_bases_loaded = get_batter_split_stats_leaderboard(
                season=s,
                league="MLB",
                min_pa=280,  # 最低打席数を設定
                split_type="Bases Loaded"  # Bases Loadedスプリットを取得
            )
            if batting_splits_leaderboards_bases_loaded:
                for player in batting_splits_leaderboards_bases_loaded:
                    bases_loaded_batting_splits_leaderboards_for_llm.append({
                        "batter_name": player.batter_name,
                        "game_year": player.game_year,
                        "team": player.team,
                        "league": player.league,
                        "grandslam": player.grandslam,
                        "ab_at_bases_loaded": player.ab_at_bases_loaded,
                        "hits_at_bases_loaded": player.hits_at_bases_loaded,
                        "doubles_at_bases_loaded": player.doubles_at_bases_loaded,
                        "triples_at_bases_loaded": player.triples_at_bases_loaded,
                        "singles_at_bases_loaded": player.singles_at_bases_loaded,
                        "bb_hbp_at_bases_loaded": player.bb_hbp_at_bases_loaded,
                        "so_at_bases_loaded": player.so_at_bases_loaded,
                        "avg_at_bases_loaded": player.avg_at_bases_loaded,
                        "obp_at_bases_loaded": player.obp_at_bases_loaded,
                        "slg_at_bases_loaded": player.slg_at_bases_loaded,
                        "ops_at_bases_loaded": player.ops_at_bases_loaded
                    })
        data_for_llm["bases_loaded_batting_splits_leaderboard"] = bases_loaded_batting_splits_leaderboards_for_llm
                
    # bases_loaded_batting_splits_leaderboard_str = " No Bases Loaded batting splits leaderboard data available."
    # if bases_loaded_batting_splits_leaderboards_for_llm:
    #     bases_loaded_batting_splits_leaderboard_str = f"Bases Loaded打者スプリットリーダーボード:\n{json.dumps(bases_loaded_batting_splits_leaderboards_for_llm, indent=2, ensure_ascii=False)}"

    # ========================== Batting Splits Leaderboards [Runner only on 1st] ===========================
    if fetch_runner_on_1b_splits:
        runner_on_first_batting_splits_leaderboards_for_llm = []
        for s in seasons_to_fetch_for_leaderboards:
    # for s in seasons_to_fetch:
            # 打者のスプリットデータを取得
            batting_splits_leaderboards_1b_only = get_batter_split_stats_leaderboard(
                season=s,
                league="MLB",
                min_pa=280,  # 最低打席数を設定
                split_type="Runner on 1B"  # 1塁にランナーのみのスプリットを取得
            )
            if batting_splits_leaderboards_1b_only:
                for player in batting_splits_leaderboards_1b_only:
                    runner_on_first_batting_splits_leaderboards_for_llm.append({
                        "batter_name": player.batter_name,
                        "game_year": player.game_year,
                        "team": player.team,
                        "league": player.league,
                        "homeruns_at_runner_on_1b": player.homeruns_at_runner_on_1b,
                        "triples_at_runner_on_1b": player.triples_at_runner_on_1b,
                        "doubles_at_runner_on_1b": player.doubles_at_runner_on_1b,
                        "singles_at_runner_on_1b": player.singles_at_runner_on_1b,
                        "hits_at_runner_on_1b": player.hits_at_runner_on_1b,
                        "ab_at_runner_on_1b": player.ab_at_runner_on_1b,
                        "so_at_runner_on_1b": player.so_at_runner_on_1b,
                        "bb_hbp_at_runner_on_1b": player.bb_hbp_at_runner_on_1b,
                        "avg_at_runner_on_1b": player.avg_at_runner_on_1b,
                        "obp_at_runner_on_1b": player.obp_at_runner_on_1b,
                        "slg_at_runner_on_1b": player.slg_at_runner_on_1b,
                        "ops_at_runner_on_1b": player.ops_at_runner_on_1b
                    })
        data_for_llm["runner_on_1b_batting_splits_leaderboard"] = runner_on_first_batting_splits_leaderboards_for_llm
    
    # runner_on_first_batting_splits_leaderboard_str = " No Runner on 1B batting splits leaderboard data available."
    # if runner_on_first_batting_splits_leaderboards_for_llm:
    #     runner_on_first_batting_splits_leaderboard_str = f"Runner on 1B打者スプリットリーダーボード:\n{json.dumps(runner_on_first_batting_splits_leaderboards_for_llm, indent=2, ensure_ascii=False)}"


    # ========================== Shohei Ohtani's Two-Way Player Stats ==========================
    if fetch_ohtani_two_way:
        ohtani_two_way_stats = get_ohtani_two_way_stats(season=season)
        if ohtani_two_way_stats:
            logger.debug(f"Fetched Ohtani two-way stats for season {season}: {ohtani_two_way_stats}")
            ohtani_two_way_stats_for_llm_filtered = ohtani_two_way_stats # リストをそのまま代入
            data_for_llm["shohei_ohtani_two_way_stats"] = ohtani_two_way_stats_for_llm_filtered
        else:
            ohtani_two_way_stats_for_llm_filtered = [] # データがない場合は空リスト
            data_for_llm["shohei_ohtani_two_way_stats"] = ohtani_two_way_stats_for_llm_filtered
    
    # Debugging: Log the data prepared for LLM
    logger.debug(f"Data prepared for LLM: {json.dumps(data_for_llm, indent=2, ensure_ascii=False)}")

    # # Debugging: Log the fetched Ohtani stats
    # if ohtani_two_way_stats:
    #     logger.debug(f"Fetched Ohtani two-way stats for season {season}: {ohtani_two_way_stats}")
    #     ohtani_two_way_stats_for_llm = ohtani_two_way_stats # リストをそのまま代入
    # else:
    #     ohtani_two_way_stats_for_llm = [] # データがない場合は空リスト
    
    # # # Debugging: Log the Ohtani two-way stats for LLM
    # # logger.debug(f"Shohei Ohtani two-way stats for LLM: {ohtani_two_way_stats_for_llm}")

    # ohtani_two_way_stats_str = "No Shohei Ohtani two-way player stats available."
    # if ohtani_two_way_stats_for_llm:
    #     ohtani_two_way_stats_str = f"Shohei Ohtani Two-Way Player Stats:\n{json.dumps(ohtani_two_way_stats_for_llm, indent=2, ensure_ascii=False)}"

    # LLMへのプロンプト構築
    prompt_data_str = json.dumps(data_for_llm, indent=2, ensure_ascii=False) # ★★★ 変更点3: 必要なデータのみをJSON文字列化 ★★★

    # LLMへのプロンプト構築
    prompt = f"""
    あなたはMLBのデータアナリストです。以下のデータに基づいて、ユーザーの質問に回答してください。
    質問の意図を理解し、提供されたデータから関連する情報を抽出し、簡潔に日本語で回答してください。
    もし提供されたデータに質問の答えが見つからない場合、「提供されたデータからは回答できません」と明確に述べてください。

    ---
    ユーザーの質問: {query}

    提供データ:
    {prompt_data_str}
    ---

    回答:
    """

    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set. Please set it as an environment variable.")
        return "APIキーが設定されていないため、AIによる分析はできません。"

    GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    # 打者リーダーボードデータ:
    # {batting_leaderboard_str}

    # 投手リーダーボードデータ:
    # {pitching_leaderboard_str}

    # RISP打者スプリットリーダーボードデータ:
    # {batting_splits_leaderboard_risp_str}

    # Bases Loaded打者スプリットリーダーボードデータ:
    # {bases_loaded_batting_splits_leaderboard_str}

    # Runner on 1B打者スプリットリーダーボードデータ:
    # {runner_on_first_batting_splits_leaderboard_str}

    # Shohei Ohtaniの二刀流選手データ:
    # {ohtani_two_way_stats_str}

    try:
        response = requests.post(GEMINI_API_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()

        if result.get("candidates") and result["candidates"][0].get("content") and result["candidates"][0]["content"].get("parts"):
            generated_text = result["candidates"][0]["content"]["parts"][0]["text"]
            formatted_text = generated_text.replace('\n', '<br>')
            return formatted_text
        else:
            logger.warning(f"Gemini API did not return expected content for query: {query}")
            return "AIによる回答を取得できませんでした。"
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Gemini API for query {query}: {e}", exc_info=True)
        return "AIによる回答中にエラーが発生しました。"
    except Exception as e:
        logger.error(f"An unexpected error occurred during AI response generation for query {query}: {e}", exc_info=True)
        return "AIによる回答中に予期せぬエラーが発生しました。"

