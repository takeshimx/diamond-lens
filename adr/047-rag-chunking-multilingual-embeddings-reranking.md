# ADR-047: Rebuild the glossary RAG as BigQuery-based agentic RAG and adopt LLM reranking

> **TL;DR（日本語）**: 既存の文書 RAG は Cloud Run のイメージ肥大化を理由に**無効化されたまま放置**され、しかも **192 ページの PDF を丸ごと 1 ベクトルに圧縮**していて検索精度は実質ゼロだった。ChromaDB と sentence-transformers を捨てて**ベクトルストアを BigQuery に置く**ことで、無効化の原因だった依存の重さが構造的に解消する（新規ライブラリはゼロ）。常時検索する naive RAG ではなく **LLM が必要と判断したときだけ引く Agentic RAG**。最大の学びは**距離では正解と不正解を分離できない**という実測で、最近傍の不正解 0.1684 が最近傍の正解 0.1816 より近く、**閾値をどこに引いても分離不能**だった。これが「閾値調整ではなく順位付け自体を変える」＝ **LLM リランク**採用の直接の根拠であり、命中@5 は 0.800 → **1.000**、MRR は 0.658 → **0.925** に改善した。
>
> **TL;DR (English)**: The existing document RAG had been **disabled and left to rot** (it bloated the Cloud Run image), and it **compressed a 192-page PDF into a single vector** — retrieval accuracy was effectively zero. Dropping ChromaDB and sentence-transformers and **putting the vector store in BigQuery** structurally removes the dependency weight that caused the shutdown, with zero new libraries. It is **agentic RAG — retrieved only when the LLM decides it is needed** — not naive always-on retrieval. The most important finding was measured, not assumed: **distance cannot separate right from wrong**. The nearest incorrect chunk sat at 0.1684, closer than the nearest correct one at 0.1816, so **no threshold can split them**. That is the direct justification for changing the ranking itself rather than the threshold — **LLM reranking** — which lifted hit@5 from 0.800 to **1.000** and MRR from 0.658 to **0.925**.

> This fills in the slot the index had reserved as "RAG chunking + multilingual embeddings + reranking." All three — chunk design, multilingual embeddings and reranking — are part of the decision recorded here.

- Status: Accepted (controlled by two flags, `USE_GLOSSARY_RAG` and `USE_GLOSSARY_RERANK`)
- Date: 2026-08-21
- Deciders: Project owner

> **Postscript (2026-09-04)**: Tier 2 (the official rules PDF) was ingested shortly after this ADR, but rule-type hit@3 stalled at 0.333, so it was removed from search via `EXCLUDED_CATEGORIES`. It later turned out that **the 0.333 was a measurement bug caused by wrong golden-set chunk_ids** — an empty heading chunk had been designated as the correct answer. After correcting that, Tier 2 was restored. See [[054-cross-lingual-rag-hyde-category-thresholds]] for the history and the countermeasures (per-category thresholds and HyDE).
>
> This ADR's claim that "cross-lingual retrieval works with a single model" was **an observation on Tier 1 (Japanese questions against a Japanese glossary)** and did not hold for Tier 2, which spans Japanese and English. ADR-054 corrects that too.
>
> **Correction (2026-09-20)**: This ADR originally gave the reason for not adopting `VECTOR_SEARCH` as "its first argument is a fixed table and cannot take a subquery, so `category` cannot be pre-filtered." **That is factually wrong.** BigQuery's documentation explicitly shows passing a subquery as the first argument to pre-filter (`VECTOR_SEARCH((SELECT * FROM t WHERE type = 'animal'), 'embedding', ...)`). The correct reason is that **a vector index is not populated for tables under 10 MB (`BASE_TABLE_TOO_SMALL`), so `VECTOR_SEARCH` silently falls back to brute force internally and there is no practical benefit at the current scale**. The original error most likely conflated **post-filter behavior** when filtering on a non-stored column (filtering after search, which thins out the top-K) with "subqueries are not allowed." The affected passages (Search Infrastructure / Alternatives Considered) have been corrected.

