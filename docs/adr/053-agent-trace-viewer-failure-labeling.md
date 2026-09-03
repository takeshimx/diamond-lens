# ADR-053: Agent Trace Viewer と失敗ラベリング — 既存ログテーブルへの相乗り

- Status: Accepted
- Date: 2026-09-03
- Deciders: Takeshi

## Context（背景・課題）

エージェントの実行経路を人間が読める形にする手段が存在しなかった。

`llm_interaction_logs` には LLM 呼び出しが 1 行ずつ記録され、[ADR-032](032-snowflake-trace-id-structured-logging.md) の `trace_id` で 1 リクエストの行を束ねられる状態にはあった。しかし読む側の実装が無く、実際の調査は BigQuery コンソールに SQL を手打ちする運用だった。

その結果、次の問いに答えられなかった。

- エージェントが**どのツールを選び、どの引数で呼んだか**
- **どのステップで時間を使ったか**（LLM の判断なのか、ツールの実行なのか）
- ツールが**失敗したかどうか**（失敗しても後続の LLM が何か答えてしまうため、応答だけ見ても分からない）
- 失敗した trace に**ラベルを付けて蓄積する**手段

### 対象経路の選定でつまずいた経緯（記録として残す）

当初、計装対象を `StrategyAgent`（LangGraph、planner → parallel_executor → aggregator → reflection → strategist）に定めた。多段グラフであり reflection による再計画も持つため、trace として最も情報量が多いと判断したためである。

**この判断はコードの構造だけを見て下したもので、誤りだった。** 実ログを集計したところ、`StrategyAgent` を呼ぶ唯一のエンドポイント `POST /api/v1/strategy-report` には 1 件も記録が無かった。フロントエンドの戦略レポート画面は 8 本の個別エンドポイントを並列に叩く構成で、そのうち LLM を使う `/strategy-report/tactics` も `StrategyAgent` を経由しない独立実装である。チャット経路も [ADR-010](010-chat-orchestrator-replaces-langgraph.md) で `ChatOrchestrator` に移行済みであり、`StrategyAgent` は**現行 UI からいずれの経路でも到達しない**。

「コードが存在すること」と「使われていること」は別である。実装対象を決める前に、その経路に実トラフィックがあるかを先に測るべきだった。この失敗は [ADR-021](021-hitl-golden-flywheel.md) が記録する「設計ではなくトラフィック量の問題」と同じ性質のものである。

## Decision（決定）

**実際に動いている `ChatOrchestrator` を計装対象とし、trace は既存の `llm_interaction_logs` に相乗りさせる。**

### 1. 既存テーブルに 3 列を追加（新テーブルを作らない）

| 列 | 型 | 意味 |
|---|---|---|
| `node` | STRING | エージェント上の役割。`oracle` / `executor` / `synthesizer` など |
| `iteration` | INT64 | その経路固有の周回カウンタ |
| `tool_calls` | STRING | ツール名・引数・成否・所要時間の JSON |

いずれも NULLABLE。既存行は NULL のままで、既存の書き込み経路は無改修で動く。

### 2. LLM を呼ばないステップも 1 行として記録する

ツール実行は LLM 呼び出しではないが、**どのツールが失敗し何ミリ秒かかったかは trace の中核情報**である。`node = "executor"` の行として記録し、`model` を **NULL のまま**にする。

`usage_stats_service` は全クエリで `WHERE model IS NOT NULL` により LLM 行だけを集計しているため、この行は LLM コストダッシュボードに一切現れない。

### 3. `node` は応答内容から判定する

`ChatOrchestrator` は LLM を呼ぶ箇所が 1 つしか無く、返ってきたものが `function_call` かテキストかで役割が変わる。

```python
entry.node = "oracle" if function_calls else "synthesizer"
```

SSE イベントが既に `state_update` を `oracle`、`token` を `synthesizer` として送り分けているため、その語彙に揃えた。

### 4. ラベルは別テーブル `trace_labels` に追記のみで持つ

ログ本体を書き換えない。ラベルの付け直しは新しい行の INSERT で表現し、読み出し側が `labeled_at` の最新を採用する。「いつ判断が変わったか」を残すためである。

ラベル軸は 7 種:

`correct` / `wrong_tool` / `wrong_params` / `right_answer_wrong_path` / `should_have_abstained` / `retrieval_miss` / `tool_error`

## Alternatives Considered（検討した代替案）

