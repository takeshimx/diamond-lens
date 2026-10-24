"""
evaluate_with_llm_judge.triage() のユニットテスト

ルールベース不合格ケースを Judge の判定で原因分類するロジックを、LLM を呼ばずに検証します。
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.app.services.llm_judge_service import JudgeVerdict, PASS_THRESHOLD
from backend.scripts.evaluate_with_llm_judge import (
    triage,
    TRIAGE_GOLDEN_FIX,
    TRIAGE_REAL_ERROR,
    TRIAGE_TOOL_SELECTION,
    TRIAGE_JUDGE_ERROR,
)

FAILED_WITH_ARGS = {"passed": False, "actual": {"query_type": "season_batting"}}


def _verdict(score: float) -> JudgeVerdict:
    return JudgeVerdict(
        case_id="GD-001",
        user_query="test",
        overall_score=score,
        passed=score >= PASS_THRESHOLD,
    )


def test_no_actual_is_tool_selection_error():
    """ツール選択自体の失敗は Judge の結果に関係なく tool_selection_error"""
    assert triage({"passed": False}, None) == TRIAGE_TOOL_SELECTION


def test_judge_pass_is_golden_fix_candidate():
    """Judge が意味的に正しいと判定 → golden 見直し候補"""
    assert triage(FAILED_WITH_ARGS, _verdict(4.5)) == TRIAGE_GOLDEN_FIX


def test_judge_fail_is_real_error():
    """Judge も不合格 → 本当の誤り"""
    assert triage(FAILED_WITH_ARGS, _verdict(2.0)) == TRIAGE_REAL_ERROR


def test_judge_call_failure_is_judge_error():
    """Judge 呼び出し失敗 (デフォルト score 0.0) は分類不能"""
    assert triage(FAILED_WITH_ARGS, _verdict(0.0)) == TRIAGE_JUDGE_ERROR
    assert triage(FAILED_WITH_ARGS, None) == TRIAGE_JUDGE_ERROR
