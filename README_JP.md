# Diamond Lens - MLBスタッツアシスタント 🔮⚾

自然言語クエリと高度なカスタムアナリティクスを通じてメジャーリーグベースボールの統計を探索するAI搭載アナリティクスインターフェース。React、FastAPI、Google Cloud BigQueryで構築。

## 🌟 機能

### 1. 自然言語Q&Aインターフェース（フルスタック）
**ステータス**: ✅ フロントエンドUI付き本番環境対応

- **💬 チャットモード**: 日本語での自然言語クエリとAI搭載レスポンス
- **⚡ クイック質問**: 事前定義された一般的な野球クエリで即座に結果を取得
- **⚙️ カスタムクエリビルダー**: カスタム状況フィルターを使った高度なアナリティクス
- **🤖 自律型エージェントモード (NEW)**: LangGraphを使用した複数ステップのデータ探索とプロフェッショナルな推論・分析

**アナリティクス機能**:
- **打撃統計**: シーズン成績、スプリット、高度なStatcastメトリクス
- **投手統計**: 防御率、WHIP、三振率、高度なアナリティクス
- **状況別スプリット**: 得点圏成績、満塁、カスタムゲーム状況
- **キャリアアナリティクス**: 複数シーズントレンド分析とキャリア集計
- **ビジュアルチャート**: 年次推移チャートとKPIサマリーカード
- **高度フィルター**: イニング別、カウント別、投手対戦別分析

### 2. 統計分析 & 予測モデリング（フルスタック）
**ステータス**: ✅ フロントエンドUI付き本番環境対応

**機能**:
- **📊 インタラクティブダッシュボード**: ビジュアル分析によるリアルタイム勝率予測
- **多変量回帰モデル**: チーム勝率を94.2%の精度で予測（R² = 0.942）
- **仮説検定**: T検定、効果量分析（Cohen's d）、信頼区間
- **多重共線性分析**: 最適なモデルパフォーマンスのためのVIFベース変数選択
- **モデル評価**: 包括的なメトリクス（R²、RMSE、MAE）と回帰係数

**フロントエンド機能**:
- **入力コントロール**: OPS（0.500-1.000）、ERA（2.00-6.00）、被本塁打数（100-250）のインタラクティブスライダー
- **予測結果**: 勝率パーセンテージ、162試合での期待勝利数、パフォーマンスティア分類
- **感度分析**: ERAと被本塁打数を固定した場合のOPSが勝率に与える影響を示す折れ線グラフ
- **モデル透明性**: R²、MSE、MAEメトリクスを表示してモデル評価を可視化

**APIエンドポイント**:
- `GET /api/v1/statistics/predict-winrate` - OPS、ERA、被本塁打から勝率を予測
- `GET /api/v1/statistics/model-summary` - モデル評価メトリクスと回帰式を取得
- `GET /api/v1/statistics/ops-sensitivity` - OPSが勝率に与える影響を分析

**技術**: React、Recharts、FastAPI、BigQuery ML、scikit-learn、scipy

**分析ノートブック**:
- `analysis/hypothesis_testing.ipynb` - 可視化付き統計的仮説検定
- `analysis/regression_analysis.ipynb` - VIF分析付き多変量回帰

### 3. 選手セグメンテーション分析（フルスタック）
**ステータス**: ✅ フロントエンドUI付き本番環境対応

**機能**:
- **🎯 K-meansクラスタリング**: 教師なし学習による選手タイプの自動分類
- **多次元分析**: 4-6個のパフォーマンス指標に基づいて選手をセグメント化
- **インタラクティブ可視化**: クラスタベースの色分け散布図
- **クラスタプロファイリング**: 各選手セグメントの統計サマリー

**フロントエンド機能**:
- **選手タイプ切り替え**: 打者と投手の分析を切り替え
- **散布図可視化**:
  - 打者: OPS vs ISOで4クラスタ（スーパースター強打者、エリートコンタクト型、堅実なレギュラー、苦戦中）
  - 投手: ERA vs K/9で4クラスタ（三振特化型、エリートバランス型、中堅、苦戦中）
- **インタラクティブツールチップ**: ホバー時に選手名、チーム、主要統計を表示
- **クラスタサマリーテーブル**: セグメント別の平均メトリクスと選手数

