# ADR-009: Adopt the dbt Semantic Layer (MetricFlow) in place of query_maps-based fixed SQL construction

> **TL;DR（日本語）**: 旧経路では、SQL を組み立てる手続き（どの列を読み、SUM か AVG か、GROUP BY をどう置くか）を **`query_maps` 辞書 ＋ 自作の `QueryBuilder`（Python）** が担っていた。これを **dbt Semantic Layer (MetricFlow) の YAML による宣言** に置き換え、**SQL 組み立て自体は dbt 公式ライブラリ `dbt-metricflow` に委譲**した。得たものは 2 つ——(1) 指標追加が Python 改修から YAML 数行に下がった、(2) GROUP BY の誤りや JOIN 粒度による二重計上（fan-out）といった、エラーにならず静かに誤る種類のバグを自前で防ぐ必要がなくなった。代償は MetricFlow を別 Cloud Run サービスとして運用する構成要素の増加。なお旧経路は text-to-SQL ではなく辞書由来の固定 SQL ビルダーであり、SQL 起因の hallucination は元々存在しない。
>
> **TL;DR (English)**: The legacy path built SQL procedurally — a `query_maps` dictionary plus a hand-written `QueryBuilder` (Python) decided which column to read, whether to SUM or AVG, and where to put GROUP BY. That procedure was replaced by **declarations in dbt Semantic Layer (MetricFlow) YAML**, with **SQL assembly itself delegated to dbt's official `dbt-metricflow` library**. Two things were gained: (1) adding a metric dropped from a Python change to a few lines of YAML, and (2) silently-wrong bugs such as a misplaced GROUP BY or double-counting from JOIN fan-out no longer have to be prevented by our own code. The cost is running MetricFlow as a separate Cloud Run service. Note the legacy path was a dictionary-driven fixed SQL builder, not text-to-SQL, so SQL-induced hallucination never existed there.
>
> **A note against overstating this**: This ADR originally claimed that "definitions were consolidated into YAML as a single source of truth," which is **stronger than what actually happened**. Column names such as `ops` still appear in **two places**: `marts/*.sql` (which creates the column) and `semantic_models/*.yml` (which points at it). What was eliminated is not the duplicated column name but **the metric semantics the backend (Python) used to own** — which table, which column, and how to aggregate. See [Consequences](#consequences) for details.

> **Note on the title**: This ADR was originally titled "replaces two-stage text-to-SQL," but the legacy path never had an LLM generate SQL; it assembled parameterized SQL through fixed logic driven by the `query_maps` dictionary. The title and body have been corrected to match that history (hallucination was not a problem of the legacy path — see Context). The filename remains `009-dbt-semantic-layer-over-text-to-sql.md` so existing links keep working.

- Status: Accepted (canary — enabled only in the Cloud Run environment via the `USE_SEMANTIC_LAYER` flag)
- Date: 2026-05-17
- Deciders: Project owner

## Context

The legacy chat path **hard-coded metric definitions into a Python dictionary in `query_maps.py`** — what OPS means, which table and column holds RBI, whether to SUM or AVG — and the application read that dictionary to **construct parameterized SQL through fixed logic** before querying BigQuery.

> **Important correction**: This path was once described as "two-stage text-to-SQL" with "hallucination from free-form SQL generation." That characterization **did not match the implementation**. The **LLM never generated a SQL string**. Its only role was NLU: turning natural language into structured parameters such as `{query_type, metrics, name, season...}`. SQL was built by [QueryBuilder](../backend/app/services/query_builder.py), which looked up table and column names in the `query_maps` / `METRIC_MAP` dictionaries, bound values as `@param`, and validated everything through `validate_query_params` against a whitelist (query_type, metrics and columns had to exist in the dictionary). **SQL-induced hallucination — wrong column names, invented metrics — was structurally impossible, and no such hallucination ever existed in that generation.**

The **real** weaknesses of the legacy path were the following, none of which are hallucination.

- **Correctness of SQL assembly rested on hand-written code**: [query_builder.py](../backend/app/services/query_builder.py) owned `_build_select_clause`, `_build_where_clause`, `_build_group_by_clause` and `_build_order_by_clause`. A misplaced GROUP BY, or double-counting caused by joining tables of different grain (fan-out), **raises no error and returns a plausible-looking number**, which makes it hard to notice. For example, joining a one-row-per-player-season table (`hr = 54`) with a per-pitch-type table (3 rows) and summing yields 162 home runs without a single exception. Preventing this class of bug was entirely the application's responsibility.
- **Adding a metric was expensive**: `METRIC_MAP` spelled out every "metric × breakdown" combination by column name — `"homerun"` alone had 12 entries. Each new metric required both a dictionary entry and new aggregation logic in `QueryBuilder`'s Python code, meaning a code change, tests and a deploy.
- **Aggregation logic had no clear home**: `query_maps` could only carry column names. The rule "HR is summed, AVG is averaged" lived neither in the dictionary nor in the table — it was buried in Python.
- **Hard-coding**: this violates the project's quality rule that `METRIC_MAP` and similar structures should be derived dynamically from existing sources rather than written inline.
- **Rigid coverage**: only query types already present in the dictionary could be handled, and a new category required changes to both the dictionary and the builder.

The problem, stated plainly: **stop hand-writing the procedure that assembles SQL, and express metric semantics declaratively instead.**

## Structural Comparison (Before → After)

### Terminology: "dbt model" and "dbt Semantic Layer" are different things

These two terms appear throughout this ADR and refer to **two different layers inside the same dbt project**. They are easy to confuse, so they are separated up front.

```
metricflow/dbt_project/models/
│
├─ core/*.sql, marts/*.sql        ← ① dbt models (transformation layer)
│     SELECT ... FROM ... SQL.
│     The layer that physically creates tables/views in BigQuery.
│     e.g. mart_batter_season_stats.sql produces a table with hr, ops, ...
│
├─ semantic_models/*.yml          ← ② dbt Semantic Layer (semantic layer)
│     Points at the tables ① created and declares
│     "which column is a measure, and how is it aggregated."
│     e.g. batter_season.yml
│           model: ref('mart_batter_season_stats')   ← references ①
│           measures: { name: home_runs, agg: sum,     expr: hr  }
│                     { name: ops,       agg: average, expr: ops }
│           dimensions: season_year, player_name ...
│
└─ metrics/*.yml                  ← continuation of ② (the exposed metric names)
      e.g. batting_metrics.yml
            - name: home_runs_total   type: simple   measure: home_runs
            - name: risp_woba         measure: clutch_woba
              filter: situation_type = 'risp'        ← filters live on the definition side too
```

- **① dbt models** = the SQL that creates tables. **Used identically before and after; this ADR did not change them.**
- **② dbt Semantic Layer (MetricFlow)** = YAML metric definitions layered on top of ①. **This is the layer this ADR introduced.**

So when the TL;DR says definitions were "duplicated between the app's `query_maps` dictionary and the dbt models," it means **① (table definitions / column semantics) and `query_maps` (the app's own column names and aggregation rules) were separately stating the same thing**. ② was introduced afterwards to resolve that duplication; **a dbt model is not the same thing as the dbt Semantic Layer**.

### Before reading the diagrams: there are two timelines

The diagrams below separate "timeline A (batch, ahead of time)" from "timeline B (the moment a question arrives)". **These run at different times.** Reading them as one flow is confusing, so keep them apart.

- **Timeline A (daily batch, ahead of time)**: `dbt run` executes `marts/*.sql` and creates physical tables in BigQuery. It finishes long before, and independently of, any user question. **Identical in the old and new structures — unchanged by this ADR.**
- **Timeline B (real time, when a question arrives)**: a SELECT is issued against the tables already built in A, and an answer is returned. **This is the only part this ADR changed.**

### Old structure: `query_maps` dictionary + fixed SQL builder

```
━━━ Timeline A: batch (independent of questions; already finished) ━━━━━━━━

   marts/*.sql  ──dbt run──▶  physical tables exist in BigQuery
   (dbt models)                 e.g. mart_batter_season_stats
                                  columns: hr, ops, avg ...
                                      └ formulas such as "OPS = OBP + SLG"
                                         are written only inside this SQL

━━━ Timeline B: the moment a question arrives ━━━━━━━━━━━━━━━━━━━━━━━━━━

   User question: "What were Ohtani's HR and OPS in 2024?"
        │
        ▼
   LLM (NLU only — generates no SQL whatsoever)
        │  → {query_type: season_batting, metrics: [hr, ops], season: 2024}
        ▼
   validate_query_params (whitelist: only values present in the dictionary pass)
        │
        ▼                          ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
   QueryBuilder ──────reads───────▶┃ metric definitions (app side) ┃
        │  · which table to read      ┃ query_maps.py / METRIC_MAP  ┃
        │  · which column to read     ┃  "the ops column lives in   ┃
        │  · SUM or AVG               ┃   fact_batting_..."         ┃
        │    ↑ this alone is not in   ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
        │      the dictionary; it is            ⚠
        │      buried in Python code            ⚠ two places state the same
        ▼ parameterized SQL (@param binding)    ⚠ thing as the SQL in timeline A
        │
        ▼
   BigQuery (reads the tables built in timeline A) → result

[Weakness] We hand-write the Python that assembles SELECT / WHERE / GROUP BY.
           A misplaced GROUP BY or double-counting from JOIN grain raises no
           exception and returns a plausible number — it fails silently.
           Worse, "HR sums / AVG averages" lives inside Python, with no clear home.
           Every new metric requires changes to both the dictionary and Python.
[Not a weakness] The LLM writes no SQL, so SQL-induced hallucination never existed.
```

### New structure: the dbt Semantic Layer (MetricFlow) as the source of truth

```
━━━ Timeline A: batch (★identical to the old structure; nothing changed) ━━

   marts/*.sql  ──dbt run──▶  physical tables exist in BigQuery
   (dbt models)                 e.g. mart_batter_season_stats

        ※ dbt models do not appear at all below this line (timeline B),
           because the job of creating tables is already done.

━━━ Timeline B: the moment a question arrives (★only this changed) ━━━━━━━

   User question: "What were Ohtani's HR and OPS in 2024?"
        │
        ▼
   ChatOrchestrator / LLM (1-pass function calling)
        │  → query_metric(metrics=["home_runs_total", "ops_metric"], ...)
        │  ※ the list of selectable metric names is fetched dynamically from
        │     MetricFlow at startup and injected into the prompt (never hard-coded)
        ▼ OIDC service-to-service authentication
   mlb-metricflow-server (Cloud Run)
        │                          ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
        │ ① read definitions ─────▶┃ metric definitions (the SSOT)   ┃
        │                          ┃ semantic_models/*.yml           ┃
        │                          ┃   model: ref('mart_...')        ┃
        │                          ┃   = merely points at A's table  ┃
        │                          ┃   measure + agg(sum/average)    ┃
        │                          ┃ metrics/*.yml                   ┃
        │                          ┃   metric name + filter          ┃
        │ ② assemble SQL           ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
        ▼ generated SELECT statement
   BigQuery (merely reads the tables built in timeline A) → result

[Resolved] The code that assembles SELECT / GROUP BY is gone from our repo.
           We now write only the declaration ("ops aggregates as average" — the what);
           how the SQL is built (the how) belongs to dbt-metricflow.
           Fan-out double-counting is structurally avoided by an engine that
           knows the grain. Adding a metric is a few lines of YAML, no Python.
[Not resolved] Column names (ops, etc.) still live in both marts/*.sql and the YAML.
           The YAML creates no columns — it only points at existing ones — so a
           metric with a new formula still requires editing marts/*.sql and dbt run.
[Cost] MetricFlow becomes an additional Cloud Run service (infra + OIDC auth).
       Environments with `USE_SEMANTIC_LAYER=false` fall back to the old structure,
       so both paths are maintained in parallel during the canary period.
```

> **A common misconception**: MetricFlow does not "assemble SQL to build dbt models." The dbt models (tables) are already complete in timeline A. What MetricFlow assembles is **the SELECT statement that reads those finished tables**. Nor is the YAML a specification used to verify the result afterwards — it is **the raw material for assembling SQL**. The dependency always points one way, `YAML → dbt model` (the YAML references the model), never the reverse.

### Summary of the difference

| Aspect | Old structure (`query_maps` + builder) | New structure (Semantic Layer) |
| --- | --- | --- |
| **Where the SQL-assembly code lives** | Our repo (`query_builder.py`) | **A pip dependency (`dbt-metricflow`) — not in our repo** |
| **Who owns GROUP BY / fan-out bugs** | We do | dbt Labs (the engine tracks grain) |
| Style | Procedural (the how, in Python) | Declarative (the what, in YAML) |
| Where aggregation (SUM/AVG) lives | Inside the builder's Python (implicit) | `agg:` in the YAML (explicit) |
| Cost of adding a metric | Dictionary + Python change, tests, deploy | A few lines of YAML (when exposing an existing column) |
| Where column names (`ops`, etc.) appear | `marts/*.sql` and `query_maps.py` — 2 places | `marts/*.sql` and the YAML — **still 2 places** |
| Adding an actual new column | Edit `marts/*.sql` → `dbt run` | **Same (unchanged)** |
| Role of the LLM | Natural language → structured parameters (NLU) | Names validated metrics via function calling |
| Does the LLM write SQL? | No | No (**neither does**) |
| dbt models (`marts/*.sql`) | Used | **Same ones used (unchanged)** |
| Moving parts | Backend only | Backend + MetricFlow Cloud Run (+ OIDC) |

**How to read this table**: the difference is *not* "definitions went from two places to one" — column names still live in two places. The difference is concentrated in the top three rows: **we stopped hand-writing the SQL-assembly procedure and moved responsibility for its correctness to an off-the-shelf library.**

## Decision

**Stop hand-writing the SQL-assembly procedure in Python and replace it with declarations in the dbt Semantic Layer (MetricFlow).** The LLM does nothing more than name metrics through **1-pass function calling**.

- Metrics, dimensions and aggregations (`agg: sum` / `average`) are defined in dbt semantic models (`metricflow/dbt_project/models/semantic_models/*.yml`). For example, [batter_season.yml](../metricflow/dbt_project/models/semantic_models/batter_season.yml) defines `home_runs = sum(hr)` and `ops = average(ops)`.
- **SQL string assembly is performed by `dbt-metricflow` (a pip dependency).** Our own [server.py](../metricflow/server.py) is 209 lines — a thin wrapper that shells out to the `mf` CLI — and contains no line that builds SQL.
- The LLM (ChatOrchestrator) **only passes validated metric names as arguments**; it never generates SQL freely. The vocabulary is fetched dynamically from MetricFlow through `semantic_layer_client` and injected into the prompt ([[010-chat-orchestrator-replaces-langgraph]]).
- MetricFlow runs as a separate Cloud Run service (`mlb-metricflow-server`), called from the backend over **OIDC service-to-service authentication** ([semantic_layer_client.py](../backend/app/services/semantic_layer_client.py)).
- The `USE_SEMANTIC_LAYER` flag enables it **as a canary in the Cloud Run environment only**. Locally, or when unset, the legacy (`query_maps`) path is used as a fallback ([[035-feature-flag-canary-rollout]]).

## Alternatives Considered

- **Keep `query_maps` + the fixed SQL builder (status quo)**: correctness of SQL assembly would remain dependent on hand-written code, and every new metric would still require a Python change. This is precisely what the ADR set out to fix (note that the legacy path built SQL from a dictionary rather than via an LLM, so the target was never hallucination).
- **Keep `query_maps` but enrich it**: a fatter dictionary still cannot express aggregation, and GROUP BY / fan-out safety would still depend on the quality of `QueryBuilder`. The underlying structure — hand-writing the procedure — would not change.
- **Move to genuine two-stage text-to-SQL (let the LLM generate SQL)**: this would **introduce** SQL-induced hallucination — wrong column names, invented metrics — deliberately manufacturing a problem the legacy path structurally avoided. Rejected.
- **Adopt a BI tool's semantic layer (Looker, etc.)**: heavy, and excessive for pulling metrics directly from an LLM. Layering a semantic layer onto dbt — the existing transformation platform — is more coherent.

## Consequences

**What got better (only two things)**

1. **Responsibility for SQL assembly moved to an off-the-shelf library.** A misplaced GROUP BY, or double-counting from joining tables of different grain (fan-out), raises no exception and returns a plausible number, which makes it hard to find. MetricFlow builds SQL with knowledge of each measure's grain, structurally avoiding that class of accident. If a bug exists, it is dbt Labs' bug — and being used worldwide, that code breaks less often than a bespoke builder.
2. **Adding a metric got cheaper.** Exposing an existing column takes a few lines of YAML, with no Python change, test cycle or deploy. Aggregation is stated explicitly on the definition side as `agg:`.

**Stated plainly, to avoid overstating the result**

- **"Definitions became a single source of truth" is inaccurate.** Column names such as `ops` **still exist in two places**: `marts/*.sql` (which creates the column) and `semantic_models/*.yml` (which points at it). What was eliminated is the semantics the backend (Python) used to hold, not the duplicated column name.
- **The YAML does not create columns.** A metric requiring a new formula must first be added to `marts/*.sql` and materialized with `dbt run` — the same procedure as before.
- **The improvement from `ref()` amounts to "the reference is now validated."** The old `"table_id": "fact_batting_stats_with_risp"` was a Python string connected to nothing, whereas `model: ref('mart_batter_season_stats')` resolves through dbt's dependency graph. That said, parsing does not guarantee that `expr: ops` refers to a column that actually exists.

**What got worse / new operational load**

- Running MetricFlow as a separate Cloud Run service adds infrastructure and authentication (OIDC) moving parts.
- Semantic Layer coverage is limited to defined metrics; questions outside it (head-to-head history, per-pitch-type breakdowns, etc.) still need the legacy tools.
- During the canary phase (`USE_SEMANTIC_LAYER`), the legacy path must be maintained in parallel.

**When this is not worth it**

This change is bought **at the price of operating one more Cloud Run service**. For a project with a handful of metrics it is plainly excessive, and `query_maps` plus a hand-written builder is lighter. This project exposes close to 200 metrics and adds new ones continuously, which is what makes the trade worthwhile.

## Why This Matters

- **A pretrained-model-centric design**: having the LLM call validated metric definitions rather than write SQL matches the project's approach of leaving the model itself untouched and building around it ([[052-build-around-pretrained-no-fine-tuning]]). Note that "the LLM does not write SQL" was equally true of the legacy path and is not a difference introduced here.
- **Tool orchestration**: exposing the Semantic Layer to the LLM as a tool, invoked in a single function-calling pass, is central to the agentic design.

## References

- Design plan: `docs/plan_docs/dbt_semantic_layer_implementation_plan.md`
- Implementation: [backend/app/services/semantic_layer_client.py](../backend/app/services/semantic_layer_client.py) / [metricflow/dbt_project/models/semantic_models/](../metricflow/dbt_project/models/semantic_models/)
- Legacy path: [backend/app/config/query_maps.py](../backend/app/config/query_maps.py) (hard-coded dictionary)
- Related ADRs: [[010-chat-orchestrator-replaces-langgraph]], [[050-tools-return-raw-data-orchestrator-composes]], [[052-build-around-pretrained-no-fine-tuning]], [[035-feature-flag-canary-rollout]]
