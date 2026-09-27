# backend/tests/test_strategy_agent.py
"""
StrategyAgent ユニットテスト (Issue #64 / P0-1 対応後)

対象実装: backend/app/services/agents/strategy_agent.py

NFR:
  NFR-03: Parallel BigQuery < 6 sec（並列実行が逐次より速いことを検証）
  NFR-05: Error recovery rate > 95%（ツール失敗時に最終回答が返る）

方針:
  - 外部接続（BigQuery / Gemini）を一切行わない。model は Mock、
    ツールは agent.tools を差し替え、BQ ログ出力は patch で塞ぐ。
  - 実 BQ / 実 LLM を要する E2E は本ファイルでは扱わない。
"""

import time
from unittest.mock import Mock, patch

import pytest

# ファイル全体を CI から除外する。SupervisorAgent 経路が BigQuery へ実接続を
# 試みるため、単体テストとして成立していない。塞いでから除外を解く。
pytestmark = pytest.mark.slow


# ============================================================
# 共通ヘルパー
# ============================================================

def _make_strategy_agent(usage_callback=None):
    """StrategyAgent をモックモデルで生成する。

    __init__ は model.bind_tools() を呼び、LangGraph のコンパイルまで行う。
    Mock は bind_tools に反応できるよう自身を返すよう設定する。
    """
    from backend.app.services.agents.strategy_agent import StrategyAgent
    mock_model = Mock()
    mock_model.bind_tools = Mock(return_value=mock_model)
    return StrategyAgent(mock_model, usage_callback=usage_callback)


def _mock_tool(name, return_value=None, side_effect=None):
    """name 属性と invoke を持つツールの Mock を作る。

    Mock(name=...) は Mock 自身の名前を設定してしまい tool.name として
    機能しないため、必ず属性代入で設定する。
    """
    tool = Mock()
    tool.name = name
    tool.invoke = Mock(return_value=return_value, side_effect=side_effect)
    return tool


def _tool_call_message(*names):
    """指定ツール名の tool_calls を持つ AI メッセージの Mock を作る。"""
    message = Mock()
    message.tool_calls = [
        {"id": f"call_{i}", "name": name, "args": {"query": "test"}}
        for i, name in enumerate(names)
    ]
    return message


# parallel_executor_node は内部で _log_tool_execution を呼び、その中の
# get_llm_logger() が実 BigQuery クライアントを生成する。単体テストで
# 認証・ネットワークに触れないよう、このパッチを必ず適用する。
_PATCH_TOOL_LOG = "backend.app.services.agents.strategy_agent.StrategyAgent._log_tool_execution"


# ============================================================
# 1. should_reflect() — 再試行するかの分岐判定
# ============================================================

def test_should_reflect_max_retries_reached():
    """最大リトライ回数到達 → strategist へ直行"""
    agent = _make_strategy_agent()
    state = {"retry_count": 2, "max_retries": 2, "last_error": "SQL error", "last_query_result_count": -1}
    assert agent.should_reflect(state) == "strategist"


@pytest.mark.parametrize("last_error", [
    "access denied: permission error",
    "query timeout exceeded",
    "dataset not found: mlb_analytics",
])
def test_should_reflect_non_retryable_errors(last_error):
    """認証・タイムアウト・スキーマ系は再試行しても直らないため strategist へ"""
    agent = _make_strategy_agent()
    state = {"retry_count": 0, "max_retries": 2, "last_error": last_error, "last_query_result_count": -1}
    assert agent.should_reflect(state) == "strategist"


def test_should_reflect_sql_syntax_error():
    """SQL シンタックス・カラム名ミスは再試行で直るため reflection へ"""
    agent = _make_strategy_agent()
    state = {"retry_count": 0, "max_retries": 2,
             "last_error": "syntax error: unrecognized column 'pitcher_id'",
             "last_query_result_count": -1}
    assert agent.should_reflect(state) == "reflection"


