# ADR-053: Agent Trace Viewer and failure labeling — riding on the existing log table

> **TL;DR（日本語）**: エージェントの実行経路を人が読む手段が無く、調査は BigQuery コンソールに SQL を手打ちする運用だった。**trace 専用テーブルを新設せず、既存 `llm_interaction_logs` に 3 列（`node` / `iteration` / `tool_calls`）を足して相乗り**させ、Trace Viewer で読めるようにした。肝は **LLM を呼ばないツール実行も 1 行として記録**すること（`model` を NULL にするためコストダッシュボードには一切現れない）。失敗ラベル（7 軸）は追記専用の別テーブルに持ち、ログ本体は書き換えない。**記録すべき失敗**: 当初は多段グラフの `StrategyAgent` を計装対象に選んだが、実ログを引いたら**トラフィックが 1 件も無かった**。「コードが存在すること」と「使われていること」は別であり、対象を決める前にトラフィックを測るべきだった。
>
> **TL;DR (English)**: There was no human-readable view of an agent's execution path — investigation meant hand-typing SQL in the BigQuery console. Rather than creating a dedicated trace table, **three columns (`node`, `iteration`, `tool_calls`) were added to the existing `llm_interaction_logs`** and surfaced in a Trace Viewer. The key move is **recording tool executions as rows even though they involve no LLM call** (with `model` left NULL, so they never pollute the cost dashboard). The seven failure labels live in a separate append-only table; the log itself is never rewritten. **A failure worth recording**: instrumentation initially targeted the multi-stage `StrategyAgent`, until real logs showed it receives **zero traffic**. Code existing and code being used are different things — measure traffic before choosing a target.

- Status: Accepted
- Date: 2026-09-03
- Deciders: Project owner

## Context

There was no way to view an agent's execution path in human-readable form.

`llm_interaction_logs` recorded one row per LLM call, and [ADR-032](032-snowflake-trace-id-structured-logging.md)'s `trace_id` already made it possible to group the rows of a single request. But nothing existed on the reading side, and real investigation meant hand-typing SQL in the BigQuery console.

As a result, these questions could not be answered.

- **Which tool did the agent choose, and with what arguments?**
- **Where did the time go** — the LLM's reasoning, or tool execution?
- **Did a tool fail?** (Even on failure the downstream LLM answers *something*, so the response alone does not tell you.)
- How to **label failed traces and accumulate those labels**.

### A misstep in choosing the target path (recorded deliberately)

Instrumentation was initially aimed at `StrategyAgent` (LangGraph: planner → parallel_executor → aggregator → reflection → strategist), on the grounds that a multi-stage graph with reflection-driven replanning would carry the richest trace information.

**That judgment was made from code structure alone, and it was wrong.** Aggregating real logs showed zero records for `POST /api/v1/strategy-report`, the only endpoint that invokes `StrategyAgent`. The frontend's strategy report screen calls eight individual endpoints in parallel, and the one among them that uses an LLM, `/strategy-report/tactics`, is an independent implementation that does not go through `StrategyAgent` either. The chat path had already moved to `ChatOrchestrator` in [ADR-010](010-chat-orchestrator-replaces-langgraph.md). `StrategyAgent` is therefore **unreachable from the current UI by any route**.

Code existing and code being used are different things. Before choosing an implementation target, measure whether that path carries real traffic. This failure is of the same kind as the "a traffic problem, not a design problem" note recorded in [ADR-021](021-hitl-golden-flywheel.md).

## Decision

**Instrument `ChatOrchestrator`, which is actually running, and let traces ride on the existing `llm_interaction_logs`.**

### 1. Add three columns to the existing table (create no new table)

| Column | Type | Meaning |
|---|---|---|
| `node` | STRING | The role within the agent: `oracle` / `executor` / `synthesizer`, etc. |
| `iteration` | INT64 | A loop counter specific to that path |
| `tool_calls` | STRING | JSON with tool name, arguments, success and duration |

All are NULLABLE. Existing rows stay NULL, and existing write paths work unmodified.

### 2. Record steps that call no LLM as rows too

Tool execution is not an LLM call, but **which tool failed and how many milliseconds it took is core trace information**. It is recorded as a row with `node = "executor"` and `model` left **NULL**.

Because `usage_stats_service` filters every query with `WHERE model IS NOT NULL` to count only LLM rows, these rows never appear in the LLM cost dashboard.

### 3. `node` is derived from the response content

