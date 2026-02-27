# backend/scripts/approve_to_golden.py

import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PENDING_FILE = "backend/tests/pending_review.json"
GOLDEN_FILE = "backend/tests/golden_dataset.json"


def approve_reviewed_cases():
    """reviewed: true のケースを golden_dataset.json に移動する"""
    with open(PENDING_FILE, 'r', encoding='utf-8') as f:
        pending = json.load(f)

    with open(GOLDEN_FILE, 'r', encoding='utf-8') as f:
        golden = json.load(f)

    approved = []
    remaining = []

    for case in pending["pending_cases"]:
        if not case.get("reviewed"):
            remaining.append(case)
            continue

        # TODO が残っていないか検証
        expected = case["correct_expected"]
        if "TODO" in json.dumps(expected):
            logger.warning(f"Skipping {case['request_id']}: still has TODO in expected")
            remaining.append(case)
            continue

        # golden_dataset 用のフォーマットに変換
        new_id = f"GD-AUTO-{len(golden['test_cases']) + 1:03d}"
        golden_case = {
            "id": new_id,
            "category": expected.get("query_type", "unknown"),
            "query": case["query"],
            "season": None,
            "expected": expected
        }
        golden["test_cases"].append(golden_case)
        approved.append(case["request_id"])

    # 保存
    pending["pending_cases"] = remaining
    with open(PENDING_FILE, 'w', encoding='utf-8') as f:
        json.dump(pending, f, indent=4, ensure_ascii=False)

    with open(GOLDEN_FILE, 'w', encoding='utf-8') as f:
        json.dump(golden, f, indent=4, ensure_ascii=False)

    logger.info(f"Approved {len(approved)} cases to golden dataset")
    logger.info(f"Remaining pending: {len(remaining)}")


if __name__ == "__main__":
    approve_reviewed_cases()
