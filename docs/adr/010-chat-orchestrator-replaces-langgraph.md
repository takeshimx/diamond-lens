# ADR-010: ChatOrchestrator (function calling, 1 LLM call) が Supervisor + 4 LangGraph sub-agent を置換する

> **用語**: 本 ADR の「function calling ループ」は、google-genai SDK の function calling（`types.Tool(function_declarations=...)` を渡し、レスポンスの `part.function_call` を検出して実行・結果返却を繰り返す）を指す。他社 SDK で「tool use」と呼ばれる概念と同一だが、本プロジェクトは Gemini を使うため SDK の実名 **function calling** に統一する。

- Status: Accepted
- Date: 2026-05-17
- Deciders: プロジェクトオーナー

## Context（背景・課題）

チャット機能のバックエンドは、当初の structured RAG から multi-agent orchestration へと発展する過程で、**`SupervisorAgent` が routing prompt で `agent_type` を決定し、Batter / Pitcher / Matchup / Stats / Strategy の専用 sub-agent へ振り分け、各 sub-agent がさらに自前の LangGraph (`oracle → executor → reflection → synthesizer`) を持つ** という二重構造になっていました（[CHAT_ORCHESTRATOR_REFACTOR_PLAN.md](../plan_docs/CHAT_ORCHESTRATOR_REFACTOR_PLAN.md) §2.1）。

### 設計の 3 世代変遷（なぜ作り直したか）

チャット経路は **3 世代**を経て現在の `ChatOrchestrator` に到達しました。重要なのは、この変遷は「前世代が壊れていたから次へ進んだ」という線形な必然ではない点です。**第1世代は正しく動いており、第2世代はスコープ拡大に向けた設計判断（一部は学習・実験を兼ねる）として導入し、その結果が芳しくなかったため第3世代へ収束**しました。各世代を後知恵で美化せず、実際に起きたことをそのまま記録します。

```
第1世代  Structured RAG                  司令塔 = アプリ
  user query
     │
     ▼  🧠 LLM が NLU（自然文 → {query_type, metrics, name, season...} を JSON 抽出）
     ▼  アプリが固定ロジックでパラメータ化 SQL を構築（テーブル/カラムは query_maps・METRIC_MAP 辞書由来、値は @param バインド、ホワイトリスト検証）
     ▼  BQ（ground truth）を叩く
     ▼  🧠 LLM が取得済みデータから回答生成
  回答
  ◎ 基本的なバッター/ピッチャースタッツのカテゴリーでは正しく動いていた。
    LLM は SQL を一文字も生成せず（パラメータ抽出のみ）、カラム名は辞書由来＝捏造の余地なし。
    ＝この世代に hallucination は実在しなかった。弱点があるとすれば「複数データ源の横断合成が苦手」
    「メトリクス定義が query_maps とアプリ側 SQL 生成に二重化」程度で、いずれも移行の決め手ではない。

           ↓ 動機は欠陥の修正ではなく「スコープ拡大」。split stats・対戦戦略・（構想として）
             チームレベル等の追加カテゴリーを単一チャットで扱いたい。カテゴリーが増えるなら
             統括役（Supervisor）が専門 sub-agent に役割分担して並行・独立に動かす方が良いと考えた。
             「複雑化したら hallucination が起きるかも」という予防的懸念もあったが、根拠は薄かった。

第2世代  Supervisor + sub-agent (LangGraph)   司令塔 = 多数の LLM（分散）
  user query
     ▼  🧠 LLM #1 routing（agent_type 判定）
     ▼  🧠 LLM #2 sub-agent oracle（質問を再解釈して計画）
     ▼  🧠 LLM #3 ツール内 _parse_query_with_llm（自然文を“もう一度”パース）
     ▼  🧠 LLM #4 synthesizer（生データ → 回答）
  回答
  ✗ 期待に反し、同じ質問を 4 回別々の LLM が解釈 →「伝言ゲーム」で意図がズレ、回答精度が低下。
    役割分担はスコープ拡大の手段として逆効果だった。どこでズレたか追えずデバッグ困難。
    LLM 4 回でレイテンシ・コストも増。Structured RAG へ戻すことも検討した。

           ↓ 戻すのではなく「解釈する LLM を 1 人に集約し、検証済みツールを呼ばせれば、
             伝言ゲームを解消しつつ第1世代の横断合成の弱さも超えられる」

第3世代  ChatOrchestrator (function calling ループ)   司令塔 = LLM 1 主体（現行）
  user query
     ▼  🧠 LLM が function calling で構造化引数を直接生成（NLU はここ1回だけ）
     ▼  アプリはツールを実行するだけ（SQL 自由生成なし／Semantic Layer 経由）
     ▼  🧠 同じ LLM が結果を見て次手を判断（最大6回ループ）→ 回答
  回答
  ✓ 解釈の主体が 1 つ＝伝言ゲーム解消。横断的なツール合成も 1 主体で扱える。
```

