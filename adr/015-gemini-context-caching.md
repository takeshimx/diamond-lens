# ADR-015: Use Gemini Context Caching to cut re-computation billing on fixed prefixes

> **TL;DR（日本語）**: 数千トークンのシステムプロンプトを毎回フル課金で送っていた（`client.caches.create()` を呼ぶコードがリポジトリに 1 件もなく `cached_tokens` は常に 0 だった）。**固定プレフィックスを Gemini の Context Caching に登録し、ヒット部分の課金を約 1/10 に下げた**。プロンプトを短縮して品質を落とすのではなく、**質を保ったまま再計算の課金だけを削る**点が要。function calling ループは 1 リクエストで複数回 LLM を呼ぶため効果が倍加する。TTL 3600 秒・残り 5 分で自動再作成、キャッシュ障害時は**非キャッシュ経路へ fail-open**。
>
> **TL;DR (English)**: A multi-thousand-token system prompt was being re-billed in full on every request — the repo contained **no call to `client.caches.create()` at all**, and `cached_tokens` was always 0. The fixed prefix is now **registered with Gemini Context Caching, cutting billing on cache hits to roughly 1/10**. The point is that this **preserves prompt quality while removing only the re-computation charge**, rather than shortening the prompt. The saving multiplies across a function-calling loop, which calls the LLM several times per request. TTL is 3600s with automatic re-creation at 5 minutes remaining, and cache failures **fail open** to the uncached path.

- Status: Accepted
- Date: 2026-05-17
- Deciders: Project owner

## Context

Sending a system prompt — a fixed prefix of several thousand tokens — to the LLM on every request means **paying full price for those input tokens every time**. Diamond Lens prompts (`oracle_semantic`, `strategy_synthesizer`, `chat_orchestrator_system`, etc.) have large fixed prefixes, and a function-calling loop calls the LLM several times per request, so the re-computation charge compounds.

Re-billing the same prefix every time is waste, and Gemini's **Context Caching** — which caches an identical prefix server-side and bills the hit portion at roughly **1/10** — removes it. Yet at the time of the AI engineering review, the repository contained **no call to `client.caches.create()` at all**, and `cached_tokens` was permanently 0 (`docs/plan_docs/diamond-lens-review-05252026.md` #2).

### How it works (one prompt = a large fixed part + a small dynamic part)

A prompt splits into "the same fixed instructions every time" (large) and "the user's question" (small, different every time).

```
┌──────────────────────────────────────┐
│ Fixed part (system prompt)           │ ← identical every time, large
│ "You are an expert MLB analyst..."   │
├──────────────────────────────────────┤
│ Dynamic part (user question)         │ ← changes every time, small
│ "How many RBIs did Ohtani have?"     │
└──────────────────────────────────────┘
```

```
■ Without caching: billed in full every time
  req1: [compute fixed][compute dynamic] → 💰💰💰💰💰
  req2: [compute fixed][compute dynamic] → 💰💰💰💰💰  ← re-computing the fixed part is expensive
  req3: [compute fixed][compute dynamic] → 💰💰💰💰💰

■ With caching: the computed state of the fixed part is reused
  req1: [compute fixed & store][compute dynamic] → 💰💰💰💰💰 (first call is normal)
  req2: [reuse stored fixed    ][compute dynamic] → 💰🪙  ← fixed part at ~1/10
  req3: [reuse stored fixed    ][compute dynamic] → 💰🪙
```

> **A common misconception**: caching does not mean "the fixed part is no longer sent to the LLM." **The fixed part is still sent every time and still informs the answer.** What is cached is the *computed state* of having read that prefix, and what is saved is **only the re-computation charge**. That is why cost drops without giving up any prompt quality — shortening the prompt would defeat the purpose (see Alternatives).

## Decision

Lifecycle management was implemented in `prompt_cache_service` to **register the fixed prefix via `client.caches.create()` and reference it as `cached_content` on `generate_content`** ([backend/app/services/prompt_cache_service.py](../backend/app/services/prompt_cache_service.py)).

- **Cache key**: a composite of `prompt_name | version | model | mode | tools | sha256(prefix)[:16]`. Changing the prefix content yields a different cache ([prompt_cache_service.py:68](../backend/app/services/prompt_cache_service.py#L68)).
- **TTL and automatic re-creation**: default TTL is 3600 seconds. With fewer than 5 minutes remaining (`MIN_REMAINING_SECONDS=300`), the cache is recreated to avoid referencing an expired entry ([prompt_cache_service.py:74](../backend/app/services/prompt_cache_service.py#L74)).
- **Fail-open**: if cache creation fails, `None` is returned and the caller **falls back to the uncached path**, so a cache failure never stops the main flow ([prompt_cache_service.py:105](../backend/app/services/prompt_cache_service.py#L105)).
- **Working around an API constraint**: `generate_content` with `cached_content` cannot also accept `system_instruction`, `tools` or `tool_config`, so caching a function-calling loop requires including `tools` in the cache itself ([prompt_cache_service.py:61](../backend/app/services/prompt_cache_service.py#L61); used by ChatOrchestrator).

## Alternatives Considered

- **Keep sending the full prompt every time (status quo)**: the fixed prefix is billed in full on every call. This is what the ADR removes.
- **Shorten the prompt to reduce tokens**: this means cutting instructions that directly determine quality — the wrong trade. Caching lowers the bill while keeping the prompt intact.
- **Make the cache mandatory (fail-closed)**: a cache failure would stop chat entirely. Availability wins, so fail-open was chosen.

## Consequences

**What got better**

- Cache hits on the fixed prefix are billed at roughly 1/10. Because a function-calling loop calls the LLM several times per request, the saving multiplies by the number of iterations.
- `cached_tokens` is now recorded, so the cache discount is reflected in cost calculation ([[013-centralized-llm-gateway]]).
- Fail-open preserves availability during cache outages.

**What got worse / new burdens**

- The registry is in memory, so a Cloud Run container restart loses the cache names and triggers re-creation (a limited cost).
- A prefix under 1,024 tokens is ineligible for Gemini caching and silently falls back — a case where the effect is zero.
- Because the cache key includes version and hash, every prompt revision ([[014-prompt-as-config]]) creates a new cache.

## Why This Matters

- **Cost optimization**: this lowers cost-per-request directly and is a concrete implementation of inference optimization.

## References

- Implementation: [backend/app/services/prompt_cache_service.py](../backend/app/services/prompt_cache_service.py)
- Consumer: [backend/app/services/chat_orchestrator.py](../backend/app/services/chat_orchestrator.py) (`get_or_create_cache`)
- AI layer: [README_ai_architecture.md](../README_ai_architecture.md) §2.5 context caching
- Review: `docs/plan_docs/diamond-lens-review-05252026.md` #2
- Related ADRs: [[013-centralized-llm-gateway]], [[014-prompt-as-config]]