**クラスタリング機能**:
- **打者セグメンテーション**: OPS、ISO、K%、BB%（n=4クラスタ）
- **投手セグメンテーション**: ERA、K/9、BB/9、HR/9、WHIP、GB%（n=4クラスタ）
- **標準化**: 最適なクラスタリングパフォーマンスのための特徴量スケーリング
- **VIF分析**: 意味のあるクラスタを確保するための多重共線性検出

**APIエンドポイント**:
- `GET /api/v1/segmentation/batters` - K-meansクラスタリングによる打者セグメンテーション取得
- `GET /api/v1/segmentation/pitchers` - K-meansクラスタリングによる投手セグメンテーション取得

**技術**: React、Recharts、scikit-learn、pandas、FastAPI

**分析ノートブック**:
- `analysis/player_segmentation.ipynb` - 可視化付きK-meansクラスタリング分析

**ビジネス応用**:
- **スカウティング効率化**: パフォーマンスプロファイルによる見込み選手の分類

### 4. 自律型アナリストエージェント（Supervisor + LangGraph）
**ステータス**: ✅ LangGraphで動作する特化型エージェントを備えた本番環境対応

**機能**:
- **🧠 マルチエージェント・オーケストレーション**: `SupervisorAgent` を使用して、クエリを特化型エージェント（`StatsAgent`, `MatchupAgent`）にインテリジェントにルーティングします。各エージェントは **LangGraph** によって制御されています。
- **🔍 推論プロセスの可視化**: 特化型グラフの各ノードにおける内部思考プロセス（Reasoning Steps）をリアルタイム表示。
- **📊 アダプティブUI**: 取得データに基づいて、ナラティブレポート、インタラクティブチャート、データテーブルを自動的に切り替え。
- **⚔️ 特化型エージェント**:
  - **StatsAgent**: チーム/選手のシーズン成績、トレンド、グループ比較の専門家。
  - **MatchupAgent**: 打者 vs 投手の直接対決アナリティクスと過去の実績の専門家。
- **🏆 プロフェッショナルレポート**: 見出し、箇条書き、深い洞察を備えた構造化されたアナリストレポートを生成。
- **⚖️ フェイルセーフ生成**: 文の断片を防ぎ、完全で自然な日本語を保証するためのコードレベルのガードレール。
- **🔄 Reflection Loop（自己修正）**: SQLエラーや空結果を検知し、原因を分析してパラメータを修正し再試行する自律的エラー回復メカニズム（最大2回リトライ）。リトライ可能なエラー（構文エラー、空結果）とリトライ不可エラー（認証、タイムアウト、スキーマエラー）をインテリジェントに分類し、無駄なリトライを回避。

### 5. MLOps: プロンプトバージョニング、LLM I/Oロギング＆評価ゲート
**ステータス**: ✅ 本番環境対応

**機能**:
- **📝 プロンプトバージョニング**: LLMプロンプトをバージョン付きテキストファイル（`parse_query_v1.txt`, `routing_v1.txt`）として外部化し、`prompt_registry.py`で管理。コード変更なしでプロンプト改善が可能
- **📊 LLM I/Oロギング**: 全LLMインタラクション（クエリ、パース結果、レイテンシ、エラー）を`llm_logger_service.py`経由でBigQueryに非同期ロギング。可観測性とドリフト検出に活用
- **🚦 LLM評価ゲート**: ゴールデンデータセット（`golden_dataset.json`）に対してLLMを実行し、精度が80%を下回った場合にデプロイを停止するCI/CD品質ゲート

### 6. Human-in-the-Loop（HITL）フィードバックシステム
**ステータス**: ✅ 本番環境対応

**機能**:
- **👍👎 ユーザーフィードバックUI**: 全AI回答にThumbs Up/Downボタンを配置し、Bad評価時は詳細フィードバックフォームを表示
- **📋 フィードバックカテゴリ**: 構造化されたカテゴリ分類（`inaccurate`, `slow`, `irrelevant`, `wrong_player`, `wrong_stats`）と自由記述の理由欄
- **🗄️ BigQueryロギング**: フィードバック（評価・カテゴリ・理由）をLLMインタラクションログと共にBigQueryに記録
- **🔄 ゴールデンデータセットパイプライン**: ユーザーフィードバックからLLM精度を継続的に改善する3ステップワークフロー

