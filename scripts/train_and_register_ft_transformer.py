"""
FT-Transformer + K-means モデルの学習と Vertex AI Model Registry への登録スクリプト

Usage:
    python scripts/train_and_register_ft_transformer.py --model-type batter --season 2025
    python scripts/train_and_register_ft_transformer.py --model-type pitcher --season 2025
"""

import sys
import os
import argparse
import json
import tempfile
import logging
from pathlib import Path
from typing import Tuple, List, Dict

import pandas as pd
import numpy as np
import torch
import joblib
from google.cloud import bigquery, aiplatform
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
from dotenv import load_dotenv

# backend モジュールのパスを追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.services.ft_transformer import FTTransformerEncoder, train_ft_transformer

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PlayerSegmentationTrainer:
    """プレイヤーセグメンテーションモデルの学習と登録を行うクラス"""

    # Batter と Pitcher の特徴量定義
    BATTER_FEATURES = ['ops', 'iso', 'k_rate', 'bb_rate']
    PITCHER_FEATURES = ['era', 'k_9', 'gbpct']

    # BigQuery クエリテンプレート
    BATTER_QUERY = """
    SELECT
        season, name, team, ops, iso,
        (100 * so / pa) AS k_rate,
        (100 * bb / pa) AS bb_rate,
        pa, ab
    FROM `{project}.{dataset}.fact_batting_stats_with_risp`
    WHERE season = {season} AND pa >= 300
    ORDER BY ops DESC
    """

    PITCHER_QUERY = """
    SELECT
        season, name, team, era, whip,
        avg AS batting_average_against,
        k_9, bb_9, hr_9, gbpct, fbpct, ip, gs
    FROM `{project}.{dataset}.fact_pitching_stats_master`
    WHERE season = {season} AND gs > 0 AND ip > 90
    ORDER BY era ASC
    """

    def __init__(self, project_id: str, dataset_id: str, location: str = 'us-central1'):
        """
        Args:
            project_id: GCP プロジェクト ID
            dataset_id: BigQuery データセット ID
            location: Vertex AI のリージョン
        """
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.location = location

        # クライアント初期化
        self.bq_client = bigquery.Client(project=project_id)
        aiplatform.init(project=project_id, location=location)

        logger.info(f"Initialized trainer: project={project_id}, location={location}")

    def fetch_data(self, model_type: str, season: int) -> pd.DataFrame:
        """BigQuery からデータを取得"""
        if model_type == 'batter':
            query = self.BATTER_QUERY.format(
                project=self.project_id,
                dataset=self.dataset_id,
                season=season
            )
        elif model_type == 'pitcher':
            query = self.PITCHER_QUERY.format(
                project=self.project_id,
                dataset=self.dataset_id,
                season=season
            )
        else:
            raise ValueError(f"Invalid model_type: {model_type}. Must be 'batter' or 'pitcher'")

        logger.info(f"Fetching {model_type} data for season {season}...")
        df = self.bq_client.query(query).to_dataframe()
        logger.info(f"Fetched {len(df)} records")

        return df

    def train_model(
        self,
        df: pd.DataFrame,
        model_type: str,
        n_clusters: int = 4,
        embedding_dim: int = 16,
        epochs: int = 200
    ) -> Tuple[FTTransformerEncoder, StandardScaler, KMeans, np.ndarray]:
        """FT-Transformer + K-means モデルを学習"""
        # 特徴量を取得
        features = self.BATTER_FEATURES if model_type == 'batter' else self.PITCHER_FEATURES
        X = df[features]

        logger.info(f"Training {model_type} model with features: {features}")
        logger.info(f"  n_clusters={n_clusters}, embedding_dim={embedding_dim}, epochs={epochs}")

        # FT-Transformer を学習
        ft_model, scaler, embeddings = train_ft_transformer(
            X, n_features=len(features), epochs=epochs, embedding_dim=embedding_dim
        )

        # K-means でクラスタリング
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(embeddings)

        logger.info(f"Model trained successfully")

        return ft_model, scaler, kmeans, embeddings

    def evaluate_clustering(self, embeddings: np.ndarray, clusters: np.ndarray) -> Dict[str, float]:
        """クラスタリング品質を評価"""
        sil = silhouette_score(embeddings, clusters)
        ch = calinski_harabasz_score(embeddings, clusters)
        db = davies_bouldin_score(embeddings, clusters)

        metrics = {
            'silhouette': float(sil),
            'calinski_harabasz': float(ch),
            'davies_bouldin': float(db)
        }

        logger.info(f"Clustering evaluation metrics:")
        logger.info(f"  Silhouette Score:        {sil:.4f} (higher is better)")
        logger.info(f"  Calinski-Harabasz Index: {ch:.2f} (higher is better)")
        logger.info(f"  Davies-Bouldin Index:    {db:.4f} (lower is better)")

        return metrics

    def register_model(
        self,
        model: FTTransformerEncoder,
        scaler: StandardScaler,
        kmeans: KMeans,
        model_type: str,
        features: List[str],
        season: int,
        metrics: Dict[str, float]
    ) -> aiplatform.Model:
        """Vertex AI Model Registry にモデルを登録"""
        logger.info(f"Registering {model_type} model to Vertex AI Model Registry...")

        # 一時ディレクトリにモデルを保存
        with tempfile.TemporaryDirectory() as temp_dir:
            model_dir = Path(temp_dir)

            # モデルファイルを保存
            torch.save(model.state_dict(), model_dir / 'ft_transformer.pth')
            joblib.dump(scaler, model_dir / 'scaler.joblib')
            joblib.dump(kmeans, model_dir / 'kmeans.joblib')

            # メタデータを保存
            metadata = {
                'model_type': model_type,
                'algorithm': 'FT-Transformer + K-means',
                'features': features,
                'n_clusters': int(kmeans.n_clusters),
                'embedding_dim': int(model.embedding_dim),
                'season': season,
                'metrics': metrics
            }

            with open(model_dir / 'metadata.json', 'w') as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Models saved to temporary directory: {model_dir}")
            logger.info(f"Files: {list(model_dir.glob('*'))}")

            # Vertex AI Model Registry に登録
            display_name = f"player-segmentation-{model_type}-ft-transformer"

            model_resource = aiplatform.Model.upload(
                display_name=display_name,
                artifact_uri=str(model_dir),
                serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/pytorch-cpu.1-13:latest",
                description=f"FT-Transformer + K-means for {model_type} segmentation (Season {season})",
                labels={
                    "model_type": model_type,
                    "algorithm": "ft-transformer",
                    "season": str(season)
                }
            )

            logger.info(f"✅ Model registered successfully!")
            logger.info(f"   Model ID: {model_resource.name}")
            logger.info(f"   Display Name: {display_name}")
            logger.info(f"   Resource Name: {model_resource.resource_name}")

            return model_resource

    def run(
        self,
        model_type: str,
        season: int,
        n_clusters: int = 4,
        embedding_dim: int = 16,
        epochs: int = 200
    ) -> aiplatform.Model:
        """学習から登録までの全パイプラインを実行"""
        logger.info("=" * 70)
        logger.info(f"Starting training pipeline: model_type={model_type}, season={season}")
        logger.info("=" * 70)

        # 1. データ取得
        df = self.fetch_data(model_type, season)

        # 2. モデル学習
        ft_model, scaler, kmeans, embeddings = self.train_model(
            df, model_type, n_clusters, embedding_dim, epochs
        )

        # 3. 評価
        clusters = kmeans.predict(embeddings)
        metrics = self.evaluate_clustering(embeddings, clusters)

        # 4. Vertex AI Model Registry に登録
        features = self.BATTER_FEATURES if model_type == 'batter' else self.PITCHER_FEATURES
        model_resource = self.register_model(
            ft_model, scaler, kmeans, model_type, features, season, metrics
        )

        logger.info("=" * 70)
        logger.info("Training pipeline completed successfully!")
        logger.info("=" * 70)

        return model_resource


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description='Train and register FT-Transformer + K-means model to Vertex AI'
    )
    parser.add_argument(
        '--model-type',
        type=str,
        required=True,
        choices=['batter', 'pitcher'],
        help='Model type: batter or pitcher'
    )
    parser.add_argument(
        '--season',
        type=int,
        required=True,
        help='Season year (e.g., 2025)'
    )
    parser.add_argument(
        '--n-clusters',
        type=int,
        default=4,
        help='Number of clusters for K-means (default: 4)'
    )
    parser.add_argument(
        '--embedding-dim',
        type=int,
        default=16,
        help='Embedding dimension for FT-Transformer (default: 16)'
    )
    parser.add_argument(
        '--epochs',
        type=int,
        default=200,
        help='Number of training epochs (default: 200)'
    )

    args = parser.parse_args()

    # 環境変数をロード
    load_dotenv()
    project_id = os.getenv('GCP_PROJECT_ID')
    dataset_id = os.getenv('BIGQUERY_DATASET_ID')

    if not project_id or not dataset_id:
        logger.error("GCP_PROJECT_ID and BIGQUERY_DATASET_ID must be set in .env file")
        sys.exit(1)

    # トレーナーを初期化して実行
    trainer = PlayerSegmentationTrainer(project_id, dataset_id)

    try:
        model_resource = trainer.run(
            model_type=args.model_type,
            season=args.season,
            n_clusters=args.n_clusters,
            embedding_dim=args.embedding_dim,
            epochs=args.epochs
        )

        logger.info("\n" + "=" * 70)
        logger.info("NEXT STEPS:")
        logger.info("=" * 70)
        logger.info("1. Deploy this model to a Vertex AI Endpoint:")
        logger.info(f"   gcloud ai endpoints create --region=us-central1 --display-name=player-segmentation-{args.model_type}")
        logger.info(f"\n2. Deploy the model to the endpoint:")
        logger.info(f"   gcloud ai endpoints deploy-model ENDPOINT_ID \\")
        logger.info(f"     --region=us-central1 \\")
        logger.info(f"     --model={model_resource.name} \\")
        logger.info(f"     --display-name=ft-transformer-v1 \\")
        logger.info(f"     --machine-type=n1-standard-2 \\")
        logger.info(f"     --min-replica-count=1 \\")
        logger.info(f"     --max-replica-count=3")
        logger.info("\n3. Update the FastAPI service to call the Vertex AI Endpoint")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"Training pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
