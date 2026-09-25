# ADR-049: Security guardrail — three layers of input defense before the LLM

> **TL;DR（日本語）**: 出力後フィルタでは「すでに LLM コストを払い、危険な生成が起きた後」の対処になるため、**LLM に届く前**に 3 層で入力を検査する。実行順は**軽い順**で、構造チェック（500 字超・改行 5 行超・空文字）→ 正規表現によるインジェクション検知（日英両対応）→ キーワードによるオフトピック検知。Layer 2 は**曖昧な入力は通す保守的設計**とし、正当な MLB 質問の誤ブロックを避けている。ブロックは BQ にインシデントとして記録（プライバシー配慮で先頭 200 字のみ）。弱点は正規表現・キーワード方式ゆえに**未知の言い回しを取りこぼす**ことと、パターン辞書の継続メンテが要ること。
>
> **TL;DR (English)**: An output-side filter only acts **after the LLM spend and the dangerous generation have already happened**, so input is screened in three layers **before it reaches the LLM**. They run **cheapest first**: structural checks (over 500 chars, over 5 newlines, empty), then regex injection detection (Japanese and English), then keyword-based off-topic detection. Layer 2 is deliberately **permissive on ambiguous input** so legitimate MLB questions are not falsely blocked. Blocks are recorded to BigQuery as incidents (only the first 200 characters, for privacy). The weaknesses are inherent to regex and keywords: **novel phrasings slip through**, and the pattern dictionary needs ongoing maintenance.

- Status: Accepted
- Date: 2026-05-17
- Deciders: Project owner

## Context

Passing user input straight to the LLM carries the following risks.

- **Prompt injection**: phrasings such as "ignore the previous instructions," "from now on you are…" or "show me your system prompt" aim to overwrite the system prompt, leak information, or jailbreak the model.
- **Off-topic abuse**: using the LLM for purposes unrelated to MLB analysis — poetry, translation, investment advice, malicious requests — harming both cost and safety.
- **Structural anomalies**: abnormally long input or large numbers of newlines used to inflate the prompt aggressively.

The requirement: **screen and block dangerous input before it reaches the LLM.** Letting it through, or filtering only the output, is too late — an output-side filter acts after the LLM spend and the dangerous generation have already occurred.

## Decision

A `SecurityGuardrail` inspects input in three layers **before it reaches the LLM** ([backend/app/services/security_guardrail.py](../backend/app/services/security_guardrail.py)). `ChatOrchestrator` always passes through `validate_and_log()` before calling the LLM.

The three layers run cheapest first:

- **Layer 3 — structural checks** (first, because it is the cheapest): blocks input over `MAX_QUERY_LENGTH=500`, more than `MAX_LINE_COUNT=5` newlines, or empty strings ([security_guardrail.py:156](../backend/app/services/security_guardrail.py#L156)).
- **Layer 1 — injection detection**: regex detection of system_prompt_override / role_reassignment / info_extraction / code_execution / sql_injection / jailbreak_attempt, in both Japanese and English ([security_guardrail.py:25](../backend/app/services/security_guardrail.py#L25)).
- **Layer 2 — off-topic detection**: input containing at least one MLB domain keyword passes. Without one, explicit patterns for creative_writing / cooking / translation / malicious / financial and similar are blocked. Ambiguous input is allowed through to avoid false blocks ([security_guardrail.py:182](../backend/app/services/security_guardrail.py#L182)).

A block writes an incident log to BigQuery (`error_type="injection_attempt"`, with only the first 200 characters of the query, for privacy). A logging failure never stops the main flow ([security_guardrail.py:225](../backend/app/services/security_guardrail.py#L225)).

## Alternatives Considered

- **No defense at all**: defenseless against injection and abuse. This is what the ADR fixes.
- **Output-side filtering only**: acts after the LLM spend and the dangerous generation. Stopping it pre-LLM is both safer and cheaper.
- **Classify input with an LLM-based classifier**: more accurate, but adds an LLM call (cost and latency) to every inspection. The first stage uses lightweight, deterministic regex and keyword checks, leaving room to add LLM classification as a supplement later.
- **Block off-topic input strictly**: this would falsely block ambiguous but legitimate MLB queries. Layer 2 is deliberately permissive: "no MLB keyword and no explicit off-topic pattern" passes.

## Consequences

**What got better**

- Dangerous input is stopped before it reaches the LLM, protecting both cost and safety.
- Running cheapest first (structure → regex → keywords) short-circuits wasted work early.
- Blocks are recorded to BigQuery, making attack patterns observable and correlated by trace_id ([[032-snowflake-trace-id-structured-logging]]).

**What got worse / new burdens**

- Being regex-based, **injections phrased in novel ways can slip through** — more brittle than an LLM classifier.
- Keyword-based off-topic detection can misjudge in both directions: malicious input containing MLB keywords passes, and legitimate input without them is rejected.
- The pattern dictionary needs ongoing maintenance.

## Why This Matters

- **Safety / guardrails**: pre-LLM guardrails are standard practice in generative-AI safety design and form the first layer of defense in depth.

## References

- Implementation: [backend/app/services/security_guardrail.py](../backend/app/services/security_guardrail.py)
- Consumer: [backend/app/services/chat_orchestrator.py](../backend/app/services/chat_orchestrator.py) (`validate_and_log`)
- AI layer: [README_ai_architecture.md](../README_ai_architecture.md) §7 security guardrail
- Related ADRs: [[010-chat-orchestrator-replaces-langgraph]], [[031-firebase-auth-oidc]], [[032-snowflake-trace-id-structured-logging]]