`ChatOrchestrator` calls the LLM in exactly one place, and the role depends on whether what came back is a `function_call` or text.

```python
entry.node = "oracle" if function_calls else "synthesizer"
```

The SSE events already distinguish `state_update` as `oracle` and `token` as `synthesizer`, so the same vocabulary is used.

### 4. Labels live in a separate, append-only `trace_labels` table

The log itself is never rewritten. Relabeling is expressed as a new INSERT, and readers take the latest `labeled_at`. This preserves *when* the judgment changed.

There are seven label axes:

`correct` / `wrong_tool` / `wrong_params` / `right_answer_wrong_path` / `should_have_abstained` / `retrieval_miss` / `tool_error`

## Alternatives Considered

- **Instrument `StrategyAgent`**: the original plan, withdrawn once real traffic turned out to be zero. The instrumentation code itself is implemented and retained, but no traces accumulate because the UI never reaches it.
- **Rewire the UI to `StrategyAgent`**: the fundamental fix for richer traces, but it would require porting `/tactics`'s structured output (an array of `tier` / `title` / `detail` / `icon`) into the `strategist` node, and generation already measures 15–18 seconds — it would get slower still. Trading product experience for observability was not worth it.
- **Mark `node` across `/tactics`'s five stages**: it has real traffic and needs no UI change, but `/tactics` has fixed data retrieval and fixed prompts — the LLM does not choose the path. It is **the execution log of a deterministic pipeline, not an agent trace**, so a path-level label such as `right_answer_wrong_path` cannot apply in principle.
- **Create a dedicated trace table**: cleaner separation of concerns, but reading a trace would then require a JOIN against `llm_interaction_logs`, and there would be two tables to operate instead of one. The existing table already distinguishes LLM rows with `WHERE model IS NOT NULL`, so mixing in non-LLM rows was anticipated at design time — riding along was chosen.

## Consequences

### What got better

- A request's path is readable in the `TRACE` tab, with tool name, arguments, success, duration, tokens and cost laid out step by step.
- Bottlenecks become visible. In one real case the LLM's reasoning took 1.74 seconds against 3.30 seconds of tool execution — **the slow part was not the LLM**.
- The foundation for accumulating failure labels exists, giving [ADR-021](021-hitl-golden-flywheel.md)'s golden promotion flow something to connect to.

### What got worse / remaining debt

- **The `iteration` column does not mean the same thing across paths.** `ChatOrchestrator` puts the LLM call's sequence number in it; `StrategyAgent` puts reflection's `retry_count`. It cannot be aggregated across paths, so the list view recounts "LLM calls" with `COUNTIF(model IS NOT NULL)`. Column name and reality have diverged and will need cleaning up.
- **Truncation by `MAX_TOOL_ITERATIONS` is indistinguishable in a trace.** Hitting the cap means "could not finish investigating," not "chose to stop," and should be distinguishable from normal termination — but no flag is recorded today.
- **Summary rows written by endpoints carry a misleading timestamp.** `LLMLogEntry` stamps its timestamp at construction, so a row created right after the request arrives and written after processing completes ends up with "the earliest time and the final content." Mixing it into the step list breaks ordering, so rows with `node IS NULL` are separated out and shown as a `summary`.
- **The sample size is thin.** There were 7 chat traces in the last 30 days — not enough volume to accumulate labels and feed golden promotion. That is a traffic problem, not an implementation one.

## Why This Matters

- **Granular tracing** — step-level tracking by `trace_id` was implemented not only in the logging layer but all the way to a viewing surface.
- **Observability framework** — a path was built for detecting and classifying failures by hand.

Viewing traces, labeling failures and comparing runs are prerequisites for improving an agent continuously, because a failure that cannot be measured cannot be fixed.

## References

- [ADR-010: ChatOrchestrator replaces LangGraph sub-agents](010-chat-orchestrator-replaces-langgraph.md)
- [ADR-011: Retain LangGraph only for StrategyAgent](011-retain-langgraph-for-strategy-agent.md)
- [ADR-032: Snowflake trace_id + structured logging](032-snowflake-trace-id-structured-logging.md)
- ADR-051: Append-only LLM logging *(TBA — indexed in [README.md](README.md), write-up not yet authored)*
- `README_ai_architecture.md` §3 / §9.7
- Implementation: `backend/app/services/trace_query_service.py` / `trace_label_service.py` / `backend/app/api/endpoints/trace_endpoints.py` / `frontend/src/components/TraceViewer.jsx`