**HITLフィードバックループ**:
```
ユーザーが回答を 👎 評価 + カテゴリ選択 + 理由記入
         │
         ▼
  BigQuery ログ（フィードバック記録）
         │
  ┌──────┴───────┐
  │   抽出        │  python backend/scripts/extract_golden_dataset.py
  │   bad クエリ  │  → pending_review.json（TODOプレースホルダー付き）
  └──────┬───────┘
         ▼
  ┌──────┴───────┐
  │  人間レビュー  │  開発者が正しい expected 値を記入
  │  （手動）     │  → reviewed: true に変更
  └──────┬───────┘
         ▼
  ┌──────┴───────┐
  │   承認        │  python backend/scripts/approve_to_golden.py
  │   → golden    │  → golden_dataset.json（テストケースが増加）
  └──────┴───────┘
         ▼
  CI/CD 評価ゲートが拡張されたゴールデンデータセットで実行
```

**APIエンドポイント**:
- `POST /api/v1/qa/feedback` - ユーザーフィードバック送信（評価・カテゴリ・理由）

### 技術機能
- **AI搭載処理**: Gemini 2.5 Flashを使用したクエリ解析とレスポンス生成
- **リアルタイムインターフェース**: ローディング状態とライブ更新付きのインタラクティブ体験
- **MCPサーバー対応**: Model Context Protocol経由でClaude DesktopやCursorから直接MLB統計にアクセス
- **大文字小文字非依存検索**: 柔軟な選手名マッチング
- **ダークテーマUI**: 長時間使用に最適化されたモダンでレスポンシブなインターフェース
- **セキュアアクセス**: Firebase Authentication（Googleログイン）とサーバーサイドトークン検証
- **SQLインジェクション対策**: 入力検証とパラメータ化クエリによる多層セキュリティ

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
   - **セキュリティ**: SQLインジェクション攻撃を防ぐためパラメータ化クエリを使用

3. **📊 BigQueryデータ取得**
   - GCPプロジェクト `project-id` のMLB統計テーブルに対して生成されたSQLを実行
   - メインテーブル：`fact_batting_stats_with_risp`、`fact_pitching_stats`
   - スプリット専用テーブル：`tbl_batter_clutch_*`、`mart_batter_inning_stats`など

4. **💬 LLMレスポンス生成** (`ai_service._generate_final_response_with_llm`)
   - 構造化データを自然な日本語レスポンスに変換
   - ナラティブ（`sentence`）と表形式（`table`）の出力形式の両方をサポート

5. **🤖 自律型マルチエージェント推論** (`app/services/agents/`)
   - **Supervisorアーキテクチャ**: `SupervisorAgent` を介して、クエリのルーティングとデータ取得を分離。
   - **特化型エージェント**: 
     - `StatsAgent`: 一般的な統計クエリとトレンド分析を担当。
     - `MatchupAgent`: 特定の選手間対決の履歴比較を担当。
   - **LangGraphの実装**: 各エージェントが独自の「Oracle」（計画）、「Executor」（データ取得）、「Synthesizer」（最終報告）ループを維持。
   - **フィードバックループ**: 最初のデータ取得が不十分な場合、エージェントが自己修正して複数のツール呼び出しを実行。
   - **Reflection Loop**: 各エージェントに`reflection`ノードを追加。Executor実行時のエラー（SQL構文エラー、空結果）を検知し、診断コンテキストをLLMにフィードバックして自己修正。無限ループ防止のための最大リトライ制限付き。
   - **統合UI**: 構造化されたチャート/テーブルメタデータをフロントエンドコンポーネントに直接流し込み。

### 主要設定システム
- **`query_maps.py`**: すべてのクエリタイプとメトリクスマッピングの中央設定
- **`QUERY_TYPE_CONFIG`**: クエリタイプをテーブルスキーマとカラムマッピングにマップ
- **`METRIC_MAP`**: セマンティックメトリクス名を実際のデータベースカラム名に翻訳
- 異なるスプリットコンテキスト間での複雑なメトリクスマッピングをサポート