def test_should_reflect_empty_result():
    """空結果（0行）は条件緩和の余地があるため reflection へ"""
    agent = _make_strategy_agent()
    state = {"retry_count": 0, "max_retries": 2, "last_error": None, "last_query_result_count": 0}
    assert agent.should_reflect(state) == "reflection"


def test_should_reflect_normal_flow():
    """エラーなし・結果ありの正常フロー → strategist"""
    agent = _make_strategy_agent()
    state = {"retry_count": 0, "max_retries": 2, "last_error": None, "last_query_result_count": 10}
    assert agent.should_reflect(state) == "strategist"


def test_should_reflect_defaults_when_state_keys_absent():
    """state にキーが無い場合もデフォルト値で strategist に落ちる"""
    agent = _make_strategy_agent()
    assert agent.should_reflect({}) == "strategist"


# ============================================================
# 2. should_execute() — planner 出力にツール呼び出しがあるか
# ============================================================

def test_should_execute_with_tool_calls():
    """tool_calls があれば parallel_executor へ"""
    agent = _make_strategy_agent()
    state = {"messages": [_tool_call_message("get_batter_stats_tool")]}
    assert agent.should_execute(state) == "execute"


def test_should_execute_without_tool_calls():
    """tool_calls が空なら strategist へ直行"""
    agent = _make_strategy_agent()
    message = Mock()
    message.tool_calls = []
    assert agent.should_execute({"messages": [message]}) == "end"


# ============================================================
# 3. parallel_executor_node() — 並列実行と例外の隔離
# ============================================================

def test_parallel_executor_tool_exception_is_isolated():
    """1ツールが例外を投げても他ツールの結果は保持される（NFR-05）"""
    agent = _make_strategy_agent()
    agent.tools = [
        _mock_tool("get_batter_stats_tool", return_value=[{"player": "Ohtani", "hr": 44}]),
        _mock_tool("mlb_matchup_history_tool", side_effect=Exception("対戦履歴の取得に失敗しました")),
    ]
    state = {"messages": [_tool_call_message("get_batter_stats_tool", "mlb_matchup_history_tool")]}

    with patch(_PATCH_TOOL_LOG):
        result = agent.parallel_executor_node(state)

    # 失敗ツールはエラー dict に変換される
    assert "error" in result["parallel_results"]["mlb_matchup_history_tool"]
    # 成功ツールの結果は失われない
    assert result["parallel_results"]["get_batter_stats_tool"] == [{"player": "Ohtani", "hr": 44}]


def test_parallel_executor_all_tools_fail():
    """全ツールが失敗した場合、last_error がセットされる"""
    agent = _make_strategy_agent()
    agent.tools = [_mock_tool("get_batter_stats_tool", side_effect=Exception("BQ connection failed"))]
    state = {"messages": [_tool_call_message("get_batter_stats_tool")]}

    with patch(_PATCH_TOOL_LOG):
        result = agent.parallel_executor_node(state)

    assert result["last_error"] is not None


def test_parallel_executor_unknown_tool_name():
    """planner が存在しないツール名を返してもクラッシュせずエラー dict になる"""
    agent = _make_strategy_agent()
    agent.tools = []
    state = {"messages": [_tool_call_message("nonexistent_tool")]}

    with patch(_PATCH_TOOL_LOG):
        result = agent.parallel_executor_node(state)

    assert "not found" in result["parallel_results"]["nonexistent_tool"]["error"]


def test_parallel_executor_counts_rows_from_list_result():
    """list を返すツールの件数が last_query_result_count に入る"""
    agent = _make_strategy_agent()
    agent.tools = [_mock_tool("get_batter_stats_tool", return_value=[{"a": 1}, {"a": 2}, {"a": 3}])]
    state = {"messages": [_tool_call_message("get_batter_stats_tool")]}

    with patch(_PATCH_TOOL_LOG):
        result = agent.parallel_executor_node(state)

    assert result["last_query_result_count"] == 3
    assert result["last_error"] is None


