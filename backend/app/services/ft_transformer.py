"""
FT-Transformer Encoder for Player Segmentation
自己教師あり学習(特徴量再構成)で特徴量の埋め込みベクトルを生成する。

Architecture:
  Input features (e.g., ops, iso, k_rate, bb_rate)
  → Feature Tokenizer (各特徴量を独立にd_model次元に射影)
  → [CLS] トークン追加（初期状態は特に意味を持たない）
  → Transformer Encoder (Self-Attention で特徴量間の交互作用を学習)
  → [CLS] トークンの出力 = 選手の埋め込みベクトル
  → Decoder (再構成ヘッド、学習時のみ使用。学習後は削除)
"""
import logging
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler
from typing import Tuple

logger = logging.getLogger(__name__)


class FTTransformerEncoder(nn.Module):
    """
    FT-Transformer のエンコーダ部分。

    Feature Tokenizer:
        各数値特徴量を独立の線形層で d_model 次元に変換。
        例: ops (スカラー) → Linear(1, 32) → 32次元ベクトル

    [CLS] Token:
        学習可能なパラメータ。Transformer通過後に全特徴の情報を集約する。
        BERTの[CLS]トークンと同じ役割。

    Transformer Encoder:
        Self-Attention で特徴量間の関係を学習。
        「OPSが高い × K%が高い」のような交互作用を捉える。
    """
    def __init__(
        self,
        n_features: int, # 入力特徴量の数 (batter: 4, pitcher: 3)
        d_model: int = 32, # 各特徴量トークンの次元数
        n_heads: int = 4, # Attentionのヘッド数
        n_layers: int = 2, # Transformer Encoderの層数
        embedding_dim: int = 16, # 最終埋め込みベクトルの次元数（K-meansに渡す）
        dropout: float = 0.1,
    ):
        super().__init__()
        self.n_features = n_features
        self.d_model = d_model
        self.embedding_dim = embedding_dim

        # ---- Feature Tokenizer ----
        # 各特徴量ごとに独立の線形射影 (これがFT-Transformerの核心)
        # StandardScalerの代わりに、データ駆動で最適な変換を学習する
        self.feature_tokenizers = nn.ModuleList([
            nn.Linear(1, d_model) for _ in range(n_features)
        ])

        # ---- [CLS] Token ----
        # 全特徴量の情報を集約する学習可能なトークン
        self.cls_token = nn.Parameter(torch.randn(1, 1, d_model))

        # ---- Transformer Encoder ----
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=n_heads, # いくつの視点（Attention）で同時に特徴量間の関係を捉えるか
            dim_feedforward=d_model * 4, # FFN内部次元 = 4 * d_model (標準的)
            dropout=dropout,
            batch_first=True, # (batch, seq, feature) の形式（batch, n_features+1, d_model）。ここでの文脈では、（選手の数、項目の数（OPS, IOSなど）、ベクトルの長さ（次元数））
        )
        self.transformer = nn.TransformerEncoder(
            encoder_layer,
            num_layers=n_layers
        )

        # ---- Projection Head ----
        # [CLS]出力 (d_model) → 最終埋め込み (embedding_dim)
        self.projection = nn.Linear(d_model, embedding_dim)

        # ---- Decoder（学習時のみ: 埋め込み → 元の特徴量を再構成）----
        self.decoder = nn.Linear(embedding_dim, n_features)
    

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """
        入力特徴量 → 埋め込みベクトル

        Args:
            x: (batch_size, n_features) の数値特徴量テンソル
        Returns:
            (batch_size, embedding_dim) の埋め込みベクトル
        """
        batch_size = x.size(0)

        # 各特徴量を独立にトークン化
        # x[:, i:i+1] → (batch, 1) → Linear → (batch, d_model)
        tokens = [
            tokenizer(x[:, i : i + 1])
            for i, tokenizer in enumerate(self.feature_tokenizers)
        ]
        # tokens: list of (batch, d_model) → stack → (batch, n_features, d_model)
        tokens = torch.stack(tokens, dim=1)

        # [CLS] トークンを先頭に追加
        # cls: (1, 1, d_model) → expand → (batch, 1, d_model)
        cls = self.cls_token.expand(batch_size, -1, -1)
        # sequence: (batch, n_features + 1, d_model)
        sequence = torch.cat([cls, tokens], dim=1)

        # Transformer Encoder に通す
        # Self-Attention で特徴量間の関係性を学習
        encoded = self.transformer(sequence)

        # [CLS] トークンの出力を取り出す (先頭位置)
        cls_output = encoded[:, 0, :] # (batch, d_model)

        # Projection → 最終埋め込み
        embedding = self.projection(cls_output) # (batch, embedding_dim)
        return embedding

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        学習時: 埋め込み + 再構成出力を返す

        Returns:
            embedding: (batch, embedding_dim)
            reconstructed: (batch, n_features) — 元の特徴量の再構成
        """
        embedding = self.encode(x)
        reconstructed = self.decoder(embedding)
        return embedding, reconstructed


def train_ft_transformer(
    X: pd.DataFrame,
    n_features: int,
    d_model: int = 32,
    n_heads: int = 4,
    n_layers: int = 2,
    embedding_dim: int = 16,
    epochs: int = 200,
    lr: float = 1e-3,
    batch_size: int = 64,
)-> Tuple[FTTransformerEncoder, StandardScaler, np.ndarray]:
    """
    FT-Transformer を自己教師あり学習で訓練し、埋め込みベクトルを返す。

    学習の流れ:
      1. StandardScaler で正規化 (Transformerの学習安定のため)
      2. 特徴量再構成タスクで学習 (MSE Loss)
      3. 学習後のエンコーダで埋め込みベクトルを生成

    Args:
        X: 特徴量の DataFrame
        n_features: 特徴量数
        その他: ハイパーパラメータ

    Returns:
        (model, scaler, embeddings)
        - model: 学習済み FTTransformerEncoder
        - scaler: 推論時にも必要な StandardScaler
        - embeddings: (n_samples, embedding_dim) のnumpy配列
    """
    # Step 1: 正規化 (Transformerの勾配安定のため、Scalerは引き続き使う)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # numpy -> PyTorch tensor
    X_tensor = torch.FloatTensor(X_scaled)

    # Step 2: モデル初期化
    model = FTTransformerEncoder(
        n_features=n_features,
        d_model=d_model,
        n_heads=n_heads,
        n_layers=n_layers,
        embedding_dim=embedding_dim,
    )

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    # Step 3: 学習ループ
    # Switch to train mode
    model.train()
    dataset = torch.utils.data.TensorDataset(X_tensor)
    loader = torch.utils.data.DataLoader(
        dataset, batch_size=batch_size, shuffle=True
    )

    # MEMO: 要するに「データを小出しにする（Loader）→ 予測する（Forward）→ 怒られる（Loss）
    #                   → 反省する（Backward）→ 修正する（Step）」をひたすら繰り返しているだけ
    for epoch in range(epochs):
        total_loss = 0.0
        for (batch,) in loader:
            optimizer.zero_grad() # 前回の反省内容（勾配）をリセット
            _, reconstructed = model(batch) # Forward Propagation モデルにデータを流し込み、復元を試みる
            loss = criterion(reconstructed, batch) # 復元した値と、元の値を比較し、loss計算
            loss.backward() # Backward Propagation この誤差をゼロにするには、どの重みをどっちに回せばいいか、を出力から入力に向かって計算
            optimizer.step() # 重みの更新
            total_loss += loss.item()
        
        # 50周ごとに現在の成績をチェック
        if (epoch + 1) % 50 == 0:
            avg_loss = total_loss / len(loader)
            logger.info(f"  Epoch {epoch+1}/{epochs}, Loss: {avg_loss:.6f}")
    
    # Step 4: 埋め込みベクトル生成 (推論モード)
    # Switch to evaluation mode
    model.eval()
    with torch.no_grad():
        embeddings = model.encode(X_tensor).numpy()
    
    logger.info(
        f"FT-Transformer trained: {X_scaled.shape[0]} samples "
        f"→ {embeddings.shape[1]}d embeddings"
    )

    return model, scaler, embeddings


