"""
基本設定、BigQueryクライアント、環境変数の管理
"""
import os
import logging
from google.cloud import bigquery
from google.oauth2 import service_account
from dotenv import load_dotenv

# ロガーの設定
logging.getLogger().handlers = []
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 環境変数の読み込み
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# プロジェクトとデータセットの設定
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
DATASET_ID = os.getenv("BIGQUERY_DATASET_ID")

# テーブルIDの設定
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

# API Keys
SERVICE_ACCOUNT_KEY_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# BigQuery client singleton
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
                _bq_client = bigquery.Client(project=PROJECT_ID)
                logger.info("BigQuery client initialized using default credentials.")
        except Exception as e:
            logger.error(f"Failed to initialize BigQuery client: {e}", exc_info=True)
            raise
    return _bq_client

# Legacy support for direct import
client = get_bq_client()