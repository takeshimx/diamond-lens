"""全ケースを 3 回ずつ実行し、pass^3（3 回とも通った率）を出す。

単発の pass/fail は非決定的システムでは無意味。3 回中何回通ったかを見る。
P0 が 1 件でも 3/3 でなければ終了コード 1 を返し、デプロイゲートとして機能する。
"""
import asyncio
import json
import logging
import sys
from collections import Counter
from pathlib import Path

from backend.tests.eval.harness import run_once, judge

# ChatOrchestrator の INFO ログで結果が埋もれるため、警告以上のみ表示する
logging.getLogger().setLevel(logging.WARNING)
logging.getLogger("token-budget").setLevel(logging.WARNING)

RUNS = 3
GOLDEN_DIR = Path(__file__).resolve().parent.parent / "tests/golden"
CASES_PATH = GOLDEN_DIR / "trajectories.jsonl"
FIXTURES = json.loads((GOLDEN_DIR / "fixtures.json").read_text("utf-8"))


async def main() -> int:
    cases = [
        json.loads(line)
        for line in CASES_PATH.read_text("utf-8").splitlines()
        if line.strip()
    ]

    # 引数でケースを絞り込む。ID (TJ-001) または tag (p0, matchup 等) を指定できる。
    # 例: python scripts/run_trajectory_eval.py TJ-001
    #     python scripts/run_trajectory_eval.py p0
    # 絞り込み時は P0 が落ちても終了コード 0 を返す (ゲート判定は全件実行時のみ)。
    selectors = sys.argv[1:]
    partial = bool(selectors)
    if partial:
        cases = [
            c for c in cases
            if c["id"] in selectors or set(selectors) & set(c.get("tags", []))
        ]
        if not cases:
            print(f"該当ケースなし: {selectors}")
            return 1
        print(f"絞り込み実行: {[c['id'] for c in cases]}\n")
    failure_counter: Counter = Counter()
    p0_broken: list[str] = []
    rates: dict[str, float] = {}

    for case in cases:
        passes = 0
        for _ in range(RUNS):
            try:
                trace = await run_once(case, FIXTURES)
            except Exception as e:
                # 1 件の異常で全体を止めない。API エラー等はここで 1 行に潰す。
                failure_counter[f"exception:{type(e).__name__}"] += 1
                print(f"  {case['id']} 実行失敗: {type(e).__name__}: {str(e)[:100]}")
                continue
            result = judge(case, trace)
            passes += result.passed
            failure_counter.update(result.failures)

        rate = passes / RUNS
        rates[case["id"]] = rate
        mark = "OK  " if rate == 1.0 else ("WARN" if rate > 0 else "FAIL")
        tier = "P0" if "p0" in case.get("tags", []) else "P1"
        print(f"{mark} {tier} {case['id']}  {passes}/{RUNS}  {case['query'][:34]}")
        if tier == "P0" and rate < 1.0:
            p0_broken.append(case["id"])

    p0 = [c for c in cases if "p0" in c.get("tags", [])]
    p1 = [c for c in cases if "p0" not in c.get("tags", [])]
    print("\n" + "=" * 60)
    if p0:
        print(f"P0 ({len(p0)}件)  pass^{RUNS}: {sum(rates[c['id']] == 1.0 for c in p0) / len(p0):.1%}")
    if p1:
        print(f"P1 ({len(p1)}件)  平均pass率: {sum(rates[c['id']] for c in p1) / len(p1):.1%}")
    print(f"全体 ({len(cases)}件) 平均pass率: {sum(rates.values()) / len(rates):.1%}")

    if failure_counter:
        print("\n失敗内訳 (多い順):")
        for label, count in failure_counter.most_common(8):
            print(f"  {count:3}  {label[:110]}")

    if p0_broken:
        print(f"\nP0 が落ちています: {p0_broken}")
        # 絞り込み実行はデプロイ判定に使わないため、終了コードは 0 のままにする
        return 0 if partial else 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
