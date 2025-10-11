# モニタリング戦略

本ドキュメントでは、Diamond Lens MLB Stats Assistantアプリケーションの包括的なモニタリング戦略を概説します。

## 概要

モニタリング戦略は、インフラストラクチャとアプリケーション層全体の可視性を提供し、プロアクティブな問題検出と迅速なインシデント対応を可能にするように設計されています。

## モニタリングアーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                    USER REQUEST                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              INFRASTRUCTURE LAYER                            │
│  - Uptime Checks (3 regions)                                │
│  - Cloud Run Metrics (CPU, Memory, Instance Count)          │
│  - Alert Policies (Down, High CPU, High Memory)             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              APPLICATION LAYER                               │
│  - Custom Metrics (Latency, Errors, Processing Time)        │
│  - Structured Logs (JSON, Searchable Fields)                │
│  - Error Classification (bigquery_error, llm_error, etc.)   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              DATA LAYER (Separate ETL Project)               │
│  - Data Freshness Checks                                    │
│  - BigQuery Job Monitoring                                  │
│  - dbt Test Results                                         │
└─────────────────────────────────────────────────────────────┘
```

## インフラストラクチャ層のモニタリング

### 1. Uptime Checks

**目的**: サービス停止と可用性の問題を検出

**設定**:
- **バックエンドヘルスチェック**: `GET /health`
- **フロントエンドヘルスチェック**: `GET /`
- **頻度**: 60秒
- **リージョン**: USA、EUROPE、ASIA_PACIFIC
- **タイムアウト**: 10秒
- **SSL検証**: 有効

**追跡メトリクス**:
- `monitoring.googleapis.com/uptime_check/check_passed`
- リージョン別成功率
- リージョン別レスポンスタイム

**アラート条件**:
- サービス停止: 60秒間で成功チェック < 1
- 劣化: 5分間で成功率 < 90%

**実装**:
- 場所: [terraform/modules/monitoring/uptime_checks.tf](../terraform/modules/monitoring/uptime_checks.tf)
- リソース: `google_monitoring_uptime_check_config.backend_health`, `google_monitoring_uptime_check_config.frontend_health`

---

### 2. Cloud Runメトリクス

**目的**: コンテナのリソース使用率とスケーリング動作を監視

**追跡メトリクス**:

| メトリクス | 説明 | アラートしきい値 | アクション |
|--------|-------------|-----------------|--------|
| `run.googleapis.com/container/memory/utilizations` | メモリ使用率 % | 5分間で > 80% | メモリ割り当てを増加 |
| `run.googleapis.com/container/cpu/utilizations` | CPU使用率 % | 5分間で > 80% | 最大インスタンス数を増加 |
| `run.googleapis.com/container/instance_count` | アクティブインスタンス数 | > 15 | トラフィックパターンをレビュー |
| `run.googleapis.com/request_count` | 総リクエスト数 | - | ベースライン追跡 |
| `run.googleapis.com/request_latencies` | リクエスト時間 | p95 > 5000ms | パフォーマンス調査 |

**ダッシュボードビュー**:
- Cloud Console → Monitoring → Dashboards → Cloud Run
- フィルタ: `service_name = mlb-diamond-lens-api OR mlb-diamond-lens-frontend`

**実装**:
- 場所: [terraform/modules/monitoring/alert_policies.tf](../terraform/modules/monitoring/alert_policies.tf)
- リソース: `google_monitoring_alert_policy.high_memory_usage`, `google_monitoring_alert_policy.high_cpu_usage`

---

## アプリケーション層のモニタリング

### 3. カスタムメトリクス

**目的**: アプリケーション固有のパフォーマンスと信頼性を追跡

**追跡メトリクス**:

#### 3.1 APIレイテンシ (`custom.googleapis.com/diamond-lens/api/latency`)

**ラベル**:
- `endpoint`: APIエンドポイントパス（例: `/api/v1/qa/player-stats`）
- `status_code`: HTTPレスポンスコード

**単位**: ミリ秒 (ms)

**集約**:
- p50、p95、p99パーセンタイル
- 平均、最小、最大

**アラートしきい値**:
- 5分間でp95 > 6000ms（SEV-2）
- 5分間でp99 > 10000ms（SEV-2）

**コードの場所**: [backend/app/main.py:51-55](../backend/app/main.py#L51-L55)

---

#### 3.2 APIエラー (`custom.googleapis.com/diamond-lens/api/errors`)

**ラベル**:
- `endpoint`: APIエンドポイントパス
- `error_type`: エラーの分類
  - `validation_error`: ユーザー入力エラー
  - `bigquery_error`: データベース障害
  - `llm_error`: AIモデル障害
  - `null_response`: ロジックエラー

**単位**: カウント（累積）

**アラートしきい値**:
- 10分間で総エラー率 > 1%（SEV-2）
- 5分間で`bigquery_error`カウント > 5（SEV-2）
- 5分間で`llm_error`カウント > 10（SEV-3）

**コードの場所**: [backend/app/api/endpoints/ai_analytics_endpoints.py:107](../backend/app/api/endpoints/ai_analytics_endpoints.py#L107)

---

#### 3.3 クエリ処理時間 (`custom.googleapis.com/diamond-lens/query/processing_time`)

**ラベル**:
- `query_type`: クエリのタイプ（例: `season_batting`、`batting_splits`）

**単位**: ミリ秒 (ms)

**目的**: タイプ別のエンドツーエンドクエリ処理パフォーマンスを追跡

**分析**:
- クエリタイプ間の処理時間を比較
- 遅いクエリタイプを特定
- BigQueryレイテンシと関連付け

**コードの場所**: [backend/app/api/endpoints/ai_analytics_endpoints.py:76](../backend/app/api/endpoints/ai_analytics_endpoints.py#L76)

---

#### 3.4 BigQueryレイテンシ (`custom.googleapis.com/diamond-lens/bigquery/latency`)

**ラベル**:
- `query_type`: クエリのタイプ

**単位**: ミリ秒 (ms)

**目的**: 全体的な処理時間からデータベースパフォーマンスを分離

**アラートしきい値**: p95 > 3000ms（クエリ最適化を調査）

**コードの場所**: [backend/app/api/endpoints/ai_analytics_endpoints.py:77](../backend/app/api/endpoints/ai_analytics_endpoints.py#L77)

---

### 4. 構造化ログ

**目的**: 詳細なデバッグとログベースの分析を可能にする

**フォーマット**: JSON（Cloud Logging互換）

**標準フィールド**:
```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "severity": "INFO",
  "message": "Query processed successfully",
  "query_type": "season_batting",
  "processing_time_ms": 2500.5,
  "bigquery_latency_ms": 1200.3,
  "status_code": 200
}
```

**深刻度レベル**:
- `DEBUG`: 詳細な診断（本番環境では無効）
- `INFO`: 通常の操作（リクエストの開始/完了）
- `WARNING`: 非クリティカルな問題（再試行、フォールバック）
- `ERROR`: 注意が必要なエラー
- `CRITICAL`: 即座の対応が必要なシステム障害

**検索可能フィールド**:
- `jsonPayload.query_type`
- `jsonPayload.error_type`
- `jsonPayload.latency_ms`
- `jsonPayload.status_code`

**一般的なログクエリ**:

```bash
# Find all errors in last hour
gcloud logging read "severity=ERROR AND resource.type=cloud_run_revision" \
  --freshness=1h \
  --limit=50

