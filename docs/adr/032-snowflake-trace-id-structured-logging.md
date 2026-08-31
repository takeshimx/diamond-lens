# ADR-032: Snowflake trace_id + 構造化 JSON ロギング（ContextVar 伝搬）

- Status: Accepted
- Date: 2026-05-17
- Deciders: プロジェクトオーナー

## Context（背景・課題）

1 つのユーザーリクエストは、エンドポイント → Orchestrator → 複数の LLM 呼び出し → ツール → BigQuery → ログ、と多くの層を横断します。素の `print` ログでは、**どのログ行がどのリクエストのものか**を相関できず、障害調査・コスト分析・shadow 比較の突き合わせができません。

「**1 リクエストを貫く相関 ID** を全層・全ログに通し、構造化して BigQuery で検索可能にしたい」という課題です。

## Decision（決定）

**Snowflake 形式の `trace_id`** をリクエスト単位で発番し、**ContextVar で全層に自動伝搬**させ、構造化 JSON ログに必ず載せる設計にしました（[SNOWFLAKE_TRACE_ID_PLAN.md](../plan_docs/SNOWFLAKE_TRACE_ID_PLAN.md) / [README_ai_architecture.md](../../README_ai_architecture.md) §9）。

- **Snowflake ID**: Twitter Snowflake 方式の時刻順ソート可能な 64bit ID（`backend/app/utils/snowflake.py`）。
- **ContextVar 伝搬**: `request_context` の `set_trace_id` / `get_trace_id` で、明示的に引き回さなくても各層が同じ `trace_id` を読める（`backend/app/middleware/request_context.py`）。
- **全ログ構造体に自動付与**: `LLMLogEntry` も `ShadowComparisonEntry` も、生成時に ContextVar から `trace_id` を取得して `to_dict()` に載せる。明示セットがあればそれが優先（[test_trace_id_propagation.py:12](../../backend/tests/utils/test_trace_id_propagation.py#L12) / [:25](../../backend/tests/utils/test_trace_id_propagation.py#L25)）。
- 伝搬は `LLMLogEntry` / `ShadowComparisonEntry` / StructuredLogger JSON / `format_sse()` ペイロードまで貫く（伝搬テストで検証）。

## Alternatives Considered（検討した代替案）

- **素の print ログ**: 相関不能。構造化もされず BQ で検索できない。本 ADR が解消する対象。
- **UUID を引数で手渡し**: 全関数シグネチャに `trace_id` を足す必要があり侵襲的。ContextVar なら呼び出しグラフを汚さず伝搬できる。
- **UUIDv4 を採用**: ランダムで時刻順ソートできない。Snowflake は ID 自体が時系列順で、ログの並べ替え・範囲検索に有利。
- **OpenTelemetry をフル導入**: 学習価値はあるが、まず BQ ログに相関 ID を通す目的にはコア実装で足り、段階的に拡張できる。

## Consequences（結果・トレードオフ）

**良くなったこと**

- 1 リクエストの全ログ（LLM 呼び出し・shadow・SSE）を `trace_id` で串刺し検索でき、障害調査・コスト分解・shadow 突き合わせが可能に。
- ContextVar 伝搬で、各層のコードを汚さず相関 ID が通る。
- Snowflake の時系列ソート性で、ログの時間順分析が容易。

**悪くなったこと / 新たな負荷**

- ContextVar はスレッド/タスク境界をまたぐと引き継がれないケースがあり、**別スレッド実行（非同期ログ書き込み・並列ツール実行）では明示的な伝搬・セットが要る**点に注意が要る。
- Snowflake 発番器の実装・運用（時刻同期・worker id）を自前で持つ。

## JD Alignment（この募集要件との対応）

- **LM★（granular tracing）/ EV（observability）**: JD が明示する granular tracing の実装。相関 ID による横断観測性を、業界標準（Snowflake / structured logging）に沿って語れる。

## References

- 設計プラン: [SNOWFLAKE_TRACE_ID_PLAN.md](../plan_docs/SNOWFLAKE_TRACE_ID_PLAN.md)
- 実装: `backend/app/utils/snowflake.py` / `backend/app/middleware/request_context.py`
- テスト: [backend/tests/utils/test_trace_id_propagation.py](../../backend/tests/utils/test_trace_id_propagation.py)
- AI レイヤー: [README_ai_architecture.md](../../README_ai_architecture.md) §9 Request Lifecycle
- 関連 ADR: [[013-centralized-llm-gateway]], [[019-shadow-evaluation]], [[033-sse-streaming]], [[051-append-only-llm-logging]]
