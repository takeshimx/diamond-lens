"""
Model Registry Service
学習済み ML モデルを GCS に保存し、BigQuery でバージョン管理するサービス。
対応アルゴリズム: KMeans, LightGBM（拡張可能）
パイロット対象: player_segmentation.py の KMeans モデル
"""
import json
import logging
import tempfile
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
import joblib
import numpy as np
import pandas as pd
from google.cloud import bigquery, storage
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from backend.app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

REGISTRY_TABLE = settings.get_table_full_name("ml_model_registry")

# ============================================================
# データモデル
# ============================================================

@dataclass
class ModelVersion:
    """Metadata for a registry model version"""
    version: str
    model_type: str
    algorithm: str
    training_season: int
    trained_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    gcs_path: str = ""
    n_samples: int = 0
    features: List[str] = field(default_factory=list)
    model_params: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = False
    created_by: str = "system"

    def to_bq_row(self) -> Dict:
        """BigQuery 挿入用の辞書に変換"""
        return {
            "version": self.version,
            "model_type": self.model_type,
            "algorithm": self.algorithm,
            "training_season": self.training_season,
            "trained_at": self.trained_at,
            "gcs_path": self.gcs_path,
            "n_samples": self.n_samples,
            "features": json.dumps(self.features),
            "model_params": json.dumps(self.model_params),
            "is_active": self.is_active,
            "created_by": self.created_by,
        }


# ============================================================
# モデル別の学習設定
# ============================================================

MODEL_TRAINING_CONFIG = {
    "batter_segmentation": {
        "algorithm": "kmeans",
        "table": "fact_batting_stats_with_risp",
        "features": ["ops", "iso", "k_rate", "bb_rate"],
        "query_template": """
            SELECT
                ops,
                iso,
                (100.0 * so / pa) AS k_rate,
                (100.0 * bb / pa) AS bb_rate
            FROM `{table_full_name}`
            WHERE season = {season}
                AND pa >= {min_sample}
        """,
        "min_sample": 300,
        "n_clusters": 4,
        "random_state": 42,
    },
    "pitcher_segmentation": {
        "algorithm": "kmeans",
        "table": "fact_pitching_stats_master",
        "features": ["era", "k_9", "gbpct"],
        "query_template": """
            SELECT
                era,
                k_9,
                gbpct
            FROM `{table_full_name}`
            WHERE season = {season}
                AND gs > 0 AND ip > {min_sample}
        """,
        "min_sample": 90,
        "n_clusters": 4,
        "random_state": 42,
    },
}


