# ADR-054: Restore the official rulebook PDF to retrieval, making cross-lingual search work with per-category thresholds and HyDE

> **TL;DR（日本語）**
>
> 公式ルール PDF（897 チャンク）は「命中@3 が 0.333 だから使い物にならない」と判断し、2026-08-21 に検索対象から外していた。しかし実データを調べると、**壊れていたのは検索ではなく測定の側**だった。
>
> 検索は 3 段構成である。**① ベクトル検索で候補を 10 件取る → ② 距離が閾値より遠い候補を捨てる（足切り）→ ③ 残った候補を LLM に並べ直させる（リランク）。** この 3 段に対し、次の 3 つが同時に壊れていた。
>
> 1. **正解ラベルが「中身のない見出し」を指していた。** `rule_001`（ボークの条件）の正解に指定していた `#6.02(a)` の全文は `(a) Balks / If there is a runner, or runners, it is a balk when:` の 134 字だけで、実際の条件は子チャンク `6.02(a)(1)`〜`(13)` にある。**検索が本物の条文を返しても不正解と記録されていた。**
> 2. **rule 型が 3 問しかなかった。** 0.333 は「3 問中 1 問」であり、1 問の当たり外れで 0.333 単位に跳ねる。小数点を議論できる分解能が無かった。
> 3. **② の足切りで候補が全滅し、③ のリランクが一度も起動していなかった。** 日本語の質問で英語の条文を引くと距離が約 0.07 遠い側へ寄るため、日本語文書の用語集用に決めた閾値 0.275 では 10 件すべてが捨てられていた（30 問中 15 問で候補 0〜1 件）。当時の「rules にリランクは効かない」という観測は、**効かなかったのではなく動いていなかった**。
>
> 是正は 3 点。**正解ラベルを実体チャンクへ貼り直す / rule 型を 3 問 → 30 問へ拡張する / `rules` 専用の閾値 0.35 を設ける**（用語集は 0.275 のまま）。ここまでで 命中@3 は 0.600 → 0.733。さらに **HyDE**（日本語の質問を英語の条文風テキストへ LLM に書き換えさせ、それを埋め込んで検索する。ユーザーの入力も最終回答も日本語のままで、変わるのは検索に使う文字列だけ）を加えて **0.833**。**チャンク分割・埋め込みモデル・検索アルゴリズムは一切変えていない。**
>
> **教訓: 「精度が出ない」と判断する前に、その数字を作っている測定系を疑うこと。** 壊れた 0.333 を信じて、897 チャンクを 2 週間封印していた。
>
> **TL;DR (English)**
>
> The official rulebook PDF (897 chunks) was pulled out of retrieval on 2026-08-21 because hit@3 sat at 0.333. Inspecting the real data showed **the retrieval was not what was broken — the measurement was.**
>
> Retrieval runs in three stages: **① vector search returns 10 candidates → ② candidates beyond a distance threshold are dropped → ③ an LLM reranks what survives.** Three things were broken at once:
>
> 1. **The golden label pointed at an empty heading.** The "correct" chunk for `rule_001` was `#6.02(a)`, whose entire body is `(a) Balks / If there is a runner, or runners, it is a balk when:` — the actual conditions live in child chunks `6.02(a)(1)`–`(13)`. **Returning the real rule text was scored as wrong.**
> 2. **There were only three rule questions.** 0.333 means "one of three"; a single question moved the metric by a third. There was no resolution to argue about.
> 3. **Stage ② cut every candidate, so stage ③ never ran.** Japanese questions against English rule text land ~0.07 further out, so the 0.275 threshold — chosen for the all-Japanese glossary — discarded all 10 candidates (0–1 survivors on 15 of 30 questions). The earlier finding that "reranking doesn't help for rules" meant **reranking had never once executed.**
>
> The fix was threefold: **repoint the labels at real chunks, grow the rule set from 3 to 30 questions, and give `rules` its own 0.35 threshold** (the glossary stays at 0.275). That alone moved hit@3 from 0.600 to 0.733. Adding **HyDE** — having an LLM rewrite the Japanese question as rulebook-style English and embedding *that*, while the user's input and the final answer stay Japanese — reached **0.833**. **No change was made to chunking, the embedding model, or the search algorithm.**
>
> **The lesson: before concluding that accuracy is bad, question the instrument producing the number.** A broken 0.333 kept 897 chunks switched off for two weeks.

- Status: Accepted (adds `USE_GLOSSARY_HYDE`; `EXCLUDED_CATEGORIES` is now empty)
- Date: 2026-09-04
- Deciders: Project owner
- Related: [[047-rag-chunking-multilingual-embeddings-reranking]] (this ADR continues it)

## Context

After [[047-rag-chunking-multilingual-embeddings-reranking]] rebuilt the glossary RAG on BigQuery, Tier 2 (the MLB official rulebook PDF, 897 chunks) was ingested. Rule-type hit@3 stalled at **0.333**, so on 2026-08-21 the category was excluded from retrieval with `EXCLUDED_CATEGORIES = ("rules",)` — **disabled while the data stayed in place**.

