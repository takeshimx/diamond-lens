# Diamond Lens - MLBスタッツアシスタント 🔮⚾

自然言語クエリと高度なカスタムアナリティクスを通じてメジャーリーグベースボールの統計を探索するAI搭載アナリティクスインターフェース。React、FastAPI、Google Cloud BigQueryで構築。

## 🌟 機能

### コアモード
- **💬 チャットモード**: 日本語での自然言語クエリとAI搭載レスポンス
- **⚡ クイック質問**: 事前定義された一般的な野球クエリで即座に結果を取得
- **⚙️ カスタムクエリビルダー**: カスタム状況フィルターを使った高度なアナリティクス

### アナリティクス機能
- **打撃統計**: シーズン成績、スプリット、高度なStatcastメトリクス
- **投手統計**: 防御率、WHIP、三振率、高度なアナリティクス
- **状況別スプリット**: 得点圏成績、満塁、カスタムゲーム状況
- **キャリアアナリティクス**: 複数シーズントレンド分析とキャリア集計
- **ビジュアルチャート**: 年次推移チャートとKPIサマリーカード
- **高度フィルター**: イニング別、カウント別、投手対戦別分析

### 技術機能
- **AI搭載処理**: Gemini 2.5 Flashを使用したクエリ解析とレスポンス生成
- **リアルタイムインターフェース**: ローディング状態とライブ更新付きのインタラクティブ体験
- **大文字小文字非依存検索**: 柔軟な選手名マッチング
- **ダークテーマUI**: 長時間使用に最適化されたモダンでレスポンシブなインターフェース
- **セキュアアクセス**: 認証ユーザー向けパスワード保護インターフェース

## 🏗 アーキテクチャ

### コアデータ処理パイプライン
アプリケーションは洗練された4ステップパイプラインに従います：

1. **🧠 LLMクエリパース** (`ai_service._parse_query_with_llm`)
   - 自然言語（日本語）を構造化されたJSONパラメータに変換
   - Gemini 2.5 Flashを使用してプレイヤー名、メトリクス、シーズン、クエリタイプを抽出
   - プレイヤー名を英語フルネームに正規化

2. **⚙️ 動的SQL生成** (`ai_service._build_dynamic_sql`)
   - `query_maps.py`を介して抽出されたパラメータをBigQueryテーブルスキーマにマップ
   - 複数のクエリタイプを処理：`season_batting`、`season_pitching`、`batting_splits`
   - 状況別スプリット（得点圏、満塁、イニング別など）をサポート

3. **📊 BigQueryデータ取得**
   - GCPプロジェクト `project-id` のMLB統計テーブルに対して生成されたSQLを実行
   - メインテーブル：`fact_batting_stats_with_risp`、`fact_pitching_stats`
   - スプリット専用テーブル：`tbl_batter_clutch_*`、`tbl_batter_inning_stats`など

4. **💬 LLMレスポンス生成** (`ai_service._generate_final_response_with_llm`)
   - 構造化データを自然な日本語レスポンスに変換
   - ナラティブ（`sentence`）と表形式（`table`）の出力形式の両方をサポート

### 主要設定システム
- **`query_maps.py`**: すべてのクエリタイプとメトリクスマッピングの中央設定
- **`QUERY_TYPE_CONFIG`**: クエリタイプをテーブルスキーマとカラムマッピングにマップ
- **`METRIC_MAP`**: セマンティックメトリクス名を実際のデータベースカラム名に翻訳
- 異なるスプリットコンテキスト間での複雑なメトリクスマッピングをサポート

## 🛠 技術スタック

### フロントエンド
- **React 19.1.1** - 最新機能を備えたモダンReact
- **Vite 7.1.2** - 高速ビルドツールと開発サーバー
- **Tailwind CSS 4.1.11** - ダークモード対応のユーティリティファーストCSSフレームワーク
- **Lucide React 0.539.0** - 美しいアイコンライブラリ
- **ESLint** - コードリンティングとフォーマッティング

### バックエンド
- **FastAPI** - モダンなPython Webフレームワーク
- **Uvicorn** - 本番デプロイメント用ASGIサーバー
- **Google Cloud BigQuery** - MLB統計のデータウェアハウス
- **Google Cloud Storage** - 追加データストレージ
- **Gemini 2.5 Flash API** - AI搭載クエリ処理

### インフラストラクチャ
- **Docker** - コンテナ化されたデプロイメント
- **Google Cloud Run** - サーバーレスコンテナプラットフォーム
- **Terraform** - GCPリソースのInfrastructure as Code
- **Cloud Build** - CI/CDパイプライン自動化
- **GitHub Codespaces** - クラウド開発環境サポート
- **Nginx** - 本番Webサーバー（フロントエンド）

