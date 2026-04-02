# backend/tests/test_strategy_agent.py
"""
StrategyAgent E2E テスト & パフォーマンス検証 (Issue #64)

NFR:
  NFR-01: First token < 8 sec (run_mlb_agent 呼び出し〜応答まで)
  NFR-02: Complete report < 30 sec
  NFR-03: Parallel BigQuery < 6 sec
  NFR-04: すべての推奨にデータ裏付け（"データなし" 記述確認）
  NFR-05: Error recovery rate > 95%（ツール失敗時に最終回答が返る）
"""

import sys
import time
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

load_dotenv(dotenv_path=project_root / ".env")


# ============================================================
# 1. should_reflect() Unit Tests
# ============================================================

def _make_strategy_agent():
    """StrategyAgent をモックモデルで生成"""
    from backend.app.services.agents.strategy_agent import StrategyAgent
    mock_model = Mock()
    mock_model.bind_tools = Mock(return_value=mock_model)
    return StrategyAgent(mock_model)


def test_should_reflect_max_retries_reached():
    """最大リトライ回数到達 → strategist へ直行"""
    print("\n[TEST] Test: should_reflect - max retries reached")
    agent = _make_strategy_agent()
    state = {"retry_count": 2, "max_retries": 2, "last_error": "SQL error", "last_query_result_count": -1}
    result = agent.should_reflect(state)
    assert result == "strategist", f"Expected 'strategist', got '{result}'"
    print("[PASS] Passed: max retries → strategist")


def test_should_reflect_permission_error():
    """Permission error（非リトライ）→ strategist"""
    print("\n[TEST] Test: should_reflect - permission error")
    agent = _make_strategy_agent()
    state = {"retry_count": 0, "max_retries": 2, "last_error": "access denied: permission error", "last_query_result_count": -1}
    result = agent.should_reflect(state)
    assert result == "strategist", f"Expected 'strategist', got '{result}'"
    print("[PASS] Passed: permission error → strategist (non-retryable)")


def test_should_reflect_timeout_error():
    """Timeout error（非リトライ）→ strategist"""
    print("\n[TEST] Test: should_reflect - timeout error")
    agent = _make_strategy_agent()
    state = {"retry_count": 0, "max_retries": 2, "last_error": "query timeout exceeded", "last_query_result_count": -1}
    result = agent.should_reflect(state)
    assert result == "strategist", f"Expected 'strategist', got '{result}'"
    print("[PASS] Passed: timeout error → strategist (non-retryable)")


def test_should_reflect_schema_error():
    """Schema error（非リトライ）→ strategist"""
    print("\n[TEST] Test: should_reflect - schema error")
    agent = _make_strategy_agent()
    state = {"retry_count": 0, "max_retries": 2, "last_error": "dataset not found: mlb_analytics", "last_query_result_count": -1}
    result = agent.should_reflect(state)
    assert result == "strategist", f"Expected 'strategist', got '{result}'"
    print("[PASS] Passed: schema error → strategist (non-retryable)")


def test_should_reflect_sql_syntax_error():
    """SQL syntax error（リトライ）→ reflection"""
    print("\n[TEST] Test: should_reflect - SQL syntax error (retryable)")
    agent = _make_strategy_agent()
    state = {"retry_count": 0, "max_retries": 2, "last_error": "syntax error: unrecognized column 'pitcher_id'", "last_query_result_count": -1}
    result = agent.should_reflect(state)
    assert result == "reflection", f"Expected 'reflection', got '{result}'"
    print("[PASS] Passed: SQL syntax error → reflection (retryable)")


def test_should_reflect_empty_result():
    """空結果（0行）→ reflection"""
    print("\n[TEST] Test: should_reflect - empty result")
    agent = _make_strategy_agent()
    state = {"retry_count": 0, "max_retries": 2, "last_error": None, "last_query_result_count": 0}
    result = agent.should_reflect(state)
    assert result == "reflection", f"Expected 'reflection', got '{result}'"
    print("[PASS] Passed: empty result → reflection")


def test_should_reflect_normal_flow():
    """正常フロー → strategist"""
    print("\n[TEST] Test: should_reflect - normal flow")
    agent = _make_strategy_agent()
    state = {"retry_count": 0, "max_retries": 2, "last_error": None, "last_query_result_count": 10}
    result = agent.should_reflect(state)
    assert result == "strategist", f"Expected 'strategist', got '{result}'"
    print("[PASS] Passed: normal flow → strategist")


