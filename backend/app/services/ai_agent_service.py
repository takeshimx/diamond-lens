import os
import json
import logging
from typing import Annotated, TypedDict, List, Dict, Any, Union
from operator import add
import pandas as pd
from .simple_chart_service import enhance_response_with_simple_chart

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END

from .mlb_data_engine import get_mlb_stats_data

logger = logging.getLogger(__name__)

# ---- 1. Agent State ----
# LangGraphでは、この辞書が各ノード（工程）間を引き継がれます。
class AgentState(TypedDict):
    # 会話履歴
    messages: Annotated[List[BaseMessage], add]
    # エンジンから取得した「生データ」を一時的に保管する場所です。
    raw_data_store: Dict[str, Any]
    # 次に何をするかのフラグや状態管理用
    next_step: str
    # 最終的な日本語の回答文
    final_answer: str
    
    # UI表示用メタデータ
    isTable: bool
    isChart: bool
    tableData: Any
    chartData: Any
    columns: Any
    isTransposed: bool
    chartType: str
    chartConfig: Any

# ---- 2. Tool Definition ----
# ツールのラッパー（既存ロジックのラップ）
@tool
def mlb_stats_tool(query: str, season: int = None):
    """
    MLBの打撃成績、投手成績、ランキング、特定の状況下（得点圏など）のデータ（BigQuery）を取得するためのツール。
    query: 検索したい内容の自然言語（例: '大谷翔平の打率'）
    season: 対象年度（例: 2024）。指定がない場合は最新を探します。
    """
    # AIはこの Docstring を読んで理解する。
    return get_mlb_stats_data(query, season)