def test_parallel_executor_logs_tool_stats():
    """ツール別の成否・レイテンシが _log_tool_execution に渡される（P0-1 Step 5）"""
    agent = _make_strategy_agent()
    agent.tools = [
        _mock_tool("get_batter_stats_tool", return_value=[{"a": 1}]),
        _mock_tool("get_pitcher_stats_tool", side_effect=Exception("boom")),
    ]
    state = {"messages": [_tool_call_message("get_batter_stats_tool", "get_pitcher_stats_tool")]}

    with patch(_PATCH_TOOL_LOG) as mock_log:
        agent.parallel_executor_node(state)

    tool_stats = mock_log.call_args[0][0]
    by_name = {s["name"]: s for s in tool_stats}
    assert by_name["get_batter_stats_tool"]["ok"] is True
    assert by_name["get_pitcher_stats_tool"]["ok"] is False
    assert by_name["get_pitcher_stats_tool"]["error"] == "boom"
    assert "latency_ms" in by_name["get_batter_stats_tool"]


# ============================================================
# 4. aggregator_node() — 部分成功の許容
# ============================================================

def test_aggregator_partial_success():
    """一部ツール成功 → last_error は None（続行可能）"""
    agent = _make_strategy_agent()
    state = {"parallel_results": {
        "get_batter_stats_tool": [{"player": "Ohtani", "hr": 44}],
        "mlb_matchup_history_tool": {"error": "対戦履歴の取得に失敗しました"},
    }}
    assert agent.aggregator_node(state).get("last_error") is None


def test_aggregator_all_fail():
    """全ツール失敗 → last_error に全エラーが連結される"""
    agent = _make_strategy_agent()
    state = {"parallel_results": {
        "get_batter_stats_tool": {"error": "BQ error 1"},
        "get_pitcher_stats_tool": {"error": "BQ error 2"},
    }}
    last_error = agent.aggregator_node(state).get("last_error")
    assert "BQ error 1" in last_error
    assert "BQ error 2" in last_error


def test_aggregator_no_results_does_not_error():
    """parallel_results が空の場合はエラー扱いにしない（失敗ゼロのため）"""
    agent = _make_strategy_agent()
    assert agent.aggregator_node({"parallel_results": {}}).get("last_error") is None


# ============================================================
# 5. _sanitize() — NaN / Infinity の除去
# ============================================================

def test_sanitize_replaces_nan_and_infinity_with_none():
    """JSON 化できない float を None に落とす（ネストも再帰的に処理）"""
    agent = _make_strategy_agent()
    payload = {
        "ops": float("nan"),
        "era": float("inf"),
        "woba": float("-inf"),
        "avg": 0.304,
        "rows": [{"x": float("nan")}, {"x": 1.5}],
    }
    result = agent._sanitize(payload)
    assert result["ops"] is None
    assert result["era"] is None
    assert result["woba"] is None
    assert result["avg"] == 0.304
    assert result["rows"] == [{"x": None}, {"x": 1.5}]


# ============================================================
# 6. _mark_node() — Trace Viewer 向け callback 連携（P0-1）
# ============================================================

def test_mark_node_passes_node_and_iteration_to_callback():
    """callback にノード名と周回数（retry_count）が渡される"""
    callback = Mock()
    agent = _make_strategy_agent(usage_callback=callback)
    agent._mark_node("planner", {"retry_count": 2})
    callback.set_node.assert_called_once_with("planner", 2)


def test_mark_node_without_callback_is_noop():
    """callback 未注入時は何もしない（後方互換）"""
    agent = _make_strategy_agent()
    agent._mark_node("planner", {"retry_count": 0})  # 例外が出ないことのみ保証


def test_mark_node_suppresses_callback_failure():
    """トレース記録の失敗が本処理を止めない"""
    callback = Mock()
    callback.set_node = Mock(side_effect=Exception("trace backend down"))
    agent = _make_strategy_agent(usage_callback=callback)
    agent._mark_node("planner", {"retry_count": 0})  # 例外が外に漏れないこと


# ============================================================
# 7. run_structured() — 対戦戦略レポート用エントリーポイント
# ============================================================

