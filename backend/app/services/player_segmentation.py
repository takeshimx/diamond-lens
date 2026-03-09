from typing import Dict, List
from google.cloud import bigquery
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from backend.app.config.settings import get_settings
from backend.app.services.model_registry_service import ModelRegistryService
import numpy as np
import logging

settings = get_settings()
logger = logging.getLogger(__name__)


class PlayerSegmentationService:
    """Service for player segmentation using k-means clustering."""

    def __init__(self):
        self.client = bigquery.Client()

        # Model Registry Service（ロード失敗時は None → fallback to fit）
        try:    
            self.model_registry = ModelRegistryService()
        except Exception:
            self.model_registry = None

        # Batter cluster labels
        self.batter_cluster_labels = {
            0: "Solid Regular Hitters",
            1: "Elite Contact Hitters",
            2: "Super Elite Sluggers",
            3: "Struggling Hitters"
        }

        # Pitcher cluster labels
        self.pitcher_cluster_labels = {
            0: "Elite Balanced Aces",
            1: "Struggling Fly Ball Pitchers",
            2: "Strikeout Dominant Aces",
            3: "Reliable Mid-Tier Starters"
        }
    
    def _load_or_fit(
        self, model_type: str, X: pd.DataFrame, n_clusters: int = 4
    ):
        """
        Registry に active モデルがあればロード、なければ従来通り fit。
        Returns:
            (kmeans, scaler, X_scaled)
        """
        # Registry からロード
        if self.model_registry:
            try:
                artifact, meta = self.model_registry.load_model(model_type)
                kmeans = artifact["kmeans"]
                scaler = artifact["scaler"]
                X_scaled = scaler.transform(X)
                logger.info(
                    f"Loaded model from registry: {model_type} "
                    f"{meta.version} (season {meta.training_season})"
                )
                return kmeans, scaler, X_scaled
            except FileNotFoundError:
                logger.info(f"No active model for {model_type}, fitting new")
            except Exception as e:
                logger.warning(f"Registry load failed, fallback to fit: {e}")
        
        # Fallback: fit new model
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        kmeans = KMeans(
            n_clusters=n_clusters,
            random_state=42,
        )
        kmeans.fit(X_scaled)
        return kmeans, scaler, X_scaled
    
    
    def _load_or_fit_ft(self, model_type: str, X: pd.DataFrame):
        """
        FT-Transformer ベースのエンベディング生成。
        Registry に active な FTTransformer モデルがあればロード、なければエラー。

        NOTE: torch は本番環境 (Cloud Run) にはインストールされていないため、
        ローカルで学習 → GCS に登録済みのモデルをロードする運用を想定。
        torch が未インストールの場合はエラーを返す。

        Returns:
            (model, scaler, embeddings)
        """
        try:
            import torch
            from backend.app.services.ft_transformer import (
                FTTransformerEncoder,
                train_ft_transformer,
            )
        except ImportError:
            raise RuntimeError(
                "FT-Transformer requires PyTorch. "
                "Install torch locally and train via model registry, "
                "then register the model to GCS."
            )

        # Load from registry
        if self.model_registry:
            try:
                artifact, meta = self.model_registry.load_model(model_type)
                # FTTransformer の場合、artifact に model_state_dict が入っている
                if meta.algorithm == "ft_transformer" and "model_state_dict" in artifact:
                    model = FTTransformerEncoder(
                        n_features=len(meta.features),
                        **meta.model_params.get("architecture", {})
                    )
                    model.load_state_dict(artifact["model_state_dict"])
                    model.eval()

                    scaler = artifact["scaler"]
                    X_scaled = scaler.transform(X)
                    X_tensor = torch.FloatTensor(X_scaled)
                    with torch.no_grad():
                        embeddings = model.encode(X_tensor).numpy()

                    logger.info(
                        f"Loaded FT-Transformer from registry: {model_type} "
                        f"{meta.version} (season {meta.training_season})"
                    )
                    return model, scaler, embeddings
            except FileNotFoundError:
                logger.info(f"No active FT model for {model_type}, training new")
            except Exception as e:
                logger.warning(f"FT Registry load failed, fallback to train: {e}")

        # Fallback: train new model (ローカル環境のみ)
        n_features = X.shape[1]
        model, scaler, embeddings = train_ft_transformer(X, n_features=n_features)
        return model, scaler, embeddings

    
    def get_batter_segmentation(
        self, season: int = 2025, min_pa: int = 300,
        use_ft_transformer: bool = False
    ) -> Dict:
        """
        Perform K-means clustering on batters.

        Args:
            season (int): The season year
            min_pa (int): The minimum plate appearances
        
        Returns:
            Dict: A dictionary containing the batter segmentation results.
        """
        query = f"""
        SELECT
            season,
            name,
            team,
            ops,
            iso,
            (100 * so / pa) AS k_rate,
            (100 * bb / pa) AS bb_rate,
            pa,
            ab
        FROM `{settings.get_table_full_name('fact_batting_stats_with_risp')}`
        WHERE season = {season}
            AND pa >= {min_pa}
        ORDER BY ops DESC
        """

        try:
            df = self.client.query(query).to_dataframe()

            if df.empty:
                return {"error": True, "message": "No data found"}
            
            # features
            features = ['ops', 'iso', 'k_rate', 'bb_rate']
            X = df[features]

            if use_ft_transformer:
                # ---- FT-Transformer モード ----
                model, scaler, embeddings = self._load_or_fit_ft("batter_segmentation_ft", X)
                # 埋め込みベクトルに対して K-means
                kmeans = KMeans(n_clusters=4, random_state=42)
                df["cluster"] = kmeans.fit_predict(embeddings)
            else:
                # Standardize features and K-means clustering
                # Load or fit
                kmeans, scaler, X_scaled = self._load_or_fit("batter_segmentation", X)
                df['cluster'] = kmeans.predict(X_scaled)
            
            df['cluster_name'] = df['cluster'].map(self.batter_cluster_labels)

            # Cluster statistics
            cluster_stats = df.groupby('cluster')[features].mean().round(3)
            cluster_counts = df['cluster'].value_counts().sort_index()

            player_data = df.to_dict('records')

            # Clusters Summary
            cluster_summary = []
            for cluster_id in range(4):
                cluster_summary.append({
                    "cluster_id": int(cluster_id),
                    "cluster_name": self.batter_cluster_labels[cluster_id],
                    "count": int(cluster_counts[cluster_id]),
                    "avg_ops": float(cluster_stats.loc[cluster_id, 'ops']),
                    "avg_iso": float(cluster_stats.loc[cluster_id, 'iso']),
                    "avg_k_rate": float(cluster_stats.loc[cluster_id, 'k_rate']),
                    "avg_bb_rate": float(cluster_stats.loc[cluster_id, 'bb_rate'])
                })
            
            return {
                "error": False,
                "season": season,
                "total_players": len(df),
                "cluster_summary": cluster_summary,
                "players": player_data
            }
        
        except Exception as e:
            return {"error": True, "message": str(e)}

    def get_pitcher_segmentation(self, season: int = 2025, min_ip: int = 90, use_ft_transformer: bool = False) -> Dict:
        """
        Perform K-means clustering on pitchers.

        Args:
            season (int): The season year
            min_ip (int): The minimum innings pitched

        Returns:
            Dict: A dictionary containing the pitcher segmentation results.
        """
        query = f"""
        SELECT
            season,
            name,
            team,
            era,
            whip,
            avg AS batting_average_against,
            k_9,
            bb_9,
            hr_9,
            gbpct,
            fbpct,
            ip,
            gs
        FROM `{settings.get_table_full_name('fact_pitching_stats_master')}`
        WHERE season = {season}
            AND gs > 0 AND ip > {min_ip} -- only starting pitchers
        ORDER BY era ASC
        """

        try:
            df = self.client.query(query).to_dataframe()

            if df.empty:
                return {"error": True, "message": "No data found"}

            # features
            features = ['era', 'k_9', 'gbpct']
            X = df[features]

            if use_ft_transformer:
                # ---- FT-Transformer モード ----
                model, scaler, embeddings = self._load_or_fit_ft("pitcher_segmentation_ft", X)
                # 埋め込みベクトルに対して K-means
                kmeans = KMeans(n_clusters=4, random_state=42)
                df["cluster"] = kmeans.fit_predict(embeddings)
            else:
                # Standardize features and K-means clustering
                # Load or fit
                kmeans, scaler, X_scaled = self._load_or_fit("pitcher_segmentation", X)
                df['cluster'] = kmeans.predict(X_scaled)
            
            df['cluster_name'] = df['cluster'].map(self.pitcher_cluster_labels)

            # Cluster statistics
            cluster_stats = df.groupby('cluster')[features].mean().round(3)
            cluster_counts = df['cluster'].value_counts().sort_index()

            player_data = df.to_dict('records')

            # Clusters Summary
            cluster_summary = []
            for cluster_id in range(4):
                # Get all pitchers in this cluster
                cluster_pitchers = df[df['cluster'] == cluster_id]

                cluster_summary.append({
                    "cluster_id": int(cluster_id),
                    "cluster_name": self.pitcher_cluster_labels[cluster_id],
                    "count": int(cluster_counts[cluster_id]),
                    # Clustering features
                    "avg_era": float(cluster_pitchers['era'].mean()),
                    "avg_k_9": float(cluster_pitchers['k_9'].mean()),
                    "avg_gbpct": float(cluster_pitchers['gbpct'].mean()),
                    # Additional reference metrics
                    "avg_whip": float(cluster_pitchers['whip'].mean()),
                    "avg_bb_9": float(cluster_pitchers['bb_9'].mean()),
                    "avg_hr_9": float(cluster_pitchers['hr_9'].mean()),
                    "avg_ip": float(cluster_pitchers['ip'].mean())
                })

            return {
                "error": False,
                "season": season,
                "total_players": len(df),
                "cluster_summary": cluster_summary,
                "players": player_data
            }

        except Exception as e:
            return {"error": True, "message": str(e)}