## 🛠 技術スタック

### フロントエンド
- **React 19.1.1** - 最新機能を備えたモダンReact
- **Vite 7.1.2** - 高速ビルドツールと開発サーバー
- **Firebase SDK** - Googleログイン認証
- **Tailwind CSS 4.1.11** - ダークモード対応のユーティリティファーストCSSフレームワーク
- **Lucide React 0.539.0** - 美しいアイコンライブラリ
- **ESLint** - コードリンティングとフォーマッティング

### バックエンド
- **FastAPI** - モダンなPython Webフレームワーク
- **Uvicorn** - 本番デプロイメント用ASGIサーバー
- **Firebase Admin SDK** - サーバーサイド認証・トークン検証
- **MCPサーバー** - Claude Desktop/Cursor統合用Model Context Protocolサーバー
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
```

frontendディレクトリに`.env`ファイルを作成：

```env
VITE_FIREBASE_API_KEY=<your_firebase_api_key>
VITE_FIREBASE_AUTH_DOMAIN=<your_project>.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=<your_project_id>
VITE_FIREBASE_STORAGE_BUCKET=<your_project>.firebasestorage.app
VITE_FIREBASE_MESSAGING_SENDER_ID=<your_sender_id>
VITE_FIREBASE_APP_ID=<your_app_id>
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

---

### 自律型エージェントAPI (LangGraph)

**POST** `/api/v1/qa/agentic-stats`

LangGraphを活用した高度な複数ステップ分析。複雑な推論と自動ビジュアライゼーションをサポートします。

#### リクエスト形式
```json
{
  "query": "大谷翔平とアーロン・ジャッジの2024年の成績を比較してチャートにして",
  "session_id": "optional-uuid"
}
```

#### レスポンス形式
```json
{
  "query": "...",
  "answer": "...",
  "steps": [
    {"thought": "...", "tool_call": "...", "status": "planning"},
    {"thought": "...", "status": "executing"}
  ],
  "is_agentic": true,
  "isChart": true,
  "chartData": [...],
  "processing_time_ms": 12500
}
```

---

### 自律型エージェントストリーミングAPI (Server-Sent Events)

**POST** `/api/v1/qa/agentic-stats-stream`

エージェントAPIのリアルタイムストリーミング版。Server-Sent Events (SSE)を使用して、エージェントの推論ステップとLLMトークンを生成時にリアルタイム配信します。

#### リクエスト形式
```json
{
  "query": "大谷翔平の2024年の打率は？",
  "session_id": "optional-uuid"
}
```

#### レスポンス形式 (SSEストリーム)
```
event: session_start
data: {"type":"session_start","session_id":"...","query":"..."}

event: routing
data: {"type":"routing","agent_type":"batter","message":"batterエージェントにルーティングしました"}

event: state_update
data: {"type":"state_update","node":"oracle","status":"started","message":"質問を分析しています"}

event: token
data: {"type":"token","content":"大谷","node":"synthesizer"}

event: final_answer
data: {"type":"final_answer","answer":"大谷翔平選手は2024年シーズンに打率.310を記録しました。","isTable":false,...}

event: stream_end
data: {"type":"stream_end","message":"処理が完了しました"}
```

#### イベントタイプ
- `session_start`: セッション初期化
- `routing`: エージェントルーティング決定
- `state_update`: エージェントノード状態変化 (oracle, executor, synthesizer)
- `tool_start/tool_end`: ツール実行イベント
- `token`: LLMトークンストリーミング（リアルタイム応答生成）
- `final_answer`: メタデータ付き完全な応答
- `stream_end`: ストリーム完了
- `error`: 処理中にエラー発生

#### フロントエンド統合例
```javascript
const response = await fetch('/api/v1/qa/agentic-stats-stream', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({query: "..."})
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const {done, value} = await reader.read();
  if (done) break;

  const text = decoder.decode(value);
  // SSE形式をパース: "event: <type>\ndata: <json>\n\n"
}
```

