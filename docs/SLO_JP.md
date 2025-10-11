# Service Level Objectives (SLO)

本ドキュメントでは、Diamond Lens MLB Stats Assistantアプリケーションのサービスレベル目標を定義します。

## 概要

SLOは、アプリケーションの目標信頼性とパフォーマンスレベルを定義します。これらの目標は、運用上の意思決定、アラートしきい値、およびインシデント対応の優先順位を導きます。

## SLOフレームワーク

**Error Budget**: 0.1% (99.9% 可用性) = 月間43.8分のダウンタイム

## Service Level Indicators (SLIs) と Objectives (SLOs)

### 1. 可用性

**定義**: 全リクエストに対する成功リクエストの割合 (HTTP 200-299)

**SLI**: `(successful_requests / total_requests) * 100`

**SLO**: 30日間のローリングウィンドウで99.9%の可用性

**測定方法**:
- **成功基準**: HTTP ステータスコード 200-299
- **失敗基準**: HTTP ステータスコード 500-599、タイムアウト
- **除外項目**: HTTP 400-499 (クライアントエラー)

**モニタリング**:
```
# Cloud Monitoring query
sum(rate(api_requests{status_code=~"2.."}[30d])) / sum(rate(api_requests[30d]))
```

**アラートしきい値**: < 99.5% (Error Budget 50%消費)

---

### 2. レイテンシ

**定義**: API応答時間の95パーセンタイル

**SLI**: `p95(request_latency_ms)`

**SLO**:
- **p95 レイテンシ**: < 5000ms (5秒)
- **p99 レイテンシ**: < 8000ms (8秒)

**測定方法**:
- 開始: APIがリクエストを受信
- 終了: クライアントにレスポンスを送信
- 含まれるもの: LLM処理、BigQueryクエリ、レスポンス生成

**モニタリング**:
```
# Custom metric
custom.googleapis.com/diamond-lens/api/latency
```

**アラートしきい値**:
- p95 > 6000ms (5分間継続)
- p99 > 10000ms (5分間継続)

**理由**:
- AI駆動のクエリ処理にはLLM呼び出し (1-3秒) + BigQuery実行 (1-3秒) が必要
- 5秒のp95は、複雑なクエリを考慮しつつ、優れたユーザーエクスペリエンスを提供

---

### 3. エラー率

**定義**: エラーが発生したリクエストの割合

**SLI**: `(error_requests / total_requests) * 100`

**SLO**: 1時間のウィンドウで < 0.5% のエラー率

**エラー分類**:
- `validation_error`: 入力検証の失敗 (カウントしない - ユーザーエラー)
- `bigquery_error`: データベースの失敗 (カウント)
- `llm_error`: AIモデルの失敗 (カウント)
- `null_response`: サービスロジックエラー (カウント)

**モニタリング**:
```
# Custom metric
custom.googleapis.com/diamond-lens/api/errors
```

**アラートしきい値**: > 1% のエラー率が10分間継続

---

### 4. データ鮮度

**定義**: BigQueryで最後にデータが正常に更新されてからの経過時間

**SLI**: `current_time - last_update_timestamp`

**SLO**: < 24時間のデータラグ

**測定方法**:
- クエリ: `SELECT MAX(game_date) FROM fact_batting_stats_with_risp`
- 現在の日付と比較

**モニタリング**: 別のETLプロジェクトでの手動チェックまたはスケジュールクエリ

**アラートしきい値**: > 48時間 (データが著しく古い)

**注意**: このSLOは、本アプリケーションではなくETL/dbtプロジェクトで監視されます

---

## SLOコンプライアンス監視

### 月次SLOレビュー

**レビュースケジュール**: 毎月第1月曜日

**レビュー項目**:
1. 目標に対するSLO達成度
2. Error Budget消費量
3. インシデントのSLOへの影響
4. SLOしきい値の調整（必要な場合）

### ダッシュボードメトリクス

**表示する主要メトリクス**:
- 当月の可用性: 99.95%
- 残りError Budget: 80%
- p95レイテンシトレンド（過去7日間）
- エラータイプ別のエラー率
- インシデント数とMTTR

**ダッシュボードの場所**:
```
Cloud Console → Monitoring → Dashboards → Diamond Lens SLO Dashboard
```

---

## Error Budgetポリシー

### Error Budget配分

**月次総予算**: 43.8分のダウンタイム

**配分**:
- **計画的メンテナンス**: 20分 (45%)
- **計画外インシデント**: 20分 (45%)
- **バッファ**: 3.8分 (10%)

### Budget消費時のアクション

| 残りBudget | アクション |
|------------------|---------|
| > 50% | 通常運用、機能開発を継続 |
| 25-50% | 監視頻度を増加、リスクの高いデプロイを延期 |
| 10-25% | 機能リリースを凍結、信頼性向上に注力 |
| < 10% | 緊急プロトコル: 重大な修正以外の変更は行わない |

### Budgetリセット

Error Budgetは毎月1日00:00 UTCにリセットされます

---

## SLO例外

**SLO計算から除外されるもの**:

1. **計画的メンテナンスウィンドウ**
   - 48時間前に通知
   - 月間最大20分
   - 低トラフィック期間にスケジュール（JST 午前3:00-5:00）

2. **クライアントエラー (HTTP 4xx)**
   - ユーザー入力検証の失敗
   - 認証の失敗
   - レート制限

3. **サードパーティサービス障害**
   - Google Cloud Platformの障害（Gemini API、BigQuery）
   - 制御外のDNS障害

**必要なドキュメント**: すべての例外はインシデントレポートに記録する必要があります

---

## SLO依存関係

### 外部依存関係

| サービス | SLOへの影響 | 緩和策 |
|---------|------------|------------|
| **Gemini API** | 高 (LLM処理) | 再試行ロジック、指数バックオフ |
| **BigQuery** | 高 (データ取得) | クエリ最適化、コネクションプーリング |
| **Cloud Run** | クリティカル (ホスティング) | マルチリージョンデプロイ（将来） |
| **Cloud Logging** | 低 (可観測性) | ローカルフォールバックログ |

### 内部依存関係

| コンポーネント | SLOへの影響 | 緩和策 |
|-----------|------------|------------|
| **query_maps.py** | 高 (SQL生成) | CI/CDでのスキーマ検証ゲート |
| **ai_service.py** | クリティカル (コアロジック) | ユニットテスト（49テスト） |
| **BigQueryスキーマ** | 高 (データアクセス) | 自動スキーマ検証 |

---

## 改訂履歴

| 日付 | バージョン | 変更内容 | 作成者 |
|------|---------|---------|--------|
| 2025-01-15 | 1.0 | 初版SLO定義 | - |

---

## 参考資料

- [Google SRE Book - Service Level Objectives](https://sre.google/sre-book/service-level-objectives/)
- [Cloud Monitoring Documentation](https://cloud.google.com/monitoring/docs)
- [INCIDENT_RESPONSE.md](./INCIDENT_RESPONSE.md)
