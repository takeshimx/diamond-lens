# ADR-032: Snowflake trace_id + structured JSON logging (ContextVar propagation)

> **TL;DR（日本語）**: 1 リクエストはエンドポイント → Orchestrator → 複数 LLM 呼び出し → ツール → BQ と多層を横断するため、素の print ログでは**どの行がどのリクエストのものか相関できない**。**Snowflake 形式（時刻順ソート可能な 64bit ID）の `trace_id` をリクエスト単位で発番し、ContextVar で全層に自動伝搬**させる。全関数シグネチャに引数を足す侵襲的な手渡しを避けつつ、LLM ログ・shadow 比較・SSE ペイロードまで串刺しできる。UUIDv4 ではなく Snowflake を選んだのは **ID 自体が時系列順**で範囲検索・並べ替えに有利なため。注意点は **ContextVar がスレッド境界を越えないこと**（非同期ログ書き込み・並列ツール実行では明示セットが必要）。
>
> **TL;DR (English)**: A single request crosses endpoint → orchestrator → several LLM calls → tools → BigQuery, so plain print logging **cannot tell which line belongs to which request**. A **Snowflake-style `trace_id` (a time-sortable 64-bit ID) is minted per request and propagated automatically through every layer via `ContextVar`**, avoiding the invasive alternative of threading an argument through every signature, and reaching LLM logs, shadow comparisons and SSE payloads alike. Snowflake was chosen over UUIDv4 because the **ID itself sorts chronologically**, which helps range queries and ordering. The caveat: **`ContextVar` does not cross thread boundaries**, so async log writes and parallel tool execution need it set explicitly.

- Status: Accepted
- Date: 2026-05-17
- Deciders: Project owner

## Context

A single user request crosses many layers: endpoint → orchestrator → several LLM calls → tools → BigQuery → logs. With plain `print` logging there is no way to correlate **which log line belongs to which request**, which makes incident investigation, cost analysis and shadow comparison impossible to line up.

The requirement: **thread a correlation ID through every layer and every log**, structured so it is searchable in BigQuery.

## Decision

A **Snowflake-style `trace_id`** is minted per request, **propagated automatically through every layer via `ContextVar`**, and always attached to structured JSON logs (`docs/plan_docs/SNOWFLAKE_TRACE_ID_PLAN.md` / [README_ai_architecture.md](../README_ai_architecture.md) §9).

- **Snowflake ID**: a time-sortable 64-bit ID in the Twitter Snowflake style (`backend/app/utils/snowflake.py`).
- **ContextVar propagation**: `set_trace_id` / `get_trace_id` in `request_context` let every layer read the same `trace_id` without passing it explicitly (`backend/app/middleware/request_context.py`).
- **Attached automatically to every log structure**: both `LLMLogEntry` and `ShadowComparisonEntry` read `trace_id` from the ContextVar at construction and include it in `to_dict()`. An explicit value takes precedence ([test_trace_id_propagation.py:12](../backend/tests/utils/test_trace_id_propagation.py#L12) / [:25](../backend/tests/utils/test_trace_id_propagation.py#L25)).
- Propagation reaches `LLMLogEntry`, `ShadowComparisonEntry`, the StructuredLogger JSON and the `format_sse()` payload alike (verified by propagation tests).

## Alternatives Considered

- **Plain print logging**: no correlation, no structure, not searchable in BigQuery. This is what the ADR fixes.
- **Pass a UUID as an argument**: requires adding `trace_id` to every function signature — invasive. A ContextVar propagates without polluting the call graph.
- **Use UUIDv4**: random, so it cannot be sorted chronologically. A Snowflake ID sorts by time on its own, which helps ordering and range queries over logs.
- **Adopt OpenTelemetry in full**: worth learning, but for the immediate goal of threading a correlation ID into BigQuery logs, the core implementation suffices and can be extended incrementally.

## Consequences

**What got better**

- Every log for one request — LLM calls, shadow rows, SSE — can be searched by `trace_id`, enabling incident investigation, cost decomposition and shadow reconciliation.
- ContextVar propagation carries the correlation ID without polluting code in each layer.
- Snowflake's chronological sortability makes time-ordered log analysis straightforward.

**What got worse / new burdens**

- A ContextVar is not always inherited across thread or task boundaries, so **execution on another thread (async log writes, parallel tool execution) needs explicit propagation** — a detail that must be kept in mind.
- The Snowflake generator (clock synchronization, worker id) is ours to implement and operate.

## Why This Matters

- **Granular tracing / observability**: it implements cross-cutting observability through a correlation ID, following industry-standard building blocks (Snowflake IDs, structured logging).

## References

- Design plan: `docs/plan_docs/SNOWFLAKE_TRACE_ID_PLAN.md`
- Implementation: `backend/app/utils/snowflake.py` / `backend/app/middleware/request_context.py`
- Tests: [backend/tests/utils/test_trace_id_propagation.py](../backend/tests/utils/test_trace_id_propagation.py)
- AI layer: [README_ai_architecture.md](../README_ai_architecture.md) §9 request lifecycle
- Related ADRs: [[013-centralized-llm-gateway]], [[019-shadow-evaluation]], [[033-sse-streaming]], [[051-append-only-llm-logging]]
