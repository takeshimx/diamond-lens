# ADR-011: Retain LangGraph only for StrategyAgent (Plan-and-Execute + Parallel Fan-Out)

> **TL;DR（日本語）**: ADR-010 でチャットから LangGraph を剥がした後、「全廃するか」の判断が残った。答えは**適材適所**で、LangGraph は `StrategyAgent` **だけ**に残す。自由会話・動的なツール選択には function calling ループが適するが、対戦戦略レポートは**並列 fan-out・一部失敗時の部分レポート・境界付き retry**を要し、5 ノードの `StateGraph`（planner → parallel_executor → aggregator → reflection → strategist）の決定論性が価値を持つ。代償は**エージェント実行モデルが 2 つ併存**すること。
>
> **TL;DR (English)**: After ADR-010 stripped LangGraph out of chat, the open question was whether to drop it entirely. The answer is **right tool for the job**: LangGraph stays in `StrategyAgent` **only**. Free-form chat with dynamic tool selection fits a function-calling loop, but the matchup strategy report needs **parallel fan-out, partial reports on partial failure, and bounded retries** — where the determinism of a 5-node `StateGraph` (planner → parallel_executor → aggregator → reflection → strategist) pays off. The cost is **maintaining two agent execution models**.

- Status: Accepted
- Date: 2026-05-17
- Deciders: Project owner

## Context

[[010-chat-orchestrator-replaces-langgraph]] folded away the two-level LangGraph structure on the chat side and consolidated it into `ChatOrchestrator` (the plain Gemini SDK plus a function-calling loop). That left one decision open: **drop LangGraph from the project entirely, or keep it on specific paths?**

Chat and the matchup strategy report have very different characteristics.

| Characteristic | Structure that fits |
|---|---|
| Free-form conversation, dynamic tool selection, variable output shape | A single LLM orchestrator + function calling (ADR-010) |
| Structured pipeline, deterministic retries, fixed output schema | A LangGraph StateGraph |

The matchup strategy report (`StrategyAgent`) **analyzes batters, pitchers and head-to-head tendencies together** and produces a six-section report against a fixed schema. Concretely, it needs:

- **Parallel fan-out** across several tools (batting stats, pitching stats, matchup history, pitch-type analysis) and aggregation of the results.
- **Deterministic aggregation and branching** so that a partial report is still returned when some tools fail.
- **Bounded retries** keyed to the error type ([[012-classified-bounded-reflection-retries]]).

This is territory a state machine expressed explicitly as nodes and edges fits naturally; the determinism of a `StateGraph` is worth more here than leaving recovery to a function-calling loop's improvised retries.

## Decision

**LangGraph is retained in `StrategyAgent` only** and was removed entirely from the chat path ([backend/app/services/agents/strategy_agent.py](../backend/app/services/agents/strategy_agent.py)).

`StrategyAgent` keeps a 5-node `StateGraph` in the **Plan-and-Execute + Parallel Fan-Out** pattern.

```
planner → parallel_executor → aggregator → (reflection ⇄ planner) → strategist → END
```

#### What "an LLM with four tools bound" means

