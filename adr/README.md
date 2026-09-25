# Architecture Decision Records (ADR)

This directory records the significant architectural decisions behind Diamond Lens.
This file is the **index**. Each ADR's body lives in its own file (`NNN-kebab-title.md`).

> **Reading the index**: this index covers **54 decisions**, of which **20 have a written ADR** — those rows link to their file. The other **34 are marked `*(TBA)*`: the decision itself is recorded here, but the full write-up has not been authored yet.**
>
> `*(TBA)*` says nothing about whether the decision is live. That is the **Status** column's job:
> - **`*(TBA)*` + ✅** (30 rows) — the decision is **implemented and running in production**; only the ADR document is missing. These are backfill targets.
> - **`*(TBA)*` + 🟡** (4 rows: 044, 045, 046, 048) — **not implemented and not yet decided.** Having no body is the expected state.
>
> For `*(TBA)*` rows, the "decision vs. alternatives" column is a starting point (a seed) for writing, not settled text.

---

## What an ADR is / why we write them

An ADR is a lightweight document that records, one decision per file, which option was chosen at a given point in time and why.
Code shows *what* was done but loses *why* it was done and *what was given up* (the trade-off). An ADR preserves that why.

For this project they are valuable for three reasons in particular.

- **Accountability for technology choices**: questions like "why BigQuery?" or "why Cloud Workflows rather than Airflow?" stay answerable with reasoning and trade-offs.
- **References already exist**: `README_architecture.md` already links ADR-001 through 004, but **the files do not exist** (broken links). Those four need backfilling first.
- **Freshness of decisions**: the chat path was substantially refactored on 2026-05-17 (ADR-010 below), and "why LangGraph was dropped" will be forgotten if it is not recorded now.

---

## Naming and conventions

- **Filename**: `NNN-kebab-case-title.md` (e.g. `001-use-bigquery.md`), matching the existing links in `README_architecture.md`.
- **Numbering**: sequential. Once assigned, a number is never reused, even if it is skipped.
- **Status**: `Proposed` → `Accepted` → (if needed) `Superseded by ADR-NNN` / `Deprecated`.
- **One ADR = one decision.** Never mix several decisions into one file.
- When a decision is reversed, do not delete the old ADR — mark it `Superseded` and reference it from the new one, preserving the history.

### Template (Michael Nygard format — copy and use)

```markdown
# ADR-NNN: <title of the decision>

- Status: Proposed | Accepted | Superseded by ADR-XXX
- Date: YYYY-MM-DD
- Deciders: <who decided>

## Context
What the problem was, and what constraints applied (cost, latency, operations, skills, time).

## Decision
What was adopted.

## Alternatives Considered
- Option A: why it was not adopted
- Option B: why it was not adopted

## Consequences
- What got better / what got worse / what new operational load or technical debt appeared.

## Why This Matters
Why this decision matters to the project as a whole (see the theme codes below).

## References
Links to related PRs, design documents and README sections.
```

---

## Theme codes (mapping legend)

The project's technical areas of concern are organized into 7 codes.
Each ADR carries one or more in its **Theme** column. **★ = a decision that is central to that theme.**

