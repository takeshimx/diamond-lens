# ADR-021: The HITL flywheel — turning thumbs-down questions into CI test cases

> **TL;DR（日本語）**: 開発者が自分で書くテストケースは、結局その開発者が最初から想定していた質問にしかならない。実際に壊れている箇所はそこにはない。👎 は違う。「本当に壊れた」という証拠そのものである。そこで、👎 が付いたやり取りを Trace Viewer 上で人が「本来の正解」に書き直し、承認したものを `golden_dataset.json` に追加する PR まで自動で作る。
>
> 最大の判断は、**CI がテストの基準として読むファイルを、BigQuery のテーブルにせず git 上の `golden_dataset.json` のままにした**ことである。👍👎 も、人が入力した正解も、すべて従来どおり BigQuery に書き込まれる。BigQuery を減らしたわけではない。承認ボタンが行うのは、その BigQuery のデータを読んで `golden_dataset.json` への PR を作ることだけで、CI が BigQuery を直接読むことはない。基準を変えるにはマージが要る、という一点を確保するためである。
>
> 実装上の要点は 2 つ。1 つ目は結合キーで、👎 は元のログ行を更新せず別行として INSERT され、その行の `trace_id` は NULL だった（実データを 1 行引いて確認した）。よって **`request_id`** で突き合わせる。2 つ目は取りこぼしの扱いで、golden 側の構造規則を満たさないものは PR に含めず、**BigQuery に残したまま保留**する。
>
> 自動化したのは記録・抽出・検証・PR 作成まで。**正解かどうかの判断と、PR のマージは人が行う**。
>
> **TL;DR (English)**: Test cases a developer invents are questions the developer already anticipated — they do not correlate with what is actually broken, whereas a 👎 _is_ evidence of a real failure. So **thumbs-down traces are turned into expected values inside the Trace Viewer, and approved ones are auto-assembled into a PR against `golden_dataset.json`**. The key decision is making **git — a PR — the exit, not BigQuery**: the criteria a gate enforces are exactly the data that must stay under review, or the bar silently shifts. Feedback is INSERTed as a separate row with a NULL `trace_id`, so the join key is **`request_id`** (verified by pulling a real row). Cases that violate the golden set's structural rules are **held in BigQuery rather than promoted**. Automation covers capture, extraction, validation and PR creation — **a human still judges the expected value and merges**.

- Status: Accepted
- Date: 2026-09-11
- Deciders: Project owner

## Context

`golden_dataset.json` is the only test set the CI accuracy gate reads (`evaluate_llm_accuracy.py`, threshold 80%). How its contents grow determines the effectiveness of the entire evaluation layer.

Writing cases by hand has a ceiling. The questions a developer thinks of are the questions that developer already anticipated. **What is actually broken usually lies outside that set.** A thumbs-down in production, by contrast, is the fact of a real failure. Converting those into regression tests lets the test set grow along the distribution of questions users actually ask.

### Limits of the previous implementation

A path for extracting thumbs-down cases already existed.

```
👎 → BigQuery → extract_golden_dataset.py → pending_review.json
   → a human hand-edits the TODOs in an editor → approve_to_golden.py → golden_dataset.json
```

It had three problems.

1. **Every step was a manual command.** There was no scheduler and no UI, and in practice it had never been run once.
2. **Expected values were entered in a text editor.** The design had a human fill in `"TODO"` inside `pending_review.json`, where a misspelled `query_type` would go unnoticed.
3. **The review queue was invisible.** There was no way to see how many cases were waiting or what to handle next.

### Framing (settled before design)

What this mechanism **does not** do was decided first. Left vague, it gets mistaken for "a system where the LLM autonomously gets smarter."

- Neither model weights nor prompts **change automatically**. The only thing that grows is the set of test cases.
- A thumbs-down does not directly produce an improvement. It produces **a list of known failures worth fixing**.
- Answers improve when a human fixes them; what this mechanism guarantees is **that they never break again afterwards**.

In short, it brings the standard regression cycle — bug report → write a reproducing test → fix → test goes green — to LLM evaluation. It differs from ordinary regression testing in two ways. The pass condition is not "no exception was raised" but "the parsed `query_type` / `name` / `metrics` match." And because an LLM's output is not identical every time, **a human approval step (HITL) deciding what counts as correct cannot be removed**.

## Decision

**Turn thumbs-down traces into expected values inside the Trace Viewer, and automatically build a PR that folds the approved ones into the golden set. Keep the human's work entirely within the Trace Viewer.**

