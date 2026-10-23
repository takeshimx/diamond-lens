# ADR-018: Multi-dimensional offline evaluation with LLM-as-a-Judge

> **TL;DR（日本語）**: 文字列の完全一致では「`rbi` と `runs_batted_in` は同義」のような**意味的な正しさ**を判定できず、かといって人手レビューは回帰のたびには回らない。**LLM を審判（Judge）として使い、出力を 4 次元（query_type / metrics / entity_resolution / intent_understanding）で 1〜5 点に採点**する仕組みを導入した。単一スコアではなく次元別スコア + `failure_category` を返させ、「どこが悪いか」を分解できるようにしている。**ルールベース評価の置換ではなく補完**。代償は Judge 自体が LLM であるがゆえの**コストと非決定性**（同じ入力でスコアが揺れる）。
>
> **TL;DR (English)**: Exact string matching cannot judge **semantic correctness** (`rbi` and `runs_batted_in` mean the same thing), while human review does not scale to every regression run. An **LLM acts as a Judge, scoring output 1–5 across four dimensions** (query_type / metrics / entity_resolution / intent_understanding). It returns per-dimension scores plus a `failure_category` rather than one number, so failures can be decomposed into causes. This **complements rather than replaces** rule-based evaluation. The cost is that the Judge is itself an LLM — it adds spend and **non-determinism** (scores wobble on identical input).

- Status: Accepted
- Date: 2026-05-17
- Deciders: Project owner

## Context

Measuring LLM output quality — parse correctness, response quality — with rule-based exact matching alone hits a ceiling. **Semantic correctness** such as "`rbi` and `runs_batted_in` mean the same thing" or "the intent is right but the wording differs" cannot be graded PASS/FAIL by string comparison.

Human review is accurate but does not scale to reviewing every case on every regression run. The requirement: **score semantic quality automatically, across multiple dimensions, without relying on humans.**

## Decision

An LLM is used as a Judge to **score output semantically across multiple dimensions** ([backend/app/services/llm_judge_service.py](../backend/app/services/llm_judge_service.py)). It **complements** rule-based evaluation (`evaluate_llm_accuracy.py`) rather than replacing it.

