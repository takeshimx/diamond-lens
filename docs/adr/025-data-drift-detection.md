# ADR-025: データドリフト検知（KS / PSI / mean-shift）+ CI ドリフトゲート

- Status: Accepted（CI ゲートは [[020-ci-evaluation-gate]] 同様、cloudbuild 上では現状無効化中）
- Date: 2026-05-17
- Deciders: プロジェクトオーナー

## Context（背景・課題）

ML モデル（`player_segmentation` の KMeans、`stuff_plus` / `pitching_plus` / `pitching_plus_plus` の XGBoost）は、学習時の入力分布を前提に推論します。シーズン進行やデータ更新で**入力分布が学習時からずれる（データドリフト）**と、モデルの予測が静かに劣化します。

「**入力データの分布変化を統計的に検知し、デプロイ判定に使いたい**（監視なしで劣化を放置したくない）」という課題です。

## Decision（決定）

統計的なドリフト検知サービス `data_drift_service` を実装し、CI のドリフトゲートに繋ぐ設計にしました（[backend/app/services/data_drift_service.py](../../backend/app/services/data_drift_service.py) / README #8 / CI/CD STEP 1.6）。

3 種類のドリフトを検知します（[data_drift_service.py:9](../../backend/app/services/data_drift_service.py#L9)）。

- **Feature Drift**: 入力特徴量の分布変化を **KS 検定（KS統計量・p値）/ PSI / 平均値シフト率**で測る。severity を `none` / `warning`（PSI>0.1）/ `critical`（PSI>0.2）で分類（[data_drift_service.py:32](../../backend/app/services/data_drift_service.py#L32)）。
- **Prediction Drift**: モデル出力（`predicted_run_exp`）の分布変化。
- **Concept Drift**: 特徴量と目的変数の関係変化（予測 vs 実績の乖離）。

### 3 種類のドリフトの違い（ハイレベル）

`X` = モデルへの入力（球速・回転数・変化量等）、`y` = 予測対象（球の価値）として、何が変わるかで区別します。

```
  Feature Drift     X の分布が変わった
                    例: リーグ全体の球速が 92mph → 96mph に上昇
                    （入口＝入力が変わった）

  Prediction Drift  y の分布が変わった
                    例: モデルの予測値が全体的に高く出るようになった
                    （出口＝出力が変わった）

  Concept Drift     X→y の「関係」が変わった ← 最も厄介
                    例: 同じ低めの球(X 不変)が、打者のアッパースイング普及で
                        「良い球」から「狙われる危険な球」(y) に逆転
                    （X は同じに見えるのに正解が変わる＝世界のルールが変わった）
```

**Concept Drift の見分け方**: 「入力 `X` は学習時と同じに見えるのに、正解 `y` が変わった」かどうか。`X` が変わって `y` が変わるのは Feature Drift。`X` が**変わらない**のに `y` が変わるのが Concept Drift で、入力は正常に見えるため**検知が最も難しい**（実装上は「予測 vs 実績の乖離」で捉える）。

baseline（学習時分布）と target（最新分布）を BigQuery から取り、CI ステップ `scripts/check_data_drift.py`（`ml-drift-check-gate`）で評価する。

## Alternatives Considered（検討した代替案）

- **監視なし**: モデル劣化を放置する。本 ADR が解消する対象。
- **単一指標（KS のみ等）**: KS は分布全体の差に敏感だが業務的な「どれだけずれたか」が分かりにくい。PSI（実務標準）と mean-shift を併用し多面的に判定する。
- **精度メトリクスのみで監視（ドリフトを見ない）**: 正解ラベルが遅れて入る指標では検知が遅れる。入力分布の drift なら正解を待たず早期に気づける。

## Consequences（結果・トレードオフ）

**良くなったこと**

- 入力・出力・概念の 3 層でモデル劣化の予兆を統計的に捉えられる。
- severity 分類（warning/critical）でアラート/ブロックの判断を機械化できる。
- CI に組み込めば、ドリフトしたデータでの再学習・デプロイを止められる。

**悪くなったこと / 新たな負荷**

- CI ドリフトゲートも cloudbuild 上では現状コメントアウト無効（[[020-ci-evaluation-gate]] と同じ事情）。検知ロジックは動くが CI 強制はされていない。
- 閾値（PSI 0.1 / 0.2、KS の alpha）はヒューリスティックで、ドメインごとの調整が要る。
- baseline の取り方（いつの分布を基準にするか）で結果が変わる運用判断が残る。

## JD Alignment（この募集要件との対応）

- **EV★（evaluation & observability / model monitoring）**: モデル監視は MLOps の標準。統計検定ベースの drift gate を設計判断として語れる。

## References

- 実装: [backend/app/services/data_drift_service.py](../../backend/app/services/data_drift_service.py)
- CI スクリプト: [backend/scripts/check_data_drift.py](../../backend/scripts/check_data_drift.py) / [cloudbuild.yaml](../../cloudbuild.yaml)（`ml-drift-check-gate`、コメントアウト中）
- テスト: [backend/tests/test_data_drift.py](../../backend/tests/test_data_drift.py)
- 関連 ADR: [[020-ci-evaluation-gate]], [[024-model-registry]], [[026-embedding-quality-semantic-drift]]