# ============================================================
# Model Registry Service
# ============================================================
class ModelRegistryService:
    """
    ML モデルのバージョン管理サービス
    使用例:
        svc = ModelRegistryService()
        version = svc.train_and_register("batter_segmentation", 2024)
        svc.promote_version("batter_segmentation", version.version)
        kmeans, scaler, meta = svc.load_model("batter_segmentation")
    """
    def __init__(self):
        self.bq_client = bigquery.Client(project=settings.gcp_project_id)
        self.gcs_client = storage.Client(project=settings.gcp_project_id)
        self.bucket_name = settings.gcs_bucket_name
        self.bucket = self.gcs_client.bucket(self.bucket_name)
    
    # ----------------------------------------------------------
    # Public: モデル学習 & 登録
    # ----------------------------------------------------------
    def train_and_register(
        self, model_type: str, season: int
    ) -> ModelVersion:
        """
        指定シーズンのデータでモデルを学習し、GCS に保存、
        BigQuery にメタデータを記録する。
        """
        if model_type not in MODEL_TRAINING_CONFIG:
            raise ValueError(
                f"Unknown model_type: {model_type}. "
                f"Available: {list(MODEL_TRAINING_CONFIG.keys())}"
            )
        config = MODEL_TRAINING_CONFIG[model_type]

        # Step 1: Fetch Training Data
        df = self._fetch_training_data(config, season)
        if df.empty:
            raise ValueError(f"No training data found for season {season}")
        
        # Step 2: Train Model
        X = df[config["features"]]
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        kmeans = KMeans(
            n_clusters=config["n_clusters"],
            random_state=config["random_state"],
        )
        kmeans.fit(X_scaled)

        # Step 3: Generate Version
        now = datetime.now(timezone.utc)
        version_str = f"v{now.strftime('%Y%m%d_%H%M%S')}_s{season}"
        gcs_path = f"models/{model_type}/{version_str}/model.joblib"

        model_params = {
            "n_clusters": config["n_clusters"],
            "random_state": config["random_state"],
            "inertia": round(float(kmeans.inertia_), 4),
            "cluster_centers": kmeans.cluster_centers_.tolist(),
        }

        version = ModelVersion(
            version=version_str,
            model_type=model_type,
            algorithm=config["algorithm"],
            training_season=season,
            trained_at=now.isoformat(),
            gcs_path=f"gs://{self.bucket_name}/{gcs_path}",
            n_samples=len(df),
            features=config["features"],
            model_params=model_params,
            is_active=False,
            created_by="system",
        )

        # Step 4: Save Model to GCS
        model_artifact = {"kmeans": kmeans, "scaler": scaler} # scalerは推論時に必要のため、セットで一つのモデルと考える
        self._upload_model(gcs_path, model_artifact)

        # Save metadata to GCS
        metadata_path = f"models/{model_type}/{version_str}/metadata.json"
        self._upload_json(metadata_path, version.to_bq_row())

        # Step 5: Save metadata to BigQuery
        self._insert_bq_metadata(version)

        logger.info(
            f"Model registered: {model_type} {version_str} "
            f"({len(df)} samples, inertia={kmeans.inertia_:.2f})"
        )

        return version
    
    # ----------------------------------------------------------
    # Public: モデルロード
    # ----------------------------------------------------------

    def load_model(
        self, model_type: str
    ) -> Tuple[KMeans, StandardScaler, ModelVersion]:
        """
        Active バージョンのモデルを GCS からロードする。
        Returns:
            (kmeans, scaler, version_metadata)
        Raises:
            FileNotFoundError: active バージョンが存在しない場合
        """
        active = self.get_active_version(model_type)
        if not active:
            raise FileNotFoundError(
                f"No active model found for {model_type}. "
                f"Train and promote a version first."
            )
        # GCS パスから bucket 相対パスを取得
        gcs_relative = active.gcs_path.replace(
            f"gs://{self.bucket_name}/", ""
        )
        artifact = self._download_model(gcs_relative)
        logger.info(
            f"Model loaded: {model_type} {active.version} "
            f"(trained on season {active.training_season})"
        )
        return artifact["kmeans"], artifact["scaler"], active
    
    # ----------------------------------------------------------
    # Public: バージョン昇格
    # ----------------------------------------------------------
    def promote_version(self, model_type: str, version: str) -> None:
        """
        指定バージョンを active に昇格する。
        既存の active バージョンは inactive に降格。
        """
        # 既存 active を全て inactive に
        query = f"""
            UPDATE `{REGISTRY_TABLE}`
            SET is_active = FALSE
            WHERE model_type = @model_type AND is_active = TRUE
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "model_type", "STRING", model_type
                ),
            ]
        )
        self.bq_client.query(query, job_config=job_config).result()
        # 対象バージョンを active に
        query = f"""
            UPDATE `{REGISTRY_TABLE}`
            SET is_active = TRUE
            WHERE model_type = @model_type AND version = @version
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "model_type", "STRING", model_type
                ),
                bigquery.ScalarQueryParameter(
                    "version", "STRING", version
                ),
            ]
        )
        self.bq_client.query(query, job_config=job_config).result()
        logger.info(f"Promoted {model_type} to version: {version}")
    
    # ----------------------------------------------------------
    # Public: バージョン一覧 / Active 取得
    # ----------------------------------------------------------
    def list_versions(self, model_type: str) -> List[Dict]:
        """登録済みバージョンの一覧を取得"""
        query = f"""
            SELECT *
            FROM `{REGISTRY_TABLE}`
            WHERE model_type = @model_type
            ORDER BY trained_at DESC
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "model_type", "STRING", model_type
                ),
            ]
        )
        result = self.bq_client.query(query, job_config=job_config)
        return [dict(row) for row in result]
    def get_active_version(self, model_type: str) -> Optional[ModelVersion]:
        """Active バージョンのメタデータを取得"""
        query = f"""
            SELECT *
            FROM `{REGISTRY_TABLE}`
            WHERE model_type = @model_type AND is_active = TRUE
            LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "model_type", "STRING", model_type
                ),
            ]
        )
        rows = list(self.bq_client.query(query, job_config=job_config))
        if not rows:
            return None
        row = dict(rows[0])
        return ModelVersion(
            version=row["version"],
            model_type=row["model_type"],
            algorithm=row["algorithm"],
            training_season=row["training_season"],
            trained_at=row["trained_at"],
            gcs_path=row["gcs_path"],
            n_samples=row.get("n_samples", 0),
            features=json.loads(row.get("features", "[]")),
            model_params=json.loads(row.get("model_params", "{}")),
            is_active=row["is_active"],
            created_by=row.get("created_by", "system"),
        )
    
    # ----------------------------------------------------------
    # Private: GCS 操作
    # ----------------------------------------------------------

    def _upload_model(self, gcs_path: str, artifact: Dict) -> None:
        """Serialize with joblib and upload to GCS"""
        with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as f:
            joblib.dump(artifact, f.name)
            blob = self.bucket.blob(gcs_path)
            blob.upload_from_filename(f.name)
    
    def _download_model(self, gcs_path: str) -> Dict:
        """Download Model from GCS and load with joblib"""
        with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as f:
            blob = self.bucket.blob(gcs_path)
            blob.download_to_filename(f.name)
            return joblib.load(f.name)
    
    def _upload_json(self, gcs_path: str, data: Dict) -> None:
        """Upload JSON to GCS"""
        blob = self.bucket.blob(gcs_path)
        blob.upload_from_string(
            json.dumps(data, indent=2, default=str), 
            content_type="application/json"
        )
    
    # ----------------------------------------------------------
    # Private: BigQuery メタデータ記録
    # ----------------------------------------------------------
    def _insert_bq_metadata(self, version: ModelVersion) -> None:
        """BigQuery にモデルメタデータを挿入 (DML INSERT — streaming buffer を使わない)"""
        query = f"""
            INSERT INTO `{REGISTRY_TABLE}`
            (version, model_type, algorithm, training_season, trained_at,
             gcs_path, n_samples, features, model_params, is_active, created_by)
            VALUES
            (@version, @model_type, @algorithm, @training_season, @trained_at,
             @gcs_path, @n_samples, @features, @model_params, @is_active, @created_by)
        """
        row = version.to_bq_row()
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("version", "STRING", row["version"]),
                bigquery.ScalarQueryParameter("model_type", "STRING", row["model_type"]),
                bigquery.ScalarQueryParameter("algorithm", "STRING", row["algorithm"]),
                bigquery.ScalarQueryParameter("training_season", "INT64", row["training_season"]),
                bigquery.ScalarQueryParameter("trained_at", "STRING", row["trained_at"]),
                bigquery.ScalarQueryParameter("gcs_path", "STRING", row["gcs_path"]),
                bigquery.ScalarQueryParameter("n_samples", "INT64", row["n_samples"]),
                bigquery.ScalarQueryParameter("features", "STRING", row["features"]),
                bigquery.ScalarQueryParameter("model_params", "STRING", row["model_params"]),
                bigquery.ScalarQueryParameter("is_active", "BOOL", row["is_active"]),
                bigquery.ScalarQueryParameter("created_by", "STRING", row["created_by"]),
            ]
        )
        try:
            self.bq_client.query(query, job_config=job_config).result()
        except Exception as e:
            logger.error(f"BigQuery DML insert failed: {e}")
    def _fetch_training_data(
        self, config: Dict, season: int
    ) -> pd.DataFrame:
        """BigQuery から学習データを取得"""
        table_full_name = settings.get_table_full_name(config["table"])
        query = config["query_template"].format(
            table_full_name=table_full_name,
            season=season,
            min_sample=config["min_sample"],
        )
        try:
            return self.bq_client.query(query).to_dataframe()
        except Exception as e:
            logger.error(f"Training data fetch failed: {e}")
            return pd.DataFrame()