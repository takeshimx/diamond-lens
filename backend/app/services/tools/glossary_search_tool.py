"""
用語集検索ツール。

ChatOrchestrator が「定義・ルールを問う質問」と判断したときだけ呼ばれる。
常時検索する naive RAG ではなく、LLM が必要性を判断する Agentic RAG 構成。

依存ルール: tools/ からは bigquery_service / cache_service / analytics のみ参照可。
glossary_rag_service は BQ 直叩きの薄いサービスであり、この方針に反しない。
"""
from typing import List, Optional

from langchain_core.tools import tool


@tool
def glossary_search_tool(
    query: str,
    category: Optional[str] = None,
    top_k: int = 5,
) -> dict:
    """MLB の用語定義・指標の意味を知識ベースから検索する。

    Args:
        query: 検索したい内容（ユーザーの質問をそのまま渡してよい）
        category: 'batting' / 'pitching' / 'statcast' の絞り込み。不明なら None
        top_k: 取得件数

    Returns:
        {"isTable": False, "answer": str, "sources": [...], "results": [...]}

        answer は chat_orchestrator._build_final_answer が認識する「形式 3」。
        用語集の中身は表ではなく文章のため、tableData ではなく answer を使う。
        該当なし・検索失敗時も同じ構造を返す（fail-open）。
    """
    from backend.app.config.settings import get_settings

    from ..glossary_rag_service import get_glossary_rag_service

    svc = get_glossary_rag_service()
    hits = svc.search(
        query_text=query,
        category=category,
        top_k=top_k,
        # USE_GLOSSARY_RERANK=true のときだけ LLM による並べ直しが走る。
        # 効果を測ってから有効化する方針のため既定は false。
        rerank=bool(get_settings().use_glossary_rerank),
    )

    if not hits:
        return {
            "isTable": False,
            "answer": "知識ベースに該当する用語が見つかりませんでした。",
            "sources": [],
            "results": [],
        }

    # chunk_text は見出しを先頭に含んでいるため、そのまま連結すれば読める
    body = "\n\n".join(h["chunk_text"] for h in hits)
    sources = sorted({h["source"] for h in hits})

    return {
        "isTable": False,
        "answer": f"{body}\n\n出典: {', '.join(sources)}",
        "sources": sources,
        # デバッグ・評価用。最終回答の組み立てには使われない
        "results": [
            {
                "term": h["section"],
                "category": h["category"],
                "distance": round(h["distance"], 4),
            }
            for h in hits
        ],
    }