# ADR-011: LangGraph は StrategyAgent のみに残す（Plan-and-Execute + Parallel Fan-Out）

- Status: Accepted
- Date: 2026-05-17
- Deciders: プロジェクトオーナー

## Context（背景・課題）

[[010-chat-orchestrator-replaces-langgraph]] でチャット側の LangGraph 二重構造を畳み、`ChatOrchestrator`（素の Gemini SDK + function calling ループ）へ統合しました。その際、**「LangGraph をプロジェクト全体から全廃するか、特定経路だけ残すか」** という判断が残りました。

チャットと対戦戦略レポートは機能特性が大きく異なります。

| 機能特性 | 適した構造 |
|---|---|
| 自由会話・動的なツール選択・出力形式が可変 | 単一 LLM Orchestrator + function calling（ADR-010） |
| 構造化パイプライン・決定論的 retry・固定スキーマ出力 | LangGraph StateGraph |

対戦戦略レポート機能（`StrategyAgent`）は、打者・投手・対戦傾向を**横断的に分析**し、6 セクションの固定スキーマレポートを生成します。具体的には以下を必要とします。

- 複数ツール（打者成績・投手成績・対戦履歴・球種別分析）の**並列 fan-out 実行**と結果集約。
- 一部ツール失敗時も部分レポートを返す**決定論的な集約・分岐**。
- エラー種別に応じた**境界付き retry**（[[012-classified-bounded-reflection-retries]]）。

これらは「ノードとエッジで明示的に表現された状態機械」が素直に合致する領域で、function calling ループの自然な再試行に委ねるより、`StateGraph` の決定論性が価値を持ちます。

## Decision（決定）

**LangGraph を `StrategyAgent` のみに残し**、チャット経路からは完全に剥がしました（[backend/app/services/agents/strategy_agent.py](../../backend/app/services/agents/strategy_agent.py)）。

`StrategyAgent` は **Plan-and-Execute + Parallel Fan-Out** パターンの 5 ノード `StateGraph` を維持します。

```
planner → parallel_executor → aggregator → (reflection ⇄ planner) → strategist → END
```

#### 「4 ツールをバインドした LLM」とは

