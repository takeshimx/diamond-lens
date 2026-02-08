from langchain_core.messages import HumanMessage
from backend.app.utils.structured_logger import get_logger

logger = get_logger("stats-agent")


class StatsAgent:
    """
    Specialized agent for general stats queries.
    Simpler than MatchupAgent - direct tool execution.
    """

    def __init__(self, model):
        self.model = model

        from ..ai_agent_service import mlb_stats_tool
        self.tools = [mlb_stats_tool]
        self.model = model.bind_tools(self.tools)
    
    def run(self, query: str) -> dict:
        """
        Execute stats query (no LangGraph needed for simple queries)

        FYI, there is no need to set 'initial_state' in this agent since this is not LangGraph.
        """

        logger.info("StatsAgent executing query", query=query)

        try:
            # Call the tool directly
            result = self.tools[0].invoke({"query": query})

            logger.info("StatsAgent completed", query=query, isTable=result.get("isTable", False))
    
            # mlb_stats_tool now returns: {"answer": "...", "isTable": True, "tableData": [...], "columns": [...]}
            # Just pass it through with minimal formatting
            
            # Format response - pass through all fields from mlb_stats_tool
            return {
                "final_answer": result.get("answer", "データが見つかりませんでした"),
                "isTable": result.get("isTable", False),
                "isChart": result.get("isChart", False),  # Pass through from tool
                "tableData": result.get("tableData", None),
                "chartData": result.get("chartData", None),  # Pass through from tool
                "columns": result.get("columns", None),
                "isTransposed": result.get("isTransposed", False),
                "chartType": result.get("chartType", ""),  # Pass through from tool
                "chartConfig": result.get("chartConfig", None),  # Pass through from tool
                "isMatchupCard": False,  # Stats queries don't use matchup cards
                "matchupData": None,
                "messages": [HumanMessage(content=query)],
                "raw_data_store": result.get("raw_data_store", {}),  # Pass through from tool
                "next_step": "END"
            }
        
        except Exception as e:
            logger.error("StatsAgent error", error=str(e), query=query)

            return {
                "final_answer": f"エラーが発生しました: {str(e)}",
                "isTable": False,
                "isChart": False,
                "tableData": None,
                "chartData": None,
                "columns": None,
                "isTransposed": False,
                "chartType": "",
                "chartConfig": None,
                "isMatchupCard": False,
                "matchupData": None,
                "messages": [HumanMessage(content=query)],
                "raw_data_store": {},
                "next_step": "END"
            }