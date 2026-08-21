"""
Glossary RAG Service

docs/knowledge/*.md 由来の用語集チャンクを BigQuery 上でセマンティック検索する。
サーバレス・Pay-as-you-go: 検索 1 回につき Vertex AI の埋め込み API を 1 コールのみ。

設計:
  - VECTOR_SEARCH ではなく ML.DISTANCE を使う。
    VECTOR_SEARCH は第 1 引数がテーブル固定でサブクエリを取れず、
    category による事前フィルタができないため（打者の質問に投手チャンクが
    返る誤検索を構造的に防ぐには、フィルタが必須）。
    件数が増えたらベクトルインデックス + VECTOR_SEARCH へ切り替える。
  - task_type='RETRIEVAL_QUERY' を指定し、文書側 ('RETRIEVAL_DOCUMENT') と
    非対称な埋め込みを生成する。
"""
from __future__ import annotations

import os
from typing import Optional

from google.cloud import bigquery

from backend.app.utils.structured_logger import get_logger

logger = get_logger("glossary-rag")

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "tksm-dash-test-25")
DATASET_ID = os.getenv("BIGQUERY_DATASET_ID", "mlb_analytics_dash_25")
EMBEDDINGS_TABLE = f"{PROJECT_ID}.{DATASET_ID}.glossary_embeddings"
EMBEDDING_MODEL = f"{PROJECT_ID}.{DATASET_ID}.query_embedding_model"

# Phase C の評価ハーネス (backend/scripts/run_retrieval_eval.py) で確定した値。
# 2026-08-20 測定 (10 問 / top_k=5):
#   0.275 以上に緩めても正解保持率は 0.800 のまま増えず、無関係な結果だけが増える
#   (0.275 -> 3.00 件/問、0.30 -> 3.40 件/問)。
#   0.275 未満に締めると「該当なし」が発生し始める。
# 注意: 正解と不正解の距離分布は重なっており
#       (最近傍の不正解 0.1684 < 最近傍の正解 0.1816)、閾値調整では精度は上がらない。
#       精度改善には順位付け自体の変更 (リランク等) が必要。
DEFAULT_TOP_K = 5
DEFAULT_DISTANCE_THRESHOLD = 0.275

VALID_CATEGORIES = ("batting", "pitching", "statcast")

# 検索対象から除外するカテゴリ。BQ のデータは残したまま無効化する。
# rules (公式ルール PDF 897 チャンク) は 2026-08-21 時点で検索精度が実用水準に
# 達していないため除外している。分割を作り直しても命中@3 は 0.333 のままで、
# 用語集 (命中@3 1.000) の足を引っ張る状態だった。
# 再開する場合はここから外し、run_retrieval_eval で rule 型を再測定すること。
EXCLUDED_CATEGORIES = ("rules",)

DEFAULT_RERANK_CANDIDATES = 10   # リランク時に取得する候補数


class GlossaryRAGService:
    """用語集チャンクのセマンティック検索"""

    def __init__(self) -> None:
        self._client: Optional[bigquery.Client] = None
    
    @property
    def client(self) -> Optional[bigquery.Client]:
        if self._client is None:
            try:
                self._client = bigquery.Client(project=PROJECT_ID)
            except Exception as e:
                logger.warning(f"BigQuery client init failed: {e}")
                return None
        return self._client
    
    def search(
        self,
        query_text: str,
        top_k: int = DEFAULT_TOP_K,
        category: Optional[str] = None,
        distance_threshold: float = DEFAULT_DISTANCE_THRESHOLD,
        rerank: bool = False,
    ) -> list[dict]:
        """用語集から関連チャンクを検索する。

        Args:
            query_text: ユーザーの質問（日本語可。多言語モデルで英語文書を引ける）
            top_k: 取得する最大件数
            category: 'batting' / 'pitching' / 'statcast' で絞り込む。
                      None なら全カテゴリ横断。
            distance_threshold: コサイン距離の上限。これを超える結果は捨てる。
            rerank: True の場合、LLM を使って関連性の高い順に並べ直す。

        Returns:
            [{"section", "source", "category", "chunk_text", "distance"}, ...]
            距離の昇順。該当なし・失敗時は空リスト（fail-open）。
        """
        if not self.client or not query_text or not query_text.strip():
            return []

        # 未知の category はフィルタなしに倒す（誤った値で 0 件になるより良い）
        if category not in VALID_CATEGORIES:
            if category is not None:
                logger.warning(f"unknown category ignored: {category}")
            category = None

        # リランクする場合は候補を広めに取る。並べ直す材料がないと意味がないため。
        fetch_k = max(top_k, DEFAULT_RERANK_CANDIDATES) if rerank else top_k

        sql = f"""
        WITH q AS (
          SELECT ml_generate_embedding_result AS qv
          FROM ML.GENERATE_EMBEDDING(
            MODEL `{EMBEDDING_MODEL}`,
            (SELECT @query_text AS content),
            STRUCT(TRUE AS flatten_json_output, 'RETRIEVAL_QUERY' AS task_type)
          )
        )
        SELECT
          e.section,
          e.source,
          e.category,
          e.chunk_text,
          ML.DISTANCE(e.embedding, q.qv, 'COSINE') AS distance
        FROM `{EMBEDDINGS_TABLE}` e, q
        WHERE (@category IS NULL OR e.category = @category)
          AND e.category NOT IN UNNEST(@excluded)
        ORDER BY distance ASC
        LIMIT @top_k
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("query_text", "STRING", query_text),
                bigquery.ScalarQueryParameter("category", "STRING", category),
                bigquery.ScalarQueryParameter("top_k", "INT64", fetch_k),
                bigquery.ArrayQueryParameter(
                    "excluded", "STRING", list(EXCLUDED_CATEGORIES)
                ),
            ]
        )

        try:
            rows = list(self.client.query(sql, job_config=job_config).result())
        except Exception as e:
            # 検索の失敗は本来のレスポンスをブロックしない
            logger.error(f"glossary search failed: {e}")
            return []
        
        if not rows:
            return []
        
        # 閾値は SQL ではなく Python 側で適用する。
        # 「何位まで惜しかったか」をログに残せるようにするため（Phase C の材料）。
        logger.info(
            f"glossary search: q='{query_text[:40]}' category={category} "
            f"top_distance={rows[0].distance:.4f} hits={len(rows)}"
        )

        hits = [
            {
                "section": r.section,
                "source": r.source,
                "category": r.category,
                "chunk_text": r.chunk_text,
                "distance": float(r.distance),
            }
            for r in rows if r.distance <= distance_threshold
        ]

        if not rerank or not hits:
            return hits[:top_k]

        # 閾値を適用した後にリランクする。
        # 無関係な候補を LLM に読ませてもトークンを消費するだけのため。
        # 循環 import を避けるため関数内で import する。
        from backend.app.services.rerank_service import rerank_hits

        return rerank_hits(query_text, hits, top_k=top_k)


# Singleton
_glossary_service: Optional[GlossaryRAGService] = None


def get_glossary_rag_service() -> GlossaryRAGService:
    global _glossary_service
    if _glossary_service is None:
        _glossary_service = GlossaryRAGService()
    return _glossary_service
