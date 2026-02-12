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
        # ツール実行後は、再び oracle に戻って「次にするべきこと」を考えさせます
        workflow.add_edge("executor", "oracle")
        # 最終回答生成後は終了
        workflow.add_edge("synthesizer", END)

        return workflow.compile()
    

    def should_continue(self, state):
        return "continue" if state["messages"][-1].tool_calls else "end"
    

    def oracle_node(self, state):
        system_prompt = """
        あなたはMLB打撃データの司令塔です。
        打撃成績に関する質問に対し、`get_batter_stats_tool` を使用してデータを取得してください。
        """
        prompt = [SystemMessage(content=system_prompt)] + state["messages"]

        return {"messages": [self.model.invoke(prompt)]}
    

    def executor_node(self, state):
        last_message = state["messages"][-1]
        tool_outputs = []
        for tool_call in last_message.tool_calls:
            from ..ai_agent_service import get_batter_stats_tool
            result = get_batter_stats_tool.invoke(tool_call["args"])
            tool_outputs.append(ToolMessage(
                tool_call_id=tool_call["id"],
                content=json.dumps(result, ensure_ascii=False)
            ))
        return {"messages": tool_outputs}
    

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
            "isTable": False,
            "isChart": False,
            "tableData": None,
            "chartData": None
        }
        return self.app.invoke(initial_state)
                    
    
