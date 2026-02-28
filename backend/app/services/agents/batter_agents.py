import os
import json
import logging
from typing import Annotated, TypedDict, List, Dict, Any, Union, Optional
from operator import add
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from backend.app.core.exceptions import AgentReasoningError
from backend.app.utils.structured_logger import get_logger


logger = get_logger("batter_agent")

class BatterAgent:
    def __init__(self, model):
        self.raw_model = model
        # 呼び出し側(ai_agent_service)で定義される batter 専用ツールをバインド
        # ※ ツール定義はこの後 ai_agent_service.py で行います
        from ..ai_agent_service import get_batter_stats_tool
        self.tools = [get_batter_stats_tool]
        self.model = self.raw_model.bind_tools(self.tools)
        # build graph
        self.app = self._build_graph()
    
    def _build_graph(self):
        from ..ai_agent_service import AgentState
        workflow = StateGraph(AgentState)

        workflow.add_node("oracle", self.oracle_node)
        workflow.add_node("executor", self.executor_node)
        workflow.add_node("reflection", self.reflection_node)
        workflow.add_node("synthesizer", self.synthesizer_node)

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
        return "continue" if state["messages"][-1].tool_calls else "end"

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
        system_prompt = """
        あなたはMLB打撃データの司令塔です。
        打撃成績に関する質問に対し、`get_batter_stats_tool` を使用してデータを取得してください。
        """
        prompt = [SystemMessage(content=system_prompt)] + state["messages"]

        return {"messages": [self.model.invoke(prompt)]}
    

    def executor_node(self, state):
        logger.info("Executor node started", node="executor", status="executing")
        last_message = state["messages"][-1]
        tool_outputs = []
        has_error = False
        result_count = -1
        error_message = ""

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            logger.info(f"Calling tool: {tool_name}")

            from ..ai_agent_service import get_batter_stats_tool
            result = get_batter_stats_tool.invoke(tool_call["args"])

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

            tool_outputs.append(ToolMessage(
                tool_call_id=tool_call["id"],
                content=json.dumps(result, ensure_ascii=False)
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
        system_prompt = """
        あなたはMLB公式シニア・打撃アナリストです。
        取得したデータを基に、打者のパフォーマンスを深く分析してください。
        """
        prompt = [SystemMessage(content=system_prompt)] + state["messages"]
        response = self.raw_model.invoke(prompt)

        # UIメタデータの抽出（MatchupAgentと同様のロジック）
        ui_metadata = self._extract_ui_metadata(state)
        return {
            "final_answer": response.content.strip(),
            **ui_metadata,
            "messages": [response]
        }
    

    def _extract_ui_metadata(self, state):

        for msg in reversed(state["messages"]):
            if isinstance(msg, ToolMessage): # msgがToolMessageかどうかをチェック。ユーザーの挨拶やAIの返答を無視して、データが入っているメッセージだけを捕まえるためのフィルター
                try:
                    res = json.loads(msg.content)
                    if res.get("isTable"):
                        return {
                            "isTable": True,
                            "tableData": res.get("tableData"),
                            "columns": res.get("columns"),
                            "isTransposed": res.get("isTransposed")
                        }
                    # チャート対応もここに入れる
                    if res.get("isChart"):
                        return {
                            "isChart": True,
                            "chartData": res.get("chartData")
                        }
                except: continue
        
        return {"isTable": False}
    

    def run(self, query: str):
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
        return self.app.invoke(initial_state)
                    
    
