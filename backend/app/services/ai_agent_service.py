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

from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter
from .mlb_data_engine import get_mlb_stats_data
from .bigquery_service import client

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


@tool
def mlb_matchup_history_tool(batter_name: str, pitcher_name: str):
    """
    特定の打者と投手の『過去の全対決履歴』を取得するツール。
    打席ごとの配球（球種の流れ）や、結果、コースなどの詳細なプロセスを取得できます。
    batter_name: 打者のフルネーム（例: 'Shohei Ohtani'）
    pitcher_name: 投手のフルネーム（例: 'Yu Darvish'）
    """
    logger.info(f"🔍 DEBUG: mlb_matchup_history_tool called with batter='{batter_name}', pitcher='{pitcher_name}'")
    batter_name = batter_name.strip()
    pitcher_name = pitcher_name.strip()

    # 名前形式の不一致（First Last vs Last, First）および大文字小文字の不一致に対応
    # ユーザーのスクリーンショットに基づき、正確なテーブル名 `view_matchup_specific_history_2025` を使用
    query = f"""
    SELECT *
    FROM `tksm-dash-test-25.mlb_analytics_dash_25.view_matchup_specific_history_2025`
    WHERE (
        (UPPER(batter_name) = UPPER(@batter_name)) OR
        (UPPER(batter_name) = UPPER(@batter_reversed)) OR
        (UPPER(batter_name) LIKE UPPER(@batter_part))
    ) AND (
        (UPPER(pitcher_name) = UPPER(@pitcher_name)) OR
        (UPPER(pitcher_name) = UPPER(@pitcher_reversed)) OR
        (UPPER(pitcher_name) LIKE UPPER(@pitcher_part))
    )
    ORDER BY game_date DESC, at_bat_number DESC
    LIMIT 20
    """

    def reverse_name(name):
        parts = name.split()
        return f"{parts[-1]}, {' '.join(parts[:-1])}" if len(parts) > 1 else name

    b_rev = reverse_name(batter_name)
    p_rev = reverse_name(pitcher_name)
    b_part = f"%{batter_name.split()[-1]}%" if len(batter_name.split()) > 0 else "%"
    p_part = f"%{pitcher_name.split()[-1]}%" if len(pitcher_name.split()) > 0 else "%"

    query_parameters = [
        ScalarQueryParameter("batter_name", "STRING", batter_name),
        ScalarQueryParameter("batter_reversed", "STRING", b_rev),
        ScalarQueryParameter("batter_part", "STRING", b_part),
        ScalarQueryParameter("pitcher_name", "STRING", pitcher_name),
        ScalarQueryParameter("pitcher_reversed", "STRING", p_rev),
        ScalarQueryParameter("pitcher_part", "STRING", p_part)
    ]

    job_config = QueryJobConfig(query_parameters=query_parameters)

    try:
        df = client.query(query, job_config=job_config).to_dataframe()
        logger.info(f"✅ Matchup history: Found {len(df)} rows for {batter_name} vs {pitcher_name}")
        return df.to_dict(orient='records')
    except Exception as e:
        logger.error(f"Error in matchup_history_tool: {e}")
        return []


@tool
def mlb_matchup_analytics_tool(batter_name: str, pitcher_name: str):
    """
    特定の打者と投手の『球種別の対戦相性サマリー』を取得する分析ツール。
    打率、OPSなどの結果だけでなく、空振り率、球速、平均回転数などの球のクオリティも取得できます。
    戦略的な分析（どの球種が苦手か、など）を行う際に最適です。
    batter_name: 打者のフルネーム（例: 'Shohei Ohtani'）
    pitcher_name: 投手のフルネーム（例: 'Yu Darvish'）
    """
    
    def reverse_name(name):
        parts = name.split()
        return f"{parts[-1]}, {' '.join(parts[:-1])}" if len(parts) > 1 else name
    
    b_rev = reverse_name(batter_name)
    p_rev = reverse_name(pitcher_name)
    b_part = f"%{batter_name.split()[-1]}%" if len(batter_name.split()) > 0 else "%"
    p_part = f"%{pitcher_name.split()[-1]}%" if len(pitcher_name.split()) > 0 else "%"

    query = f"""
    SELECT *
    FROM `tksm-dash-test-25.mlb_analytics_dash_25.view_matchup_pitch_analytics_2021_2025`
    WHERE (
        (UPPER(batter_name) = UPPER(@batter_name)) OR
        (UPPER(batter_name) = UPPER(@batter_reversed)) OR
        (UPPER(batter_name) LIKE UPPER(@batter_part))
    ) AND (
        (UPPER(pitcher_name) = UPPER(@pitcher_name)) OR
        (UPPER(pitcher_name) = UPPER(@pitcher_reversed)) OR
        (UPPER(pitcher_name) LIKE UPPER(@pitcher_part))
    )
    ORDER BY pitch_count DESC
    """

    query_parameters = [
        ScalarQueryParameter("batter_name", "STRING", batter_name),
        ScalarQueryParameter("batter_reversed", "STRING", b_rev),
        ScalarQueryParameter("batter_part", "STRING", b_part),
        ScalarQueryParameter("pitcher_name", "STRING", pitcher_name),
        ScalarQueryParameter("pitcher_reversed", "STRING", p_rev),
        ScalarQueryParameter("pitcher_part", "STRING", p_part)
    ]

    job_config = QueryJobConfig(query_parameters=query_parameters)

    try:
        df = client.query(query, job_config=job_config).to_dataframe()
        logger.info(f"Matchup Analytics: Found {len(df)} pitch types for {batter_name} vs {pitcher_name}")
        return df.to_dict(orient='records')
    except Exception as e:
        logger.error(f"Error in mlb_matchup_analytics_tool: {e}")
        return []