- **Parse-evaluation Judge**, `LLMJudgeService`: scores expected vs. actual on **four dimensions** (`query_type_accuracy` / `metrics_accuracy` / `entity_resolution` / `intent_understanding`) from 1 to 5, passes at `overall_score >= 3.5` (`PASS_THRESHOLD`), and attaches a `failure_category` (e.g. synonym_mismatch) to failures ([llm_judge_service.py:19](../backend/app/services/llm_judge_service.py#L19) / [:45](../backend/app/services/llm_judge_service.py#L45)).
- Several Judge services exist, one per perspective — parsing, response synthesis, routing, reflection and drift alerting: `llm_judge` / `synthesizer_judge` / `routing_judge` / `reflection_judge` / `drift_alert_judge`. The "5-panel" in README #10 refers to this set.
- Judges are themselves LLM calls, so their cost is recorded through the Gateway ([[013-centralized-llm-gateway]]).

### Amendment (2026-10-23): the production Synthesizer Judge scores per answer path

The Synthesizer Judge running on production traffic applied one rubric — factual accuracy, analytical depth, language quality, structure, completeness — to every answer. Most answers, however, are tool output **formatted mechanically** by design ([[050-tools-return-raw-data-orchestrator-composes]]). A local run showed the consequence: an answer with every number correct scored `factual_accuracy = 5` and still **failed at 2.4**, penalized for prose it never claims to write. The rubric was measuring the wrong thing on the majority path.

The rubric now follows the answer path, resolved from tool names in `online_judge_service.resolve_answer_mode`:

| Path | When | Scored (1–5) |
|---|---|---|
| `raw` | Tool data formatted mechanically (default) | `factual_accuracy`, `completeness` |
| `rag` | `glossary_search_tool` fired and the LLM wrote prose | the above + `analytical_depth` (judged as *fit to what the question asks*), `language_quality`, `structure` (judged as *proportionate to length*), + `context_relevance` |
| — | The LLM answered without calling a tool | **Not judged.** There is no source data to check against; abstention is covered offline by `expected_no_tool` golden cases |

- **Pass/fail is computed in code**, not taken from the LLM: the mean of the scored dimensions must be ≥ 3.5 **and** `factual_accuracy` ≥ 3. A factual error cannot be averaged away by good prose.
- Unscored dimensions are recorded as `0` (not applicable), distinct from the lowest score `1`. The path is stored in the existing `synthesizer_path` column, so no schema change was needed.
- The rubrics moved out of code into `app/prompts/synthesizer_judge_{raw,rag}_v1.txt`, loaded through `prompt_registry`, so a rubric change is a versioned prompt change.
- Failed verdicts are reviewed in the Trace Viewer ([[053-agent-trace-viewer-failure-labeling]]); a reviewer labeling a judge-failed trace `correct` records a judge false positive ([[021-hitl-golden-flywheel]]).

## Alternatives Considered

- **Rule-based (exact match) only**: synonyms and wording variation are failed incorrectly, and semantic evaluation is impossible. The Judge fills that gap.
- **Human review only**: accurate but unscalable, and unsuited to automated regression. The Judge acts as a first-pass filter so human attention concentrates on promoting golden cases in the HITL loop ([[021-hitl-golden-flywheel]]).
- **A Judge that returns a single score**: gives no indication of which aspect failed and therefore leads nowhere. Per-dimension scores plus a `failure_category` decompose the cause.

## Consequences

**What got better**

- Semantic quality can be scored automatically across dimensions, so regression detection scales.
- Per-dimension scores plus `failure_category` show *where* the failure is, giving a starting point for improvement.
- The same engine is reusable for shadow evaluation ([[019-shadow-evaluation]]) and the CI gate ([[020-ci-evaluation-gate]]).

**What got worse / new burdens**

- Because the Judge is itself an LLM, judging carries **cost and non-determinism** (scores can wobble on identical input).
- The Judge model (`gemini-2.0-flash`) carries its own bias and misjudgment risk, and the 3.5 threshold is a heuristic.
- Results depend on the prompt, so revising the Judge prompt shifts evaluation outcomes.

## Compliance

| | |
|---|---|
| **Invariant** | The Judge returns per-dimension scores plus a `failure_category`, and passes at `overall_score >= 3.5`. A Judge collapsed to a single number has stopped serving its purpose, which is locating the failure, not counting it. |
| **How it is checked** | `backend/tests/test_llm_judge.py` and `test_synthesizer_judge.py` cover the parsing, per-path scoring, and pass rule without calling the API. Production responses are scored at 50% sampling (`ONLINE_JUDGE_SAMPLE_RATE`, set in the Cloud Run deploy step) by `online_judge_service`. |
| **Enforcement** | ✅ for the unit tests (`.github/workflows/ci.yml`) / 👁 for the production score — a drop fires nothing, though failures are now reviewable in the Trace Viewer (`JUDGE NG`). |
| **Reading (2026-10-23)** | `PASS_THRESHOLD = 3.5`, `FACTUAL_ACCURACY_FLOOR = 3`. No production chat traffic in the preceding 30 days, so no production verdicts yet. Listed in [docs/FITNESS_FUNCTIONS.md](../docs/FITNESS_FUNCTIONS.md) §2-1 as observation only. |

**The Judge is deliberately not a gate, and that is a consequence of its own design.** Scores wobble on identical input, so a single reading below 3.5 is as likely to be Judge noise as a real regression. Blocking a deploy on one non-deterministic number would produce false stops and train everyone to re-run the build.

Making it gate-able would require the same move [[020-ci-evaluation-gate]] makes for trajectories: **repeat the measurement and require consistency** (the `pass^3` pattern), or gate on a moving average rather than a point reading. Neither is implemented. Until then the score belongs on a trend line, and the enforcement column should keep saying 👁 rather than implying more than it does.

Note also that the Judge is itself billed through the Gateway, so adding sampling volume to tighten the signal has a direct cost. Until 2026-10-23 the code default was 5% and the live service ran at 1% (set by hand on Cloud Run, outside git); it is now 50%, set in the deploy step. At current traffic the absolute cost is small, and at 1% almost nothing was being judged. The rate should come down again as traffic grows.

## Why This Matters

- **The core of the evaluation pipeline**: LLM-as-a-Judge is the standard method for quality evaluation in generative AI and forms the foundation for accuracy measurement.

## References

- Implementation: [backend/app/services/llm_judge_service.py](../backend/app/services/llm_judge_service.py) and the other `*_judge_service.py` modules
- Evaluation script: [backend/scripts/evaluate_with_llm_judge.py](../backend/scripts/evaluate_with_llm_judge.py)
- Tests: `backend/tests/test_llm_judge.py` and others
- Related ADRs: [[019-shadow-evaluation]], [[020-ci-evaluation-gate]], [[021-hitl-golden-flywheel]], [[013-centralized-llm-gateway]]
