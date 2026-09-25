# ADR-025: Data drift detection (KS / PSI / mean-shift) + a CI drift gate

> **TL;DR（日本語）**: KMeans / XGBoost 系のモデルは学習時の入力分布を前提にするため、シーズン進行で分布がずれると**予測が静かに劣化**する。**KS 検定・PSI・平均値シフト率**で 3 層のドリフト（Feature = 入力 `X` の変化 / Prediction = 出力 `y` の変化 / Concept = `X→y` の関係の変化）を検知し、PSI>0.1 を warning、>0.2 を critical として分類する。正解ラベルを待つ精度監視と違い、**入力分布なら劣化の予兆を早期に掴める**。最も厄介なのは Concept Drift で、入力が正常に見えるまま正解だけが変わる。CI ゲートは ADR-020 と同じ事情で**現状コメントアウト無効**。
>
> **TL;DR (English)**: KMeans and XGBoost models assume the input distribution they were trained on, so as a season progresses that distribution shifts and predictions **degrade silently**. Three layers of drift are detected with **KS tests, PSI and mean-shift ratio** — Feature (input `X` moved), Prediction (output `y` moved) and Concept (the `X→y` relationship itself moved) — with PSI > 0.1 flagged warning and > 0.2 critical. Unlike accuracy monitoring, which waits for ground-truth labels, **input-distribution drift gives early warning**. Concept drift is the nastiest: inputs look perfectly normal while the correct answer changes underneath. The CI gate is **currently commented out**, for the same reason as ADR-020.

- Status: Accepted (the CI gate is currently disabled in cloudbuild, as with [[020-ci-evaluation-gate]])
- Date: 2026-05-17
- Deciders: Project owner

## Context

The ML models — KMeans for `player_segmentation`, XGBoost for `stuff_plus` / `pitching_plus` / `pitching_plus_plus` — infer on the assumption of the input distribution they were trained on. As a season progresses and data is refreshed, **the input distribution drifts away from the training distribution**, and predictions degrade silently.

The requirement: **detect distributional change in the input data statistically and use it in deployment decisions**, rather than leaving degradation unmonitored.

## Decision

A statistical drift detection service, `data_drift_service`, was implemented and wired into a CI drift gate ([backend/app/services/data_drift_service.py](../backend/app/services/data_drift_service.py) / README #8 / CI/CD STEP 1.6).

It detects three kinds of drift ([data_drift_service.py:9](../backend/app/services/data_drift_service.py#L9)).

- **Feature drift**: distributional change in input features, measured with a **KS test (statistic and p-value), PSI and mean-shift ratio**. Severity is classified as `none` / `warning` (PSI > 0.1) / `critical` (PSI > 0.2) ([data_drift_service.py:32](../backend/app/services/data_drift_service.py#L32)).
- **Prediction drift**: distributional change in model output (`predicted_run_exp`).
- **Concept drift**: change in the relationship between features and target (divergence between prediction and actual).

### How the three differ (at a high level)

With `X` = model input (velocity, spin rate, movement, etc.) and `y` = the prediction target (pitch value), they are distinguished by *what* changed.

```
  Feature drift     the distribution of X changed
                    e.g. league-wide velocity rose from 92mph to 96mph
                    (the entrance changed — the input moved)

  Prediction drift  the distribution of y changed
                    e.g. the model's predictions skew higher across the board
                    (the exit changed — the output moved)

  Concept drift     the X→y *relationship* changed ← the nastiest
                    e.g. the same low pitch (X unchanged) flips from "a good
                    pitch" to "a dangerous pitch" (y) as uppercut swings spread
                    (X looks identical but the correct answer changed —
                     the rules of the world moved)
```

**How to recognize concept drift**: ask whether "the input `X` looks the same as at training time, yet the correct answer `y` changed." If `X` moved and `y` followed, that is feature drift. If `y` moved while `X` **did not**, that is concept drift — and because the input looks perfectly normal, it is **the hardest to detect** (in practice it is caught as divergence between prediction and actual).

Baseline (training distribution) and target (latest distribution) are pulled from BigQuery and evaluated in the CI step `scripts/check_data_drift.py` (`ml-drift-check-gate`).

## Alternatives Considered

- **No monitoring**: model degradation goes unaddressed. This is what the ADR fixes.
- **A single metric (KS alone, etc.)**: KS is sensitive to differences across the whole distribution but says little about *how much* has shifted in business terms. PSI (the industry standard) and mean-shift are used alongside it for a multi-angle verdict.
- **Monitor accuracy metrics only, ignoring drift**: metrics that depend on late-arriving ground truth detect problems late. Input-distribution drift gives early warning without waiting for labels.

## Consequences

**What got better**

- Early signs of model degradation can be caught statistically across three layers: input, output and concept.
- Severity classification (warning/critical) mechanizes the alert-versus-block decision.
- Wired into CI, it can stop retraining and deployment on drifted data.

**What got worse / new burdens**

- The CI drift gate is also currently commented out in cloudbuild (the same situation as [[020-ci-evaluation-gate]]). The detection logic runs, but CI does not enforce it.
- The thresholds (PSI 0.1 / 0.2, the KS alpha) are heuristics and need per-domain tuning.
- Choosing the baseline — which period's distribution to compare against — remains an operational judgment that changes the result.

## Why This Matters

- **Model monitoring**: monitoring is standard MLOps practice. This records a statistically grounded drift gate together with the reasoning behind its thresholds.

## References

- Implementation: [backend/app/services/data_drift_service.py](../backend/app/services/data_drift_service.py)
- CI script: [backend/scripts/check_data_drift.py](../backend/scripts/check_data_drift.py) / [cloudbuild.yaml](../cloudbuild.yaml) (`ml-drift-check-gate`, commented out)
- Tests: [backend/tests/test_data_drift.py](../backend/tests/test_data_drift.py)
- Related ADRs: [[020-ci-evaluation-gate]], [[024-model-registry]], [[026-embedding-quality-semantic-drift]]