```
[HUMAN] Trace Viewer
   ├─ failure labels (the 7 axes from ADR-053)
   └─ enter the expected value → save
        ↓
   [ Approve and create PR ]
        ↓
[AUTOMATED]
   read trace_expectations
     → fetch the latest golden_dataset.json from GitHub
     → decide promotion (the two rules below)
     → create branch → commit → open PR
```

### 1. Thumbs-down joins on `request_id` (not `trace_id`)

Feedback does not update the existing log row; it is **INSERTed as a separate row** with `user_query='[FEEDBACK_UPDATE]'`, because the streaming buffer does not permit UPDATE.

Pulling one real row to check showed that this row has `node` **and `trace_id` both NULL**. The implementation fills `trace_id` when it can read it from a ContextVar (a per-request variable), but submitting feedback is a *different* request from the original chat — so the original chat's `trace_id` is simply not there.

```
the 👎 row:  trace_id = NULL, node = NULL, request_id = present
```

Joining on `trace_id` is therefore impossible, and `request_id` serves as the join key instead. That exactly one `request_id` corresponds to one trace was verified against real data.

This fact also explained a bug in the detail screen. Because `get_trace` queried `WHERE trace_id = @trace_id`, it never picked up the 👎 row, leaving **the rating chip permanently invisible**. That query was re-pointed at `request_id` so the two merge.

### 2. "Failed step" and "thumbs-down" are different axes

The existing `only_failed` filter looks at `failed_steps > 0` — whether a tool execution raised an exception.

There is a concrete example. A trace requesting `career_pitching` recorded every step as `success = true` / `ok: true`, yet the final answer was "invalid input detected." The fact that the guardrail rejected the request was never recorded as a failure.

```
As instrumented: all steps succeeded, no FAIL chip
In reality     : a complete failure
```

**This class of failure will never be found through `only_failed`.** User rating has to exist as an axis separate from step success, so `only_bad_rating` was added.

### 3. The vocabulary for expected values derives from the tool schema enum

Hard-coding the choices into the frontend invites them to drift out of sync when the enum changes (the same class of accident recorded for `_split_types` in ADR-053). They are served from the backend via `GET /traces/expected-options` instead.

Where to derive them from was a stumble worth recording. The first attempt expanded `QUERY_TYPE_CONFIG`. But that structure holds splits in two levels (`batting_splits` → `risp`), so a choice came out as a single dotted value like `batting_splits.risp`. **What the LLM actually emits is two fields — `query_type="batting_splits"` and `split_type="risp"`** — and `golden_dataset.json` is written that way too. The shape matched neither the existing golden set nor the evaluation script.

The correct source is **the enum on the tool schema's `FunctionDeclaration`**. The authoritative vocabulary is the declaration of what the LLM may choose, not the implementation side (`query_maps`).

### 4. Expected values are append-only, and the UI locks them after saving

The design mirrors `trace_labels`: the `trace_expectations` table is only ever appended to. Relabeling is expressed as a new INSERT, and readers take the row with the latest `created_at`.

In the UI, however, **a saved expected value is read-only by default** and unlocks only when the user explicitly presses "edit." This is the source data for the golden set, and the lock prevents accidentally overwriting it on a screen opened merely to look.

### 5. The criterion CI reads is a file in git, not a BigQuery table

**This is not about writing less to BigQuery.** Thumbs-up and thumbs-down, and the expected values a human enters, all still go to BigQuery. The decision concerns exactly one thing: what CI reads when it scores.

| Stage | What happens | Where the data goes |
| --- | --- | --- |
| ① Recording 👍👎 | The user presses a button | BigQuery (a `[FEEDBACK_UPDATE]` row) |
| ② Entering the expected value | A human enters and saves it in the Trace Viewer | BigQuery (`trace_expectations`) |
| **③ Reflecting it into CI's criteria** | A human presses "approve and create PR" | **Read from BigQuery, open a PR in git** ← the decision |

Only when the PR created at ③ is merged does CI's scoring criterion change. There were two options for this stage.

| Option | Content | Drawback |
| --- | --- | --- |
| A. BigQuery as the source | Approval INSERTs into a `golden_dataset` table, which CI reads at run time | No diff history and no review — **the pass/fail bar changes without anyone noticing** |
| **B. git as the source (chosen)** | Approval calls the GitHub API to open a PR; the gate changes only on merge | Somewhat heavier to implement |

