"""
Routing Judge サービスのユニットテスト
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import patch

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.app.services.routing_judge_service import (
    RoutingJudgeService,
    RoutingVerdict,
    PASS_THRESHOLD,
    VALID_ROUTES,
)


class TestRoutingVerdictStructure:
    """RoutingVerdict データクラスのテスト"""

    def test_default_verdict_has_required_fields(self):
        verdict = RoutingVerdict(
            case_id="TEST-001",
            user_query="test",
            actual_route="batter",
            expected_route="batter",
        )
        d = verdict.to_dict()
        required = [
            "case_id", "user_query", "actual_route", "expected_route",
            "route_accuracy", "ambiguity_handling", "reasoning_quality",
            "overall_score", "passed", "is_exact_match",
            "reasoning", "ambiguity_notes",
            "timestamp", "judge_model", "latency_ms",
        ]
        for f in required:
            assert f in d, f"Missing field: {f}"

    def test_default_scores_are_zero(self):
        verdict = RoutingVerdict(
            case_id="TEST", user_query="test",
            actual_route="batter", expected_route="batter",
        )
        assert verdict.route_accuracy == 0
        assert verdict.ambiguity_handling == 0
        assert verdict.reasoning_quality == 0


class TestRoutingPromptConstruction:
    """Judge プロンプト構築のテスト"""

    def test_prompt_contains_user_query(self):
        judge = RoutingJudgeService()
        prompt = judge._build_judge_prompt(
            user_query="大谷翔平の2025年の打率は？",
            actual_route="batter",
            expected_route="batter",
        )
        assert "大谷翔平の2025年の打率は？" in prompt

    def test_prompt_contains_routing_rules(self):
        judge = RoutingJudgeService()
        prompt = judge._build_judge_prompt(
            user_query="test",
            actual_route="batter",
            expected_route="batter",
        )
        assert "batter" in prompt
        assert "pitcher" in prompt
        assert "matchup" in prompt
        assert "stats" in prompt

    def test_prompt_contains_two_way_player_note(self):
        """二刀流選手の注意事項がプロンプトに含まれる"""
        judge = RoutingJudgeService()
        prompt = judge._build_judge_prompt(
            user_query="大谷翔平の成績",
            actual_route="batter",
            expected_route="batter",
        )
        assert "二刀流" in prompt

    def test_prompt_contains_actual_and_expected(self):
        judge = RoutingJudgeService()
        prompt = judge._build_judge_prompt(
            user_query="test",
            actual_route="pitcher",
            expected_route="batter",
        )
        assert "pitcher" in prompt
        assert "batter" in prompt

    def test_prompt_contains_all_three_dimensions(self):
        judge = RoutingJudgeService()
        prompt = judge._build_judge_prompt(
            user_query="test",
            actual_route="batter",
            expected_route="batter",
        )
        assert "route_accuracy" in prompt
        assert "ambiguity_handling" in prompt
        assert "reasoning_quality" in prompt


class TestRoutingResponseParsing:
    """レスポンスパースのテスト"""

    def test_parse_correct_routing(self):
        judge = RoutingJudgeService()
        response = {
            "route_accuracy": 5,
            "ambiguity_handling": 5,
            "reasoning_quality": 5,
            "overall_score": 5.0,
            "passed": True,
            "reasoning": "打率の質問なので batter エージェントが完全に正しい",
            "ambiguity_notes": "",
        }
        verdict = judge._parse_judge_response(
            response, "GD-001", "打率は？", "batter", "batter"
        )
        assert verdict.passed is True
        assert verdict.overall_score == 5.0
        assert verdict.ambiguity_notes == ""

    def test_parse_incorrect_routing(self):
        judge = RoutingJudgeService()
        response = {
            "route_accuracy": 1,
            "ambiguity_handling": 3,
            "reasoning_quality": 2,
            "overall_score": 2.0,
            "passed": False,
            "reasoning": "防御率は投手の指標なので pitcher が正しい",
            "ambiguity_notes": "",
        }
        verdict = judge._parse_judge_response(
            response, "GD-002", "防御率は？", "batter", "pitcher"
        )
        assert verdict.passed is False
        assert verdict.overall_score == 2.0

    def test_parse_ambiguous_routing(self):
        judge = RoutingJudgeService()
        response = {
            "route_accuracy": 4,
            "ambiguity_handling": 3,
            "reasoning_quality": 4,
            "overall_score": 3.7,
            "passed": True,
            "reasoning": "大谷翔平は二刀流で曖昧だが、文脈なしでは batter で許容範囲",
            "ambiguity_notes": "二刀流選手のため、batter/pitcher どちらも許容可能",
        }
        verdict = judge._parse_judge_response(
            response, "GD-003", "大谷翔平の成績", "batter", "batter"
        )
        assert verdict.passed is True
        assert "二刀流" in verdict.ambiguity_notes

    def test_score_clamping(self):
        judge = RoutingJudgeService()
        response = {
            "route_accuracy": 99,
            "ambiguity_handling": -1,
            "overall_score": 100.0,
        }
        verdict = judge._parse_judge_response(
            response, "test", "test", "batter", "batter"
        )
        assert verdict.route_accuracy == 5
        assert verdict.ambiguity_handling == 1
        assert verdict.overall_score == 5.0


class TestRoutingEvaluationWithMock:
    """モックを使用した統合テスト"""

    @patch.object(RoutingJudgeService, "_call_gemini")
    def test_evaluate_correct_batter_routing(self, mock_gemini):
        mock_gemini.return_value = {
            "route_accuracy": 5,
            "ambiguity_handling": 5,
            "reasoning_quality": 5,
            "overall_score": 5.0,
            "passed": True,
            "reasoning": "正しいルーティング",
            "ambiguity_notes": "",
        }
        judge = RoutingJudgeService()
        judge.api_key = "test-key"

        verdict = judge.evaluate_routing(
            case_id="GD-001",
            user_query="大谷翔平の2025年のHR数は？",
            actual_route="batter",
            expected_route="batter",
        )

        assert verdict.passed is True
        assert verdict.is_exact_match is True
        assert verdict.actual_route == "batter"
        mock_gemini.assert_called_once()

    @patch.object(RoutingJudgeService, "_call_gemini")
    def test_evaluate_incorrect_routing(self, mock_gemini):
        mock_gemini.return_value = {
            "route_accuracy": 1,
            "ambiguity_handling": 3,
            "reasoning_quality": 2,
            "overall_score": 2.0,
            "passed": False,
            "reasoning": "投手の指標なのに batter にルーティングされた",
            "ambiguity_notes": "",
        }
        judge = RoutingJudgeService()
        judge.api_key = "test-key"

        verdict = judge.evaluate_routing(
            case_id="GD-002",
            user_query="山本由伸の防御率は？",
            actual_route="batter",
            expected_route="pitcher",
        )

        assert verdict.passed is False
        assert verdict.is_exact_match is False

    @patch.object(RoutingJudgeService, "_call_gemini")
    def test_evaluate_matchup_routing(self, mock_gemini):
        mock_gemini.return_value = {
            "route_accuracy": 5,
            "ambiguity_handling": 5,
            "reasoning_quality": 5,
            "overall_score": 5.0,
            "passed": True,
            "reasoning": "対戦成績の質問なので matchup が正しい",
            "ambiguity_notes": "",
        }
        judge = RoutingJudgeService()
        judge.api_key = "test-key"

        verdict = judge.evaluate_routing(
            case_id="GD-003",
            user_query="大谷翔平 vs ダルビッシュの対戦成績",
            actual_route="matchup",
            expected_route="matchup",
        )

        assert verdict.passed is True
        assert verdict.is_exact_match is True

    @patch.object(RoutingJudgeService, "_call_gemini")
    def test_evaluate_handles_api_error(self, mock_gemini):
        mock_gemini.side_effect = Exception("API error")
        judge = RoutingJudgeService()
        judge.api_key = "test-key"

        verdict = judge.evaluate_routing(
            case_id="GD-001",
            user_query="test",
            actual_route="batter",
            expected_route="batter",
        )
        assert verdict.passed is False
        assert "error" in verdict.reasoning.lower()

    def test_evaluate_without_api_key(self):
        judge = RoutingJudgeService()
        judge.api_key = None
        verdict = judge.evaluate_routing(
            case_id="GD-001",
            user_query="test",
            actual_route="batter",
            expected_route="batter",
        )
        assert verdict.passed is False
        assert "not configured" in verdict.reasoning
        assert verdict.is_exact_match is True  # exact matchは API 無しでも判定可能


class TestValidRoutes:
    """有効なルーティング先の確認"""

    def test_valid_routes(self):
        assert "batter" in VALID_ROUTES
        assert "pitcher" in VALID_ROUTES
        assert "stats" in VALID_ROUTES
        assert "matchup" in VALID_ROUTES
        assert len(VALID_ROUTES) == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
