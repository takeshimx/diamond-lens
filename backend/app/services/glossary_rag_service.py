"""
Glossary RAG Service

docs/knowledge/*.md 由来の用語集チャンクを BigQuery 上でセマンティック検索する。
サーバレス・Pay-as-you-go: 検索 1 回につき Vertex AI の埋め込み API を 1 コールのみ。

設計:
  - VECTOR_SEARCH ではなく ML.DISTANCE を使う (厳密 KNN の総当たり)。
    glossary_embeddings が 10 MB 未満のうちはベクトルインデックスが
    populate されず (BASE_TABLE_TOO_SMALL)、VECTOR_SEARCH を書いても
    BigQuery 側がブルートフォースに退避するだけで実体が変わらないため。
    テーブルが 10 MB を超えたらベクトルインデックス + VECTOR_SEARCH へ
    切り替える。その際 category は CREATE VECTOR INDEX ... STORING に
    含めること。stored column でないカラムで絞ると post-filter になり、
    上位 K 件を取った後に削られて結果が目減りする。
    (category による事前フィルタは必須。打者の質問に投手チャンクが返る
     誤検索を構造的に防いでいるのはこのフィルタである。)
    https://cloud.google.com/bigquery/docs/vector-index
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

# BQ に取り込み済みの全カテゴリ。
ALL_CATEGORIES = ("batting", "pitching", "statcast", "rules")

# 検索対象から除外するカテゴリ。BQ のデータは残したまま無効化する。
# rules (公式ルール PDF 897 チャンク) は 2026-08-21 時点で検索精度が実用水準に
# 達していないため除外している。分割を作り直しても命中@3 は 0.333 のままで、
# 用語集 (命中@3 1.000) の足を引っ張る状態だった。
#
# 2026-09-04 追記: 上記 0.333 はゴールデンセット側の正解 chunk_id が
# 「見出しだけのリード文チャンク」を指していたことによる測定誤りを含む。
# 正解を貼り直し rule 型を 30 問へ拡張して再測定した結果は 命中@3 0.600。
# 2026-09-04: 除外を解除した。解除時点の実測 (rule 型 30 問 / リランク + HyDE):
#   命中@3 0.833 / 命中@5 0.867 / MRR 0.766
# 前提: USE_GLOSSARY_RERANK と USE_GLOSSARY_HYDE の両方が true であること。
#       どちらも false だと rules の命中@3 は 0.500 まで落ちる。
EXCLUDED_CATEGORIES: tuple[str, ...] = ()

# LLM に選ばせてよいカテゴリ。除外中のものを渡されても結果は 0 件になるため、
# 選択肢そのものから外す。ハードコードせず EXCLUDED_CATEGORIES から導出する。
VALID_CATEGORIES = tuple(c for c in ALL_CATEGORIES if c not in EXCLUDED_CATEGORIES)

# カテゴリ別の距離閾値。ここに無いカテゴリは DEFAULT_DISTANCE_THRESHOLD を使う。
#
# rules だけが「日本語の質問 -> 英語の条文」というクロスリンガル検索になる。
# 用語集 (docs/knowledge/*.md) は日本語で執筆しているため日本語同士であり、
# 距離分布が構造的に異なる。用語集用に決めた 0.275 を rules に当てると
# 候補がすべて足切りされ、リランクが起動しないまま終わる。
#
# 2026-09-04 測定 (rule 型 30 問 / 候補 10 件):
#   閾値   正解保持率  ノイズ/問  リランクが起動する問
#   0.275    0.333      3.17      15/30   <- 用語集用の値
#   0.325    0.700      7.13      27/30
#   0.350    0.733      7.67      28/30   <- 採用。ここで正解保持率が頭打ち
#   0.400    0.733      8.60      30/30   <- 保持率は増えずノイズだけ増える
#
# 0.275 -> 0.35 の適用結果 (rule 型 30 問 / リランク ON):
#   命中@3 0.600 -> 0.733、MRR 0.580 -> 0.708
# 注意: リランクは LLM 呼び出しのため実行ごとに揺れる。同一条件のはずの
#       用語集 paraphrase も 0.800 -> 1.000 と動いており、上記の改善幅には
#       ばらつきが含まれる。複数回実行して確認していない。
CATEGORY_DISTANCE_THRESHOLDS = {"rules": 0.35}

DEFAULT_RERANK_CANDIDATES = 10   # リランク時に取得する候補数


def resolve_distance_threshold(category: Optional[str]) -> float:
    """カテゴリに対応する距離閾値を返す。

    本番と評価ハーネスで同じ値を使うため、両者からこの関数を呼ぶ。
    """
    if not category:
        return DEFAULT_DISTANCE_THRESHOLD
    return CATEGORY_DISTANCE_THRESHOLDS.get(category, DEFAULT_DISTANCE_THRESHOLD)


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
        distance_threshold: Optional[float] = None,
        rerank: bool = False,
        hyde: bool = False,
    ) -> list[dict]:
        """用語集から関連チャンクを検索する。

        Args:
            query_text: ユーザーの質問（日本語可。多言語モデルで英語文書を引ける）
            top_k: 取得する最大件数
            category: 'batting' / 'pitching' / 'statcast' で絞り込む。
                      None なら全カテゴリ横断。
            distance_threshold: コサイン距離の上限。これを超える結果は捨てる。
                      None ならカテゴリ別の既定値
                      (CATEGORY_DISTANCE_THRESHOLDS) を使う。
            rerank: True の場合、LLM を使って関連性の高い順に並べ直す。
            hyde: True の場合、英語文書のカテゴリに限り、質問を英語の条文風に
                      書き換えてから埋め込む（query_rewrite_service）。

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

        # 閾値は category 確定後に解決する。未知の category を None に倒した後の
        # 値を使わないと、フィルタと閾値がちぐはぐになるため。
        if distance_threshold is None:
            distance_threshold = resolve_distance_threshold(category)

        # 検索に使う文字列。HyDE 有効時のみ英語の条文風に書き換わる。
        # ログとリランクには元の質問を使う（利用者が何を聞いたかが本体のため）。
        # 循環 import を避けるため関数内で import する。
        search_text = query_text
        if hyde:
            from backend.app.services.query_rewrite_service import (
                rewrite_for_retrieval,
            )
            search_text = rewrite_for_retrieval(query_text, category)

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
                bigquery.ScalarQueryParameter("query_text", "STRING", search_text),
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
            f"threshold={distance_threshold:.3f} "
            f"hyde={'on' if search_text != query_text else 'off'} "
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
