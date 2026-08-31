# ADR-019: Shadow Evaluation（champion / challenger の本番並走比較）

- Status: Accepted
- Date: 2026-05-17
- Deciders: プロジェクトオーナー

## Context（背景・課題）

プロンプトやモデルを新版（challenger）に替えるとき、「本番（champion）より良いか」を確かめたい。しかしオフラインの golden データセットだけでは、**実際の本番トラフィックでの挙動**は分かりません。一方、いきなり challenger を本番に出すのはリスクが高い。

「**本番の実トラフィックで、新旧を安全に比較したい**（ただしユーザー応答には影響させない）」という課題です。

## Decision（決定）

**Shadow Evaluation**（champion を本番として返しつつ、裏で challenger も走らせてペア比較ログを取る）を導入しました（[SHADOW_EVALUATION_PLAN.md](../plan_docs/SHADOW_EVALUATION_PLAN.md) / [backend/app/services/shadow_logger_service.py](../../backend/app/services/shadow_logger_service.py)）。

- champion / challenger の出力ペアを `ShadowComparisonEntry` に積み、BigQuery の shadow_comparisons テーブルへ記録。
- **非同期書き込み**: `llm_logger_service` と同じ「別スレッド + `daemon=True`」パターンで fire-and-forget（[shadow_logger_service.py:5](../../backend/app/services/shadow_logger_service.py#L5)）。
- **本番フローに例外を絶対伝播させない**: shadow 側の失敗を内部で握り潰す（「シャドー評価の鉄則」）。ユーザー応答は champion のみで決まる。
- **trace_id 自動付与**: `ShadowComparisonEntry` は ContextVar から `trace_id` を取得し、本番ログと相関できる（[shadow_logger_service.py:55](../../backend/app/services/shadow_logger_service.py#L55)、[[032-snowflake-trace-id-structured-logging]]）。
- 比較の採点には LLM-as-a-Judge（[[018-llm-as-a-judge-offline-evaluation]]）を流用できる。

## Alternatives Considered（検討した代替案）

- **オフライン評価のみ（golden dataset）**: 実トラフィックの分布・エッジケースを見られない。shadow で本番分布を捉える。
- **A/B テスト（challenger を一部ユーザーに実際に返す）**: ユーザーが challenger の劣化を被るリスクがある。shadow なら**ユーザー影響ゼロ**で比較できる（劣化リスクを取らない）。
- **同期で shadow を実行**: 本番レイテンシに challenger 実行時間が乗る。非同期 fire-and-forget で本番を遅らせない。

## Consequences（結果・トレードオフ）

**良くなったこと**

- 本番の実トラフィックで新旧を比較でき、デプロイ判断の材料になる。
- 非同期 + 例外握り潰しで、shadow が本番のレイテンシ・可用性に影響しない。
- trace_id で本番ログと突き合わせられ、ケース単位で深掘りできる。

**悪くなったこと / 新たな負荷**

- challenger も LLM を呼ぶため、**追加のトークンコスト**が発生する（サンプリングで緩和可能）。
- 非同期 daemon thread のため、プロセス即死時に shadow ログが欠落しうる（本番影響はないが評価データは欠ける）。
- champion/challenger のペア管理・採点の運用コスト。

## JD Alignment（この募集要件との対応）

- **EV★（evaluation pipelines & observability）**: 本番安全な online 評価。champion/challenger は MLOps 標準パターンで、production を意識した評価設計として語れる。

## References

- 設計プラン: [SHADOW_EVALUATION_PLAN.md](../plan_docs/SHADOW_EVALUATION_PLAN.md)
- 実装: [backend/app/services/shadow_logger_service.py](../../backend/app/services/shadow_logger_service.py)
- 関連 ADR: [[018-llm-as-a-judge-offline-evaluation]], [[020-ci-evaluation-gate]], [[032-snowflake-trace-id-structured-logging]], [[051-append-only-llm-logging]]
