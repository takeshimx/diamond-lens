import os
import json
import logging
import time
from datetime import datetime, timezone
from typing import Annotated, TypedDict, List, Dict, Any, Union, Optional, AsyncGenerator
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

from backend.app.core.exceptions import DataFetchError, AgentReasoningError, DataStructureError
from backend.app.utils.structured_logger import get_logger
from .cache_service import StatsCache

from backend.app.core.exceptions import PromptInjectionError
from .security_guardrail import get_security_guardrail

logger = get_logger("ai-agent")

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

    # ====== For Reflection Loop ======
    retry_count: int # current retry count
    max_retries: int # max retry count for preventing infinite loop
    last_error: Optional[str] # last error message
    last_query_result_count: int # last query result count for detecting empty result
    original_user_intent: str # original user intent
    # =================================
    
    # UI表示用メタデータ
    isTable: bool
    isChart: bool
    tableData: Any
    chartData: Any
    columns: Any
    isTransposed: bool
    chartType: str
    chartConfig: Any
    isMatchupCard: bool
    matchupData: Optional[Dict[str, Any]]

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
    raw_data = get_mlb_stats_data(query, season)

    data = raw_data.get("data", [])
    columns = raw_data.get("columns", [])

    if len(data) == 0:
        return {
            "answer": "該当するデータが見つかりませんでした。",
            "isTable": False
            }
    
    # Output Format に応じて処理を分岐
    params = raw_data.get("parameters", {})
    output_format = params.get("output_format", "sentence")

    if output_format == "table":
        return {
            "answer": f"以下は{len(data)}件の結果です：",
            "isTable": True,
            "tableData": data,
            "columns": [{
                "key": col,
                "label": col.replace('_', ' ').title()
            }
            for col in columns],
            "isTransposed": len(data) == 1
        }
    else:
        from .simple_chart_service import enhance_response_with_simple_chart
        import pandas as pd

        df = pd.DataFrame(data)

        # Chart
        try:
            logger.info(f"Attempting chart enhancement for query: {query}")
            logger.info(f"Parameters: {params}")
            logger.info(f"DataFrame shape: {df.shape}")
            
            chart_data = enhance_response_with_simple_chart(
                query, params, df, params.get("season")
            )
            
            logger.info(f"Chart data result: {chart_data is not None}")

            if chart_data:
                response = {
                    "answer": "📈",
                    "isTable": False
                }
                response.update(chart_data)
                return response
        except Exception as e:
            logger.warning(f"Chart enhancement failed: {e}", exc_info=True)
        
        # チャートがない場合: LLM で自然言語生成
        from .ai_service import _generate_final_response_with_llm
        final_response = _generate_final_response_with_llm(query, df)
        
        return {
            "answer": final_response,
            "isTable": False
        }


@tool
def get_batter_stats_tool(query: str, season: int = None):
    """打撃成績（打率、本塁打、ランキング、状況別スタッツ等）を取得する専門ツール"""
    from .analytics.batter_services import get_ai_response_for_batter_stats
    return get_ai_response_for_batter_stats(query, season)


@tool
def get_pitcher_stats_tool(query: str, season: int = None):
    """投球成績（防御率、奪三振、ランキング、状況別スタッツ等）を取得する専門ツール"""
    from .analytics.pitcher_services import get_ai_response_for_pitcher_stats
    return get_ai_response_for_pitcher_stats(query, season)


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

    query = f"""
    SELECT *
    FROM `tksm-dash-test-25.mlb_analytics_dash_25.view_matchup_specific_history`
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
    LIMIT 30
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

    # Check cache first
    cache = StatsCache()
    cached_data = cache.get_player_stats(player_name=batter_name, season=2024, query_type=f"matchup_{pitcher_name}")
    if cached_data:
        logger.info("Cache HIT")
        return cached_data
    
    try:
        df = client.query(query, job_config=job_config).to_dataframe()
        logger.info(f"✅ Matchup history found", row_count=len(df), batter_name=batter_name, pitcher_name=pitcher_name)
        result = df.to_dict(orient='records')
        # Save to Redis
        cache.set_player_stats(player_name=batter_name, season=2024, query_type=f"matchup_{pitcher_name}", data=result)
        return result
    except Exception as e:
        raise DataFetchError("対戦履歴の取得に失敗しました", original_error=e) from e


@tool
def mlb_matchup_analytics_tool(batter_name: str, pitcher_name: str):
    """
    特定の打者と投手の『球種別の対戦相性サマリー』を取得する分析ツール。
    打率、OPSなどの結果だけでなく、空振り率、球速、平均回転数などの球のクオリティも取得できます。
    batter_name: 打者のフルネーム（例: 'Shohei Ohtani'）
    pitcher_name: 投手のフルネーム（例: 'Yu Darvish'）
    """
    query = f"""
    SELECT *
    FROM `tksm-dash-test-25.mlb_analytics_dash_25.view_matchup_pitch_analytics`
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
        return df.to_dict(orient='records')
    except Exception as e:
        logger.error(f"Error in mlb_matchup_analytics_tool: {e}")
        return []