| | 第1世代 Structured RAG | 第2世代 Supervisor + sub-agent | 第3世代 ChatOrchestrator |
|---|---|---|---|
| **司令塔** | アプリ（固定の一本道） | 多数の LLM に分散 | **LLM 1 主体** |
| **質問を解釈する LLM** | 1（NLU 専用、回答とは別） | **4**（routing/oracle/ツール内/synth） | **1**（function calling に統合） |
| **データ取得** | LLM はパラメータ抽出のみ。アプリが**辞書由来のパラメータ化 SQL を固定ロジックで構築**（`query_maps`・`METRIC_MAP`、`@param` バインド、ホワイトリスト検証） | sub-agent 経由でツール（同上 `query_maps` 依存） | **ツール／Semantic Layer 経由**（SQL 自由生成なし、メトリクス定義は dbt に一本化＝SSOT） |
| **この世代の状態** | 基本スタッツでは正しく動作。弱点は横断合成の苦手さ・定義の二重化（移行の決め手ではない） | **伝言ゲームで精度低下**（スコープ拡大の手段として逆効果） | （伝言ゲームを解消し横断合成も 1 主体で扱える） |
| **次世代へ進んだ理由** | スコープ拡大（追加カテゴリーを単一チャットで）に向け役割分担を試行 | 役割分担が裏目に出たため解釈主体を 1 つへ集約 | — |

**要点**: 第3世代の本質的な成果は **第2世代の*伝言ゲーム*の解消**です。第2世代は第1世代の欠陥を直すために生まれたのではなく、**スコープ拡大に向けた設計判断（一部は学習・実験）** として導入され、期待に反して精度を落としました。第3世代はそれを「解釈する LLM を 1 主体に集約」することで解き、同時に第1世代が苦手だった横断的なデータ合成も 1 主体で扱えるようにしています。なお、データ取得を SQL 自由生成ではなくツール／Semantic Layer 経由に統一した点（[[009-dbt-semantic-layer-over-text-to-sql]]）は、第1世代の SQL を「直した」のではなく、第1世代の決定論的 SQL 構築が持っていた**定義の二重化（SSOT の不在）**を解消する独立の改善です。

> **補足（データ取得層の変遷）**: 第1〜2世代は「どのスタッツが・どのテーブルの・どのメトリクスか」を `query_maps`（[backend/app/config/query_maps.py](../../backend/app/config/query_maps.py)）の Python 辞書にハードコードし、それを見て**アプリが固定ロジックでパラメータ化 SQL を構築**していました（LLM は SQL を生成せず、テーブル名・カラム名は辞書由来、値は `@param` バインド）。したがって SQL 起因の hallucination はこの世代に存在しません。弱点は別にあり、この定義がアプリ側（SQL 構築ロジック）と dbt 側に二重化してズレる（＝サイレントな誤集計のリスク）点でした。第3世代では同じ定義を **dbt Semantic Layer の YAML に一本化（SSOT）** し、集約方法（`agg: sum` / `average`）まで定義側が持つことで、メトリクスの真実源を 1 つに統一しています。詳細は [[009-dbt-semantic-layer-over-text-to-sql]] を参照。

この構造は次の制約・課題を抱えていました（第2世代の問題の詳細）。

