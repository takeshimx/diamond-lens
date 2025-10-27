# MLB Analytics Platform - Presentation Template
## Google Slides構成案（L'Oréal Technical Analytics Manager Position）

---

## スライド1: タイトルスライド
**レイアウト**: Title Slide

### コンテンツ:
```
MLB Analytics Platform
End-to-End Data Engineering & Governance

[あなたの名前]
Data Engineer
[日付]
```

### デザイン:
- 背景: 白またはライトグレー
- タイトル: 大きく、太字（48pt）
- サブタイトル: 中サイズ（24pt）
- 名前: 下部中央（18pt）

### ノート（話すこと）:
```
本日は、私が設計・実装したMLB分析プラットフォームを通じて、
L'Oréal Japanで求められるData Governance、ETL、クラウドスキルを
どのように活用できるかをご説明します。
```

---

## スライド2: プロジェクト概要
**レイアウト**: Title and Body

### タイトル:
```
Project Overview
```

### コンテンツ（左側：テキスト）:
```
■ 目的
MLB統計データの分析プラットフォーム構築

■ 技術スタック
- Cloud: Google Cloud Platform
- Data Warehouse: BigQuery
- Transformation: dbt
- Orchestration: Cloud Workflows
- Backend: FastAPI + Gemini API
- Frontend: React + Vite

■ 規模
- データ量: 60GB+ (BigQuery)
- 更新頻度: 週次自動実行
- データ品質: 18個の自動テスト
```

### コンテンツ（右側：箇条書き）:
```
■ Key Features
✓ 4-layer data modeling (dbt)
✓ Automated data quality testing
✓ Cost-optimized architecture
✓ Natural language query interface (Japanese)
✓ CI/CD pipeline with Cloud Build
```

### 画像配置:
**不要**（テキストのみ）

### ノート:
```
このプロジェクトは、ETL、データモデリング、品質管理、コスト最適化という
L'Oréalで求められる全ての要素を網羅しています。
```

---

## スライド3: System Architecture
**レイアウト**: Title Only

### タイトル:
```
System Architecture
```

### 画像配置:
**📍 重要**: `docs/images/architecture.png` を全画面配置
- 位置: スライド中央
- サイズ: スライド幅の90%
- 配置: 上下左右センタリング

### ノート:
```
このアーキテクチャ図から3つのポイントをご説明します：

1. データフロー: 外部API → ETL → BigQuery → dbt → Application
2. AI統合: Gemini APIによる自然言語処理（日本語対応）
3. オーケストレーション: Cloud Workflowsによる週次自動実行

特に注目いただきたいのは、dbtによる4層のTransformation Layerです。
これにより、データ品質とコード再利用性を両立しています。
```

---

## スライド4: Technical Stack vs L'Oréal Requirements
**レイアウト**: Title and Body

### タイトル:
```
How My Skills Match L'Oréal Requirements
```

### コンテンツ（表形式）:
```
┌─────────────────────────┬──────────────────────────┬────────────────────────┐
│ L'Oréal Requirement     │ My Implementation        │ Evidence               │
├─────────────────────────┼──────────────────────────┼────────────────────────┤
│ Strong SQL skills (GCP) │ BigQuery optimization    │ Partitioning,          │
│                         │                          │ Clustering,            │
│                         │                          │ Incremental updates    │
├─────────────────────────┼──────────────────────────┼────────────────────────┤
│ Python (ETL/Automation) │ pandas transformations   │ transform.py: 257 lines│
│                         │ + Cloud Run deployment   │ 3 data pipelines       │
├─────────────────────────┼──────────────────────────┼────────────────────────┤
│ Data Warehousing        │ 4-layer dimensional      │ dbt: Staging →         │
│ & Modeling              │ modeling                 │ Intermediate → Core    │
│                         │                          │ → Marts                │
├─────────────────────────┼──────────────────────────┼────────────────────────┤
│ Cloud Platform (GCP)    │ 5 GCP services           │ BigQuery, Cloud Run,   │
│                         │                          │ Workflows, Build,      │
│                         │                          │ Scheduler              │
├─────────────────────────┼──────────────────────────┼────────────────────────┤
│ Data Quality Tools      │ Automated testing        │ dbt tests: 18 tests    │
│                         │ + CI/CD integration      │ Cloud Build validation │
├─────────────────────────┼──────────────────────────┼────────────────────────┤
│ Data Lineage            │ dbt DAG + documentation  │ Automatic lineage      │
│                         │                          │ graph generation       │
├─────────────────────────┼──────────────────────────┼────────────────────────┤
│ Communication Skills    │ Bilingual NL interface   │ JP→EN translation via  │
│ (JP/EN)                 │                          │ LLM integration        │
└─────────────────────────┴──────────────────────────┴────────────────────────┘
```

