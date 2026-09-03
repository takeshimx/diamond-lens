"""
Trace Label Service (P0-1 Trace Viewer)

trace 単位の失敗ラベルを BigQuery `trace_labels` に書き込む。

設計方針:
- llm_logger_service / shadow_logger_service と同じ「別スレッド + daemon」パターン。
  ただしラベル付与は UI からの明示操作であり、書き込み結果をユーザーに返す必要が
  あるため **同期書き込み** とし、失敗は例外として呼び出し元に返す。
- ラベルは追記のみ。付け直しは新しい行の INSERT で表現し、読み出し側が
  labeled_at の最新を採用する。過去のラベル履歴を消さないことで、
  「いつ判断が変わったか」を後から追える。
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from google.cloud import bigquery

from backend.app.config.settings import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()
PROJECT_ID = _settings.gcp_project_id
DATASET_ID = _settings.bigquery_dataset_id
LABELS_TABLE = f"{PROJECT_ID}.{DATASET_ID}.trace_labels"

# ラベル軸。UI (frontend/src/constants/traceLabels.js) と対で管理する。
# 追加するときは必ず両方を更新すること。
VALID_LABELS: List[str] = [
    "correct",
    "wrong_tool",
    "wrong_params",
    "right_answer_wrong_path",
    "should_have_abstained",
    "retrieval_miss",
    "tool_error",
]

_client: Optional[bigquery.Client] = None


def _get_client() -> bigquery.Client:
    global _client
    if _client is None:
        _client = bigquery.Client(project=PROJECT_ID)
    return _client


def put_label(
    trace_id: str,
    label: str,
    note: Optional[str] = None,
    labeled_by: Optional[str] = None,
) -> Dict[str, Any]:
    """trace にラベルを付与する（追記）。

    Raises:
        ValueError: 未定義のラベルが渡された場合
        RuntimeError: BigQuery への INSERT が失敗した場合
    """
    if label not in VALID_LABELS:
        raise ValueError(f"unknown label: {label}. valid={VALID_LABELS}")

    row = {
        "label_id": str(uuid.uuid4()),
        "trace_id": trace_id,
        "label": label,
        "note": (note or None) and note[:1000],
        "labeled_by": labeled_by or "unknown",
        "labeled_at": datetime.now(timezone.utc).isoformat(),
    }

    errors = _get_client().insert_rows_json(LABELS_TABLE, [row])
    if errors:
        logger.error(f"trace_labels insert errors: {errors}")
        raise RuntimeError(f"failed to insert label: {errors}")

    logger.info(f"trace label written: {trace_id} -> {label}")
    return row