Re-examining the real data before restarting showed that **the 0.333 itself contained measurement error**.

### Finding 1: the golden label pointed at an empty heading

`rule_001` ("in what situations is a balk called?") designated `#6.02(a)` as its correct chunk. That chunk's entire body is 134 characters:

```
(a) Balks
If there is a runner, or runners, it is a balk when:
```

The actual balk conditions are split across 15 chunks, `6.02(a)(1)`–`(13)`. Retrieval returning those was scored as wrong, and the fact that this empty lead-in ranked **414th** was taken as evidence that retrieval was catastrophic. **The error was in the label.**

### Finding 2: n=3 supports no conclusion

There were only three rule questions. 0.333 means "one out of three," and a single question moves the metric by a third. It was never a basis for a decision.

### Finding 3: the glossary and the rules differ in language composition

ADR-047 recorded that "cross-lingual retrieval works with a single model," but that was an observation on Tier 1. In reality there is a difference.

| | Question | Document |
|---|---|---|
| Tier 1 glossary (43 entries) | Japanese | **Japanese** (`docs/knowledge/*.md` was written in Japanese in-house) |
| Tier 2 rulebook PDF (897 chunks) | Japanese | **English** |

**Only `rules` spans two languages**, and the threshold had never been validated under that condition.

## Decision

### 1. Rebuild the golden set (fix the measurement)

- Repoint the correct chunk_ids at real content chunks. `_rules` now states explicitly: do not designate a lead-in chunk as the correct answer.
- Grow the rule type from **3 to 30 questions**, with the subtype mix shaped by how people actually ask.

| Subtype | Count | Content |
|---|---:|---|
| situation | 9 | Describe a scenario and find the rule |
| paraphrase | 8 | Uses no technical term at all |
| enumeration | 6 | "In what cases…" — the answer is spread over a dozen-plus chunks |
| definition / spec / confusable | 6 | Already perfect; kept for regression detection |
| citation | 1 | Direct rule-number lookup. **Excluded from improvement targets** (real users do not ask this way) |

- The self-imposed rule "do not change existing questions" gained one exception: **corrections are allowed when the correct label itself was wrong.** The harm of continuing to measure against a broken standard is greater.

### 2. Make the distance threshold per-category

`CATEGORY_DISTANCE_THRESHOLDS = {"rules": 0.35}`. The glossary stays at 0.275.

Crossing Japanese and English shifts the distance distribution about 0.07 further out, so the 0.275 chosen for the glossary cut every candidate and **the rerank stage never ran** (0–1 survivors on 15 of 30 questions).

### 3. Introduce HyDE (query rewriting)

`query_rewrite_service.py`. An LLM rewrites the Japanese question as **rulebook-style English**, and that text is embedded for search. The user's input and the final answer both stay in Japanese; the only thing rewritten is the string used for retrieval.

Application is limited to `HYDE_CATEGORIES = ("rules",)`. The glossary is in Japanese, so translating to English would move the query further away.

### 4. Make `category` a required tool argument

`"required": ["query", "category"]`. Both the threshold and the HyDE decision are keyed on `category`, so omitting it drops the configuration back to defaults and nullifies every improvement.

### 5. Give auxiliary LLM calls a `node`

`call_gemini(node=...)` was added, and applied to reranking (`node="reranker"`) and HyDE (`node="hyde"`).

## Alternatives Considered

- **Split it out as a separate `rules_search_tool`**: `category` could be fixed in code, structurally eliminating LLM selection errors. But adding `required` (one line) already removes the "omitted" case, leaving only "chosen wrongly." The cheap fix was tried first, so this is **deferred** — to be revisited if misfire measurements show a problem.
- **Rename the tables and services to `knowledge_base_*`**: the names have drifted from reality, but the retrieval mechanism is identical, and separating them would duplicate the SQL, the service and the evaluation harness. Nothing functional changes for the scope of the impact, so **rejected**. Only the face the LLM sees — the tool description — was brought in line with reality.
- **Ask users to write their questions in English**: out of the question. It pushes an implementation detail onto the user. HyDE achieves the same effect entirely internally.
- **Apply HyDE to every category**: translation is counterproductive for the Japanese glossary. The line is drawn by category.
- **Search with both the rewritten and original query and merge via RRF**: this would rescue cases like `rule_016` where the original question is better, but it adds one more embedding API call. The effect is unverified, so it is **deferred for now**.
- **Loosen the threshold globally**: the glossary already reaches hit@3 of 1.000 at 0.275, so loosening only adds noise. Per-category is the correct shape.

## Consequences

### Measured results (30 rule questions, reranking ON)