# ---- 3. Agent Definition ----
class MLBStatsAgent:
    def __init__(self):
        # 思考エンジン
        self.raw_model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=os.getenv("GEMINI_API_KEY_V2"),
            temperature=0 # 分析精度を高めるため、ランダム性を排除
        )

        # Bind tools to model
        self.tools = [
            mlb_stats_tool, 
            mlb_matchup_history_tool,
            mlb_matchup_analytics_tool
        ]
        self.model = self.raw_model.bind_tools(self.tools)

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
        
        # 物理的にツール呼び出しを強制するためのフラグ (Gemini 2.0 Flash用)
        # 最初のターンの場合、あるいはまだデータがない場合は強制する
        is_first_turn = len(state["messages"]) <= 1
        
        system_prompt = """あなたはMLBデータエンジニアです。
        ユーザーの質問を解決するために、利用可能なツールから最適なものを選択して実行してください。
        
        【ルール】
        - 自分の知識で答えず、必ずツール（mlb_matchup_analytics_tool等）を使ってください。
        - 選手名は英語（Shohei Ohtani等）に変換してツールに渡してください。
        - このステップでは日本語の説明文を生成せず、ツール呼び出し（tool_call）のみを行ってください。"""

        prompt = [SystemMessage(content=system_prompt)] + state["messages"]
        
        # tool_choice="any" (またはモデル固有の ANY モード) を使用して強制召喚
        # config = {"tool_config": {"function_calling_config": {"mode": "ANY"}}}
        # LangChainの汎用的な方式で試行
        try:
            # First turn: Force the matchup analytics tool to ensure we get data
            if is_first_turn:
                # 特定の対戦に関する質問なら、analyticsツールを強制
                response = self.model.invoke(prompt, tool_choice="mlb_matchup_analytics_tool")
            else:
                response = self.model.invoke(prompt)
        except Exception as e:
            logger.error(f"Error in oracle tool binding: {e}")
            response = self.model.invoke(prompt)
        
        logger.debug(f"🔍 DEBUG: Oracle Response: {response.content}")
        if response.tool_calls:
            logger.info(f"✅ Oracle planned {len(response.tool_calls)} tool calls")
        else:
            logger.warning("⚠️ Oracle did NOT call any tools. Trying one last fallback.")
            # それでも呼ばない場合は、モデルを介さず history ツールなどを呼ぶべきだが、まずはinvokeを信じる

        return {"messages": [response]}
    
    # Executor node （実際に道具を使う）
    def executor_node(self, state: AgentState):
        logger.info("--- NODE: EXECUTOR (Executing tool...) ---")
        # ユーザーの最新の質問を取得
        last_message = state["messages"][-1]

        tool_outputs = []
        # 利用可能なツールをマッピング
        tools_map = {
            "mlb_stats_tool": mlb_stats_tool,
            "mlb_matchup_history_tool": mlb_matchup_history_tool,
            "mlb_matchup_analytics_tool": mlb_matchup_analytics_tool
        }

        # 要求されたすべてのツール呼び出しを処理
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            logger.info(f"Calling tool: {tool_name}")
            
            if tool_name in tools_map:
                # ツール名に応じて適切な関数を呼び出す
                result = tools_map[tool_name].invoke(tool_call["args"])
            else:
                logger.warning(f"Tool {tool_name} not found in tools_map")
                result = {"error": f"Tool '{tool_name}' not found."}

            # 結果を ToolMessage として作成
            # Gemini API は NaN や Infinity を許容しないため、それらを None (null) に置換します。
            # また、date型などの特殊な型を文字列に変換できるよう default=str を指定します。
            def sanitize_data(obj):
                if isinstance(obj, list):
                    return [sanitize_data(item) for item in obj]
                elif isinstance(obj, dict):
                    return {k: sanitize_data(v) for k, v in obj.items()}
                elif isinstance(obj, float):
                    if obj != obj: # NaN check
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
    
    # Synthesizer node (分析と応答)
    def synthesizer_node(self, state: AgentState):
        logger.info("--- NODE: SYNTHESIZER (Final analysis) ---")
        
        # 1. AIへの指示（丁寧な説明と要約統計を最優先する）
        system_prompt = """あなたはMLBアナリストです。
        提供されたデータを基に、ユーザーに対し丁寧かつ魅力的にレポートしてください。

        **【出力の絶対ルール】:**
        1. **データの裏付けがない回答の禁止**: ツールから提供されたデータ（ToolMessageの内容）のみをソースとしてください。もしツールがデータを返さなかった場合は、知っているふりをせず「データが取得できませんでした」と正直に回答してください。自身の知識で数値を補完することは厳禁です。
        2. **「説明」から始める**: 数値や結論を出す前に、まず「どのようなデータを調査したか」「その結果、全体として何が分かったか」を最初に言葉で丁寧に説明してください（ユーザーからの強い要望です）。
        3. **主要成績（Key Stats）の要約**: 打席ごとのデータがある場合は、それらを基に必ず「対戦成績の要約」（打率、OPS、三振、四球など）を算出して提示してください。
           - 算出項目例: 打率(BA)、出塁率、長打率、OPS、ホームラン数、三振数、四球数。
           - これらを回答の冒頭（状況説明の直後）に分かりやすく表または箇条書きで示してください。
        3. **挨拶と丁寧な言葉遣い**: 「分析の結果、〜ということが分かりました」といった対話形式の丁寧な言葉遣いを心がけてください。
        4. **データがない場合の説明**: 単に「データがありません」で終わらせず、どのような条件で検索し、なぜ見つからなかったのかをユーザーに寄り添って詳しく説明してください。"""

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
