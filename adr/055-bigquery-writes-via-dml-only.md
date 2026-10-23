# ADR-055: All application writes to BigQuery go through DML, never the streaming API

> **TL;DR（日本語）**: アプリから BigQuery への行書き込み 6 か所（LLM ログ・shadow 比較・Online Judge 判定・ドリフト監視ログ・Trace Viewer のラベルと期待値）が、`insert_rows_json`（ストリーミング挿入）を使っていた。ストリーミングで入った行はストリーミングバッファに置かれ、その間（最大 90 分程度）は **UPDATE も DELETE もできない**。テスト行を消せず、付け間違えたラベルも直せない状態だった。**すべて DML INSERT に統一**し、共通関数 `insert_rows_dml()` にまとめた。列の型は実行時にテーブル定義から取得するため、呼び出し側は従来どおり dict を渡すだけで済む。ストリーミング挿入は**アーキテクチャテストで禁止**した。代償は、1 回の書き込みが 1 回のクエリジョブになること。
>
> **TL;DR (English)**: Six application write paths — LLM logs, shadow comparisons, online judge verdicts, drift monitoring logs, and the Trace Viewer's labels and expected values — used `insert_rows_json`, the streaming API. Streamed rows sit in the streaming buffer, and while they do (up to roughly 90 minutes) they **cannot be updated or deleted**: a test row could not be removed and a mislabeled trace could not be corrected. **Every write now goes through a DML INSERT** via a shared `insert_rows_dml()`, which reads column types from the live table schema so callers still pass plain dicts. Streaming inserts are **banned by an architecture test**. The cost is that each write is a query job.

- Status: Accepted
- Date: 2026-10-23
- Deciders: Project owner

## Context

`insert_rows_json` is the most convenient way to write a row from the Python client, and it was copied from service to service. It is not a neutral "insert" — it is the streaming API (`tabledata.insertAll`). No one chose streaming as an architecture; it arrived as the default of whoever wrote the first logger.

The consequence surfaced during a local test of the online judge. One verdict row was written to the production table for verification, and the cleanup `DELETE` was rejected:

```
UPDATE or DELETE statement over table ... would affect rows in the streaming buffer, which is not supported
```

Looking for the cause turned up six services on the streaming path:

| Service | Table |
|---|---|
| `llm_logger_service` | `llm_interaction_logs` |
| `shadow_logger_service` | `shadow_comparisons` |
| `online_judge_service` | `online_judge_verdicts` |
| `ml_monitoring_logger` | `ml_drift_monitoring_logs` |
| `trace_label_service` | `trace_labels` |
| `trace_expectation_service` | `trace_expectations` |

The restriction was already shaping the design without being named as a decision. The 👍👎 feedback row is a separate `[FEEDBACK_UPDATE]` INSERT partly "because the streaming buffer does not permit UPDATE" ([[021-hitl-golden-flywheel]]), and the Trace Viewer front end avoided re-fetching after a save with comments blaming the buffer. Meanwhile `model_registry_service` already used a DML INSERT precisely to avoid the buffer. The project had two write conventions and no rule.

The Trace Viewer tables make the cost concrete. A failure label or an expected value is a **human judgement that feeds the golden set** ([[021-hitl-golden-flywheel]]). A wrong one must be correctable immediately, not after the buffer drains.

## Decision

**All application writes to BigQuery are DML INSERTs through [`backend/app/utils/bq_dml.py`](../backend/app/utils/bq_dml.py). `insert_rows_json` and `insert_rows` are not used under `backend/app/`.**