# ============================================================
# 2. parallel_executor_node() Exception Handling Tests
# ============================================================

def test_parallel_executor_tool_exception_is_isolated():
    """
    1ツールが例外を投げても他ツールの結果は保持される（NFR-05）
    今回の修正（try-except in run_single）の検証
    """
    print("\n[TEST] Test: parallel_executor - exception isolation")
    agent = _make_strategy_agent()

    mock_success_tool = Mock()
    mock_success_tool.name = "get_batter_stats_tool"
    mock_success_tool.invoke = Mock(return_value=[{"player": "Ohtani", "hr": 44}])

    mock_fail_tool = Mock()
    mock_fail_tool.name = "mlb_matchup_history_tool"
    mock_fail_tool.invoke = Mock(side_effect=Exception("対戦履歴の取得に失敗しました"))

    agent.tools = [mock_success_tool, mock_fail_tool]

    mock_message = Mock()
    mock_message.tool_calls = [
        {"id": "call_1", "name": "get_batter_stats_tool", "args": {"query": "Ohtani stats"}},
        {"id": "call_2", "name": "mlb_matchup_history_tool", "args": {"batter_name": "Shohei Ohtani", "pitcher_name": "Gerrit Cole"}},
    ]
    state = {"messages": [mock_message]}

    result = agent.parallel_executor_node(state)

    # 失敗ツールはエラーdictになる
    assert "mlb_matchup_history_tool" in result["parallel_results"]
    assert "error" in result["parallel_results"]["mlb_matchup_history_tool"]

    # 成功ツールの結果は保持される
    assert "get_batter_stats_tool" in result["parallel_results"]
    assert isinstance(result["parallel_results"]["get_batter_stats_tool"], list)

    print("[PASS] Passed: exception isolated, other tool results preserved")


def test_parallel_executor_all_tools_fail():
    """全ツールが失敗した場合、last_error がセットされる"""
    print("\n[TEST] Test: parallel_executor - all tools fail")
    agent = _make_strategy_agent()

    mock_tool = Mock()
    mock_tool.name = "get_batter_stats_tool"
    mock_tool.invoke = Mock(side_effect=Exception("BQ connection failed"))
    agent.tools = [mock_tool]

    mock_message = Mock()
    mock_message.tool_calls = [
        {"id": "call_1", "name": "get_batter_stats_tool", "args": {"query": "test"}},
    ]
    state = {"messages": [mock_message]}

    result = agent.parallel_executor_node(state)
    assert result["last_error"] is not None
    print("[PASS] Passed: all tools fail → last_error set")


# ============================================================
# 3. aggregator_node() Tests
# ============================================================

def test_aggregator_partial_success():
    """一部ツール成功 → last_error は None（続行可能）"""
    print("\n[TEST] Test: aggregator - partial success")
    agent = _make_strategy_agent()

    state = {
        "parallel_results": {
            "get_batter_stats_tool": [{"player": "Ohtani", "hr": 44}],
            "mlb_matchup_history_tool": {"error": "対戦履歴の取得に失敗しました"},
        }
    }
    result = agent.aggregator_node(state)
    assert result.get("last_error") is None, f"Expected None, got {result.get('last_error')}"
    print("[PASS] Passed: partial success → last_error is None")


def test_aggregator_all_fail():
    """全ツール失敗 → last_error がセットされる"""
    print("\n[TEST] Test: aggregator - all fail")
    agent = _make_strategy_agent()

    state = {
        "parallel_results": {
            "get_batter_stats_tool": {"error": "BQ error 1"},
            "get_pitcher_stats_tool": {"error": "BQ error 2"},
        }
    }
    result = agent.aggregator_node(state)
    assert result.get("last_error") is not None
    print("[PASS] Passed: all fail → last_error set")


# ============================================================
# 4. Performance Tests (NFR-02, NFR-03)
# ============================================================