### デザイン:
- 表: 3列、7行
- フォント: 12-14pt
- ヘッダー行: 背景色（濃いグレー）、白文字
- 奇数行: 白背景
- 偶数行: ライトグレー背景

### 画像配置:
**不要**

### ノート:
```
この表は、L'Oréalの求人要件と私の実装を1対1でマッピングしたものです。
特に重要なポイントは：

1. Data Quality Tools: 18個の自動テストをCI/CDに組み込み、
   本番環境への不良データ流入を防止

2. Communication Skills: LLM統合により、技術者と非技術者の橋渡しを自動化

3. Cloud Platform: GCPのマネージドサービスをフル活用し、
   運用コストを最小化
```

---

## スライド5: Data Quality & Governance
**レイアウト**: Two Content (左右2分割)

### タイトル:
```
Data Quality & Governance Implementation
```

### コンテンツ（左側：テキスト）:
```
■ Data Quality Controls
• 18 automated tests (dbt)
  - not_null validations
  - accepted_range checks
  - accepted_values enforcement

■ Data Lineage
• Automatic DAG generation
• 4-layer transformation tracking
• Source-to-mart visibility

■ CI/CD Integration
• Cloud Build triggers on git push
• Tests run before deployment
• Production blocked on test failures
```

### 画像配置（右側）:
**📍 重要**: `docs/images/transformation-layers.png`
- 位置: スライド右半分
- サイズ: 右側領域の90%
- 配置: 右側センタリング

### ノート:
```
Data Governanceの実装について3つのポイント:

1. Data Quality as Code:
   テストをコードとして管理し、バージョン管理

2. Automated Validation:
   例えば、打球速度が0-130mphの範囲外のデータは自動検出され、
   本番環境にデプロイされる前にブロック

3. Full Lineage Visibility:
   この図のように、生データからAPIまでの全ての変換過程を追跡可能
```

---

## スライド6: ETL Pipeline & Orchestration
**レイアウト**: Two Content (左右2分割)

### タイトル:
```
ETL Pipeline & Orchestration
```

### コンテンツ（左側：テキスト）:
```
■ Weekly Automated Pipeline
• Cloud Scheduler: Sunday 6:00 AM JST
• Cloud Workflows orchestration
• 7-step execution:
  1. Trigger ETL (Cloud Run)
  2. Load to BigQuery staging
  3. Run dbt transformations
  4. Execute 18 data quality tests
  5. Refresh backend cache
  6. Clear frontend cache
  7. Send Discord notification

■ Incremental Updates
• Statcast data: Daily incremental
• Batting/Pitching stats: Weekly full refresh
• Partition-level insert_overwrite strategy
```

### 画像配置（右側）:
**📍 重要**: `docs/images/data-flow.png`
- 位置: スライド右半分
- サイズ: 右側領域の90%
- 配置: 右側センタリング

### ノート:
```
ETLパイプラインの特徴:

1. Full Automation:
   週次で完全自動実行。手動介入ゼロ

2. Error Handling:
   各ステップで失敗を検知し、Discord通知

3. Cost Optimization:
   増分更新により、不要なデータ処理を回避
```

---

## スライド7: Technical Achievements & Business Impact
**レイアウト**: Title and Body (3列レイアウト)

### タイトル:
```
Technical Achievements & Business Impact
```

### コンテンツ（3列構成）:

**【左列】Cost Optimization**
```
■ Storage Cost Reduction
Before: 10GB+ master tables
After: View-first approach
💰 Savings: $2+/month

■ Query Cost Reduction
• Partitioning: Skip irrelevant data
• Clustering: Minimize scan range
• Incremental: Process only deltas

■ Results
• 10GB storage eliminated
• Query costs reduced by ~30%
```

