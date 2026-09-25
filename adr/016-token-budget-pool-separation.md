# ADR-016: Split the token budget into pools (chat / report / shared)

> **TL;DR（日本語）**: 日次トークン上限が**単一プール**だったため、戦略レポート 1 本（並列 fan-out で数千トークン）を生成するとチャット用の枠まで一緒に枯渇していた。**chat / report の 2 プールに分離し、両者の合算 hard cap を shared として被せる二段構え**にした。判定は「プール別上限 OR 合算 hard cap のいずれか超過で拒否」。実装は in-memory + `threading.Lock` の日次リセットで、Redis 依存を増やさない。代償は**複数インスタンス間でカウントが共有されない**こと（分散整合は未対応）。
>
> **TL;DR (English)**: The daily token cap was a **single pool**, so generating one strategy report (thousands of tokens via parallel fan-out) drained the chat allowance along with it. The budget is now **split into `chat` and `report` pools, with a `shared` combined hard cap layered on top** — a request is rejected if **either** its pool limit or the combined cap is exceeded. It is implemented in memory with a `threading.Lock` and a daily reset, adding no Redis dependency. The trade-off is that **counts are not shared across instances** (no distributed consistency yet).

- Status: Accepted
- Date: 2026-05-17 (Phase 3-A)
- Deciders: Project owner

## Context

Daily LLM token usage is capped as a cost defense, but a **single pool** causes two problems.

- Generating one strategy report (`StrategyAgent` burns thousands of tokens through parallel fan-out) **drains the chat allowance along with it**.
- Reports and chat differ greatly in frequency and per-call cost, yet they draw from the same wallet, so one heavy workload takes the other down with it.

The requirement is to separate allowances by purpose so that **heavy report work cannot starve lightweight chat**.

## Decision

The token budget was split into **two pools plus one derived cap: chat / report / shared** ([backend/app/services/token_budget_service.py](../backend/app/services/token_budget_service.py), Phase 3-A).

- **chat**: usage through `ChatOrchestrator` ([token_budget_service.py:8](../backend/app/services/token_budget_service.py#L8)).
- **report**: usage through `StrategyAgent` / strategy-report / tactics.
- **shared**: the **combined hard cap** over both (a derived value; nothing is recorded against it directly).
- **Decision logic**: `is_budget_exceeded(pool)` returns True if **either the pool's own limit or the combined hard cap is exceeded** ([token_budget_service.py:77](../backend/app/services/token_budget_service.py#L77)) — two layers of protection, per-pool and overall.
- **Accounting**: each path adds to its own pool via `record_usage(tokens, pool=...)` (ChatOrchestrator uses `pool="chat"`).
- **Implementation**: in memory with a `threading.Lock` and a daily reset on the UTC date. No Redis required (the same philosophy as [[030-in-memory-rate-limit]]).

## Alternatives Considered

- **A single pool (status quo)**: reports would keep starving the chat allowance. This is what the ADR fixes.
- **Two fully independent pools (no shared cap)**: the overall cost ceiling would stop working, and the combined total could grow without bound. A derived `shared` hard cap is layered on to guard both levels.
- **A distributed counter such as Redis**: excessive for single-container operation. Even when a restart resets the count, it still serves its purpose as a cost defense (distributed consistency is deferred to [[048-distributed-rate-limit]]).

## Consequences

**What got better**

- Heavy report generation no longer takes the chat allowance down with it, and vice versa.
- The per-pool plus combined structure delivers both fairness by purpose and an overall cost ceiling.
- The implementation is lightweight (in-memory plus a lock) and adds no dependency.

**What got worse / new burdens**

- Because it is in memory, counts are lost on a Cloud Run container restart and are not shared across instances (no distributed consistency yet).
- The per-pool limits (`LLM_DAILY_TOKEN_BUDGET_CHAT` and friends) are heuristics with no guarantee of being an optimal split.
- Operating two sets of thresholds — the existing combined alert and the new per-pool ones — adds overhead.

## Why This Matters

- **Managing LLM-specific state**: a cost-control decision that manages a distinctly LLM-native piece of state — the token budget — on a per-pool basis.

## References

- Implementation: [backend/app/services/token_budget_service.py](../backend/app/services/token_budget_service.py)
- Consumer: [backend/app/services/chat_orchestrator.py](../backend/app/services/chat_orchestrator.py) (`record_usage(..., pool="chat")`)
- AI layer: [README_ai_architecture.md](../README_ai_architecture.md) §9.5 token budget pool separation
- Related ADRs: [[010-chat-orchestrator-replaces-langgraph]], [[011-retain-langgraph-for-strategy-agent]], [[013-centralized-llm-gateway]], [[030-in-memory-rate-limit]], [[048-distributed-rate-limit]]