## Context

A document RAG implementation existed but had been **disabled and left to rot**.

- `rag_service.py` (ChromaDB + sentence-transformers `all-MiniLM-L6-v2`) was outside Git via `.gitignore`.
- `rag_endpoints.py` was commented out in `router.py`, the stated reason being **reducing the Cloud Run image size**.
- `chromadb`, `sentence-transformers` and `pypdf2` were likewise commented out of `requirements.txt`.

The design flaw was equally large: it **compressed an entire PDF into a single vector**, with no chunking at all. Reduce a 192-page document to one vector and every question comes back at the same distance. Retrieval accuracy was effectively zero.

Meanwhile the main chat path (`ChatOrchestrator`) was complete as a tool-use design querying BigQuery directly, so **numeric aggregation needed no RAG**. RAG was needed only for **unstructured text**, such as "what is xwOBA?"

The problems were:

- Revive the document RAG without adding dependencies (without inflating the image).
- Handle cross-lingual retrieval — questions in Japanese, documents partly in English.
- Ensure that a failure in an auxiliary feature like term lookup never takes chat down.
- Above all, **there was no way to measure retrieval accuracy.** Nothing beyond "it runs" could be said.

## Decision

The glossary RAG was rebuilt as **agentic RAG contained entirely within BigQuery**, with **LLM reranking built in**.

### Search infrastructure

- The vector store lives in **BigQuery** (`glossary_chunks` / `glossary_embeddings`). Abandoning ChromaDB and sentence-transformers structurally removes the image bloat that caused the shutdown. Zero new libraries.
- Search is **brute force via `ML.DISTANCE`**. `VECTOR_SEARCH` plus a vector index would not change anything at this scale, because **a table under 10 MB does not get its index populated (`BASE_TABLE_TOO_SMALL`) and automatically falls back to brute force**. Plain SQL also lets `WHERE category = ...` pre-filters be written directly — and a filter is required to structurally prevent the failure described below.
- The embedding model is **`text-multilingual-embedding-002`**, absorbing cross-lingual retrieval (Japanese questions against partly English documents) in a single model.
- **`task_type` is specified asymmetrically**: `RETRIEVAL_DOCUMENT` for documents, `RETRIEVAL_QUERY` for questions.

### Knowledge source and chunk design

- Tier 1 is **43 hand-curated glossary entries** (`docs/knowledge/glossary_*.md`) kept under Git. The term list is extracted mechanically from `METRIC_MAP` and MetricFlow's `metrics/*.yml`; definitions are drafted by an LLM, cross-checked against official sources (MLB.com Glossary, FanGraphs Library) and then reviewed by a human — a semi-automated flow.
- **One `## heading` = one chunk.** Including the heading term at the start of the chunk puts the term itself into the vector.
- **Metadata is excluded from vectorization.** Category, metric names and verification status move to separate columns: `category`, `metric_names`, `verified_source`.
- Idempotency is **DELETE→INSERT per `source` (file)**, so adding, removing or reordering headings leaves no orphan rows.

### Invocation model

- Not naive always-on RAG but **agentic RAG — retrieved only when the LLM decides it is needed**. It is registered with `ChatOrchestrator` as `glossary_search_tool`, following the separation of concerns in [[050-tools-return-raw-data-orchestrator-composes]].
- The tool declaration's `description` spells out **when not to use it** (fetching a player's stat values). This is what determines the misfire rate.
- The LLM chooses a `category` (batting / pitching / statcast), which is used as a pre-filter.

### Reranking

- Vector search takes **10 candidates**, narrows by threshold, and then **has Gemini reorder them** (`rerank_service.rerank_hits`).
- The LLM returns **only an array of candidate numbers**, and sees just the first 300 characters of each body.
- Out-of-range and duplicate numbers are discarded, because LLM output carries no guarantees.
- The call goes **through `call_gemini` (the gateway)** ([[013-centralized-llm-gateway]]); hitting the SDK directly would lose the cost accounting.

### Response generation and citations

