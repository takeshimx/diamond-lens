"""
Trace Query Service (P0-1 Trace Viewer)

`llm_interaction_logs` を trace_id 単位で束ね、エージェントの実行経路を
時系列のステップ列として返す。

設計方針:
- usage_stats_service と同じく **1 リクエスト 1 クエリ** に寄せ、BQ の
  round-trip とスキャン回数を抑える。
- `node IS NOT NULL` の行のみを trace 対象とする。node は Trace Viewer 用に
  後から追加したカラムであり、これが埋まっている行だけが
  「エージェントのステップとして記録された行」である。
- ラベルは別テーブル `trace_labels` に持ち、LEFT JOIN で最新の 1 件を引く。
  ログ本体を書き換えないことで、ラベルの付け直しがログの改竄にならない。
"""

import json
import logging
from typing import Any, Dict, List, Optional

from google.cloud import bigquery

from backend.app.config.settings import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()
PROJECT_ID = _settings.gcp_project_id
DATASET_ID = _settings.bigquery_dataset_id
LOGS_TABLE = f"{PROJECT_ID}.{DATASET_ID}.llm_interaction_logs"
LABELS_TABLE = f"{PROJECT_ID}.{DATASET_ID}.trace_labels"

_client: Optional[bigquery.Client] = None


def _get_client() -> bigquery.Client:
    global _client
    if _client is None:
        _client = bigquery.Client(project=PROJECT_ID)
    return _client


def _parse_tool_calls(raw: Optional[str]) -> Optional[List[Dict[str, Any]]]:
    """tool_calls は STRING 列に JSON 文字列で入っている。壊れていれば None。"""
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else None
    except (TypeError, ValueError):
        logger.warning("failed to parse tool_calls JSON")
        return None


