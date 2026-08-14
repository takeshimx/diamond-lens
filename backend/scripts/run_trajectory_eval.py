"""全ケースを 3 回ずつ実行し、pass^3（3回とも通った率）を出す。

単発の pass/fail は非決定的システムでは無意味。3 回中何回通ったかを見る。
"""
import asyncio, json, sys
from collections import Counter
from pathlib import Path

from backend.tests.eval.harness import run_once, judge

RUNS = 3
CASES = Path(__file__).parent.parent / "tests/golden/trajectories.jsonl"
FIXTURES = json.loads((Path(__file__).parent.parent / "tests/golden/fixtures.json").read_text("utf-8"))


async def main() -> int:
    cases = [json.loads(line) for line in CASES.read_text("utf-8").splitlines() if line.strip()]
    all_failures: Counter = Counter()
    p0_broken, rows = [], []

    for case in cases:
        passes = 0
        for _ in range(RUNS):
            trace = await run_once(case, FIXTURES)
            res = judge(case, trace)
            passes += res.passed
            all_failures.update(res.failures)
        rate = passes / RUNS
        rows.append((case["id"], rate))
        print(f"{case['id']:8} pass^{RUNS}={passes}/{RUNS}  {case['query'][:30]}")
        if "p0" in case.get("tags", []) and rate < 1.0:
            p0_broken.append(case["id"])

    print(f"\n全体: {sum(r for _, r in rows) / len(rows):.1%}")
    print("失敗内訳:", all_failures.most_common(5))
    if p0_broken:
        print(f"❌ P0 が落ちています: {p0_broken}")
        return 1          # ← 終了コード 1 でデプロイを止める
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