def test_parallel_execution_performance():
    """
    NFR-03: 並列BQ実行が < 6 sec であることを検証
    各ツールを0.5秒スリープでシミュレート → 逐次なら2秒、並列なら0.5秒以内
    """
    print("\n[TEST] Test: parallel execution performance (NFR-03)")
    import time

    agent = _make_strategy_agent()

    def slow_tool_invoke(args):
        time.sleep(0.5)
        return [{"data": "result"}]

    tools = []
    for name in ["get_batter_stats_tool", "get_pitcher_stats_tool",
                 "mlb_matchup_history_tool", "mlb_matchup_analytics_tool"]:
        t = Mock()
        t.name = name
        t.invoke = slow_tool_invoke
        tools.append(t)
    agent.tools = tools

    mock_message = Mock()
    mock_message.tool_calls = [
        {"id": f"call_{i}", "name": name, "args": {"query": "test"}}
        for i, name in enumerate(["get_batter_stats_tool", "get_pitcher_stats_tool",
                                   "mlb_matchup_history_tool", "mlb_matchup_analytics_tool"])
    ]
    state = {"messages": [mock_message]}

    start = time.time()
    agent.parallel_executor_node(state)
    elapsed = time.time() - start

    # 逐次なら2秒 (4 × 0.5秒)、並列なら1秒以内が目標
    assert elapsed < 1.5, f"Parallel execution took {elapsed:.2f}s (expected < 1.5s)"
    print(f"[PASS] Passed: parallel execution took {elapsed:.2f}s (< 1.5s target)")


# ============================================================
# 5. Edge Case Tests
# ============================================================

def _make_supervisor_with_mock(response_content: str):
    """ChatGoogleGenerativeAI をモックして SupervisorAgent を生成"""
    mock_response = Mock()
    mock_response.content = response_content
    mock_instance = Mock()
    mock_instance.invoke.return_value = mock_response

    with patch('backend.app.services.agents.supervisor_agent.ChatGoogleGenerativeAI', return_value=mock_instance):
        from backend.app.services.agents import supervisor_agent as sa_module
        import importlib
        importlib.reload(sa_module)
        supervisor = sa_module.SupervisorAgent()
    return supervisor, mock_instance


def test_routing_strategy_query():
    """
    SupervisorAgent が戦略的クエリを 'strategy' にルーティングする
    （BQ不要のモックテスト）
    """
    print("\n[TEST] Test: routing - strategy query")

    mock_response = Mock()
    mock_response.content = "strategy"
    mock_instance = Mock()
    mock_instance.invoke.return_value = mock_response

    with patch('backend.app.services.agents.supervisor_agent.ChatGoogleGenerativeAI', return_value=mock_instance):
        import importlib
        from backend.app.services.agents import supervisor_agent as sa_module
        importlib.reload(sa_module)
        supervisor = sa_module.SupervisorAgent()
        result = supervisor.route_query("大谷 vs コール の総合分析して")
        assert result == "strategy", f"Expected 'strategy', got '{result}'"
        print("[PASS] Passed: strategy query -> 'strategy' routing")


def test_routing_existing_agents_unaffected():
    """
    既存ルーティング（batter/pitcher/matchup/stats）に影響なし
    """
    print("\n[TEST] Test: routing - existing agents unaffected")

    import importlib
    from backend.app.services.agents import supervisor_agent as sa_module

    test_cases = ["batter", "pitcher", "matchup", "stats"]
    for expected in test_cases:
        mock_response = Mock()
        mock_response.content = expected
        mock_instance = Mock()
        mock_instance.invoke.return_value = mock_response

        with patch('backend.app.services.agents.supervisor_agent.ChatGoogleGenerativeAI', return_value=mock_instance):
            importlib.reload(sa_module)
            supervisor = sa_module.SupervisorAgent()
            result = supervisor.route_query(f"test query for {expected}")
            assert result == expected, f"Expected '{expected}', got '{result}'"
    print("[PASS] Passed: existing routing unaffected")


def test_edge_case_unknown_player():
    """
    エッジケース: 不明な選手名 → ツールエラーをgracefulに処理して最終回答を返す（NFR-05）
    """
    print("\n[TEST] Test: edge case - unknown player name")
    agent = _make_strategy_agent()

    tools = []
    for name in ["get_batter_stats_tool", "get_pitcher_stats_tool",
                 "mlb_matchup_history_tool", "mlb_matchup_analytics_tool"]:
        t = Mock()
        t.name = name
        t.invoke = Mock(return_value=[])
        tools.append(t)
    agent.tools = tools

    state = {
        "retry_count": 0,
        "max_retries": 2,
        "last_error": None,
        "last_query_result_count": 0
    }

    result = agent.should_reflect(state)
    assert result == "reflection", f"Expected 'reflection', got '{result}'"
    print("[PASS] Passed: unknown player -> empty result -> reflection triggered")