# ---- 3. Agent Definition ----
class MLBStatsAgent:
    def __init__(self, model, tools):
        # 思考エンジン
        self.raw_model = model

        # Bind tools to model
        self.tools = tools
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
        workflow.add_node("reflection", self.reflection_node) # 自己修正
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

        # ========== executorからの条件分岐 ==========
        # executor実行後、エラー/空結果があればreflectionへ、なければoracleへ
        workflow.add_conditional_edges(
            "executor",
            self.should_reflect,
            {
                "reflection": "reflection",
                "oracle": "oracle"
            }
        )

        # ツール実行後は、再び oracle に戻って「次にするべきこと」を考えさせます
        workflow.add_edge("reflection", "oracle") # reflection -> oracle
        workflow.add_edge("synthesizer", END) # synthesizer -> END

        return workflow
    
    # Helper fucntion to determine if we should continue or end
    def should_continue(self, state: AgentState):
        last_message = state["messages"][-1]
        # メッセージの中にツール呼び出し要求が含まれているかチェック
        if last_message.tool_calls:
            return "continue"
        return "end"
    

        # Helper function: executorの結果を判定
    def should_reflect(self, state: AgentState):
        """
        executor実行後、Reflectionが必要かどうかを判定します。
        
        Reflectionが必要な条件:
        1. BigQueryエラーが発生した（SQLシンタックスエラー、カラム名誤認識等）
        2. クエリ結果が0行だった（フィルタ条件が厳しすぎる等）
        3. まだ最大リトライ回数に達していない
        
        Reflectionが不要な条件（Do NOT retry）:
        - パーミッション/認証エラー
        - タイムアウトエラー
        - データセット/スキーマレベルの構造エラー
        - 最大リトライ回数に達した
        """
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 2)
        last_error = state.get("last_error")
        result_count = state.get("last_query_result_count", -1)
        
        # 最大リトライ回数に達している場合は、Reflectionしない
        if retry_count >= max_retries:
            logger.info("Max retries reached, skipping reflection", 
                        retry_count=retry_count, 
                        max_retries=max_retries)
            return "oracle"  # 通常フローに戻る
        
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

    
    # Oracle node (判断)
    def oracle_node(self, state: AgentState):
        logger.info("Oracle node started", node="oracle", status="thinking")
        
        system_prompt = """あなたはMLBデータ収集の司令塔です。ユーザーの質問を分析し、最適なツール呼び出しを計画してください。

        **【絶対ルール】:**
        - 自分の知識だけで回答することは絶対に禁止です。必ずツールを呼び出してデータを取得してください。
        - **2025年を含む全シーズンのデータがデータベースに存在します。** 「データがない」「まだシーズンが始まっていない」などと判断せず、必ずツールを呼んでください。
        - ツールを呼ばずに直接回答することは禁止です。

        **重要な行動指針:**
        1. 打者と投手の特定の対戦（Matchup）に関する質問の場合、必ず `mlb_matchup_analytics_tool` と `mlb_matchup_history_tool` を使用して最新データを取得してください。
        2. 必ずBigQuery上のカスタムビューからデータを取得してください。
        3. 複数の選手を比較する場合、各対象について個別かつ詳細にデータを取得してください。
        4. 必要なデータが全て揃ったと確信できるまで、繰り返し実行（continue）を選択してください。"""

        # これまでの全履歴を Gemini に渡して推理させます
        prompt = [SystemMessage(content=system_prompt)] + state["messages"]

        try:
            response = self.model.invoke(prompt)
            return {"messages": [response]}
        except Exception as e:
            raise AgentReasoningError("AIの思考プロセス中にエラーが発生しました", original_error=e) from e
    
    # Executor node （実際に道具を使う）
    def executor_node(self, state: AgentState):
        logger.info("Executor node started", node="executor", status="executing")
        # ユーザーの最新の質問を取得
        last_message = state["messages"][-1]

        tool_outputs = []
        has_error = False
        result_count = -1
        error_message = ""

        # 要求されたすべてのツール呼び出しを処理
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            logger.info(f"Calling tool: {tool_name}")

            selected_tool = next((t for t in self.tools if t.name == tool_name), None)

            if selected_tool:
                result = selected_tool.invoke(tool_call["args"])

                # ===== エラー/空結果の検出 =====
                # デバッグ: 実際のresultの型と内容をログ出力
                logger.info(f"Tool result type: {type(result).__name__}, preview: {str(result)[:200]}")

                # 1. BigQuery error
                if isinstance(result, dict) and "error" in result:
                    has_error = True
                    error_message = result.get("error", "Unknown error")
                    logger.warning("Tool execution error detected",
                                   tool_name=tool_name,
                                   error=error_message)

                # 2. Empty result
                # ツールは通常 list を返す（df.to_dict(orient='records')）
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
                    # mlb_stats_toolの場合は`answer`フィールドもチェック
                    elif result.get("answer") and "データが見つかりませんでした" in result.get("answer", ""):
                        result_count = 0
                        logger.warning("Empty result detected (no data message)",
                                       tool_name=tool_name,
                                       answer_preview=result.get("answer", "")[:100])
                #==============================
            else:
                result = {"error": f"Tool {tool_name} not found in injected tools"}
                has_error = True
                error_message = result["error"]

            # Gemini API は NaN や Infinity を許容しないため、それらを None (null) に置換します。
            def sanitize_data(obj):
                if isinstance(obj, list):
                    return [sanitize_data(item) for item in obj]
                elif isinstance(obj, dict):
                    return {k: sanitize_data(v) for k, v in obj.items()}
                elif isinstance(obj, float):
                    if obj != obj: # NaN check (NaN is not equal to itself)
                        return None
                    if obj == float('inf') or obj == float('-inf'):
                        return None
                return obj

            sanitized_result = sanitize_data(result)

            # 結果を ToolMessage として作成
            tool_outputs.append(ToolMessage(
                tool_call_id=tool_call["id"],
                content=json.dumps(sanitized_result, ensure_ascii=False, default=str)
            ))
        
        return {
            "messages": tool_outputs,
            "last_error": error_message if has_error else None,
            "last_query_result_count": result_count
        }
    
    # Synthesizer node (分析と応答)
    def synthesizer_node(self, state: AgentState):
        logger.info("Synthesizer node started", node="synthesizer", status="analyzing")
        
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
            "chartConfig": None,
            "isMatchupCard": False,
            "matchupData": {}
        }

        # ツール呼び出し結果から対戦データを抽出 (UIカード用)
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

        # 履歴を遡って最後のツール実行結果（データ）を探す
        last_tool_res = None
        for msg in reversed(state["messages"]):
            if isinstance(msg, ToolMessage):
                try:
                    last_tool_res = json.loads(msg.content)
                    break
                except Exception as e:
                    raise DataStructureError("JSON解析エラーが発生しました。", original_error=e) from e
        
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
    
    # 3. Reflection node
    def reflection_node(self, state: AgentState):
        """
        In case of error or empty result, provide feedback to LLM and retry
        """
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


