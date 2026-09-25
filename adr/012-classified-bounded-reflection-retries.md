# ADR-012: Make the reflection loop a bounded retry with error classification

> **TL;DR（日本語）**: 自己修復は「全部リトライ」でも「一切しない」でもなく、**エラーを回復可能／不能に分類し、回復可能なものだけを上限 2 回で再試行**する。SQL シンタックスミス・カラム名誤り・空結果は再計画へ送り、権限エラー・タイムアウト・スキーマ不在は**直しても無駄**なので即確定。上限があるため暴走とコスト青天井が構造的に起こらない。弱点は分類が**キーワードマッチ**であり、想定外の文言を取りこぼし得ること。明示的な Reflection ノードは `StrategyAgent` のみ現役。
>
> **TL;DR (English)**: Self-correction retries neither everything nor nothing: errors are **classified as recoverable or not, and only recoverable ones are retried, capped at 2 attempts**. SQL syntax errors, wrong column names and empty results go back for replanning; permission, timeout and missing-schema errors **cannot be fixed by retrying** and terminate immediately. The cap makes runaway loops and unbounded cost structurally impossible. The weakness is that classification is **keyword matching**, so unexpected error wording can slip through. Only `StrategyAgent` still runs an explicit reflection node.

- Status: Accepted
- Date: 2026-05-17 (originated in the legacy sub-agent era; inherited by StrategyAgent)
- Deciders: Project owner

## Context

When an LLM agent calls a tool (a BigQuery query), the result can be a **SQL error, an empty result (0 rows), or a schema mismatch**. How those are handled determines both the agent's capacity for self-correction and its risk of running away.

Naively looping "if it fails, have the LLM fix it and run again" without limit creates three problems.

- **Retrying errors that retrying cannot fix**: permission errors, timeouts, a missing dataset or a missing schema are not solved by adjusting arguments. Retrying only burns LLM calls, latency and money.
- **Infinite loops and runaway cost**: without a cap, the LLM can repeat the same mistake forever, or API cost can grow without bound.
- **But recoverable errors are worth catching**: SQL syntax errors, wrong column names and empty results often *are* fixable by revising the arguments. Those deserve a retry.

So the design needed is neither **retry everything** nor **retry nothing**, but **classify the nature of the error and retry only the recoverable ones, under a cap**.

## Decision

The reflection loop is implemented as a bounded loop with **(1) a retry/no-retry decision based on error classification and (2) a cap of 2 retries**. The decision is made by `should_reflect()` (live at [strategy_agent.py:116](../backend/app/services/agents/strategy_agent.py#L116)).

**Classification rules ([strategy_agent.py:116-143](../backend/app/services/agents/strategy_agent.py#L116-L143))**:

| Error kind | Example keywords | Decision |
|---|---|---|
| Cap reached | `retry_count >= max_retries` (=2) | No retry; finalize (go to strategist) |
| **Non-retryable** (retrying cannot help) | `permission` / `access denied` / `unauthorized` / `timeout` / `dataset` / `schema` / `not found` / `does not exist` | No retry; finalize |
| **Retryable** (fixable) | `syntax` / `unrecognized` / `invalid` / `column` / `table` | Go to the reflection node |
| **Retryable** (empty result) | `last_query_result_count == 0` | Go to the reflection node |
| Normal | No error, results present | Finalize |

The reflection node ([strategy_agent.py:249](../backend/app/services/agents/strategy_agent.py#L249)) weaves the error details (a possible column-name misunderstanding, a filter that may be too strict, and so on) together with the user's original intent into a prompt, has the LLM replan, increments `retry_count`, and returns to the planner.

This behavior is covered by unit tests ([test_reflection_loop.py](../backend/tests/test_reflection_loop.py)), which assert per case that permission/timeout/schema errors are not retried, that SQL syntax errors and empty results are, and that the loop stops at the cap.

## Alternatives Considered

- **An unbounded self-correction loop**: no cap means runaway loops, unbounded cost, and repetition of the same mistake. Rejected.
- **Never retry (a single pass, always final)**: this gives up on genuinely recoverable cases such as SQL syntax errors and transient empty results, lowering the answer success rate. Rejected.
- **Retry every error uniformly**: this retries permission, schema and timeout errors that retrying cannot fix, wasting latency and cost. Rejected.
- **Branch on exception types rather than strings**: stricter, but BigQuery and SDK errors frequently arrive as string messages, and keyword matching is simpler to implement and easier to cover. Keyword classification is used for now, with room to tighten it into type-based dispatch later.

## Consequences

**What got better**

- Recoverable errors (SQL mistakes, empty results) are corrected automatically, raising the answer success rate.
- Errors that retrying cannot fix drop straight through to finalization, containing wasted LLM calls, latency and cost.
- The cap of 2 guarantees the loop terminates, so runaway behavior and unbounded cost are structurally impossible.

**What got worse / new burdens**

- Because classification is **keyword matching**, an error phrased unexpectedly can be misclassified — more brittle than type-based dispatch.
- Errors that are recoverable but not fixed within two attempts are abandoned. The cap of 2 is a heuristic with no guarantee of being optimal.

**Implementation note (differences between paths)**

An explicit reflection loop is **live only in `StrategyAgent` (LangGraph)**. On the chat side, `ChatOrchestrator` has no reflection node; it relies on a system-prompt instruction ("on an empty result or error, revise the arguments and retry once or twice") plus the LLM's natural retries inside the function-calling loop (`MAX_TOOL_ITERATIONS=6`) ([[010-chat-orchestrator-replaces-langgraph]]).

Note also that the unit tests in [test_reflection_loop.py](../backend/tests/test_reflection_loop.py) **originate from the legacy sub-agents** (`BatterAgent` / `PitcherAgent` / `MatchupAgent`), where the branch targets are named `oracle` / `reflection`. The live `StrategyAgent.should_reflect()` applies the same classification logic but branches to `strategist` / `reflection` — only the node names differ, the rules are identical in spirit. The legacy sub-agents have not been physically deleted, so these tests still exist.

## Why This Matters

- **Bounding self-reflection**: it records, with its trade-offs, the production-minded self-correction decision to use "error classification plus a bound" rather than unbounded self-repair.

## References

- Implementation: [backend/app/services/agents/strategy_agent.py](../backend/app/services/agents/strategy_agent.py) (`should_reflect` / `reflection_node`)
- Tests: [backend/tests/test_reflection_loop.py](../backend/tests/test_reflection_loop.py)
- AI layer: [README_ai_architecture.md](../README_ai_architecture.md) §8 reflection loop
- Related ADRs: [[010-chat-orchestrator-replaces-langgraph]], [[011-retain-langgraph-for-strategy-agent]]