bind（バインド）とは、**LLM に「呼べる道具のリスト」を結びつけて渡しておく**ことです（[strategy_agent.py:61-67](../../backend/app/services/agents/strategy_agent.py#L61-L67) の `model.bind_tools(self.tools)`）。バインドされた LLM は、質問を読んで「どの道具を・どの引数で呼ぶか」を**自分で選べる**ようになります。

```
            ┌─────────────────────────────────────────┐
            │   LLM (Gemini) に 4 つの道具を bind        │
            │                                          │
   質問 ──► │  使える道具:                              │
「大谷 vs    │   ① get_batter_stats_tool   （打者成績）   │
  Cole の   │   ② get_pitcher_stats_tool  （投手成績）   │
  戦略を」   │   ③ mlb_matchup_history_tool（過去対戦履歴）│
            │   ④ mlb_matchup_analytics_tool（球種別分析）│
            └───────────────────┬─────────────────────┘
                                ▼
        LLM が「①③④ を呼ぼう」と自分で計画（= planner ノードの仕事）
```

つまり planner は「**4 つのデータ取得関数を持たされ、どれを呼ぶか自分で判断できる状態の Gemini**」が、必要な道具をまとめて選ぶ工程です。

#### 各ノードのデータの流れ

```
  ┌──────────┐  「①打者 ③対戦履歴 ④球種別 を呼べ」という計画（複数ツールを一度に指名）
  │ planner  │ ───────────────────────────────────────────────┐
  └──────────┘  🧠 4ツールbindのLLM                            │
                                                              ▼
  ┌──────────────────┐  3つのツールを“同時に”実行（待ち時間を短縮）
  │ parallel_executor│   ① ──┐
  │                  │   ③ ──┼─► asyncio.gather で並列 ─► 各結果を集める
  │                  │   ④ ──┘    （1つ失敗しても error dict にして他を守る）
  └────────┬─────────┘
           ▼
  ┌──────────────┐  成功/失敗を仕分け
  │ aggregator   │   ・全部失敗 → エラーをセット
  │              │   ・一部でも成功 → そのまま続行（= 部分レポート）
  └──────┬───────┘
         │
         ├─ SQLミス/空結果など“直せる”失敗 ─► ┌────────────┐ 引数を直して
         │                                  │ reflection │ planner へ戻る
         │                                  └─────┬──────┘ （上限2回まで）
         │                                        └──► planner（再計画）
         │
         └─ 成功 or “直しても無駄”な失敗 ──► ┌────────────┐
                                           │ strategist │ 🧠 集めたデータを
                                           └─────┬──────┘ 6セクションの
                                                 ▼         戦略レポートに合成
                                                END
```

- **planner**: 4 ツールをバインドした LLM が、複数ツールの同時呼び出しを計画（`strategy_planner` プロンプト）。
- **parallel_executor**: `asyncio.gather()` + `asyncio.to_thread()` で同期ツールを並列実行し、例外はエラー dict に変換して他ツールの結果を守る。
- **aggregator**: 成功/失敗を仕分け。全失敗時のみエラーをセットし、一部成功なら続行（部分レポート設計）。
- **reflection**: エラー種別・空結果に応じた境界付き再計画（[[012-classified-bounded-reflection-retries]]）。
- **strategist**: `strategy_synthesizer` プロンプトで 6 セクションの戦略レポートを生成。

`StrategyAgent` は `/api/v1/strategy-report/*` および `/tactics` 経路からのみ呼ばれ、`langgraph` 依存はこの 1 ファイルに局所化されます。構造化入力（打者名・投手名・シーズン）からの `run_structured()` も追加済みですが、内部で既存 `run()` を再利用し、ノード・プロンプトには手を入れていません。

## Alternatives Considered（検討した代替案）

- **LangGraph を全廃し StrategyAgent も function calling ループへ移植**: 並列 fan-out・部分集約・境界付き retry を function calling ループ + プロンプト指示で再現する必要があり、決定論性が失われる。横断分析という性質に StateGraph が素直に合致するため、ここでの全廃は割に合わず不採用。
- **StrategyAgent をチャット経路（Supervisor 経由）からも呼べる二系統のまま維持**: ADR-010 でチャット経由を停止し、Strategy エンドポイント経路のみ残す方針と矛盾。結合を残すと「片方の変更が他方を巻き込む」課題が続くため不採用。
- **Cloud Workflows / Step Functions 等の外部オーケストレータに載せ替え**: LLM ノードとツール実行が密に絡む処理を外部オーケストレータに出すとレイテンシと運用が増える。アプリ内 `StateGraph` で十分なため不採用。

## Consequences（結果・トレードオフ）

**良くなったこと**

- 各機能が「特性に合った構造」で動く（チャット=function calling ループ、横断分析=StateGraph）。適材適所の意思決定として説明可能。
- `langgraph` 依存が `strategy_agent.py` に局所化され、チャット側の認知負荷から切り離された。
- 並列 fan-out・部分レポート・境界付き retry という、StateGraph が得意とする決定論的振る舞いを保全。

**悪くなったこと / 新たな負荷**

- プロジェクトに **2 つのエージェント実行モデル（function calling ループ / StateGraph）が併存**し、それぞれの保守知識が要る。
- ツール定義は共通化（`tools/`）したが、Reflection など一部ロジックは経路ごとに異なる（チャットは自然な再試行、Strategy は明示的 Reflection ノード）。
- 旧 LangGraph sub-agent 群（`SupervisorAgent` 等）の物理削除が保留中で、`langgraph` が `strategy_agent.py` のみで使われる状態への収束は Phase 2-G 完了待ち（CLAUDE.md「アーキテクチャ現状」参照）。

## JD Alignment（この募集要件との対応）

- **AG★（multi-agent / LangGraph・hierarchical delegation / tool orchestration）**: JD が `LangGraph` を名指しする要件に直接対応。「どこに LangGraph を残し、どこで畳んだか」を機能特性の判断軸（決定論 vs 自由会話）で語れる。ADR-010 と対で、技術選定の justification を示す中核 ADR。
- 関連: [[012-classified-bounded-reflection-retries]]（Reflection ノードの retry 分類）。

## References

- 設計プラン: [MATCHUP_STRATEGY_REPORT_PLAN.md](../plan_docs/MATCHUP_STRATEGY_REPORT_PLAN.md) / [CHAT_ORCHESTRATOR_REFACTOR_PLAN.md](../plan_docs/CHAT_ORCHESTRATOR_REFACTOR_PLAN.md) §1.2 判断軸
- 実装: [backend/app/services/agents/strategy_agent.py](../../backend/app/services/agents/strategy_agent.py)
- AI レイヤー: [README_ai_architecture.md](../../README_ai_architecture.md) §1 全体像 / §9 Request Lifecycle / §8 Reflection Loop
- 関連 ADR: [[010-chat-orchestrator-replaces-langgraph]], [[012-classified-bounded-reflection-retries]]
