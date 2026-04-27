"""
Shadow Comparison Logger Service
シャドー評価のペア比較ログを BigQuery に非同期書き込みするサービス。

設計方針:
- llm_logger_service.py と同じ「別スレッド + daemon=True」パターンで非同期書き込み
- 例外は内部で握り潰し、本番フローには絶対に伝播させない（シャドー評価の鉄則）
- JSON カラム（active_output / shadow_output）には dict を json.dumps で文字列化して渡す
"""

import uuid
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from google.cloud import bigquery
import json
import logging

from backend.app.config.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
PROJECT_ID = settings.gcp_project_id
DATASET_ID = settings.bigquery_dataset_id
TABLE_ID = settings.bigquery_shadow_comparisons_table_id
FULL_TABLE_ID = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"


def _serialize_for_bq_json(value: Any) -> Optional[str]:
    """
    BigQuery の JSON カラムに insert_rows_json で渡す形式に変換する。

    - None はそのまま None を返す
    - それ以外は常に json.dumps で変換する。
      str をそのまま返すと BQ が「invalid JSON literal」エラーを出すため、
      文字列も json.dumps して JSON文字列（ダブルクォート付き）にする。
    """
    if value is None:
        return None
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError) as e:
        logger.warning(f"Failed to serialize value for BQ JSON: {e}")
        return json.dumps({"_serialize_error": str(e)}, ensure_ascii=False)


class ShadowComparisonEntry:
    """1回のシャドー評価のペア比較エントリ"""

    def __init__(self):
        self.comparison_id: str = str(uuid.uuid4())
        self.request_id: str = ""
        self.session_id: Optional[str] = None
        self.user_id: Optional[str] = None
        self.user_query: str = ""
        self.query_type: Optional[str] = None
        self.prompt_name: str = ""

        # Active 側
        self.active_version: str = ""
        self.active_output: Optional[Any] = None
        self.active_latency_ms: Optional[float] = None
        self.active_cost_usd: Optional[float] = None

        # Shadow 側
        self.shadow_version: str = ""
        self.shadow_output: Optional[Any] = None
        self.shadow_latency_ms: Optional[float] = None
        self.shadow_cost_usd: Optional[float] = None
        self.shadow_error: Optional[str] = None

        # 比較メタ
        self.outputs_match: Optional[bool] = None

        self.created_at: str = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """BigQuery INSERT 用の辞書に変換"""
        return {
            "comparison_id": self.comparison_id,
            "request_id": self.request_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "user_query": self.user_query[:2000] if self.user_query else "",
            "query_type": self.query_type,
            "prompt_name": self.prompt_name,
            "active_version": self.active_version,
            "active_output": _serialize_for_bq_json(self.active_output),
            "active_latency_ms": self.active_latency_ms,
            "active_cost_usd": self.active_cost_usd,
            "shadow_version": self.shadow_version,
            "shadow_output": _serialize_for_bq_json(self.shadow_output),
            "shadow_latency_ms": self.shadow_latency_ms,
            "shadow_cost_usd": self.shadow_cost_usd,
            "shadow_error": self.shadow_error[:500] if self.shadow_error else None,
            "outputs_match": self.outputs_match,
            "created_at": self.created_at,
        }


class ShadowLoggerService:
    """シャドー比較ログを BigQuery に非同期書き込みするサービス"""

    def __init__(self):
        self.client: Optional[bigquery.Client] = None
        try:
            self.client = bigquery.Client(project=PROJECT_ID)
            logger.info(f"ShadowLoggerService initialized for {FULL_TABLE_ID}")
        except Exception as e:
            logger.warning(f"Failed to initialize ShadowLoggerService: {e}")

    def log(self, entry: ShadowComparisonEntry):
        """ペア比較ログを別スレッドで書き込み（メイン応答をブロックしない）"""
        if not self.client:
            logger.warning("ShadowLoggerService not initialized, skipping log")
            return

        thread = threading.Thread(
            target=self._write_to_bigquery,
            args=(entry.to_dict(),),
            daemon=True,
        )
        thread.start()

    def _write_to_bigquery(self, row_data: Dict[str, Any]):
        try:
            errors = self.client.insert_rows_json(FULL_TABLE_ID, [row_data])
            if errors:
                logger.error(f"Shadow comparison insert errors: {errors}")
            else:
                logger.debug(f"Shadow comparison written: {row_data['comparison_id']}")
        except Exception as e:
            # ロギング失敗はアプリを止めない（シャドー評価の鉄則）
            logger.error(f"Failed to write shadow comparison: {e}")


# Singleton
_shadow_logger_instance: Optional[ShadowLoggerService] = None


def get_shadow_logger() -> ShadowLoggerService:
    """シングルトンの ShadowLoggerService を取得"""
    global _shadow_logger_instance
    if _shadow_logger_instance is None:
        _shadow_logger_instance = ShadowLoggerService()
    return _shadow_logger_instance
