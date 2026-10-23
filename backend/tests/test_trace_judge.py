"""
Trace Viewer の Online Judge 表示まわりのユニットテスト

BigQuery は呼ばず、trace_query_service の組み立てと整形だけを検証する。
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from backend.app.services import trace_query_service as svc


def _client_returning(rows):
    client = MagicMock()
    client.query.return_value.result.return_value = rows
    return client


def _verdict_row(**overrides):
    row = {
        "passed": False,
        "overall_score": 2.5,
        "synthesizer_path": "raw",
        "reasoning": "主要な値に誤り",
        "issues": '["HR が元データと違う"]',
        "timestamp": datetime(2026, 10, 23, tzinfo=timezone.utc),
        "factual_accuracy": 2,
        "completeness": 3,
        "analytical_depth": 0,
        "language_quality": 0,
        "structure": 0,
        "context_relevance": 0,
    }
    row.update(overrides)
    return row


class TestFetchJudge:
    def test_returns_none_when_not_sampled(self):
        with patch.object(svc, "_get_client", return_value=_client_returning([])):
            assert svc._fetch_judge("req-1") is None

    def test_drops_not_applicable_dimensions(self):
        """0 は「評価対象外」。UI に最低点として出さない"""
        with patch.object(svc, "_get_client", return_value=_client_returning([_verdict_row()])):
            judge = svc._fetch_judge("req-1")
        assert judge["scores"] == {"factual_accuracy": 2, "completeness": 3}
        assert judge["passed"] is False
        assert judge["mode"] == "raw"
        assert judge["issues"] == ["HR が元データと違う"]

    def test_malformed_issues_become_empty_list(self):
        rows = [_verdict_row(issues="not json")]
        with patch.object(svc, "_get_client", return_value=_client_returning(rows)):
            assert svc._fetch_judge("req-1")["issues"] == []

    def test_read_failure_is_suppressed(self):
        """Judge テーブルが読めなくても trace 本体の表示は止めない"""
        client = MagicMock()
        client.query.side_effect = RuntimeError("table not found")
        with patch.object(svc, "_get_client", return_value=client):
            assert svc._fetch_judge("req-1") is None


class TestListTracesJudgeFilter:
    def test_only_judge_failed_is_passed_as_query_parameter(self):
        client = _client_returning([])
        with patch.object(svc, "_get_client", return_value=client):
            svc.list_traces(only_judge_failed=True)
        params = {
            p.name: p.value
            for p in client.query.call_args.kwargs["job_config"].query_parameters
        }
        assert params["only_judge_failed"] is True

    def test_judge_fields_are_none_when_not_sampled(self):
        row = {
            "trace_id": "t1", "request_id": "r1",
            "started_at": None, "ended_at": None, "labeled_at": None,
            "step_count": 2, "llm_calls": 1, "max_iteration": 1, "failed_steps": 0,
            "cost_usd": 0, "llm_latency_ms": 0, "user_query": "q", "nodes": [],
            "session_id": None, "endpoint": None, "label": None, "note": None,
            "user_rating": None, "feedback_category": None, "feedback_reason": None,
            "expected_query_type": None,
            "judge_passed": None, "judge_score": None, "judge_mode": None,
        }
        with patch.object(svc, "_get_client", return_value=_client_returning([row])):
            traces = svc.list_traces()
        assert traces[0]["judge_passed"] is None
        assert traces[0]["judge_score"] is None
