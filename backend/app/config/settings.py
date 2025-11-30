"""
アプリケーション設定の一元管理
環境変数を型安全に管理し、バリデーションを実施
"""
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache
import os
from pathlib import Path


class Settings(BaseSettings):
    """
    アプリケーション設定クラス
    
    pydantic_settingsを使用することで:
    - 環境変数の自動読み込み
    - 型バリデーション
    - デフォルト値の管理
    - IDE補完のサポート
    を実現
    """

    # ============================================================
    # GCP関連設定
    # ============================================================
    gcp_project_id: str
    google_application_credentials: Optional[str] = None

    # ============================================================
    # BigQuery設定
    # ============================================================
    bigquery_dataset_id: str

    # Table IDs
    bigquery_batting_stats_table_id: str = "fact_batting_stats_with_risp"
    bigquery_pitching_stats_table_id: str = "fact_pitching_stats"
    bigquery_dim_players_table_id: str = "dim_players"
    bigquery_batter_offensive_stats_table_id: str = "tbl_batter_offensive_stats_monthly"
    bigquery_batter_performance_by_strike_count_table_id: str = "tbl_batter_performance_by_strike_count"
    bigquery_batter_performance_at_risp_table_id: str = "tbl_batter_performance_risp_monthly"
    bigquery_pitcher_performance_by_inning_table_id: str = "tbl_pitching_performance_by_inning"
    bigquery_team_batting_stats_table_id: str = "fact_team_batting_stats_master"
    bigquery_team_pitching_stats_table_id: str = "fact_team_pitching_stats_master"
    bigquery_batter_split_stats_table_id: str = "tbl_batter_split_stats"
    bigquery_batter_performance_flags_7days_table_id: str = "view_tbl_batter_rolling_vs_season_stats_7_days"
    bigquery_batter_performance_flags_15days_table_id: str = "view_tbl_batter_rolling_vs_season_stats_15_days"

    # ============================================================
    # API Keys
    # ============================================================
    gemini_api_key: str = Field(validation_alias='GEMINI_API_KEY_V2')

    # ============================================================
    # アプリケーション設定
    # ============================================================
    log_level: str = "INFO"
    api_timeout: int = 30
    enable_debug_mode: bool = False

    # ============================================================
    # LLM設定
    # ============================================================
    gemini_model: str = "gemini-2.5-flash"
    gemini_temperature: float = 0.7
    gemini_max_tokens: int = 2000

    # ============================================================
    # BigQueryクエリ設定
    # ============================================================
    bigquery_timeout: int = 60  # seconds
    bigquery_max_results: int = 10000

    class Config:
        """Pydantic設定"""
        # env_file = ".env"
        env_file = str(Path(__file__).resolve().parent.parent.parent.parent / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def get_table_full_name(self, table_id: str) -> str:
        """
        テーブルのフルパスを取得
        
        Args:
            table_id: テーブルID
        
        Returns:
            `project.dataset.table` 形式の文字列
        
        Example:
            >>> settings.get_table_full_name("fact_batting_stats_with_risp")
            "my-project.my-dataset.fact_batting_stats_with_risp"
        """
        return f"{self.gcp_project_id}.{self.bigquery_dataset_id}.{table_id}"
    
    def is_production(self) -> bool:
        """
        本番環境かどうかを判定
        
        Returns:
            本番環境の場合True
        """
        env = os.getenv("ENVIRONMENT", "developmment").lower()
        return env in ["production", "prod"]
    
    def is_development(self) -> bool:
        """
        開発環境かどうかを判定
        
        Returns:
            開発環境の場合True
        """
        return not self.is_production()
    

@lru_cache()
def get_settings() -> Settings:
    """
    設定のシングルトンインスタンスを取得
    
    @lru_cache デコレータにより、初回呼び出し時のみ
    Settingsインスタンスが作成され、以降はキャッシュされる
    
    Returns:
        Settingsインスタンス
    
    Example:
        >>> from app.config.settings import get_settings
        >>> settings = get_settings()
        >>> print(settings.gcp_project_id)
        "my-project-id"
    """
    return Settings()

# ============================================================
# 後方互換性のためのエイリアス
# 既存コードで直接定数を参照している箇所のために残す
# ============================================================

_settings = get_settings()

# 既存のコードで使われている定数
PROJECT_ID = _settings.gcp_project_id
DATASET_ID = _settings.bigquery_dataset_id
BATTING_STATS_TABLE_ID = _settings.bigquery_batting_stats_table_id
PITCHING_STATS_TABLE_ID = _settings.bigquery_pitching_stats_table_id
DIM_PLAYERS_TABLE_ID = _settings.bigquery_dim_players_table_id
BATTING_OFFENSIVE_STATS_TABLE_ID = _settings.bigquery_batter_offensive_stats_table_id
BAT_PERFORMANCE_SC_TABLE_ID = _settings.bigquery_batter_performance_by_strike_count_table_id
BAT_PERFORMANCE_RISP_TABLE_ID = _settings.bigquery_batter_performance_at_risp_table_id
PITCHING_PERFORMANCE_BY_INNING_TABLE_ID = _settings.bigquery_pitcher_performance_by_inning_table_id
TEAM_BATTING_STATS_TABLE_ID = _settings.bigquery_team_batting_stats_table_id
TEAM_PITCHING_STATS_TABLE_ID = _settings.bigquery_team_pitching_stats_table_id
BATTER_SPLIT_STATS_TABLE_ID = _settings.bigquery_batter_split_stats_table_id
BATTER_PERFORMANCE_FLAGS_7DAYS_TABLE_ID = _settings.bigquery_batter_performance_flags_7days_table_id
BATTER_PERFORMANCE_FLAGS_15DAYS_TABLE_ID = _settings.bigquery_batter_performance_flags_15days_table_id
SERVICE_ACCOUNT_KEY_PATH = _settings.google_application_credentials
GEMINI_API_KEY = _settings.gemini_api_key
    
