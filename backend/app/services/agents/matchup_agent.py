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
        workflow.add_node("reflection", self.reflection_node)
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

        # executor実行後、エラー/空結果があればreflectionへ、なければoracleへ
        workflow.add_conditional_edges(
            "executor",
            self.should_reflect,
            {
                "reflection": "reflection",
                "oracle": "oracle"
            }
        )

        workflow.add_edge("reflection", "oracle")
        workflow.add_edge("synthesizer", END)

        return workflow.compile()
    
    def should_continue(self, state):
        """Determine if we should continue or end"""
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            return "continue"
        return "end"

    def should_reflect(self, state):
        """executor実行後、Reflectionが必要かどうかを判定"""
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 2)
        last_error = state.get("last_error")
        result_count = state.get("last_query_result_count", -1)

        # 最大リトライ回数に達している場合は、Reflectionしない
        if retry_count >= max_retries:
            logger.info("Max retries reached, skipping reflection",
                        retry_count=retry_count,
                        max_retries=max_retries)
            return "oracle"

        # Do NOT retry: 認証・パーミッションエラー
        if last_error and any(keyword in last_error.lower() for keyword in [
            "permission", "access denied", "unauthorized", "forbidden"
        ]):
            logger.info("Non-retryable error detected (permission)", error=last_error)
            return "oracle"

        # Do NOT retry: タイムアウトエラー
        if last_error and "timeout" in last_error.lower():
            logger.info("Non-retryable error detected (timeout)", error=last_error)
            return "oracle"

        # Do NOT retry: データセット/スキーマエラー
        if last_error and any(keyword in last_error.lower() for keyword in [
            "dataset", "schema", "not found", "does not exist"
        ]):
            logger.info("Non-retryable error detected (schema/dataset)", error=last_error)
            return "oracle"

        # Retry: SQLシンタックスエラー、カラム名誤認識
        if last_error and any(keyword in last_error.lower() for keyword in [
            "syntax", "unrecognized", "invalid", "column", "table"
        ]):
            logger.info("Retryable error detected (SQL syntax/column)",
                        error=last_error,
                        retry_count=retry_count)
            return "reflection"

        # Retry: 空結果（0行）
        if result_count == 0:
            logger.info("Empty result detected, triggering reflection",
                        retry_count=retry_count)
            return "reflection"

        # デフォルト: 通常フロー（oracleに戻る）
        return "oracle"

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
        logger.info("Executor node started", node="executor", status="executing")

        last_message = state["messages"][-1]
        tool_outputs = []
        has_error = False
        result_count = -1
        error_message = ""

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            logger.info(f"Calling tool: {tool_name}")

            selected_tool = next((t for t in self.tools if t.name == tool_name), None)

            if selected_tool:
                result = selected_tool.invoke(tool_call["args"])
            else:
                result = {"error": f"Tool {tool_name} not found"}
                has_error = True
                error_message = result["error"]

            # ===== エラー/空結果の検出 =====
            logger.info(f"Tool result type: {type(result).__name__}, preview: {str(result)[:200]}")

            # 1. BigQuery error
            if isinstance(result, dict) and "error" in result:
                has_error = True
                error_message = result.get("error", "Unknown error")
                logger.warning("Tool execution error detected",
                               tool_name=tool_name,
                               error=error_message)

            # 2. Empty result
            if isinstance(result, list):
                result_count = len(result)
                if result_count == 0:
                    logger.warning("Empty result detected (0 rows from list)",
                                   tool_name=tool_name,
                                   result_count=result_count)
            elif isinstance(result, dict):
                if "data" in result and isinstance(result["data"], list):
                    result_count = len(result["data"])
                    if result_count == 0:
                        logger.warning("Empty result detected (0 rows from dict)",
                                       tool_name=tool_name,
                                       result_count=result_count)
                elif result.get("answer") and "データが見つかりませんでした" in result.get("answer", ""):
                    result_count = 0
                    logger.warning("Empty result detected (no data message)",
                                   tool_name=tool_name,
                                   answer_preview=result.get("answer", "")[:100])
            #==============================

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

        return {
            "messages": tool_outputs,
            "last_error": error_message if has_error else None,
            "last_query_result_count": result_count
        }
    
    def reflection_node(self, state):
        """エラーや空結果の場合、LLMにフィードバックを提供して再試行"""
        logger.info("Reflection node started",
                    node="reflection_node",
                    status="analyzing_error",
                    retry_count=state.get("retry_count", 0))

        # Build error context
        error_context = ""
        if state.get("last_error"):
            error_context = f"""
            **発生したエラー**:
{state['last_error']}

**エラーの原因として考えられること**:
- カラム名の誤認識（例: `player_name` ではなく `name_display_first_last` が正しい可能性）
- テーブル名の誤認識
- SQLシンタックスエラー（JOIN句、WHERE句の記述ミス等）
            """
        elif state.get("last_query_result_count") == 0:
            error_context = f"""
            **問題**:
クエリは成功しましたが、結果が0行でした。

**改善の方向性**:
- フィルタ条件が厳しすぎる可能性があります（例: 年度指定、選手名のスペルミス）
- WHERE句の条件を緩和するか、LIKEクエリを使用してください
- 元のユーザー意図: "{state.get('original_user_intent', '')}"
            """
        else:
            error_context = "不明なエラーが発生しました。"

        # Reflection Prompt
        reflection_prompt = f"""
        あなたはMLBデータ分析の専門家です。以下のエラーを分析し、改善策を提案してください。

{error_context}

**あなたのタスク**:
1. エラーの根本原因を特定してください
2. 修正した条件で再度データ取得を試みてください
3. それでも失敗する場合は、別のアプローチ（別のツール、別のテーブル等）を検討してください

**重要**: ユーザーの元の質問「{state.get('original_user_intent', '')}」に答えるため、適切なツールを選択して実行してください。
        """

        # Let LLM think
        prompt = [SystemMessage(content=reflection_prompt)] + state["messages"]

        try:
            response = self.model.invoke(prompt)
            logger.info("Reflection completed",
                        has_tool_calls=bool(response.tool_calls),
                        retry_count=state.get("retry_count", 0))

            # Increment retry count
            return {
                "messages": [response],
                "retry_count": state.get("retry_count", 0) + 1
            }
        except Exception as e:
            logger.error("Reflection node error", error=str(e))
            raise AgentReasoningError("自己修正プロセス中にエラーが発生しました", original_error=e) from e

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
            # Reflection Loop fields
            "retry_count": 0,
            "max_retries": 2,
            "last_error": None,
            "last_query_result_count": -1,
            "original_user_intent": query,
            # UI metadata
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
