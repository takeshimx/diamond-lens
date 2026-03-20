"""
LLM Judge サービスのユニットテスト

LLM API を呼び出さずに、Judge サービスのロジックを検証します。
"""

import pytest
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# プロジェクトルートをパスに追加
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.app.services.llm_judge_service import (
    LLMJudgeService,
    JudgeVerdict,
    PASS_THRESHOLD,
)


class TestJudgeVerdictStructure:
    """JudgeVerdict データクラスの構造テスト"""

    def test_default_verdict_has_required_fields(self):
        """デフォルトのVerdictが全必須フィールドを持つ"""
        verdict = JudgeVerdict(case_id="TEST-001", user_query="テストクエリ")
        d = verdict.to_dict()

        required_fields = [
            "case_id",
            "user_query",
            "query_type_accuracy",
            "metrics_accuracy",
            "entity_resolution",
            "intent_understanding",
            "overall_score",
            "passed",
            "reasoning",
            "failure_category",
            "timestamp",
            "judge_model",
            "latency_ms",
        ]
        for field in required_fields:
            assert field in d, f"Missing field: {field}"

    def test_default_scores_are_zero(self):
        """デフォルトのスコアが0であること"""
        verdict = JudgeVerdict(case_id="TEST-001", user_query="test")
        assert verdict.query_type_accuracy == 0
        assert verdict.metrics_accuracy == 0
        assert verdict.entity_resolution == 0
        assert verdict.intent_understanding == 0
        assert verdict.overall_score == 0.0

    def test_verdict_to_dict_serialization(self):
        """to_dict()が正しくシリアライズされる"""
        verdict = JudgeVerdict(
            case_id="GD-001",
            user_query="2025年のホームラン王は誰？",
            query_type_accuracy=5,
            metrics_accuracy=4,
            entity_resolution=5,
            intent_understanding=4,
            overall_score=4.5,
            passed=True,
            reasoning="パース結果は概ね正確",
        )
        d = verdict.to_dict()
        assert d["case_id"] == "GD-001"
        assert d["overall_score"] == 4.5
        assert d["passed"] is True
        assert isinstance(d, dict)


class TestJudgePromptConstruction:
    """Judge プロンプト構築のテスト"""

    def test_prompt_contains_user_query(self):
        """プロンプトにユーザークエリが含まれる"""
        judge = LLMJudgeService()
        prompt = judge._build_judge_prompt(
            user_query="大谷翔平の2025年の打率は？",
            expected={"query_type": "season_batting"},
            actual={"query_type": "season_batting"},
        )
        assert "大谷翔平の2025年の打率は？" in prompt

    def test_prompt_contains_expected_and_actual(self):
        """プロンプトに期待値と実際値が含まれる"""
        judge = LLMJudgeService()
        expected = {"query_type": "season_batting", "name": "Shohei Ohtani"}
        actual = {"query_type": "season_batting", "name": "Shohei Ohtani"}
        prompt = judge._build_judge_prompt(
            user_query="test", expected=expected, actual=actual
        )
        assert "season_batting" in prompt
        assert "Shohei Ohtani" in prompt

    def test_prompt_contains_scoring_criteria(self):
        """プロンプトに評価基準が含まれる"""
        judge = LLMJudgeService()
        prompt = judge._build_judge_prompt(
            user_query="test", expected={}, actual={}
        )
        assert "query_type_accuracy" in prompt
        assert "metrics_accuracy" in prompt
        assert "entity_resolution" in prompt
        assert "intent_understanding" in prompt

    def test_prompt_contains_metric_map_constraint(self):
        """プロンプトにMETRIC_MAP登録キーの制約説明が含まれる"""
        judge = LLMJudgeService()
        prompt = judge._build_judge_prompt(
            user_query="test", expected={}, actual={}
        )
        assert "METRIC_MAP" in prompt
        assert "登録されていないキー" in prompt
        assert "batting_average" in prompt

    def test_prompt_contains_valid_metric_keys(self):
        """プロンプトに登録済みキー一覧が含まれる"""
        judge = LLMJudgeService()
        prompt = judge._build_judge_prompt(
            user_query="test", expected={}, actual={}
        )
        # METRIC_MAPの主要キーがプロンプトに含まれていること
        assert "homerun" in prompt
        assert "era" in prompt