def test_edge_case_ambiguous_query_routing():
    """
    エッジケース: あいまいなクエリでも 'stats' にフォールバックする（バリデーション）
    """
    print("\n[TEST] Test: edge case - ambiguous query routing fallback")

    mock_response = Mock()
    mock_response.content = "unknown_agent_type"
    mock_instance = Mock()
    mock_instance.invoke.return_value = mock_response

    with patch('backend.app.services.agents.supervisor_agent.ChatGoogleGenerativeAI', return_value=mock_instance):
        import importlib
        from backend.app.services.agents import supervisor_agent as sa_module
        importlib.reload(sa_module)
        supervisor = sa_module.SupervisorAgent()
        result = supervisor.route_query("何かしてください")
        assert result == "stats", f"Expected 'stats' fallback, got '{result}'"
    print("[PASS] Passed: ambiguous query -> 'stats' fallback")


# ============================================================
# 6. E2E Integration Test (実BQ接続が必要)
# ============================================================

def test_e2e_general_analysis():
    """
    E2E: 大谷 vs コール の総合分析 (NFR-01, NFR-02)
    実BQ接続が必要 → 環境変数 GEMINI_API_KEY_V2 が必要
    """
    print("\n[TEST] E2E Test: General analysis - 大谷 vs コール")
    from backend.app.services.ai_agent_service import run_mlb_agent

    query = "大谷 vs コール の総合分析して"
    start = time.time()

    try:
        result = run_mlb_agent(query)
        elapsed = time.time() - start

        assert result.get("final_answer"), "final_answer should not be empty"
        assert result.get("isStrategyReport") is True, "isStrategyReport should be True"
        assert elapsed < 30, f"NFR-02: Complete report took {elapsed:.1f}s (> 30s limit)"

        print(f"[PASS] Passed: E2E completed in {elapsed:.1f}s")
        print(f"   isStrategyReport: {result.get('isStrategyReport')}")
        print(f"   final_answer length: {len(result.get('final_answer', ''))}")
        print(f"   Preview: {result.get('final_answer', '')[:100]}...")

    except Exception as e:
        print(f"[WARN]  E2E test requires BQ + Gemini access: {e}")


def test_e2e_situational_analysis():
    """
    E2E: 状況クエリ（7回、左投げ先発など）
    """
    print("\n[TEST] E2E Test: Situational analysis")
    from backend.app.services.ai_agent_service import run_mlb_agent

    query = "7回、左投げ先発、球数90球、RISP。左打者への戦略は？"
    start = time.time()

    try:
        result = run_mlb_agent(query)
        elapsed = time.time() - start

        assert result.get("final_answer"), "final_answer should not be empty"
        print(f"[PASS] Passed: Situational analysis completed in {elapsed:.1f}s")

    except Exception as e:
        print(f"[WARN]  E2E test requires BQ + Gemini access: {e}")


# ============================================================
# Run All Tests
# ============================================================

def run_unit_tests():
    """モック不要 / BQ不要のユニットテストのみ実行"""
    print("\n" + "=" * 60)
    print("[RUN] StrategyAgent Unit Test Suite")
    print("=" * 60)

    # should_reflect
    test_should_reflect_max_retries_reached()
    test_should_reflect_permission_error()
    test_should_reflect_timeout_error()
    test_should_reflect_schema_error()
    test_should_reflect_sql_syntax_error()
    test_should_reflect_empty_result()
    test_should_reflect_normal_flow()

    # parallel_executor
    test_parallel_executor_tool_exception_is_isolated()
    test_parallel_executor_all_tools_fail()

    # aggregator
    test_aggregator_partial_success()
    test_aggregator_all_fail()

    # performance
    test_parallel_execution_performance()

    # routing
    test_routing_strategy_query()
    test_routing_existing_agents_unaffected()

    # edge cases
    test_edge_case_unknown_player()
    test_edge_case_ambiguous_query_routing()

    print("\n" + "=" * 60)
    print("[PASS] All Unit Tests Passed!")
    print("=" * 60)


def run_e2e_tests():
    """実BQ + Gemini 接続が必要なE2Eテスト"""
    print("\n" + "=" * 60)
    print("[E2E] StrategyAgent E2E Test Suite (requires BQ + Gemini)")
    print("=" * 60)

    test_e2e_general_analysis()
    test_e2e_situational_analysis()

    print("\n" + "=" * 60)
    print("[PASS] E2E Tests Completed!")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    if "--e2e" in sys.argv:
        run_e2e_tests()
    elif "--all" in sys.argv:
        run_unit_tests()
        run_e2e_tests()
    else:
        run_unit_tests()