# Main function from external API
def run_mlb_agent(query: str) -> dict:
    """
    Main entry point for MLB agent system.
    Uses Supervisor pattern to route queries to specialized agents.
    """
    
    # Step 0: Security Guardrail
    guardrail = get_security_guardrail()
    is_safe, reason = guardrail.validate_and_log(query)
    if not is_safe:
        logger.warning(f"🚨 Query blocked by guardrail: {reason}", query=query[:100])
        raise PromptInjectionError(
            message="申し訳ございませんが、このリクエストにはお応えできません。MLB統計に関する質問をお願いいたします。",
            detected_pattern=reason
        )
    
    # Step 1: Import agents
    from .agents.supervisor_agent import SupervisorAgent
    from .agents.stats_agent import StatsAgent
    from .agents.batter_agents import BatterAgent
    from .agents.pitcher_agents import PitcherAgent
    from .agents.matchup_agent import MatchupAgent
    from .agents.strategy_agent import StrategyAgent

    # Step 2: Route query
    supervisor = SupervisorAgent()
    agent_type = supervisor.route_query(query)

    logger.info(f"Supervisor routed to: {agent_type}", query=query, agent_type=agent_type)

    # Step 3: Initialize model
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GEMINI_API_KEY_V2"),
        temperature=0 # 分析精度を高めるため、ランダム性を排除
    )

    # Step 4: Select and initialize agent
    if agent_type == "matchup":
        agent = MatchupAgent(model=model)
        result = agent.run(query)
    elif agent_type == "batter":
        agent = BatterAgent(model=model)
        result = agent.run(query)
    elif agent_type == "pitcher":
        agent = PitcherAgent(model=model)
        result = agent.run(query)
    elif agent_type == "stats":
        agent = StatsAgent(model=model)
        result = agent.run(query)
    elif agent_type == "strategy":
        agent = StrategyAgent(model=model)
        result = agent.run(query)
    else: # fallback to stats at this point
        logger.warning(f"Unknown agent type: '{agent_type}', falling back to StatsAgent")
        agent = StatsAgent(model=model)
        result = agent.run(query)
    
    logger.info(f" Agent execution completed", agent_type=agent_type)

    return result


