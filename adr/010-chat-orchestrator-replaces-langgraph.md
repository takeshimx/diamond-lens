# ADR-010: ChatOrchestrator (function calling, 1 LLM call) replaces Supervisor + 4 LangGraph sub-agents

> **TL;DR（日本語）**: チャット経路を `Supervisor + 4 つの LangGraph sub-agent` から、**素の google-genai SDK + function calling ループで動く単一クラス `ChatOrchestrator`** へ統合した。最大の成果はコスト削減ではなく**精度**で、1 つの質問を routing / oracle / ツール内 NLU / synthesizer の **4 つの LLM が解釈し直す「伝言ゲーム」を解消**した。LLM 呼び出しは 4 回 → 1〜2 回、エージェントコードは約 2,500 行 → 約 400 行。代償は明示的 Reflection ノードを失い、エラー時の立て直しが LLM 任せになったこと。
>
> **TL;DR (English)**: The chat path moved from `Supervisor + four LangGraph sub-agents` to a **single `ChatOrchestrator` class running a plain google-genai function-calling loop**. The headline win is **accuracy, not cost**: one question is no longer reinterpreted by **four separate LLMs** (routing / oracle / in-tool NLU / synthesizer), eliminating the "telephone game" that degraded answers. LLM calls dropped from 4 to 1–2 and agent code from ~2,500 to ~400 lines. The trade-off is losing the explicit reflection node — error recovery is now left to the LLM.

> **Terminology**: "function-calling loop" in this ADR means the google-genai SDK's function calling — passing `types.Tool(function_declarations=...)`, detecting `part.function_call` in the response, executing it, returning the result, and repeating. It is the same concept other SDKs call "tool use," but since this project uses Gemini, the SDK's own term **function calling** is used throughout.

- Status: Accepted
- Date: 2026-05-17
- Deciders: Project owner

## Context

As the chat backend grew from structured RAG into multi-agent orchestration, it ended up with a two-level structure: **`SupervisorAgent` decided `agent_type` via a routing prompt and dispatched to a dedicated Batter / Pitcher / Matchup / Stats / Strategy sub-agent, and each sub-agent in turn ran its own LangGraph (`oracle → executor → reflection → synthesizer`)** (`docs/plan_docs/CHAT_ORCHESTRATOR_REFACTOR_PLAN.md` §2.1).

### Three generations of design (why it was rebuilt)

The chat path passed through **three generations** before arriving at today's `ChatOrchestrator`. What matters is that this was not a linear progression in which each generation fixed a broken predecessor. **Generation 1 worked correctly; generation 2 was a design decision aimed at expanding scope (partly as a learning exercise); and because the result disappointed, the design converged on generation 3.** Each generation is recorded as it actually happened, without hindsight flattery.

```
Gen 1  Structured RAG                     control = the application
  user query
     │
     ▼  🧠 LLM performs NLU (natural language → JSON {query_type, metrics, name, season...})
     ▼  the app builds parameterized SQL with fixed logic (tables/columns from the
        query_maps / METRIC_MAP dictionaries, values bound as @param, whitelist-validated)
     ▼  queries BigQuery (ground truth)
     ▼  🧠 LLM composes an answer from the retrieved data
  answer
  ◎ Worked correctly for basic batter/pitcher stat categories.
    The LLM generated not one character of SQL (parameter extraction only) and column
    names came from a dictionary, leaving no room for fabrication — so hallucination
    genuinely did not exist in this generation. Its weaknesses were elsewhere: poor at
    synthesizing across multiple data sources, and metric definitions duplicated between
    query_maps and the app's SQL construction. Neither weakness drove the migration.

           ↓ The motivation was scope expansion, not defect repair: split stats, matchup
             strategy and (as an idea) team-level questions, all in one chat. If categories
             were going to multiply, a supervisor delegating to specialist sub-agents that
             run independently seemed better. There was also a precautionary worry that
             "complexity might cause hallucination," but the evidence for it was thin.

Gen 2  Supervisor + sub-agents (LangGraph)   control = many LLMs (distributed)
  user query
     ▼  🧠 LLM #1 routing (decides agent_type)
     ▼  🧠 LLM #2 sub-agent oracle (reinterprets the question and plans)
     ▼  🧠 LLM #3 in-tool _parse_query_with_llm (parses the natural language *again*)
     ▼  🧠 LLM #4 synthesizer (raw data → answer)
  answer
  ✗ Contrary to expectations, four separate LLMs interpreted the same question, intent
    drifted at each hop — a telephone game — and answer accuracy fell. Delegation proved
    counterproductive as a means of expanding scope, and debugging was hard because there
    was no way to tell where the drift occurred. Four LLM calls also raised latency and
    cost. Reverting to Structured RAG was considered.

           ↓ Instead of reverting: "consolidate interpretation into a single LLM and have
             it call validated tools — that removes the telephone game while also beating
             gen 1's weakness at cross-source synthesis."

Gen 3  ChatOrchestrator (function-calling loop)   control = one LLM (current)
  user query
     ▼  🧠 the LLM emits structured arguments directly via function calling (NLU happens once)
     ▼  the app merely executes tools (no free-form SQL; via the Semantic Layer)
     ▼  🧠 the same LLM reads the results and decides the next move (loop, max 6) → answer
  answer
  ✓ One interpreter = no telephone game. Cross-tool synthesis is handled by that same mind.
```

