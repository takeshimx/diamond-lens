from typing import List, Optional

from langchain_core.tools import tool


@tool
def get_pitcher_stats_tool(
    query_type: Optional[str] = None,
    metrics: Optional[List[str]] = None,
    name: Optional[str] = None,
    season: Optional[int] = None,
    split_type: Optional[str] = None,
    inning: Optional[List[int]] = None,
    strikes: Optional[int] = None,
    balls: Optional[int] = None,
    game_score: Optional[str] = None,
    pitch_type: Optional[List[str]] = None,
    order_by: Optional[str] = None,
    limit: Optional[int] = None,
    output_format: str = "data",
    query: Optional[str] = None,
):
    """投球成績を取得する。呼び出し元 LLM が構造化引数を渡すこと。
    query (NL) を渡した場合は後方互換として tool 内で NLU が走る (非推奨)。
    """
    from ..analytics.pitcher_services import get_ai_response_for_pitcher_stats

    structured = {
        "query_type": query_type,
        "metrics": metrics,
        "name": name,
        "season": season,
        "split_type": split_type,
        "inning": inning,
        "strikes": strikes,
        "balls": balls,
        "game_score": game_score,
        "pitch_type": pitch_type,
        "order_by": order_by,
        "limit": limit,
        "output_format": output_format,
    }
    return get_ai_response_for_pitcher_stats(
        query=query,
        season=season,
        output_format=output_format,
        structured_params=structured,
    )
