"""
Synthesizer Judge サービスのユニットテスト

LLM API を呼び出さずに、Judge サービスのロジックを検証します。
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import patch

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.app.services.synthesizer_judge_service import (
    SynthesizerJudgeService,
    SynthesizerVerdict,
    PASS_THRESHOLD,
)


class TestSynthesizerVerdictStructure:
    """SynthesizerVerdict データクラスの構造テスト"""

    def test_default_verdict_has_required_fields(self):
        verdict = SynthesizerVerdict(case_id="TEST-001", user_query="テスト")
        d = verdict.to_dict()
        required = [
            "case_id", "user_query",
            "factual_accuracy", "analytical_depth", "language_quality",
            "structure", "completeness", "overall_score",
            "passed", "reasoning", "issues",
            "synthesizer_path", "timestamp", "judge_model", "latency_ms",
        ]
        for f in required:
            assert f in d, f"Missing field: {f}"

    def test_default_scores_are_zero(self):
        verdict = SynthesizerVerdict(case_id="TEST", user_query="test")
        assert verdict.factual_accuracy == 0
        assert verdict.analytical_depth == 0
        assert verdict.language_quality == 0
        assert verdict.structure == 0
        assert verdict.completeness == 0

    def test_issues_default_is_empty_list(self):
        verdict = SynthesizerVerdict(case_id="TEST", user_query="test")
        assert verdict.issues == []


class TestSynthesizerPromptConstruction:
    """Judge プロンプト構築のテスト"""

    def test_prompt_contains_user_query(self):
        judge = SynthesizerJudgeService()
        prompt = judge._build_judge_prompt(
            user_query="大谷翔平の2025年の打率は？",
            source_data='[{"name": "Shohei Ohtani", "avg": 0.310}]',
            synthesizer_output="大谷翔平選手の2025年の打率は.310です。",
            synthesizer_path="simple",
        )
        assert "大谷翔平の2025年の打率は？" in prompt

    def test_prompt_contains_source_data(self):
        judge = SynthesizerJudgeService()
        prompt = judge._build_judge_prompt(
            user_query="test",
            source_data='[{"name": "Shohei Ohtani", "avg": 0.310}]',
            synthesizer_output="test output",
            synthesizer_path="agent",
        )
        assert "Shohei Ohtani" in prompt
        assert "0.310" in prompt

    def test_agent_path_expects_markdown(self):
        """Agent Flow の場合 Markdown 構造化が求められる"""
        judge = SynthesizerJudgeService()
        prompt = judge._build_judge_prompt(
            user_query="test",
            source_data="{}",
            synthesizer_output="test",
            synthesizer_path="agent",
        )
        assert "Markdown" in prompt

    def test_simple_path_expects_natural_language(self):
        """Simple Flow の場合 自然な文章が求められる"""
        judge = SynthesizerJudgeService()
        prompt = judge._build_judge_prompt(
            user_query="test",
            source_data="{}",
            synthesizer_output="test",
            synthesizer_path="simple",
        )
        assert "推測表現は不可" in prompt

    def test_prompt_contains_all_five_dimensions(self):
        judge = SynthesizerJudgeService()
        prompt = judge._build_judge_prompt(
            user_query="test",
            source_data="{}",
            synthesizer_output="test",
            synthesizer_path="agent",
        )
        assert "factual_accuracy" in prompt
        assert "analytical_depth" in prompt
        assert "language_quality" in prompt
        assert "structure" in prompt
        assert "completeness" in prompt


class TestSynthesizerResponseParsing:
    """Judge レスポンスパースのテスト"""

    def test_parse_perfect_score(self):
        judge = SynthesizerJudgeService()
        response = {
            "factual_accuracy": 5,
            "analytical_depth": 5,
            "language_quality": 5,
            "structure": 5,
            "completeness": 5,
            "overall_score": 5.0,
            "passed": True,
            "reasoning": "完璧なレポート",
            "issues": [],
        }
        verdict = judge._parse_judge_response(response, "GD-001", "test")
        assert verdict.overall_score == 5.0
        assert verdict.passed is True
        assert verdict.issues == []

    def test_parse_with_issues(self):
        judge = SynthesizerJudgeService()
        response = {
            "factual_accuracy": 3,
            "analytical_depth": 2,
            "language_quality": 4,
            "structure": 3,
            "completeness": 3,
            "overall_score": 3.0,
            "passed": False,
            "reasoning": "分析深度が不足",
            "issues": ["データの朗読に留まっている", "「なぜ」への言及がない"],
        }
        verdict = judge._parse_judge_response(response, "GD-001", "test")
        assert verdict.passed is False
        assert len(verdict.issues) == 2

    def test_score_clamping(self):
        judge = SynthesizerJudgeService()
        response = {
            "factual_accuracy": 10,
            "analytical_depth": -1,
            "overall_score": 99.9,
        }
        verdict = judge._parse_judge_response(response, "GD-001", "test")
        assert verdict.factual_accuracy == 5
        assert verdict.analytical_depth == 1
        assert verdict.overall_score == 5.0

    def test_malformed_issues_handled(self):
        """issues が list でない場合でもクラッシュしない"""
        judge = SynthesizerJudgeService()
        response = {
            "overall_score": 3.0,
            "issues": "not a list",
        }
        verdict = judge._parse_judge_response(response, "GD-001", "test")
        assert verdict.issues == []


class TestSynthesizerEvaluationWithMock:
    """モックを使用した統合テスト"""

    @patch.object(SynthesizerJudgeService, "_call_gemini")
    def test_evaluate_output_success(self, mock_gemini):
        mock_gemini.return_value = {
            "factual_accuracy": 5,
            "analytical_depth": 4,
            "language_quality": 4,
            "structure": 5,
            "completeness": 4,
            "overall_score": 4.4,
            "passed": True,
            "reasoning": "高品質なレポート",
            "issues": [],
        }
        judge = SynthesizerJudgeService()
        judge.api_key = "test-key"

        verdict = judge.evaluate_output(
            case_id="GD-001",
            user_query="大谷翔平の2025年のHR数は？",
            source_data='[{"name": "Shohei Ohtani", "hr": 54}]',
            synthesizer_output="大谷翔平選手は2025年シーズンで54本塁打を記録しました。",
            synthesizer_path="simple",
        )

        assert verdict.passed is True
        assert verdict.overall_score == 4.4
        assert verdict.synthesizer_path == "simple"
        mock_gemini.assert_called_once()

    @patch.object(SynthesizerJudgeService, "_call_gemini")
    def test_evaluate_handles_api_error(self, mock_gemini):
        mock_gemini.side_effect = Exception("API error")
        judge = SynthesizerJudgeService()
        judge.api_key = "test-key"

        verdict = judge.evaluate_output(
            case_id="GD-001",
            user_query="test",
            source_data="{}",
            synthesizer_output="test",
        )
        assert verdict.passed is False
        assert "error" in verdict.reasoning.lower()

    def test_evaluate_without_api_key(self):
        judge = SynthesizerJudgeService()
        judge.api_key = None
        verdict = judge.evaluate_output(
            case_id="GD-001",
            user_query="test",
            source_data="{}",
            synthesizer_output="test",
        )
        assert verdict.passed is False
        assert "not configured" in verdict.reasoning


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
