# ADR-012: Reflection Loop はエラー分類 + 上限付きの境界付き再試行とする

- Status: Accepted
- Date: 2026-05-17（初出は旧 sub-agent 時代。StrategyAgent に継承）
- Deciders: プロジェクトオーナー

## Context（背景・課題）

LLM エージェントがツール（BigQuery クエリ）を呼んだ結果、**SQL エラー・空結果（0 行）・スキーマ不一致**などが起こります。これにどう対処するかで、エージェントの「自己修復力（self-correction）」と「暴走リスク」が決まります。

素朴に「失敗したら LLM に直させて再実行」を無制限に回すと、次の問題が生じます。

- **直しても無駄なエラーまで再試行する**: 権限エラー・タイムアウト・データセット不在・スキーマ不在は、引数を直しても解決しない。再試行は LLM 呼び出しとレイテンシ・コストを空費するだけ。
- **無限ループ・暴走**: 上限がないと、LLM が同じミスを繰り返して止まらない、あるいは API コストが青天井になる。
- **回復可能なエラーは見逃したくない**: 一方で、SQL シンタックスミス・カラム名誤り・空結果は、引数を見直せば直る「回復可能」なエラー。これは再試行する価値がある。

つまり「**全部リトライ**」でも「**一切リトライしない**」でもなく、**エラーの性質を分類し、回復可能なものだけを上限付きで再試行する**設計が要ります。

## Decision（決定）

Reflection Loop を、**(1) エラー分類による retry 可否判定 + (2) 再試行上限 2 回** の境界付きループとして実装しました。判定は `should_reflect()` が担います（現役は [strategy_agent.py:116](../../backend/app/services/agents/strategy_agent.py#L116)）。

**分類ルール（[strategy_agent.py:116-143](../../backend/app/services/agents/strategy_agent.py#L116-L143)）**:

| エラーの種類 | キーワード例 | 判定 |
|---|---|---|
| 上限到達 | `retry_count >= max_retries`(=2) | 再試行せず確定（strategist へ） |
| **非リトライ**（直しても無駄） | `permission` / `access denied` / `unauthorized` / `timeout` / `dataset` / `schema` / `not found` / `does not exist` | 再試行せず確定 |
| **リトライ**（直せば回る） | `syntax` / `unrecognized` / `invalid` / `column` / `table` | reflection ノードへ |
| **リトライ**（空結果） | `last_query_result_count == 0` | reflection ノードへ |
| 正常 | エラーなし・結果あり | 確定 |

reflection ノード（[strategy_agent.py:249](../../backend/app/services/agents/strategy_agent.py#L249)）は、エラー内容（カラム名誤認の可能性／フィルタが厳しすぎる可能性等）と元のユーザー意図をプロンプトに織り込んで LLM に再計画させ、`retry_count` を 1 つ増やして planner に戻します。

この振る舞いはユニットテストで検証されています（[test_reflection_loop.py](../../backend/tests/test_reflection_loop.py)：権限/タイムアウト/スキーマは非リトライ、SQL シンタックス/空結果はリトライ、上限到達で停止、を各ケースで assert）。

## Alternatives Considered（検討した代替案）

- **無制限の自己修正ループ**: 上限がなく、暴走・コスト青天井・同一ミスの反復のリスク。採用しない。
- **一切リトライしない（1 パスで確定）**: SQL シンタックスミスや一時的な空結果という回復可能なケースまで諦めることになり、回答成功率が下がる。不採用。
- **全エラーを一律リトライ**: 権限・スキーマ・タイムアウトという「直しても無駄」なエラーまで再試行し、レイテンシ・コストを空費する。不採用。
- **例外種別を型で握って分岐**: より厳密だが、BigQuery / SDK のエラーが文字列メッセージで返るケースが多く、キーワードマッチの方が実装が単純で網羅しやすい。現状はキーワード分類を採用（将来、型ベースに精緻化する余地あり）。

## Consequences（結果・トレードオフ）

**良くなったこと**

- 回復可能なエラー（SQL ミス・空結果）は自動で直り、回答成功率が上がる。
- 直しても無駄なエラーは即座に確定処理へ抜けるため、無駄な LLM 呼び出し・レイテンシ・コストを抑制。
- 上限 2 でループが必ず停止するため、暴走・コスト青天井が構造的に起こらない。

**悪くなったこと / 新たな負荷**

- 分類が**キーワードマッチ**のため、想定外の文言のエラーは分類を取りこぼす可能性がある（型ベースより脆い）。
- 「回復可能だが 2 回で直らない」エラーは諦める。上限 2 はヒューリスティックで、最適値の保証はない。

**実装上の注意（経路差）**

明示的な Reflection Loop は **`StrategyAgent`（LangGraph）でのみ現役**です。チャット側 `ChatOrchestrator` は Reflection ノードを持たず、system prompt の「空結果/エラー時は引数を見直して 1〜2 回再試行」指示と function calling ループ（`MAX_TOOL_ITERATIONS=6`）による LLM の自然な再試行に委ねます（[[010-chat-orchestrator-replaces-langgraph]]）。

なお、ユニットテスト [test_reflection_loop.py](../../backend/tests/test_reflection_loop.py) は **旧 sub-agent（`BatterAgent` / `PitcherAgent` / `MatchupAgent`）由来**で、分岐先ノード名が `oracle` / `reflection` です。現役の `StrategyAgent.should_reflect()` は同じ分類ロジックながら分岐先が `strategist` / `reflection` で、ノード名のみ異なります（分類ルール自体は同一思想）。旧 sub-agent の物理削除はユーザー判断で保留中のため、テストも現存します。

## JD Alignment（この募集要件との対応）

- **AG★（self-reflection / agentic workflows）**: JD が明示する `self-reflection` に直接対応。「無制限の自己修正」ではなく「エラー分類 + 境界付き」という、production を意識した self-correction の設計判断を trade-off で語れる。

## References

- 実装: [backend/app/services/agents/strategy_agent.py](../../backend/app/services/agents/strategy_agent.py)（`should_reflect` / `reflection_node`）
- テスト: [backend/tests/test_reflection_loop.py](../../backend/tests/test_reflection_loop.py)
- AI レイヤー: [README_ai_architecture.md](../../README_ai_architecture.md) §8 Reflection Loop
- 関連 ADR: [[010-chat-orchestrator-replaces-langgraph]], [[011-retain-langgraph-for-strategy-agent]]