# Find slow queries (> 5 seconds)
gcloud logging read "jsonPayload.processing_time_ms>5000" \
  --limit=50

# Count errors by type
gcloud logging read "jsonPayload.error_type=*" \
  --format=json | jq '.[] | .jsonPayload.error_type' | sort | uniq -c

# View specific query type performance
gcloud logging read "jsonPayload.query_type=batting_splits" \
  --limit=50 \
  --format="table(timestamp, jsonPayload.processing_time_ms)"
```

**コードの場所**: [backend/app/utils/structured_logger.py](../backend/app/utils/structured_logger.py)

---

## モニタリングダッシュボード

### ダッシュボード1: サービスヘルス概要

**目的**: 一目でわかる高レベルのサービスヘルス

**ウィジェット**:
1. **可用性スコアカード**: 現在の稼働率 %
2. **エラー率ゲージ**: 現在のエラー率 vs. SLO
3. **アクティブインシデント**: オープンインシデント数
4. **リクエストボリューム**: 毎分のリクエスト（時系列）
5. **レイテンシ分布**: p50、p95、p99（時系列）

**更新頻度**: 1分

---

### ダッシュボード2: アプリケーションパフォーマンス

**目的**: 詳細なアプリケーションパフォーマンスメトリクス

**ウィジェット**:
1. **エンドポイント別レイテンシ**: レイテンシ分布のヒートマップ
2. **クエリ処理時間**: クエリタイプ別（積み上げ時系列）
3. **BigQueryレイテンシ**: 時間経過のp95
4. **エラー内訳**: エラータイプの円グラフ
5. **遅いクエリ**: 5秒以上のクエリの詳細テーブル

**更新頻度**: 1分

---

### ダッシュボード3: インフラストラクチャメトリクス

**目的**: Cloud Runリソース使用率

**ウィジェット**:
1. **メモリ使用率**: バックエンド vs. フロントエンド（時系列）
2. **CPU使用率**: バックエンド vs. フロントエンド（時系列）
3. **インスタンス数**: 時間経過のアクティブインスタンス数
4. **リクエスト同時実行性**: インスタンスあたりの同時リクエスト数
5. **コールドスタート数**: 時間あたりのコールドスタート数

**更新頻度**: 1分

---

## アラート通知チャネル

### メール通知

**設定**:
- タイプ: `email`
- 変数: Terraformの`notification_email`
- 使用法: すべてのアラートポリシー

**メールフォーマット**:
```
Subject: [ALERT] MLB Diamond Lens - Backend API Down