- Glossary results are prose rather than raw data, so **whether to synthesize a response is decided by tool name** (`SYNTHESIS_REQUIRED_TOOLS`). Stat lookups keep their mechanical formatting.
- **Citations are appended mechanically, not at the LLM's discretion** (`_append_sources`).

### Evaluation

- A golden set (`backend/tests/golden/retrieval_fixtures.json`) and an evaluation harness (`backend/scripts/run_retrieval_eval.py`) were built, and **thresholds, category filtering and reranking were all decided by measurement**.
- Question-side embeddings are cached in BigQuery so that re-running configuration comparisons incurs no extra billing.

## Alternatives Considered

- **Keep ChromaDB and revive it**: the direct cause of the shutdown (image size) would recur. It adds local dependencies and fits poorly with a serverless Cloud Run setup.
- **`VECTOR_SEARCH` + a vector index**: the right answer at scale, but **an index is not populated for tables under 10 MB**, so writing it at the current scale merely has BigQuery report `BASE_TABLE_TOO_SMALL` and fall back to brute force — no gain. (`ML.DISTANCE` brute force is vector search too, in the sense of exact KNN; the difference is exact versus approximate ANN.) The switching criterion is not row count but **a table size of 10 MB**. On migration, include the `category` used for pre-filtering in `CREATE VECTOR INDEX ... STORING`; filtering on a non-stored column becomes a **post-filter** (search first, then narrow), which thins out the top-K.
- **Hand-write "anticipated questions" for each entry to bridge the vocabulary gap**: this only works because there are 43 entries; **human effort grows in proportion to document count and does not scale**. Vocabulary gaps should be solved at search time (reranking, query expansion). **Rejected.**
- **Enable `synthesize_response=True` globally**: stat lookups are more accurate and cheaper with mechanical formatting. This would just add one LLM call to every question.
- **Call an LLM inside the tool to summarize**: LLM calls would be scattered across two places and token accounting would be maintained twice.
- **Instruct the system prompt to "always cite sources"**: that reaches "mostly obeyed" at best. Citations were in fact observed to drop during summarization, so it does not guarantee attribution.
- **Decide whether to synthesize based on a key in the tool's return value (`sources`, etc.)**: the moment another tool returns the same key, behavior changes silently. Deciding explicitly by tool name avoids that.

## Consequences

### Measured results

A golden set of 12 questions (2 of which are `should_not_fire` and excluded from retrieval scoring).

| | hit@3 | hit@5 | MRR |
|---|---:|---:|---:|
| Vector search only | 0.700 | 0.800 | 0.658 |
| **+ LLM reranking** | **0.900** | **1.000** | **0.925** |

By type, paraphrased questions that omit the term name went from 0.600 to 0.800 (MRR 0.567 → 0.850), and confusable pairs from 0.500 to **1.000** (MRR 0.375 → 1.000). The misfire rate is **0.000** (2 of 2 correctly chose the stats tool instead).

### The failure this design revealed, recorded deliberately

**A pitching metric came back first for a batting question.** For "which metric identifies hitters whose contact quality is good but whose results are not," vector search returned the pitching metric **Stuff+** first (distance 0.221). The correct answer, xwOBA, was nowhere in range.

There were two causes.

1. **Surface-level lexical overlap**: the question's phrase "contact quality" never appears in the xwOBA chunk (which says "batted-ball content" instead), while the pitching chunk's **headings** contained "stuff index" and "quality of contact allowed."
2. **Loss of discriminative power**: all 43 entries share one domain, one template and one writing style, so most of the embedding was occupied by a common component meaning "this is a definition of a baseball metric."

Removing metadata did not help. A category filter removed the pitching noise, but **xwOBA still ranked 8th out of 15 batting entries**. The batting distance range spanned only **0.2381–0.2919 (a width of 0.054)** — near-indiscriminate.

**Further, distance turned out to be unable to separate correct from incorrect at all.**

| Target | min | p50 | max |
|---|---:|---:|---:|
| Correct chunks | 0.1816 | 0.2261 | 0.2542 |
| Top-ranked incorrect | **0.1684** | 0.2363 | - |