**【中央列】LLM Integration**
```
■ Data Democratization
Non-technical users can:
1. Ask in Japanese
2. Get instant SQL results
3. Receive natural language answers

■ Technical Implementation
• Gemini 2.5 Flash API
• NL → SQL → NL pipeline
• Dynamic SQL generation
• Japanese ↔ English translation

■ Business Value
→ Power BI alternative
→ Self-service analytics
```

**【右列】Technical Metrics**
```
■ Data Scale
• 60GB+ in BigQuery
• 2M+ Statcast records
• 50K+ batting/pitching stats

■ Code Efficiency
• dbt macros: 52% code reduction
  (157 lines → 75 lines)
• 6 reusable calculation macros

■ Reliability
• Weekly automated execution
• 18 data quality tests
• Custom monitoring metrics
• Zero manual intervention
```

### デザイン:
- 3列を色分け
  - 左列（Cost）: ライトブルー背景
  - 中央列（Innovation）: ライトグリーン背景
  - 右列（Metrics）: ライトイエロー背景
- 各列のタイトル: 太字、16pt
- 本文: 12pt

### 画像配置:
**不要**（テキストのみ、視覚的に3列で区別）

### ノート:
```
このスライドは3つの視点から成果を示しています:

1. Cost Optimization:
   View-first approachにより、ストレージコストを削減。
   L'Oréalのコスト意識の高い環境でも貢献可能

2. LLM Integration:
   技術者と非技術者の橋渡しを自動化。
   これはL'Oréalの"Bridge Technical and Business Needs"に直結

3. Technical Metrics:
   具体的な数値で技術力を証明
```

---

## スライド8: L'Oréal Contribution Potential
**レイアウト**: Title and Body (2列)

### タイトル:
```
How I Can Contribute to L'Oréal Japan
```

### コンテンツ（左側：スキル）:
```
■ Skills Developed in This Project

✓ GCP Data Platform Architecture
  → Design & implement centralized data lake

✓ Data Quality Automation
  → Implement validation at source level

✓ Technical-Business Bridge
  → Translate requirements to technical solutions

✓ Cost Optimization
  → Reduce infrastructure costs via smart design

✓ Bilingual Communication (JP/EN)
  → Support Japan business units
```

### コンテンツ（右側：貢献内容）:
```
■ Direct Contributions to L'Oréal

1️⃣ Asia Region Data Lake Optimization
   • Apply partitioning/clustering best practices
   • Implement cost-effective storage strategies

2️⃣ Japan Business Unit Support
   • Enhance Power BI user experience
   • Provide technical guidance to Data Stewards

3️⃣ Data Quality Implementation
   • Build automated validation frameworks
   • Ensure data integrity at source level

4️⃣ Regional Team Collaboration
   • Act as technical liaison between Japan & Regional team
   • Bridge communication gaps with bilingual skills
```

### デザイン:
- 左右2列を矢印（→）で接続
- 左列: スキル（What I Learned）
- 右列: 貢献（How I Apply）

### 画像配置:
**不要**

### ノート:
```
このプロジェクトで培ったスキルは、L'Oréalの求人要件と完全に一致します。

特に強調したいのは：
1. Technical Liaison: 日本と地域チーム間の技術的な橋渡し
2. Data Quality at Source: ソースレベルでのデータ品質管理の実装経験
3. Bilingual Capability: 日英両言語での技術コミュニケーション

これらのスキルを活かし、L'Oréal Japanのデータ基盤最適化に貢献できます。
```

---

## スライド9: Questions & Discussion
**レイアウト**: Title Only

### タイトル:
```
Thank You
Questions & Discussion
```

### コンテンツ（中央配置）:
```
[あなたの名前]
Email: [your-email@example.com]
GitHub: https://github.com/[your-username]
LinkedIn: [your-linkedin-url]

Portfolio Repository:
https://github.com/[your-username]/mlb-analytics-platform
```

### デザイン:
- 大きなテキスト（中央揃え）
- シンプル、クリーンなデザイン