# ---- 3. Agent Definition ----
class MLBStatsAgent:
    def __init__(self):
        # 思考エンジン
        self.raw_model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=os.getenv("GEMINI_API_KEY_V2"),
            temperature=0 # 分析精度を高めるため、ランダム性を排除
        )

        # Bind tools to model
        self.model = self.raw_model.bind_tools([mlb_stats_tool])

        # Build graph
        self.workflow = self._create_workflow()
        self.app = self.workflow.compile()
    
    def _create_workflow(self):
        # ワークフロー（状態遷移図）を定義
        workflow = StateGraph(AgentState)

        # 1. 各工程（ノード）を登録
        workflow.add_node("oracle", self.oracle_node) # 判断
        workflow.add_node("executor", self.executor_node) # 実行（ツールを呼び出し）
        workflow.add_node("synthesizer", self.synthesizer_node) # 分析（回答を生成）

        # 2. 工程を線（エッジ）でつなぐ
        workflow.set_entry_point("oracle") # Start from oracle

        # 条件付きエッジ
        # oracle の結果、ツール呼び出しがあれば executor へ、なければ synthesizer へ
        workflow.add_conditional_edges(
            "oracle",
            self.should_continue,
            {
                "continue": "executor",
                "end": "synthesizer"
            }
        )

        # ツール実行後は、再び oracle に戻って「次にするべきこと」を考えさせます
        workflow.add_edge("executor", "oracle") # executor -> oracle
        workflow.add_edge("synthesizer", END) # synthesizer -> END

        return workflow
    
    # Helper fucntion to determine if we should continue or end
    def should_continue(self, state: AgentState):
        last_message = state["messages"][-1]
        # メッセージの中にツール呼び出し要求が含まれているかチェック
        if last_message.tool_calls:
            return "continue"
        return "end"
    
    # Oracle node (判断)
    def oracle_node(self, state: AgentState):
        logger.info("--- NODE: ORACLE (Thinking...) ---")
        
        system_prompt = """あなたはMLBデータ収集の司令塔です。ユーザーの質問を分析し、最適なツール呼び出しを計画してください。
        
        **重要な行動指針:**
        1. 複数の選手や項目（例: 大谷とジャッジ）を比較する場合、1回の検索で済ませようとせず、必ず各対象について個別かつ詳細にデータを取得してください。
        2. ツールからの応答が「不十分」と感じた場合は、検索クエリを変えて再度実行してください。
        3. 必要なデータが全て揃ったと確信できるまで、繰り返し実行（continue）を選択してください。"""

        # これまでの全履歴を Gemini に渡して推理させます
        prompt = [SystemMessage(content=system_prompt)] + state["messages"]
        response = self.model.invoke(prompt)
        return {"messages": [response]}
    
    # Executor node （実際に道具を使う）
    def executor_node(self, state: AgentState):
        logger.info("--- NODE: EXECUTOR (Executing tool...) ---")
        # ユーザーの最新の質問を取得
        last_message = state["messages"][-1]

        tool_outputs = []
        # 要求されたすべてのツール呼び出しを処理
        for tool_call in last_message.tool_calls:
            # 実際にエンジンを実行
            result = mlb_stats_tool.invoke(tool_call["args"])

            # 結果を ToolMessage として作成（tool_call_id でどの要求への回答か紐付けます）
            tool_outputs.append(ToolMessage(
                tool_call_id=tool_call["id"],
                content=json.dumps(result, ensure_ascii=False)
            ))
        
        return {"messages": tool_outputs}
    
    # Synthesizer node (分析と応答)
    def synthesizer_node(self, state: AgentState):
        logger.info("--- NODE: SYNTHESIZER (Final analysis) ---")
        
        # 1. AIへの指示
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
        
        response = self.raw_model.invoke(prompt)
        final_answer = response.content.strip()

        # 書き出しのバグ（「〜となっています」等）に対する強力な防護策
        bad_prefixes = ["となっています。", "と言えます。", "となりました。", "となっております。", "となっています", "となっております"]
        for prefix in bad_prefixes:
            if final_answer.startswith(prefix):
                final_answer = final_answer[len(prefix):].lstrip("。").strip()
                break

        # 2. UI表示用のデータの抽出ロジック
        ui_metadata = {
            "isTable": False,
            "isChart": False,
            "tableData": None,
            "chartData": None,
            "columns": None,
            "isTransposed": False,
            "chartType": "",
            "chartConfig": None
        }

        # 履歴を遡って最後のツール実行結果（データ）を探す
        last_tool_res = None
        for msg in reversed(state["messages"]):
            if isinstance(msg, ToolMessage):
                try:
                    last_tool_res = json.loads(msg.content)
                    break
                except: continue
        
        if last_tool_res and "data" in last_tool_res:
            # データをデータフレーム化し、カラム名を小文字に統一（チャート/テーブルのキー不一致を防ぐ）
            df = pd.DataFrame(last_tool_res["data"])
            df.columns = [c.lower() for c in df.columns]
            
            # パラメータも小文字のカラムを参照するように調整
            params = last_tool_res.get("parameters", {})
            normalized_data = df.to_dict(orient="records")

            # 1. まずチャートの判定を優先
            chart_info = enhance_response_with_simple_chart(state["messages"][0].content, params, df)
            
            # フォールバック: データに月情報があればチャート化を試みる
            if not chart_info and any(col in df.columns for col in ['month', 'game_month']):
                params['split_type'] = 'monthly'
                chart_info = enhance_response_with_simple_chart(state["messages"][0].content, params, df)

            if chart_info:
                ui_metadata.update(chart_info)
            else:
                # 2. チャートでない場合のみテーブル表示を検討
                if params.get("output_format") == "table" or len(df) > 5:
                    ui_metadata["isTable"] = True
                    ui_metadata["tableData"] = normalized_data
                    ui_metadata["columns"] = [{"key": c, "label": c.replace('_', ' ').title()} for c in df.columns]
                    ui_metadata["isTransposed"] = len(df) == 1

        return {
            "final_answer": final_answer,
            **ui_metadata
            }


# Main function from external API
def run_mlb_agent(query: str) -> dict:
    agent = MLBStatsAgent()

    # 初期状態をセット
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
        "chartConfig": None
    }

    # グラフを実行（最大10ステップに制限してタイムアウトを防ぐ）
    final_state = agent.app.invoke(initial_state, config={"recursion_limit": 10})

    # 最終的なメッセージ履歴を含めた状態全体を返却
    # AIMessageオブジェクトなどはJSON化できないため、文字列化または辞書化が必要になる場合があるが、
    # ここでは辞書として返し、エンドポイント側でパースする
    return final_state
