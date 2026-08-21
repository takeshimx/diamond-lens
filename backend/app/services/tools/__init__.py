"""
共通ツールモジュール。
ChatOrchestrator (Phase 2 で導入) と StrategyAgent の両方から import される。

依存ルール:
  - 他の services/*.py に依存してよいのは bigquery_service / cache_service / analytics/ のみ
  - LangGraph / LangChain agent ロジックには依存しない（双方向依存を避けるため）
"""
from .batter_stats_tool import get_batter_stats_tool
from .pitcher_stats_tool import get_pitcher_stats_tool
from .matchup_history_tool import mlb_matchup_history_tool
from .matchup_analytics_tool import mlb_matchup_analytics_tool
from .glossary_search_tool import glossary_search_tool

__all__ = [
    "get_batter_stats_tool",
    "get_pitcher_stats_tool",
    "mlb_matchup_history_tool",
    "mlb_matchup_analytics_tool",
    "glossary_search_tool",
]


from ._genai_schemas import (
    CHAT_TOOL_DECLARATIONS,
    CHAT_TOOL_DECLARATIONS_SEMANTIC,
    GET_BATTER_STATS_DECL,
    GET_PITCHER_STATS_DECL,
    MATCHUP_HISTORY_DECL,
    MATCHUP_ANALYTICS_DECL,
    QUERY_SEMANTIC_METRICS_DECL,
    GLOSSARY_SEARCH_DECL,
)

# ツール名 → 実体関数のマップ（ChatOrchestrator の dispatch 用）
# USE_SEMANTIC_LAYER=false 用 (legacy METRIC_MAP 経路)
CHAT_TOOL_REGISTRY = {
    "get_batter_stats_tool": get_batter_stats_tool,
    "get_pitcher_stats_tool": get_pitcher_stats_tool,
    "mlb_matchup_history_tool": mlb_matchup_history_tool,
    "mlb_matchup_analytics_tool": mlb_matchup_analytics_tool,
    # glossary_search_tool は USE_GLOSSARY_RAG フラグ制御に移管（A-6）。
    # ChatOrchestrator.__init__ が条件付きで registry へ追加する。
}


def _get_semantic_tool_registry() -> dict:
    """USE_SEMANTIC_LAYER=true 用の registry を遅延構築する。
    query_semantic_metrics_tool が ai_agent_service にあるため、
    モジュール読み込み時に import すると循環依存が発生する。
    呼び出し時 (ChatOrchestrator.__init__) に解決する。

    matchup 系は Semantic Layer 化未着手のため legacy のまま維持。
    """
    from backend.app.services.ai_agent_service import query_semantic_metrics_tool
    return {
        "query_semantic_metrics_tool": query_semantic_metrics_tool,
        "mlb_matchup_history_tool": mlb_matchup_history_tool,
        "mlb_matchup_analytics_tool": mlb_matchup_analytics_tool,
        # glossary_search_tool は USE_GLOSSARY_RAG フラグ制御に移管（A-6）
    }


__all__ += [
    "CHAT_TOOL_DECLARATIONS",
    "CHAT_TOOL_DECLARATIONS_SEMANTIC",
    "CHAT_TOOL_REGISTRY",
    "_get_semantic_tool_registry",
    "GET_BATTER_STATS_DECL",
    "GET_PITCHER_STATS_DECL",
    "MATCHUP_HISTORY_DECL",
    "MATCHUP_ANALYTICS_DECL",
    "QUERY_SEMANTIC_METRICS_DECL",
    "GLOSSARY_SEARCH_DECL",
]
