"""Trajectory Eval ハーネス。

LLM は実際に呼ぶ（非決定性を測るのが目的なのでモックしない）。
BigQuery は _execute_tool を差し替えて固定データを返す（データ変動を排除）。
→ 「LLM の揺れ」だけを分離して測定できる。
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List

from backend.app.services.chat_orchestrator import ChatOrchestrator


@dataclass
class ToolCall:
    name: str
    args: Dict[str, Any]


@dataclass
class RunTrace:
    tool_calls: List[ToolCall] = field(default_factory=list)
    answer: str = ""
    iterations: int = 0

def _make_recorder(trace: RunTrace, fixtures: Dict[str, Any]):
    """_execute_tool の差し替え関数を作る。呼び出しを記録し、固定データを返す。"""
    def _fake_execute_tool(self, name: str, args: Dict[str, Any]) -> Any:
        trace.tool_calls.append(ToolCall(name=name, args=dict(args)))
        # ツール名に対応する固定データ。無ければ空リスト（＝データ無し時の挙動も測れる）
        return fixtures.get(name, [])
    return _fake_execute_tool

async def run_once(case: dict, fixtures: Dict[str, Any]) -> RunTrace:
    trace = RunTrace()
    orch = ChatOrchestrator()
    orch._execute_tool = _make_recorder(trace, fixtures).__get__(orch, ChatOrchestrator)

    result = await orch.run(case["query"])
    # ChatOrchestrator.run() の返り値キーは "final_answer"。
    # なお synthesize_response=False (既定) では常に "" になるため、
    # must_not_mention による文章チェックは実質無効となる。
    trace.answer = str(result.get("final_answer", ""))
    trace.iterations = len(trace.tool_calls)
    return trace


@dataclass
class CaseResult:
    case_id: str
    passed: bool
    failures: List[str]


def judge(case: dict, trace: RunTrace) -> CaseResult:
    """期待（expect）と実測（trace）を突き合わせる。LLM は使わない決定的判定。"""
    exp = case["expect"]
    failures: List[str] = []

    called = {tc.name for tc in trace.tool_calls}
    for spec in exp.get("tool_calls", []):
        if spec["name"] not in called:
            failures.append(f"tool_missing:{spec['name']}")
            continue
        # 同名ツールのうち 1 つでも条件を満たせば合格とする
        matched = [tc for tc in trace.tool_calls if tc.name == spec["name"]]
        ok = any(
            all(tc.args.get(k) == v for k, v in spec.get("args_contains", {}).items())
            and all(k not in tc.args or tc.args[k] is None for k in spec.get("args_absent", []))
            for tc in matched
        )
        if not ok:
            failures.append(f"arg_mismatch:{spec['name']}:{[tc.args for tc in matched]}")

    if trace.iterations > exp.get("max_iterations", 6):
        failures.append(f"too_many_iterations:{trace.iterations}")
    for word in exp.get("must_not_mention", []):
        if word in trace.answer:
            failures.append(f"forbidden_phrase:{word}")

    return CaseResult(case_id=case["id"], passed=not failures, failures=failures)
