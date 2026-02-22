#!/usr/bin/env python3
"""
LLM Evaluation GATE for CI/CD Pipeline
ゴールデンデータセットを使って LLM のパース精度を評価します。
精度が閾値（PASS_THRESHOLD）を下回った場合、CI/CD パイプラインを停止します。
使用方法:
    python scripts/evaluate_llm_accuracy.py
終了コード:
    0: 精度が閾値以上（デプロイ可能）
    1: 精度が閾値未満（デプロイ停止）
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, List

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.app.services.ai_service import _parse_query_with_llm

# ============================================
# 設定
# ============================================
GOLDEN_DATASET_PATH = project_root / "backend" / "tests" / "golden_dataset.json"
PASS_THRESHOLD = 0.8  # 80% 以上で合格
CRITICAL_FIELDS = ["query_type"]  # これが間違っていたら即NG


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def load_golden_dataset() -> List[Dict[str, Any]]:
    """ゴールデンデータセットを読み込む"""
    with open(GOLDEN_DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["test_cases"]


def evaluate_single_case(test_case: Dict[str, Any]) -> Dict[str, Any]:
    """
    1つのテストケースを評価する
    Returns:
        {
            "id": "GD-001",
            "passed": True/False,
            "details": {...},
            "critical_failure": True/False
        }
    """
    case_id = test_case["id"]
    query = test_case["query"]
    season = test_case.get("season")
    expected = test_case["expected"]

    print(f"\n{Colors.BLUE}Testing [{case_id}]: {query}{Colors.RESET}")
    # LLM にパースさせる
    try:
        result = _parse_query_with_llm(query, season)
    except Exception as e:
        print(f"  {Colors.RED}[FAIL] LLM call failed: {e}{Colors.RESET}")
        return {
            "id": case_id,
            "passed": False,
            "critical_failure": True,
            "details": {"error": str(e)}
        }
    
    if result is None:
        print(f"  {Colors.RED}[FAIL] LLM returned None{Colors.RESET}")
        return {
            "id": case_id,
            "passed": False,
            "critical_failure": True,
            "details": {"error": "LLM returned None"}
        }
    
    # フィールドごとの比較
    field_results = {}
    all_passed = True
    critical_failure = False

    for field, expected_value in expected.items():
        if expected_value is None:
            # null が期待される場合、存在しないか null であることを確認
            actual = result.get(field)
            passed = actual is None or actual == ""
        elif field == "metrics_contains":
            # メトリクスは部分一致チェック（expected のメトリクスが actual に含まれているか）
            actual_metrics = result.get("metrics", [])
            # all()を使用して、expected_value のすべての要素が actual_metrics に含まれているかをチェック
            # all()は、すべての要素が True なら True、1つでも False なら False を返す
            passed = all(m in actual_metrics for m in expected_value)
            actual = actual_metrics
        else:
            actual = result.get(field)
            passed = actual == expected_value
        
        field_results[field] = {
            "expected": expected_value,
            "actual": actual,
            "passed": passed
        }

        if not passed:
            all_passed = False
            if field in CRITICAL_FIELDS:
                critical_failure = True
            print(f"  {Colors.RED}[FAIL] {field}: expected={expected_value}, actual={actual}{Colors.RESET}")
        else:
            print(f"  {Colors.GREEN}[OK]   {field}: {actual}{Colors.RESET}")
    
    return {
        "id": case_id,
        "passed": all_passed,
        "critical_failure": critical_failure,
        "details": field_results
    }


def main():
    """メイン処理"""
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}LLM Evaluation GATE - Starting...{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}")

    # ゴールデンデータセット読み込み
    test_cases = load_golden_dataset()
    print(f"\nLoaded {len(test_cases)} test cases from golden dataset")
    print(f"Pass threshold: {PASS_THRESHOLD * 100}%")

    # 全テストケースを評価
    results = []
    for test_case in test_cases:
        result = evaluate_single_case(test_case)
        results.append(result)
    
    # 結果集計
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    critical_failures = sum(1 for r in results if r.get("critical_failure", False))
    accuracy = passed / total if total > 0 else 0

    # 結果出力
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.BOLD}Evaluation Results{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}")
    print(f"\n  Total:    {total}")
    print(f"  Passed:   {Colors.GREEN}{passed}{Colors.RESET}")
    print(f"  Failed:   {Colors.RED}{failed}{Colors.RESET}")
    print(f"  Critical: {Colors.RED}{critical_failures}{Colors.RESET}")
    print(f"  Accuracy: {accuracy * 100:.1f}%")
    print(f"  Threshold: {PASS_THRESHOLD * 100:.1f}%")

    # 判定
    if accuracy >= PASS_THRESHOLD and critical_failures == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}[PASS] LLM Evaluation GATE PASSED ✅{Colors.RESET}")
        print(f"CI/CD Pipeline can proceed safely.\n")
        sys.exit(0)
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}[FAIL] LLM Evaluation GATE FAILED ❌{Colors.RESET}")
        if critical_failures > 0:
            print(f"  Reason: {critical_failures} critical field(s) failed (query_type)")
        else:
            print(f"  Reason: Accuracy {accuracy*100:.1f}% < Threshold {PASS_THRESHOLD*100:.1f}%")
        print(f"\nCI/CD Pipeline STOPPED.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
    