## 🚀 クイックスタート

### 前提条件
- Python 3.9+
- Node.js 18+
- BigQueryアクセス権限付きGoogle Cloudプロジェクト
- Gemini APIキー

### 環境設定

backendディレクトリに`.env`ファイルを作成：

```env
GCP_PROJECT_ID=<project_id>
BIGQUERY_DATASET_ID=<dataset_name>
BIGQUERY_BATTING_STATS_TABLE_ID=fact_batting_stats_with_risp
BIGQUERY_PITCHING_STATS_TABLE_ID=fact_pitching_stats
GEMINI_API_KEY=<your_gemini_api_key>
GOOGLE_APPLICATION_CREDENTIALS=<path_to_service_account_json>
VITE_APP_PASSWORD=<your_app_password>
```

### 開発

#### フロントエンドセットアップ
```bash
cd frontend
npm install
npm run dev          # 開発サーバー起動（ポート5173）
npm run build        # 本番ビルド
npm run lint         # ESLint実行
npm run preview      # 本番ビルドプレビュー
```

#### バックエンドセットアップ
```bash
cd backend
pip install -r requirements.txt
# 適切なモジュール解決での開発：
PYTHONPATH=/path/to/diamond-lens python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 本番デプロイメント

#### Dockerビルド
```bash
# フロントエンド
cd frontend
docker build -t diamond-lens-frontend .

# バックエンド
cd backend  
docker build -t diamond-lens-backend .
```

#### Google Cloud Run とCI/CD
プロジェクトはTerraformインフラ管理を統合した自動CI/CDパイプライン用にCloud Buildを使用しています。

詳細なセットアップ手順は [TERRAFORM_INTEGRATION_GUIDE.md](TERRAFORM_INTEGRATION_GUIDE.md) を参照してください。

## 📡 API ドキュメント

### メインエンドポイント
**POST** `/api/v1/qa/player-stats`

#### リクエスト形式
```json
{
  "query": "大谷翔平の2024年の打率は？",
  "season": 2024
}
```

#### レスポンス形式
```json
{
  "answer": "大谷翔平の2024年シーズンの打率は.310でした。",
  "isTable": false,
  "isTransposed": false,
  "tableData": null,
  "columns": null,
  "decimalColumns": [],
  "grouping": null,
  "stats": {
    "games": "150",
    "hits": "186",
    "at_bats": "600"
  }
}
```

#### その他のエンドポイント
- **GET** `/health` - ヘルスチェックエンドポイント
- **GET** `/debug/routes` - デバッグルート一覧
- **GET** `/test` - バックエンド接続テスト
- **POST** `/test-post` - POSTエンドポイントテスト

## 🔧 設定

### サポートされているクエリタイプ
- **チャットモード**: 打撃・投手に関する自然言語処理
- **クイック質問**: 一般的な統計用の事前設定クエリ
- **カスタムアナリティクス**: 高度な状況別分析：
  - `batting_splits` - 得点圏、満塁、カスタム状況
  - `statcast_advanced` - 打球速度、打球角度、ハードヒット率
  - キャリア集計と年次推移分析

### BigQuery連携
- **シングルトンパターン**: `bigquery_service.py`での効率的なBigQueryクライアント管理
- **プロジェクト**: GCPプロジェクト`<your-project-id>`にハードコード
- **認証**: サービスアカウントベース認証が必要

### LLM連携
- **デュアル使用**: クエリパース + レスポンス生成
- **言語**: 英語名正規化を伴う日本語処理
- **形式**: リトライロジック付き構造化JSONレスポンス形式

## 🎨 UI機能

- **ダークテーマ**: 長時間の使用に最適化された永続ダークモード
- **レスポンシブデザイン**: モバイルフレンドリーなインターフェース
- **リアルタイム更新**: タイピングインジケーター付きのライブメッセージ更新
- **パスワード保護**: セキュアなアクセス制御
- **自動スクロール**: 最新メッセージへの自動スクロール
- **ローディング状態**: API呼び出し中の視覚的フィードバック
- **エラーハンドリング**: 優雅なエラー表示と回復

## 🏗️ インフラ管理

### Terraform構成

このプロジェクトはTerraformを使用してGCPインフラをコードとして管理しています：

- **Cloud Run サービス**: バックエンドとフロントエンドのサービス設定
- **BigQuery データセット**: MLB統計データウェアハウス
- **IAM 権限**: サービスアカウントのロールとアクセス制御
- **State管理**: GCSバケットに保存されたリモートState

インフラは再利用可能なモジュールとして構成されています：

```
terraform/
├── modules/
│   ├── cloud-run/         # 再利用可能なCloud Runモジュール
│   ├── bigquery/          # BigQueryデータセットモジュール
│   ├── iam/               # IAM設定モジュール
│   └── secrets/           # Secret Managerモジュール（使用しない）
└── environments/
    └── production/        # 本番環境設定
        └── main.tf        # メインTerraform設定