async def run_mlb_agent_stream(query: str) -> AsyncGenerator[Dict[str, Any], None]:
    """
    MLB エージェントをストリーミングモードで実行します。

    LangGraphの astream_events() を使用して、エージェントの実行過程を
    リアルタイムでイベントとして送信します。

    Args:
        query: ユーザーからの質問

    Yields:
        イベント辞書:
            - type: イベントタイプ ("thinking", "tool_start", "tool_end", "token", "final_answer")
            - その他のメタデータ
    """
    import asyncio

    # ロガーを取得
    stream_logger = get_logger("ai-agent-stream")

    # Step 0: Security Guardrail
    guardrail = get_security_guardrail()
    is_safe, reason = guardrail.validate_and_log(query)
    if not is_safe:
        stream_logger.warning(f"🚨 Query blocked by guardrail: {reason}", query=query[:100])
        yield {
            "type": "error",
            "error_type": "blocked",
            "message": "申し訳ございませんが、このリクエストにはお応えできません。MLB統計に関する質問をお願いいたします。",
            "detected_pattern": reason
        }
        return
    
    # Step 1: Import agents
    from .agents.supervisor_agent import SupervisorAgent
    from .agents.stats_agent import StatsAgent
    from .agents.batter_agents import BatterAgent
    from .agents.pitcher_agents import PitcherAgent
    from .agents.matchup_agent import MatchupAgent
    from .agents.strategy_agent import StrategyAgent

    # Step 2: Route query
    supervisor = SupervisorAgent()
    agent_type = supervisor.route_query(query)

    stream_logger.info(f"Supervisor routed to: {agent_type}", query=query, agent_type=agent_type)

    yield {
        "type": "routing",
        "agent_type": agent_type,
        "message": f"{agent_type}エージェントにルーティングしました"
    }

    # Step 3: Initialize model
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.getenv("GEMINI_API_KEY_V2"),
        temperature=0
    )

    # Step 4: Select and initialize agent
    if agent_type == "matchup":
        agent = MatchupAgent(model=model)
    elif agent_type == "batter":
        agent = BatterAgent(model=model)
    elif agent_type == "pitcher":
        agent = PitcherAgent(model=model)
    elif agent_type == "stats":
        agent = StatsAgent(model=model)
    elif agent_type == "strategy":
        agent = StrategyAgent(model=model)
    else:
        stream_logger.warning(f"Unknown agent type: '{agent_type}', falling back to StatsAgent")
        agent = StatsAgent(model=model)

    # Step 5: ストリーミング実行
    # LangGraphの app.astream_events() を使ってイベントをキャプチャ
    from langchain_core.messages import HumanMessage
    
    initial_state = {
        "messages": [HumanMessage(content=query)],
        "raw_data_store": {},
        "next_step": "",
        "final_answer": "",
        "retry_count": 0,
        "max_retries": 2,
        "last_error": None,
        "last_query_result_count": -1,
        "original_user_intent": query,
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
        # StrategyAgent用（他エージェントでは無視される）
        "parallel_results": {},
    }
    
    # astream_events は async なので、ループで await する
    current_node = ""
    accumulated_answer = ""  # トークンを蓄積するための変数
    llm_start_time = None
    accumulated_llm_ms = 0.0  # LLM推論時間の累計（ミリ秒）

    # エージェントタイプに応じて適切なアプリを取得
    if hasattr(agent, 'app'):
        agent_app = agent.app
    elif hasattr(agent, 'graph'):
        agent_app = agent.graph
    else:
        # LangGraphを使わないエージェント（StatsAgent）の場合は、通常の実行
        stream_logger.info("Agent does not support streaming, falling back to regular execution")
        final_result = agent.run(query)
        yield {
            "type": "final_answer",
            "answer": final_result.get("final_answer", ""),
            "isTable": final_result.get("isTable", False),
            "tableData": final_result.get("tableData"),
            "columns": final_result.get("columns"),
            "isTransposed": final_result.get("isTransposed", False),
            "isChart": final_result.get("isChart", False),
            "chartType": final_result.get("chartType"),
            "chartData": final_result.get("chartData"),
            "chartConfig": final_result.get("chartConfig"),
            "isMatchupCard": final_result.get("isMatchupCard", False),
            "matchupData": final_result.get("matchupData"),
            "isStrategyReport": final_result.get("isStrategyReport", False),
            "strategyData": final_result.get("strategyData", None),
        }
        return

    async for event in agent_app.astream_events(initial_state, version="v2"):
        event_type = event.get("event")
        
        # ノード開始イベント
        if event_type == "on_chain_start":
            node_name = event.get("name", "")
            if node_name in ["oracle", "executor", "synthesizer", "reflection",
                             "planner", "parallel_executor", "aggregator", "strategist"]:
                current_node = node_name
                node_labels = {
                    # 既存エージェントノード
                    "oracle": "質問を分析しています",
                    "executor": "データを取得しています",
                    "synthesizer": "回答を生成しています",
                    "reflection": "エラーを分析し、修正を試みています",
                    # StrategyAgentノード
                    "planner": "分析計画を立てています",
                    "parallel_executor": "データを並列取得しています",
                    "aggregator": "データを集約・検証しています",
                    "strategist": "戦略レポートを生成しています",
                }
                node_details = {
                    # 既存エージェントノード
                    "oracle": "ユーザーの質問を理解し、必要なツールを選択",
                    "executor": "BigQueryからMLBデータを取得",
                    "synthesizer": "取得したデータを基に最終レポートを作成",
                    "reflection": "エラー原因を特定し、クエリを修正して再試行",
                    # StrategyAgentノード
                    "planner": "打者・投手・対戦傾向の収集対象を決定",
                    "parallel_executor": "4つのデータソースから並列でデータを取得",
                    "aggregator": "並列取得結果を検証し、次の処理を判断",
                    "strategist": "収集データを統合し、戦略分析レポートを作成",
                }

                # Reflectionノードの場合、リトライ回数も送信
                event_data = {
                    "type": "state_update",
                    "node": node_name,
                    "status": "started",
                    "message": node_labels.get(node_name, f"{node_name} を実行中"),
                    "node_details": node_details.get(node_name, ""),
                    "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                    "step_type": "node_start"
                }

                # Reflectionノードの場合のみ、リトライ情報を追加
                if node_name == "reflection":
                    # 現在のstateからretry_countを取得する必要があるが、
                    # astream_eventsではstateに直接アクセスできないため、
                    # イベントのメタデータから推測するか、グローバルカウンターを使用
                    event_data["retry_attempt"] = "リトライ中"

                yield event_data
        
        # ツール呼び出し開始
        elif event_type == "on_tool_start":
            tool_name = event.get("name", "")
            yield {
                "type": "tool_start",
                "tool_name": tool_name,
                "message": f"🔧 {tool_name} を実行中...",
                "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                "step_type": "tool_call"
            }
        
        # ツール呼び出し終了
        elif event_type == "on_tool_end":
            tool_name = event.get("name", "")
            tool_output = event.get("data", {}).get("output", {})

            # 出力サマリー生成
            output_summary = ""
            if isinstance(tool_output, str):
                try:
                    parsed = json.loads(tool_output)
                    if isinstance(parsed, list):
                        output_summary = f"{len(parsed)}件のデータを取得"
                except:
                    pass

            yield {
                "type": "tool_end",
                "tool_name": tool_name,
                "message": f"✅ {tool_name} 完了",
                "output_summary": output_summary,
                "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                "step_type": "tool_result"
            }
        
        # LLM呼び出し開始（レイテンシ計測）
        elif event_type == "on_chat_model_start":
            llm_start_time = time.time()

        # LLM呼び出し終了（レイテンシ計測）
        elif event_type == "on_chat_model_end":
            if llm_start_time is not None:
                accumulated_llm_ms += (time.time() - llm_start_time) * 1000
                llm_start_time = None

        # LLMトークンストリーミング
        elif event_type == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk", {})
            raw_content = getattr(chunk, "content", "")
            # langchain-google-genai v2+ はリスト形式で返す場合がある
            if isinstance(raw_content, list):
                content = "".join(
                    item.get("text", "") if isinstance(item, dict) else str(item)
                    for item in raw_content
                )
            else:
                content = raw_content or ""
            if content:
                accumulated_answer += content  # トークンを蓄積
                yield {
                    "type": "token",
                    "content": content,
                    "node": current_node
                }
        
        # ノード終了イベント
        elif event_type == "on_chain_end":
            node_name = event.get("name", "")
            if node_name in ["oracle", "executor", "synthesizer", "reflection",
                             "planner", "parallel_executor", "aggregator", "strategist"]:
                yield {
                    "type": "state_update",
                    "node": node_name,
                    "status": "completed",
                    "message": f"{node_name} 完了",
                    "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                    "step_type": "node_end"
                }
    
    # 最終状態を取得 (ストリーミング終了後)
    # ストリーミング中に蓄積した答えを使用
    if accumulated_answer:
        # トークンが蓄積されている場合は、すぐに final_answer を送信
        stream_logger.info("Accumulated answer available, sending final_answer immediately")
        yield {
            "type": "final_answer",
            "answer": accumulated_answer,
            "isTable": False,
            "tableData": None,
            "columns": None,
            "isTransposed": False,
            "isChart": False,
            "chartType": None,
            "chartData": None,
            "chartConfig": None,
            "isMatchupCard": False,
            "matchupData": None,
            "isStrategyReport": agent_type == "strategy",
            "strategyData": None,
            "llm_latency_ms": accumulated_llm_ms,
        }
    else:
        # 蓄積された答えがない場合は agent.run() を実行
        stream_logger.info("No accumulated answer, running agent.run() to get final result")
        final_result = agent.run(query)
        yield {
            "type": "final_answer",
            "answer": final_result.get("final_answer", ""),
            "isTable": final_result.get("isTable", False),
            "tableData": final_result.get("tableData"),
            "columns": final_result.get("columns"),
            "isTransposed": final_result.get("isTransposed", False),
            "isChart": final_result.get("isChart", False),
            "chartType": final_result.get("chartType"),
            "chartData": final_result.get("chartData"),
            "chartConfig": final_result.get("chartConfig"),
            "isMatchupCard": final_result.get("isMatchupCard", False),
            "matchupData": final_result.get("matchupData"),
            "isStrategyReport": final_result.get("isStrategyReport", False),
            "strategyData": final_result.get("strategyData", None),
            "llm_latency_ms": accumulated_llm_ms,
        }

    stream_logger.info(f"✅ Stream execution completed", agent_type=agent_type)