ポリシー: Backend API Down Alert
リソース: mlb-diamond-lens-api (Cloud Run service)
条件: アップタイムチェックが60秒間失敗
深刻度: CRITICAL

インシデントを表示: [Cloud Consoleリンク]
ログを表示: [Cloud Loggingリンク]
ランブック: https://github.com/.../docs/INCIDENT_RESPONSE.md
```

**設定の場所**: [terraform/modules/monitoring/alert_policies.tf](../terraform/modules/monitoring/alert_policies.tf)

---

### 将来: Slack統合

**計画機能**:
- #alertsチャネルへのリアルタイムアラート通知
- コラボレーションのためのインシデントスレッド作成
- Slackコマンドによるアラート確認
- ステータス更新の自動投稿

**実装**: タイプ`slack`の`google_monitoring_notification_channel`を追加

---

## ログ保持とエクスポート

### Cloud Loggingの保持

**デフォルト保持**: 30日

**推奨**: 長期分析のためにBigQueryにログをエクスポート

### BigQueryエクスポート設定

```bash
# Create log sink to BigQuery
gcloud logging sinks create diamond-lens-logs-sink \
  bigquery.googleapis.com/projects/tksm-dash-test-25/datasets/application_logs \
  --log-filter='resource.type="cloud_run_revision" AND (resource.labels.service_name="mlb-diamond-lens-api" OR resource.labels.service_name="mlb-diamond-lens-frontend")'
```

**分析クエリ**:
```sql
-- Average latency by day
SELECT
  DATE(timestamp) as date,
  AVG(CAST(jsonPayload.latency_ms AS FLOAT64)) as avg_latency_ms
FROM `tksm-dash-test-25.application_logs.cloud_run_revision_*`
WHERE jsonPayload.latency_ms IS NOT NULL
GROUP BY date
ORDER BY date DESC;

-- Error rate by hour
SELECT
  TIMESTAMP_TRUNC(timestamp, HOUR) as hour,
  COUNTIF(severity = 'ERROR') as error_count,
  COUNT(*) as total_count,
  SAFE_DIVIDE(COUNTIF(severity = 'ERROR'), COUNT(*)) * 100 as error_rate_pct
