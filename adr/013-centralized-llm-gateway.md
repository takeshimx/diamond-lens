# ADR-013: Route every LLM call through a central gateway and always record cost and tokens

> **TL;DR（日本語）**: LLM 呼び出しが各サービスに散在すると、記録漏れ・コスト不可視・価格表の分散が起きる。**単一窓口 `llm_gateway_service` を設け、成功・失敗・例外のいずれでも必ずログを書く**ことで「LLM を呼ぶ＝必ず記録される」を構造的に担保した。記録するのはコストだけでなく、レイテンシ・NLU 解釈結果・成否・フィードバック・trace_id を含む**約 40 カラムの包括的インタラクションログ**。記録は網羅的に完成済みだが、活用（ダッシュボード化）は一部着手に留まる意図的な設計。例外は `ChatOrchestrator` で、窓口関数を経由せず自前でログを書く（テーブルは同一、欠落なし）。
>
> **TL;DR (English)**: Scattering LLM calls across services causes missed logs, invisible cost, and duplicated pricing tables. A **single entry point, `llm_gateway_service`, writes a log entry on success, failure and exception alike**, structurally guaranteeing that calling an LLM always produces a record. It captures far more than cost: **~40 columns of comprehensive interaction logging** — latency, parsed NLU output, success/error, user feedback, trace_id. Capture is complete by design; consumption (dashboards) is deliberately only partly built out. The one exception is `ChatOrchestrator`, which bypasses the wrapper and writes its own entries (same table, nothing lost).

- Status: Accepted
- Date: 2026-05-17
- Deciders: Project owner

## Context

Scattering LLM calls across services causes the following problems.

- **Invisible cost**: there is no way to tell who used which model, when, for how many tokens, at what price. LLM-native cost management (cost-per-request) is impossible.
- **Missed records**: when each site calls `generate_content` independently, some forget to write a log, and records vanish on exceptions.
- **Duplicated model and pricing tables**: pricing tables and token-extraction logic get copied around, and updates are missed.

The requirement is to **structurally** guarantee that calling an LLM always produces a log entry. And what should be recorded is not only cost but the whole interaction: parsed output, latency, success or failure, user feedback, and more.

## Decision

A **single entry point for every LLM call, `llm_gateway_service`**, centralizes token extraction, cost calculation and BigQuery logging ([backend/app/services/llm_gateway_service.py](../backend/app/services/llm_gateway_service.py)).