def test_run_structured_builds_query_with_season():
    """打者名・投手名・シーズンから自然言語クエリを組み立て run() に委譲する"""
    agent = _make_strategy_agent()
    with patch.object(agent, "run", return_value={"final_answer": "ok"}) as mock_run:
        result = agent.run_structured("大谷翔平", "ゲリット・コール", season=2025)

    query = mock_run.call_args[0][0]
    assert "大谷翔平" in query
    assert "ゲリット・コール" in query
    assert "2025年" in query
    assert result == {"final_answer": "ok"}


def test_run_structured_omits_season_when_none():
    """season 未指定時は年の記述を含めない"""
    agent = _make_strategy_agent()
    with patch.object(agent, "run", return_value={}) as mock_run:
        agent.run_structured("大谷翔平", "ゲリット・コール")

    assert "年）" not in mock_run.call_args[0][0]


# ============================================================
# 8. パフォーマンス（NFR-03）
# ============================================================

@pytest.mark.slow
def test_parallel_execution_performance():
    """
    NFR-03: 4ツールを並列実行できていることを検証。
    各ツール 0.5 秒スリープ → 逐次なら 2 秒、並列なら 1.5 秒未満。
    実時間に依存するため CI からは除外する（slow マーカー）。
    """
    agent = _make_strategy_agent()

    def slow_invoke(args):
        time.sleep(0.5)
        return [{"data": "result"}]

    names = ["get_batter_stats_tool", "get_pitcher_stats_tool",
             "mlb_matchup_history_tool", "mlb_matchup_analytics_tool"]
    tools = []
    for name in names:
        tool = Mock()
        tool.name = name
        tool.invoke = slow_invoke
        tools.append(tool)
    agent.tools = tools

    state = {"messages": [_tool_call_message(*names)]}

    with patch(_PATCH_TOOL_LOG):
        start = time.time()
        agent.parallel_executor_node(state)
        elapsed = time.time() - start

    assert elapsed < 1.5, f"Parallel execution took {elapsed:.2f}s (expected < 1.5s)"


# ============================================================
# 9. SupervisorAgent ルーティング（旧 LangGraph 経路）
# ============================================================
# SupervisorAgent は現行のチャット経路（ChatOrchestrator）では使われない。
# CLAUDE.md 記載のとおり Phase 2-G の削除判断が保留中のため、テストも
# legacy マーカーを付けて残置する。SupervisorAgent を削除する際に本節も削除する。

@pytest.mark.legacy
def test_routing_strategy_query():
    """戦略的クエリを 'strategy' にルーティングする"""
    supervisor, _ = _make_supervisor_with_mock("strategy")
    assert supervisor.route_query("大谷 vs コール の総合分析して") == "strategy"


@pytest.mark.legacy
@pytest.mark.parametrize("expected", ["batter", "pitcher", "matchup", "stats"])
def test_routing_existing_agents_unaffected(expected):
    """既存ルーティング（batter/pitcher/matchup/stats）に影響なし"""
    supervisor, _ = _make_supervisor_with_mock(expected)
    assert supervisor.route_query(f"test query for {expected}") == expected


@pytest.mark.legacy
def test_routing_unknown_type_falls_back_to_stats():
    """LLM が未知の分類を返した場合は 'stats' にフォールバックする"""
    supervisor, _ = _make_supervisor_with_mock("unknown_agent_type")
    assert supervisor.route_query("何かしてください") == "stats"


def _make_supervisor_with_mock(response_content: str):
    """ChatGoogleGenerativeAI をモックして SupervisorAgent を生成する。

    SupervisorAgent.__init__ がモジュールレベルで解決した
    ChatGoogleGenerativeAI を掴むため、patch 下で reload してから生成する。
    """
    import importlib
    from backend.app.services.agents import supervisor_agent as sa_module

    mock_response = Mock()
    mock_response.content = response_content
    mock_instance = Mock()
    mock_instance.invoke.return_value = mock_response

    with patch("backend.app.services.agents.supervisor_agent.ChatGoogleGenerativeAI",
               return_value=mock_instance):
        importlib.reload(sa_module)
        supervisor = sa_module.SupervisorAgent()
    return supervisor, mock_instance