- **冗長な LLM 呼び出し**: 単純な質問でも「routing 用 LLM 1 回 → sub-agent の oracle/executor/reflection/synthesizer で複数回」と LLM を消費し、レイテンシとコストが嵩む（旧 4 回 → 後述の通り 1 回まで削減可能）。
- **ロジックの重複**: 各 sub-agent の `oracle / executor / reflection / synthesizer` がほぼコピーで、一方の修正が他方に反映されず一貫性が崩れやすい。
- **デバッグ困難性**: routing → sub-agent 初期化 → graph compile → astream のオーバーヘッドが、伝言ゲームで回答精度が落ちた際に「どの解釈段でズレたか」の調査を難しくしていた。
- **新規ツール追加コスト**: ツール 1 つ足すのに sub-agent と tools の最低 2 ファイル更新が必要。
- **アーキテクチャの過剰適合**: 自由会話・動的なツール選択・可変な出力形式という「単一 LLM + function calling ループ」で十分賄える領域に、決定論的な StateGraph を適用していたことが複雑性の主因と判明した。

加えて、対象 JD（GenAI Forward Deployed Engineer, Google Cloud）が `tool orchestration` を明示する文脈で、「LLM が tool を直接選べる現代の構成」を採れていない点は説明上も弱点でした。

## Decision（決定）

チャット経路を、**素の `google-genai` SDK + function calling ループで動く単一クラス `ChatOrchestrator`**（[backend/app/services/chat_orchestrator.py](../../backend/app/services/chat_orchestrator.py)）に統合しました。

