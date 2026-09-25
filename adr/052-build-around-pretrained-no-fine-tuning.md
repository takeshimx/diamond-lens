# ADR-052: Build around pretrained models — no fine-tuning

> **TL;DR（日本語）**: ログも golden データセットも揃っておりファインチューニングは技術的に可能だが、**あえて行わない**ことを方針として明文化した。**モデル本体は変えず、プロンプト・RAG・ツール側**（プロンプトの版管理・Semantic Layer による定義の SSOT・context caching・評価パイプライン）で品質と効率を担保する。理由は、学習データ整備・再学習パイプライン・モデル管理の運用コストに見合わないこと、および**特定の重みにロックインされずモデル差し替えが容易**であること。「やらない」ではなく**中期課題として保留**する判断であり、素材があるのに使っていない機会費用は残る。
>
> **TL;DR (English)**: Logs and a golden dataset are both in place, so fine-tuning is technically feasible — but the decision is to **deliberately not do it**. Quality and efficiency are secured **outside the model**: versioned prompts, a semantic layer as the single source of truth for metric definitions, context caching, and an evaluation pipeline. The reasoning is that the operational cost of training-data curation, retraining pipelines and model management is not yet justified, and staying off custom weights keeps **model swaps easy — no lock-in**. This is a **deferral, not a rejection**; the opportunity cost of unused training material is acknowledged.

- Status: Accepted
- Date: 2026-05-25 (raised as an open question in an AI engineering review; this ADR states the position)
- Deciders: Project owner

## Context

There are broadly two families of ways to raise answer quality in an LLM application.

1. **Train the model itself**: fine-tuning (SFT, LoRA, etc.) to fit the model to your own data.
2. **Use a pretrained model as is and build around it**: prompt engineering, structured tools, RAG, a single source of truth for metrics, context caching — securing quality and efficiency without touching the model.

Diamond Lens has the raw material (logs, a golden dataset), so fine-tuning is technically feasible. An internal design review did in fact raise it as an open question: "**Fine-tuning: not implemented (material is available) / low priority / medium-term**."

This project, however, has taken the position of **putting a pretrained foundation model at the center and building around it**, with prompt engineering, RAG and external tool orchestration as the focus. Since a primary goal is learning and validating new concepts, it is worth stating the decision to *deliberately* skip fine-tuning explicitly.

## Decision

The position is stated explicitly: **use the pretrained model (Gemini 2.5 Flash) as is and do not fine-tune.** Answer quality and efficiency are secured **outside the model**, through the following.

- **Prompt engineering plus version control**: prompts are treated as assets via external txt files and `prompt_registry` ([[014-prompt-as-config]]).
- **Structured tools plus the Semantic Layer**: metric definitions are consolidated in dbt as the single source of truth, and tools return validated data ([[009-dbt-semantic-layer-over-text-to-sql]] / [[050-tools-return-raw-data-orchestrator-composes]]).
- **Context caching**: fixed prefixes are cached to hold down billing ([[015-gemini-context-caching]]).
- **An evaluation pipeline**: LLM-as-a-Judge, shadow evaluation and the golden dataset measure quality continuously.

Fine-tuning is not rejected outright but **deferred as a medium-term item**: as long as the means above meet the requirements, it will not be started.

## Alternatives Considered

- **Fine-tune with SFT / LoRA**: fitting the model to our own data might raise accuracy. But the operational cost of curating training data, running a retraining pipeline and managing models is large, and it diverges from this project's focus on staying pretrained-centric. Prompting plus the Semantic Layer plus caching meet current requirements, so it is not adopted for now (deferred as a medium-term item).
- **Do nothing and leave everything to the bare model**: hallucination and drift in metric definitions would go unsolved. This ADR's position is "do not change the model, but do build around it," which is not the same as leaving it alone.

## Consequences

**What got better**

- No operational burden from a training pipeline, model retraining, or version management.
- Swapping models (a future Gemini release, or a different model entirely) stays easy, with no lock-in to particular fine-tuned weights.
- "Why we do not fine-tune" survives as a conscious technology choice, explainable through its trade-offs.

**What got worse / new burdens**

- Fine domain-specific nuance (baseball-specific phrasing and idiom) must be covered through prompt and RAG work, which has limits.
- The state of "the material is there and unused" persists. The accuracy that fine-tuning might have delivered remains an acknowledged opportunity cost (recorded as a medium-term item).

## Why This Matters

- **A position on building around a pretrained model**: it states, with trade-offs, the decision to **deliberately not choose fine-tuning** as a quality lever, and to build with prompts, RAG and tools instead.

## References

- Related ADRs: [[009-dbt-semantic-layer-over-text-to-sql]], [[014-prompt-as-config]], [[015-gemini-context-caching]], [[050-tools-return-raw-data-orchestrator-composes]]
- Note: this ADR states a project-wide position rather than describing specific code, so it does not map one-to-one onto any file — it exists to put the decision on the record.