| | Gen 1 Structured RAG | Gen 2 Supervisor + sub-agents | Gen 3 ChatOrchestrator |
|---|---|---|---|
| **Control** | The app (a fixed pipeline) | Distributed across many LLMs | **A single LLM** |
| **LLMs that interpret the question** | 1 (NLU only, separate from answering) | **4** (routing / oracle / in-tool / synth) | **1** (folded into function calling) |
| **Data retrieval** | The LLM only extracts parameters; the app **builds dictionary-driven parameterized SQL with fixed logic** (`query_maps`, `METRIC_MAP`, `@param` binding, whitelist validation) | Through sub-agents into the same tools (same `query_maps` dependency) | **Through tools / the Semantic Layer** (no free-form SQL; metric definitions consolidated in dbt as the SSOT) |
| **State of this generation** | Correct for basic stats. Weak at cross-source synthesis; definitions duplicated (neither drove the migration) | **Accuracy fell from the telephone game** (delegation backfired as a scope-expansion device) | (Telephone game removed; one mind handles cross-source synthesis) |
| **Why it moved on** | Tried delegation to expand scope (more categories in one chat) | Delegation backfired, so interpretation was consolidated into one mind | — |

**The point**: the substantive achievement of gen 3 is **removing gen 2's *telephone game***. Gen 2 was not born to fix a defect in gen 1; it was introduced as **a design decision for expanding scope (partly experimental)** and, against expectations, lowered accuracy. Gen 3 resolves that by consolidating interpretation into one LLM, and in doing so also makes the cross-source synthesis gen 1 struggled with tractable. Note that standardizing data retrieval on tools and the Semantic Layer rather than free-form SQL ([[009-dbt-semantic-layer-over-text-to-sql]]) did not "fix gen 1's SQL"; it is an independent improvement that removes the **duplicated metric definitions (the absence of an SSOT)** in gen 1's deterministic SQL construction.

> **Supplement (how the data-retrieval layer evolved)**: Generations 1 and 2 hard-coded "which stat lives in which table as which metric" into a Python dictionary, `query_maps` ([backend/app/config/query_maps.py](../backend/app/config/query_maps.py)), and **the app built parameterized SQL from it with fixed logic** (the LLM generated no SQL; table and column names came from the dictionary and values were bound as `@param`). SQL-induced hallucination therefore did not exist in those generations. The weakness lay elsewhere: the same definitions were duplicated between the app (SQL construction) and dbt, and could drift apart — a risk of silently wrong aggregates. Generation 3 **consolidates those definitions into dbt Semantic Layer YAML as the single source of truth**, with aggregation (`agg: sum` / `average`) owned by the definition side as well. See [[009-dbt-semantic-layer-over-text-to-sql]].

This structure carried the following constraints and problems (the details of the gen-2 issues).

- **Redundant LLM calls**: even a trivial question consumed one routing LLM call plus several more inside the sub-agent's oracle/executor/reflection/synthesizer, driving up latency and cost (4 calls, reducible to 1 as described below).
- **Duplicated logic**: each sub-agent's `oracle / executor / reflection / synthesizer` was close to a copy of the others, so a fix in one did not reach the rest and consistency eroded.
- **Hard to debug**: the overhead of routing → sub-agent initialization → graph compile → astream made it difficult to investigate *which interpretation stage* had drifted when the telephone game degraded an answer.
- **Cost of adding a tool**: adding one tool meant updating at least two files — the sub-agent and the tools module.
- **Architectural overfit**: applying a deterministic StateGraph to a domain well served by a single LLM plus a function-calling loop — free-form conversation, dynamic tool selection, variable output shapes — turned out to be the main source of complexity.

On top of this, with `tool orchestration` (the LLM selecting tools directly) becoming the common shape, the old structure's inability to take that shape was itself a design weakness.

## Decision

The chat path was consolidated into **a single `ChatOrchestrator` class running a plain `google-genai` SDK function-calling loop** ([backend/app/services/chat_orchestrator.py](../backend/app/services/chat_orchestrator.py)).

