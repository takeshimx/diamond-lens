# MLB Analysis Dashboard - System Documentation

> Complete technical documentation for the MLB Analytics Dashboard platform

## Quick Navigation

| Section | Description |
|---------|-------------|
| [Architecture Overview](#architecture-overview) | System architecture and component relationships |
| [Service Catalog](#service-catalog) | All microservices and their details |
| [Data Flow](#data-flow) | How data flows through the system |
| [GCP Resources](#gcp-resources) | BigQuery, Cloud Run, and other GCP services |
| [Quick Commands](#quick-commands) | Common operations and CLI commands |

---

## Architecture Overview

### High-Level Architecture

```mermaid
graph TB
    subgraph "External Data Sources"
        MLB[MLB Stats API]
        Statcast[Statcast Data API]
    end

    subgraph "ETL Layer - Cloud Run"
        ETL[mlb-analytics-etl-service-v2<br/>Python Flask<br/>Weekly data extraction]
    end

    subgraph "Data Warehouse - BigQuery"
        RawData[(mlb_raw_data<br/>- statcast_2021_partitioned<br/>- statcast_2022-2025<br/>- dim_players<br/>- fact_batting_stats_staging<br/>- fact_pitching_stats_staging)]
    end

    subgraph "Transformation Layer - dbt + Cloud Build"
        Staging[Staging Layer<br/>stg_statcast_events<br/>stg_batting_stats<br/>stg_pitching_stats]
        Intermediate[Intermediate Layer<br/>int_statcast_risp_events<br/>int_statcast_bases_loaded<br/>int_statcast_runner_on_1b]
        Core[Core Layer<br/>fact_batting_stats_master<br/>fact_pitching_stats_master<br/>statcast_2025_partitioned]
        Marts[Marts Layer<br/>tbl_batter_clutch_risp<br/>tbl_batter_clutch_bases_loaded<br/>tbl_batter_monthly_*]
    end

    subgraph "Authentication Layer"
        FirebaseAuth[Firebase Authentication<br/>Google Sign-In<br/>ID Token Verification]
    end

subgraph "Application Layer - Cloud Run"
        Backend[mlb-diamond-lens-api<br/>FastAPI<br/>REST API endpoints]
        Frontend[mlb-diamond-lens-frontend<br/>React + Vite<br/>User dashboard]
        MCPServer[MCP Server<br/>Model Context Protocol<br/>Claude Desktop/Cursor]
        
        subgraph "AI Core"
            StandardAI[Standard AI Service<br/>Gemini 2.5 Flash<br/>Simple Q&A]
            subgraph "Multi-Agent System"
                Supervisor[SupervisorAgent<br/>Query Routing]
                StatsAgent[StatsAgent<br/>Season Analytics]
                MatchupAgent[MatchupAgent<br/>Matchup History]
            end
        end
    end

    subgraph "Orchestration Layer"
        Scheduler[Cloud Scheduler<br/>Weekly: Sunday 6:00 AM JST]
        Workflows[Cloud Workflows<br/>mlb-pipeline<br/>Orchestrates entire pipeline]
    end

    subgraph "HITL Feedback Loop"
        FeedbackUI[Feedback UI<br/>👍👎 + Category + Reason]
        FeedbackBQ[(BigQuery<br/>llm_interaction_logs<br/>user_rating, category, reason)]
        PendingReview[pending_review.json<br/>Human Review]
        GoldenDataset[golden_dataset.json<br/>LLM Evaluation]
    end

    subgraph "Monitoring & Alerts"
        CloudMonitoring[Cloud Monitoring<br/>Custom Metrics<br/>Alert Policies<br/>Dashboards]
        Discord[Discord Webhook<br/>Pipeline status notifications]
    end

    MLB --> ETL
    Statcast --> ETL
    ETL --> RawData

    RawData --> Staging
    Staging --> Intermediate
    Staging --> Core
    Intermediate --> Marts
    Core --> Marts

    Marts --> Backend
    Marts --> MCPServer
    Frontend --> FirebaseAuth
    FirebaseAuth --> Backend
    Backend --> StandardAI
    Backend --> Supervisor
    MCPServer --> StandardAI
    Supervisor --> StatsAgent
    Supervisor --> MatchupAgent
    StandardAI --> Frontend
    StatsAgent --> Frontend
    MatchupAgent --> Frontend

    Scheduler --> Workflows
    Workflows --> ETL
    Workflows --> Staging
    Workflows --> Discord

    Frontend --> FeedbackUI
    FeedbackUI --> FeedbackBQ
    FeedbackBQ --> PendingReview
    PendingReview --> GoldenDataset

    Backend --> CloudMonitoring
    Frontend --> CloudMonitoring

    style FeedbackUI fill:#e91e63,color:#fff
    style FeedbackBQ fill:#34a853,color:#fff
    style GoldenDataset fill:#9c27b0,color:#fff
    style FirebaseAuth fill:#ff9800,color:#fff
    style ETL fill:#4285f4,color:#fff
    style Backend fill:#4285f4,color:#fff
    style Frontend fill:#4285f4,color:#fff
    style AgenticAI fill:#9c27b0,color:#fff
    style RawData fill:#34a853,color:#fff
    style Marts fill:#34a853,color:#fff
    style Workflows fill:#fbbc04,color:#000
    style CloudMonitoring fill:#ea4335,color:#fff
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Data Sources** | MLB API, Statcast | Raw baseball statistics |
| **ETL** | Python Flask, Cloud Run | Data extraction and loading |
| **Data Warehouse** | BigQuery | Centralized data storage |
| **Transformation** | dbt, Cloud Build | Data modeling and quality |
| **Authentication** | Firebase Auth (Google Sign-In), Firebase Admin SDK | User authentication and server-side token verification |
| **Backend** | FastAPI, Cloud Run | REST API for analytics |
| **Frontend** | React + Vite, Cloud Run | User interface |
| **MCP Server** | Model Context Protocol | Claude Desktop/Cursor integration |
| **AI Agent** | LangGraph, Gemini 2.5 Flash | Multi-step reasoning & Tool use |
| **MLOps** | Prompt Registry, Golden Dataset, BigQuery Logging | Prompt versioning, LLM evaluation gate, I/O observability |
| **HITL Feedback** | Feedback UI, BigQuery, pending_review.json | User feedback collection, golden dataset expansion pipeline |
| **Orchestration** | Cloud Workflows, Cloud Scheduler | Pipeline automation |
| **Monitoring** | Cloud Monitoring, Discord Webhooks | Custom metrics, alerts, dashboards, pipeline notifications |

---

## Service Catalog

### 1. ETL Pipeline

| Property | Value |
|----------|-------|
| **Name** | mlb-analytics-etl-service-v2 |
| **Repository** | `mlb-analytics-etl` (private) |
| **Deployment** | Cloud Run (asia-northeast1) |
| **URL** | https://mlb-analytics-etl-service-v2-907924272679.asia-northeast1.run.app |
| **Trigger Endpoint** | `/trigger` (POST) |
| **Language** | Python 3.11 |
| **Framework** | Flask |
| **Responsibility** | Extract MLB data from source APIs and load to BigQuery raw tables |
| **Schedule** | Weekly (via Cloud Workflows) |
| **Dependencies** | MLB API, BigQuery `mlb_raw_data` |

### 2. dbt Transformation

| Property | Value |
|----------|-------|
| **Name** | mlb-analytics-data-dbt |
| **Repository** | https://github.com/takeshimx/mlb-analytics-data-dbt |
| **Deployment** | Cloud Build Trigger |
| **Trigger ID** | `18e20064-5449-4096-a733-95ecae5bea5c` |
| **Language** | SQL (dbt) |
| **Responsibility** | Transform raw data into analytics-ready tables with data quality tests |
| **Layers** | Staging → Intermediate → Core → Marts |
| **Materialization** | Views (staging/intermediate), Incremental (core), Tables (marts) |
| **Tests** | 18 data quality tests |
| **Dependencies** | BigQuery `mlb_raw_data`, `dbt_utils` package |

**Key Models:**
- **Staging**: `stg_statcast_events`, `stg_batting_stats`, `stg_pitching_stats`
- **Intermediate**: `int_statcast_risp_events`, `int_statcast_bases_loaded_events`
- **Core**: `fact_batting_stats_master` (incremental), `statcast_2025_partitioned`
- **Marts**: `tbl_batter_clutch_risp`, `tbl_batter_monthly_performance`

### 3. Authentication (Firebase)

| Property | Value |
|----------|-------|
| **Provider** | Firebase Authentication (Google Sign-In) |
| **Frontend SDK** | Firebase JS SDK (`signInWithPopup` + `GoogleAuthProvider`) |
| **Backend SDK** | Firebase Admin SDK (`firebase-admin`) |
| **Middleware** | `FirebaseAuthMiddleware` (Pure ASGI) |
| **Token Format** | `Authorization: Bearer <Firebase ID Token>` |
| **Public Paths** | `/`, `/health`, `/debug/routes`, `/docs`, `/openapi.json`, `/redoc` |
| **User Tracking** | `user_id` extracted from token, logged to BigQuery via `llm_logger_service.py` |
| **CSP** | `nginx.conf` allows `apis.google.com`, `gstatic.com`, `accounts.google.com`, `*.firebaseapp.com` |

**Authentication Flow:**
1. User clicks "Sign in with Google" on frontend
2. Firebase SDK opens Google OAuth popup and returns ID token
3. Frontend attaches `Authorization: Bearer <token>` to all API requests
4. Backend `FirebaseAuthMiddleware` intercepts requests and verifies token via Firebase Admin SDK
5. Verified `user_id` and `email` are stored in `request.state` for downstream use
6. Unauthenticated requests to protected endpoints receive `401 Unauthorized`

### 4. Backend API

| Property | Value |
|----------|-------|
| **Name** | mlb-diamond-lens-api |
| **Repository** | `mlb-diamond-lens-api` (private) |
| **Deployment** | Cloud Run (asia-northeast1) |
| **URL** | https://mlb-diamond-lens-api-907924272679.asia-northeast1.run.app |
| **Language** | Python 3.11 |
| **Framework** | FastAPI |
| **Responsibility** | Serve analytics data via REST API endpoints |
| **Endpoints** | `/api/refresh` (POST) - Refresh data cache |
| **Dependencies** | BigQuery `mlb_analytics_dash_25` |

### 5. Frontend Dashboard

| Property | Value |
|----------|-------|
| **Name** | mlb-diamond-lens-frontend |
| **Repository** | `mlb-diamond-lens-frontend` (private) |
| **Deployment** | Cloud Run (asia-northeast1) |
| **URL** | https://mlb-diamond-lens-frontend-907924272679.asia-northeast1.run.app |
| **Language** | JavaScript (React) |
| **Framework** | React + Vite |
| **Responsibility** | User-facing dashboard for MLB analytics |
| **Endpoints** | `/api/cache/clear` (POST) - Clear frontend cache |
| **Dependencies** | Backend API |

### 6. Agentic AI System (Supervisor + LangGraph)

| Property | Value |
|----------|-------|
| **Architecture** | Supervisor + Specialized Agents |
| **Core Engine** | LangGraph (StateGraph) |
| **LLM Model** | Gemini 2.0/2.5 Flash |
| **Supervisor** | `SupervisorAgent` - Parses intent and routes to Stats or Matchup |
| **Specialized Agents** | `StatsAgent` (Season/Trend), `MatchupAgent` (Head-to-Head) |
| **State Management** | `AgentState` (TypedDict with message history, UI meta, and specialized analytics data) |
| **Nodes per Agent** | Oracle (Planning), Action Tool, Synthesizer (Reporting) |
| **Capabilities** | Intelligently handles complex vs specific queries, automated visualization, and professional analyst reports |
| **Frontend Sync** | Structured `matchupData` or `chartData` triggers specialized UI components |
| **Streaming Mode** | Server-Sent Events (SSE) with real-time token and state updates via `/api/v1/qa/agentic-stats-stream` |

### 6.1. Real-Time Streaming Architecture (SSE)

| Property | Value |
|----------|-------|
| **Protocol** | Server-Sent Events (SSE) |
| **Content-Type** | `text/event-stream` |
| **Backend Engine** | FastAPI StreamingResponse + AsyncGenerator |
| **LangGraph Integration** | `astream_events(version="v2")` for event streaming |
| **Event Types** | `session_start`, `routing`, `state_update`, `tool_start`, `tool_end`, `token`, `final_answer`, `stream_end`, `error` |
| **Frontend** | ReadableStream API with SSE parsing |
| **UI Updates** | Real-time streaming status display: `準備中` → `質問を分析中 🤔` → `データ取得中 🔍` → `回答生成中 ✍️` |
| **Token Accumulation** | LLM tokens streamed incrementally and accumulated in frontend |

**Streaming Data Flow:**

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant Frontend as React Frontend
    participant Backend as FastAPI Backend
    participant LangGraph as LangGraph Agent
    participant LLM as Gemini 2.5 Flash

    User->>Frontend: クエリ入力 & Enter
    Frontend->>Frontend: handleSendMessageStream()
    Frontend->>Frontend: isStreaming: true<br/>streamingStatus: '準備中...'

    Frontend->>Backend: POST /agentic-stats-stream
    activate Backend
    Backend->>Backend: SupervisorAgent.route_query()
    Backend-->>Frontend: event: routing<br/>data: {agent_type: "batter"}
    Frontend->>Frontend: streamingStatus: 'batterエージェントで処理中'

    Backend->>LangGraph: agent.app.astream_events()
    activate LangGraph
    LangGraph->>LangGraph: oracle node start
    LangGraph-->>Backend: on_chain_start (oracle)
    Backend-->>Frontend: event: state_update<br/>data: {node: "oracle"}
    Frontend->>Frontend: streamingStatus: '質問を分析中 🤔'

    LangGraph->>LangGraph: executor node start
    LangGraph-->>Backend: on_chain_start (executor)
    Backend-->>Frontend: event: state_update<br/>data: {node: "executor"}
    Frontend->>Frontend: streamingStatus: 'データ取得中 🔍'

    LangGraph->>LLM: BigQuery tool call
    LangGraph->>LangGraph: synthesizer node start
    LangGraph-->>Backend: on_chain_start (synthesizer)
    Backend-->>Frontend: event: state_update<br/>data: {node: "synthesizer"}
    Frontend->>Frontend: streamingStatus: '回答生成中 ✍️'

    LLM-->>LangGraph: token stream
    loop トークンストリーミング
        LangGraph-->>Backend: on_chat_model_stream
        Backend->>Backend: accumulated_answer += token
        Backend-->>Frontend: event: token<br/>data: {content: "大"}
        Frontend->>Frontend: content += "大"
        LangGraph-->>Backend: on_chat_model_stream
        Backend-->>Frontend: event: token<br/>data: {content: "谷"}
        Frontend->>Frontend: content += "谷"
    end

    deactivate LangGraph
    Backend->>Backend: ストリーミング完了
    Backend-->>Frontend: event: final_answer<br/>data: {answer: "...", isTable: false}
    Frontend->>Frontend: isStreaming: false<br/>streamingStatus: undefined

    Backend-->>Frontend: event: stream_end
    deactivate Backend
    Frontend->>User: 完全な応答を表示
```

**Key Implementation Details:**

| Component | Implementation | Purpose |
|-----------|---------------|---------|
| **Backend Endpoint** | `ai_analytics_endpoints.py` Line 372-432 | SSE streaming endpoint `/qa/agentic-stats-stream` |
| **Streaming Service** | `ai_agent_service.py` Line 558-780 | `run_mlb_agent_stream()` with LangGraph `astream_events()` |
| **SSE Formatter** | `utils/streaming.py` | `format_sse()` converts dict to SSE format |
| **Frontend Handler** | `App.jsx` Line 1167-1371 | `handleSendMessageStream()` with ReadableStream parsing |
| **Event Routing** | `handleSendMessageStream()` switch cases | Maps event types to UI state updates |
| **Token Accumulation** | Backend: `accumulated_answer` variable | Collects tokens during streaming, sends as `final_answer` |

### 7. MLOps: Prompt Versioning, LLM I/O Logging & Evaluation Gate

| Property | Value |
|----------|-------|
| **Prompt Versioning** | Externalized prompts as versioned text files (`parse_query_v1.txt`, `routing_v1.txt`) |
| **Prompt Registry** | `prompt_registry.py` manages prompt loading and version switching |
| **LLM I/O Logging** | `llm_logger_service.py` logs all LLM interactions to BigQuery asynchronously |
| **Logged Fields** | User query, parsed result, prompt version, latency, errors, routing result, user feedback |
| **Evaluation Gate** | `evaluate_llm_accuracy.py` runs LLM against golden dataset in CI/CD |
| **Golden Dataset** | `golden_dataset.json` with test cases covering batting, pitching, splits, career (expandable via HITL) |
| **Pass Threshold** | 80% accuracy required to proceed with deployment |
| **Critical Fields** | `query_type` mismatch causes immediate failure regardless of overall accuracy |

### 8. Human-in-the-Loop (HITL) Feedback System

| Property | Value |
|----------|-------|
| **Feedback UI** | Thumbs up/down on every bot response, detailed form for negative ratings |
| **Feedback Categories** | `inaccurate`, `slow`, `irrelevant`, `wrong_player`, `wrong_stats` |
| **Storage** | Feedback logged to BigQuery `llm_interaction_logs` table with `user_rating`, `feedback_category`, `feedback_reason` |
| **API Endpoint** | `POST /api/v1/qa/feedback` |
| **Extract Script** | `extract_golden_dataset.py` fetches bad-rated queries → `pending_review.json` |
| **Approve Script** | `approve_to_golden.py` promotes reviewed cases → `golden_dataset.json` |
| **Review Process** | Manual: developer edits `pending_review.json`, fills correct `expected` values, sets `reviewed: true` |

**HITL Feedback Loop**:

```mermaid
graph TD
    A[User rates response 👎] --> B[BigQuery: feedback logged]
    B --> C[extract_golden_dataset.py]
    C --> D[pending_review.json<br/>TODOs as placeholders]
    D --> E[Developer reviews<br/>fills correct expected values]
    E --> F[approve_to_golden.py]
    F --> G[golden_dataset.json<br/>test cases expanded]
    G --> H[CI/CD Evaluation Gate<br/>LLM accuracy checked]
    H -->|Accuracy ≥ 80%| I[Deploy]
    H -->|Accuracy < 80%| J[Block: Fix prompts]
    J --> H
```

### 8. Orchestration

| Property | Value |
|----------|-------|
| **Name** | mlb-pipeline |
| **Repository** | https://github.com/takeshimx/mlb-pipeline-orchestration |
| **Deployment** | Cloud Workflows (asia-northeast1) |
| **Schedule** | Cloud Scheduler: `mlb-pipeline-weekly` |
| **Cron** | `0 6 * * 0` (Sunday 6:00 AM JST) |
| **Responsibility** | Orchestrate ETL → dbt → Backend → Frontend pipeline |
| **Notifications** | Discord webhook on success/failure |

**Pipeline Steps:**
1. Trigger ETL Cloud Run (`/trigger`)
2. Wait for ETL completion
3. Trigger dbt Cloud Build
4. Poll dbt build status (30s intervals)
5. Refresh Backend API (`/api/refresh`)
6. Clear Frontend cache (`/api/cache/clear`)
7. Send Discord notification

---

## Data Flow

### Weekly Pipeline Execution

```mermaid
sequenceDiagram
    participant Scheduler as Cloud Scheduler
    participant Workflows as Cloud Workflows
    participant ETL as ETL Service
    participant BQ as BigQuery
    participant dbt as dbt (Cloud Build)
    participant Backend as Backend API
    participant Frontend as Frontend
    participant Discord as Discord

    Note over Scheduler: Sunday 6:00 AM JST
    Scheduler->>Workflows: Trigger mlb-pipeline

    activate Workflows
    Workflows->>ETL: POST /trigger
    activate ETL
    ETL->>BQ: INSERT INTO mlb_raw_data.*
    ETL-->>Workflows: 200 OK
    deactivate ETL

    Workflows->>dbt: Trigger Cloud Build
    activate dbt
    dbt->>BQ: CREATE OR REPLACE VIEW stg_*
    dbt->>BQ: INSERT INTO fact_* (incremental)
    dbt->>BQ: CREATE OR REPLACE TABLE tbl_*
    dbt->>dbt: Run 18 data quality tests
    dbt-->>Workflows: Build SUCCESS
    deactivate dbt

    Workflows->>Backend: POST /api/refresh
    activate Backend
    Backend->>BQ: SELECT * FROM tbl_batter_clutch_*
    Backend-->>Workflows: Cache refreshed
    deactivate Backend

    Workflows->>Frontend: POST /api/cache/clear
    activate Frontend
    Frontend-->>Workflows: Cache cleared
    deactivate Frontend

    Workflows->>Discord: Success notification
    deactivate Workflows
```

### Data Transformation Layers

```mermaid
graph LR
    subgraph "Source"
        S1[statcast_2021_partitioned]
        S2[statcast_2022-2025]
        S3[dim_players]
        S4[fact_batting_stats_staging]
    end

    subgraph "Staging (VIEW)"
        ST1[stg_statcast_events]
        ST2[stg_batting_stats]
    end

    subgraph "Intermediate (VIEW)"
        INT1[int_statcast_risp_events]
        INT2[int_statcast_bases_loaded]
    end

    subgraph "Core (INCREMENTAL TABLE)"
        C1[fact_batting_stats_master]
        C2[statcast_2025_partitioned]
    end

    subgraph "Marts (TABLE)"
        M1[tbl_batter_clutch_risp]
        M2[tbl_batter_clutch_bases_loaded]
        M3[tbl_batter_monthly_*]
    end

    S1 --> ST1
    S2 --> ST1
    S3 --> ST1
    S4 --> ST2

    ST1 --> INT1
    ST1 --> INT2
    ST1 --> C2
    ST2 --> C1

    INT1 --> M1
    INT2 --> M2
    C1 --> M3

    M1 --> API[Backend API]
    M2 --> API
    M3 --> API
```

---

## GCP Resources

### BigQuery

**Project**: `tksm-dash-test-25`

**Datasets:**

| Dataset | Purpose | Materialization | Size |
|---------|---------|----------------|------|
| `mlb_raw_data` | Raw source data from ETL | Tables | ~50GB |
| `mlb_analytics_dash_25` | Production analytics (marts) | Tables + Views | ~10GB |
| `mlb_analytics_dev` | Development environment | Views | Minimal |
| `mlb_analytics_staging` | Pre-production testing | Views | Minimal |

**Key Tables:**

| Table | Type | Partitioning | Clustering | Rows | Description |
|-------|------|--------------|-----------|------|-------------|
| `mlb_raw_data.statcast_2021_partitioned` | TABLE | `game_date` (DATE) | `player_name`, `pitcher`, `batter` | ~2M | Statcast pitch-level data 2021 |
| `mlb_raw_data.dim_players` | TABLE | None | None | ~5K | Player dimension table |
| `mlb_analytics_dash_25.fact_batting_stats_master` | INCREMENTAL | `season` (INT64 RANGE) | None | ~50K | Weekly batting statistics |
| `mlb_analytics_dash_25.tbl_batter_clutch_risp` | TABLE | None | None | ~1K | Clutch hitting with RISP |

### Cloud Run Services

| Service Name | Region | Min Instances | Max Instances | Memory | CPU |
|--------------|--------|--------------|---------------|--------|-----|
| `mlb-analytics-etl-service-v2` | asia-northeast1 | 0 | 1 | 2GB | 1 |
| `mlb-diamond-lens-api` | asia-northeast1 | 0 | 10 | 1GB | 1 |
| `mlb-diamond-lens-frontend` | asia-northeast1 | 0 | 10 | 512MB | 1 |

### Cloud Build

**Trigger:**
- **Name**: `dbt-pipeline`
- **ID**: `18e20064-5449-4096-a733-95ecae5bea5c`
- **Repository**: mlb-analytics-data-dbt
- **Branch**: `main`
- **Config**: `cloudbuild.yaml`

### Cloud Workflows

**Workflow:**
- **Name**: `mlb-pipeline`
- **Region**: `asia-northeast1`
- **Service Account**: `cloud-build-dbt@tksm-dash-test-25.iam.gserviceaccount.com`

### Cloud Scheduler

**Job:**
- **Name**: `mlb-pipeline-weekly`
- **Schedule**: `0 6 * * 0` (Sunday 6:00 AM JST)
- **Target**: Cloud Workflows `mlb-pipeline`
- **Timezone**: `Asia/Tokyo`

### Service Accounts

| Email | Roles | Used By |
|-------|-------|---------|
| `cloud-build-dbt@tksm-dash-test-25.iam.gserviceaccount.com` | Workflows Invoker<br/>Cloud Run Invoker<br/>Cloud Build Editor<br/>BigQuery Data Editor | Cloud Workflows, Cloud Scheduler |

---

## Architecture Decisions

See [Architecture Decision Records](./adr/) for detailed design decisions.

**Key Decisions:**
- [ADR-001: Use BigQuery as Data Warehouse](./adr/001-use-bigquery.md)
- [ADR-002: Separate ETL, dbt, and Orchestration Repositories](./adr/002-separate-repos.md)
- [ADR-003: Weekly Batch Processing Strategy](./adr/003-weekly-batch-processing.md)
- [ADR-004: Cloud Workflows over Airflow](./adr/004-cloud-workflows-over-airflow.md)

---

## Quick Commands

### Pipeline Operations

```bash
# Manually trigger weekly pipeline
gcloud scheduler jobs run mlb-pipeline-weekly --location=asia-northeast1

# Run workflow directly (bypass scheduler)
gcloud workflows run mlb-pipeline --location=asia-northeast1

# View workflow execution history
gcloud workflows executions list mlb-pipeline --location=asia-northeast1 --limit=10

# Get specific execution details
gcloud workflows executions describe EXECUTION_ID \
  --workflow=mlb-pipeline \
  --location=asia-northeast1
```

### dbt Commands

```bash
# Run dbt locally (dev environment)
cd mlb-analytics-data-dbt
dbt run --target dev

# Run specific model
dbt run --select stg_statcast_events

# Run tests only
dbt test

# Generate documentation
dbt docs generate && dbt docs serve

# Full refresh (rebuild all incremental models)
dbt run --full-refresh
```

### BigQuery Queries

```sql
-- Check latest data in staging
SELECT MAX(game_date) as latest_game
FROM `tksm-dash-test-25.mlb_raw_data.statcast_2025`;

-- View marts data
SELECT * FROM `tksm-dash-test-25.mlb_analytics_dash_25.tbl_batter_clutch_risp`
WHERE game_year = 2025
ORDER BY barrels_count DESC
LIMIT 10;

-- Check incremental model status
SELECT season, COUNT(*) as rows
FROM `tksm-dash-test-25.mlb_analytics_dash_25.fact_batting_stats_master`
GROUP BY season
ORDER BY season DESC;
```

### Cloud Run Commands

```bash
# View ETL logs
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=mlb-analytics-etl-service-v2" \
  --limit=50 \
  --format=json

# Trigger ETL manually
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://mlb-analytics-etl-service-v2-907924272679.asia-northeast1.run.app/trigger

# Check Backend API health
curl https://mlb-diamond-lens-api-907924272679.asia-northeast1.run.app/health
```

---

## Monitoring & Observability

### Infrastructure Monitoring (Diamond Lens Application)

The Diamond Lens application has comprehensive monitoring and alerting implemented via Terraform:

**Uptime Checks**:
- Backend API health monitoring (`/health` endpoint)
- Frontend health monitoring
- Multi-region checks (USA, EUROPE, ASIA_PACIFIC)
- Frequency: 60 seconds
- Timeout: 10 seconds

**Alert Policies**:
- **Backend API Down**: Triggers when health check fails for 60+ seconds
- **Frontend Down**: Triggers when frontend is unreachable
- **High Memory Usage**: Alerts when memory > 80% for 5 minutes
- **High CPU Usage**: Alerts when CPU > 80% for 5 minutes
- **High Latency**: Alerts when API p95 latency > 5 seconds

**Custom Metrics** (Application Layer):
- `custom.googleapis.com/diamond-lens/api/latency` - API response time by endpoint
- `custom.googleapis.com/diamond-lens/api/errors` - Error count by type (validation, bigquery, llm, null_response)
- `custom.googleapis.com/diamond-lens/query/processing_time` - Query processing time by query type
- `custom.googleapis.com/diamond-lens/bigquery/latency` - BigQuery query latency

**Monitoring Dashboard**:
- Uptime metrics (backend/frontend availability)
- API latency (p50, p95, p99)
- CPU and memory utilization
- Instance count tracking
- Error rate monitoring

**Notification Channels**:
- Email alerts configured via Terraform
- All alerts include runbook links and severity classification

**Structured Logging**:
- JSON format logs with searchable fields
- Severity levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Queryable fields: `query_type`, `error_type`, `latency_ms`, `status_code`

**Implementation**:
- Location: `diamond-lens/terraform/modules/monitoring/`
- Files: `uptime_checks.tf`, `alert_policies.tf`, `dashboard.tf`
- Documentation: `diamond-lens/docs/MONITORING.md`

### GCP Console Links

| Resource | Link |
|----------|------|
| **Cloud Workflows** | [View Executions](https://console.cloud.google.com/workflows/workflow/asia-northeast1/mlb-pipeline/executions?project=tksm-dash-test-25) |
| **Cloud Scheduler** | [View Jobs](https://console.cloud.google.com/cloudscheduler?project=tksm-dash-test-25) |
| **Cloud Build** | [View Builds](https://console.cloud.google.com/cloud-build/builds?project=tksm-dash-test-25) |
| **BigQuery** | [View Datasets](https://console.cloud.google.com/bigquery?project=tksm-dash-test-25) |
| **Cloud Run** | [View Services](https://console.cloud.google.com/run?project=tksm-dash-test-25) |
| **Cloud Logging** | [View Logs](https://console.cloud.google.com/logs?project=tksm-dash-test-25) |
| **Cloud Monitoring** | [View Dashboards](https://console.cloud.google.com/monitoring/dashboards?project=tksm-dash-test-25) |

### Pipeline Notifications

Pipeline status notifications are sent to Discord webhook:
- ✅ Success: Pipeline completed successfully
- ❌ Failure: ETL, dbt, or Backend step failed
- ⚠️ Warning: Non-critical errors (e.g., Frontend cache clear failed)

---

## Cost Breakdown

| Service | Monthly Cost (Estimated) | Notes |
|---------|-------------------------|-------|
| BigQuery Storage | $10-20 | ~60GB total storage |
| BigQuery Queries | $5-10 | Weekly pipeline queries |
| Cloud Run | $5-10 | Pay-per-use, minimal traffic |
| Cloud Build | $2-5 | Weekly dbt builds |
| Cloud Workflows | $0.15 | Weekly executions |
| Cloud Scheduler | $0.10 | Single job |
| **Total** | **$22-45/month** | Production costs |

---

## Troubleshooting

See [Runbooks](./runbooks/) for detailed troubleshooting guides:
- [Pipeline Failure Response](./runbooks/pipeline-failure.md)
- [dbt Build Errors](./runbooks/dbt-errors.md)
- [BigQuery Permission Issues](./runbooks/bigquery-permissions.md)

---

## Contributing

This documentation is maintained alongside the codebase. When making changes:
1. Update relevant service documentation in `/services/`
2. Update architecture diagrams if system design changes
3. Add new ADRs for significant decisions
4. Keep GCP resource inventory up-to-date

---

## Contact

**Owner**: takeshimx
**GitHub**: https://github.com/takeshimx
**Discord**: mlb-pipeline alerts channel
