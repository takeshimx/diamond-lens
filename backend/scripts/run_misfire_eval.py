"""
用語集ツールの誤発火を測る。

誤発火 = 用語集を引くべきでない質問（選手の成績照会など）で
         glossary_search_tool が呼ばれてしまうこと。

これは検索ではなく「LLM がどのツールを選ぶか」の問題であり、
ベクトル検索の精度とは別レイヤー。そのため run_retrieval_eval.py とは分ける。

コスト:
  質問 1 件につき Gemini 1〜3 コール（tool_use ループの回数による）。
  成績照会ツールが実行されるため BigQuery のクエリも発生する。

使い方:
  python -m backend.scripts.run_misfire_eval            # should_not_fire のみ
  python -m backend.scripts.run_misfire_eval --all      # 全型（正発火も確認）
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

FIXTURES_PATH = Path("backend/tests/golden/retrieval_fixtures.json")
GLOSSARY_TOOL = "glossary_search_tool"


def run_one(query: str) -> list[str]:
    """1 問を ChatOrchestrator に流し、呼ばれたツール名を返す。

    _execute_tool を包んで名前を記録する。ツールの戻り値は素通しするため
    本来の挙動は変わらない。
    """
    from backend.app.services.chat_orchestrator import ChatOrchestrator

    orch = ChatOrchestrator(use_glossary_rag=True)
    called: list[str] = []
    original = orch._execute_tool

    def spy(name, args):
        called.append(name)
        return original(name, args)

    orch._execute_tool = spy
    try:
        # ChatOrchestrator.run は async。await しないとツールが一度も実行されない
        asyncio.run(orch.run(query))
    except Exception as e:
        print(f"    (run failed: {e})")
    return called


def main() -> None:
    parser = argparse.ArgumentParser(description="Glossary tool misfire evaluation")
    parser.add_argument("--all", action="store_true",
                        help="should_not_fire 以外も流し、正しく発火するかも確認する")
    args = parser.parse_args()

    data = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    fixtures = data["fixtures"]
    targets = fixtures if args.all else [
        f for f in fixtures if f["type"] == "should_not_fire"
    ]

    print(f"queries: {len(targets)} (billable: Gemini + BigQuery)")
    print()

    misfire = 0
    missed = 0
    for f in targets:
        called = run_one(f["query"])
        fired = GLOSSARY_TOOL in called
        should_fire = f["type"] != "should_not_fire"

        if fired and not should_fire:
            verdict, misfire = "NG (誤発火)", misfire + 1
        elif not fired and should_fire:
            verdict, missed = "NG (未発火)", missed + 1
        else:
            verdict = "OK"

        print(f"[{verdict}] {f['id']}  {f['query']}")
        print(f"          called: {called or '(none)'}")

    n = len(targets) or 1
    print()
    print(f"誤発火率: {misfire / n:.3f}  ({misfire}/{n})")
    if args.all:
        print(f"未発火率: {missed / n:.3f}  ({missed}/{n})")


if __name__ == "__main__":
    main()
