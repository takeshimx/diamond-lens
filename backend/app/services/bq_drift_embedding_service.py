"""
Embedding-based semantic drift detection using BigQuery VECTOR_SEARCH.
既存の data_drift_service.py (KS/PSI) を補完する。
"""
import os
import logging
from datetime import date, timedelta
from typing import Optional
from google.cloud import bigquery

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "tksm-dash-test-25")
DATASET_ID = os.getenv("BIGQUERY_DATASET_ID", "mlb_analytics_dash_25")

logger = logging.getLogger(__name__)

# コサイン距離のしきい値（1 - cosine_similarity に相当）
DRIFT_THRESHOLDS = {
    "stable":   0.10,  # < 0.10: 安定
    "warning":  0.20,  # 0.10-0.20: 警告
    # >= 0.20: クリティカル
}


class BQDriftEmbeddingService:
    def __init__(self):
        self.client = bigquery.Client(project=PROJECT_ID)
        self.project = PROJECT_ID
        self.dataset = DATASET_ID

    def detect_semantic_drift(
        self,
        current_week: Optional[date] = None,
        baseline_weeks: int = 4,
    ) -> dict:
        """
        現在週のEmbeddingとベースライン（過去N週平均）のコサイン距離を計算して返す。

        Returns:
            {
                "semantic_drift_score": float,  # コサイン距離 (0〜1)
                "semantic_drift_status": str,   # "stable" / "warning" / "critical"
                "current_week": str,
                "baseline_week_count": int,
                "error": Optional[str]
            }
        """
        if current_week is None:
            current_week = self._get_latest_week()

        try:
            score = self._run_vector_search(current_week, baseline_weeks)
            status = self._classify(score)
            return {
                "semantic_drift_score": round(score, 4),
                "semantic_drift_status": status,
                "current_week": str(current_week),
                "baseline_week_count": baseline_weeks,
                "error": None,
            }
        except Exception as e:
            logger.error(f"BQ semantic drift detection failed: {e}")
            return {
                "semantic_drift_score": None,
                "semantic_drift_status": "unknown",
                "current_week": str(current_week),
                "baseline_week_count": baseline_weeks,
                "error": str(e),
            }

    def _get_latest_week(self) -> date:
        """snapshotsテーブルの最新week_startを取得する"""
        query = f"""
            SELECT MAX(week_start) AS latest
            FROM `{self.project}.{self.dataset}.pitcher_metrics_snapshots`
        """
        result = self.client.query(query).result()
        row = next(iter(result))
        return row["latest"] or date.today()

    def _run_vector_search(self, current_week: date, baseline_weeks: int) -> float:
        """
        VECTOR_SEARCHで現在週のEmbeddingとベースラインのコサイン距離を計算。
        ベースライン = 過去N週のEmbeddingをCENTROIDとして使用。
        """
        baseline_start = current_week - timedelta(weeks=baseline_weeks)

        query = f"""
        WITH current_snapshot AS (
            SELECT ml_generate_embedding AS embedding
            FROM `{self.project}.{self.dataset}.pitcher_metrics_snapshots`
            WHERE week_start = @current_week
            LIMIT 1
        ),
        baseline_snapshots AS (
            SELECT ml_generate_embedding AS embedding
            FROM `{self.project}.{self.dataset}.pitcher_metrics_snapshots`
            WHERE week_start >= @baseline_start
              AND week_start < @current_week
        ),
        -- ベースライン: 各次元の平均（セントロイド）を計算
        baseline_centroid AS (
            SELECT [AVG(e)] AS centroid_embedding
            -- ※ BQ ARRAYの次元ごとの平均はUNNEST+GROUP BYが必要（後述補足）
            FROM baseline_snapshots, UNNEST(embedding) AS e WITH OFFSET pos
            GROUP BY pos
            ORDER BY pos
        )
        SELECT
          1 - ML.DISTANCE(
            (SELECT embedding FROM current_snapshot),
            (SELECT centroid_embedding FROM baseline_centroid),
            'COSINE'
          ) AS cosine_distance  -- 距離なので小さいほど類似
        """
        # NOTE: BQでARRAY次元ごとのAVGは少し複雑なため、
        # シンプル版として VECTOR_SEARCH の distance をそのまま使うアプローチも可

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("current_week", "DATE", str(current_week)),
                bigquery.ScalarQueryParameter("baseline_start", "DATE", str(baseline_start)),
            ]
        )
        result = self.client.query(query, job_config=job_config).result()
        row = next(iter(result))
        if row["cosine_distance"] is None:
            raise ValueError("No snapshot data available for the specified week or baseline period")
        return float(row["cosine_distance"])

    def _classify(self, score: float) -> str:
        if score < DRIFT_THRESHOLDS["stable"]:
            return "stable"
        elif score < DRIFT_THRESHOLDS["warning"]:
            return "warning"
        return "critical"


# シングルトン
_instance: Optional[BQDriftEmbeddingService] = None

def get_bq_drift_embedding_service() -> BQDriftEmbeddingService:
    global _instance
    if _instance is None:
        _instance = BQDriftEmbeddingService()
    return _instance
