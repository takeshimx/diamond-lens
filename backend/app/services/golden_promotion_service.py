"""
Golden Promotion Service (HITL フライホイール)

trace_expectations に溜まった期待値を golden_dataset.json の形へ変換し、
「今入れてよいもの」だけを選ぶ純粋ロジック。

ここには I/O を持たせない。golden の読み書きは呼び出し側が担う:
- API 経由 (`golden_pr_service`): GitHub の contents API で読み、PR を作る
- ローカル (`scripts/approve_to_golden.py`): ファイルを直接読み書きする

同じ判定を二重実装すると、UI 経由と CLI 経由で golden の中身が食い違う。
"""

import logging
from collections import Counter
from typing import Any, Dict, List, Tuple

from backend.app.config.query_maps import QUERY_TYPE_CONFIG

logger = logging.getLogger(__name__)

# tests/test_llm_evaluation.py::test_category_coverage が課す下限
MIN_CASES_PER_CATEGORY = 3


def to_golden_case(exp: Dict[str, Any], index: int) -> Dict[str, Any]:
    """期待値 1 件を golden_dataset のテストケース形式に変換する。

    expected に入れるキーは evaluate_llm_accuracy がそのまま比較対象にする。
    値が無いキーを入れると「None が期待値」として採点されてしまうため、
    指定されたものだけを入れる。
    """
    if exp.get("expected_no_tool"):
        return {
            "id": f"GD-AUTO-{index:03d}",
            "category": "abstain",
            "query": exp["user_query"],
            "season": None,
            "source_trace_id": exp["trace_id"],
            "expected_no_tool": True,
            "expected": {},
        }

    expected: Dict[str, Any] = {"query_type": exp["query_type"]}
    if exp.get("metrics"):
        expected["metrics_contains"] = exp["metrics"]
    if exp.get("split_type"):
        expected["split_type"] = exp["split_type"]
    if exp.get("player_name"):
        expected["name"] = exp["player_name"]
    if exp.get("season") is not None:
        expected["season"] = exp["season"]
    if exp.get("order_by"):
        expected["order_by"] = exp["order_by"]

    return {
        "id": f"GD-AUTO-{index:03d}",
        "category": exp["query_type"],
        # test_case 直下の season は既存ケースが全て null。expected 側で持つ。
        "season": None,
        "query": exp["user_query"],
        "source_trace_id": exp["trace_id"],
        "expected": expected,
    }


def _category_of(exp: Dict[str, Any]) -> str:
    return "abstain" if exp.get("expected_no_tool") else exp["query_type"]


def hold_unpromotable(
    pending: List[Dict[str, Any]], existing: List[Dict[str, Any]]
) -> Dict[str, str]:
    """昇格すると golden の構造テストを壊すものを選び、理由付きで返す。

    tests/test_llm_evaluation.py が課している規則:
      1. query_type は QUERY_TYPE_CONFIG に存在すること
         → 未実装の機能に対するテストを入れると、プロンプトを幾ら直しても
           緑にならない。CI が永久に赤くなる。
      2. 各カテゴリ最低 MIN_CASES_PER_CATEGORY 件
         → 新カテゴリを 1 件だけ入れると必ずこれに当たる。同じカテゴリが
           規定数まで溜まるのを待つ。

    弾いたものは BigQuery 側に残す。人の判断（正解はこれだ）は正しく、
    足りないのは受け入れ側の実装なので、記録を消す理由はない。
    """
    held: Dict[str, str] = {}

    # 規則 1: 実装のある query_type か
    survivors: List[Dict[str, Any]] = []
    for exp in pending:
        if exp.get("expected_no_tool"):
            survivors.append(exp)
            continue
        if exp["query_type"] not in QUERY_TYPE_CONFIG:
            held[exp["trace_id"]] = (
                f"query_type '{exp['query_type']}' は query_maps に未実装。"
                "実装してから昇格させること（今入れると CI が永久に赤くなる）"
            )
            continue
        survivors.append(exp)

    # 規則 2: カテゴリ件数。既存 + 今回分で規定数に届くか
    counts = Counter(c.get("category") for c in existing)
    counts.update(_category_of(e) for e in survivors)
    for exp in survivors:
        category = _category_of(exp)
        if counts[category] < MIN_CASES_PER_CATEGORY:
            held[exp["trace_id"]] = (
                f"カテゴリ '{category}' が {counts[category]} 件しかない"
                f"（最低 {MIN_CASES_PER_CATEGORY} 件必要）。"
                "同カテゴリが揃うまで保留する"
            )

    return held


def build_promotion(
    golden: Dict[str, Any], expectations: List[Dict[str, Any]]
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, str]]:
    """golden に期待値を取り込んだ結果を返す。

    Args:
        golden: 現在の golden_dataset.json の中身
        expectations: trace_expectations から読んだ期待値

    Returns:
        (更新後の golden, 追加されたケース, 保留した {trace_id: 理由})
        追加が 0 件なら golden は入力と同じ内容を返す。
    """
    cases: List[Dict[str, Any]] = list(golden.get("test_cases", []))
    # 既に昇格済みの trace は弾く。trace_expectations は追記のみのため、
    # 「処理済み」の状態は昇格先である golden 側に持たせる。
    promoted = {c.get("source_trace_id") for c in cases if c.get("source_trace_id")}

    pending = [e for e in expectations if e["trace_id"] not in promoted]
    held = hold_unpromotable(pending, cases)
    pending = [e for e in pending if e["trace_id"] not in held]

    added: List[Dict[str, Any]] = []
    for exp in pending:
        case = to_golden_case(exp, len(cases) + 1)
        cases.append(case)
        added.append(case)

    updated = {**golden, "test_cases": cases}
    return updated, added, held
