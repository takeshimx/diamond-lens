"""
Synthesizer Judge サービスのユニットテスト

LLM API を呼び出さずに、Judge サービスのロジックを検証します。
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.app.services.synthesizer_judge_service import (
    SynthesizerJudgeService,
    SynthesizerVerdict,
    PASS_THRESHOLD,
    FACTUAL_ACCURACY_FLOOR,
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
            "context_relevance", "retrieval_used",
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


class TestPromptConstruction:
    """プロンプトファイルからの組み立て"""

    def _prompt(self, answer_mode):
        return SynthesizerJudgeService()._build_judge_prompt(
            user_query="大谷翔平の2025年の打率は？",
            source_data='[{"name": "Shohei Ohtani", "avg": 0.310}]',
            synthesizer_output="- avg: 0.310",
            answer_mode=answer_mode,
        )

    @pytest.mark.parametrize("mode", ["raw", "rag"])
    def test_placeholders_are_filled(self, mode):
        prompt = self._prompt(mode)
        assert "大谷翔平の2025年の打率は？" in prompt
        assert "Shohei Ohtani" in prompt
        assert "- avg: 0.310" in prompt
        assert "{user_query}" not in prompt
        assert "{source_data}" not in prompt
        assert "{output}" not in prompt

    def test_raw_prompt_has_only_two_dimensions(self):
        """生データ経路は書式・文章・分析を採点しない"""
        prompt = self._prompt("raw")
        assert "factual_accuracy" in prompt
        assert "completeness" in prompt
        for dim in ("analytical_depth", "language_quality", "structure", "context_relevance"):
            assert dim not in prompt

    def test_rag_prompt_has_all_dimensions(self):
        prompt = self._prompt("rag")
        for dim in (
            "factual_accuracy", "completeness", "analytical_depth",
            "language_quality", "structure", "context_relevance",
        ):
            assert dim in prompt

    def test_prompts_do_not_ask_llm_for_overall_score(self):
        """総合点と合否はコードで計算する"""
        for mode in ("raw", "rag"):
            prompt = self._prompt(mode)
            assert "overall_score" not in prompt
            assert '"passed"' not in prompt

    def test_unknown_answer_mode_is_rejected(self):
        judge = SynthesizerJudgeService()
        judge.api_key = "test-key"
        with pytest.raises(ValueError, match="unknown answer_mode"):
            judge.evaluate_output("T", "q", "{}", "a", answer_mode="direct")


class TestScoringRaw:
    """生データ経路の採点"""

    def _parse(self, response):
        return SynthesizerJudgeService()._parse_judge_response(response, "T", "q", "raw")

    def test_overall_is_mean_of_two_dimensions(self):
        verdict = self._parse({"factual_accuracy": 5, "completeness": 3})
        assert verdict.overall_score == 4.0
        assert verdict.passed is True

    def test_non_scored_dimensions_are_zero(self):
        """LLM が余計な項目を返しても採点対象外は 0 のまま"""
        verdict = self._parse({
            "factual_accuracy": 5, "completeness": 5,
            "analytical_depth": 1, "language_quality": 1, "structure": 1,
            "context_relevance": 1,
        })
        assert verdict.analytical_depth == 0
        assert verdict.language_quality == 0
        assert verdict.structure == 0
        assert verdict.context_relevance == 0
        assert verdict.retrieval_used is False
        assert verdict.overall_score == 5.0

    def test_llm_overall_score_is_ignored(self):
        verdict = self._parse({"factual_accuracy": 5, "completeness": 5, "overall_score": 1.0})
        assert verdict.overall_score == 5.0

    def test_records_answer_mode(self):
        assert self._parse({"factual_accuracy": 5, "completeness": 5}).synthesizer_path == "raw"


class TestScoringRag:
    """RAG 文章合成経路の採点"""

    def _parse(self, response):
        return SynthesizerJudgeService()._parse_judge_response(response, "T", "q", "rag")

    def test_overall_is_mean_of_five_dimensions(self):
        verdict = self._parse({
            "factual_accuracy": 5, "completeness": 4, "analytical_depth": 3,
            "language_quality": 4, "structure": 4, "context_relevance": 2,
        })
        assert verdict.overall_score == 4.0
        assert verdict.passed is True

    def test_context_relevance_is_scored_but_excluded_from_overall(self):
        verdict = self._parse({
            "factual_accuracy": 4, "completeness": 4, "analytical_depth": 4,
            "language_quality": 4, "structure": 4, "context_relevance": 1,
        })
        assert verdict.context_relevance == 1
        assert verdict.retrieval_used is True
        assert verdict.overall_score == 4.0

    def test_missing_context_relevance_is_zero_not_one(self):
        """キー欠落は「評価対象外」の 0。最低点 1 と混同しない"""
        verdict = self._parse({"factual_accuracy": 4, "completeness": 4})
        assert verdict.context_relevance == 0


class TestPassRule:
    """合否ルール（両経路共通）"""

    def test_threshold_constants(self):
        assert PASS_THRESHOLD == 3.5
        assert FACTUAL_ACCURACY_FLOOR == 3

    def test_low_factual_accuracy_fails_even_with_high_mean(self):
        """事実の誤りは他の項目で取り返せない"""
        verdict = SynthesizerJudgeService()._parse_judge_response({
            "factual_accuracy": 2, "completeness": 5, "analytical_depth": 5,
            "language_quality": 5, "structure": 5,
        }, "T", "q", "rag")
        assert verdict.overall_score == 4.4
        assert verdict.passed is False

    def test_below_threshold_fails(self):
        verdict = SynthesizerJudgeService()._parse_judge_response(
            {"factual_accuracy": 4, "completeness": 2}, "T", "q", "raw"
        )
        assert verdict.overall_score == 3.0
        assert verdict.passed is False

    def test_score_clamping(self):
        verdict = SynthesizerJudgeService()._parse_judge_response(
            {"factual_accuracy": 10, "completeness": -1}, "T", "q", "raw"
        )
        assert verdict.factual_accuracy == 5
        assert verdict.completeness == 1

    def test_malformed_issues_handled(self):
        """issues が list でない場合でもクラッシュしない"""
        verdict = SynthesizerJudgeService()._parse_judge_response(
            {"factual_accuracy": 3, "completeness": 3, "issues": "not a list"}, "T", "q", "raw"
        )
        assert verdict.issues == []


class TestSynthesizerEvaluationWithMock:
    """モックを使用した統合テスト"""

    @patch.object(SynthesizerJudgeService, "_call_gemini")
    def test_evaluate_output_success(self, mock_gemini):
        mock_gemini.return_value = {
            "factual_accuracy": 5,
            "completeness": 3,
            "reasoning": "数値は正確",
            "issues": [],
        }
        judge = SynthesizerJudgeService()
        judge.api_key = "test-key"

        verdict = judge.evaluate_output(
            case_id="GD-001",
            user_query="大谷翔平の2025年のHR数は？",
            source_data='[{"name": "Shohei Ohtani", "hr": 55}]',
            synthesizer_output="### Shohei Ohtani / 2025年\n- hr: 55",
            answer_mode="raw",
        )

        assert verdict.passed is True
        assert verdict.overall_score == 4.0
        assert verdict.synthesizer_path == "raw"
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

    def test_retrieval_used_preserved_on_api_error(self):
        """Judge が失敗しても「RAG は動いた」事実は記録に残す"""
        judge = SynthesizerJudgeService()
        judge.api_key = None
        verdict = judge.evaluate_output(
            case_id="T", user_query="t", source_data="{}",
            synthesizer_output="t", answer_mode="rag",
        )
        assert verdict.retrieval_used is True
        assert verdict.context_relevance == 0


class TestOnlineJudgeAnswerMode:
    """online_judge_service 側の採点モード判定"""

    def test_machine_formatted_answer_is_raw(self):
        from backend.app.services.online_judge_service import resolve_answer_mode
        assert resolve_answer_mode({"get_batter_stats_tool"}, synthesized=False) == "raw"

    def test_glossary_answer_is_rag(self):
        from backend.app.services.online_judge_service import resolve_answer_mode
        assert resolve_answer_mode({"glossary_search_tool"}, synthesized=True) == "rag"

    def test_direct_answer_is_not_judged(self):
        """ツールを呼ばずに直接答えた回答は採点しない"""
        from backend.app.services.online_judge_service import resolve_answer_mode
        assert resolve_answer_mode(set(), synthesized=True) is None
        assert resolve_answer_mode(None, synthesized=True) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
