"""
query_rewrite_service（HyDE）の単体テスト。

LLM には一切接続しない（call_gemini をモックに差し替える）ため、
課金は発生しない。CI でそのまま実行できる。

検証の主眼は 2 点:
  1. 対象カテゴリの線引き。用語集（日本語文書）まで英訳してしまうと逆効果になる
  2. fail-open。書き換えに失敗しても元の質問を返し、検索を止めない
"""
from unittest.mock import patch

from backend.app.services.query_rewrite_service import (
    HYDE_CATEGORIES,
    MAX_REWRITE_CHARS,
    rewrite_for_retrieval,
    should_rewrite,
)

_JA = "ボークが宣告されるのはどんな場合ですか"
_EN = "It is a balk when the pitcher, while touching his plate, feints a throw."

_TARGET = "backend.app.services.query_rewrite_service.call_gemini"


# ---------------------------------------------------------------- 対象の線引き


def test_should_rewrite_only_for_english_sources():
    """英語文書のカテゴリだけが対象。用語集は日本語なので対象外。"""
    for c in HYDE_CATEGORIES:
        assert should_rewrite(c) is True
    assert should_rewrite("batting") is False
    assert should_rewrite(None) is False
    assert should_rewrite("") is False


def test_non_target_category_skips_llm_call():
    """対象外のカテゴリでは LLM を呼ばない（無駄な課金を防ぐ）。"""
    with patch(_TARGET) as mock_llm:
        assert rewrite_for_retrieval(_JA, category="batting") == _JA
        mock_llm.assert_not_called()


def test_blank_query_skips_llm_call():
    """空文字・空白のみでは LLM を呼ばない。"""
    with patch(_TARGET) as mock_llm:
        assert rewrite_for_retrieval("", category="rules") == ""
        assert rewrite_for_retrieval("   ", category="rules") == "   "
        mock_llm.assert_not_called()


# ---------------------------------------------------------------- 正常系


def test_rewrites_target_category():
    """対象カテゴリでは書き換え結果を返す。"""
    with patch(_TARGET, return_value=_EN):
        assert rewrite_for_retrieval(_JA, category="rules") == _EN


def test_rewrite_is_truncated():
    """長すぎる生成文は打ち切る。

    説明文が長いと「条文らしさ」よりも「説明文らしさ」がベクトルを占有する。
    """
    with patch(_TARGET, return_value="x" * (MAX_REWRITE_CHARS + 500)):
        out = rewrite_for_retrieval(_JA, category="rules")
    assert len(out) == MAX_REWRITE_CHARS


# ---------------------------------------------------------------- fail-open


def test_returns_original_query_when_llm_raises():
    """LLM が落ちても例外を漏らさず、元の質問で検索を続行させる。"""
    with patch(_TARGET, side_effect=RuntimeError("Gemini unavailable")):
        assert rewrite_for_retrieval(_JA, category="rules") == _JA


def test_returns_original_query_when_llm_returns_empty():
    """空文字・None が返っても元の質問に倒す（空文字で検索させない）。"""
    with patch(_TARGET, return_value=""):
        assert rewrite_for_retrieval(_JA, category="rules") == _JA
    with patch(_TARGET, return_value=None):
        assert rewrite_for_retrieval(_JA, category="rules") == _JA
    with patch(_TARGET, return_value="   \n  "):
        assert rewrite_for_retrieval(_JA, category="rules") == _JA