The nearest incorrect chunk (0.1684) sits closer than the nearest correct one (0.1816). **No threshold can separate them.** A threshold can only cut away the obviously irrelevant; improving accuracy requires changing the ranking itself — a conclusion shown by measurement rather than guesswork. That is the direct justification for adopting reranking.

The threshold was set to **0.275** based on measurement. Loosening beyond 0.275 does not raise the correct-answer retention rate above 0.800 and only admits more irrelevant results (3.00 results/question at 0.275, 3.70 at 0.35). Below 0.275, "no match" starts occurring.

### What got better

- **The document RAG is back with zero dependencies.** Without ChromaDB or sentence-transformers, the image bloat that caused the shutdown cannot recur.
- **Serverless and pay-as-you-go.** No always-on instance; one Vertex AI call per search.
- **Cross-lingual retrieval works with a single model.** For the Japanese paraphrase "which metric identifies hitters whose contact quality is good but whose results are not," the partly-English xwOBA chunk comes back first.
- **Behavior is backed by numbers.** Thresholds, category filtering and reranking were all chosen from measured recall and MRR.
- **Fail-open is present on every path.** Neither a BigQuery outage nor a reranking failure takes chat down.

### What got worse / new burdens

- **Each glossary question adds one Gemini call** (the rerank). Measured latency varies from 2 to 15 seconds and needs further measurement.
- **Brute-force search is linear in row count.** Ingesting Tier 2 (the official rules PDF, ~192 pages) will require re-evaluation. The criterion for migrating is `glossary_embeddings` exceeding 10 MB (roughly 1,700 rows at an estimate of 768 dimensions × 8 bytes ≈ 6 KB per row; not yet verified in practice).
- **The golden set is small, at 12 questions.** A misfire rate of 0.000 means no more than "no problem was detected at this point."
- **The legacy ChromaDB implementation is still present** (`rag_service.py`, `rag_endpoints.py`, `document_loader.py`, `index_knowledge_base.py`). Following the project's "do not delete" policy, the new implementation runs alongside it in separate files.

## Why This Matters

- **Search and RAG design**: it answers "why not put everything in RAG" by backing the split — SQL for structured numbers, RAG only for unstructured text — with both implementation and measurement.
- **Evaluation**: it defines recall, MRR and misfire rate, and measures down to the difference between hit@k and recall@k when several answers are correct.
- **Failure analysis**: it records the causal chain — mis-retrieval from surface lexical overlap and inseparability from overlapping distance distributions, both shown numerically, leading to the adoption of reranking.

## References

- Plan and execution log: `docs/plan_docs/RAG_REBUILD_PLAN.md`
- Search service: [backend/app/services/glossary_rag_service.py](../backend/app/services/glossary_rag_service.py)
- Reranking: [backend/app/services/rerank_service.py](../backend/app/services/rerank_service.py)
- Tool: [backend/app/services/tools/glossary_search_tool.py](../backend/app/services/tools/glossary_search_tool.py)
- Ingestion: [backend/scripts/ingest_glossary.py](../backend/scripts/ingest_glossary.py)
- Evaluation: [backend/scripts/run_retrieval_eval.py](../backend/scripts/run_retrieval_eval.py) / [run_misfire_eval.py](../backend/scripts/run_misfire_eval.py)
- Golden set: [backend/tests/golden/retrieval_fixtures.json](../backend/tests/golden/retrieval_fixtures.json)
- BigQuery vector index (not populated under 10 MB; `STORING`, pre-filter and post-filter): https://cloud.google.com/bigquery/docs/vector-index
- `VECTOR_SEARCH` function reference: https://cloud.google.com/bigquery/docs/reference/standard-sql/search_functions#vector_search
- Related ADRs: [[010-chat-orchestrator-replaces-langgraph]] / [[013-centralized-llm-gateway]] / [[050-tools-return-raw-data-orchestrator-composes]] / [[018-llm-as-a-judge-offline-evaluation]]