### 画像配置:
**オプション**: あなたのプロフィール写真（小さく、右下）

### ノート:
```
ご清聴ありがとうございました。
ご質問があれば、喜んでお答えします。
```

---

## 補足資料（Appendix Slides）

### スライドA1: dbt Model Details
**レイアウト**: Title and Body

### タイトル:
```
Appendix: dbt Model Details
```

### コンテンツ:
```
■ Staging Layer (Views)
• stg_statcast_events: 2M+ records
• stg_batting_stats: Weekly updated
• stg_pitching_stats: Weekly updated

■ Intermediate Layer (Views)
• int_statcast_risp_events: RISP situations
• int_statcast_bases_loaded: Bases loaded filter
• int_statcast_runner_on_1b: Runner on 1st only

■ Core Layer (Incremental Tables)
• fact_batting_stats_master: Range partitioned by season
• statcast_2025_partitioned: Date partitioned by game_date

■ Marts Layer (Tables)
• tbl_batter_clutch_risp: Clutch hitting metrics
• tbl_batter_monthly_performance: Monthly aggregations
```

---

### スライドA2: BigQuery Cost Breakdown
**レイアウト**: Title and Body

### タイトル:
```
Appendix: BigQuery Cost Breakdown
```

### コンテンツ（表形式）:
```
┌──────────────────┬─────────────┬──────────────┬──────────┐
│ Resource         │ Before      │ After        │ Savings  │
├──────────────────┼─────────────┼──────────────┼──────────┤
│ Storage (GB)     │ 70GB        │ 60GB         │ -14%     │
│ Monthly queries  │ ~500GB scan │ ~350GB scan  │ -30%     │
│ Storage cost     │ $14/month   │ $12/month    │ $2/month │
│ Query cost       │ $2.5/month  │ $1.75/month  │ $0.75/mo │
└──────────────────┴─────────────┴──────────────┴──────────┘

Optimization Techniques:
• Partitioning: Scan only relevant date ranges
• Clustering: Skip irrelevant data blocks
• Views: Eliminate redundant storage
• Incremental: Process only new data
```

---

## 📝 Google Slidesでの作成手順

### ステップ1: 新規スライド作成
1. Google Slidesを開く
2. 「空白のプレゼンテーション」を選択
3. テーマ: **Simple Light** または **Swiss** を推奨

### ステップ2: 画像のアップロード
1. Google Slidesを開いた状態で
2. メニュー: **挿入 > 画像 > パソコンからアップロード**
3. 以下の3つをアップロード:
   - `docs/images/architecture.png`
   - `docs/images/data-flow.png`
   - `docs/images/transformation-layers.png`

### ステップ3: スライドごとに作成
- 上記テンプレートに従って各スライドを作成
- 画像は「📍 重要」マークがついている箇所に配置

### ステップ4: デザイン調整
- フォント: **Roboto** または **Open Sans**（読みやすさ重視）
- カラースキーム:
  - プライマリ: #4285f4（GCPブルー）
  - セカンダリ: #34a853（GCPグリーン）
  - アクセント: #ea4335（GCPレッド）

---

## 🎨 カラーパレット（GCP公式カラー使用）

```
Blue (Cloud Run):     #4285f4
Green (BigQuery):     #34a853
Yellow (Workflows):   #fbbc04
Red (Monitoring/AI):  #ea4335
Gray (Background):    #f5f5f5
Dark Gray (Text):     #202124
```

---

## ⏱️ プレゼン時間配分（15分想定）

| スライド | 時間 | 内容 |
|---------|------|------|
| 1 | 0:30 | イントロダクション |
| 2 | 1:30 | プロジェクト概要 |
| 3 | 3:00 | アーキテクチャ説明（最重要） |
| 4 | 2:00 | 要件マッピング |
| 5 | 2:00 | Data Governance |
| 6 | 2:00 | ETL Pipeline |
| 7 | 2:00 | 成果とインパクト |
| 8 | 1:30 | L'Oréalへの貢献 |
| 9 | 0:30 | クロージング |
| **合計** | **15:00** | |

---

## 📤 次のステップ

このテンプレートをもとに、Google Slidesで作成を開始してください。

質問や調整が必要な箇所があれば、お知らせください！
