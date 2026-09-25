# ADR-019: Shadow evaluation (champion / challenger comparison alongside production)

> **TL;DR（日本語）**: オフラインの golden だけでは**本番トラフィックでの挙動**が分からず、かといって新版をいきなり出すのは危険。**champion をユーザーに返しつつ、裏で challenger も走らせてペア比較ログを BQ に残す**。A/B テストと違い、劣化した challenger の出力が**ユーザーに届くことは一度もない**。書き込みは daemon thread の fire-and-forget で、shadow 側の例外は本番フローに**絶対に伝播させない**（シャドー評価の鉄則）。`trace_id` で本番ログと突き合わせられる。代償は challenger 分の**追加トークンコスト**。
>
> **TL;DR (English)**: An offline golden set says nothing about **behavior on real production traffic**, yet shipping a new version blind is risky. The **champion answers the user while the challenger runs in the shadow**, and the pair is logged to BigQuery for comparison. Unlike an A/B test, a degraded challenger response **never reaches a user**. Writes are fire-and-forget on a daemon thread, and shadow-side exceptions **must never propagate** into the production flow. `trace_id` correlates shadow rows with production logs. The cost is the **extra tokens** the challenger burns.

- Status: Accepted
- Date: 2026-05-17
- Deciders: Project owner

## Context

When swapping in a new prompt or model (the challenger), we want to know whether it beats what is in production (the champion). An offline golden dataset says nothing about **behavior on real production traffic**, yet putting the challenger straight into production is risky.

The requirement: **compare old and new safely on real traffic, without affecting what users receive.**

## Decision

**Shadow evaluation** was introduced — the champion answers the user while the challenger runs behind it, and the pair is logged for comparison (`docs/plan_docs/SHADOW_EVALUATION_PLAN.md` / [backend/app/services/shadow_logger_service.py](../backend/app/services/shadow_logger_service.py)).

- Champion/challenger output pairs are accumulated into `ShadowComparisonEntry` and written to the BigQuery `shadow_comparisons` table.
- **Asynchronous writes**: fire-and-forget on a separate thread with `daemon=True`, the same pattern as `llm_logger_service` ([shadow_logger_service.py:5](../backend/app/services/shadow_logger_service.py#L5)).
- **Exceptions must never propagate into the production flow**: shadow-side failures are swallowed internally. The user's response is determined by the champion alone.
- **Automatic trace_id**: `ShadowComparisonEntry` pulls `trace_id` from the ContextVar so shadow rows correlate with production logs ([shadow_logger_service.py:55](../backend/app/services/shadow_logger_service.py#L55), [[032-snowflake-trace-id-structured-logging]]).
- Scoring the comparison can reuse LLM-as-a-Judge ([[018-llm-as-a-judge-offline-evaluation]]).

## Alternatives Considered

- **Offline evaluation only (golden dataset)**: cannot observe the real traffic distribution or its edge cases. Shadow evaluation captures the production distribution.
- **An A/B test (actually serving the challenger to some users)**: risks exposing users to a degraded challenger. Shadow evaluation compares with **zero user impact** and takes no such risk.
- **Running the shadow synchronously**: the challenger's execution time would be added to production latency. Asynchronous fire-and-forget keeps production fast.

## Consequences

**What got better**

- Old and new can be compared on real production traffic, informing the decision to deploy.
- Asynchrony plus swallowed exceptions keep the shadow path from touching production latency or availability.
- `trace_id` allows shadow rows to be matched against production logs for case-by-case investigation.

**What got worse / new burdens**

- The challenger also calls an LLM, so it incurs **extra token cost** (mitigable by sampling).
- Because writes run on an async daemon thread, shadow logs can be lost if the process dies abruptly (no production impact, but evaluation data is missing).
- Managing and scoring champion/challenger pairs adds operational overhead.

## Why This Matters

- **Online evaluation that never interrupts production**: champion/challenger is a standard MLOps pattern, letting new models and prompts be validated without any user impact.

## References

- Design plan: `docs/plan_docs/SHADOW_EVALUATION_PLAN.md`
- Implementation: [backend/app/services/shadow_logger_service.py](../backend/app/services/shadow_logger_service.py)
- Related ADRs: [[018-llm-as-a-judge-offline-evaluation]], [[020-ci-evaluation-gate]], [[032-snowflake-trace-id-structured-logging]], [[051-append-only-llm-logging]]
