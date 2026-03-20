"""
Reflection Judge サービスのユニットテスト
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import patch

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.app.services.reflection_judge_service import (
    ReflectionJudgeService,
    ReflectionVerdict,
    PASS_THRESHOLD,
)


# テスト用データ
SAMPLE_SQL_ERROR_PRE = {
    "query": "SELECT player_name, avg FROM batting_stats WHERE season = 2025",
    "error": "Unrecognized name: player_name; Did you mean name?",
}

SAMPLE_SQL_ERROR_POST = {
    "query": "SELECT name, batting_average FROM fact_batting_stats_with_risp WHERE season = 2025",
    "result_count": 150,
}

SAMPLE_EMPTY_RESULT_PRE = {
    "query": "SELECT name, hr FROM fact_batting_stats_with_risp WHERE name = 'Shouhei Ohtani' AND season = 2025",
    "error": None,
    "result_count": 0,
}

SAMPLE_EMPTY_RESULT_POST = {
    "query": "SELECT name, hr FROM fact_batting_stats_with_risp WHERE name = 'Shohei Ohtani' AND season = 2025",
    "result_count": 1,
}


class TestReflectionVerdictStructure:
    """ReflectionVerdict データクラスのテスト"""

    def test_default_verdict_has_required_fields(self):
        verdict = ReflectionVerdict(
            case_id="TEST-001",
            user_query="test",
            trigger_reason="sql_error",
        )
        d = verdict.to_dict()
        required = [
            "case_id", "user_query", "trigger_reason",
            "trigger_appropriateness", "root_cause_identification",
            "correction_quality", "over_correction_risk",
            "overall_score", "passed", "reasoning",
            "identified_root_cause", "suggested_improvement",
            "retry_count", "timestamp", "judge_model", "latency_ms",
        ]
        for f in required:
            assert f in d, f"Missing field: {f}"

    def test_default_scores_are_zero(self):
        verdict = ReflectionVerdict(
            case_id="TEST", user_query="test", trigger_reason="sql_error"
        )
        assert verdict.trigger_appropriateness == 0
        assert verdict.root_cause_identification == 0
        assert verdict.correction_quality == 0
        assert verdict.over_correction_risk == 0

    def test_to_dict_serialization(self):
        verdict = ReflectionVerdict(
            case_id="GD-001",
            user_query="大谷のHR",
            trigger_reason="empty_result",
            trigger_appropriateness=5,
            root_cause_identification=4,
            correction_quality=5,
            over_correction_risk=5,
            overall_score=4.8,
            passed=True,
            reasoning="選手名スペルミスの修正が適切",
            identified_root_cause="選手名のスペルミス",
        )
        d = verdict.to_dict()
        assert d["case_id"] == "GD-001"
        assert d["overall_score"] == 4.8
        assert isinstance(d, dict)


class TestReflectionPromptConstruction:
    """Judge プロンプト構築のテスト"""

    def test_prompt_contains_user_query(self):
        judge = ReflectionJudgeService()
        prompt = judge._build_judge_prompt(
            user_query="大谷翔平の2025年のHR数",
            trigger_reason="sql_error",
            error_context="Unrecognized name: player_name",
            pre_state=SAMPLE_SQL_ERROR_PRE,
            post_state=SAMPLE_SQL_ERROR_POST,
            retry_count=1,
        )
        assert "大谷翔平の2025年のHR数" in prompt

    def test_prompt_contains_error_context(self):
        judge = ReflectionJudgeService()
        prompt = judge._build_judge_prompt(
            user_query="test",
            trigger_reason="sql_error",
            error_context="Unrecognized name: player_name",
            pre_state=SAMPLE_SQL_ERROR_PRE,
            post_state=SAMPLE_SQL_ERROR_POST,
            retry_count=0,
        )
        assert "Unrecognized name" in prompt

    def test_prompt_contains_should_reflect_spec(self):
        """should_reflect() のルールベース仕様がプロンプトに含まれる"""
        judge = ReflectionJudgeService()
        prompt = judge._build_judge_prompt(
            user_query="test",
            trigger_reason="sql_error",
            error_context="test error",
            pre_state={},
            post_state={},
            retry_count=0,
        )
        assert "パーミッション" in prompt
        assert "タイムアウト" in prompt
        assert "最大リトライ" in prompt

    def test_prompt_contains_all_four_dimensions(self):
        judge = ReflectionJudgeService()
        prompt = judge._build_judge_prompt(
            user_query="test",
            trigger_reason="sql_error",
            error_context="test",
            pre_state={},
            post_state={},
            retry_count=0,
        )
        assert "trigger_appropriateness" in prompt
        assert "root_cause_identification" in prompt
        assert "correction_quality" in prompt
        assert "over_correction_risk" in prompt

    def test_prompt_contains_pre_and_post_state(self):
        judge = ReflectionJudgeService()
        prompt = judge._build_judge_prompt(
            user_query="test",
            trigger_reason="empty_result",
            error_context="0行",
            pre_state=SAMPLE_EMPTY_RESULT_PRE,
            post_state=SAMPLE_EMPTY_RESULT_POST,
            retry_count=1,
        )
        assert "Shouhei Ohtani" in prompt   # pre: ミススペル
        assert "Shohei Ohtani" in prompt    # post: 修正済み


class TestReflectionResponseParsing:
    """レスポンスパースのテスト"""

    def test_parse_perfect_reflection(self):
        judge = ReflectionJudgeService()
        response = {
            "trigger_appropriateness": 5,
            "root_cause_identification": 5,
            "correction_quality": 5,
            "over_correction_risk": 5,
            "overall_score": 5.0,
            "passed": True,
            "reasoning": "カラム名誤認識を正確に特定し、最小限の修正で解決",
            "identified_root_cause": "player_name → name のカラム名誤認識",
            "suggested_improvement": "なし",
        }
        verdict = judge._parse_judge_response(
            response, "GD-001", "test", "sql_error"
        )
        assert verdict.passed is True
        assert verdict.overall_score == 5.0
        assert verdict.identified_root_cause != ""

    def test_parse_poor_reflection(self):
        judge = ReflectionJudgeService()
        response = {
            "trigger_appropriateness": 2,
            "root_cause_identification": 1,
            "correction_quality": 2,
            "over_correction_risk": 1,
            "overall_score": 1.5,
            "passed": False,
            "reasoning": "パーミッションエラーでリトライしており不適切",
            "identified_root_cause": "認証設定の不備",
            "suggested_improvement": "should_reflectでパーミッションエラーを除外すべき",
        }
        verdict = judge._parse_judge_response(
            response, "GD-001", "test", "sql_error"
        )
        assert verdict.passed is False
        assert verdict.overall_score == 1.5

    def test_score_clamping(self):
        judge = ReflectionJudgeService()
        response = {
            "trigger_appropriateness": 99,
            "root_cause_identification": -1,
            "overall_score": 100.0,
        }
        verdict = judge._parse_judge_response(
            response, "test", "test", "sql_error"
        )
        assert verdict.trigger_appropriateness == 5
        assert verdict.root_cause_identification == 1
        assert verdict.overall_score == 5.0

    def test_malformed_response_handling(self):
        judge = ReflectionJudgeService()
        response = {"unexpected_field": "value"}
        verdict = judge._parse_judge_response(
            response, "test", "test", "sql_error"
        )
        assert verdict.trigger_appropriateness == 1
        assert verdict.overall_score == 1.0
        assert verdict.passed is False


class TestReflectionEvaluationWithMock:
    """モックを使用した統合テスト"""

    @patch.object(ReflectionJudgeService, "_call_gemini")
    def test_evaluate_sql_error_reflection(self, mock_gemini):
        mock_gemini.return_value = {
            "trigger_appropriateness": 5,
            "root_cause_identification": 5,
            "correction_quality": 4,
            "over_correction_risk": 5,
            "overall_score": 4.8,
            "passed": True,
            "reasoning": "SQLカラム名の修正が適切",
            "identified_root_cause": "カラム名の誤認識",
            "suggested_improvement": "特になし",
        }
        judge = ReflectionJudgeService()
        judge.api_key = "test-key"

        verdict = judge.evaluate_reflection(
            case_id="GD-001",
            user_query="大谷翔平の打率",
            trigger_reason="sql_error",
            error_context="Unrecognized name: player_name",
            pre_reflection_state=SAMPLE_SQL_ERROR_PRE,
            post_reflection_state=SAMPLE_SQL_ERROR_POST,
            retry_count=1,
        )

        assert verdict.passed is True
        assert verdict.overall_score == 4.8
        assert verdict.trigger_reason == "sql_error"
        assert verdict.retry_count == 1
        mock_gemini.assert_called_once()

    @patch.object(ReflectionJudgeService, "_call_gemini")
    def test_evaluate_empty_result_reflection(self, mock_gemini):
        mock_gemini.return_value = {
            "trigger_appropriateness": 5,
            "root_cause_identification": 4,
            "correction_quality": 5,
            "over_correction_risk": 5,
            "overall_score": 4.8,
            "passed": True,
            "reasoning": "選手名スペルミスの修正が適切",
            "identified_root_cause": "Shouhei → Shohei のスペルミス",
            "suggested_improvement": "特になし",
        }
        judge = ReflectionJudgeService()
        judge.api_key = "test-key"

        verdict = judge.evaluate_reflection(
            case_id="GD-002",
            user_query="大谷翔平のHR",
            trigger_reason="empty_result",
            error_context="クエリ結果が0行",
            pre_reflection_state=SAMPLE_EMPTY_RESULT_PRE,
            post_reflection_state=SAMPLE_EMPTY_RESULT_POST,
        )

        assert verdict.passed is True
        assert verdict.trigger_reason == "empty_result"

    @patch.object(ReflectionJudgeService, "_call_gemini")
    def test_evaluate_handles_api_error(self, mock_gemini):
        mock_gemini.side_effect = Exception("API error")
        judge = ReflectionJudgeService()
        judge.api_key = "test-key"

        verdict = judge.evaluate_reflection(
            case_id="GD-001",
            user_query="test",
            trigger_reason="sql_error",
            error_context="test",
            pre_reflection_state={},
            post_reflection_state={},
        )
        assert verdict.passed is False
        assert "error" in verdict.reasoning.lower()

    def test_evaluate_without_api_key(self):
        judge = ReflectionJudgeService()
        judge.api_key = None
        verdict = judge.evaluate_reflection(
            case_id="GD-001",
            user_query="test",
            trigger_reason="sql_error",
            error_context="test",
            pre_reflection_state={},
            post_reflection_state={},
        )
        assert verdict.passed is False
        assert "not configured" in verdict.reasoning


class TestPassThreshold:
    """合格閾値の確認"""

    def test_threshold_is_reasonable(self):
        assert 3.0 <= PASS_THRESHOLD <= 4.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