| Configuration | hit@3 | hit@5 | MRR |
|---|---:|---:|---:|
| Threshold 0.275 (same as the glossary) | 0.600 | 0.667 | 0.580 |
| + `rules`-specific threshold 0.35 | 0.733 | 0.733 | 0.708 |
| **+ HyDE** | **0.833** | **0.867** | **0.766** |

Across all 40 questions: hit@3 **0.850** / MRR **0.793**. The misfire rate was re-measured with `rules` re-enabled: **0.000 (0/7)**.

### Quantifying the Japanese–English gap

Isolated with `rule_020` ("what happens to a batter who receives four pitches outside the strike zone?", correct answer `def:BASE ON BALLS`).

| String used for retrieval | Rank of the correct chunk | Distance |
|---|---:|---:|
| The Japanese question as-is | **212th** | 0.3244 |
| An equivalent English sentence | **16th** | 0.2450 |

The correct chunk contains `receives four pitches outside the strike zone` — almost a word-for-word match with the question. **Even with matching vocabulary, staying in Japanese put it 212nd.**

At the same time, ranking only 16th in English shows **the language gap is not the sole cause**. All 897 chunks share the same legal English and the same template, so the distance band is narrow (0.026 between the top hit at 0.2190 and the correct chunk at 0.2450). This is the same loss of discriminative power ADR-047 recorded across 43 glossary entries, now occurring at 20× the scale.

### The failure this design revealed, recorded deliberately

**A feature was disabled on the conclusion that accuracy was bad, when in fact the measurement was broken.** The 0.333 behind that decision came from designating an empty lead-in as the correct answer. After repointing the label, the same question moved from 414th to 25th — still outside the top 5, but an order of magnitude different.

**That broken measurement then distorted the next decision too.** The observation that "reranking did not improve rules" was caused by the 0.275 threshold wiping out all candidates, so **reranking had never once executed**. The conclusion "reranking doesn't work" was reached without measuring the cause.

The lesson: **before doubting an accuracy number, doubt the instrument producing it.**

### The limits of HyDE

Net clearly positive, but not universal.

| Question type | Effect |
|---|---|
| Describe a situation and find the rule | **Improved** (`rule_022`, hit by pitch: 126th → within the top 5) |
| Ask for the name of a term | **Worse**. `rule_016` (rundown) lost `run-down` in the rewrite and fell to 180th |
| Look up by rule number | **Worse**. Rewriting drops the number (no real harm — the type is out of scope) |

### Latency

**20–35 seconds** per rule question (HyDE ~10s + reranking ~19.5s + overhead). ADR-047 recorded reranking at 2–15 seconds; this exceeds it. The stages are serial — search on the HyDE output, then rerank that output — so they **cannot be parallelized**. Cutting the number of rerank candidates is the candidate lever for shortening it.

### What got worse / new burdens

- **Two Gemini calls per rule question** (HyDE + reranking). A glossary question takes one (reranking only).
- The latency above.
- **A side effect of unspecified `node` surfaced.** Because `call_gemini` did not set `node`, the rerank's log row (whose content is an array of candidate numbers) was treated by `trace_query_service` as the endpoint's summary row, and the array was displayed as the FINAL RESULT in the Trace Viewer. Both fixes went in: setting `node`, and defensively selecting the summary row by the presence of `total_latency_ms` ([[053-agent-trace-viewer-failure-labeling]]).
- **Tier 2 chunk quality is still unfixed.** Ingestion bugs remain: 12.8% residual page headers, 4.6% lead-in-only stubs, `def:WIND-UP POSITION` split into 28 pieces, and more. Fixing them requires re-ingestion (897 embeddings), so it was split out as separate work.

## Why This Matters

- **Evaluation**: it records not stopping at "accuracy is bad" but identifying and correcting a defect in the measurement system from real data, together with how the numbers moved (0.333 → 0.833) — including the judgment not to trust a metric at n=3.
- **Multilingual RAG**: it quantifies cross-lingual degradation in a single experiment ("212th vs. 16th") and separates the countermeasure (HyDE) from the residual cause (insufficient discriminative power).
- **Failure analysis**: it acknowledges and records that the decision to disable the feature rested on a broken measurement.

## References

- Search service: [backend/app/services/glossary_rag_service.py](../backend/app/services/glossary_rag_service.py)
- HyDE: [backend/app/services/query_rewrite_service.py](../backend/app/services/query_rewrite_service.py)
- Golden set: [backend/tests/golden/retrieval_fixtures.json](../backend/tests/golden/retrieval_fixtures.json)
- Evaluation: [backend/scripts/run_retrieval_eval.py](../backend/scripts/run_retrieval_eval.py) (added `--hyde`) / [run_misfire_eval.py](../backend/scripts/run_misfire_eval.py) (added `--ids`)
- Related ADRs: [[047-rag-chunking-multilingual-embeddings-reranking]] / [[013-centralized-llm-gateway]] / [[053-agent-trace-viewer-failure-labeling]]