- **NLU became the responsibility of the orchestrator's own LLM.** Dedicated NLU calls such as the in-tool `_parse_query_with_llm` were removed; the LLM emits structured arguments (`name`, `season`, `metrics`, …) directly through function calling.
- A function-calling loop with `MAX_TOOL_ITERATIONS=6` invokes either `CHAT_TOOL_REGISTRY` (legacy) or the Semantic Layer registry, selected by the `use_semantic_layer` flag.
- The switch is a feature flag, `use_legacy_chat_agent` ([settings.py:173](../backend/app/config/settings.py#L173)); the endpoint at [ai_analytics_endpoints.py:553](../backend/app/api/endpoints/ai_analytics_endpoints.py#L553) chooses between the old `run_mlb_agent_stream` and the new `ChatOrchestrator().run_stream()`, preserving the SSE event contract and I/O compatibility.
- Every legacy SSE event (`routing`, `state_update`, `tool_start`, `tool_end`, `token`, `final_answer`, `error`) is emitted under the same name so the frontend needed no changes. `agent_type` is fixed to `"chat"` and `routing` is sent once.

LLM calls dropped from **4 to 2 — or 1 with `synthesize_response=False`** ([README_ai_architecture.md](../README_ai_architecture.md) §1).

## Alternatives Considered

- **Keep LangGraph as is (status quo)**: the cognitive load of the two-level structure and the debugging difficulty would remain, effectively freezing chat maintenance. A StateGraph's determinism is excessive for free-form conversation. Rejected.
- **Keep the Supervisor but thin out the sub-agents**: the routing LLM call would survive, leaving the root of the redundancy intact and a half-measure of complexity behind. Rejected.
- **Move to a higher-level framework such as LangChain AgentExecutor**: the abstraction is thick, and fine-grained control over `function_call` chunks during streaming and over cost logging is lost. The plain SDK gives transparent control over both the function-calling loop and `LLMLogEntry` logging. Rejected.

## Consequences

**What got better**

- **[Most important] Better answer accuracy and reliability — the telephone game is gone**: in gen 2, **four LLMs reinterpreted one question** (routing / oracle / in-tool NLU / synthesizer) and intent drifted at each hop, lowering accuracy. That was a problem gen 2 introduced; it did not exist in gen 1. `ChatOrchestrator` consolidates interpretation into **a single LLM**, so the drift can no longer occur structurally. Correctness and stability of answers are the primary achievement of this refactor; the code reduction and cost savings below are secondary. Note again that standardizing retrieval on validated tools and the Semantic Layer ([[009-dbt-semantic-layer-over-text-to-sql]]) is an independent improvement addressing duplicated metric definitions — it did not "fix gen 1 SQL hallucination," because gen 1's SQL was dictionary-driven rather than LLM-generated and no such hallucination existed.
- Chat-side agent code shrank dramatically (`MLBStatsAgent` + 5 sub-agents + `SupervisorAgent`, roughly 2,500 lines in total, converge into a ~400-line `ChatOrchestrator`).
- Fewer LLM calls improved latency and cost. Folding NLU into the orchestrator's LLM also simplified tool definitions.
- Adding a tool now means one new file under `tools/` plus its declaration.

**What got worse / new burdens**

- **Error recovery went from strict to LLM-directed**: the explicit reflection node in each sub-agent is gone, and recovery from SQL errors or empty results is left to the **LLM's natural retry behavior** (a "retry once or twice" instruction in the system prompt plus the function-calling loop). Deterministic recovery is less certain. Explicit reflection is retained in StrategyAgent ([[011-retain-langgraph-for-strategy-agent]] / [[012-classified-bounded-reflection-retries]]).
- **Logging runs on a separate path from the Gateway (a consistency note; no actual loss)**: LangChain's `LangchainUsageCallback` is unavailable, so `ChatOrchestrator` calls the SDK directly and assembles its own `LLMLogEntry` rather than going through `llm_gateway_service`'s entry point. **Cost and tokens are recorded in the `llm_interaction_logs` table exactly as elsewhere; nothing is lost** ([chat_orchestrator.py:578](../backend/app/services/chat_orchestrator.py#L578); only `_calc_cost_usd` is reused from the Gateway). What remains is a deviation from the [[013-centralized-llm-gateway]] ideal of routing every LLM call through one entry point.

**Migration status**: accepted after canary operation behind the feature flag (`USE_LEGACY_CHAT_AGENT=false`). Physically deleting the legacy LangGraph sub-agents (`SupervisorAgent`, `BatterAgent`, `PitcherAgent`, `MatchupAgent`, `StatsAgent`, `MLBStatsAgent`, `AgentState`) is deferred pending the owner's decision.

## Why This Matters

- **Modernizing the agent architecture**: this is the move to a function-calling loop in which the LLM selects tools directly. It is the core ADR recording why LangGraph was folded away in the chat path (a right-tool-for-the-job judgment), together with its trade-offs.
- Related: [[009-dbt-semantic-layer-over-text-to-sql]] (tools return metrics through the Semantic Layer) and [[050-tools-return-raw-data-orchestrator-composes]] (tools return raw data only; the orchestrator composes the response).

## References

- Design plan: `docs/plan_docs/CHAT_ORCHESTRATOR_REFACTOR_PLAN.md` (§2 As-Is / §3 To-Be / §5.2 Phase 2)
- AI layer: [README_ai_architecture.md](../README_ai_architecture.md) §1 overview / §9 request lifecycle
- Implementation: [backend/app/services/chat_orchestrator.py](../backend/app/services/chat_orchestrator.py)
- Switch points: [ai_analytics_endpoints.py:553](../backend/app/api/endpoints/ai_analytics_endpoints.py#L553) / [settings.py:173](../backend/app/config/settings.py#L173)
- Related ADRs: [[011-retain-langgraph-for-strategy-agent]], [[012-classified-bounded-reflection-retries]], [[050-tools-return-raw-data-orchestrator-composes]]
