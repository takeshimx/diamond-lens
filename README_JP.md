# Diamond Lens - MLBスタッツアシスタント 🔮⚾

自然言語クエリを通じてメジャーリーグベースボールの統計を探索するAI搭載チャットインターフェース。React、FastAPI、Google Cloud BigQueryで構築。

## 🌟 機能

- **自然言語クエリ**: 日本語で質問してMLB統計の包括的な分析を取得
- **リアルタイムチャットインターフェース**: ローディング状態とメッセージ履歴付きのインタラクティブなチャット体験
- **AI搭載アナリティクス**: Gemini 2.5 Flashを使用したインテリジェントなクエリ解析とレスポンス生成
- **包括的なMLBデータ**: 打撃成績、投手成績、状況別スプリット（得点圏、勝負どころなど）へのアクセス
- **ダークテーマUI**: 長時間の使用に最適化されたモダンでレスポンシブなインターフェース
- **セキュアアクセス**: 認証されたユーザーのためのパスワード保護インターフェース
- **動的SQL生成**: 自然言語からBigQuery SQLへのインテリジェントなマッピング
- **柔軟な出力形式**: ナラティブレスポンスと構造化テーブルの両方をサポート

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
   - GCPプロジェクト `tksm-dash-test-25` のMLB統計テーブルに対して生成されたSQLを実行
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

#### Google Cloud Run
プロジェクトにはGoogle Cloud Runへの自動デプロイメント用の`cloudbuild.yaml`が含まれています。

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
- `season_batting` - リーグ全体のシーズン打撃統計
- `season_pitching` - リーグ全体のシーズン投手統計
- `batting_splits` - 状況別パフォーマンスメトリクス（得点圏、左右別、イニング別など）

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
├── CLAUDE.md                # 開発ガイダンス
├── cloudbuild.yaml          # GCPデプロイメント設定
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