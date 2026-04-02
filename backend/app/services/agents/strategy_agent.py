import asyncio
import json
from typing import Annotated, TypedDict, List, Dict, Any, Optional
from operator import add

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, ToolMessage

from backend.app.utils.structured_logger import get_logger
from backend.app.core.exceptions import AgentReasoningError
from backend.app.config.prompt_registry import get_prompt

logger = get_logger("strategy-agent")


# ===== 1. State定義 =====
# AgentState を拡張し、並列実行結果を保持する parallel_results フィールドを追加
class StrategyAgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add]
    raw_data_store: Dict[str, Any]
    next_step: str
    final_answer: str
    # Reflection Loop
    retry_count: int
    max_retries: int
    last_error: Optional[str]
    last_query_result_count: int
    original_user_intent: str
    # 並列実行結果の保管場所（ツール名 → 結果）
    parallel_results: Dict[str, Any]
    # UI metadata（既存AgentStateと同一）
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


# ===== 2. StrategyAgent クラス =====
class StrategyAgent:
    """
    Plan-and-Execute + Parallel Fan-Out パターンで
    打者・投手・対戦傾向を横断的に分析する戦略エージェント。
    """

    def __init__(self, model):
        self.raw_model = model  # ツールなし（最終レポート生成用）

        # 4つのツールをインポートしてバインド
        from ..ai_agent_service import (
            get_batter_stats_tool,
            get_pitcher_stats_tool,
            mlb_matchup_history_tool,
            mlb_matchup_analytics_tool,
        )
        self.tools = [
            get_batter_stats_tool,
            get_pitcher_stats_tool,
            mlb_matchup_history_tool,
            mlb_matchup_analytics_tool,
        ]
        self.model = model.bind_tools(self.tools)
        self.graph = self._build_graph()

    # ===== 3. グラフ構築 =====
    def _build_graph(self):
        """LangGraph ワークフローを構築"""
        workflow = StateGraph(StrategyAgentState)

        # ノード追加
        workflow.add_node("planner", self.planner_node)
        workflow.add_node("parallel_executor", self.parallel_executor_node)
        workflow.add_node("aggregator", self.aggregator_node)
        workflow.add_node("reflection", self.reflection_node)
        workflow.add_node("strategist", self.strategist_node)

        # エッジ設定
        workflow.set_entry_point("planner")

        # planner → ツール呼び出しがあれば並列実行、なければ直接strategistへ
        workflow.add_conditional_edges(
            "planner",
            self.should_execute,
            {"execute": "parallel_executor", "end": "strategist"}
        )

        # parallel_executor → aggregator（常に）
        workflow.add_edge("parallel_executor", "aggregator")

        # aggregator → エラーがあればreflection、なければstrategistへ
        workflow.add_conditional_edges(
            "aggregator",
            self.should_reflect,
            {"reflection": "reflection", "strategist": "strategist"}
        )

        # reflection → planner（再計画）
        workflow.add_edge("reflection", "planner")
        workflow.add_edge("strategist", END)

        return workflow.compile()

    # ===== 4. 条件分岐ロジック =====
    def should_execute(self, state):
        """plannerの出力にtool_callsがあるか判定"""
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            return "execute"
        return "end"

    def should_reflect(self, state):
        """MatchupAgentパターン踏襲 + 非リトライエラーはstrategistへ直行"""
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 2)
        last_error = state.get("last_error")
        result_count = state.get("last_query_result_count", -1)

        if retry_count >= max_retries:
            return "strategist"

        # 非リトライ: 認証・タイムアウト・スキーマ系エラー
        if last_error and any(kw in last_error.lower() for kw in [
            "permission", "access denied", "unauthorized", "forbidden",
            "timeout", "dataset", "schema", "not found", "does not exist"
        ]):
            return "strategist"

        # リトライ: SQLシンタックス・カラム名ミス
        if last_error and any(kw in last_error.lower() for kw in [
            "syntax", "unrecognized", "invalid", "column", "table"
        ]):
            return "reflection"

        # リトライ: 空結果
        if result_count == 0:
            return "reflection"

        return "strategist"

    # ===== 5. ノード実装 =====
    def planner_node(self, state):
        """Plannerノード: 4ツールをバインドし、複数ツールを同時呼び出し計画"""
        logger.info("Planner node started", node="planner")

        system_prompt = get_prompt("strategy_planner")
        prompt = [SystemMessage(content=system_prompt)] + state["messages"]

        try:
            response = self.model.invoke(prompt)
            return {"messages": [response]}
        except Exception as e:
            raise AgentReasoningError("計画ノードでエラーが発生しました", original_error=e) from e

    def parallel_executor_node(self, state):
        """ParallelExecutorノード: asyncio.gather() + asyncio.to_thread() で並列実行"""
        logger.info("Parallel executor node started", node="parallel_executor")

        last_message = state["messages"][-1]
        tool_calls = last_message.tool_calls

        # 非同期で全ツールを並列実行
        async def run_all():
            async def run_single(tool_call):
                tool_name = tool_call["name"]
                selected_tool = next((t for t in self.tools if t.name == tool_name), None)
                if selected_tool:
                    try:
                        # 同期ツールをスレッドプールで非同期実行
                        result = await asyncio.to_thread(selected_tool.invoke, tool_call["args"])
                    except Exception as e:
                        # 例外をエラーdictに変換して他ツールの結果を守る
                        logger.warning(f"Tool {tool_name} raised exception", error=str(e))
                        result = {"error": str(e)}
                else:
                    result = {"error": f"Tool {tool_name} not found"}
                return tool_call, result

            return await asyncio.gather(*[run_single(tc) for tc in tool_calls])

        results = asyncio.run(run_all())

        tool_outputs = []
        has_error = False
        result_count = -1
        error_message = ""
        parallel_results = {}

        for tool_call, result in results:
            tool_name = tool_call["name"]
            logger.info(f"Parallel tool completed: {tool_name}")

            # エラー検出
            if isinstance(result, dict) and "error" in result:
                has_error = True
                error_message = result.get("error", "Unknown error")
                logger.warning("Tool error detected", tool_name=tool_name, error=error_message)

            # 件数カウント（MatchupAgentと同じ方式）
            if isinstance(result, list):
                result_count = len(result)
            elif isinstance(result, dict) and "data" in result:
                result_count = len(result["data"])

            # 結果を保管
            parallel_results[tool_name] = result

            # NaN/Infinity のサニタイズ
            sanitized = self._sanitize(result)

            tool_outputs.append(ToolMessage(
                tool_call_id=tool_call["id"],
                content=json.dumps(sanitized, ensure_ascii=False, default=str)
            ))

        return {
            "messages": tool_outputs,
            "parallel_results": parallel_results,
            "last_error": error_message if has_error else None,
            "last_query_result_count": result_count,
        }

    def aggregator_node(self, state):
        """Aggregatorノード: 並列結果を検証し、次ステップを判断"""
        logger.info("Aggregator node started", node="aggregator")

        parallel_results = state.get("parallel_results", {})
        failed = {k: v for k, v in parallel_results.items()
                  if isinstance(v, dict) and "error" in v}
        successful = {k: v for k, v in parallel_results.items() if k not in failed}

        logger.info(f"Results: {len(successful)} success, {len(failed)} failed")

        # 全ツールが失敗した場合はエラーをセット
        if len(successful) == 0 and len(failed) > 0:
            error_msg = "; ".join([v.get("error", "") for v in failed.values()])
            logger.warning("All tools failed", error=error_msg)
            return {"last_error": error_msg}

        # 一部成功していれば続行（エラーはリセット）
        return {"last_error": None}

    def reflection_node(self, state):
        """Reflectionノード: MatchupAgentパターン踏襲"""
        logger.info("Reflection node started",
                    node="reflection",
                    retry_count=state.get("retry_count", 0))

        error_context = ""
        if state.get("last_error"):
            error_context = f"""
**発生したエラー**: {state['last_error']}

**エラーの原因として考えられること**:
- カラム名の誤認識（例: `player_name` ではなく `name_display_first_last` が正しい可能性）
- テーブル名の誤認識
- SQLシンタックスエラー（JOIN句、WHERE句の記述ミス等）"""
        elif state.get("last_query_result_count") == 0:
            error_context = f"""
**問題**: クエリは成功しましたが、結果が0行でした。

**改善の方向性**:
- フィルタ条件が厳しすぎる可能性があります
- WHERE句の条件を緩和するか、LIKEクエリを使用してください
- 元のユーザー意図: "{state.get('original_user_intent', '')}"
"""

        reflection_prompt = f"""
あなたはMLBデータ分析の専門家です。以下の問題を分析し、改善策を提案してください。

{error_context}

**重要**: ユーザーの元の質問「{state.get('original_user_intent', '')}」に答えるため、
適切なツールを選択して再実行してください。
"""
        prompt = [SystemMessage(content=reflection_prompt)] + state["messages"]

        try:
            response = self.model.invoke(prompt)
            return {
                "messages": [response],
                "retry_count": state.get("retry_count", 0) + 1
            }
        except Exception as e:
            raise AgentReasoningError("リフレクションノードでエラーが発生しました", original_error=e) from e

    def strategist_node(self, state):
        """Strategistノード: 戦略レポートを生成"""
        logger.info("Strategist node started", node="strategist")

        system_prompt = get_prompt("strategy_synthesizer")
        prompt = [SystemMessage(content=system_prompt)] + state["messages"] + [
            HumanMessage(content="それでは、戦略分析レポートを作成してください。必ず主語から始まる完全な文章で開始すること。")
        ]

        try:
            response = self.raw_model.invoke(prompt)
            logger.info(f"Strategist response length: {len(response.content)}")
            return {
                "final_answer": response.content,
                "messages": [response]
            }
        except Exception as e:
            raise AgentReasoningError("戦略レポート生成中にエラーが発生しました", original_error=e) from e

    # ===== 6. ユーティリティ =====
    def _sanitize(self, obj):
        """NaN / Infinity を None に変換（MatchupAgentと同一ロジック）"""
        if isinstance(obj, list):
            return [self._sanitize(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: self._sanitize(v) for k, v in obj.items()}
        elif isinstance(obj, float):
            if obj != obj or obj == float('inf') or obj == float('-inf'):
                return None
        return obj

    # ===== 7. エントリーポイント =====
    def run(self, query: str):
        """StrategyAgentを実行し、戦略レポートを返す"""
        initial_state = {
            "messages": [HumanMessage(content=query)],
            "raw_data_store": {},
            "next_step": "",
            "final_answer": "",
            # Reflection Loop
            "retry_count": 0,
            "max_retries": 2,
            "last_error": None,
            "last_query_result_count": -1,
            "original_user_intent": query,
            # 並列実行結果
            "parallel_results": {},
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
            "matchupData": None,
        }

        result = self.graph.invoke(initial_state)

        # APIレスポンスに必要なフィールドのみ返す（MatchupAgentと同一形式）
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
            "next_step": "END",
            # Strategy固有フィールド
            "isStrategyReport": True,
            "strategyData": result.get("parallel_results", {}),
        }
