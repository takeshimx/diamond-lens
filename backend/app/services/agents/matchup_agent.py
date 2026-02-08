import json
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from backend.app.utils.structured_logger import get_logger
from backend.app.core.exceptions import AgentReasoningError

logger = get_logger("matchup-agent")


class MatchupAgent:
    """
    Specialized agent for matchup analysis.
    Uses existing LangGraph structure (Oracle → Executor → Synthesizer).
    """
    
    def __init__(self, model):
        self.raw_model = model  # For text generation (no tools)
        
        # Import and define tools first
        from ..ai_agent_service import mlb_matchup_history_tool, mlb_matchup_analytics_tool
        self.tools = [mlb_matchup_history_tool, mlb_matchup_analytics_tool]
        
        # Then bind tools to model
        self.model = model.bind_tools(self.tools)
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """Build LangGraph workflow"""
        from ..ai_agent_service import AgentState
        
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("oracle", self.oracle_node)
        workflow.add_node("executor", self.executor_node)
        workflow.add_node("synthesizer", self.synthesizer_node)
        
        # Add edges
        workflow.set_entry_point("oracle")
        workflow.add_conditional_edges(
            "oracle",
            self.should_continue,
            {
                "continue": "executor",
                "end": "synthesizer"
            }
        )
        workflow.add_edge("executor", "oracle")
        workflow.add_edge("synthesizer", END)
        
        return workflow.compile()
    
    def should_continue(self, state):
        """Determine if we should continue or end"""
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            return "continue"
        return "end"
    
    def oracle_node(self, state):
        """Oracle node - plans tool execution"""
        logger.info("Oracle node started", node="oracle")
        
        system_prompt = """あなたはMLBデータ収集の司令塔です。ユーザーの質問を分析し、最適なツール呼び出しを計画してください。
        
        **重要な行動指針:**
        1. 打者と投手の特定の対戦（Matchup）に関する質問の場合、必ず `mlb_matchup_analytics_tool` と `mlb_matchup_history_tool` を使用して最新データを取得してください。
        2. 自分の知識だけで答えず、必ずBigQuery上のカスタムビューからデータを取得してください。
        3. 複数の選手を比較する場合、各対象について個別かつ詳細にデータを取得してください。
        4. 必要なデータが全て揃ったと確信できるまで、繰り返し実行（continue）を選択してください。"""
        
        prompt = [SystemMessage(content=system_prompt)] + state["messages"]
        
        try:
            response = self.model.invoke(prompt)
            return {"messages": [response]}
        except Exception as e:
            raise AgentReasoningError("AIの思考プロセス中にエラーが発生しました", original_error=e) from e
    
    def executor_node(self, state):
        """Executor node - executes tools"""
        logger.info("Executor node started", node="executor")
        
        last_message = state["messages"][-1]
        tool_outputs = []
        
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            logger.info(f"Calling tool: {tool_name}")
            
            selected_tool = next((t for t in self.tools if t.name == tool_name), None)
            
            if selected_tool:
                result = selected_tool.invoke(tool_call["args"])
            else:
                result = {"error": f"Tool {tool_name} not found"}
            
            # Sanitize data (remove NaN, Infinity)
            def sanitize_data(obj):
                if isinstance(obj, list):
                    return [sanitize_data(item) for item in obj]
                elif isinstance(obj, dict):
                    return {k: sanitize_data(v) for k, v in obj.items()}
                elif isinstance(obj, float):
                    if obj != obj:  # NaN check
                        return None
                    if obj == float('inf') or obj == float('-inf'):
                        return None
                return obj
            
            sanitized_result = sanitize_data(result)
            
            tool_outputs.append(ToolMessage(
                tool_call_id=tool_call["id"],
                content=json.dumps(sanitized_result, ensure_ascii=False, default=str)
            ))
        
        return {"messages": tool_outputs}
    
    def synthesizer_node(self, state):
        """Synthesizer node - generates final answer"""
        logger.info("Synthesizer node started", node="synthesizer")
        
        system_prompt = """あなたはMLB公式シニア・アナリストです。
        提供されたデータを基に、一目でポイントがわかるプロフェッショナルな分析レポートを作成してください。

        **【出力構成の必須ルール】:**
        1. **Markdownによる構造化**:
           - 適切な見出し（###）を使用し、情報を整理してください。
           - 数値データの列挙には箇条書き（- ）を使用し、視認性を高めてください。
        2. **プロの分析エッセンス**:
           - 単なるデータの朗読ではなく、「なぜそうなったか」「その数字が持つ意味」をアナリストの視点で簡潔に添えてください。
        3. **流暢で自然な日本語**:
           - **最初の一文は必ず整合性の取れた完全な文章（例：「大谷選手の〜」）で始めてください。**
           - 同じ主語（大谷選手は〜）の連続使用を避け、指示語や接続詞を使いこなしたプロの文章を目指してください。
           - 冗長な表現は避け、核心を突くスマートな記述を心がけてください。"""
        
        prompt = [
            SystemMessage(content=system_prompt),
        ] + state["messages"] + [
            # 最後に改めて「主語から始めろ」と念押しする
            HumanMessage(content="それでは、分析レポートを作成してください。必ず主語から始まる完全な文章で開始すること。")
        ]
        
        try:
            response = self.raw_model.invoke(prompt)
            
            logger.info(f"🔍 LLM Response length: {len(response.content)}")
            logger.info(f"🔍 LLM Response preview: {response.content[:200]}")
            
            # Extract matchup card data if present
            matchup_metadata = self._extract_matchup_data(state)
            
            final_result = {
                "final_answer": response.content,
                **matchup_metadata,  # Spread the dictionary
                "messages": [response]
            }
            
            logger.info(f"🔍 Final result keys: {final_result.keys()}")
            logger.info(f"🔍 final_answer length in result: {len(final_result.get('final_answer', ''))}")
            
            return final_result
        except Exception as e:
            raise AgentReasoningError("分析中にエラーが発生しました", original_error=e) from e
    
    def _extract_matchup_data(self, state):
        """Extract matchup card data from tool results"""
        # ツール呼び出し結果から対戦データを抽出 (UIカード用)

        # ui_metadata を初期化
        ui_metadata = {
            "isMatchupCard": False,
            "matchupData": None
        }
    
        matchup_history = []
        matchup_stats = []
        
        for msg in state["messages"]:
            if isinstance(msg, ToolMessage):
                try:
                    data = json.loads(msg.content)
                    if isinstance(data, list) and len(data) > 0:
                        first_row = data[0]
                        # 球種別分析データが含まれているかチェック
                        if "pitch_name" in first_row and ("batting_average" in first_row or "avg" in first_row):
                            # カラム名を統一
                            for item in data:
                                if "avg" in item and "batting_average" not in item:
                                    item["batting_average"] = item["avg"]
                            matchup_stats = data
                            ui_metadata["isMatchupCard"] = True
                        # 打席履歴データが含まれているかチェック
                        elif "game_date" in first_row:
                            matchup_history = data
                            ui_metadata["isMatchupCard"] = True
                except:
                    continue

        if ui_metadata["isMatchupCard"]:
            ui_metadata["matchupData"] = {
                "stats": matchup_stats,
                "history": matchup_history[:50], # 最新50球分
                "summary": {
                    "batter": matchup_stats[0].get("batter_name") if matchup_stats else (matchup_history[0].get("batter_name") if matchup_history else "Batter"),
                    "pitcher": matchup_stats[0].get("pitcher_name") if matchup_stats else (matchup_history[0].get("pitcher_name") if matchup_history else "Pitcher"),
                }
            }
        
        return ui_metadata

    
    def run(self, query: str):
        """Execute matchup analysis"""
        from ..ai_agent_service import AgentState
        
        initial_state = {
            "messages": [HumanMessage(content=query)],
            "raw_data_store": {},
            "next_step": "",
            "final_answer": "",
            "isTable": False,
            "isChart": False,
            "tableData": None,
            "chartData": None,
            "columns": None,
            "isTransposed": False,
            "chartType": "",
            "chartConfig": None,
            "isMatchupCard": False,
            "matchupData": None
        }
        
        result = self.graph.invoke(initial_state)
        
        # Extract only the fields needed by the API response
        return {
            "final_answer": result.get("final_answer", ""),
            "isTable": result.get("isTable", False),
            "isChart": result.get("isChart", False),
            "tableData": result.get("tableData", None),
            "chartData": result.get("chartData", None),
            "columns": result.get("columns", None),
            "isTransposed": result.get("isTransposed", False),
            "chartType": result.get("chartType", ""),
            "chartConfig": result.get("chartConfig", None),
            "isMatchupCard": result.get("isMatchupCard", False),
            "matchupData": result.get("matchupData", None),
            "raw_data_store": result.get("raw_data_store", {}),
            "next_step": "END"
        }
