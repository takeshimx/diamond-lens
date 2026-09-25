# ADR-050: Tools return raw data; the orchestrator owns response composition

> **TL;DR（日本語）**: 旧経路ではツールが**内部でもう一度 LLM を呼んで文章を作って**おり、1 質問で LLM が二重に走るうえ、ツールが「データ取得器」なのか「応答生成器」なのか曖昧だった。**ツールは生データ（`output_format='data'`）を返すだけにし、複数ツールの結果を 1 つの回答に組み立てる責務は Orchestrator の LLM に一元化**した。これにより複数ツールを横断した合成が可能になり、ツール内 LLM の独自解釈による**伝言ゲームの一因も消える**（ADR-010 と対）。代償は、ツール単体では読める文章を返さないため、デバッグや MCP 経路では呼び出し側が整形を担うこと。
>
> **TL;DR (English)**: In the legacy path each tool **called an LLM of its own to write prose**, so a single question ran two LLMs and it was unclear whether a tool was a data fetcher or an answer generator. Tools now **return raw data only (`output_format='data'`), and composing multiple tool results into one answer belongs solely to the orchestrator's LLM**. That makes cross-tool synthesis possible and removes **one source of the "telephone game"** — tools reinterpreting things on their own (the counterpart to ADR-010). The trade-off: a tool no longer returns readable prose by itself, so debugging and the MCP path must format results at the call site.

- Status: Accepted
- Date: 2026-05-17
- Deciders: Project owner

## Context

In the legacy chat path, a tool (fetching batting stats, say) **called an LLM inside itself to generate a natural-language response** — the so-called two-stage LLM. A tool carried both data retrieval and prose writing.

That creates three problems.

- **Double LLM calls**: a single question ran the orchestrator's LLM and the in-tool LLM separately, raising latency and cost.
- **Mixed responsibilities**: it became unclear whether a tool was a data fetcher or an answer generator, which lowered reusability. When several tools' results needed to be combined into one answer, tools that wrote their own prose were hard to compose.
- **One source of the telephone game**: the in-tool LLM interpreted and summarized on its own, drifting from the context the orchestrator held (see the Context section of [[010-chat-orchestrator-replaces-langgraph]]).

The requirement: let tools focus purely on **what to retrieve**, and consolidate **how multiple retrieved results are assembled into one answer** in the orchestrator's LLM.

## Decision

Tool return values were standardized on **`output_format='data'` (the default) = raw data**, and **generating the response text (composition) belongs to the calling LLM (the orchestrator)**.

- Every tool takes an `output_format` argument and **returns raw data under the default `'data'`** ([batter_stats_tool.py:21](../backend/app/services/tools/batter_stats_tool.py#L21)). `'table'` produces UI table form, and `'sentence'` (prose written by an in-tool LLM) survives only as **deprecated** ([_genai_schemas.py:75](../backend/app/services/tools/_genai_schemas.py#L75)).
- The tool schema descriptions state it explicitly: "`output_format='data'` (default) returns raw data; **the calling LLM generates the response text**" ([_genai_schemas.py:20](../backend/app/services/tools/_genai_schemas.py#L20)).
- `ChatOrchestrator` receives the raw data and returns structured data to the UI layer — with `synthesize_response=False` (the default) it formats Markdown without an LLM, and with `True` an LLM composes the response ([[010-chat-orchestrator-replaces-langgraph]]).

In short, the separation is **tool = raw data fetcher, orchestrator = response composer**.

## Alternatives Considered

- **Call a response-generating LLM inside the tool (the legacy two-stage approach)**: self-contained tools have their appeal, but this brings double LLM calls, mixed responsibilities, difficult composition and a breeding ground for the telephone game. It is precisely what this ADR removes. Rejected.
- **Always return sentences from tools**: cross-tool synthesis becomes impossible, and structured data for the UI (tables, charts, matchup cards) cannot be extracted. Rejected (`'sentence'` remains only as deprecated).
- **Raw data only, with no formatting at all**: the UI needs table form, so a `'table'` mode is necessary. `'data'` is primary and `'table'` supplementary.

## Consequences

**What got better**

- Tools focus on raw data retrieval and become more reusable. The orchestrator can compose several tools' results into one answer in a single pass.
- In-tool LLM calls disappear, lowering latency and cost. With `synthesize_response=False`, not even the composition LLM is called — raw data is formatted and returned directly.
- Ownership of "who assembles the response" is consolidated in the orchestrator, consistent with ADR-010's removal of the telephone game.

**What got worse / new burdens**

- A tool no longer returns readable prose on its own, so anything invoking a tool standalone (debugging, the MCP path) must format the result at the call site.
- The `'sentence'` mode is kept for backward compatibility, leaving a "deprecated but functional" path that can still be misused.

## Why This Matters

- **Separating responsibilities in tool orchestration**: "tools return raw data, the orchestrator composes" is a decision at the core of the agent design.
- Related: [[010-chat-orchestrator-replaces-langgraph]] (only once this separation holds can a single mind do the composing).

## References

- Implementation: [backend/app/services/tools/batter_stats_tool.py](../backend/app/services/tools/batter_stats_tool.py) / [pitcher_stats_tool.py](../backend/app/services/tools/pitcher_stats_tool.py)
- Schema definitions: [backend/app/services/tools/_genai_schemas.py](../backend/app/services/tools/_genai_schemas.py) (the `output_format` description)
- AI layer: [README_ai_architecture.md](../README_ai_architecture.md) §1 (the crux of the design)
- Related ADRs: [[010-chat-orchestrator-replaces-langgraph]]
