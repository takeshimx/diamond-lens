# ADR-013: 全 LLM 呼び出しを中央 Gateway に集約し、コスト/トークンを必ず記録する

- Status: Accepted
- Date: 2026-05-17
- Deciders: プロジェクトオーナー

## Context（背景・課題）

LLM 呼び出しが各サービスに散在していると、次の問題が起こります。

- **コストの不可視化**: 誰が・いつ・どのモデルを・何トークン・いくら使ったかが分からない。LLM-native なコスト管理（cost-per-request）が不可能。
- **記録漏れ**: 各所が個別に `generate_content` を叩くと、ログを書き忘れる箇所が出る。例外時に記録が飛ぶ。
- **モデル・価格表の分散**: 価格表やトークン抽出ロジックが各所にコピーされ、更新が漏れる。

「LLM を呼ぶ＝必ずログが書かれる」を**構造的に**担保したい、という課題です。記録したいのはコストだけでなく、解釈結果・レイテンシ・成否・フィードバック等を含む「やり取り全体」です。

## Decision（決定）

**全 LLM 呼び出しの単一窓口 `llm_gateway_service`** を設け、トークン抽出・コスト計算・BQ ロギングを集約しました（[backend/app/services/llm_gateway_service.py](../../backend/app/services/llm_gateway_service.py)）。

- `call_gemini()`（[llm_gateway_service.py:97](../../backend/app/services/llm_gateway_service.py#L97)）が Gemini を呼び、`try/finally` で**成功・失敗・例外時も必ず `LLMLogEntry` を書く**。
- `usage_metadata` から `input_tokens` / `output_tokens` / `cached_tokens` を抽出し、`_calc_cost_usd()` がモデル別 `PRICING` 表から USD コストを算出（[llm_gateway_service.py:52](../../backend/app/services/llm_gateway_service.py#L52)）。記録先は `llm_interaction_logs` テーブル。
- これらが README #24「LLM Usage Cost Dashboard」の基礎データになる。
- `get_genai_client()` で SDK クライアント生成も一元化。

設計原則は「**LLM を呼ぶ＝Gateway を通す＝必ずログが書かれる**」（[README_ai_architecture.md](../../README_ai_architecture.md) §2 / §3）。

### 記録するのはコスト/トークンだけではない（包括的インタラクションログ基盤）

Gateway が `llm_interaction_logs` に書くのは、コスト/トークンに**留まりません**。1 回の LLM 呼び出しにつき、約 40 カラムの情報を 1 行として記録します。コストはその一部です。

```
                      全 LLM 呼び出しが必ずここを通る
                                  │
                          ┌───────▼────────┐
                          │  LLM Gateway    │
                          └───────┬────────┘
                                  │ 1 呼び出し = 1 行（約40カラム）を記録
                                  ▼
              ┌─────────────  llm_interaction_logs  ─────────────┐
              │                                                  │
   コスト/トークン   レイテンシ      NLU解釈        成否/エラー    Reflection
   input_tokens   llm_latency_ms  parsed_metrics  success      is_retry
   cost_usd       bq_latency_ms   parsed_player   error_type   retry_count
   model          …               …               …            …
              │                                                  │
   フィードバック    相関ID         プロンプト版     入出力
   user_rating    trace_id       prompt_version  user_query
   feedback_*     request_id     …               response_*
              └──────────────────────────────────────────────────┘
```

つまり Gateway は「コスト記録係」ではなく、**LLM とのやり取りを丸ごと残す包括的なインタラクションログ基盤**です。

### 「記録」は網羅的に完成、「活用」は一部着手・多くは伸びしろ

重要なのは、**記録（capture）と活用（consume）を分けて捉える**点です。

```
┌──────────────────────────────────────────┐
│ ① 記録：もう完成している                     │
│   全呼び出しで約40カラムが必ず貯まり続ける      │
│   ＝ 分析の「素材」が網羅的に揃っている         │
└───────────────────┬──────────────────────┘
                    │ この土台があるから
                    ▼
┌──────────────────────────────────────────┐
│ ② 活用：一部だけ着手・多くは未開              │
│   ✅ コストダッシュボード（着手）              │
│   ✅ Judge 評価（parsed_* を使用）            │
│   ✅ HITL フライホイール（feedback_* を使用）   │
│   ⬜ レイテンシ分析・エラー率…（未メトリクス化） │
└──────────────────────────────────────────┘
```

全カラムをメトリクス化・ダッシュボード化しているわけではありませんが、**素材が先に網羅的に貯まっている**ため、新しい分析・改善は「掘れば出てくる」状態です。これは弱点ではなく、**分析基盤を先に厚く敷いておく意図的な設計判断**です。

## Alternatives Considered（検討した代替案）

- **各サービスで SDK を直叩き**: ログの書き忘れ・例外時の記録漏れ・価格表の分散が起こる。本 ADR が解消する対象。
- **外部 LLM オブザーバビリティ SaaS（LangSmith / Helicone 等）に委譲**: 依存と費用が増え、BQ に閉じた自前ダッシュボードと二重になる。自前 Gateway + BQ ログで要件を満たせるため不採用。
- **APM/ミドルウェアで HTTP 層をフックして計測**: トークン・コストという LLM 固有メタは HTTP 層から取りにくい。アプリ層の Gateway が適切。

## Consequences（結果・トレードオフ）

**良くなったこと**

- cost-per-request・モデル別・feature 別のコスト/トークンが BQ に揃い、ダッシュボード化できる（LM 要件の核）。
- **コストに留まらず約40カラムのインタラクションログが網羅的に貯まる**ため、評価（Judge）・HITL フライホイール・レイテンシ/エラー分析など、後から掘れる分析・改善の土台ができる（記録は完成、活用は伸びしろ）。
- `try/finally` により、例外時も記録が飛ばない。
- 価格表・トークン抽出が 1 箇所に集約され、更新漏れがない。

**悪くなったこと / 新たな負荷**

- **例外経路**: `ChatOrchestrator` は LangChain callback が使えないため Gateway の窓口関数を経由せず、`_calc_cost_usd` だけ流用して `LLMLogEntry` を自前で書く。**ログは同じテーブルに記録され欠落はない**が、「全呼び出しを Gateway 窓口に一本化」という理想からは外れる（[[010-chat-orchestrator-replaces-langgraph]] の Consequences 参照）。
- `PRICING` 表は手動メンテで、未登録モデルはコスト 0 で記録される（warning は出る）。

## JD Alignment（この募集要件との対応）

- **LM★（LLM-native metrics: cost-per-request / tokens）**: JD が明示する cost-per-request の計測基盤そのもの。
- **EV（observability）**: 全 LLM 呼び出しの可観測性を担保する。

## References

- 実装: [backend/app/services/llm_gateway_service.py](../../backend/app/services/llm_gateway_service.py)（`call_gemini` / `_calc_cost_usd` / `PRICING`）
- ログ: `LLMLogEntry`（`backend/app/services/llm_logger_service.py`）/ `llm_interaction_logs` テーブル
- AI レイヤー: [README_ai_architecture.md](../../README_ai_architecture.md) §2 LLM Gateway 層 / §3 Logging & Cost Tracking 層
- 関連 ADR: [[010-chat-orchestrator-replaces-langgraph]], [[015-gemini-context-caching]], [[016-token-budget-pool-separation]], [[032-snowflake-trace-id-structured-logging]], [[051-append-only-llm-logging]]