- ユーザー質問の **NLU（自然文解析）を Orchestrator の LLM 自身の責務**に移管。ツール内 `_parse_query_with_llm` のような NLU 専用 LLM 呼び出しを廃止し、LLM が function calling で構造化引数（`name` / `season` / `metrics` 等）を直接生成する。
- `MAX_TOOL_ITERATIONS=6` の function calling ループで、`CHAT_TOOL_REGISTRY`（legacy）/ Semantic Layer registry を `use_semantic_layer` フラグで切替えて呼び出す。
- 切替は feature flag `use_legacy_chat_agent`（[settings.py:173](../../backend/app/config/settings.py#L173)）で行い、エンドポイント [ai_analytics_endpoints.py:553](../../backend/app/api/endpoints/ai_analytics_endpoints.py#L553) が旧 `run_mlb_agent_stream` と新 `ChatOrchestrator().run_stream()` を切替える（SSE イベント契約・I/O 互換を維持）。
- 旧 SSE イベント（`routing` / `state_update` / `tool_start` / `tool_end` / `token` / `final_answer` / `error`）を全て同名で発火し、フロント側を無改修にする。`agent_type` は `"chat"` 固定で `routing` を 1 回送る。

これにより LLM 呼び出しは **旧 4 回 → 2 回（`synthesize_response=False` で 1 回）** に削減されました（[README_ai_architecture.md](../../README_ai_architecture.md) §1）。

## Alternatives Considered（検討した代替案）

- **LangGraph のまま維持（現状維持）**: 二重構造の認知負荷とデバッグ困難性が解消されず、チャット保守が事実上停止する。自由会話には StateGraph の決定論性が過剰で、採用しない。
- **Supervisor を残しつつ sub-agent だけ薄くする**: routing 用 LLM 呼び出し（C6）が残り、冗長性の根を断てない。中途半端な複雑性が残るため不採用。
- **LangChain AgentExecutor 等の高水準フレームワークに載せ替え**: 抽象が厚く、ストリーミング時の `function_call` chunk 制御やコストロギングを細かく握れない。素の SDK の方が function calling ループと `LLMLogEntry` ロギングを透明に制御できるため不採用。

## Consequences（結果・トレードオフ）

**良くなったこと**

- **【最重要】回答精度・信頼性の向上 — 伝言ゲームの消滅**: 第2世代では 1 つの質問を routing / oracle / ツール内 NLU / synthesizer の **4 つの LLM が解釈し直し**、各段で意図がズレて回答精度が低下していた（＝伝言ゲーム。これは第2世代で新たに生じた問題であり、第1世代には存在しなかった）。`ChatOrchestrator` は質問を解釈する主体を **1 つの LLM に集約**したため、このズレが構造的に発生しなくなった。本リファクタの最大の成果はこの「回答の正しさ・安定」であり、以下のコード簡素化やコスト改善はその副次的効果である。なお、データ取得を検証済みツール／Semantic Layer 経由に統一した点（[[009-dbt-semantic-layer-over-text-to-sql]]）は、メトリクス定義の二重化（SSOT の不在）を解消する独立の改善であって、「第1世代の SQL hallucination を直した」ものではない（第1世代の SQL は LLM 生成ではなく辞書由来の固定構築であり、hallucination は元々存在しない）。
- チャット側エージェントコードが大幅に削減（`MLBStatsAgent` + 5 sub-agent + `SupervisorAgent` 合計 約 2,500 行が `ChatOrchestrator` 約 400 行に収束する見込み）。
- LLM 呼び出し回数が減り、レイテンシ・コストが改善。NLU を Orchestrator の LLM に一本化したことでツール定義もシンプル化。
- ツール追加が `tools/` への 1 ファイル追加 + 宣言追加で済む。

**悪くなったこと / 新たな負荷**

- **エラー時の自己修復が「厳密」から「LLM 任せ」に**: sub-agent ごとの明示的 Reflection ノードが消え、SQL エラー/空結果時の立て直しを **LLM の自然な再試行**（system prompt の「1〜2 回再試行」指示 + function calling ループ）に委ねる。決定論的な修復の確実さは下がる（明示的 Reflection は StrategyAgent 側に維持＝[[011-retain-langgraph-for-strategy-agent]] / [[012-classified-bounded-reflection-retries]]）。
- **ロギング経路が Gateway 窓口と別系統になった（一貫性の注記、実害なし）**: LangChain の `LangchainUsageCallback` が使えないため、`ChatOrchestrator` は `llm_gateway_service` の窓口関数を経由せず、SDK を直接叩いたうえで `LLMLogEntry` を自前で組み立てて記録する。**コスト・トークンは `llm_interaction_logs` テーブルに同等に記録されており、ログ欠落はない**（[chat_orchestrator.py:578](../../backend/app/services/chat_orchestrator.py#L578)。Gateway からは `_calc_cost_usd` のみ流用）。「全 LLM 呼び出しを Gateway 窓口に一本化する」という [[013-centralized-llm-gateway]] の理想からは外れる点だけが残る。

**移行ステータス**: feature flag によるカナリア運用（`USE_LEGACY_CHAT_AGENT=false`）を経て Accepted。旧 LangGraph sub-agent 群（`SupervisorAgent` / `BatterAgent` / `PitcherAgent` / `MatchupAgent` / `StatsAgent` / `MLBStatsAgent` / `AgentState`）の物理削除（Phase 2-G）は、ユーザー判断で保留中（CLAUDE.md「アーキテクチャ現状」参照）。

## JD Alignment（この募集要件との対応）

- **AG★（agentic workflows / tool orchestration）**: 「LLM が tool を直接選ぶ function calling ループ」という現代的なエージェント構成への移行そのもの。なぜ LangGraph を捨てたか（適材適所の判断）を trade-off で語れる中核 ADR。
- 関連: [[009-dbt-semantic-layer-over-text-to-sql]]（ツールが Semantic Layer 経由でメトリクスを返す）、[[050-tools-return-raw-data-orchestrator-composes]]（ツールは生データ返却に専念し応答合成は Orchestrator）。

## References

- 設計プラン: [CHAT_ORCHESTRATOR_REFACTOR_PLAN.md](../plan_docs/CHAT_ORCHESTRATOR_REFACTOR_PLAN.md)（§2 As-Is / §3 To-Be / §5.2 Phase 2）
- AI レイヤー: [README_ai_architecture.md](../../README_ai_architecture.md) §1 全体像 / §9 Request Lifecycle
- 実装: [backend/app/services/chat_orchestrator.py](../../backend/app/services/chat_orchestrator.py)
- 切替点: [ai_analytics_endpoints.py:553](../../backend/app/api/endpoints/ai_analytics_endpoints.py#L553) / [settings.py:173](../../backend/app/config/settings.py#L173)
- 関連 ADR: [[011-retain-langgraph-for-strategy-agent]], [[012-classified-bounded-reflection-retries]], [[050-tools-return-raw-data-orchestrator-composes]]