Binding means **handing the LLM a list of tools it is allowed to call** (`model.bind_tools(self.tools)` at [strategy_agent.py:61-67](../backend/app/services/agents/strategy_agent.py#L61-L67)). A bound LLM can read the question and **decide for itself** which tool to call with which arguments.

```
                ┌─────────────────────────────────────────────┐
                │   four tools bound to the LLM (Gemini)      │
                │                                             │
   question ──► │  available tools:                           │
  "strategy     │   ① get_batter_stats_tool    (batting)      │
   for Ohtani   │   ② get_pitcher_stats_tool   (pitching)     │
   vs. Cole"    │   ③ mlb_matchup_history_tool (past matchups)│
                │   ④ mlb_matchup_analytics_tool (pitch types)│
                └───────────────────┬─────────────────────────┘
                                    ▼
        the LLM plans "call ①③④" on its own (= the planner node's job)
```

In other words, the planner is the step in which **a Gemini instance equipped with four data-retrieval functions, free to judge which to call**, selects the tools it needs.

#### How data flows through the nodes

```
  ┌──────────┐  a plan: "call ① batting, ③ matchup history, ④ pitch types" (several at once)
  │ planner  │ ───────────────────────────────────────────────┐
  └──────────┘  🧠 the LLM with 4 tools bound                  │
                                                              ▼
  ┌──────────────────┐  runs the three tools *concurrently* (cutting wall time)
  │ parallel_executor│   ① ──┐
  │                  │   ③ ──┼─► asyncio.gather ─► collect each result
  │                  │   ④ ──┘    (one failure becomes an error dict, protecting the rest)
  └────────┬─────────┘
           ▼
  ┌──────────────┐  sorts successes from failures
  │ aggregator   │   · all failed      → set an error
  │              │   · any succeeded   → continue (= partial report)
  └──────┬───────┘
         │
         ├─ fixable failures (SQL error, empty result) ─► ┌────────────┐ fix arguments,
         │                                                │ reflection │ return to planner
         │                                                └─────┬──────┘ (max 2 times)
         │                                                      └──► planner (replan)
         │
         └─ success, or a failure retrying cannot fix ──► ┌────────────┐
                                                          │ strategist │ 🧠 composes the
                                                          └─────┬──────┘ collected data into
                                                                ▼        a six-section report
                                                               END
```

- **planner**: the LLM, with four tools bound, plans simultaneous tool calls (the `strategy_planner` prompt).
- **parallel_executor**: runs synchronous tools concurrently via `asyncio.gather()` + `asyncio.to_thread()`, converting exceptions into error dicts so one failure cannot take down the others' results.
- **aggregator**: sorts successes from failures. Only a total failure sets an error; any success continues (the partial-report design).
- **reflection**: bounded replanning based on error type and empty results ([[012-classified-bounded-reflection-retries]]).
- **strategist**: generates the six-section strategy report using the `strategy_synthesizer` prompt.

`StrategyAgent` is invoked only from `/api/v1/strategy-report/*` and the `/tactics` path, which localizes the `langgraph` dependency to this single file. A `run_structured()` entry point for structured input (batter name, pitcher name, season) has been added, but it reuses the existing `run()` internally and touches neither the nodes nor the prompts.

## Alternatives Considered

- **Drop LangGraph entirely and port StrategyAgent to a function-calling loop too**: parallel fan-out, partial aggregation and bounded retries would have to be recreated with prompt instructions inside a function-calling loop, losing determinism. A StateGraph maps cleanly onto cross-cutting analysis, so a total removal is not worth it. Rejected.
- **Keep StrategyAgent callable from both the chat path (via Supervisor) and its own endpoint**: this contradicts ADR-010's decision to stop the chat route and keep only the strategy endpoint. Retaining the coupling would keep the "a change on one side drags in the other" problem alive. Rejected.
- **Move to an external orchestrator such as Cloud Workflows or Step Functions**: externalizing work in which LLM nodes and tool execution are tightly interleaved adds latency and operational surface. An in-process `StateGraph` is sufficient. Rejected.

## Consequences

**What got better**

- Each feature runs on the structure that suits it — chat on a function-calling loop, cross-cutting analysis on a StateGraph — which is explainable as a right-tool-for-the-job decision.
- The `langgraph` dependency is localized to `strategy_agent.py` and no longer contributes to cognitive load on the chat side.
- The deterministic behavior a StateGraph is good at — parallel fan-out, partial reports, bounded retries — is preserved.

**What got worse / new burdens**

- The project now carries **two agent execution models (function-calling loop and StateGraph)** side by side, each demanding its own maintenance knowledge.
- Tool definitions are shared (`tools/`), but some logic still differs per path — chat retries naturally, while Strategy has an explicit reflection node.
- Physical deletion of the legacy LangGraph sub-agents (`SupervisorAgent` and friends) is still pending, so convergence on a state where `langgraph` is used only by `strategy_agent.py` awaits that cleanup.

## Why This Matters

- **Choosing where multi-agent / hierarchical delegation belongs**: a record of where LangGraph was kept and where it was folded away, decided on functional characteristics (determinism vs. free-form conversation). Paired with ADR-010, it is the core ADR documenting the rationale behind the technology choice.
- Related: [[012-classified-bounded-reflection-retries]] (retry classification in the reflection node).

## References

- Design plans: `docs/plan_docs/MATCHUP_STRATEGY_REPORT_PLAN.md` / `docs/plan_docs/CHAT_ORCHESTRATOR_REFACTOR_PLAN.md` §1.2 (decision criteria)
- Implementation: [backend/app/services/agents/strategy_agent.py](../backend/app/services/agents/strategy_agent.py)
- AI layer: [README_ai_architecture.md](../README_ai_architecture.md) §1 overview / §9 request lifecycle / §8 reflection loop
- Related ADRs: [[010-chat-orchestrator-replaces-langgraph]], [[012-classified-bounded-reflection-retries]]
