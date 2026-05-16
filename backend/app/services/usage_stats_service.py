"""
Usage Stats Service
LLM usage / cost ダッシュボード向けの集計クエリを提供する。

ソーステーブル: llm_interaction_logs
判別: WHERE model IS NOT NULL  ← gateway 由来の LLM 呼び出し行のみを対象
(model IS NULL は request-level / feedback 行で別概念)

タイムゾーン: BQ の timestamp は UTC。日次集計のみ Asia/Tokyo に変換。
"""

import os
import logging
from typing import Any, Dict, List

from google.cloud import bigquery

from backend.app.services.bigquery_service import client

logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "tksm-dash-test-25")
DATASET_ID = os.getenv("BIGQUERY_DATASET_ID", "mlb_analytics_dash_25")
TABLE_ID = "llm_interaction_logs"
FULL_TABLE_ID = f"`{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`"

DEFAULT_TZ = "Asia/Tokyo"


def get_dashboard_all(
    target_year: int,
    target_month: int,
    prev_year: int,
    prev_month: int,
    trend_days: int,
    recent_limit: int,
) -> Dict[str, Any]:
    """ダッシュボードに必要な全集計を **単一の BQ クエリ** で取得する。

    実装方針:
      - 1回の round-trip で 6 種類の集計を ARRAY<STRUCT> でネスト返却
      - 直近 90 日に scan を限定（month + prev_month + trend_days を最大カバー）
      - target_month / prev_month / 直近 trend_days のいずれかに該当する行のみ base に残す
    """
    sql = f"""
    WITH base AS (
      SELECT
        log_id,
        timestamp,
        DATE(timestamp, @tz) AS d_jst,
        EXTRACT(YEAR FROM timestamp AT TIME ZONE @tz) AS yr,
        EXTRACT(MONTH FROM timestamp AT TIME ZONE @tz) AS mo,
        feature,
        model,
        IFNULL(input_tokens, 0) AS input_tokens,
        IFNULL(output_tokens, 0) AS output_tokens,
        IFNULL(estimated_cost_usd, 0.0) AS estimated_cost_usd,
        llm_latency_ms,
        success,
        error_type,
        endpoint
      FROM {FULL_TABLE_ID}
      WHERE model IS NOT NULL
        AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
    ),
    target_rows AS (
      SELECT * FROM base WHERE yr = @target_year AND mo = @target_month
    ),
    prev_rows AS (
      SELECT * FROM base WHERE yr = @prev_year AND mo = @prev_month
    ),
    date_range AS (
      SELECT DATE_SUB(CURRENT_DATE(@tz), INTERVAL n DAY) AS date
      FROM UNNEST(GENERATE_ARRAY(0, @days - 1)) AS n
    ),
    daily_agg AS (
      SELECT d_jst AS date,
             COUNT(*) AS invocations,
             SUM(estimated_cost_usd) AS cost_usd,
             SUM(input_tokens + output_tokens) AS tokens
      FROM base
      WHERE d_jst >= DATE_SUB(CURRENT_DATE(@tz), INTERVAL @days - 1 DAY)
      GROUP BY d_jst
    )
    SELECT
      STRUCT(
        @target_year AS year,
        @target_month AS month,
        (SELECT COUNT(*) FROM target_rows) AS total_invocations,
        (SELECT COUNTIF(success = TRUE) FROM target_rows) AS success_count,
        (SELECT IFNULL(SUM(estimated_cost_usd), 0) FROM target_rows) AS total_cost_usd,
        (SELECT IFNULL(SUM(input_tokens), 0) FROM target_rows) AS total_input_tokens,
        (SELECT IFNULL(SUM(output_tokens), 0) FROM target_rows) AS total_output_tokens,
        (SELECT IFNULL(AVG(llm_latency_ms), 0) FROM target_rows) AS avg_latency_ms,
        (SELECT IFNULL(APPROX_QUANTILES(llm_latency_ms, 100)[OFFSET(95)], 0) FROM target_rows) AS p95_latency_ms
      ) AS summary,
      STRUCT(
        @prev_year AS year,
        @prev_month AS month,
        (SELECT COUNT(*) FROM prev_rows) AS total_invocations,
        (SELECT COUNTIF(success = TRUE) FROM prev_rows) AS success_count,
        (SELECT IFNULL(SUM(estimated_cost_usd), 0) FROM prev_rows) AS total_cost_usd,
        (SELECT IFNULL(SUM(input_tokens), 0) FROM prev_rows) AS total_input_tokens,
        (SELECT IFNULL(SUM(output_tokens), 0) FROM prev_rows) AS total_output_tokens,
        (SELECT IFNULL(AVG(llm_latency_ms), 0) FROM prev_rows) AS avg_latency_ms,
        (SELECT IFNULL(APPROX_QUANTILES(llm_latency_ms, 100)[OFFSET(95)], 0) FROM prev_rows) AS p95_latency_ms
      ) AS prev_summary,
      ARRAY(
        SELECT AS STRUCT
          model,
          COUNT(*) AS invocations,
          SUM(estimated_cost_usd) AS cost_usd,
          SUM(input_tokens) AS input_tokens,
          SUM(output_tokens) AS output_tokens
        FROM target_rows
        GROUP BY model
        ORDER BY cost_usd DESC
      ) AS by_model,
      ARRAY(
        SELECT AS STRUCT
          IFNULL(feature, '(unknown)') AS feature,
          COUNT(*) AS invocations,
          SUM(estimated_cost_usd) AS cost_usd,
          SUM(input_tokens) AS input_tokens,
          SUM(output_tokens) AS output_tokens,
          AVG(llm_latency_ms) AS avg_latency_ms
        FROM target_rows
        GROUP BY feature
        ORDER BY cost_usd DESC
      ) AS by_feature,
      ARRAY(
        SELECT AS STRUCT
          r.date AS date,
          IFNULL(a.invocations, 0) AS invocations,
          IFNULL(a.cost_usd, 0.0) AS cost_usd,
          IFNULL(a.tokens, 0) AS tokens
        FROM date_range r
        LEFT JOIN daily_agg a USING (date)
        ORDER BY r.date ASC
      ) AS daily,
      ARRAY(
        SELECT AS STRUCT
          log_id,
          timestamp,
          IFNULL(feature, '(unknown)') AS feature,
          model,
          input_tokens,
          output_tokens,
          estimated_cost_usd,
          llm_latency_ms,
          success,
          error_type,
          endpoint
        FROM base
        ORDER BY timestamp DESC
        LIMIT @recent_limit
      ) AS recent
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("target_year", "INT64", target_year),
            bigquery.ScalarQueryParameter("target_month", "INT64", target_month),
            bigquery.ScalarQueryParameter("prev_year", "INT64", prev_year),
            bigquery.ScalarQueryParameter("prev_month", "INT64", prev_month),
            bigquery.ScalarQueryParameter("days", "INT64", trend_days),
            bigquery.ScalarQueryParameter("recent_limit", "INT64", recent_limit),
            bigquery.ScalarQueryParameter("tz", "STRING", DEFAULT_TZ),
        ]
    )
    rows = list(client.query(sql, job_config=job_config).result())
    if not rows:
        return _empty_dashboard(target_year, target_month, prev_year, prev_month)
    r = rows[0]

    def _summary_to_dict(s):
        return {
            "year": int(s["year"]),
            "month": int(s["month"]),
            "total_invocations": int(s["total_invocations"] or 0),
            "success_count": int(s["success_count"] or 0),
            "total_cost_usd": float(s["total_cost_usd"] or 0),
            "total_input_tokens": int(s["total_input_tokens"] or 0),
            "total_output_tokens": int(s["total_output_tokens"] or 0),
            "avg_latency_ms": float(s["avg_latency_ms"] or 0),
            "p95_latency_ms": float(s["p95_latency_ms"] or 0),
        }

    return {
        "summary": _summary_to_dict(r["summary"]),
        "prev_summary": _summary_to_dict(r["prev_summary"]),
        "by_model": [
            {
                "model": m["model"],
                "invocations": int(m["invocations"] or 0),
                "cost_usd": float(m["cost_usd"] or 0),
                "input_tokens": int(m["input_tokens"] or 0),
                "output_tokens": int(m["output_tokens"] or 0),
            }
            for m in (r["by_model"] or [])
        ],
        "by_feature": [
            {
                "feature": f["feature"],
                "invocations": int(f["invocations"] or 0),
                "cost_usd": float(f["cost_usd"] or 0),
                "input_tokens": int(f["input_tokens"] or 0),
                "output_tokens": int(f["output_tokens"] or 0),
                "avg_latency_ms": float(f["avg_latency_ms"] or 0),
            }
            for f in (r["by_feature"] or [])
        ],
        "daily": [
            {
                "date": d["date"].isoformat(),
                "invocations": int(d["invocations"] or 0),
                "cost_usd": float(d["cost_usd"] or 0),
                "tokens": int(d["tokens"] or 0),
            }
            for d in (r["daily"] or [])
        ],
        "recent": [
            {
                "log_id": rec["log_id"],
                "timestamp": rec["timestamp"].isoformat() if rec["timestamp"] else None,
                "feature": rec["feature"],
                "model": rec["model"],
                "input_tokens": int(rec["input_tokens"] or 0),
                "output_tokens": int(rec["output_tokens"] or 0),
                "estimated_cost_usd": float(rec["estimated_cost_usd"] or 0),
                "llm_latency_ms": float(rec["llm_latency_ms"] or 0),
                "success": bool(rec["success"]) if rec["success"] is not None else None,
                "error_type": rec["error_type"],
                "endpoint": rec["endpoint"],
            }
            for rec in (r["recent"] or [])
        ],
    }


def _empty_dashboard(ty, tm, py, pm):
    empty = lambda y, m: {
        "year": y, "month": m,
        "total_invocations": 0, "success_count": 0,
        "total_cost_usd": 0.0, "total_input_tokens": 0, "total_output_tokens": 0,
        "avg_latency_ms": 0.0, "p95_latency_ms": 0.0,
    }
    return {
        "summary": empty(ty, tm), "prev_summary": empty(py, pm),
        "by_model": [], "by_feature": [], "daily": [], "recent": [],
    }


def get_monthly_summary(year: int, month: int) -> Dict[str, Any]:
    """指定月のサマリ (cost / invocations / tokens / latency)"""
    sql = f"""
    SELECT
      COUNT(*) AS total_invocations,
      COUNTIF(success = TRUE) AS success_count,
      COALESCE(SUM(estimated_cost_usd), 0) AS total_cost_usd,
      COALESCE(SUM(input_tokens), 0) AS total_input_tokens,
      COALESCE(SUM(output_tokens), 0) AS total_output_tokens,
      COALESCE(AVG(llm_latency_ms), 0) AS avg_latency_ms,
      COALESCE(APPROX_QUANTILES(llm_latency_ms, 100)[OFFSET(95)], 0) AS p95_latency_ms
    FROM {FULL_TABLE_ID}
    WHERE model IS NOT NULL
      AND EXTRACT(YEAR FROM timestamp AT TIME ZONE @tz) = @year
      AND EXTRACT(MONTH FROM timestamp AT TIME ZONE @tz) = @month
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("year", "INT64", year),
            bigquery.ScalarQueryParameter("month", "INT64", month),
            bigquery.ScalarQueryParameter("tz", "STRING", DEFAULT_TZ),
        ]
    )
    rows = list(client.query(sql, job_config=job_config).result())
    if not rows:
        return _empty_summary(year, month)
    r = rows[0]
    return {
        "year": year,
        "month": month,
        "total_invocations": int(r["total_invocations"] or 0),
        "success_count": int(r["success_count"] or 0),
        "total_cost_usd": float(r["total_cost_usd"] or 0),
        "total_input_tokens": int(r["total_input_tokens"] or 0),
        "total_output_tokens": int(r["total_output_tokens"] or 0),
        "avg_latency_ms": float(r["avg_latency_ms"] or 0),
        "p95_latency_ms": float(r["p95_latency_ms"] or 0),
    }


