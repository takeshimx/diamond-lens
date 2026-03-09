"""FT-Transformer Encoder のユニットテスト"""
import numpy as np
import pandas as pd
import torch
import pytest
from backend.app.services.ft_transformer import (
    FTTransformerEncoder,
    train_ft_transformer,
)


class TestFTTransformerEncoder:
    """モデルアーキテクチャのテスト"""

    def test_encode_output_shape(self):
        """encode() の出力形状が (batch, embedding_dim) であること"""
        model = FTTransformerEncoder(n_features=4, embedding_dim=16)
        x = torch.randn(10, 4)  # 10選手, 4特徴量
        embedding = model.encode(x)
        assert embedding.shape == (10, 16)

    def test_forward_returns_embedding_and_reconstruction(self):
        """forward() が (embedding, reconstructed) を返すこと"""
        model = FTTransformerEncoder(n_features=3)
        x = torch.randn(5, 3)
        embedding, reconstructed = model(x)
        assert embedding.shape == (5, 16)  # default embedding_dim
        assert reconstructed.shape == (5, 3)  # 元の特徴量数に再構成

    def test_different_feature_counts(self):
        """batter(4特徴量) と pitcher(3特徴量) の両方で動作すること"""
        for n_feat in [3, 4]:
            model = FTTransformerEncoder(n_features=n_feat)
            x = torch.randn(8, n_feat)
            emb = model.encode(x)
            assert emb.shape == (8, 16)


class TestTrainFTTransformer:
    """学習関数のテスト"""

    def test_train_produces_embeddings(self):
        """train_ft_transformer がembeddingsを正しい形状で返すこと"""
        # ダミーデータ (50選手, 4特徴量)
        np.random.seed(42)
        X = pd.DataFrame({
            'ops': np.random.uniform(0.5, 1.0, 50),
            'iso': np.random.uniform(0.05, 0.35, 50),
            'k_rate': np.random.uniform(10, 35, 50),
            'bb_rate': np.random.uniform(3, 15, 50),
        })
        model, scaler, embeddings = train_ft_transformer(
            X, n_features=4, epochs=10  # テスト用に少ないepoch
        )
        assert embeddings.shape == (50, 16)
        assert model is not None
        assert scaler is not None

    def test_reconstruction_loss_decreases(self):
        """学習でlossが減少すること (学習が機能している確認)"""
        np.random.seed(42)
        X = pd.DataFrame({
            'a': np.random.randn(100),
            'b': np.random.randn(100),
            'c': np.random.randn(100),
        })
        # epochs少なめでも loss が初期より下がればOK
        model, scaler, _ = train_ft_transformer(
            X, n_features=3, epochs=50
        )
        # 推論して再構成精度を確認
        from sklearn.preprocessing import StandardScaler
        X_scaled = scaler.transform(X)
        X_tensor = torch.FloatTensor(X_scaled)
        model.eval()
        with torch.no_grad():
            _, recon = model(X_tensor)
        mse = ((recon.numpy() - X_scaled) ** 2).mean()
        assert mse < 1.0  # 正規化済みデータなので、学習が機能すればMSE < 1
