"""
Trace Expectation Service (HITL フライホイール)

Trace Viewer で付与された「正解はこうあるべきだった」という期待値を
BigQuery `trace_expectations` に書き込む。

設計方針:
- `trace_label_service` と同じ **追記のみ**。付け直しは新しい行の INSERT で
  表現し、読み出し側が `created_at` の最新を採用する。
  「いつ判断が変わったか」を残すため。
- ラベル付与と同じく UI からの明示操作なので **同期書き込み** とし、
  失敗は例外として呼び出し元に返す。
- `query_type` / `metrics` の妥当性は **既存の QUERY_TYPE_CONFIG / METRIC_MAP**
  に対して検証する。新しい辞書を作らない。UI が選択肢から選ぶ設計でも API は
  直接叩けるため、サーバ側でも必ず弾く。"TODO" のような値が golden に流れ込むと
  CI が意味不明な理由で落ちる。
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from google.cloud import bigquery

from backend.app.config.query_maps import METRIC_MAP
from backend.app.config.settings import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()
PROJECT_ID = _settings.gcp_project_id
DATASET_ID = _settings.bigquery_dataset_id
EXPECTATIONS_TABLE = f"{PROJECT_ID}.{DATASET_ID}.trace_expectations"

_client: Optional[bigquery.Client] = None


def _get_client() -> bigquery.Client:
    global _client
    if _client is None:
        _client = bigquery.Client(project=PROJECT_ID)
    return _client


# 語彙の唯一のソースは **tool schema の enum** である。
#
# QUERY_TYPE_CONFIG を直接展開してはいけない。QUERY_TYPE_CONFIG は splits を
# 2 階層で持つが (batting_splits -> risp -> {...})、LLM が実際に出力するのは
# query_type="batting_splits" + split_type="risp" の 2 フィールドであり、
# golden_dataset もその形で書かれている。階層をドット結合すると
# ("batting_splits.risp") 既存 golden とも評価スクリプトとも噛み合わない。
#
# import は遅延させる。_genai_schemas は google.genai と glossary_rag_service を
# 引き込むため、モジュール読み込み時に走らせたくない。
_VOCAB_CACHE: Optional[Dict[str, Any]] = None

# "main_stats" は METRIC_MAP に無いが「主要スタッツ一式」を表す特殊キーワードで、
# base_engine が実際に展開する (backend/app/services/analytics/base_engine.py)。
# golden_dataset でも使われているため候補に含める。
MAIN_STATS_KEYWORD = "main_stats"


def _vocab() -> Dict[str, Any]:
    """tool schema から query_type / split_type の語彙を導出する。"""
    global _VOCAB_CACHE
    if _VOCAB_CACHE is not None:
        return _VOCAB_CACHE

    from backend.app.services.tools._genai_schemas import CHAT_TOOL_DECLARATIONS

    query_types: List[str] = []
    split_types: Dict[str, List[str]] = {}
    for decl in CHAT_TOOL_DECLARATIONS:
        props = getattr(decl.parameters, "properties", None)
        if not props:
            continue
        qt = getattr(props.get("query_type"), "enum", None) or []
        st = getattr(props.get("split_type"), "enum", None) or []
        query_types.extend(qt)
        # splits 系 query_type だけが split_type を取る。同じツールの enum を割り当てる。
        for t in qt:
            if t.endswith("_splits"):
                split_types[t] = sorted(st)

    _VOCAB_CACHE = {
        "query_types": sorted(set(query_types)),
        "split_types": split_types,
    }
    return _VOCAB_CACHE


def valid_query_types() -> List[str]:
    """query_type の候補。tool schema の enum が正。"""
    return _vocab()["query_types"]


def valid_split_types() -> Dict[str, List[str]]:
    """query_type -> split_type 候補。splits 系以外は含まれない。"""
    return _vocab()["split_types"]


def valid_metrics() -> List[str]:
    """metrics_contains に指定できる値。METRIC_MAP + 特殊キーワード。"""
    return sorted(set(METRIC_MAP.keys()) | {MAIN_STATS_KEYWORD})


def _validate(
    query_type: str, metrics: List[str], split_type: Optional[str]
) -> None:
    if query_type not in set(valid_query_types()):
        raise ValueError(
            f"unknown query_type: {query_type}. valid={valid_query_types()}"
        )

    allowed_splits = valid_split_types().get(query_type)
    if split_type:
        if not allowed_splits:
            raise ValueError(f"{query_type} does not take split_type")
        if split_type not in allowed_splits:
            raise ValueError(
                f"unknown split_type for {query_type}: {split_type}. "
                f"valid={allowed_splits}"
            )

    unknown = [m for m in metrics if m not in set(valid_metrics())]
    if unknown:
        raise ValueError(f"unknown metrics: {unknown}")


def put_expectation(
    trace_id: str,
    user_query: str,
    query_type: str,
    metrics: Optional[List[str]] = None,
    split_type: Optional[str] = None,
    player_name: Optional[str] = None,
    season: Optional[int] = None,
    order_by: Optional[str] = None,
    expected_no_tool: bool = False,
    request_id: Optional[str] = None,
    note: Optional[str] = None,
    created_by: Optional[str] = None,
) -> Dict[str, Any]:
    """trace に期待値を付与する（追記）。

    Args:
        expected_no_tool: 「ツールを呼ばず断るのが正解」のケース。
            should_have_abstained ラベルに対応する。True のときは
            query_type 以下の検証をせず、抑制すべきだった事実のみ記録する。

    Raises:
        ValueError: query_type / split_type / metrics が既存定義に無い場合
        RuntimeError: BigQuery への INSERT が失敗した場合
    """
    metrics = metrics or []
    if not expected_no_tool:
        _validate(query_type, metrics, split_type)

    row = {
        "expectation_id": str(uuid.uuid4()),
        "trace_id": trace_id,
        "request_id": request_id or None,
        "user_query": user_query,
        "query_type": query_type,
        "split_type": split_type or None,
        "order_by": order_by or None,
        "expected_no_tool": bool(expected_no_tool),
        # 既存の tool_calls 列と同じく JSON 文字列で持つ。REPEATED にすると
        # Streaming Insert のスキーマ変更コストが上がるため。
        "metrics": json.dumps(metrics, ensure_ascii=False),
        "player_name": player_name or None,
        "season": season,
        "note": (note or None) and note[:1000],
        "created_by": created_by or "unknown",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    errors = _get_client().insert_rows_json(EXPECTATIONS_TABLE, [row])
    if errors:
        logger.error(f"trace_expectations insert errors: {errors}")
        raise RuntimeError(f"failed to insert expectation: {errors}")

    logger.info(f"trace expectation written: {trace_id} -> {query_type}")
    return {**row, "metrics": metrics}


def _row_to_dict(r: Any) -> Dict[str, Any]:
    try:
        metrics = json.loads(r["metrics"] or "[]")
    except (TypeError, ValueError):
        logger.warning(f"failed to parse metrics JSON for trace {r['trace_id']}")
        metrics = []
    return {
        "trace_id": r["trace_id"],
        "request_id": r["request_id"],
        "user_query": r["user_query"],
        "query_type": r["query_type"],
        "split_type": r["split_type"],
        "metrics": metrics,
        "player_name": r["player_name"],
        "season": r["season"],
        "order_by": r["order_by"],
        "expected_no_tool": bool(r["expected_no_tool"]),
        "note": r["note"],
        "created_by": r["created_by"],
        "created_at": r["created_at"].isoformat() if r["created_at"] else None,
    }


def get_latest_expectation(trace_id: str) -> Optional[Dict[str, Any]]:
    """trace に付与された最新の期待値を返す。無ければ None。"""
    query = f"""
    SELECT trace_id, request_id, user_query, query_type, split_type, metrics,
           player_name, season, order_by, expected_no_tool,
           note, created_by, created_at
    FROM `{EXPECTATIONS_TABLE}`
    WHERE trace_id = @trace_id
    ORDER BY created_at DESC
    LIMIT 1
    """
    try:
        rows = list(
            _get_client()
            .query(
                query,
                job_config=bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("trace_id", "STRING", trace_id)
                    ]
                ),
            )
            .result()
        )
    except Exception as e:
        # テーブル未作成でも trace 本体は読めるようにする（labels と同じ方針）
        logger.warning(f"trace_expectations read failed (suppressed): {e}")
        return None
    return _row_to_dict(rows[0]) if rows else None


def list_expectations(days: int = 90) -> List[Dict[str, Any]]:
    """昇格候補となる期待値を trace 単位で最新 1 件ずつ返す。"""
    query = f"""
    SELECT trace_id, request_id, user_query, query_type, split_type, metrics,
           player_name, season, order_by, expected_no_tool,
           note, created_by, created_at
    FROM `{EXPECTATIONS_TABLE}`
    WHERE DATE(created_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL @days DAY)
    QUALIFY ROW_NUMBER() OVER (PARTITION BY trace_id ORDER BY created_at DESC) = 1
    ORDER BY created_at ASC
    """
    rows = (
        _get_client()
        .query(
            query,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("days", "INT64", days)
                ]
            ),
        )
        .result()
    )
    return [_row_to_dict(r) for r in rows]
