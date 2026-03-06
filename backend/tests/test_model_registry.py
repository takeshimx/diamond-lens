"""
Model Registry ユニットテスト
GCS・BigQuery 接続不要: モックで純粋なロジックを検証する。
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import json
import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock, PropertyMock
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from backend.app.services.model_registry_service import (
    ModelRegistryService,
    ModelVersion,
    MODEL_TRAINING_CONFIG,
)


class TestModelVersion:
    """ModelVersion データモデルのテスト"""

    def test_to_bq_row(self):
        """to_bq_row() が正しい構造を返す"""
        version = ModelVersion(
            version="v20250305_120000_s2024",
            model_type="batter_segmentation",
            algorithm="kmeans",
            training_season=2024,
            gcs_path="gs://bucket/models/test/model.joblib",
            n_samples=185,
            features=["ops", "iso", "k_rate", "bb_rate"],
            model_params={"n_clusters": 4, "inertia": 245.7},
            is_active=False,
        )
        row = version.to_bq_row()

        assert row["model_type"] == "batter_segmentation"
        assert row["algorithm"] == "kmeans"
        assert row["training_season"] == 2024
        assert json.loads(row["features"]) == ["ops", "iso", "k_rate", "bb_rate"]
        assert json.loads(row["model_params"])["n_clusters"] == 4

    def test_model_training_config_keys(self):
        """MODEL_TRAINING_CONFIG に必要なモデルが定義されている"""
        assert "batter_segmentation" in MODEL_TRAINING_CONFIG
        assert "pitcher_segmentation" in MODEL_TRAINING_CONFIG

    def test_config_has_algorithm(self):
        """各設定に algorithm が含まれている"""
        for model_type, config in MODEL_TRAINING_CONFIG.items():
            assert "algorithm" in config, f"{model_type} missing algorithm"


class TestTrainAndRegister:
    """train_and_register のテスト (モック)"""

    @patch.object(ModelRegistryService, '__init__', lambda self: None)
    def test_train_with_mock_data(self):
        """モックデータでモデル学習と登録を検証"""
        service = ModelRegistryService()
        service.bq_client = MagicMock()
        service.gcs_client = MagicMock()
        service.bucket_name = "test-bucket"
        service.bucket = MagicMock()

        np.random.seed(42)
        mock_df = pd.DataFrame({
            "ops": np.random.normal(0.750, 0.08, 100),
            "iso": np.random.normal(0.150, 0.04, 100),
            "k_rate": np.random.normal(22.0, 4.0, 100),
            "bb_rate": np.random.normal(8.5, 2.0, 100),
        })

        with patch.object(
            service, '_fetch_training_data', return_value=mock_df
        ), patch.object(
            service, '_upload_model'
        ), patch.object(
            service, '_upload_json'
        ), patch.object(
            service, '_insert_bq_metadata'
        ):
            version = service.train_and_register(
                model_type="batter_segmentation",
                season=2024,
            )

        assert version.model_type == "batter_segmentation"
        assert version.algorithm == "kmeans"
        assert version.training_season == 2024
        assert version.n_samples == 100
        assert "n_clusters" in version.model_params

    @patch.object(ModelRegistryService, '__init__', lambda self: None)
    def test_train_invalid_model_type(self):
        """不正な model_type で ValueError"""
        service = ModelRegistryService()
        with pytest.raises(ValueError, match="Unknown model_type"):
            service.train_and_register("invalid_model", 2024)

    @patch.object(ModelRegistryService, '__init__', lambda self: None)
    def test_train_empty_data(self):
        """空データで ValueError"""
        service = ModelRegistryService()
        service.bq_client = MagicMock()

        with patch.object(
            service, '_fetch_training_data', return_value=pd.DataFrame()
        ):
            with pytest.raises(ValueError, match="No training data"):
                service.train_and_register("batter_segmentation", 2024)


class TestLoadModel:
    """load_model のテスト"""

    @patch.object(ModelRegistryService, '__init__', lambda self: None)
    def test_load_no_active_version(self):
        """Active バージョンがない場合 FileNotFoundError"""
        service = ModelRegistryService()
        with patch.object(service, 'get_active_version', return_value=None):
            with pytest.raises(FileNotFoundError):
                service.load_model("batter_segmentation")


class TestPlayerSegmentationWithRegistry:
    """player_segmentation の Registry 連携テスト"""

    def test_load_or_fit_fallback(self):
        """Registry なしの場合、従来通り fit する"""
        from backend.app.services.player_segmentation import (
            PlayerSegmentationService,
        )

        with patch.object(
            PlayerSegmentationService, '__init__', lambda self: None
        ):
            svc = PlayerSegmentationService()
            svc.model_registry = None

            np.random.seed(42)
            X = pd.DataFrame({
                "ops": np.random.normal(0.750, 0.08, 50),
                "iso": np.random.normal(0.150, 0.04, 50),
                "k_rate": np.random.normal(22.0, 4.0, 50),
                "bb_rate": np.random.normal(8.5, 2.0, 50),
            })

            kmeans, scaler, X_scaled = svc._load_or_fit(
                "batter_segmentation", X
            )
            assert hasattr(kmeans, 'cluster_centers_')
            assert X_scaled.shape == (50, 4)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
