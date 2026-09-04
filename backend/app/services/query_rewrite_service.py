"""
検索用のクエリ書き換え（HyDE: Hypothetical Document Embeddings）。

日本語の質問をそのままベクトル化すると、英語で書かれた公式ルール PDF との
距離が構造的に遠くなる。質問文ではなく「答えがこう書かれているはずだ」という
仮の英文を LLM に書かせ、それをベクトル化して検索する。

実測 (2026-09-04 / rule_020「ストライクゾーンを外れた投球を4つ受けた打者は
どうなりますか」/ 正解 def:BASE ON BALLS):
    日本語のまま検索 -> 212 位 (距離 0.3244)
    同義の英文で検索 ->  16 位 (距離 0.2450)

対象は英語文書のカテゴリのみ。用語集 (docs/knowledge/*.md) は日本語で
執筆しているため、英訳すると逆に遠ざかる。HYDE_CATEGORIES で線を引く。

fail-open: 書き換えに失敗したら元の質問をそのまま返す。検索が劣化しても
チャット本体は止めない (glossary_rag_service と同じ方針)。
"""
from __future__ import annotations

from typing import Optional

from backend.app.services.llm_gateway_service import call_gemini
from backend.app.utils.structured_logger import get_logger

logger = get_logger("query-rewrite")

HYDE_MODEL = "gemini-2.5-flash"

# 書き換えを適用するカテゴリ。文書が英語のものだけを対象にする。
HYDE_CATEGORIES = ("rules",)

# 生成文が長いと、条文そのものより「説明文らしさ」がベクトルを占有する。
# 2〜3 文に制限し、余った分は捨てる。
MAX_REWRITE_CHARS = 600


_PROMPT = """You are helping a search engine find the right passage in the
Official Baseball Rules (the English rulebook of Major League Baseball).

Below is a question written in Japanese.

Question:
{query}

Write the passage that would answer it, as if quoting the rulebook itself.

Rules for your output:
- English only.
- Use the wording and register of the official rules, not an explanation.
- 1 to 3 sentences. No preamble, no heading, no quotation marks.
- If you are unsure of the exact rule, still write the most plausible
  rulebook-style sentence. A close guess is more useful here than a refusal.
"""


def should_rewrite(category: Optional[str]) -> bool:
    """このカテゴリで書き換えを行うか。"""
    return bool(category) and category in HYDE_CATEGORIES


def rewrite_for_retrieval(
    query: str,
    category: Optional[str] = None,
    request_id: Optional[str] = None,
) -> str:
    """検索に使う文字列を返す。

    Args:
        query: ユーザーの質問（日本語）
        category: 検索対象カテゴリ。HYDE_CATEGORIES 以外は書き換えない
        request_id: ログ相関用

    Returns:
        書き換えた英文。対象外・失敗時は query をそのまま返す。
    """
    if not should_rewrite(category) or not query or not query.strip():
        return query

    try:
        raw = call_gemini(
            _PROMPT.format(query=query),
            model=HYDE_MODEL,
            feature="glossary_hyde",
            # rerank_service と同様、node 未指定だと Trace Viewer の
            # サマリ行と混同される（書き換えた英文が最終回答として表示される）
            node="hyde",
            request_id=request_id,
            user_query=query,
        )
    except Exception as e:
        # 書き換えの失敗で検索そのものを止めない
        logger.warning(f"hyde rewrite failed, using original query: {e}")
        return query

    rewritten = (raw or "").strip()
    if not rewritten:
        logger.warning("hyde rewrite returned empty, using original query")
        return query

    rewritten = rewritten[:MAX_REWRITE_CHARS]
    logger.info(f"hyde: '{query[:30]}' -> '{rewritten[:60]}'")
    return rewritten
