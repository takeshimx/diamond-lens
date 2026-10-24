#!/usr/bin/env python3
"""
LLM-as-a-Judge 評価パイプライン (不合格ケースの原因分類)

役割分担:
  - 合否判定 = ルールベース (evaluate_tool_call_accuracy.evaluate_single_case をそのまま使う。決定的)
  - 不合格の原因分類 = LLM Judge (非決定的なのでビルドは止めない。終了コードは常に 0)

ゴールデンデータセットの各ケースについて:
  1. 本番チャット経路 (ChatOrchestrator.plan_tool_call) でツールと引数を選ばせる
  2. ルールベースで採点する
  3. 不合格のケースだけを Judge にかけ、次のどれかに分類する
     - golden_fix_candidate: 表記違いだが意味は正しい → golden の期待値を見直す候補
     - real_error:           本当に誤り → プロンプト・コードの修正対象
     - tool_selection_error: ツールを選ばなかった / 選ぶべきでないのに選んだ (Judge にかけず real_error 扱い)
     - judge_error:          Judge 呼び出しが失敗し分類できなかった
Judge の呼び出しは不合格件数分のみ。

使用方法:
    python backend/scripts/evaluate_with_llm_judge.py
    python backend/scripts/evaluate_with_llm_judge.py --output results.json
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv(dotenv_path=project_root / ".env")

from backend.scripts.evaluate_tool_call_accuracy import evaluate_single_case, load_golden_dataset
from backend.app.services.llm_judge_service import LLMJudgeService, JudgeVerdict

# ============================================
# 設定
# ============================================
RESULTS_DIR = project_root / "backend" / "tests"

TRIAGE_GOLDEN_FIX = "golden_fix_candidate"
TRIAGE_REAL_ERROR = "real_error"
TRIAGE_TOOL_SELECTION = "tool_selection_error"
TRIAGE_JUDGE_ERROR = "judge_error"


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"


def triage(rule_result: Dict[str, Any], verdict: Optional[JudgeVerdict]) -> str:
    """ルールベース不合格ケースを、Judge の判定から原因別に分類する。

    - actual が無い = ツール選択自体の失敗。引数の表記違いは起こりえないので Judge に聞かない
    - Judge の overall_score が 0 = 呼び出し失敗 (正常応答は 1.0 以上にクランプされる)
    - Judge が合格 = 完全一致はしないが意味は正しい → golden 側の見直し候補
    """
    if rule_result.get("actual") is None:
        return TRIAGE_TOOL_SELECTION
    if verdict is None or verdict.overall_score == 0.0:
        return TRIAGE_JUDGE_ERROR
    if verdict.passed:
        return TRIAGE_GOLDEN_FIX
    return TRIAGE_REAL_ERROR


def run_evaluation(output_path: str = None):
    """メイン評価パイプライン"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}🧑‍⚖️ LLM-as-a-Judge Failure Triage{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")

    test_cases = load_golden_dataset()
    print(f"\n  📂 Loaded {len(test_cases)} test cases from golden dataset")

    judge = LLMJudgeService()

    results = []
    rule_based_pass = 0
    triage_counts: Dict[str, int] = {}
    failure_categories: Dict[str, int] = {}

    for case in test_cases:
        case_id = case["id"]
        query = case["query"]
        expected = case["expected"]

        # ---- Step 1-2: 本番経路でツール選択 + ルールベース採点 ----
        rule_result = evaluate_single_case(case)

        if rule_result["passed"]:
            rule_based_pass += 1
            results.append(
                {
                    "case_id": case_id,
                    "query": query,
                    "expected": expected,
                    "actual": rule_result.get("actual"),
                    "rule_based": rule_result,
                    "triage": None,
                    "judge_verdict": None,
                }
            )
            continue

        # ---- Step 3: 不合格ケースだけ Judge で原因分類 ----
        verdict = None
        if rule_result.get("actual") is not None:
            verdict = judge.evaluate_parse_result(
                case_id=case_id,
                user_query=query,
                expected=expected,
                actual=rule_result["actual"],
            )

        label = triage(rule_result, verdict)
        triage_counts[label] = triage_counts.get(label, 0) + 1

        label_color = Colors.YELLOW if label == TRIAGE_GOLDEN_FIX else Colors.RED
        print(f"  Triage: {label_color}{label}{Colors.RESET}")
        if verdict is not None:
            print(
                f"    {Colors.DIM}Judge {verdict.overall_score:.1f}/5.0 | "
                f"query_type: {verdict.query_type_accuracy}/5 | "
                f"metrics: {verdict.metrics_accuracy}/5 | "
                f"entity: {verdict.entity_resolution}/5 | "
                f"intent: {verdict.intent_understanding}/5{Colors.RESET}"
            )
            if verdict.reasoning:
                print(f"    {Colors.DIM}Reasoning: {verdict.reasoning}{Colors.RESET}")
            if verdict.failure_category and verdict.failure_category != "none":
                failure_categories[verdict.failure_category] = (
                    failure_categories.get(verdict.failure_category, 0) + 1
                )

        results.append(
            {
                "case_id": case_id,
                "query": query,
                "expected": expected,
                "actual": rule_result.get("actual"),
                "rule_based": rule_result,
                "triage": label,
                "judge_verdict": verdict.to_dict() if verdict else None,
            }
        )

    # ---- サマリー出力 ----
    total = len(test_cases)
    failed = total - rule_based_pass

    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}Results Summary{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    accuracy = rule_based_pass / total if total > 0 else 0
    print(f"  Rule-Based Accuracy: {rule_based_pass}/{total} ({accuracy * 100:.0f}%)")
    print(f"  Failed cases sent to triage: {failed}")

    if triage_counts:
        print(f"\n  {Colors.YELLOW}Failure Triage:{Colors.RESET}")
        for label in (TRIAGE_GOLDEN_FIX, TRIAGE_REAL_ERROR, TRIAGE_TOOL_SELECTION, TRIAGE_JUDGE_ERROR):
            if label in triage_counts:
                print(f"    {label:30s} {triage_counts[label]} case(s)")

    golden_fix_ids = [r["case_id"] for r in results if r["triage"] == TRIAGE_GOLDEN_FIX]
    if golden_fix_ids:
        print(f"\n  {Colors.YELLOW}Golden review candidates:{Colors.RESET} {', '.join(golden_fix_ids)}")

    if failure_categories:
        print(f"\n  {Colors.YELLOW}Judge Failure Categories:{Colors.RESET}")
        for category, count in sorted(
            failure_categories.items(), key=lambda x: x[1], reverse=True
        ):
            print(f"    {category:30s} {count} case(s)")

    # ---- 結果をJSONに保存 ----
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = RESULTS_DIR / f"llm_judge_results_{timestamp}.json"

    output_data = {
        "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_cases": total,
        "rule_based_accuracy": accuracy,
        "failed_cases": failed,
        "triage_counts": triage_counts,
        "failure_categories": failure_categories,
        "results": results,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n  📄 Results saved to: {output_path}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}\n")

    return output_data


def main():
    parser = argparse.ArgumentParser(description="LLM-as-a-Judge Failure Triage")
    parser.add_argument("--output", "-o", help="Output JSON file path", default=None)
    args = parser.parse_args()

    # 分類結果に関わらず終了コードは 0。合否ゲートは evaluate_tool_call_accuracy.py が担う。
    run_evaluation(output_path=args.output)


if __name__ == "__main__":
    main()