B was chosen because `golden_dataset.json` is not "test data" but **the yardstick that decides pass and fail**.

A concrete example. Suppose a question's expected answer is mistakenly approved as `query_type: "batting_splits"` when it should be `career_batting`.

- **Option A**: from that moment CI scores against the wrong value — and **turns red when the LLM correctly returns `career_batting`**. Correct behavior gets reported as failure, while the fact that the yardstick bent never surfaces anywhere. A BigQuery INSERT leaves neither a diff nor a review, so there is no way to trace who entered that value or when.
- **Option B**: a PR appears and the diff `+ "query_type": "batting_splits"` is visible. It can be caught before merge. Even if it slips through, `git blame` recovers the history and `git revert` undoes it.

Put plainly: **when code breaks, a test turns red and we notice; when the yardstick breaks, no mechanism exists to detect it.** Keeping test code in git under review is ordinary practice, and B simply extends that practice to the test *data*. Option A is the equivalent of keeping test code in a database where anyone can rewrite it without review.

Note also that when building the PR, the base `golden_dataset.json` is **always read from GitHub**. The copy baked into the Cloud Run container is from build time and is stale if another PR has merged since; writing back from stale content would revert those changes.

## 6. Cases that break the structural rules are held rather than promoted

`tests/test_llm_evaluation.py` imposes rules on the golden set's contents. Breaking them fails CI with a **structural error** before the accuracy gate is even reached.

| Rule | Why a violation is held back |
| --- | --- |
| `query_type` must exist in `QUERY_TYPE_CONFIG` | A test for an unimplemented feature will never go green no matter how the prompt is fixed |
| At least 3 cases per category | Adding a single case in a new category fails `test_category_coverage` |

Held cases **stay in BigQuery**. The human's judgment ("this is the right answer") is itself correct; what is missing is the implementation on the receiving side. There is no reason to delete the record — running the same command after the implementation lands adds it to the golden set unchanged.

The decision logic lives in `golden_promotion_service`, and both the UI path (`golden_pr_service`) and the local CLI (`scripts/approve_to_golden.py`) call the same functions. Implementing it twice would let the golden set's contents diverge depending on which route was taken.

## Consequences

### What was gained

- A thumbs-down turns from "a forgettable row in BigQuery" into "a red test that will not go away."
- The second and subsequent occurrences of the same bug are caught by CI before reaching users (only the first occurrence is reactive).
- The review queue is visible in the UI and shrinks as it is worked.

### Constraints accepted

- **Human work does not disappear.** Despite the name "flywheel," a human turns it. Automation covers capture, extraction, validation and PR creation; judging the expected value and merging the PR remain human tasks.
- **Only the parse layer can be scored.** `evaluate_llm_accuracy.py` compares the arguments passed to a tool without executing the tool itself. Bugs where "the LLM's parse is right but everything downstream is broken" — the guardrail example above — cannot be caught in the golden set. `evaluate_with_llm_judge.py`, or unit tests on the code in question, cover that.
- **Unimplemented features cannot become tests.** The idea that "a red PR is a ticket awaiting a fix" only holds where a prompt or logic change can fix it. Adding a case for a feature that does not exist would keep CI red forever, so those are held.
- A GitHub fine-grained PAT (Contents / Pull requests, read-write) becomes an operational prerequisite. The app still starts without it and fails explicitly only when PR creation is invoked.

### Debt surfaced along the way (not addressed here)

`career_pitching` is **declared in the tool schema but absent from both `query_maps` and the guardrail whitelist**. The allow-list for `query_type` is split across three places (6 values in the tool schema, 5 in `query_maps`, 4 in `validate_query_params`), with the guardrail's being the narrowest. As a result, pitchers' career totals and some splits are rejected as "invalid input." Since the pitchers' career-totals table is not yet in place, this is left alone.

## References

- [ADR-053: Agent Trace Viewer and failure labeling](053-agent-trace-viewer-failure-labeling.md) — the 7 failure-label axes and trace instrumentation
- [ADR-049: Security guardrail](049-security-guardrail-pre-llm-defense.md) — the `validate_query_params` referenced above
- [ADR-032: trace_id and structured logging](032-snowflake-trace-id-structured-logging.md)
- `backend/app/services/golden_promotion_service.py` — promotion logic (no I/O)
- `backend/app/services/golden_pr_service.py` — PR creation via the GitHub API
- `backend/app/services/trace_expectation_service.py` — recording expected values and deriving the vocabulary
- `backend/sql/create_trace_expectations.sql`
