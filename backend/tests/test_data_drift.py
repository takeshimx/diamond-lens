"""
Data Drift Detection ユニットテスト

BigQuery接続不要: モックデータで純粋な統計計算ロジックを検証する。
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock
from dataclasses import asdict

from backend.app.services.data_drift_service import (
    DataDriftService,
    DriftReport,
    FeatureDriftResult,
    MODEL_FEATURE_CONFIG,
)


class TestPSICalculation:
    """PSI (Population Stability Index) 計算のテスト"""

    def test_psi_identical_distributions(self):
        """同一分布ではPSI ≈ 0（微小値のepsilonは許容）"""
        np.random.seed(42)
        data = pd.Series(np.random.normal(0, 1, 1000))
        psi = DataDriftService._calculate_psi(data, data)
        assert psi < 0.01, f"PSI should be near 0 for identical data, got {psi}"

    def test_psi_shifted_distribution(self):
        """平均がシフトした分布ではPSI > 0"""
        np.random.seed(42)
        baseline = pd.Series(np.random.normal(0, 1, 1000))
        target = pd.Series(np.random.normal(2, 1, 1000))
        psi = DataDriftService._calculate_psi(baseline, target)
        assert psi > 0.1, f"PSI should indicate drift, got {psi}"

    def test_psi_different_variance(self):
        """分散が異なる分布でもPSI > 0"""
        np.random.seed(42)
        baseline = pd.Series(np.random.normal(0, 1, 1000))
        target = pd.Series(np.random.normal(0, 3, 1000))
        psi = DataDriftService._calculate_psi(baseline, target)
        assert psi > 0.05, f"PSI should detect variance change, got {psi}"

    def test_psi_always_non_negative(self):
        """PSIは常に非負"""
        np.random.seed(42)
        baseline = pd.Series(np.random.normal(0, 1, 500))
        target = pd.Series(np.random.normal(0.5, 1.2, 500))
        psi = DataDriftService._calculate_psi(baseline, target)
        assert psi >= 0, f"PSI should be non-negative, got {psi}"


class TestKSTestIntegration:
    """KS 検定の統合テスト"""

    @patch.object(DataDriftService, '__init__', lambda self: None)
    def setup_method(self, _mock):
        self.service = DataDriftService()
        self.service.psi_warning = 0.1
        self.service.psi_critical = 0.2
        self.service.ks_alpha = 0.05

    def test_no_drift_similar_distributions(self):
        """類似分布ではドリフトなし"""
        np.random.seed(42)
        baseline = pd.Series(np.random.normal(0, 1, 500))
        target = pd.Series(np.random.normal(0, 1, 500))
        result = self.service._analyze_feature_drift(
            baseline, target, "test_feature"
        )
        assert result.severity == "none"
        assert result.drift_detected is False

    def test_drift_detected_large_shift(self):
        """大きなシフトでドリフト検出"""
        np.random.seed(42)
        baseline = pd.Series(np.random.normal(0, 1, 500))
        target = pd.Series(np.random.normal(3, 1, 500))
        result = self.service._analyze_feature_drift(
            baseline, target, "test_feature"
        )
        assert result.drift_detected is True
        assert result.severity == "critical"


class TestSeverityDetermination:
    """深刻度判定のテスト"""

    @patch.object(DataDriftService, '__init__', lambda self: None)
    def setup_method(self, _mock):
        self.service = DataDriftService()
        self.service.psi_warning = 0.1
        self.service.psi_critical = 0.2
        self.service.ks_alpha = 0.05

    def test_no_drift(self):
        """PSI低 & p値高 → none"""
        severity, drift = self.service._determine_severity(
            ks_p_value=0.5, psi_value=0.05
        )
        assert severity == "none"
        assert drift is False

    def test_warning_level(self):
        """PSI 0.1-0.2 → warning"""
        severity, drift = self.service._determine_severity(
            ks_p_value=0.3, psi_value=0.15
        )
        assert severity == "warning"
        assert drift is True

    def test_critical_by_psi(self):
        """PSI >= 0.2 → critical"""
        severity, drift = self.service._determine_severity(
            ks_p_value=0.3, psi_value=0.25
        )
        assert severity == "critical"
        assert drift is True

    def test_critical_by_ks_pvalue(self):
        """KS p値 < alpha → critical"""
        severity, drift = self.service._determine_severity(
            ks_p_value=0.01, psi_value=0.05
        )
        assert severity == "critical"
        assert drift is True


class TestDriftReport:
    """DriftReport 構造のテスト"""

    def test_report_to_dict(self):
        """DriftReport.to_dict() が正しい構造を返す"""
        feature = FeatureDriftResult(
            feature_name="ops",
            ks_statistic=0.12,
            ks_p_value=0.03,
            psi_value=0.15,
            mean_baseline=0.750,
            mean_target=0.720,
            mean_shift_pct=-4.0,
            drift_detected=True,
            severity="warning",
        )
        report = DriftReport(
            model_type="batter_segmentation",
            baseline_season=2024,
            target_season=2025,
            features=[feature],
            overall_drift_detected=True,
            summary="Test summary",
        )
        d = report.to_dict()

        assert d["model_type"] == "batter_segmentation"
        assert d["overall_drift_detected"] is True
        assert len(d["features"]) == 1
        assert d["features"][0]["feature_name"] == "ops"
        assert d["features"][0]["severity"] == "warning"

    def test_model_feature_config_keys(self):
        """MODEL_FEATURE_CONFIG に必要なモデルが定義されている"""
        assert "batter_segmentation" in MODEL_FEATURE_CONFIG
        assert "pitcher_segmentation" in MODEL_FEATURE_CONFIG

    def test_batter_features_match_segmentation(self):
        """打者特徴量が player_segmentation.py と一致"""
        expected = ["ops", "iso", "k_rate", "bb_rate"]
        actual = MODEL_FEATURE_CONFIG["batter_segmentation"]["features"]
        assert actual == expected

    def test_pitcher_features_match_segmentation(self):
        """投手特徴量が player_segmentation.py と一致"""
        expected = ["era", "k_9", "gbpct"]
        actual = MODEL_FEATURE_CONFIG["pitcher_segmentation"]["features"]
        assert actual == expected


class TestDetectDriftEndToEnd:
    """detect_drift のE2Eテスト（BigQueryモック）"""

    @patch.object(DataDriftService, '__init__', lambda self: None)
    def test_detect_drift_with_mock_data(self):
        """モックデータでドリフト検知の全フローを検証"""
        service = DataDriftService()
        service.psi_warning = 0.1
        service.psi_critical = 0.2
        service.ks_alpha = 0.05

        # モックデータ
        np.random.seed(42)
        baseline_df = pd.DataFrame({
            "season": [2024] * 100,
            "ops": np.random.normal(0.750, 0.08, 100),
            "iso": np.random.normal(0.150, 0.04, 100),
            "k_rate": np.random.normal(22.0, 4.0, 100),
            "bb_rate": np.random.normal(8.5, 2.0, 100),
        })
        target_df = pd.DataFrame({
            "season": [2025] * 100,
            "ops": np.random.normal(0.750, 0.08, 100),  # 変化なし
            "iso": np.random.normal(0.150, 0.04, 100),  # 変化なし
            "k_rate": np.random.normal(25.0, 4.0, 100),  # +3ptシフト
            "bb_rate": np.random.normal(8.5, 2.0, 100),  # 変化なし
        })

        with patch.object(
            service, '_fetch_season_data',
            side_effect=[baseline_df, target_df]
        ):
            report = service.detect_drift(
                baseline_season=2024,
                target_season=2025,
                model_type="batter_segmentation",
            )

        assert report.model_type == "batter_segmentation"
        assert len(report.features) == 4

        # k_rate にはドリフトが検出されるはず
        k_rate_result = next(
            f for f in report.features if f.feature_name == "k_rate"
        )
        assert k_rate_result.mean_shift_pct > 0

    @patch.object(DataDriftService, '__init__', lambda self: None)
    def test_detect_drift_invalid_model_type(self):
        """不正なmodel_typeでValueError"""
        service = DataDriftService()
        service.psi_warning = 0.1
        service.psi_critical = 0.2
        service.ks_alpha = 0.05

        with pytest.raises(ValueError, match="Unknown model_type"):
            service.detect_drift(2024, 2025, "invalid_model")

    @patch.object(DataDriftService, '__init__', lambda self: None)
    def test_detect_drift_empty_data(self):
        """データ不足時のハンドリング"""
        service = DataDriftService()
        service.psi_warning = 0.1
        service.psi_critical = 0.2
        service.ks_alpha = 0.05

        with patch.object(
            service, '_fetch_season_data',
            return_value=pd.DataFrame()
        ):
            report = service.detect_drift(
                baseline_season=2024,
                target_season=2025,
                model_type="batter_segmentation",
            )
        assert report.overall_drift_detected is False
        assert "データ不足" in report.summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