- `call_gemini()` ([llm_gateway_service.py:97](../backend/app/services/llm_gateway_service.py#L97)) invokes Gemini and uses `try/finally` so that **an `LLMLogEntry` is written on success, failure and exception alike**.
- It extracts `input_tokens` / `output_tokens` / `cached_tokens` from `usage_metadata`, and `_calc_cost_usd()` computes USD cost from a per-model `PRICING` table ([llm_gateway_service.py:52](../backend/app/services/llm_gateway_service.py#L52)). Records land in the `llm_interaction_logs` table.
- These records are the source data for the LLM Usage Cost Dashboard (README #24).
- `get_genai_client()` also centralizes SDK client construction.

The design principle is: **calling an LLM means going through the Gateway, which means a log is always written** ([README_ai_architecture.md](../README_ai_architecture.md) §2 / §3).

### It records far more than cost and tokens (a comprehensive interaction log)

What the Gateway writes to `llm_interaction_logs` is **not limited** to cost and tokens. Each LLM call produces one row of roughly 40 columns; cost is only part of it.

```
                      every LLM call passes through here
                                  │
                          ┌───────▼────────┐
                          │  LLM Gateway   │
                          └───────┬────────┘
                                  │ 1 call = 1 row (~40 columns)
                                  ▼
              ┌─────────────  llm_interaction_logs  ─────────────┐
              │                                                  │
   cost/tokens      latency        NLU parse      success/error   reflection
   input_tokens   llm_latency_ms  parsed_metrics  success        is_retry
   cost_usd       bq_latency_ms   parsed_player   error_type     retry_count
   model          …               …               …              …
              │                                                  │
   feedback        correlation ID  prompt version  input/output
   user_rating    trace_id        prompt_version  user_query
   feedback_*     request_id      …               response_*
              └──────────────────────────────────────────────────┘
```

The Gateway is therefore not a cost recorder but **a comprehensive interaction log that preserves the whole exchange with the LLM**.

### Capture is complete; consumption is partly started and mostly upside

The important distinction is between **capture and consumption**.

```
┌──────────────────────────────────────────────┐
│ ① Capture: already complete                  │
│   ~40 columns accumulate on every single call│
│   = the raw material for analysis is all here│
└───────────────────┬──────────────────────────┘
                    │ because that foundation exists
                    ▼
┌──────────────────────────────────────────────┐
│ ② Consumption: partly started, mostly open   │
│   ✅ cost dashboard (started)                │
│   ✅ Judge evaluation (uses parsed_*)        │
│   ✅ HITL flywheel (uses feedback_*)         │
│   ⬜ latency analysis, error rates… (no      │
│      metrics built yet)                      │
└──────────────────────────────────────────────┘
```

Not every column has been turned into a metric or a dashboard, but because **the material accumulates comprehensively first**, new analysis and improvements are there to be dug out. This is not a weakness but **a deliberate decision to lay a thick analytical foundation early**.

## Alternatives Considered

- **Call the SDK directly from each service**: forgotten logs, records lost on exceptions, and duplicated pricing tables. This is exactly what the ADR eliminates.
- **Delegate to an external LLM observability SaaS (LangSmith, Helicone, etc.)**: adds a dependency and a bill, and duplicates the self-hosted dashboard that already lives in BigQuery. A homegrown Gateway plus BigQuery logs meets the requirement. Rejected.
- **Instrument the HTTP layer via APM or middleware**: LLM-specific metadata such as tokens and cost is hard to obtain at the HTTP layer. An application-layer gateway is the right place.

## Consequences

**What got better**

- Cost and tokens by request, model and feature are all in BigQuery and can be dashboarded — the core of LLM-native cost management.
- **Beyond cost, roughly 40 columns of interaction logging accumulate comprehensively**, creating a foundation for evaluation (Judge), the HITL flywheel, and latency/error analysis to be mined later (capture complete, consumption still upside).
- `try/finally` means records survive exceptions.
- The pricing table and token extraction live in one place, so updates cannot be missed.

**What got worse / new burdens**

- **One exception path**: `ChatOrchestrator` cannot use the LangChain callback, so it bypasses the Gateway's entry point, reuses only `_calc_cost_usd`, and writes its own `LLMLogEntry`. **Logs land in the same table and nothing is lost**, but it deviates from the ideal of funneling every call through the Gateway (see the Consequences section of [[010-chat-orchestrator-replaces-langgraph]]).
- The `PRICING` table is maintained by hand; an unregistered model is recorded at zero cost (a warning is emitted).

## Why This Matters

- **LLM-native metrics (cost-per-request / tokens)**: this is the measurement foundation for per-request cost and token usage.
- **Observability**: it guarantees that every LLM call is observable.

## References

- Implementation: [backend/app/services/llm_gateway_service.py](../backend/app/services/llm_gateway_service.py) (`call_gemini` / `_calc_cost_usd` / `PRICING`)
- Logging: `LLMLogEntry` (`backend/app/services/llm_logger_service.py`) / the `llm_interaction_logs` table
- AI layer: [README_ai_architecture.md](../README_ai_architecture.md) §2 LLM gateway layer / §3 logging & cost tracking layer
- Related ADRs: [[010-chat-orchestrator-replaces-langgraph]], [[015-gemini-context-caching]], [[016-token-budget-pool-separation]], [[032-snowflake-trace-id-structured-logging]], [[051-append-only-llm-logging]]
