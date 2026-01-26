# Diamond Lens: 自律型マルチステップ・アナリティクス実装計画書

## 1. 概要
本プロジェクトは、現在の単一回答型（1-Pass）システムを、LangGraphを用いた**自律型エージェント（Multi-Step Reasoning）**へと進化させるものです。
既存の堅牢なダイナミックSQL生成ロジック（`ai_service.py`）をエージェントの「ツール」として再定義し、複雑な質問に対して「計画・実行・分析・回答」のループを自律的に回せるようにします。

## 2. 実装フェーズ

### フェーズ 1: 既存ロジックのコンポーネント化 (Tooling)
エージェントが「道具」として扱えるように、現在のサービス層を疎結合にします。
- **[MODIFY] `backend/app/services/ai_service.py`**:
    - LLMの回答生成からデータ取得ロジックを分離。
    - `get_mlb_stats_data` 関数を新設（BigQueryからの生データ返却に特化）。
- **[NEW] ツール定義**:
    - LangChainの `@tool` デコレータを使用し、解析済みパラメータを引数に取るツールを作成。

### フェーズ 2: LangGraph オーケストレーションの実装
推論のコアとなる状態遷移（State Graph）を構築します。
- **[NEW] `backend/app/services/ai_agent_service.py`**:
    - `AgentState` 定義: messages, intermediate_steps, raw_data_store 等。
    - グラフ構築: `Planner` -> `Executor` -> `Analyzer` -> `End` のループ。
- **推論ロジックの改良**:
    - 「A選手とB選手の比較」のような、複数回のツール実行が必要な問いに対応。

### フェーズ 3: 構造化出力とフロントエンド連携
中間ステップの可視化と、APIインターフェースの更新。
- **[NEW] APIエンドポイント**: `POST /api/v1/qa/agentic/query`
- **[MODIFY] フロントエンド (React)**:
    - 思考プロセスのステータス表示（Progress UI）。
    - 取得した生データを元にした動的グラフ（Chart.js等）の出し分け。

## 3. アクションアイテム (詳細)

### バックエンド / AIロジック
- [ ] `ai_service.py` のリファクタリング（回答生成の分離）
- [ ] LangChain/LangGraph 依存関係の追加（`requirements.txt`）
- [ ] `AgentState` クラスと各ノード関数の実装
- [ ] `with_structured_output` によるPydanticモデルでのレスポンス固定

### フロントエンド / UI
- [ ] エージェント専用のチャットフック（`useAgenticChat`）の作成
- [ ] 中間ログ（Thought Log）の表示コンポーネント
- [ ] `chart_type` （bar, line, scatter）に応じた動的レンダリング

## 4. 技術的メリット (FDE的視点)
1. **ハイブリッド・アプローチ**: 100% LLM生成のSQLではなく、既存の検証済みSQLビルダをツール化することで、生成AIの不確実性を抑えつつ複雑な推論を可能にする。
2. **トレーサビリティ**: 思考プロセスを可視化することで、ユーザーが回答の根拠を理解でき、信頼性が向上する。
3. **拡張性**: 将来的に別のデータソースやツールを追加する際、グラフのノードを追加するだけで対応可能。

## 5. 次のステップ
1. `requirements.txt` に `langgraph`, `langchain-google-genai` 等を追加。
2. `ai_service.py` からデータ取得のみを行う `get_raw_stats` 関数を抽出。
3. `ai_agent_service.py` のプロトタイプ作成。
