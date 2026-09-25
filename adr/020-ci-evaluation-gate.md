# ADR-020: Deployment evaluation gate (block the deploy on the golden dataset)

> **On the name**: the filename is still `020-ci-evaluation-gate.md`, but this gate is strictly a **CD gate**, not CI. What it stops is the deploy, not the merge, and it runs after the merge to main. The filename is left alone so that `[[020-ci-evaluation-gate]]` links from other ADRs keep working.

> **TL;DR（日本語）**: 手動確認では LLM のパース精度の回帰を見落とすため、**golden dataset に対する精度が閾値 80% を下回ったら Cloud Build がデプロイを止める**品質ゲートを導入した。**この LLM 精度ゲートは現在有効**（golden 40 ケース）。**PR 時点では LLM を呼ぶ評価は走らない**（GitHub Actions は pytest + ruff のみで、golden 関連のテストは JSON の構造検証にとどまる）。「PR では静的検査、デプロイ直前に実 LLM ゲート」という二段構えが現状の姿。
>
> **TL;DR (English)**: Manual checks miss regressions in LLM parse accuracy, so a quality gate blocks the deploy when accuracy against the golden dataset falls below an **80% threshold** (40 golden cases), alongside schema-validation, trajectory, and drift gates for layered protection. **No LLM-calling evaluation runs at PR time**: GitHub Actions runs pytest and ruff, and the golden-dataset test there only validates the file's structure. The shape is static checks on the PR, then real LLM and real BigQuery gates immediately before deploy.

- Status: Accepted
- Date: 2026-05-17
- Last reviewed: 2026-09-21
- Deciders: Project owner

## Context

When prompts or code change, we want **automatic assurance** that LLM parse accuracy has not regressed before the change reaches production. Relying on manual checks lets regressions slip through into production unnoticed.

The requirement: **build a quality gate into the delivery pipeline that blocks the deploy when quality falls below a bar.**

## Decision

An **evaluation gate using the golden dataset** was added to the CD pipeline (Cloud Build). If parse accuracy against the golden dataset falls below the threshold (**≥80%**), the deploy is stopped ([README_ai_architecture.md](../README_ai_architecture.md) §10 / README CI/CD STEP 1.5).

- The evaluation script `scripts/evaluate_llm_accuracy.py` runs as STEP 1.1, `llm-evaluation-gate`, in the same pipeline as image build / push / Cloud Run deploy ([cloudbuild.yaml:32](../cloudbuild.yaml#L32)). Because it calls a real LLM, `GEMINI_API_KEY_V2` is supplied through `availableSecrets`.
- There are two stop conditions: the build fails with `sys.exit(1)` when **accuracy < 80%** or when **even one critical failure** is present ([evaluate_llm_accuracy.py:252](../backend/scripts/evaluate_llm_accuracy.py#L252)).
- Comparable quality gates sit in the same pipeline — schema validation (query_maps vs. live BigQuery, [[022-schema-validation-gate]]), trajectory evaluation (verifying multi-step paths) and drift checks ([[025-data-drift-detection]]) — protecting data, schema and LLM quality in layers.
- The golden dataset grows through the HITL flywheel ([[021-hitl-golden-flywheel]]): 👎 → human review → promotion to golden.

## Two layers of defense

The two layers protect different things.

| Layer | Trigger | Content |
|---|---|---|
| CI ([.github/workflows/ci.yml](../.github/workflows/ci.yml)) | pull_request / push to main | 4 pytest suites + ruff. No external dependencies; finishes in tens of seconds |
| CD ([cloudbuild.yaml](../cloudbuild.yaml)) | push to main (at deploy time) | schema validation → `llm-evaluation-gate` → trajectory → drift. Uses a real LLM and real BigQuery |

**No LLM-calling evaluation runs at PR time.** The `tests/test_llm_evaluation.py` that runs on a PR only validates the structure of golden_dataset.json — required fields, duplicate IDs, valid query_type values, category coverage — and never touches the LLM API. Gates that check consistency against a real LLM and real BigQuery involve credentials and billing, so they are kept off the PR and concentrated in Cloud Build just before deploy. The Cloud Build unit-test step was deleted on 2026-09-08 because it duplicated the GitHub Actions run entirely.

The golden dataset now holds **40 cases** (expanded from 14 in commit 9ce1209). The original premise behind the 80% threshold — "only 14 cases" — is weakening, so raising the bar is now a reasonable thing to consider.

## Alternatives Considered

- **Manual checks only**: regressions get missed. An automated gate stops them mechanically.
- **Detect through monitoring after deploy**: degradation is noticed only once it is live. A pre-deploy gate prevents it instead.
- **A stricter threshold (say ≥95%)**: while the golden set was small (14 cases at the time of writing), a single wobbling case would block deploys constantly and the process would not function. Starting at ≥80% and raising it as the golden set grows was chosen (now 40 cases).
- **Run the real LLM gate at PR time**: that would call the LLM API and real BigQuery on every PR, increasing time, billing and secret exposure. PRs stay static; execution-level gates moved next to the deploy.

## Consequences

**What got better**

- Parse-accuracy regressions are mechanically stopped pre-deploy.
- Together with the schema, trajectory and drift gates, data, schema and LLM quality are protected in layers.
- Beyond the accuracy threshold, requiring zero critical failures catches individually fatal cases that an average score would hide.
- PRs run in tens of seconds with static checks only; the heavy gates are concentrated at deploy time.

**What got worse / open problems**

- **Being a CD gate, it cannot stop a merge.** A change that lowers accuracy lands on main and is only blocked at the moment of deploy. The assumption "main is always deployable" does not hold for LLM accuracy, and recovery requires a revert or a follow-up fix, during which main stays undeployable.
- Even 40 golden cases cannot cover the real traffic distribution. Behavior on unseen input is the job of shadow evaluation ([[019-shadow-evaluation]]).
- Every added gate lengthens deploy time, and a single failure halts the whole release.
- The 80% threshold is a heuristic, and the decision to raise it as the golden set grows has not yet been made.
- Because the gate calls a real LLM, every deploy carries additional token cost and build time.

## Why This Matters

- **A deployment quality gate**: pre-deploy quality gates are standard MLOps/LLMOps practice. This records the split between CI (PR, static checks) and CD (just before deploy, real LLM gate) along with its cost — merges cannot be blocked, so feedback arrives late.

## References

- AI layer: [README_ai_architecture.md](../README_ai_architecture.md) §10
- CD definition: [cloudbuild.yaml](../cloudbuild.yaml) (`llm-evaluation-gate` and the other gates)
- CI definition: [.github/workflows/ci.yml](../.github/workflows/ci.yml) (pytest + ruff)
- Evaluation script: `backend/scripts/evaluate_llm_accuracy.py` (threshold `PASS_THRESHOLD = 0.8`)
- Golden dataset: `backend/tests/golden_dataset.json` (40 cases) / structural validation in `backend/tests/test_llm_evaluation.py`
- Related ADRs: [[018-llm-as-a-judge-offline-evaluation]], [[019-shadow-evaluation]], [[021-hitl-golden-flywheel]], [[022-schema-validation-gate]], [[025-data-drift-detection]]
