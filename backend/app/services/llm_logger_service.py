"""
LLM Interaction Logger Service
LLMの入出力を BigQuery に記録するサービス。
非同期でログを書き込むため、メインのレスポンスには影響を与えません。
"""

import os
import uuid
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from google.cloud import bigquery
import json
import logging

logger = logging.getLogger(__name__)

# BigQuery 設定
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "tksm-dash-test-25")
DATASET_ID = os.getenv("BIGQUERY_DATASET_ID", "mlb_analytics_dash_25")
TABLE_ID = "llm_interaction_logs"
FULL_TABLE_ID = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

class LLMLogEntry:
    """1回のLLMインタラクションのログエントリ"""

    def __init__(self):
        self.log_id = str(uuid.uuid4())
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.request_id: Optional[str] = None
        self.session_id: Optional[str] = None
        self.user_query: str = ""
        self.resolved_query: Optional[str] = None
        self.prompt_name: Optional[str] = None
        self.prompt_version: Optional[str] = None
        self.parsed_query_type: Optional[str] = None
        self.parsed_metrics: Optional[str] = None
        self.parsed_player_name: Optional[str] = None
        self.parsed_season: Optional[int] = None
        self.routing_result: Optional[str] = None
        self.response_answer: Optional[str] = None
        self.response_has_table: bool = False
        self.response_has_chart: bool = False
        self.success: bool = True
        self.error_type: Optional[str] = None
        self.error_message: Optional[str] = None
        self.llm_latency_ms: Optional[float] = None
        self.total_latency_ms: Optional[float] = None
        self.bigquery_latency_ms: Optional[float] = None
        self.endpoint: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """BigQuery INSERT 用の辞書に変換"""
        return {
            "log_id": self.log_id,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
            "session_id": self.session_id,
            "user_query": self.user_query,
            "resolved_query": self.resolved_query,
            "prompt_name": self.prompt_name,
            "prompt_version": self.prompt_version,
            "parsed_query_type": self.parsed_query_type,
            "parsed_metrics": self.parsed_metrics,
            "parsed_player_name": self.parsed_player_name,
            "parsed_season": self.parsed_season,
            "routing_result": self.routing_result,
            # 回答テキストは長くなりすぎないよう先頭500文字に制限
            "response_answer": self.response_answer[:500] if self.response_answer else None,
            "response_has_table": self.response_has_table,
            "response_has_chart": self.response_has_chart,
            "success": self.success,
            "error_type": self.error_type,
            "error_message": self.error_message[:500] if self.error_message else None,
            "llm_latency_ms": self.llm_latency_ms,
            "total_latency_ms": self.total_latency_ms,
            "bigquery_latency_ms": self.bigquery_latency_ms,
            "endpoint": self.endpoint,
        }


class LLMLoggerService:
    """LLM ログを BigQuery に非同期書き込みするサービス"""

    def __init__(self):
        self.client: Optional[bigquery.Client] = None
        try:
            self.client = bigquery.Client(project=PROJECT_ID)
            logger.info(f"LLMLoggerService initialized for {FULL_TABLE_ID}")
        except Exception as e:
            logger.warning(f"Failed to initialize LLMLoggerService: {e}")
    
    def log(self, entry: LLMLogEntry):
        """
        ログエントリを非同期で BigQuery に書き込む。
        メインのAPIレスポンスをブロックしないよう、別スレッドで実行する。
        """
        if not self.client:
            logger.warning("LLMLoggerService not initialized, skipping log")
            return
        
        # 別スレッドで書き込み（レスポンス速度に影響を与えない）
        thread = threading.Thread(
            target=self._write_to_bigquery,
            args=(entry.to_dict(),),
            daemon=True # メインプロセス終了時に自動的に終了
        )
        thread.start()
    
    def _write_to_bigquery(self, row_data: Dict[str, Any]):
        """BigQuery にRow を挿入（内部用）"""
        try:
            errors = self.client.insert_rows_json(
                FULL_TABLE_ID,
                [row_data]
            )
            if errors:
                logger.error(f"BigQuery insert errors: {errors}")
            else:
                logger.debug(f"LLM log written: {row_data['log_id']}")
        except Exception as e:
            # ロギング失敗はアプリを止めない
            logger.error(f"Failed to write LLM log: {e}")

# Singleton instance
_logger_instance: Optional[LLMLoggerService] = None

def get_llm_logger() -> LLMLoggerService:
    """シングルトンの LLMLoggerService を取得"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = LLMLoggerService()
    return _logger_instance
