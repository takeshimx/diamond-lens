# ADR-020: CI 評価ゲート（golden dataset でデプロイをブロック）

- Status: Accepted（**設計・スクリプトは存在。現状 cloudbuild 上では無効化中**）
- Date: 2026-05-17
- Deciders: プロジェクトオーナー

## Context（背景・課題）

プロンプトやコードを変更したとき、LLM のパース精度がデプロイ前に劣化していないかを**自動で保証**したい。手動確認に頼ると、回帰を見落としたまま本番に出てしまいます。

「**品質が基準を下回ったらデプロイをブロックする品質ゲート**を CI に組み込みたい」という課題です。

## Decision（決定）

CI（Cloud Build）に **golden dataset を用いた評価ゲート**を設計しました。golden dataset に対する parse accuracy が閾値（**≥80%**）を下回ったらデプロイを止める方針です（[README_ai_architecture.md](../../README_ai_architecture.md) §10 / README CI/CD STEP 1.5）。

- 評価スクリプト `scripts/evaluate_llm_accuracy.py` を CI ステップ `llm-evaluation-gate` として実行（[cloudbuild.yaml:37](../../cloudbuild.yaml#L37)）。
- 同様の品質ゲートとして schema validation（query_maps vs live BigQuery、[[022-schema-validation-gate]]）、drift check（[[025-data-drift-detection]]）も CI に配置する設計。
- golden dataset は HITL フライホイール（[[021-hitl-golden-flywheel]]）で育つ（👎 → 人手レビュー → golden 昇格）。

## ⚠️ 現状（正直な記載）

**この評価ゲートは、現在 cloudbuild.yaml 上で全面コメントアウトされており無効です**（[cloudbuild.yaml](../../cloudbuild.yaml) の `backend-unit-tests` / `schema-validation-gate` / `llm-evaluation-gate` / `ml-drift-check-gate` がすべて `#` でコメントアウト）。理由は、レイヤー単位デプロイ時に対象外ステップの実行時間・課金を避けるための運用上の措置（feature: cloudbuild step のレイヤー別スコープ管理）。**ゲートの設計・スクリプトは存在するが、CI で強制されていない**のが実態。golden は現状 14 ケース規模。

## Alternatives Considered（検討した代替案）

- **手動確認のみ**: 回帰を見落とす。自動ゲートで機械的に止める。
- **デプロイ後にモニタリングで検知**: 劣化が本番に出てから気づく。pre-deploy ゲートで未然に防ぐ設計を採る。
- **閾値を厳しく（例 ≥95%）**: golden が小規模（14 ケース）な段階では 1 ケースの揺れで頻繁にブロックし運用が回らない。≥80% から始め、golden 拡充に合わせて引き上げる。

## Consequences（結果・トレードオフ）

**良くなったこと（有効化時）**

- parse accuracy の回帰を pre-deploy で機械的に止められる。
- schema/drift ゲートと併せ、データ・スキーマ・LLM 品質を多段で守る CI 思想を示せる。

**悪くなったこと / 課題**

- **現状無効化中**のため、実際の回帰防御は効いていない（最大の負債）。有効化と golden 拡充が残課題。
- golden 14 ケースは小規模で、カバレッジが限定的。閾値 80% もヒューリスティック。
- Judge/評価実行が CI 時間とコストを増やす（有効化時）。

## JD Alignment（この募集要件との対応）

- **EV★（evaluation pipelines）/ BP（best practices: CI 品質ゲート）**: pre-deploy の品質ゲートは MLOps/LLMOps の標準。「設計はあるが現状無効」という運用の正直さも含め、trade-off で語れる。

## References

- AI レイヤー: [README_ai_architecture.md](../../README_ai_architecture.md) §10
- CI 定義: [cloudbuild.yaml](../../cloudbuild.yaml)（評価ゲートはコメントアウト中）
- 評価スクリプト: `backend/scripts/evaluate_llm_accuracy.py`
- 関連 ADR: [[018-llm-as-a-judge-offline-evaluation]], [[021-hitl-golden-flywheel]], [[022-schema-validation-gate]], [[025-data-drift-detection]]