---

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
- **Firebase認証**: Googleログインによるサーバーサイドトークン検証
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
│ STEP 1: スキーマ検証GATE             │
│  - query_maps.py設定の検証          │
│  - BigQueryスキーマとの比較          │
│  - カラム存在チェック                │
│  ⚠️  不一致 → ビルド停止             │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ STEP 1.5: LLM評価GATE              │
│  - ゴールデンデータセットでLLMを実行  │
│  - パース精度を評価（≧80%）          │
│  - 重要フィールドをチェック           │
│  ⚠️  精度低下 → ビルド停止           │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ STEP 2: Terraform (インフラ管理)      │
│  - terraform init                   │
│  - terraform plan                   │
│  - terraform apply (変更がある場合)   │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ STEP 3: Backendビルド&プッシュ       │
│  - Docker build                     │
│  - gcr.io へプッシュ                 │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ STEP 4: Backendセキュリティスキャン  │
│  - Trivy脆弱性スキャン              │
│  - HIGH/CRITICAL CVEチェック        │
│  ⚠️  脆弱性検出 → ビルド停止         │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ STEP 5: Backendデプロイ              │
│  - Cloud Runへデプロイ               │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ STEP 6-7: Frontendビルド&プッシュ    │
│  - Docker build                     │
│  - gcr.io へプッシュ                 │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ STEP 8: Frontendセキュリティスキャン │
│  - Trivy脆弱性スキャン              │
│  - HIGH/CRITICAL CVEチェック        │
│  ⚠️  脆弱性検出 → ビルド停止         │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ STEP 9: Frontendデプロイ             │
│  - Cloud Runへデプロイ               │
└─────────────────────────────────────┘
```

**主な機能:**
- **自動テスト:** 全デプロイ前にユニットテストを実行
- **スキーマ検証ゲート:** `query_maps.py`が本番BigQueryスキーマと一致することを保証
- **LLM評価ゲート:** ゴールデンデータセットに対するLLMパース精度をデプロイ前に検証
- **セキュリティスキャン:** TrivyでDockerイメージのHIGH/CRITICAL脆弱性をスキャン
- **Fail-fastアプローチ:** テスト、スキーマ、LLM精度、またはセキュリティ失敗時は本番デプロイを防止
- インフラ変更はアプリケーションデプロイメントの前に適用されます
- Terraformはインフラ変更が検出された場合のみ実行されます
- Dockerイメージはインフラ更新後にビルドおよびデプロイされます
- Secretsはセキュリティのため、Terraform外で管理されています

### セキュリティ

アプリケーションはSQLインジェクション、不正アクセス、およびその他の攻撃から保護するための複数層のセキュリティを実装しています：

**セキュリティ対策:**

0. **Firebase認証**:
   - フロントエンド: Firebase SDKによるGoogleログイン（`signInWithPopup` + `GoogleAuthProvider`）
   - バックエンド: Firebase Admin SDKによるサーバーサイドトークン検証（`firebase-admin`）
   - Pure ASGIミドルウェア（`FirebaseAuthMiddleware`）が全APIリクエストの`Authorization: Bearer <token>`を検証
   - 公開パス（`/health`, `/docs`等）は認証対象外
   - ユーザーID・メールをエンドポイントに伝播し、LLMログにユーザー単位で記録
   - Content Security Policy（CSP）でGoogle/Firebase認証ドメインを許可

1. **入力検証** (`_validate_query_params`):
   - SQL生成前にLLMが生成したすべてのパラメータを検証
   - SQLキーワード（SELECT、UNION、DROPなど）をチェック
   - 選手名に対して文字ホワイトリストを適用
   - データ型、範囲、形式を検証
   - 悪意のあるパターン（例: `' OR '1'='1`）を拒否

2. **パラメータ化クエリ**:
   - すべてのユーザー入力をBigQueryクエリパラメータとして渡す
   - SQL構造とデータ値を分離
   - データベースレベルでインジェクション攻撃を防止
   - 文字列連結の代わりにプレースホルダー（例: `@player_name`）を使用

3. **ホワイトリストベースORDER BY**:
   - ORDER BY句は`METRIC_MAP`から事前定義されたカラムのみを使用
   - ユーザー入力を直接ORDER BY句に使用しない

**テストカバレッジ:**
- `test_security.py`: SQLインジェクション攻撃パターンと入力検証
- 悪意のある入力をブロックし、正当な入力を許可することをテストで検証

### テスト

プロジェクトには重要なビジネスロジックの包括的なユニットテストが含まれています：

**テストカバレッジ (73テスト):**
- `test_query_maps.py` (21テスト): 設定検証とデータ構造の整合性
- `test_build_dynamic_sql.py` (28テスト): 全クエリタイプのSQL生成ロジック
- `test_security.py` (13テスト): SQLインジェクション防止と入力検証
- `test_reflection_loop.py` (11テスト): Reflection Loop自己修正ロジック、エラー分類、Executor空結果検出

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

### スキーマ検証

スキーマ検証GATEはアプリケーション設定とデータベース間のデータ整合性を保証します：

**検証内容:**
- `query_maps.py`で参照される全テーブルがBigQueryに存在するか
- 必須カラム（`year_col`, `player_col`, `month_col`）が各テーブルに存在するか
- 全`available_metrics`カラムが実際のテーブルスキーマに存在するか
- 全`METRIC_MAP`カラムマッピングが有効なカラムを指しているか

**ローカルで検証実行:**
```bash
cd backend
export GCP_PROJECT_ID=your-project-id
export BIGQUERY_DATASET_ID=your-dataset-id
python scripts/validate_schema_config.py
```

**検証失敗時:**
- CI/CDパイプラインが即座に停止（コストのかかるビルドステップの前に）
- エラーメッセージで欠落カラムを表示
- 対処方法: `query_maps.py`またはBigQueryスキーマを一致させる

このゲートはスキーマ不一致による実行時エラーを防ぎ、設定バグを早期に検出します。

### セキュリティスキャン

コンテナイメージはデプロイ前にTrivyを使用して脆弱性スキャンされます：

**スキャン対象:**
- OSパッケージ（Debian, Alpineなど）
- アプリケーション依存関係（Pythonパッケージ、npmパッケージ）
- 既知のCVE（Common Vulnerabilities and Exposures）
- 深刻度レベル：HIGHとCRITICALのみ

**スキャンプロセス:**
```
Dockerイメージビルド → GCRへプッシュ → Trivyスキャン → デプロイ（脆弱性なしの場合）
```

**脆弱性検出時:**
- CI/CDパイプラインが即座に停止（デプロイ前）
- Trivyが脆弱性のあるパッケージを報告
- 対処方法: ベースイメージまたは依存関係を更新

**チェック内容:**
- Backendイメージ: Python依存関係、OSパッケージ
- Frontendイメージ: Node.js依存関係、nginx、OSパッケージ

これにより既知の高深刻度脆弱性が本番環境に到達しないことを保証します。

### モニタリング & アラート

アプリケーションはインフラストラクチャ層とアプリケーション層全体で包括的なモニタリングを実装しています：

#### インフラストラクチャ層モニタリング

**アップタイムチェック:**
- Backend `/health` エンドポイント: 3つのグローバルリージョン（USA、EUROPE、ASIA_PACIFIC）から60秒間隔でチェック
- Frontend `/` エンドポイント: 3つのグローバルリージョンから60秒間隔でチェック
- SSL検証とHTTPS強制

**アラートポリシー:**
- **サービスダウン**: アップタイムチェックが60秒間連続で失敗した場合にトリガー
- **高メモリ使用率**: Cloud Runメモリが5分間80%を超えた場合にアラート
- **高CPU使用率**: Cloud Run CPUが5分間80%を超えた場合にアラート
- **通知**: 解決後30分で自動クローズするメールアラート

**Terraform設定:**
```bash
cd terraform/environments/production
terraform apply -var="notification_email=your-email@example.com"
```

#### アプリケーション層モニタリング

**追跡されるカスタムメトリクス:**
- `api/latency`: エンドポイント別リクエストレイテンシ（ms）
- `api/errors`: エンドポイントとエラータイプ別エラーカウント
- `query/processing_time`: クエリタイプ別クエリ処理時間（ms）
- `bigquery/latency`: クエリタイプ別BigQuery実行時間（ms）

**構造化ログ:**
- Google Cloud Loggingと互換性のあるJSON形式ログ
- Cloud Loggingによる自動解析とインデックス作成
- 検索可能フィールド: `timestamp`、`severity`、`message`、`query_type`、`latency_ms`、`error_type`

**エラー分類:**
- `validation_error`: 入力検証エラー
- `bigquery_error`: データベースクエリエラー
- `llm_error`: AIモデル処理エラー
- `null_response`: サービスからの空レスポンス

**ログ深刻度レベル:**
- `DEBUG`: 詳細なデバッグ情報
- `INFO`: 通常の操作イベント（リクエスト、完了）
- `WARNING`: 重大ではない問題
- `ERROR`: 注意が必要なエラーイベント
- `CRITICAL`: 即座の対応が必要な重大な障害

**ログとメトリクスの表示:**
```bash
# Cloud Logging
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Cloud Monitoring Metrics Explorer
# 移動先: Cloud Console → Monitoring → Metrics Explorer
# カスタムメトリクス: custom.googleapis.com/diamond-lens/*
```

Terraformセットアップと統合手順の詳細は [TERRAFORM_INTEGRATION_GUIDE.md](TERRAFORM_INTEGRATION_GUIDE.md) を参照してください。

## 📁 プロジェクト構造

```
diamond-lens/
├── frontend/                 # Reactフロントエンドアプリケーション
│   ├── src/
│   │   ├── App.jsx          # メインアプリケーションコンポーネント
│   │   ├── firebase.js      # Firebase SDK設定
│   │   ├── hooks/useAuth.js # Googleログイン認証フック
│   │   ├── main.jsx         # アプリケーションエントリーポイント
│   │   └── index.css        # グローバルスタイル
│   ├── tailwind.config.js   # Tailwind CSS設定
│   ├── package.json         # フロントエンド依存関係
│   └── Dockerfile           # フロントエンドコンテナ
├── backend/                  # FastAPIバックエンドアプリケーション
│   ├── app/
│   │   ├── main.py          # FastAPIアプリケーション
│   │   ├── api/endpoints/   # APIルートハンドラー
│   │   ├── middleware/       # ASGIミドルウェア
│   │   │   ├── firebase_auth.py    # Firebaseトークン検証ミドルウェア
│   │   │   └── request_id.py       # リクエストID追跡
│   │   ├── services/        # ビジネスロジックサービス
│   │   │   ├── ai_service.py       # AIクエリ処理
│   │   │   ├── bigquery_service.py # BigQueryクライアント
│   │   │   ├── firebase_service.py # Firebase Admin SDK初期化
│   │   │   ├── llm_logger_service.py # LLM I/Oロギング（user_id対応）
│   │   │   └── monitoring_service.py # カスタムメトリクス
│   │   ├── prompts/         # バージョン管理されたLLMプロンプトテンプレート
│   │   │   ├── parse_query_v1.txt  # クエリパースプロンプト
│   │   │   └── routing_v1.txt      # エージェントルーティングプロンプト
│   │   ├── utils/           # ユーティリティ関数
│   │   │   └── structured_logger.py # JSONログ
│   │   └── config/          # 設定とマッピング
│   │       └── prompt_registry.py  # プロンプトバージョン管理
│   ├── tests/               # ユニットテスト + ゴールデンデータセット
│   │   ├── golden_dataset.json    # LLM評価テストケース
│   │   └── pending_review.json    # HITLフィードバック レビュー待ち
│   ├── scripts/             # 検証・評価スクリプト
│   │   ├── extract_golden_dataset.py  # BigQueryからbad評価クエリを抽出
│   │   ├── approve_to_golden.py       # レビュー済みケースをゴールデンデータセットに昇格
│   │   └── evaluate_llm_accuracy.py   # CI/CD LLM精度ゲート
│   ├── requirements.txt     # Python依存関係
│   └── Dockerfile           # バックエンドコンテナ
├── terraform/                # Infrastructure as Code
│   ├── modules/             # 再利用可能なTerraformモジュール
│   │   ├── cloud-run/       # Cloud Runサービスモジュール
│   │   ├── bigquery/        # BigQueryデータセットモジュール
│   │   ├── monitoring/      # モニタリング & アラートモジュール
│   │   └── iam/             # IAM設定モジュール
│   └── environments/        # 環境別設定
│       └── production/      # 本番環境
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