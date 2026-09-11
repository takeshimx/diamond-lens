# backend/scripts/approve_to_golden.py
"""
trace_expectations (BigQuery) → golden_dataset.json への昇格スクリプト。

通常は Trace Viewer の「承認して PR 作成」から自動で走る (golden_pr_service)。
これはその **ローカル版** で、GitHub 連携を使わずに手元のファイルを直接
書き換えたいとき（オフライン確認、PAT 未設定時）に使う。

判定ロジックは golden_promotion_service に集約してある。ここで独自に
判定を書くと、UI 経由と CLI 経由で golden の中身が食い違う。

Usage:
    python scripts/approve_to_golden.py                # dry-run (既定)
    python scripts/approve_to_golden.py --apply        # 実際に書き込む
    python scripts/approve_to_golden.py --days 30      # 遡る日数
"""

import argparse
import json
import logging
import os
import sys

# scripts/ から直接実行されるため、リポジトリルートを import パスに載せる
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.services.golden_promotion_service import (  # noqa: E402
    build_promotion,
)
from backend.app.services.trace_expectation_service import (  # noqa: E402
    list_expectations,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

GOLDEN_FILE = "backend/tests/golden_dataset.json"


def promote(days: int, apply: bool) -> int:
    with open(GOLDEN_FILE, "r", encoding="utf-8") as f:
        golden = json.load(f)

    expectations = list_expectations(days=days)
    logger.info(f"fetched {len(expectations)} expectations from BigQuery (last {days}d)")

    updated, added, held = build_promotion(golden, expectations)

    for trace_id, reason in held.items():
        logger.warning(f"  - HELD {trace_id}: {reason}")
    for case in added:
        logger.info(
            f"  + {case['id']}  {case['query'][:40]!r}  -> "
            f"{json.dumps(case['expected'], ensure_ascii=False)}"
        )

    if not added:
        logger.info("no new expectations to promote")
        return 0

    if not apply:
        logger.info(
            f"[dry-run] would add {len(added)} case(s). re-run with --apply to write."
        )
        return len(added)

    with open(GOLDEN_FILE, "w", encoding="utf-8") as f:
        json.dump(updated, f, indent=4, ensure_ascii=False)
        f.write("\n")

    logger.info(
        f"wrote {len(added)} case(s) to {GOLDEN_FILE} "
        f"(total {len(updated['test_cases'])})"
    )
    logger.info(
        "NOTE: 追加したケースは元々システムが間違えた質問である。"
        "evaluate_llm_accuracy.py が落ちても異常ではない。"
    )
    return len(added)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=90, help="遡る日数 (既定 90)")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="実際に golden_dataset.json を書き換える。省略時は dry-run",
    )
    args = parser.parse_args()
    promote(days=args.days, apply=args.apply)


if __name__ == "__main__":
    main()
