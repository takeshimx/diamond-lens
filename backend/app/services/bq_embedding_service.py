"""
BQ Embedding Service
BQ ML の ML.GENERATE_EMBEDDING + VECTOR_SEARCH を使い、
ユーザークエリと類似した低品質クエリを検索するサービス。
サーバレス・Pay-as-you-go: BQ クエリ実行時のみ Vertex AI API をコール。
"""
import os
import logging
from typing import Optional
from google.cloud import bigquery

logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "tksm-dash-test-25")
DATASET_ID = os.getenv("BIGQUERY_DATASET_ID", "mlb_analytics_dash_25")
EMBEDDING_MODEL = f"{PROJECT_ID}.{DATASET_ID}.query_embedding_model"
EMBEDDINGS_TABLE = f"{PROJECT_ID}.{DATASET_ID}.llm_query_embeddings"

# 類似度の閾値: コサイン距離 0.15 以下なら「似ている」と判定
# （0=完全一致, 1=正反対。0.15は約86%以上の類似度に相当）
SIMILARITY_THRESHOLD = 0.15
# 検索する類似事例の最大数
TOP_K = 3


class BQEmbeddingService:
    """Semantic search service using BQ ML Embeddings"""

    def __init__(self):
        try:
            self.client = bigquery.Client(project=PROJECT_ID)
        except Exception as e:
            logger.warning(f"BQEmbeddingService init failed: {e}")
            self.client = None

    def check_quality_warning(self, query_text: str) -> dict:
        """
        クエリテキストと類似した過去の低品質事例をBQ VECTOR_SEARCHで検索する。
        
        Args:
            query_text: ユーザーのクエリ（自然言語）
        Returns:
            {
                "has_warning": bool,        # True なら警告あり
                "similar_count": int,       # 類似した低品質事例の数
                "top_failure_category": str # 最も多い失敗カテゴリ
            }
        """
        if not self.client or not query_text:
            return {"has_warning": False, "similar_count": 0, "top_failure_category": None}
        
        try:
            # VECTOR_SEARCH: BQ の組み込み関数。embedding テーブルに対して
            # ベクター化されたユーザークエリを保存するのでなく、保存された過去の低品質クエリを参照、比較する。
            # クエリのベクトルで近傍探索を行う。
            # ML.GENERATE_EMBEDDING はここで1回だけ Vertex AI を呼ぶ（Pay-as-you-go
            sql = f"""
            SELECT
                COUNT(*) AS similar_count
            FROM
                VECTOR_SEARCH(
                    TABLE `{EMBEDDINGS_TABLE}`,
                    'query_embedding',
                    (
                        SELECT ml_generate_embedding_result AS query_embedding
                        FROM ML.GENERATE_EMBEDDING(
                            MODEL `{EMBEDDING_MODEL}`,
                            (SELECT @query_text AS content)
                        )
                    ),
                    top_k => {TOP_K},
                    distance_threshold => {SIMILARITY_THRESHOLD}
                )
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("query_text", "STRING", query_text)
                ]
            )
            result = self.client.query(sql, job_config=job_config).result()
            row = next(iter(result), None)

            if row and row.similar_count > 0:
                return {
                    "has_warning": True,
                    "similar_count": row.similar_count,
                    "top_failure_category": None,
                }
            return {"has_warning": False, "similar_count": 0, "top_failure_category": None}
        
        except Exception as e:
            # 警告チェックの失敗は本来のレスポンスをブロックしない
            logger.error(f"Quality warning check failed: {e}")
            return {"has_warning": False, "similar_count": 0, "top_failure_category": None}


# Singleton
_embedding_service: Optional[BQEmbeddingService] = None

def get_bq_embedding_service() -> BQEmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = BQEmbeddingService()
    return _embedding_service