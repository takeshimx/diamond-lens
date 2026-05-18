# backend/tests/test_reflection_loop.py
"""
Reflection Loop (Self-Correction) 機能のテスト
- should_reflect() のロジック検証
- reflection_node() の動作確認
- executor_node() のエラー検出ロジック検証
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch
from langchain_core.messages import HumanMessage

# プロジェクトルートをパスに追加
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from dotenv import load_dotenv
from backend.app.services.agents.batter_agents import BatterAgent
from backend.app.services.agents.pitcher_agents import PitcherAgent
from backend.app.services.agents.matchup_agent import MatchupAgent

# .env を読み込む
load_dotenv(dotenv_path=project_root / ".env")


# ============================================================
# 1. should_reflect() Unit Tests
# ============================================================

def test_should_reflect_max_retries_reached():
    """
    最大リトライ回数に達している場合、reflectionしない（oracleに戻る）
    """
    print("\n🧪 Test: should_reflect - max retries reached")

    # Mock model
    mock_model = Mock()
    agent = BatterAgent(mock_model)

    state = {
        "retry_count": 2,
        "max_retries": 2,
        "last_error": "Some SQL error",
        "last_query_result_count": -1
    }

    result = agent.should_reflect(state)
    assert result == "oracle", f"Expected 'oracle', got '{result}'"
    print("✅ Passed: Max retries reached → oracle")


def test_should_reflect_permission_error():
    """
    Permission errorはリトライしない（oracle に戻る）
    """
    print("\n🧪 Test: should_reflect - permission error (non-retryable)")

    mock_model = Mock()
    agent = PitcherAgent(mock_model)

    state = {
        "retry_count": 0,
        "max_retries": 2,
        "last_error": "Access denied: permission error",
        "last_query_result_count": -1
    }

    result = agent.should_reflect(state)
    assert result == "oracle", f"Expected 'oracle', got '{result}'"
    print("✅ Passed: Permission error → oracle (non-retryable)")


def test_should_reflect_timeout_error():
    """
    Timeout errorはリトライしない（oracle に戻る）
    """
    print("\n🧪 Test: should_reflect - timeout error (non-retryable)")

    mock_model = Mock()
    agent = MatchupAgent(mock_model)

    state = {
        "retry_count": 0,
        "max_retries": 2,
        "last_error": "Query timeout exceeded",
        "last_query_result_count": -1
    }

    result = agent.should_reflect(state)
    assert result == "oracle", f"Expected 'oracle', got '{result}'"
    print("✅ Passed: Timeout error → oracle (non-retryable)")


def test_should_reflect_schema_error():
    """
    Schema/Dataset errorはリトライしない（oracle に戻る）
    """
    print("\n🧪 Test: should_reflect - schema error (non-retryable)")

    mock_model = Mock()
    agent = BatterAgent(mock_model)

    state = {
        "retry_count": 0,
        "max_retries": 2,
        "last_error": "Dataset not found: baseball.batting_stats",
        "last_query_result_count": -1
    }

    result = agent.should_reflect(state)
    assert result == "oracle", f"Expected 'oracle', got '{result}'"
    print("✅ Passed: Schema error → oracle (non-retryable)")


def test_should_reflect_sql_syntax_error():
    """
    SQL syntax errorはリトライする（reflection へ）
    """
    print("\n🧪 Test: should_reflect - SQL syntax error (retryable)")

    mock_model = Mock()
    agent = PitcherAgent(mock_model)

    state = {
        "retry_count": 0,
        "max_retries": 2,
        "last_error": "Syntax error: unrecognized column name 'player_name'",
        "last_query_result_count": -1
    }

    result = agent.should_reflect(state)
    assert result == "reflection", f"Expected 'reflection', got '{result}'"
    print("✅ Passed: SQL syntax error → reflection (retryable)")


def test_should_reflect_empty_result():
    """
    空結果（0行）の場合、reflectionへ
    """
    print("\n🧪 Test: should_reflect - empty result (retryable)")

    mock_model = Mock()
    agent = MatchupAgent(mock_model)

    state = {
        "retry_count": 0,
        "max_retries": 2,
        "last_error": None,
        "last_query_result_count": 0
    }

    result = agent.should_reflect(state)
    assert result == "reflection", f"Expected 'reflection', got '{result}'"
    print("✅ Passed: Empty result → reflection (retryable)")


def test_should_reflect_normal_flow():
    """
    正常フロー（エラーなし、結果あり）の場合、oracleへ
    """
    print("\n🧪 Test: should_reflect - normal flow")

    mock_model = Mock()
    agent = BatterAgent(mock_model)

    state = {
        "retry_count": 0,
        "max_retries": 2,
        "last_error": None,
        "last_query_result_count": 5
    }

    result = agent.should_reflect(state)
    assert result == "oracle", f"Expected 'oracle', got '{result}'"
    print("✅ Passed: Normal flow → oracle")


# ============================================================
# 2. executor_node() Empty Result Detection Test
# ============================================================

def test_executor_empty_result_detection_list():
    """
    executor_node: 空結果（list形式）の検出
    """
    print("\n🧪 Test: executor_node - empty result detection (list)")

    mock_model = Mock()
    agent = BatterAgent(mock_model)

    # Mock tool call
    mock_tool_call = {
        "id": "test_call_123",
        "name": "get_batter_stats_tool",
        "args": {"query": "test query", "season": 2024}
    }

    mock_message = Mock()
    mock_message.tool_calls = [mock_tool_call]

    state = {
        "messages": [mock_message]
    }

    # Mock tool result (empty list)
    with patch("backend.app.services.tools.batter_stats_tool.get_batter_stats_tool") as mock_tool:
        mock_tool.invoke.return_value = []

        result = agent.executor_node(state)

        assert result["last_query_result_count"] == 0, \
            f"Expected result_count=0, got {result['last_query_result_count']}"
        print("✅ Passed: Empty list detected correctly")


def test_executor_empty_result_detection_dict():
    """
    executor_node: 空結果（dict形式、answer field）の検出
    """
    print("\n🧪 Test: executor_node - empty result detection (dict with answer)")

    mock_model = Mock()
    agent = PitcherAgent(mock_model)

    # Mock tool call
    mock_tool_call = {
        "id": "test_call_456",
        "name": "get_pitcher_stats_tool",
        "args": {"query": "test query", "season": 2024}
    }

    mock_message = Mock()
    mock_message.tool_calls = [mock_tool_call]

    state = {
        "messages": [mock_message]
    }

    # Mock tool result (dict with "データが見つかりませんでした" message)
    with patch("backend.app.services.tools.pitcher_stats_tool.get_pitcher_stats_tool") as mock_tool:
        mock_tool.invoke.return_value = {
            "answer": "指定された条件に一致するデータが見つかりませんでした。",
            "isTable": False
        }

        result = agent.executor_node(state)

        assert result["last_query_result_count"] == 0, \
            f"Expected result_count=0, got {result['last_query_result_count']}"
        print("✅ Passed: Empty result message detected correctly")


def test_executor_error_detection():
    """
    executor_node: BigQuery errorの検出
    """
    print("\n🧪 Test: executor_node - error detection")

    mock_model = Mock()
    agent = MatchupAgent(mock_model)

    # Mock tool call
    mock_tool_call = {
        "id": "test_call_789",
        "name": "get_matchup_stats_tool",
        "args": {"pitcher_name": "test", "batter_name": "test", "season": 2024}
    }

    mock_message = Mock()
    mock_message.tool_calls = [mock_tool_call]

    state = {
        "messages": [mock_message]
    }

    # Mock tool result (error dict)
    # MatchupAgentはツールを動的に選択するため、直接モックする
    mock_tool = Mock()
    mock_tool.name = "get_matchup_stats_tool"
    mock_tool.invoke.return_value = {
        "error": "Unrecognized column name: invalid_column"
    }
    agent.tools = [mock_tool]

    result = agent.executor_node(state)

    assert result["last_error"] == "Unrecognized column name: invalid_column", \
        f"Expected error message, got {result['last_error']}"
    print("✅ Passed: Error detected correctly")


# ============================================================
# 3. Integration Test (Workflow)
# ============================================================

def test_integration_reflection_triggered_on_empty_result():
    """
    統合テスト: 空結果時にReflection Loopが発動するか
    ※ 実際のBigQueryを使わず、モックで動作確認
    """
    print("\n🧪 Integration Test: Reflection triggered on empty result")

    mock_model = Mock()
    agent = BatterAgent(mock_model)

    # Scenario:
    # 1. oracle → executor (empty result) → reflection → oracle (retry) → executor (success) → synthesizer

    # Mock oracle response (tool call)
    mock_oracle_response = Mock()
    mock_oracle_response.tool_calls = [{
        "id": "call_1",
        "name": "get_batter_stats_tool",
        "args": {"query": "test", "season": 2024}
    }]

    # Mock reflection response (retry with tool call)
    mock_reflection_response = Mock()
    mock_reflection_response.tool_calls = [{
        "id": "call_2",
        "name": "get_batter_stats_tool",
        "args": {"query": "test corrected", "season": 2024}
    }]

    # Mock synthesizer response
    mock_synthesizer_response = Mock()
    mock_synthesizer_response.content = "Final answer after reflection"
    mock_synthesizer_response.tool_calls = []

    agent.model.invoke.side_effect = [
        mock_oracle_response,       # First oracle call
        mock_reflection_response,   # Reflection call
        mock_synthesizer_response   # Second oracle call (no tool calls → synthesizer)
    ]
    agent.raw_model.invoke.return_value = mock_synthesizer_response

    # Mock tool results
    with patch("backend.app.services.tools.batter_stats_tool.get_batter_stats_tool") as mock_tool:
        mock_tool.invoke.side_effect = [
            {"answer": "データが見つかりませんでした"},  # Empty result (triggers reflection)
            [{"player": "Test Player", "hr": 30}]       # Success after reflection
        ]

        # Run agent
        state = {
            "messages": [HumanMessage(content="test query")],
            "raw_data_store": {},
            "next_step": "",
            "final_answer": "",
            "retry_count": 0,
            "max_retries": 2,
            "last_error": None,
            "last_query_result_count": -1,
            "original_user_intent": "test query",
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

        # Note: Full workflow test requires proper graph execution
        # This is a simplified mock test

        # Test should_reflect logic
        state_after_empty = {
            "retry_count": 0,
            "max_retries": 2,
            "last_error": None,
            "last_query_result_count": 0
        }

        decision = agent.should_reflect(state_after_empty)
        assert decision == "reflection", "Should trigger reflection on empty result"

        print("✅ Passed: Reflection triggered correctly on empty result")


# ============================================================
# Run All Tests
# ============================================================

def run_all_tests():
    """全テストを実行"""
    print("\n" + "="*60)
    print("🚀 Reflection Loop Test Suite")
    print("="*60)

    # Unit Tests
    test_should_reflect_max_retries_reached()
    test_should_reflect_permission_error()
    test_should_reflect_timeout_error()
    test_should_reflect_schema_error()
    test_should_reflect_sql_syntax_error()
    test_should_reflect_empty_result()
    test_should_reflect_normal_flow()

    # Executor Tests
    test_executor_empty_result_detection_list()
    test_executor_empty_result_detection_dict()
    test_executor_error_detection()

    # Integration Test
    test_integration_reflection_triggered_on_empty_result()

    print("\n" + "="*60)
    print("✅ All Reflection Loop Tests Passed!")
    print("="*60)


if __name__ == "__main__":
    run_all_tests()