FROM `tksm-dash-test-25.application_logs.cloud_run_revision_*`
GROUP BY hour
ORDER BY hour DESC;
```

---

## モニタリングのベストプラクティス

### 1. アラート疲労の防止

**問題**: 過剰なアラートは対応の有効性を低下させる

**解決策**:
- SLOへの影響に基づいてアラートしきい値を設定（恣意的な値ではなく）
- 適切な時間ウィンドウを使用（一時的なスパイクでアラートしない）
- 関連するアラートをグループ化（相関する問題に対して個別のアラートを作成しない）
- 既知のメンテナンスウィンドウ中のアラート抑制を実装

**現在の設定**:
- すべてのアラートには最低60秒の期間しきい値がある
- 高メモリ/CPUアラートには5分間の持続的な違反が必要
- 通常運用の30分後に自動終了

---

### 2. アクション可能なアラート

**すべてのアラートには以下が必要**:
- 何が問題かの明確な説明
- 調査手順を含むランブックへのリンク
- 対応の緊急性を示す深刻度レベル
- 予想される解決時間

**例**（アラートポリシーから）:
```hcl
documentation {
  content = <<-EOT
    バックエンドAPIがヘルスチェックに応答していません。

    深刻度: CRITICAL (SEV-1)

    調査手順:
    1. Cloud Runサービスステータスを確認
    2. エラーのアプリケーションログをレビュー
    3. 依存関係を確認（BigQuery、Gemini API）

    ランブック: https://github.com/.../docs/INCIDENT_RESPONSE.md#alert-backend-api-down
  EOT
}
```

---

### 3. メトリクス収集の効率性

**避けるべきこと**:
- 高カーディナリティラベル（例: user_id、query_text）
- 過剰なメトリクス書き込み（メトリクスあたり > 1/秒）
- 無制限のラベル値

**現在の設計**:
- 限定されたラベル: `endpoint`、`status_code`、`query_type`、`error_type`
- リクエスト完了時のみメトリクス書き込み（毎秒ではない）
- 制限されたラベル値（クエリタイプは`query_maps.py`で事前定義）

---

### 4. コスト最適化

**Cloud Monitoringのコスト**:
- 課金対象メトリクス: カスタムメトリクス（課金アカウントあたり150を超える）
- ログ取り込み: $0.50/GiB（無料枠後）

**現在の使用量見積もり**:
- カスタムメトリクス: 4タイプ × 10ラベル組み合わせ = 40時系列（無料枠内）
- ログボリューム: 月間約500MB（低トラフィックの場合、無料枠内）

**コスト管理**:
- 必須フィールドのみの構造化ログ
- DEBUGログのログサンプリング（有効な場合）
- 書き込み前のメトリクス集約（リクエストごとの書き込みではない）

---

## モニタリングのギャップと将来の改善

### 現在のギャップ

1. **ユーザーエクスペリエンスモニタリング**
   - フロントエンドパフォーマンス追跡なし（ページロード時間、インタラクションレイテンシ）
   - 解決策: Google AnalyticsまたはカスタムメトリクスでReal User Monitoring (RUM)を追加

2. **合成モニタリング**
   - アップタイムチェックはヘルスエンドポイントのみを検証、完全なユーザーフローではない
   - 解決策: 合成トランザクション（完全なクエリ実行テスト）を実装

3. **依存関係モニタリング**
   - Gemini APIまたはBigQueryヘルスの直接モニタリングなし
   - 解決策: タイムアウト追跡付きのヘルスチェックラッパーを追加

4. **ビジネスメトリクス**
   - クエリ成功率、人気選手、クエリパターンの追跡なし
   - 解決策: ビジネスレベルのカスタムメトリクスを追加

### 計画的改善

**TBD**:
- [ ] Cloud MonitoringでSLOベースのアラートを実装
- [ ] SLOコンプライアンスのカスタムダッシュボードを作成
- [ ] 重要なユーザーフローの合成モニタリングを追加

**TBD**:
- [ ] フロントエンドパフォーマンスモニタリング（Core Web Vitals）
- [ ] BigQueryクエリパフォーマンス追跡
- [ ] ビジネスメトリクスダッシュボード

---

## モニタリングのテスト

### メトリクス収集の確認

```bash
# Check custom metrics are being written
gcloud monitoring time-series list \
  --filter='metric.type=starts_with("custom.googleapis.com/diamond-lens")' \
  --interval-start-time="$(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%SZ)" \
  --interval-end-time="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

### テストアラートのトリガー

```bash
# Test backend down alert (stop service temporarily)
gcloud run services update mlb-diamond-lens-api \
  --region=asia-northeast1 \
  --min-instances=0 \
  --max-instances=0

# Wait 2 minutes for alert to trigger

# Restore service
gcloud run services update mlb-diamond-lens-api \
  --region=asia-northeast1 \
  --min-instances=0 \
  --max-instances=20
```

### ログ収集の確認

```bash
# Generate test log
curl -X POST https://mlb-diamond-lens-api-907924272679.asia-northeast1.run.app/api/v1/qa/player-stats \
  -H "Content-Type: application/json" \
  -d '{"query": "大谷翔平の2024年の打率は？", "season": 2024}'

# Check log appears (wait 30 seconds)
gcloud logging read "jsonPayload.query=*" --limit=1 --freshness=1m
```

---

## 参考資料

- [SLO.md](./SLO.md) - Service Level Objectives
- [INCIDENT_RESPONSE.md](./INCIDENT_RESPONSE.md) - インシデント対応ランブック
- [Google Cloud Monitoring Documentation](https://cloud.google.com/monitoring/docs)
- [Cloud Logging Best Practices](https://cloud.google.com/logging/docs/best-practices)
- [Terraform Monitoring Module](../terraform/modules/monitoring/)

---

## 改訂履歴

| 日付 | バージョン | 変更内容 | 作成者 |
|------|---------|---------|--------|
| 2025-10-01 | 1.0 | 初版モニタリング戦略 | - |
