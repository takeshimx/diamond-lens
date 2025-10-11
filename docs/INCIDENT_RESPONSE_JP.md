# インシデント対応ランブック

本ドキュメントでは、Diamond Lens MLB Stats Assistantの本番環境インシデントに対応するための段階的な手順を提供します。

## 目次

1. [インシデント深刻度レベル](#インシデント深刻度レベル)
2. [アラート対応手順](#アラート対応手順)
3. [一般的なインシデントと解決策](#一般的なインシデントと解決策)
4. [エスカレーション手順](#エスカレーション手順)
5. [インシデント事後レビュー](#インシデント事後レビュー)

---

## インシデント深刻度レベル

### SEV-1: クリティカル（完全なサービス停止）

**定義**: アプリケーションが完全に利用不可、または重大なデータ損失

**例**:
- すべてのリクエストに対してバックエンドAPIが500エラーを返す
- フロントエンドが読み込まれない
- データベース接続が完全に失われる
- データ破損が検出される

**対応時間**: 即座 (< 5分)

**解決目標**: < 1時間

**アクション**:
- オンコールエンジニアに即座にページング
- インシデントチャネルを作成（Slack/Teams）
- 経営陣への通知が必要
- 公開ステータスページを更新

---

### SEV-2: 高（部分的なサービス劣化）

**定義**: 複数のユーザーに影響する重大な劣化

**例**:
- APIレイテンシ > 10秒 (p95)
- エラー率 > 5%
- 特定のクエリタイプが失敗（例: すべてのバッティングスプリットクエリ）
- BigQueryクォータ超過

**対応時間**: < 15分

**解決目標**: < 4時間

**アクション**:
- オンコールエンジニアに通知
- 調査を開始
- 内部関係者への通知

---

### SEV-3: 中（軽微な劣化）

**定義**: ユーザーの一部に限定的な影響

**例**:
- 特定の選手クエリが失敗
- チャートレンダリングの問題
- 特定のクエリタイプの応答時間が遅い
- 高メモリ使用率（80-90%）

**対応時間**: < 1時間

**解決目標**: < 24時間

**アクション**:
- チケットを作成
- 営業時間内に調査
- エスカレーションを監視

---

### SEV-4: 低（外観的または非機能的）

**定義**: ユーザーへの影響はないが運用上の懸念

**例**:
- ログエラー
- 監視のギャップ
- ドキュメントが古い
- 非クリティカルな依存関係の脆弱性

**対応時間**: < 1営業日

**解決目標**: < 1週間

---

## アラート対応手順

### アラート: Backend API Down

**トリガー**: アップタイムチェックが60秒間失敗

**深刻度**: SEV-1

#### 調査手順

1. **アラートを確認** (1分)
   ```bash
   # Check if backend is responding
   curl https://mlb-diamond-lens-api-907924272679.asia-northeast1.run.app/health
   ```

2. **Cloud Runサービスステータスを確認** (2分)
   ```bash
   # View service status
   gcloud run services describe mlb-diamond-lens-api --region=asia-northeast1

   # Check recent revisions
   gcloud run revisions list --service=mlb-diamond-lens-api --region=asia-northeast1
   ```

3. **最近のログをレビュー** (3分)
   ```bash
   # Check for errors in last 10 minutes
   gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" \
     --limit 50 \
     --format json \
     --freshness=10m
   ```

#### 一般的な原因と解決策

**原因1: メモリ不足 (OOMKilled)**

**症状**: ログに「Memory limit exceeded」またはコンテナの再起動が表示される

**解決策**:
```bash
# Increase memory allocation
gcloud run services update mlb-diamond-lens-api \
  --region=asia-northeast1 \
  --memory=1Gi

# Or via Terraform
# Update terraform/modules/cloud-run/main.tf: memory = "1Gi"
terraform apply
```

**原因2: 依存関係の失敗（BigQuery/Gemini API）**

**症状**: ログに接続エラーまたはAPIタイムアウトが表示される

**解決策**:
```bash
# Check service account permissions
gcloud projects get-iam-policy tksm-dash-test-25 \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:907924272679-compute@developer.gserviceaccount.com"

# Verify Gemini API key
gcloud secrets versions access latest --secret="GEMINI_API_KEY"

# Test BigQuery access
bq query --use_legacy_sql=false 'SELECT COUNT(*) FROM `tksm-dash-test-25.mlb_analytics_dash_25.fact_batting_stats_with_risp`'
```

**原因3: 不適切なデプロイ**

**症状**: デプロイ直後に問題が発生

**解決策**:
```bash
# Rollback to previous revision
gcloud run services update-traffic mlb-diamond-lens-api \
  --region=asia-northeast1 \
  --to-revisions=PREVIOUS_REVISION=100

# Or redeploy last known good image
gcloud run deploy mlb-diamond-lens-api \
  --region=asia-northeast1 \
  --image=gcr.io/tksm-dash-test-25/mlb-diamond-lens-api:PREVIOUS_TAG
```

---

### アラート: Frontend Down

**トリガー**: フロントエンドのアップタイムチェックが60秒間失敗

**深刻度**: SEV-1

#### 調査手順

1. **フロントエンドのアクセス可能性を確認**
   ```bash
   curl https://mlb-diamond-lens-frontend-907924272679.asia-northeast1.run.app/
   ```

2. **Cloud Runサービスを確認**
   ```bash
   gcloud run services describe mlb-diamond-lens-frontend --region=asia-northeast1
   ```

3. **nginxログを確認**
   ```bash
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=mlb-diamond-lens-frontend" \
     --limit 50 \
     --freshness=10m
   ```

#### 解決策

**原因: バックエンドURLの設定ミス**

**症状**: フロントエンドは読み込まれるがAPI呼び出しが失敗

**解決策**:
```bash
# Verify VITE_API_URL environment variable
gcloud run services describe mlb-diamond-lens-frontend \
  --region=asia-northeast1 \
  --format="value(spec.template.spec.containers[0].env)"

# Update if incorrect
gcloud run services update mlb-diamond-lens-frontend \
  --region=asia-northeast1 \
  --set-env-vars="VITE_API_URL=https://mlb-diamond-lens-api-907924272679.asia-northeast1.run.app"
```

---

### アラート: High Memory Usage (>80%)

**トリガー**: Cloud Runメモリが5分間80%を超える

**深刻度**: SEV-2

#### 調査手順

1. **現在のメモリ使用量を確認**
   ```bash
   # Cloud Monitoring query
   gcloud monitoring time-series list \
     --filter='metric.type="run.googleapis.com/container/memory/utilizations"' \
     --format=json
   ```

2. **メモリ集約的な操作を特定**
   ```bash
   # Check for large result sets in logs
   gcloud logging read "jsonPayload.query_type=* AND resource.type=cloud_run_revision" \
     --limit 50 \
     --format json
   ```

#### 解決策

**短期的な緩和策**:
```bash
# Increase memory allocation
gcloud run services update mlb-diamond-lens-api \
  --region=asia-northeast1 \
  --memory=1Gi
```

**長期的な修正**:
- 大規模なBigQueryクエリに対して結果のページネーションを実装
- クエリ結果のキャッシュを追加
- PythonでのDataFrame操作を最適化

---

### アラート: High CPU Usage (>80%)

**トリガー**: Cloud Run CPUが5分間80%を超える

**深刻度**: SEV-2

#### 調査手順

1. **同時リクエスト数を確認**
   ```bash
   # View active instances
   gcloud run services describe mlb-diamond-lens-api \
     --region=asia-northeast1 \
     --format="value(status.traffic[0].latestRevision)"
   ```

2. **遅いクエリをレビュー**
   ```bash
   # Find high latency requests
   gcloud logging read "jsonPayload.latency_ms>5000" \
     --limit 50 \
     --format json
   ```

#### 解決策

**短期的**:
```bash
# Increase max instances
gcloud run services update mlb-diamond-lens-api \
  --region=asia-northeast1 \
  --max-instances=50
```

**長期的**:
- BigQueryクエリを最適化（インデックスの追加、フルテーブルスキャンの削減）
- クエリ結果のキャッシュを実装
- コストの高い操作にレート制限を追加

---

### アラート: High Error Rate (>1%)

**トリガー**: エラー率が10分間1%を超える

**深刻度**: SEV-2

#### 調査手順

1. **エラータイプを特定**
   ```bash
   # Group errors by type
   gcloud logging read "jsonPayload.error_type=* AND severity=ERROR" \
     --limit 100 \
     --format json | jq '.[] | .jsonPayload.error_type' | sort | uniq -c
   ```

2. **エラーの詳細をレビュー**
   ```bash
   # Get recent error messages
   gcloud logging read "jsonPayload.error_type=bigquery_error" \
     --limit 10 \
     --format="table(timestamp, jsonPayload.error_message)"
   ```

#### エラータイプ別の解決策

**bigquery_error**:
- BigQueryクォータを確認: Cloud Console → BigQuery → Quotas
- テーブルの存在と権限を確認
- スキーマ検証を実行: `python backend/scripts/validate_schema_config.py`

**llm_error**:
- Gemini APIキーの有効性を確認
- Gemini APIのクォータとレート制限を確認
- 最近のGemini APIモデル更新をレビュー

**null_response**:
- ロジックエラーについてアプリケーションログを確認
- クエリパラメータのデータが存在するか確認
- `ai_service.py`の最近のコード変更をレビュー

---

## エスカレーション手順

### レベル1: オンコールエンジニア

**責任**:
- 初期トリアージと調査
- ランブック手順の実行
- 即座の緩和策の実施

**レベル2にエスカレーションする条件**:
- 30分以内に解決できない（SEV-1）
- Cloud Runを超えたインフラストラクチャの変更が必要
- 制限されたリソースへのアクセスが必要

---

### レベル2: シニアエンジニア / テックリード

**責任**:
- 複雑なデバッグと根本原因分析
- 緩和のためのアーキテクチャ決定
- 外部チームとの調整（GCPサポート）

**レベル3にエスカレーションする条件**:
- GCPプラットフォームの問題が疑われる
- セキュリティインシデントが検出される
- 複数のサービスが影響を受ける

---

### レベル3: エンジニアリングマネージャー / CTO

**責任**:
- 経営層の意思決定
- 顧客コミュニケーション
- GCPサポートのエスカレーション
- インシデント事後レビューの監督

---

## インシデントコミュニケーション

### 内部コミュニケーションテンプレート

```
[INCIDENT] [SEV-X] 簡単な説明

ステータス: INVESTIGATING / IDENTIFIED / MONITORING / RESOLVED
開始: YYYY-MM-DD HH:MM UTC
影響: ユーザーへの影響の説明
ETA: 解決までの推定時間

現在のアクション:
- アクション1
- アクション2

次の更新: X分後
```

### ステータスページ更新テンプレート

```
現在、Diamond Lensアプリケーションの問題を調査中です。
ユーザーは[影響の説明]を経験する可能性があります。

30分ごとに更新を提供します。

最終更新: YYYY-MM-DD HH:MM UTC
```

---

## インシデント事後レビュー

### タイムライン

**24時間以内**: 初期インシデントサマリー

**3営業日以内**: 完全なポストモーテムドキュメント

**1週間以内**: アクションアイテムの割り当てと追跡

---

### ポストモーテムテンプレート

```markdown
# インシデントポストモーテム: [簡単な説明]

## インシデントサマリー
- **日付**: YYYY-MM-DD
- **期間**: X時間Y分
- **深刻度**: SEV-X
- **影響**: X人のユーザーに影響、Yリクエストが失敗

## タイムライン (UTC)
- HH:MM - インシデント開始
- HH:MM - アラート発動
- HH:MM - 調査開始
- HH:MM - 根本原因特定
- HH:MM - 緩和策適用
- HH:MM - サービス復旧
- HH:MM - 監視により通常運用を確認

## 根本原因
何が問題で、なぜそうなったかの詳細な説明。

## 影響評価
- 失敗したリクエスト: X
- 影響を受けたユーザー: Y
- SLOへの影響: Z分のError Budget消費
- 収益への影響（該当する場合）: $X

## うまくいったこと
- インシデント対応のポジティブな側面
- 効果的なランブック手順
- 良好なコミュニケーション

## うまくいかなかったこと
- 監視のギャップ
- 検出の遅れ
- 不十分なドキュメント

## アクションアイテム
| アクション | 担当者 | 優先度 | 期限 | ステータス |
|--------|-------|----------|----------|--------|
| Xの監視を追加 | エンジニアA | 高 | YYYY-MM-DD | オープン |
| ランブックを更新 | エンジニアB | 中 | YYYY-MM-DD | オープン |
| サーキットブレーカーを実装 | エンジニアC | 高 | YYYY-MM-DD | オープン |

## 学んだ教訓
主な学びと必要なシステム的改善。
```

---

## 緊急連絡先

### オンコールローテーション

PagerDuty / Opsgenieで管理

**エスカレーションチェーン**:
1. オンコールエンジニア（0-30分）
2. テックリード（30-60分）
3. エンジニアリングマネージャー（60分以上）

### 外部サポート

**Google Cloud Support**:
- Console: https://console.cloud.google.com/support
- 電話: [サポート階層に基づくサポート番号]
- 優先度: SEV-1インシデントにはP1

**Gemini API Support**:
- ドキュメント: https://ai.google.dev/docs
- コミュニティ: https://discuss.ai.google.dev

---

## 便利なコマンドリファレンス

### クイック診断
```bash
# Check all services health
gcloud run services list --region=asia-northeast1

# View recent deployments
gcloud run revisions list --service=mlb-diamond-lens-api --region=asia-northeast1 --limit=5

# Check error logs (last 1 hour)
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" \
  --freshness=1h \
  --limit=50

# View custom metrics
gcloud monitoring time-series list \
  --filter='metric.type=starts_with("custom.googleapis.com/diamond-lens")'

# Check BigQuery quota
gcloud alpha bq show --project_id=tksm-dash-test-25

# Test backend locally
curl -X POST https://mlb-diamond-lens-api-907924272679.asia-northeast1.run.app/api/v1/qa/player-stats \
  -H "Content-Type: application/json" \
  -d '{"query": "大谷翔平の2024年の打率は？", "season": 2024}'
```

---

## 改訂履歴

| 日付 | バージョン | 変更内容 | 作成者 |
|------|---------|---------|--------|
| 2025-01-15 | 1.0 | 初版ランブック作成 | - |

---

## 参考資料

- [SLO.md](./SLO.md)
- [MONITORING.md](./MONITORING.md)
- [Google Cloud Run Troubleshooting](https://cloud.google.com/run/docs/troubleshooting)
- [Google SRE Book - Incident Management](https://sre.google/sre-book/managing-incidents/)