- `insert_rows_dml(client, table_id, rows)` builds one parameterized `INSERT INTO ... VALUES (...), (...)` for the batch. Values are always query parameters, never interpolated.
- **Column types come from the live table schema** (`client.get_table`), cached per table per process. Callers keep passing the same dicts they passed to `insert_rows_json`; no per-call type list is written by hand.
- `TIMESTAMP` / `DATE` / `DATETIME` / `TIME` values are passed as strings and `CAST` in SQL, and `JSON` columns go through `PARSE_JSON`. This accepts the ISO-8601 and JSON strings the existing callers already produce.
- Unknown columns raise `ValueError` instead of being dropped, so a typo fails loudly. `RECORD` columns are rejected explicitly; none of the six tables has one.
- Callers that previously inspected the `errors` list returned by `insert_rows_json` now catch exceptions. Synchronous writers (labels, expected values) re-raise as `RuntimeError` so the UI sees the failure; background loggers still swallow and log, as before.

The append-only shape of the logs is unchanged. Feedback is still a separate row rather than an UPDATE — that remains the better design for an audit trail — but it is now a choice, not a workaround.

## Alternatives Considered

- **Keep streaming and work around it**: the status quo. It forces every correction to be modeled as a new row and makes deletion of test or erroneous rows impossible for a window. For human-entered judgements that window is exactly when mistakes get noticed.
- **Storage Write API**: a different client and stream lifecycle for writes that are single rows at low volume. The added machinery is not justified at current traffic; DML covers the need with the client already in use.
- **Load jobs** (`load_table_from_*`): suited to bulk ingestion and already used for that (`scripts/ingest_glossary.py`). Per-request rows from an API handler are the wrong shape for them.
- **Hand-written typed parameters per call site** (the `model_registry_service` style): correct, but six call sites with dozens of columns would each carry a type list that drifts from the table. Reading the schema keeps one source of truth.

## Consequences

**What got better**

- Rows written by the application can be corrected or deleted immediately. The verification test for this ADR wrote two judge rows and deleted them in the same session — the operation that originally failed.
- One write convention across the project, enforced by a test rather than by memory.
- Comments and documents that described buffer behavior as a constraint were corrected.

**What got worse / new burdens**

- **Each write is a query job.** It takes longer than a streaming call. Background loggers absorb this on their daemon threads; label and expected-value saves are synchronous, so the reviewer waits for the job.
- **Per-query cost and quota impact have not been measured.** At current traffic it is not visible; it should be checked against the billing export before traffic grows, and `llm_interaction_logs` (one row per LLM call) is the table to watch.
- **The schema cache lives for the process.** A column added to a table is not seen until the service restarts. Deploys restart the service, so this only matters for manual schema changes on a running instance.

## Compliance

| | |
|---|---|
| **Invariant** | No file under `backend/app/` calls `insert_rows_json` or `insert_rows`. |
| **How it is checked** | `test_no_streaming_inserts_to_bigquery` in [`backend/tests/test_architecture.py`](../backend/tests/test_architecture.py) walks the AST of every file and fails on any call to either method. |
| **Enforcement** | ✅ Runs in GitHub Actions on every PR. |
| **Reading (2026-10-23)** | 0 offending files. A BigQuery dry run of the generated INSERT against all six tables' live schemas passed. |

The check is an AST walk rather than a grep so that a call inside a function body, or one split across lines, is still caught — the same reasoning as the other checks in that file. It cannot see a streaming write made through a different client library; none exists in the codebase today.

## Why This Matters

- **LM / EV**: the logs and verdicts are the evidence the evaluation layer reasons from. Evidence that cannot be corrected is a liability the moment a human makes a mistake entering it.
- **BP**: a default inherited from copy-paste had become an unstated architecture. Naming it, choosing deliberately, and enforcing the choice in CI is the reusable part.

## References

- Implementation: [`backend/app/utils/bq_dml.py`](../backend/app/utils/bq_dml.py)
- Test: [`backend/tests/test_architecture.py`](../backend/tests/test_architecture.py) (`test_no_streaming_inserts_to_bigquery`)
- Related ADRs: [[021-hitl-golden-flywheel]], [[053-agent-trace-viewer-failure-labeling]], [[018-llm-as-a-judge-offline-evaluation]], [[019-shadow-evaluation]]
- `README_ai_architecture.md` §3 (Logging & Cost Tracking)