def list_traces(
    days: int = 30,
    limit: int = 100,
    only_unlabeled: bool = False,
    only_failed: bool = False,
) -> List[Dict[str, Any]]:
    """trace の一覧を返す。1 trace = 1 行に集約する。

    Args:
        days: 何日前まで遡るか
        limit: 返す trace 数の上限
        only_unlabeled: True ならラベル未付与の trace のみ
        only_failed: True なら失敗ステップを含む trace のみ
    """
    query = f"""
    WITH steps AS (
      SELECT
        trace_id,
        MIN(timestamp)                                  AS started_at,
        MAX(timestamp)                                  AS ended_at,
        COUNT(*)                                        AS step_count,
        -- LLM 呼び出し回数は model の有無で数える。
        -- iteration 列は経路によって意味が違う（ChatOrchestrator は LLM 呼び出しの
        -- 通し番号、StrategyAgent は reflection の retry_count）ため、
        -- 横断的な指標としては使えない。
        COUNTIF(model IS NOT NULL)                      AS llm_calls,
        MAX(iteration)                                  AS max_iteration,
        COUNTIF(success = FALSE)                         AS failed_steps,
        SUM(IFNULL(estimated_cost_usd, 0))              AS cost_usd,
        SUM(IFNULL(llm_latency_ms, 0))                  AS llm_latency_ms,
        ARRAY_AGG(
          IF(user_query IS NOT NULL AND user_query != '[TOOL_EXECUTION]', user_query, NULL)
          IGNORE NULLS ORDER BY timestamp LIMIT 1
        )                                               AS first_query,
        ARRAY_AGG(DISTINCT node IGNORE NULLS)           AS nodes,
        MAX(session_id)                                 AS session_id,
        MAX(endpoint)                                   AS endpoint
      FROM `{LOGS_TABLE}`
      WHERE node IS NOT NULL
        AND trace_id IS NOT NULL
        AND DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL @days DAY)
      GROUP BY trace_id
    ),
    -- 同じ trace に複数回ラベルが付いた場合は最新の 1 件を採用する
    latest_label AS (
      SELECT trace_id, label, note, labeled_at
      FROM `{LABELS_TABLE}`
      QUALIFY ROW_NUMBER() OVER (PARTITION BY trace_id ORDER BY labeled_at DESC) = 1
    )
    SELECT
      s.trace_id,
      s.started_at,
      s.ended_at,
      s.step_count,
      s.llm_calls,
      s.max_iteration,
      s.failed_steps,
      s.cost_usd,
      s.llm_latency_ms,
      s.first_query[SAFE_OFFSET(0)] AS user_query,
      s.nodes,
      s.session_id,
      s.endpoint,
      l.label,
      l.note,
      l.labeled_at
    FROM steps s
    LEFT JOIN latest_label l USING (trace_id)
    WHERE (@only_unlabeled = FALSE OR l.label IS NULL)
      AND (@only_failed = FALSE OR s.failed_steps > 0)
    ORDER BY s.started_at DESC
    LIMIT @limit
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("days", "INT64", days),
            bigquery.ScalarQueryParameter("limit", "INT64", limit),
            bigquery.ScalarQueryParameter("only_unlabeled", "BOOL", only_unlabeled),
            bigquery.ScalarQueryParameter("only_failed", "BOOL", only_failed),
        ]
    )
    rows = _get_client().query(query, job_config=job_config).result()
    return [
        {
            "trace_id": r["trace_id"],
            "started_at": r["started_at"].isoformat() if r["started_at"] else None,
            "ended_at": r["ended_at"].isoformat() if r["ended_at"] else None,
            "step_count": r["step_count"],
            "llm_calls": r["llm_calls"],
            "max_iteration": r["max_iteration"],
            "failed_steps": r["failed_steps"],
            "cost_usd": float(r["cost_usd"] or 0),
            "llm_latency_ms": float(r["llm_latency_ms"] or 0),
            "user_query": r["user_query"],
            "nodes": list(r["nodes"] or []),
            "session_id": r["session_id"],
            "endpoint": r["endpoint"],
            "label": r["label"],
            "note": r["note"],
            "labeled_at": r["labeled_at"].isoformat() if r["labeled_at"] else None,
        }
        for r in rows
    ]


def get_trace(trace_id: str) -> Dict[str, Any]:
    """1 trace の全ステップを時系列で返す。"""
    query = f"""
    SELECT
      log_id, timestamp, node, iteration, feature, model,
      user_query, response_answer, tool_calls,
      success, error_type, error_message,
      llm_latency_ms, total_latency_ms, bigquery_latency_ms,
      input_tokens, output_tokens, estimated_cost_usd,
      parsed_query_type, parsed_metrics, parsed_player_name, parsed_season,
      is_retry, retry_count, retry_reason,
      user_rating, feedback_category, feedback_reason,
      session_id, request_id, endpoint
    FROM `{LOGS_TABLE}`
    WHERE trace_id = @trace_id
    ORDER BY timestamp ASC
    """
    label_query = f"""
    SELECT label, note, labeled_by, labeled_at
    FROM `{LABELS_TABLE}`
    WHERE trace_id = @trace_id
    ORDER BY labeled_at DESC
    """
    params = [bigquery.ScalarQueryParameter("trace_id", "STRING", trace_id)]
    client = _get_client()

    rows = client.query(
        query, job_config=bigquery.QueryJobConfig(query_parameters=params)
    ).result()

    steps: List[Dict[str, Any]] = []
    summaries: List[Dict[str, Any]] = []
    for r in rows:
        # node が NULL の行 = エンドポイントが書く「リクエスト全体のサマリ行」。
        # timestamp は LLMLogEntry 生成時（リクエスト受信直後）に打たれるため、
        # 中身は最終結果なのに時刻は最古になる。ステップ列に混ぜると順序が壊れるので
        # summary として分離する。
        target = steps if r["node"] else summaries
        target.append({
            "log_id": r["log_id"],
            "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
            "node": r["node"] or "summary",
            "iteration": r["iteration"],
            "feature": r["feature"],
            # model が NULL の行は「LLM を呼んでいないステップ」（ツール実行など）
            "is_llm_call": r["model"] is not None,
            "model": r["model"],
            "user_query": r["user_query"],
            "response_answer": r["response_answer"],
            "tool_calls": _parse_tool_calls(r["tool_calls"]),
            "success": r["success"],
            "error_type": r["error_type"],
            "error_message": r["error_message"],
            "llm_latency_ms": r["llm_latency_ms"],
            "total_latency_ms": r["total_latency_ms"],
            "bigquery_latency_ms": r["bigquery_latency_ms"],
            "input_tokens": r["input_tokens"],
            "output_tokens": r["output_tokens"],
            "estimated_cost_usd": r["estimated_cost_usd"],
            "parsed_query_type": r["parsed_query_type"],
            "parsed_metrics": r["parsed_metrics"],
            "parsed_player_name": r["parsed_player_name"],
            "parsed_season": r["parsed_season"],
            "is_retry": r["is_retry"],
            "retry_count": r["retry_count"],
            "retry_reason": r["retry_reason"],
            "user_rating": r["user_rating"],
            "feedback_category": r["feedback_category"],
            "feedback_reason": r["feedback_reason"],
            "session_id": r["session_id"],
            "request_id": r["request_id"],
            "endpoint": r["endpoint"],
        })

    labels: List[Dict[str, Any]] = []
    try:
        for r in client.query(
            label_query, job_config=bigquery.QueryJobConfig(query_parameters=params)
        ).result():
            labels.append({
                "label": r["label"],
                "note": r["note"],
                "labeled_by": r["labeled_by"],
                "labeled_at": r["labeled_at"].isoformat() if r["labeled_at"] else None,
            })
    except Exception as e:
        # trace_labels が未作成でも trace 本体は読めるようにする
        logger.warning(f"trace_labels read failed (suppressed): {e}")

    # サマリは「最終回答を持つもの」を優先。無ければ最後の1件。
    summary: Optional[Dict[str, Any]] = None
    if summaries:
        with_answer = [s for s in summaries if s.get("response_answer")]
        summary = (with_answer or summaries)[-1]

    return {
        "trace_id": trace_id,
        "steps": steps,
        "summary": summary,
        "labels": labels,
        "current_label": labels[0]["label"] if labels else None,
    }


def compare_traces(trace_id_a: str, trace_id_b: str) -> Dict[str, Any]:
    """2 つの trace をノード単位で並べて返す（run 比較の最小版）。"""
    a = get_trace(trace_id_a)
    b = get_trace(trace_id_b)

    def _summary(t: Dict[str, Any]) -> Dict[str, Any]:
        steps = t["steps"]
        tools: List[str] = []
        for s in steps:
            for tc in (s.get("tool_calls") or []):
                if tc.get("name"):
                    tools.append(tc["name"])
        return {
            "trace_id": t["trace_id"],
            "step_count": len(steps),
            "nodes": [s["node"] for s in steps],
            "tools": tools,
            "failed_steps": sum(1 for s in steps if s.get("success") is False),
            "cost_usd": sum(s.get("estimated_cost_usd") or 0 for s in steps),
            "llm_latency_ms": sum(s.get("llm_latency_ms") or 0 for s in steps),
            "label": t.get("current_label"),
        }

    return {"a": _summary(a), "b": _summary(b), "a_steps": a["steps"], "b_steps": b["steps"]}