| Code | Theme | Main concerns |
|-------|-------|-----------|
| **AG** | Agentic Architecture | Agentic workflows, multi-agent, MCP servers, LangGraph / ReAct / self-reflection / hierarchical delegation, tool orchestration |
| **EV** | Evaluation & Observability | Evaluation pipelines and observability (accuracy / safety / latency) |
| **LM** | LLM Operations | LLM-native metrics (tokens/sec, cost-per-request), state management, granular tracing |
| **GC** | Cloud Infrastructure | Architecture, deployment and operations on GCP |
| **INT** | Data Integration | Integration with existing data platforms, resolving data silos, security perimeter design |
| **FM** | Foundation Model Usage | Everything around a pretrained model (prompt engineering, RAG, whether to fine-tune, orchestrating external tools) |
| **BP** | Engineering Practices | Repeatable development and operational practices, reusable modules |
| **—** | — | Weakly related to the themes above (solid work, but not this project's focus) |

---

## ADR index

Legend —
**ADR**: a linked number means the write-up exists; **`*(TBA)*` means the body has not been authored yet** (see the note at the top of this file) /
**Status**: ✅ Accepted (decided and implemented) / 🟡 Proposed (undecided, pending review) /
**Tier**: ⭐P1 (large design impact; write first) / P2 / P3 /
**Theme**: the theme codes above (★ = central to that theme)

> **Where the primary sources live**:
> - The product overall → `README.md` / `README_JP.md`
> - Infrastructure, GCP, data flow → `README_architecture.md`
> - **The AI / LLM layer (sections C and D, plus 013/015/016/032/049/050/051) → `README_ai_architecture.md`** ← the main source when writing LLM-related ADRs
> - Feature-level design decisions → `docs/plan_docs/*.md` (internal working documents; not published)

### A. Data & storage

| ADR | Title | Decision vs. alternatives (seed) | Status | Tier | Theme | Primary source |
|-----|---------|----------------------|--------|------|----|---------|
| 001 *(TBA)* | Use BigQuery as data warehouse | Serverless columnar DWH vs. self-hosted PostgreSQL/Snowflake. DWH selection is table stakes | ✅ | P2 | GC★ INT★ | `README_architecture.md` GCP resources / existing links |
| 005 *(TBA)* | Star schema + dbt 4-layer medallion | staging→intermediate→core→marts vs. flat hand-written SQL | ✅ | P2 | INT★ | `README_architecture.md` data transformation layers |
| 006 *(TBA)* | Partition by `game_date` + cluster by player/pitcher/batter | Physical design for billing/scan reduction vs. no partitioning | ✅ | P2 | — | `README_architecture.md` key tables |
| 007 *(TBA)* | Incremental materialization for fact tables | Incremental updates vs. full refresh every run | ✅ | P2 | — | `README_architecture.md` data transformation layers |
| 008 *(TBA)* | fact→mart migration and dual keys (idfg→mlbid, season≥2026 boundary) | A unified mlbid surrogate key vs. keeping the legacy idfg alongside | ✅ | P2 | — | `DATA_LAYER_REDESIGN_PROPOSAL_JP.md` |

### B. Pipelines & orchestration

| ADR | Title | Decision vs. alternatives (seed) | Status | Tier | Theme | Primary source |
|-----|---------|----------------------|--------|------|----|---------|
| 002 *(TBA)* | Separate ETL / dbt / app repos + git submodule | Polyrepo + submodule vs. monorepo | ✅ | P2 | BP INT | Existing links / `README.md` dbt submodule workflow |
| 003 *(TBA)* | Weekly batch processing strategy | Weekly batch vs. streaming/daily | ✅ | P2 | GC★ | Existing links / `README_architecture.md` |
| 004 *(TBA)* | Cloud Workflows over Airflow | Managed serverless vs. a resident Composer/Airflow | ✅ | P2 | GC★ | Existing links / cost breakdown |

### C. LLM / agents

| ADR | Title | Decision vs. alternatives (seed) | Status | Tier | Theme | Primary source |
|-----|---------|----------------------|--------|------|----|---------|
| [009](009-dbt-semantic-layer-over-text-to-sql.md) | dbt Semantic Layer (MetricFlow) over query_maps-based fixed SQL construction | Metric definitions as an SSOT in dbt vs. duplication between query_maps and app-side SQL construction | ✅ (canary) | ⭐P1 | AG★ FM★ | `dbt_semantic_layer_implementation_plan.md` / README #22 |
| [010](010-chat-orchestrator-replaces-langgraph.md) | ChatOrchestrator (function calling, 1 LLM call) replaces Supervisor + 4 LangGraph sub-agents | Raw google-genai + a function-calling loop vs. 4 LangGraph agents (4→1 call). NLU moved into the orchestrator's LLM | ✅ (2026-05-17) | ⭐P1 | AG★ | `README_ai_architecture.md` §1, §9 / `CHAT_ORCHESTRATOR_REFACTOR_PLAN.md` |
| [011](011-retain-langgraph-for-strategy-agent.md) | Retain LangGraph only for StrategyAgent (Plan-and-Execute + parallel fan-out) | Keep the multi-stage graph only for cross-cutting analysis vs. remove it entirely | ✅ | ⭐P1 | AG★ | `MATCHUP_STRATEGY_REPORT_PLAN.md` |
| [012](012-classified-bounded-reflection-retries.md) | Reflection loop with classified, bounded retries | Classify errors as retryable or not, capped at 2 vs. unbounded self-correction | ✅ | ⭐P1 | AG★ | README #4 / `test_reflection_loop.py` |
| [013](013-centralized-llm-gateway.md) | Centralized LLM gateway + cost/token telemetry | Funnel every call through `llm_gateway_service` vs. calling the SDK everywhere | ✅ | ⭐P1 | LM★ EV | README #24 LLM usage cost dashboard |
| [015](015-gemini-context-caching.md) | Gemini context caching | Cache the fixed prefix (~1/10 billing) vs. full billing every time. sha256 key / automatic TTL re-creation / fail-open | ✅ | ⭐P1 | LM★ | `README_ai_architecture.md` §2.5 / `prompt_cache_service.py` |
| [016](016-token-budget-pool-separation.md) | Token budget pool separation (chat / report / shared) | Pool separation so reports cannot starve chat vs. a single pool | ✅ | ⭐P1 | LM★ | `README_ai_architecture.md` §9.5 / `token_budget_service.py` |
| [052](052-build-around-pretrained-no-fine-tuning.md) | Build around pretrained models — no fine-tuning | Prompt engineering + Semantic Layer + context caching vs. SFT/LoRA. States the "deliberately not fine-tuning" decision with its trade-offs | ✅ | ⭐P1 | FM★ | Project-wide position / AI engineering review #25 |
| 014 *(TBA)* | Prompt-as-config (external txt + prompt_registry + versioning) | Externalized, versioned prompts vs. prompts inline in code | ✅ | P2 | FM★ | README #5 |
| [050](050-tools-return-raw-data-orchestrator-composes.md) | Tools return raw data; orchestrator owns response composition | `output_format='data'` so tools return raw data and the orchestrator composes vs. calling a response LLM inside the tool (the legacy two-stage) | ✅ | P2 | AG★ | `README_ai_architecture.md` §1 (crux of the design) |
| 017 *(TBA)* | Default model = Gemini 2.5 Flash (single tier) | One fixed model vs. a difficulty-based cascade (revisited in ADR-045) | ✅/revisit | P3 | LM | README technical stack |

### D. Evaluation & quality

| ADR | Title | Decision vs. alternatives (seed) | Status | Tier | Theme | Primary source |
|-----|---------|----------------------|--------|------|----|---------|
| [018](018-llm-as-a-judge-offline-evaluation.md) | LLM-as-a-Judge (5-panel) offline evaluation | Automatic multi-dimensional scoring by a Judge vs. human review only | ✅ | ⭐P1 | EV★ | README #10 |
| [019](019-shadow-evaluation.md) | Shadow evaluation (champion / challenger) | Sampled comparison alongside production vs. offline only | ✅ | ⭐P1 | EV★ | `SHADOW_EVALUATION_PLAN.md` |
| [020](020-ci-evaluation-gate.md) | CI evaluation gate (golden dataset ≥80% parse accuracy) | A quality gate that blocks the deploy vs. manual verification. **Note: currently all gates are commented out in cloudbuild; golden set has 14 cases at the time of writing** | ✅ (disabled) | ⭐P1 | EV★ BP | `README_ai_architecture.md` §10 / README CI/CD STEP 1.5 |
| [021](021-hitl-golden-flywheel.md) | HITL feedback → golden dataset flywheel | 👎 → assign expected values in the Trace Viewer → approval auto-creates a PR vs. a static test set / BigQuery as the source | ✅ | P2 | EV FM | `README_ai_architecture.md` §6.1 / README #6 |
| 022 *(TBA)* | Schema validation gate (query_maps vs. live BigQuery) | Enforce schema reconciliation in CI vs. discovering mismatches at run time (also commented out) | ✅ (disabled) | P2 | EV BP | README CI/CD STEP 1 |

### E. ML / MLOps

| ADR | Title | Decision vs. alternatives (seed) | Status | Tier | Theme | Primary source |
|-----|---------|----------------------|--------|------|----|---------|
| [025](025-data-drift-detection.md) | Data drift detection (KS/PSI/mean-shift) + CI drift gate | Statistical drift detection gating deploys vs. no monitoring | ✅ | ⭐P1 | EV★ | README #8 / CI/CD STEP 1.6 |
| 026 *(TBA)* | Embedding quality warnings + semantic drift via BQ VECTOR_SEARCH | Serverless vector search vs. a resident dedicated vector DB | ✅ | ⭐P1 | FM★ LM | README #11, #12 |
| 024 *(TBA)* | Model registry (GCS + BQ metadata) + promotion | Versioning plus promotion to active vs. fitting on the spot | ✅ | P2 | — | README #8 |
| 028 *(TBA)* | XGBoost for Stuff+ / Pitching+ / Pitching++ | Gradient-boosted regression vs. linear models or deep learning | ✅ | P2 | — | README #9 |
| 023 *(TBA)* | 3-layer ML separation, no PyTorch in prod | Separate training/inference/application with a light production image vs. a monolith (3.9GB). Weakly related, as the project is *pretrained-model-centric* | ✅ | P3 | — | README ML model architecture |
| 027 *(TBA)* | FT-Transformer encoder + K-means for segmentation | Self-supervised representation learning vs. plain K-means | ✅ (experiment) | P3 | — | README #3 / `test_ft_transformer.py` |

### F. Application / infrastructure / security

| ADR | Title | Decision vs. alternatives (seed) | Status | Tier | Theme | Primary source |
|-----|---------|----------------------|--------|------|----|---------|
| 029 *(TBA)* | Cloud Run (scale-to-zero) over GKE | Serverless containers vs. operating Kubernetes | ✅ | ⭐P1 | GC★ | README infrastructure / cost |
| 031 *(TBA)* | Firebase Auth (public) + service-to-service OIDC (internal) | Two authentication paths vs. one | ✅ | ⭐P1 | INT★ | README security / #22 |
| [032](032-snowflake-trace-id-structured-logging.md) | Snowflake trace_id + structured JSON logging (ContextVar propagation) | Structured logs with a correlation ID vs. plain print | ✅ | ⭐P1 | LM★ EV | `SNOWFLAKE_TRACE_ID_PLAN.md` / `README_ai_architecture.md` §9 |
| 037 *(TBA)* | Terraform brownfield import + Cloud Build multi-gate CI/CD | Importing existing resources with multi-stage gates vs. greenfield or manual | ✅ | ⭐P1 | GC★ BP | `TERRAFORM_INTEGRATION_GUIDE.md` |
| [040](040-mcp-server-exposure.md) | MCP server exposure (Claude Desktop / Cursor) | Usable from external AI clients over the Model Context Protocol vs. our own API only | ✅ | ⭐P1 | AG★ | README technical features |
| [049](049-security-guardrail-pre-llm-defense.md) | Security guardrail: 3-layer pre-LLM input defense | Screen injection / off-topic / length and structure anomalies before the LLM vs. passing everything through or filtering only output | ✅ | ⭐P1 | EV★ | `README_ai_architecture.md` §7 / `security_guardrail.py` |
| 030 *(TBA)* | In-memory rate limit + token budget (single container) | Deliberately skipping Redis vs. a distributed counter (revisited in ADR-048) | ✅/revisit | P2 | LM | README #7 |
| 033 *(TBA)* | SSE streaming for agent reasoning | Progressive display of reasoning over Server-Sent Events vs. returning everything at once | ✅ | P2 | EV | README streaming API |
| 034 *(TBA)* | In-memory trie autocomplete over BigQuery `LIKE` | A resident trie built at startup, ordered by popularity vs. `LIKE '%q%'` on every keystroke. A latency optimization, but feature-scoped | ✅ | P2 | — | `SEARCH_AUTOCOMPLETE_PLAN_VOL1.md` / README #23 |
| 035 *(TBA)* | Feature-flag canary rollout convention | Switch old/new paths by env var with instant rollback vs. a big-bang cutover | ✅ | P2 | BP | README #22, #23 |
| 036 *(TBA)* | Live data via MLB Stats API, no DB persistence | Fetch live per request vs. caching or storing in a database | ✅ | P3 | — | README #14, #17 |
| 038 *(TBA)* | Trivy security scan gate | Block deploys on HIGH/CRITICAL CVEs vs. no scanning | ✅ | P3 | BP | README CI/CD STEP 4, 8 |
| 039 *(TBA)* | Secrets outside Terraform (Secret Manager + GitHub PAT) | Manage secrets outside IaC vs. storing them in tfstate | ✅ | P3 | BP | README infrastructure |

### G. Observability / operations

| ADR | Title | Decision vs. alternatives (seed) | Status | Tier | Theme | Primary source |
|-----|---------|----------------------|--------|------|----|---------|
| 041 *(TBA)* | SLO + error budget policy | Defined SLOs with an error budget vs. no definition | ✅ | P2 | EV BP | `docs/SLO.md` |
| 043 *(TBA)* | Cloud Monitoring custom metrics over Prometheus | Managed monitoring vs. self-operated Prometheus | ✅ | P2 | EV GC★ | `docs/MONITORING.md` / README monitoring |
| 042 *(TBA)* | Incident response runbook | A written incident procedure vs. ad-hoc response | ✅ | P3 | BP | `docs/INCIDENT_RESPONSE.md` |
| 051 *(TBA)* | Append-only LLM logging (daemon thread) + feedback via placeholder INSERT | Asynchronous fire-and-forget writes avoiding UPDATE vs. synchronous writes / direct UPDATE (working around the BQ streaming buffer; note the residual risk of losing logs if the process dies abruptly) | ✅/revisit | P3 | EV LM | `README_ai_architecture.md` §3 |
| [053](053-agent-trace-viewer-failure-labeling.md) | Agent Trace Viewer + failure labeling (riding on the existing log table) | Add node/iteration/tool_calls to `llm_interaction_logs` and mix in tool rows with `model IS NULL` vs. a dedicated trace table. **Records how instrumentation was wrongly aimed at StrategyAgent and moved to ChatOrchestrator once real logs showed it unreachable** | ✅ | ⭐P1 | LM★ EV★ | `README_ai_architecture.md` §9.7 |

### H. Future decisions (Proposed — from DDIA / AI engineering reviews, undecided)

| ADR | Title | Question (seed) | Status | Tier | Theme | Primary source |
|-----|---------|-------------|--------|------|----|---------|
| 044 *(TBA)* | Idempotency keys for POST / LLM calls | How to prevent double billing and double recording | 🟡 | P2 | BP | DDIA review Ch.7 |
| 045 *(TBA)* | Model cascade (Flash → Pro escalation) | Whether to escalate to a larger model only on low confidence | 🟡 | P2 | LM | AI engineering review Ch.7 |
| [047](047-rag-chunking-multilingual-embeddings-reranking.md) | RAG chunking + multilingual embeddings + reranking | BQ vector search + category pre-filter + LLM reranking vs. reviving ChromaDB / hand-writing anticipated questions / threshold tuning alone (measured hit@5 0.800→1.000, MRR 0.658→0.925) | ✅ | P2 | FM★ | AI engineering review Ch.7 |
| [054](054-cross-lingual-rag-hyde-category-thresholds.md) | Restore the official rulebook PDF via cross-lingual RAG (per-category thresholds + HyDE) | A `rules`-specific 0.35 threshold plus HyDE for the Japanese–English gap vs. loosening thresholds globally / asking users to write in English / splitting the table. **Records how the decision to disable on "bad accuracy" turned out to be a measurement bug from wrong golden labels** (rule-type hit@3 0.333→0.833) | ✅ | ⭐P1 | FM★ EV★ | Continuation of ADR-047 / `README_ai_architecture.md` §8r |
| 046 *(TBA)* | Semantic response cache | Whether to repurpose the existing embedding stack as a response cache | 🟡 | P3 | LM | AI engineering review Ch.7 |
| 048 *(TBA)* | Distributed rate limit / circuit breaker standardization | Multi-instance consistency and shared retry/circuit-breaker handling | 🟡 | P3 | BP GC | DDIA Ch.1 / revisiting ADR-030 |

---

## Theme × ADR reverse index

A reverse lookup from each theme to the ADRs that cover it (★ = central to that theme).
Use it to find where the design decisions for a given area are written down.

| Code | Theme | ADRs (★ = central) |
|-------|-------|---------------------|
| **AG** | Agentic / multi-agent / MCP / LangGraph / self-reflection / tool orchestration | **010★, 011★, 012★, 040★ (MCP), 009★, 050★** |
| **EV** | Evaluation pipelines & observability (accuracy/safety/latency) | **018★, 019★, 020★, 049★ (safety), 025★, 013, 032, 033, 041, 043, 051** |
| **LM** | LLM-native metrics (cost-per-request), state management, granular tracing | **013★, 015★, 016★ (cost+state), 032★ (tracing), 017, 026, 030, 045, 046, 051** |
| **GC** | Architecture, deployment and operations on GCP | **029★, 037★, 003★, 004★, 043★, 001★, 048** |
| **INT** | Data platform integration / data silos / security perimeters | **031★ (perimeter), 001★, 005★, 002** |
| **FM** | Prompt engineering / RAG / fine-tuning / tool orchestration (pretrained-centric) | **009★, 014★ (prompt), 052★ (no FT), 026★ (RAG), 047★ (RAG), 021** |
| **BP** | Repeatable development and operational practices | **037, 020, 022, 002, 035, 038, 039, 041, 042, 044, 048** |

---

## Suggested writing order (by design impact)

Tiers are calibrated by **how much a decision shapes this project's design**, and the writing order follows the same ranking.

1. **Agent core (AG, highest priority)**: **010** ChatOrchestrator → **011** StrategyAgent (LangGraph) / **012** reflection (self-reflection) / **040** MCP server / **050** tool-vs-composition split / **052** deliberately not fine-tuning
2. **Evaluation, observability, safety (EV)**: **018** Judge / **019** shadow / **020** CI gate / **049** guardrail (safety) / **025** drift / **032** granular tracing
3. **LLM-native cost / latency / state (LM)**: **013** gateway (cost-per-request) / **015** context caching / **016** token budget pools
4. **GCP build-out and integration (GC / INT)**: **029** Cloud Run / **037** Terraform + CI/CD / **031** OIDC (security perimeter) / **009** Semantic Layer / **026** serverless vector search
5. **Backfilling broken links (lower priority, still required)**: **001–004** (resolving the broken links in `README_architecture.md` — maintenance work rather than a headline)

> Conversely, **001/005/006/007/008 (DWH, dimensional modeling) and 023/024/027/028 (in-house ML training)** are technically solid but **deliberately placed in a lower tier**, because the project's approach is to *build around a pretrained foundation model* (their Theme column is "—" or carries no ★).

---

## Maintenance guidelines

- When a significant technical decision is made, add an ADR in the same PR (also stated in the Contributing section of `README_architecture.md`).
- Keep the "Architecture Decisions" section of `README_architecture.md` in sync with this file's numbers and titles.
- If the index (this file) and a body file diverge in granularity, treat the index as authoritative and update the body.
- If the project's areas of focus change, revisit the **theme codes** and each row's **Theme column** (and let the Tier follow).