```

### CI/CDパイプライン

デプロイメントパイプラインはテスト統合されたCloud Buildによって完全に自動化されています：

```
git push → Cloud Buildトリガー → cloudbuild.yaml 実行
  ↓
┌─────────────────────────────────────┐
│ STEP 0: ユニットテスト                │
│  - pytest実行 (49テスト)            │
│  - query_maps設定の検証             │
│  - SQL生成ロジックのテスト            │
│  ⚠️  テスト失敗 → ビルド停止         │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ STEP 1: Terraform (インフラ管理)      │
│  - terraform init                   │
│  - terraform plan                   │
│  - terraform apply (変更がある場合)   │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ STEP 2-4: Backend                   │
│  - Docker build                     │
│  - gcr.io へプッシュ                 │
│  - Cloud Runへデプロイ               │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ STEP 5-7: Frontend                  │
│  - Docker build                     │
│  - gcr.io へプッシュ                 │
│  - Cloud Runへデプロイ               │
└─────────────────────────────────────┘
```

**主な機能:**
- **自動テスト:** 全デプロイ前にユニットテストを実行
- **Fail-fastアプローチ:** テスト失敗時は本番デプロイを防止
- インフラ変更はアプリケーションデプロイメントの前に適用されます
- Terraformはインフラ変更が検出された場合のみ実行されます
- Dockerイメージはインフラ更新後にビルドおよびデプロイされます
- Secretsはセキュリティのため、Terraform外で管理されています

### テスト

プロジェクトには重要なビジネスロジックの包括的なユニットテストが含まれています：

**テストカバレッジ (49テスト):**
- `test_query_maps.py` (21テスト): 設定検証とデータ構造の整合性
- `test_build_dynamic_sql.py` (28テスト): 全クエリタイプのSQL生成ロジック

**ローカルでテスト実行:**
```bash
cd backend
pip install pytest pytest-asyncio
export PYTHONPATH=$(pwd)  # Linux/Mac
set PYTHONPATH=%cd%       # Windows
python -m pytest tests/ -v
```

**テストカテゴリ:**
- クエリタイプ設定の検証
- メトリクスマッピングの整合性
- シーズン打撃/投手成績のSQL生成
- キャリア通算統計クエリ
- 打撃スプリット（得点圏、満塁、イニング別など）
- エッジケース処理とエラー検証

Terraformセットアップと統合手順の詳細は [TERRAFORM_INTEGRATION_GUIDE.md](TERRAFORM_INTEGRATION_GUIDE.md) を参照してください。

## 📁 プロジェクト構造

```
diamond-lens/
├── frontend/                 # Reactフロントエンドアプリケーション
│   ├── src/
│   │   ├── App.jsx          # メインアプリケーションコンポーネント
│   │   ├── main.jsx         # アプリケーションエントリーポイント
│   │   └── index.css        # グローバルスタイル
│   ├── tailwind.config.js   # Tailwind CSS設定
│   ├── package.json         # フロントエンド依存関係
│   └── Dockerfile           # フロントエンドコンテナ
├── backend/                  # FastAPIバックエンドアプリケーション
│   ├── app/
│   │   ├── main.py          # FastAPIアプリケーション
│   │   ├── api/endpoints/   # APIルートハンドラー
│   │   ├── services/        # ビジネスロジックサービス
│   │   └── config/          # 設定とマッピング
│   ├── requirements.txt     # Python依存関係
│   └── Dockerfile           # バックエンドコンテナ
├── terraform/                # Infrastructure as Code
│   ├── modules/             # 再利用可能なTerraformモジュール
│   └── environments/        # 環境別設定
├── CLAUDE.md                # 開発ガイダンス
├── cloudbuild.yaml          # CI/CDパイプライン設定
├── TERRAFORM_INTEGRATION_GUIDE.md  # Terraformセットアップガイド
└── README.md                # 英語版README
```

## 🤝 貢献

このプロジェクトは標準的なGitワークフローに従います：
1. リポジトリをフォーク
2. フィーチャーブランチを作成
3. 変更を実装
4. 十分にテスト
5. プルリクエストを提出

## 📜 ライセンス

このプロジェクトは教育・デモンストレーション目的です。

---

**MLB統計アシスタント v1.0** - AI搭載野球アナリティクスをあなたの手に！🔮⚾