class TestJudgeResponseParsing:
    """Judge レスポンスパースのテスト"""

    def test_parse_perfect_score(self):
        """満点レスポンスの正常パース"""
        judge = LLMJudgeService()
        response = {
            "query_type_accuracy": 5,
            "metrics_accuracy": 5,
            "entity_resolution": 5,
            "intent_understanding": 5,
            "overall_score": 5.0,
            "passed": True,
            "reasoning": "完璧なパース結果",
            "failure_category": "none",
        }
        verdict = judge._parse_judge_response(response, "GD-001", "test query")

        assert verdict.overall_score == 5.0
        assert verdict.passed is True
        assert verdict.query_type_accuracy == 5

    def test_parse_failing_score(self):
        """低スコアレスポンスの正常パース"""
        judge = LLMJudgeService()
        response = {
            "query_type_accuracy": 1,
            "metrics_accuracy": 2,
            "entity_resolution": 1,
            "intent_understanding": 2,
            "overall_score": 1.5,
            "passed": False,
            "reasoning": "query_typeが根本的に間違っている",
            "failure_category": "type_misclassification",
        }
        verdict = judge._parse_judge_response(response, "GD-001", "test query")

        assert verdict.overall_score == 1.5
        assert verdict.passed is False
        assert verdict.failure_category == "type_misclassification"

    def test_score_clamping_upper_bound(self):
        """スコアが5を超える場合にクランプされる"""
        judge = LLMJudgeService()
        response = {
            "query_type_accuracy": 10,
            "metrics_accuracy": 99,
            "entity_resolution": 5,
            "intent_understanding": 5,
            "overall_score": 7.5,
            "passed": True,
            "reasoning": "test",
        }
        verdict = judge._parse_judge_response(response, "GD-001", "test")

        assert verdict.query_type_accuracy == 5
        assert verdict.metrics_accuracy == 5
        assert verdict.overall_score == 5.0

    def test_score_clamping_lower_bound(self):
        """スコアが1未満の場合にクランプされる"""
        judge = LLMJudgeService()
        response = {
            "query_type_accuracy": -1,
            "metrics_accuracy": 0,
            "entity_resolution": 0,
            "intent_understanding": 0,
            "overall_score": 0.0,
            "passed": False,
            "reasoning": "test",
        }
        verdict = judge._parse_judge_response(response, "GD-001", "test")

        assert verdict.query_type_accuracy == 1
        assert verdict.metrics_accuracy == 1
        assert verdict.overall_score == 1.0

    def test_malformed_response_handling(self):
        """不正なレスポンスでもクラッシュしない"""
        judge = LLMJudgeService()
        response = {"unexpected_field": "value"}
        verdict = judge._parse_judge_response(response, "GD-001", "test")

        # デフォルト値にフォールバック
        assert verdict.query_type_accuracy == 1
        assert verdict.overall_score == 1.0
        assert verdict.passed is False


class TestValidMetricKeys:
    """METRIC_MAP キー取得のテスト"""

    def test_get_valid_metric_keys_returns_json_string(self):
        """有効なJSON文字列が返される"""
        result = LLMJudgeService._get_valid_metric_keys()
        keys = json.loads(result)
        assert isinstance(keys, list)
        assert len(keys) > 0

    def test_get_valid_metric_keys_contains_core_keys(self):
        """主要なMETRIC_MAPキーが含まれる"""
        result = LLMJudgeService._get_valid_metric_keys()
        keys = json.loads(result)
        assert "homerun" in keys
        assert "batting_average" in keys
        assert "era" in keys


class TestJudgeEvaluationWithMock:
    """モックを使用した Judge 評価の統合テスト"""

    @patch.object(LLMJudgeService, "_call_gemini")
    def test_evaluate_parse_result_success(self, mock_gemini):
        """正常な評価フロー"""
        mock_gemini.return_value = {
            "query_type_accuracy": 5,
            "metrics_accuracy": 4,
            "entity_resolution": 5,
            "intent_understanding": 4,
            "overall_score": 4.5,
            "passed": True,
            "reasoning": "パース結果は正確",
            "failure_category": "none",
        }

        judge = LLMJudgeService()
        judge.api_key = "test-key"

        verdict = judge.evaluate_parse_result(
            case_id="GD-002",
            user_query="大谷翔平の2025年の打率は？",
            expected={"query_type": "season_batting", "name": "Shohei Ohtani"},
            actual={"query_type": "season_batting", "name": "Shohei Ohtani"},
        )

        assert verdict.passed is True
        assert verdict.overall_score == 4.5
        assert verdict.case_id == "GD-002"
        assert verdict.latency_ms > 0
        mock_gemini.assert_called_once()

    @patch.object(LLMJudgeService, "_call_gemini")
    def test_evaluate_handles_api_error(self, mock_gemini):
        """API エラー時にクラッシュしない"""
        mock_gemini.side_effect = Exception("API rate limit exceeded")

        judge = LLMJudgeService()
        judge.api_key = "test-key"

        verdict = judge.evaluate_parse_result(
            case_id="GD-001",
            user_query="test",
            expected={},
            actual={},
        )

        assert verdict.passed is False
        assert "error" in verdict.reasoning.lower()

    def test_evaluate_without_api_key(self):
        """API キー未設定時のハンドリング"""
        judge = LLMJudgeService()
        judge.api_key = None

        verdict = judge.evaluate_parse_result(
            case_id="GD-001",
            user_query="test",
            expected={},
            actual={},
        )

        assert verdict.passed is False
        assert "not configured" in verdict.reasoning


class TestPassThreshold:
    """合格閾値の確認"""

    def test_threshold_is_reasonable(self):
        """閾値が妥当な範囲 (3.0-4.5) にある"""
        assert 3.0 <= PASS_THRESHOLD <= 4.5

    def test_borderline_pass(self):
        """閾値ちょうどのスコアは PASS"""
        verdict = JudgeVerdict(
            case_id="TEST",
            user_query="test",
            overall_score=PASS_THRESHOLD,
            passed=True,
        )
        assert verdict.passed is True

    def test_borderline_fail(self):
        """閾値を下回るスコアは FAIL"""
        verdict = JudgeVerdict(
            case_id="TEST",
            user_query="test",
            overall_score=PASS_THRESHOLD - 0.1,
            passed=False,
        )
        assert verdict.passed is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