def get_monthly_by_model(year: int, month: int) -> List[Dict[str, Any]]:
    """指定月のモデル別集計"""
    sql = f"""
    SELECT
      model,
      COUNT(*) AS invocations,
      COALESCE(SUM(estimated_cost_usd), 0) AS cost_usd,
      COALESCE(SUM(input_tokens), 0) AS input_tokens,
      COALESCE(SUM(output_tokens), 0) AS output_tokens
    FROM {FULL_TABLE_ID}
    WHERE model IS NOT NULL
      AND EXTRACT(YEAR FROM timestamp AT TIME ZONE @tz) = @year
      AND EXTRACT(MONTH FROM timestamp AT TIME ZONE @tz) = @month
    GROUP BY model
    ORDER BY cost_usd DESC
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("year", "INT64", year),
            bigquery.ScalarQueryParameter("month", "INT64", month),
            bigquery.ScalarQueryParameter("tz", "STRING", DEFAULT_TZ),
        ]
    )
    return [
        {
            "model": r["model"],
            "invocations": int(r["invocations"] or 0),
            "cost_usd": float(r["cost_usd"] or 0),
            "input_tokens": int(r["input_tokens"] or 0),
            "output_tokens": int(r["output_tokens"] or 0),
        }
        for r in client.query(sql, job_config=job_config).result()
    ]


def get_monthly_by_feature(year: int, month: int) -> List[Dict[str, Any]]:
    """指定月の feature (prompt_name) 別集計"""
    sql = f"""
    SELECT
      COALESCE(feature, '(unknown)') AS feature,
      COUNT(*) AS invocations,
      COALESCE(SUM(estimated_cost_usd), 0) AS cost_usd,
      COALESCE(SUM(input_tokens), 0) AS input_tokens,
      COALESCE(SUM(output_tokens), 0) AS output_tokens,
      COALESCE(AVG(llm_latency_ms), 0) AS avg_latency_ms
    FROM {FULL_TABLE_ID}
    WHERE model IS NOT NULL
      AND EXTRACT(YEAR FROM timestamp AT TIME ZONE @tz) = @year
      AND EXTRACT(MONTH FROM timestamp AT TIME ZONE @tz) = @month
    GROUP BY feature
    ORDER BY cost_usd DESC
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("year", "INT64", year),
            bigquery.ScalarQueryParameter("month", "INT64", month),
            bigquery.ScalarQueryParameter("tz", "STRING", DEFAULT_TZ),
        ]
    )
    return [
        {
            "feature": r["feature"],
            "invocations": int(r["invocations"] or 0),
            "cost_usd": float(r["cost_usd"] or 0),
            "input_tokens": int(r["input_tokens"] or 0),
            "output_tokens": int(r["output_tokens"] or 0),
            "avg_latency_ms": float(r["avg_latency_ms"] or 0),
        }
        for r in client.query(sql, job_config=job_config).result()
    ]