- **`StrategyAgent` を計装対象にする**: 当初の方針。実トラフィックがゼロであることが判明して撤回した。計装コード自体は実装済みで残してあるが、UI から到達しないため trace は蓄積されない。
- **UI を `StrategyAgent` に繋ぎ変える**: trace を濃くする根本策だが、`/tactics` の構造化出力（`tier` / `title` / `detail` / `icon` の配列）を `strategist` ノードに移植する必要があり、実測で 15〜18 秒かかる生成が更に遅くなる。プロダクトの体験を落として観測性を得る取引になるため見送った。
- **`/tactics` の 5 段階に `node` を刻む**: 実トラフィックがあり UI 変更も不要だが、`/tactics` はデータ取得もプロンプトも固定で、LLM が経路を決めていない。**エージェントの trace ではなく決定的パイプラインの実行ログ**であり、`right_answer_wrong_path` のような経路ラベルが原理的に付けられない。
- **trace 専用テーブルを新設する**: 責務は綺麗になるが、trace を読むたびに `llm_interaction_logs` との JOIN が必要になり、テーブルが 2 つに増えて運用対象も増える。既存テーブルには `WHERE model IS NOT NULL` による LLM 行の判別が既に存在しており、非 LLM 行の混在は設計時点で想定済みだったため相乗りを選んだ。

## Consequences（結果・トレードオフ）

### 良くなったこと

- 1 リクエストの経路が `TRACE` タブで読めるようになった。ツール名・引数・成否・所要時間・トークン・コストがステップ単位で並ぶ
- ボトルネックの所在が分かる。実例では LLM 判断 1.74 秒に対しツール実行 3.30 秒で、**遅いのは LLM ではなくツール**だった
- 失敗ラベルを蓄積する土台ができた。[ADR-021](021-hitl-golden-flywheel.md) の golden 昇格フローに繋げる先が用意された

### 悪くなったこと / 残った負債

- **`iteration` 列の意味が経路で揃っていない。** `ChatOrchestrator` では LLM 呼び出しの通し番号、`StrategyAgent` では reflection の `retry_count` を入れている。横断的な集計には使えないため、一覧の「LLM 呼び出し回数」は `COUNTIF(model IS NOT NULL)` で数え直している。列名と実態が乖離しており、いずれ整理が要る
- **`MAX_TOOL_ITERATIONS` による打ち切りが trace 上で判別できない。** 上限到達は「黙った」のではなく「調べ切れなかった」であり、通常終了と区別すべきだが、現状フラグを記録していない
- **エンドポイントが書くサマリ行の timestamp が実態とずれる。** `LLMLogEntry` はインスタンス生成時に timestamp を打つため、リクエスト受信直後に生成して処理完了後に書き込むエンドポイントの行は「時刻は最古・中身は最終結果」になる。ステップ列に混ぜると順序が壊れるため、`node IS NULL` の行は `summary` として分離して別枠に表示している
- **母数が薄い。** 直近 30 日のチャット trace は 7 本。ラベルを溜めて golden 昇格に回すには量が足りない。これは実装ではなくトラフィックの問題

## JD Alignment

対象 JD: **Forward Deployed Engineer, Generative AI, Google Cloud**

- **LM★** — granular tracing。`trace_id` によるステップ単位の追跡を、ログ基盤だけでなく閲覧面まで実装した
- **EV★** — observability framework。失敗の検出と分類を人手で回す導線

なお本 ADR は **Agent Learning Engineer 系の JD**（*"Build tools for inspecting traces, labeling failures, comparing runs"*）に対して逐語的に対応する。詳細は [docs/plan_docs/AGENT_LEARNING_ENGINEER_PREP_PLAN.md](../plan_docs/AGENT_LEARNING_ENGINEER_PREP_PLAN.md) の P0-1 を参照。

## References

- [ADR-010: ChatOrchestrator replaces LangGraph sub-agents](010-chat-orchestrator-replaces-langgraph.md)
- [ADR-011: Retain LangGraph only for StrategyAgent](011-retain-langgraph-strategy-agent.md)
- [ADR-032: Snowflake trace_id + structured logging](032-snowflake-trace-id-structured-logging.md)
- [ADR-051: Append-only LLM logging](051-append-only-llm-logging.md)
- `README_ai_architecture.md` §3 / §9.7
- 実装: `backend/app/services/trace_query_service.py` / `trace_label_service.py` / `backend/app/api/endpoints/trace_endpoints.py` / `frontend/src/components/TraceViewer.jsx`
