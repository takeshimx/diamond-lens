"""
検索結果のリランク（並べ直し）。

ベクトル検索は文章全体を 768 次元に潰して比較するため、細かい判断ができない。
候補を広めに取り、LLM に質問と本文を読み比べさせて並べ直す。

fail-open: LLM 呼び出しに失敗したら元の順序をそのまま返す。
"""
from __future__ import annotations

import json
from typing import Optional

from backend.app.services.llm_gateway_service import call_gemini
from backend.app.utils.structured_logger import get_logger

logger = get_logger("rerank")

RERANK_MODEL = "gemini-2.5-flash"
# 本文は先頭のみ渡す。全文を入れるとトークンが嵩み、判断精度も上がらないため
SNIPPET_CHARS = 300


_PROMPT = """あなたは検索結果の並べ替えを行います。

【質問】
{query}

【候補】
{candidates}

上記の候補を、質問への回答として適切な順に並べ替えてください。

出力は候補番号の配列のみ。説明は不要です。
例: [3, 1, 5, 2, 4]

関連のない候補は配列から除外して構いません。
"""


def rerank_hits(
    query: str,
    hits: list[dict],
    top_k: int = 5,
    request_id: Optional[str] = None,
) -> list[dict]:
    """hits を LLM に並べ直させ、上位 top_k 件を返す。

    Args:
        query: ユーザーの質問
        hits: glossary_rag_service.search() の戻り値（距離の昇順）
        top_k: 返す件数
    Returns:
        並べ直された hits。失敗時は元の順序の先頭 top_k 件（fail-open）。
    """
    if len(hits) <= 1:
        return hits[:top_k]
    
    candidates = "\n".join(
        f"{i + 1}. 【{h['section']}】{h['chunk_text'][:SNIPPET_CHARS]}"
        for i, h in enumerate(hits)
    )
    prompt = _PROMPT.format(query=query, candidates=candidates)

    try:
        raw = call_gemini(
            prompt,
            model=RERANK_MODEL,
            response_mime_type="application/json",
            feature="glossary_rerank",
            request_id=request_id,
            user_query=query,
        )
        order = json.loads(raw or "[]")
        seen: set[int] = set()
        picked: list[dict] = []
        for n in order:
            idx = int(n) - 1
            if 0 <= idx < len(hits) and idx not in seen:
                seen.add(idx)
                picked.append(hits[idx])
        if not picked:
            raise ValueError("rerank returned no valid index")

        logger.info(
            f"rerank: {len(hits)} -> {len(picked)} "
            f"top='{picked[0]['section']}' (was '{hits[0]['section']}')"
        )
        return picked[:top_k]
    
    except Exception as e:
        # 並べ直しの失敗は検索結果そのものを捨てる理由にならない
        logger.warning(f"rerank failed, falling back to vector order: {e}")
        return hits[:top_k]