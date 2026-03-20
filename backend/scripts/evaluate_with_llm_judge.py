#!/usr/bin/env python3
"""
LLM-as-a-Judge 評価パイプライン

ゴールデンデータセットに対して:
  1. LLMパーサーを実行 (既存の _parse_query_with_llm)
  2. ルールベース評価 (既存ロジック)
  3. LLM Judge 評価 (新規)
を並列実行し、比較レポートを出力します。

使用方法:
    python backend/scripts/evaluate_with_llm_judge.py
    python backend/scripts/evaluate_with_llm_judge.py --output results.json
"""

import json
import sys
import os
import argparse
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv(dotenv_path=project_root / ".env")

from backend.app.services.ai_service import _parse_query_with_llm as parse_batting
from backend.app.services.analytics.pitcher_services import _parse_query_with_llm as parse_pitching
from backend.app.services.llm_judge_service import LLMJudgeService, JudgeVerdict

# 投手系カテゴリの定義
PITCHING_CATEGORIES = ["season_pitching", "pitching_splits", "career_pitching"]


# ============================================
# 設定
# ============================================
GOLDEN_DATASET_PATH = project_root / "backend" / "tests" / "golden_dataset.json"
RESULTS_DIR = project_root / "backend" / "tests"

RULE_BASED_CRITICAL_FIELDS = ["query_type"]


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"


def load_golden_dataset() -> List[Dict[str, Any]]:
    """ゴールデンデータセットを読み込む"""
    with open(GOLDEN_DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["test_cases"]


def evaluate_rule_based(expected: Dict[str, Any], actual: Dict[str, Any]) -> Dict[str, Any]:
    """既存のルールベース評価ロジック (evaluate_llm_accuracy.py と同等)"""
    field_results = {}
    all_passed = True
    critical_failure = False

    for field_name, expected_value in expected.items():
        if expected_value is None:
            actual_val = actual.get(field_name)
            passed = actual_val is None or actual_val == ""
        elif field_name == "metrics_contains":
            actual_metrics = actual.get("metrics", [])
            passed = all(m in actual_metrics for m in expected_value)
            actual_val = actual_metrics
        else:
            actual_val = actual.get(field_name)
            passed = actual_val == expected_value

        field_results[field_name] = {
            "expected": expected_value,
            "actual": actual_val,
            "passed": passed,
        }

        if not passed:
            all_passed = False
            if field_name in RULE_BASED_CRITICAL_FIELDS:
                critical_failure = True

    return {
        "passed": all_passed,
        "critical_failure": critical_failure,
        "fields": field_results,
    }


def run_evaluation(output_path: str = None):
    """メイン評価パイプライン"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}🧑‍⚖️ LLM-as-a-Judge Evaluation Pipeline{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")

    # データセット読み込み
    test_cases = load_golden_dataset()
    print(f"\n  📂 Loaded {len(test_cases)} test cases from golden dataset")

    # Judge 初期化
    judge = LLMJudgeService()

    # 結果格納
    results = []
    rule_based_pass = 0
    judge_pass = 0
    total_judge_score = 0.0
    failure_categories = {}

    for case in test_cases:
        case_id = case["id"]
        query = case["query"]
        season = case.get("season")
        expected = case["expected"]

        print(f"\n{Colors.BLUE}[{case_id}] \"{query}\"{Colors.RESET}")

        # ---- Step 1: LLM パーサー実行（カテゴリに応じて切り替え） ----
        is_pitching = case.get("category") in PITCHING_CATEGORIES
        parser_label = "Pitching" if is_pitching else "Batting"
        try:
            if is_pitching:
                actual = parse_pitching(query, season)
            else:
                actual = parse_batting(query, season)
            if actual is None:
                actual = {}
                print(f"  {Colors.RED}⚠ Parser ({parser_label}) returned None{Colors.RESET}")
        except Exception as e:
            actual = {}
            print(f"  {Colors.RED}⚠ Parser error: {e}{Colors.RESET}")

        # ---- Step 2: ルールベース評価 ----
        rule_result = evaluate_rule_based(expected, actual)
        rule_passed = rule_result["passed"]
        if rule_passed:
            rule_based_pass += 1
            print(f"  Rule-Based: {Colors.GREEN}✅ PASS{Colors.RESET}")
        else:
            failed_fields = [
                f for f, v in rule_result["fields"].items() if not v["passed"]
            ]
            print(
                f"  Rule-Based: {Colors.RED}❌ FAIL ({', '.join(failed_fields)}){Colors.RESET}"
            )

        # ---- Step 3: LLM Judge 評価 ----
        verdict = judge.evaluate_parse_result(
            case_id=case_id,
            user_query=query,
            expected=expected,
            actual=actual,
        )

        if verdict.passed:
            judge_pass += 1
            score_color = Colors.GREEN
        else:
            score_color = Colors.RED

        total_judge_score += verdict.overall_score

        print(
            f"  LLM Judge:  {score_color}"
            f"{'✅ PASS' if verdict.passed else '❌ FAIL'} "
            f"({verdict.overall_score:.1f}/5.0){Colors.RESET}"
        )
        print(
            f"    {Colors.DIM}query_type: {verdict.query_type_accuracy}/5 | "
            f"metrics: {verdict.metrics_accuracy}/5 | "
            f"entity: {verdict.entity_resolution}/5 | "
            f"intent: {verdict.intent_understanding}/5{Colors.RESET}"
        )
        if verdict.reasoning:
            print(f"    {Colors.DIM}Reasoning: {verdict.reasoning}{Colors.RESET}")

        # 失敗カテゴリの集計
        if verdict.failure_category and verdict.failure_category != "none":
            failure_categories[verdict.failure_category] = (
                failure_categories.get(verdict.failure_category, 0) + 1
            )

        results.append(
            {
                "case_id": case_id,
                "query": query,
                "expected": expected,
                "actual": actual,
                "rule_based": rule_result,
                "judge_verdict": verdict.to_dict(),
            }
        )

    # ---- サマリー出力 ----
    total = len(test_cases)
    avg_score = total_judge_score / total if total > 0 else 0

    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}Results Summary{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    print(
        f"  Rule-Based Accuracy: {rule_based_pass}/{total} "
        f"({rule_based_pass / total * 100:.0f}%)"
    )
    print(
        f"  LLM Judge Accuracy:  {judge_pass}/{total} "
        f"({judge_pass / total * 100:.0f}%)"
    )
    print(f"  Average Judge Score: {avg_score:.1f}/5.0")

    if failure_categories:
        print(f"\n  {Colors.YELLOW}Failure Pattern Analysis:{Colors.RESET}")
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
        "rule_based_accuracy": rule_based_pass / total if total > 0 else 0,
        "judge_accuracy": judge_pass / total if total > 0 else 0,
        "average_judge_score": avg_score,
        "failure_categories": failure_categories,
        "results": results,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n  📄 Results saved to: {output_path}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}\n")

    return output_data


def main():
    parser = argparse.ArgumentParser(description="LLM-as-a-Judge Evaluation Pipeline")
    parser.add_argument("--output", "-o", help="Output JSON file path", default=None)
    args = parser.parse_args()

    run_evaluation(output_path=args.output)


if __name__ == "__main__":
    main()