def get_daily_trend(trend_days: int = 30) -> List[Dict[str, Any]]:
    """直近 N 日間の日次トレンド (cost / invocations / tokens)。欠損日は 0 埋め。"""
    sql = f"""
    WITH date_range AS (
      SELECT DATE_SUB(CURRENT_DATE(@tz), INTERVAL n DAY) AS date
      FROM UNNEST(GENERATE_ARRAY(0, @days - 1)) AS n
    ),
    agg AS (
      SELECT
        DATE(timestamp, @tz) AS date,
        COUNT(*) AS invocations,
        SUM(estimated_cost_usd) AS cost_usd,
        SUM(IFNULL(input_tokens, 0) + IFNULL(output_tokens, 0)) AS tokens
      FROM {FULL_TABLE_ID}
      WHERE model IS NOT NULL
        AND DATE(timestamp, @tz) >= DATE_SUB(CURRENT_DATE(@tz), INTERVAL @days - 1 DAY)
      GROUP BY date
    )
    SELECT
      r.date,
      IFNULL(a.invocations, 0) AS invocations,
      IFNULL(a.cost_usd, 0) AS cost_usd,
      IFNULL(a.tokens, 0) AS tokens
    FROM date_range r
    LEFT JOIN agg a USING (date)
    ORDER BY r.date ASC
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("days", "INT64", trend_days),
            bigquery.ScalarQueryParameter("tz", "STRING", DEFAULT_TZ),
        ]
    )
    return [
        {
            "date": r["date"].isoformat(),
            "invocations": int(r["invocations"] or 0),
            "cost_usd": float(r["cost_usd"] or 0),
            "tokens": int(r["tokens"] or 0),
        }
        for r in client.query(sql, job_config=job_config).result()
    ]


def get_recent_invocations(limit: int = 10) -> List[Dict[str, Any]]:
    """直近 N 件の LLM 呼び出し"""
    sql = f"""
    SELECT
      log_id,
      timestamp,
      COALESCE(feature, '(unknown)') AS feature,
      model,
      input_tokens,
      output_tokens,
      estimated_cost_usd,
      llm_latency_ms,
      success,
      error_type,
      endpoint
    FROM {FULL_TABLE_ID}
    WHERE model IS NOT NULL
    ORDER BY timestamp DESC
    LIMIT @limit
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("limit", "INT64", limit),
        ]
    )
    return [
        {
            "log_id": r["log_id"],
            "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
            "feature": r["feature"],
            "model": r["model"],
            "input_tokens": int(r["input_tokens"] or 0),
            "output_tokens": int(r["output_tokens"] or 0),
            "estimated_cost_usd": float(r["estimated_cost_usd"] or 0),
            "llm_latency_ms": float(r["llm_latency_ms"] or 0),
            "success": bool(r["success"]) if r["success"] is not None else None,
            "error_type": r["error_type"],
            "endpoint": r["endpoint"],
        }
        for r in client.query(sql, job_config=job_config).result()
    ]


def _empty_summary(year: int, month: int) -> Dict[str, Any]:
    return {
        "year": year,
        "month": month,
        "total_invocations": 0,
        "success_count": 0,
        "total_cost_usd": 0.0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "avg_latency_ms": 0.0,
        "p95_latency_ms": 0.0,
    }
