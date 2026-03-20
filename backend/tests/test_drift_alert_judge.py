"""
Drift Alert Judge サービスのユニットテスト
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import patch

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.app.services.drift_alert_judge_service import (
    DriftAlertJudgeService,
    DriftAlertVerdict,
    ACTION_THRESHOLD,
)


# テスト用のダミー DriftReport
SAMPLE_FEATURE_DRIFT_REPORT = {
    "report_id": "test-001",
    "model_type": "stuff_plus",
    "drift_type": "feature",
    "baseline_season": 2024,
    "target_season": 2025,
    "overall_drift_detected": True,
    "summary": "stuff_plus: 2024→2025 シーズン間でドリフトを検出。CRITICAL: release_speed",
    "features": [
        {
            "feature_name": "release_speed",
            "ks_statistic": 0.15,
            "ks_p_value": 0.001,
            "psi_value": 0.25,
            "mean_baseline": 93.2,
            "mean_target": 94.1,
            "mean_shift_pct": 0.97,
            "drift_detected": True,
            "severity": "critical",
        },
        {
            "feature_name": "release_spin_rate",
            "ks_statistic": 0.05,
            "ks_p_value": 0.45,
            "psi_value": 0.03,
            "mean_baseline": 2300,
            "mean_target": 2310,
            "mean_shift_pct": 0.43,
            "drift_detected": False,
            "severity": "none",
        },
    ],
}

SAMPLE_NO_DRIFT_REPORT = {
    "report_id": "test-002",
    "model_type": "batter_segmentation",
    "drift_type": "feature",
    "baseline_season": 2024,
    "target_season": 2025,
    "overall_drift_detected": False,
    "summary": "batter_segmentation: ドリフトは検出されませんでした。",
    "features": [],
}


class TestDriftAlertVerdictStructure:
    """DriftAlertVerdict データクラスのテスト"""

    def test_default_verdict_has_required_fields(self):
        verdict = DriftAlertVerdict(
            report_id="test", model_type="stuff_plus", drift_type="feature"
        )
        d = verdict.to_dict()
        required = [
            "report_id", "model_type", "drift_type",
            "statistical_validity", "practical_significance",
            "actionability", "domain_relevance", "overall_score",
            "action_required", "recommended_action", "reasoning",
            "risk_factors", "timestamp", "judge_model", "latency_ms",
        ]
        for f in required:
            assert f in d, f"Missing field: {f}"

    def test_risk_factors_default_is_empty(self):
        verdict = DriftAlertVerdict(
            report_id="test", model_type="test", drift_type="feature"
        )
        assert verdict.risk_factors == []


class TestDriftAlertPromptConstruction:
    """Judge プロンプト構築のテスト"""

    def test_prompt_contains_model_type(self):
        judge = DriftAlertJudgeService()
        prompt = judge._build_judge_prompt(SAMPLE_FEATURE_DRIFT_REPORT)
        assert "stuff_plus" in prompt

    def test_prompt_contains_domain_context(self):
        judge = DriftAlertJudgeService()
        prompt = judge._build_judge_prompt(SAMPLE_FEATURE_DRIFT_REPORT)
        assert "Hawk-Eye" in prompt  # stuff_plus のドメインコンテキスト

    def test_prompt_contains_statistical_guide(self):
        judge = DriftAlertJudgeService()
        prompt = judge._build_judge_prompt(SAMPLE_FEATURE_DRIFT_REPORT)
        assert "PSI" in prompt
        assert "KS検定" in prompt

    def test_prompt_contains_all_four_dimensions(self):
        judge = DriftAlertJudgeService()
        prompt = judge._build_judge_prompt(SAMPLE_FEATURE_DRIFT_REPORT)
        assert "statistical_validity" in prompt
        assert "practical_significance" in prompt
        assert "actionability" in prompt
        assert "domain_relevance" in prompt

    def test_prompt_contains_feature_data(self):
        judge = DriftAlertJudgeService()
        prompt = judge._build_judge_prompt(SAMPLE_FEATURE_DRIFT_REPORT)
        assert "release_speed" in prompt
        assert "0.25" in prompt  # PSI値

    def test_different_model_gets_different_context(self):
        judge = DriftAlertJudgeService()
        prompt_batter = judge._build_judge_prompt(SAMPLE_NO_DRIFT_REPORT)
        prompt_stuff = judge._build_judge_prompt(SAMPLE_FEATURE_DRIFT_REPORT)
        # batter_segmentation は KMeans, stuff_plus は Hawk-Eye
        assert "KMeans" in prompt_batter
        assert "Hawk-Eye" in prompt_stuff


class TestDriftAlertResponseParsing:
    """レスポンスパースのテスト"""

    def test_parse_action_required(self):
        judge = DriftAlertJudgeService()
        response = {
            "statistical_validity": 5,
            "practical_significance": 4,
            "actionability": 4,
            "domain_relevance": 5,
            "overall_score": 4.5,
            "action_required": True,
            "recommended_action": "retrain",
            "reasoning": "球速分布の有意なシフトが検出され、再学習推奨",
            "risk_factors": ["ボール仕様変更の可能性", "Hawk-Eyeキャリブレーション"],
        }
        verdict = judge._parse_judge_response(
            response, "test-001", "stuff_plus", "feature"
        )
        assert verdict.action_required is True
        assert verdict.recommended_action == "retrain"
        assert len(verdict.risk_factors) == 2

    def test_parse_no_action(self):
        judge = DriftAlertJudgeService()
        response = {
            "statistical_validity": 3,
            "practical_significance": 2,
            "actionability": 2,
            "domain_relevance": 2,
            "overall_score": 2.0,
            "recommended_action": "ignore",
            "reasoning": "統計的ノイズの範囲内",
            "risk_factors": [],
        }
        verdict = judge._parse_judge_response(
            response, "test-002", "batter_segmentation", "feature"
        )
        assert verdict.action_required is False
        assert verdict.recommended_action == "ignore"

    def test_invalid_recommended_action_defaults_to_monitor(self):
        judge = DriftAlertJudgeService()
        response = {
            "overall_score": 3.0,
            "recommended_action": "invalid_action",
        }
        verdict = judge._parse_judge_response(
            response, "test", "test", "feature"
        )
        assert verdict.recommended_action == "monitor"

    def test_score_clamping(self):
        judge = DriftAlertJudgeService()
        response = {
            "statistical_validity": 99,
            "practical_significance": -5,
            "overall_score": 100.0,
        }
        verdict = judge._parse_judge_response(
            response, "test", "test", "feature"
        )
        assert verdict.statistical_validity == 5
        assert verdict.practical_significance == 1
        assert verdict.overall_score == 5.0

    def test_malformed_risk_factors(self):
        judge = DriftAlertJudgeService()
        response = {"overall_score": 3.0, "risk_factors": "not a list"}
        verdict = judge._parse_judge_response(
            response, "test", "test", "feature"
        )
        assert verdict.risk_factors == []


class TestDriftAlertEvaluationWithMock:
    """モックを使用した統合テスト"""

    @patch.object(DriftAlertJudgeService, "_call_gemini")
    def test_evaluate_drift_report_success(self, mock_gemini):
        mock_gemini.return_value = {
            "statistical_validity": 5,
            "practical_significance": 4,
            "actionability": 4,
            "domain_relevance": 5,
            "overall_score": 4.5,
            "action_required": True,
            "recommended_action": "retrain",
            "reasoning": "再学習推奨",
            "risk_factors": ["球速シフト"],
        }
        judge = DriftAlertJudgeService()
        judge.api_key = "test-key"

        verdict = judge.evaluate_drift_report(SAMPLE_FEATURE_DRIFT_REPORT)

        assert verdict.action_required is True
        assert verdict.model_type == "stuff_plus"
        assert verdict.drift_type == "feature"
        mock_gemini.assert_called_once()

    @patch.object(DriftAlertJudgeService, "_call_gemini")
    def test_evaluate_handles_api_error(self, mock_gemini):
        mock_gemini.side_effect = Exception("API error")
        judge = DriftAlertJudgeService()
        judge.api_key = "test-key"

        verdict = judge.evaluate_drift_report(SAMPLE_FEATURE_DRIFT_REPORT)
        assert verdict.action_required is False
        assert "error" in verdict.reasoning.lower()

    def test_evaluate_without_api_key(self):
        judge = DriftAlertJudgeService()
        judge.api_key = None
        verdict = judge.evaluate_drift_report(SAMPLE_FEATURE_DRIFT_REPORT)
        assert verdict.action_required is False
        assert "not configured" in verdict.reasoning


class TestDomainContext:
    """ドメインコンテキスト取得のテスト"""

    def test_all_model_types_have_context(self):
        models = [
            "batter_segmentation", "pitcher_segmentation",
            "stuff_plus", "pitching_plus", "pitching_plus_plus",
        ]
        for model in models:
            ctx = DriftAlertJudgeService._get_domain_context(model)
            assert len(ctx) > 10, f"Missing context for {model}"

    def test_unknown_model_returns_fallback(self):
        ctx = DriftAlertJudgeService._get_domain_context("unknown_model")
        assert "なし" in ctx


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
