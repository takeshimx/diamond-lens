# Diamond Lens - MLB Stats Assistant 🔮⚾

An AI-powered analytics interface for exploring Major League Baseball statistics through natural language queries and advanced custom analytics. Built with React, FastAPI, and Google Cloud BigQuery.

## 🌟 Features

### 1. Natural Language Q&A Interface (Full Stack)
**Status**: ✅ Production-ready with frontend UI

- **💬 Chat Mode**: Natural language queries in Japanese with AI-powered responses
- **⚡ Quick Questions**: Pre-defined common baseball queries for instant results
- **⚙️ Custom Query Builder**: Advanced analytics with custom situational filters
- **🤖 Autonomous Agent Mode (NEW)**: High-performance reasoning agent using LangGraph for multi-step data exploration and professional analysis

**Analytics Capabilities**:
- **Batting Statistics**: Season stats, splits, and advanced Statcast metrics
- **Pitching Statistics**: ERA, WHIP, strikeout rates, and advanced analytics
- **Situational Splits**: RISP performance, bases loaded, custom game situations
- **Career Analytics**: Multi-season trend analysis and career aggregation
- **Visual Charts**: YoY trend charts and KPI summary cards
- **Advanced Filters**: Inning-specific, count-specific, pitcher matchup analysis

### 2. Statistical Analysis & Predictive Modeling (Full Stack)
**Status**: ✅ Production-ready with frontend UI

**Capabilities**:
- **📊 Interactive Dashboard**: Real-time win rate predictions with visual analytics
- **Multivariate Regression Model**: Predict team win rates with 94.2% accuracy (R² = 0.942)
- **Hypothesis Testing**: T-tests, effect size analysis (Cohen's d), confidence intervals
- **Multicollinearity Analysis**: VIF-based variable selection for optimal model performance
- **Model Evaluation**: Comprehensive metrics (R², RMSE, MAE) and regression coefficients

**Frontend Features**:
- **Input Controls**: Interactive sliders for OPS (0.500-1.000), ERA (2.00-6.00), HRs Allowed (100-250)
- **Prediction Results**: Win rate percentage, expected wins per 162 games, performance tier classification
- **Sensitivity Analysis**: Line chart showing OPS impact on win rate with fixed ERA and HRs Allowed
- **Model Transparency**: Display R², MSE, MAE metrics for model evaluation

**API Endpoints**:
- `GET /api/v1/statistics/predict-winrate` - Predict win rate from OPS, ERA, and home runs allowed
- `GET /api/v1/statistics/model-summary` - Get model evaluation metrics and regression equation
- `GET /api/v1/statistics/ops-sensitivity` - Analyze OPS impact on win rate

**Technologies**: React, Recharts, FastAPI, BigQuery ML, scikit-learn, scipy

**Analysis Notebooks**:
- `analysis/hypothesis_testing.ipynb` - Statistical hypothesis testing with visualizations
- `analysis/regression_analysis.ipynb` - Multivariate regression with VIF analysis

### 3. Player Segmentation Analysis (Full Stack)
**Status**: ✅ Production-ready with frontend UI

**Capabilities**:
- **🎯 K-means Clustering**: Automated player type classification using unsupervised learning
- **🧠 FT-Transformer + K-means (Experimental)**: Self-supervised FT-Transformer encoder learns feature interactions via Self-Attention, then K-means clusters the learned embeddings for more nuanced player grouping
- **Multi-dimensional Analysis**: Segment players based on 4-6 performance metrics
- **Interactive Visualization**: Scatter plots with cluster-based color coding
- **Cluster Profiling**: Statistical summaries for each player segment

**Frontend Features**:
- **Player Type Toggle**: Switch between Batter and Pitcher analysis
- **Scatter Plot Visualization**:
  - Batters: OPS vs ISO with 4 clusters (Superstar Sluggers, Elite Contact Hitters, Solid Regulars, Struggling)
  - Pitchers: ERA vs K/9 with 4 clusters (Strikeout Dominant, Elite Balanced, Mid-Tier, Struggling)
- **Interactive Tooltips**: Player name, team, and key statistics on hover
- **Cluster Summary Table**: Average metrics and player count per segment

**Clustering Features**:
- **Batter Segmentation**: OPS, ISO, K%, BB% (n=4 clusters)
- **Pitcher Segmentation**: ERA, K/9, BB/9, HR/9, WHIP, GB% (n=4 clusters)
- **Standardization**: Feature scaling for optimal clustering performance
- **VIF Analysis**: Multicollinearity detection to ensure meaningful clusters

**API Endpoints**:
- `GET /api/v1/segmentation/batters` - Get batter segmentation with K-means clustering
- `GET /api/v1/segmentation/pitchers` - Get pitcher segmentation with K-means clustering

**Technologies**: React, Recharts, scikit-learn, PyTorch, pandas, FastAPI

**Analysis Notebooks**:
- `analysis/player_segmentation.ipynb` - K-means clustering analysis with visualizations

**Business Applications**:
- **Scouting Efficiency**: Categorize prospects by performance profile

### 4. Autonomous Analyst Agent (Supervisor + LangGraph)
**Status**: ✅ Production-ready with specialized agents powered by LangGraph

**Capabilities**:
- **🧠 Multi-Agent Orchestration**: Uses a `SupervisorAgent` to intelligently route queries to specialized agents (`StatsAgent`, `MatchupAgent`), each orchestrated by **LangGraph**.
- **🔍 Reasoning Visualization**: Live display of the autonomous reasoning steps across different specialized graph nodes.
- **📊 Adaptive UI**: Automatically switches between narrative reports, interactive charts, and data tables based on found data.
- **⚔️ Specialized Agents**:
  - **StatsAgent**: Expert in team/player season stats, trends, and group comparisons.
  - **MatchupAgent**: Expert in batter vs. pitcher head-to-head analytics and historic outcomes.
  - **StrategyAgent** *(NEW — Phase 1 MVP)*: Cross-domain strategy analysis using Plan-and-Execute + Parallel Fan-Out pattern. Simultaneously invokes all 4 tools (batter stats, pitcher stats, matchup history, matchup analytics) via `asyncio.gather()` and synthesizes a structured 6-section strategy report. Renders a dedicated `StrategyReportCard` UI component.
- **🏆 Professional Reports**: Generates structured analyst reports with headers, bullet points, and deep insights.
- **⚖️ Fail-safe Generation**: Code-level guards to ensure complete, natural Japanese sentences without fragments.
- **🔄 Reflection Loop (Self-Correction)**: Autonomous error recovery mechanism that detects SQL errors or empty query results and self-corrects by analyzing the root cause and retrying with improved parameters (max 2 retries). Intelligently classifies errors as retryable (syntax errors, empty results) vs non-retryable (permission, timeout, schema errors) to avoid wasteful retries.

### 5. MLOps: Prompt Versioning, LLM I/O Logging & Evaluation Gate
**Status**: ✅ Production-ready

**Capabilities**:
- **📝 Prompt Versioning**: Externalized LLM prompts as versioned text files (`parse_query_v1.txt`, `routing_v1.txt`) managed via `prompt_registry.py`, enabling version-controlled prompt iteration without code changes
- **📊 LLM I/O Logging**: Async logging of all LLM interactions (queries, parsed results, latency, errors) to BigQuery via `llm_logger_service.py` for observability and drift detection
- **🚦 LLM Evaluation Gate**: CI/CD quality gate that runs LLM against a golden dataset (`golden_dataset.json`) and blocks deployment if accuracy drops below 80%

### 6. Human-in-the-Loop (HITL) Feedback System
**Status**: ✅ Production-ready

**Capabilities**:
- **👍👎 User Feedback UI**: Thumbs up/down buttons on every AI response with detailed feedback form for negative ratings
- **📋 Feedback Categories**: Structured categorization (`inaccurate`, `slow`, `irrelevant`, `wrong_player`, `wrong_stats`) with optional free-text reason
- **🗄️ BigQuery Logging**: All feedback (rating, category, reason) is recorded to BigQuery alongside the original LLM interaction log
- **🔄 Golden Dataset Pipeline**: Three-step workflow to continuously improve LLM accuracy from user feedback

**HITL Feedback Loop**:
```
User rates response 👎 + selects category + writes reason
         │
         ▼
  BigQuery logs (feedback recorded)
         │
  ┌──────┴───────┐
  │   Extract     │  python backend/scripts/extract_golden_dataset.py
  │   bad queries │  → pending_review.json (with TODO placeholders)
  └──────┬───────┘
         ▼
  ┌──────┴───────┐
  │  Human Review │  Developer fills in correct expected values
  │  (manual)     │  → reviewed: true
  └──────┬───────┘
         ▼
  ┌──────┴───────┐
  │   Approve     │  python backend/scripts/approve_to_golden.py
  │   to golden   │  → golden_dataset.json (test cases grow)
  └──────┴───────┘
         ▼
  CI/CD Evaluation Gate runs with expanded golden dataset
```

**API Endpoint**:
- `POST /api/v1/qa/feedback` - Submit user feedback (rating, category, reason)

### 7. Rate Limiting & Quota Management
**Status**: ✅ Production-ready

**Capabilities**:
- **🌐 Global Rate Limit**: 100 requests/minute across all users via custom ASGI middleware
- **👤 Per-Session Rate Limit**: 20 requests/minute per user (Firebase user_id > Session ID > IP address)
- **🎯 Per-Endpoint Rate Limit**: Configurable limits per endpoint via slowapi decorators (e.g., AI chat: 5/min, player stats: 10/min, statistics: 10/min)
- **💰 LLM Token Budget**: Daily token usage cap (default: 1,000,000 tokens/day) with automatic reset at UTC midnight
- **📊 Monitoring Integration**: All rate limit rejections are logged to Cloud Monitoring custom metrics and BigQuery `llm_interaction_logs`
- **⚙️ Configurable via `.env`**: All limits are adjustable without code changes

**Architecture**:
- **In-memory storage**: No Redis dependency — uses Python `dict` + `threading.Lock` for thread-safe counters. Suitable for Cloud Run single-container deployment.
- **Fixed-window algorithm**: 1-minute sliding windows for rate counting
- **Middleware stack**: `RequestID → RateLimitMiddleware (Global/Session) → FirebaseAuth → Per-Endpoint (slowapi)`
- **Graceful 429 responses**: Returns `Retry-After` header with seconds until next window

**Configuration** (`.env`):
```env
RATE_LIMIT_GLOBAL_PER_MINUTE=100
RATE_LIMIT_SESSION_PER_MINUTE=20
RATE_LIMIT_PLAYER_STATS_PER_MINUTE=10
RATE_LIMIT_AGENT_CHAT_PER_MINUTE=5
RATE_LIMIT_STATISTICS_PER_MINUTE=10
LLM_DAILY_TOKEN_BUDGET=1000000
RATE_LIMIT_ENABLED=true
```

### 8. ML Model Monitoring & Data Drift Detection
**Status**: ✅ Production-ready

**Capabilities**:
- **📊 Data Drift Detection**: Statistical monitoring of ML model input data distribution changes between seasons using KS test, PSI (Population Stability Index), and mean shift analysis
- **🗄️ Model Registry & Versioning**: Persist trained ML models (KMeans, FT-Transformer + StandardScaler) to GCS with version tracking. Metadata logged to BigQuery for model lineage
- **🔄 Auto-Baseline**: Drift detection automatically references the active model's training season — no manual baseline specification needed
- **🚦 CI/CD Drift Gate**: Pre-deployment check blocks releases when critical data drift is detected, prompting model retraining

**Architecture**:
```
Model Training → GCS (model.joblib) + BigQuery (ml_model_registry)
       ↓
Promote to Active → player_segmentation loads from GCS
       ↓
CI/CD Drift Check → Compare active model's training data vs latest season
       ↓
   ├── none/warning → Deploy proceeds
   └── critical     → Deploy blocked 🚫 (retrain required)
```

**Drift Detection Methods**:
- **KS Test**: Kolmogorov-Smirnov test for distribution shape changes
- **PSI**: Population Stability Index for overall distribution shift (Warning ≥ 0.1, Critical ≥ 0.2)
- **Mean Shift**: Percentage change in feature means between seasons

**Model Registry Features**:
- **GCS Storage**: Versioned model artifacts (`models/{model_type}/{version}/model.joblib`)
- **BigQuery Metadata**: Version tracking with `algorithm` column (supports KMeans, FT-Transformer, LightGBM, etc.) and `model_params` JSON for algorithm-specific parameters
- **Version Promotion**: Active version management with `promote_version()`
- **Fallback**: `player_segmentation.py` loads from registry if available, falls back to on-the-fly fitting

**API Endpoints**:
- `POST /api/v1/ml-monitoring/detect-drift` - Detect data drift (auto-baseline from registry)
- `GET /api/v1/ml-monitoring/drift-history` - Historical drift reports
- `GET /api/v1/ml-monitoring/drift-summary` - Latest drift status summary
- `POST /api/v1/model-registry/train` - Train and register a new model version
- `GET /api/v1/model-registry/versions` - List registered versions
- `POST /api/v1/model-registry/promote` - Promote a version to active
- `GET /api/v1/model-registry/active` - Get current active version

**Technologies**: scikit-learn, PyTorch, scipy, joblib, Google Cloud Storage, BigQuery

### 9. Stuff+ / Pitching+ / Pitching++ Pitch Quality Evaluation (Backend)
**Status**: ✅ Backend API ready (frontend pending)

**Capabilities**:
- **⚾ Stuff+ Model**: Evaluates pure pitch quality (velocity, spin rate, movement, release point, arm angle) independent of location, using XGBoost regression on `delta_pitcher_run_exp`
- **🎯 Pitching+ Model**: Evaluates total pitching effectiveness by adding pitch location (`plate_x`, `plate_z`) to the Stuff+ feature set
- **🚀 Pitching++ Model**: Advanced pitching evaluation combining Pitching+ with sequence context (tunneling, speed difference), precise command (`zone_distance`), and count (`balls`, `strikes`)
- **📊 Pre-computed Rankings**: Pitcher × pitch type rankings stored in BigQuery for fast retrieval with pagination and sorting
- **🔮 Real-time Inference**: On-demand per-pitcher prediction using active model from Model Registry
- **⚖️ Stuff+ vs Pitching+ Gap Analysis**: Compares both scores to classify pitchers as "stuff-dominant", "command-dominant", or "balanced"

**Model Architecture**:
- **Algorithm**: XGBoost Regressor (500 estimators, max_depth=6, early stopping)
- **Target Variable**: `delta_pitcher_run_exp` (pitch-level run expectancy change)
- **Stuff+ Features** (11): `release_speed`, `release_spin_rate`, `spin_axis`, `pfx_x`, `pfx_z`, `release_extension`, `release_pos_x`, `release_pos_z`, `api_break_z_with_gravity`, `api_break_x_arm`, `arm_angle`
- **Pitching+ Features** (13): Stuff+ features + `plate_x`, `plate_z`
- **Pitching++ Features**: Pitching+ features + command (`zone_distance`) + count (`balls`, `strikes`) + tunneling (`release_diff`, `speed_diff`, `prev_pfx_z`)
- **Scoring**: z-score normalization (100 = league average, 15 points = 1σ)
- **Aggregation**: Pitcher × pitch type level with minimum pitch count filter (default: 100)

**Training Pipeline** (`scripts/train_stuff_plus.py`):
1. Fetch pitch-level data from BigQuery `statcast_master`
2. Train XGBoost for Stuff+, Pitching+, and Pitching++ models
3. Compute pitcher × pitch type rankings with z-score normalization
4. Save model artifacts to GCS via Model Registry
5. Write pre-computed rankings to BigQuery `stuff_plus_rankings` table

**API Endpoints**:
- `GET /api/v1/stuff-plus/rankings` - Get Stuff+, Pitching+, or Pitching++ leaderboard (paginated, sortable)
- `GET /api/v1/stuff-plus/pitcher/{pitcher_id}` - Real-time per-pitcher pitch-level scores
- `GET /api/v1/stuff-plus/pitcher/{pitcher_id}/compare` - Stuff+ vs Pitching+ gap analysis

**Technologies**: XGBoost, scikit-learn, pandas, BigQuery, GCS, Model Registry

**Analysis Notebooks**:
- `analysis/stuff_plus.ipynb` - Stuff+ / Pitching+ / Pitching++ model development and validation

### 10. LLM as a Judge (Automated Quality Evaluation)
**Status**: ✅ Service layer + unit tests complete

**Overview**: A quality assurance framework where a separate LLM (Gemini Flash) automatically scores the output quality of each processing step across multiple dimensions. Designed to log production request I/O to BigQuery and run batch sample evaluations.

**5 Judge Services**:

| # | Judge | Evaluation Target | Evaluation Dimensions | File |
|---|---|---|---|---|
| 1 | **Parse Accuracy** | LLM query parse results | query_type accuracy, metrics extraction, player name resolution, intent understanding | `llm_judge_service.py` |
| 2 | **Synthesizer Quality** | AI-generated responses | Factual accuracy, analytical depth, language quality, structure, completeness | `synthesizer_judge_service.py` |
| 3 | **Reflection Decision** | Self-correction loop | Trigger appropriateness, root cause identification, correction quality, over-correction risk | `reflection_judge_service.py` |
| 4 | **Routing Accuracy** | Supervisor routing | Route accuracy, ambiguity handling, reasoning quality | `routing_judge_service.py` |
| 5 | **Drift Alert Quality** | Data drift detection results | Statistical validity, practical significance, actionability, domain relevance | `drift_alert_judge_service.py` |

**Operational Architecture**:
```
[Real-time] User query → Log step I/O to BigQuery (0 additional Gemini calls)
[Batch]     Sample from BQ → 5 Judges score → Results saved to BQ
```

**E2E Script**:
- `backend/scripts/evaluate_with_llm_judge.py` — Parse accuracy regression testing against golden dataset

**Tests**:
- `test_llm_judge.py`, `test_synthesizer_judge.py`, `test_reflection_judge.py`, `test_routing_judge.py`, `test_drift_alert_judge.py`

### 11. BQ Embedding-based Quality Warning System
**Status**: ✅ Production-ready

**Overview**: A serverless, pay-as-you-go quality warning system that detects when a user's query is similar to past queries that received negative feedback. Uses BigQuery ML `ML.GENERATE_EMBEDDING` + `VECTOR_SEARCH` with no always-on instances.

**Architecture**:
```
[Daily Batch: 02:00 UTC]
  llm_interaction_logs (user_rating='bad')
    → JOIN original query via request_id
    → ML.GENERATE_EMBEDDING (Vertex AI text-multilingual-embedding-002)
    → INSERT INTO llm_query_embeddings (append-only)

[At Request Time - Parallel with AI response]
  User query → BQ ML.GENERATE_EMBEDDING (1 Vertex AI API call)
             → VECTOR_SEARCH against llm_query_embeddings
             → quality_warning flag returned with response
             → Frontend: amber warning banner displayed
```

**Key Design Decisions**:
- **Serverless**: Vertex AI API called only on BQ query execution — zero always-on instances
- **Parallel execution**: `asyncio.gather` runs warning check alongside AI response generation, adding zero perceived latency
- **Append-only**: Both `llm_interaction_logs` and `llm_query_embeddings` are append-only tables (no UPDATE)
- **Feedback-driven**: Improves automatically as users submit negative ratings — no manual labeling required

**Components**:
- `services/bq_embedding_service.py` — VECTOR_SEARCH wrapper with graceful fallback
- `llm_query_embeddings` BQ table — stores embeddings of bad-rated queries
- BQ Scheduled Query (daily) — batch embedding generation
- Frontend warning banner — amber alert with `AlertTriangle` icon

**New BQ Resources**:
- `mlb_analytics_dash_25.query_embedding_model` — Remote model (Vertex AI `text-multilingual-embedding-002`)
- `mlb_analytics_dash_25.llm_query_embeddings` — Embedding storage table
- BQ Connection: `asia-northeast1.vertex_ai_connection`

### 12. Embedding-Based Semantic Data Drift Detection
**Status**: ✅ Production-ready

**Overview**: Complements existing statistical drift detection (KS test / PSI) by detecting *semantic* shifts in pitching characteristics using BigQuery ML embeddings. Weekly snapshots of league-wide pitch arsenal metrics — aggregated per pitch type (4-Seam Fastball, Slider, Changeup, Curveball, etc.) — are embedded and compared against a 4-week rolling baseline using cosine distance.

**Architecture**:
```
[Weekly Batch: Monday 03:00 UTC]
  statcast_master
    → Aggregate per pitch_name: avg_velo, avg_spin, pfx_x, pfx_z,
      api_break_z_with_gravity, release_extension, usage_pct, avg_delta_run_exp
    → Concatenate all pitch types into single metrics_text string
    → ML.GENERATE_EMBEDDING → INSERT INTO pitcher_metrics_snapshots

[At Drift Detection Time]
  Current week snapshot embedding
    → ML.DISTANCE (COSINE) vs 4-week baseline centroid
    → semantic_drift_score appended to existing DriftReport
```

**Why per pitch type**: Each pitch type has completely different velocity ranges, spin rates, and movement profiles. Aggregating across all pitch types would mask meaningful changes — e.g., a league-wide velocity drop on fastballs or a shift in slider sweep angle.

**Drift Thresholds**:
| Score | Status |
|-------|--------|
| < 0.10 | `stable` |
| 0.10 – 0.20 | `warning` |
| ≥ 0.20 | `critical` |

**Components**:
- `services/bq_drift_embedding_service.py` — Cosine distance computation via BQ ML
- `services/data_drift_service.py` — `semantic_drift` field added to `DriftReport`
- `queries/create_pitcher_metrics_snapshots.sql` — Table DDL
- `queries/scheduled_pitcher_embedding_weekly.sql` — Weekly embedding generation

**New BQ Resources**:
- `mlb_analytics_dash_25.pitcher_metrics_snapshots` — Weekly pitch arsenal snapshots with embeddings
- BQ Scheduled Query: `pitcher_metrics_weekly_embedding` (Monday 03:00 UTC)

### Technical Features
- **AI-Powered Processing**: Uses Gemini 2.5 Flash for query parsing and response generation
- **Real-time Interface**: Interactive experience with loading states and live updates
- **MCP Server Support**: Access MLB stats directly from Claude Desktop and Cursor via Model Context Protocol
- **Case-insensitive Search**: Flexible player name matching
- **Dark Theme UI**: Modern, responsive interface optimized for extended use
- **Secure Access**: Firebase Authentication with Google Sign-In and server-side token verification
- **SQL Injection Protection**: Multi-layered security with input validation and parameterized queries
- **Rate Limiting**: Multi-tier rate limiting (Global, Per-Session, Per-Endpoint) with LLM token budget tracking

## 🏗 Architecture

### Core Data Processing Pipeline
The application follows a sophisticated 4-step pipeline:

1. **🧠 LLM Query Parsing** (`ai_service._parse_query_with_llm`)
   - Converts natural language (Japanese) to structured JSON parameters
   - Uses Gemini 2.5 Flash to extract player names, metrics, seasons, query types
   - Normalizes player names to English full names

2. **⚙️ Dynamic SQL Generation** (`ai_service._build_dynamic_sql`)
   - Maps extracted parameters to BigQuery table schemas via `query_maps.py`
   - Handles multiple query types: `season_batting`, `season_pitching`, `batting_splits`
   - Supports situational splits (RISP, bases loaded, inning-specific, etc.)
   - **Security**: Uses parameterized queries to prevent SQL injection attacks

3. **📊 BigQuery Data Retrieval**
   - Executes generated SQL against MLB statistics tables in GCP project `your-project-id`
   - Main tables: `fact_batting_stats_with_risp`, `fact_pitching_stats`
   - Specialized tables for splits: `tbl_batter_clutch_*`, `mart_batter_inning_stats`, etc.

4. **💬 LLM Response Generation** (`ai_service._generate_final_response_with_llm`)
   - Converts structured data back to natural Japanese responses
   - Supports both narrative (`sentence`) and tabular (`table`) output formats

5. **🤖 Autonomous Multi-Agent Reasoning** (`app/services/agents/`)
   - **Supervisor Architecture**: Decouples query routing from data retrieval via a `SupervisorAgent`.
   - **Specialized Agents**: 
     - `StatsAgent`: Handles general statistical queries and trend analysis.
     - `MatchupAgent`: Handles specific head-to-head player historical comparisons.
   - **LangGraph Implementation**: Each agent maintains its own "Oracle" (Planning), "Executor" (Data Retrieval), and "Synthesizer" (Final Reporting) loop.
   - **Feedback Loop**: Agents can self-correct and perform multiple tool calls if the initial measurement is insufficient.
   - **Reflection Loop**: Each agent includes a `reflection` node that detects executor errors (SQL syntax, empty results) and feeds diagnostic context back to the LLM for self-correction, with a max retry cap to prevent infinite loops.
   - **Integrated UI**: Pipes structured chart/table metadata directly into the specialized frontend components.

### ML Model Architecture: 3-Layer Separation of Concerns

The project follows modern MLOps best practices by separating machine learning workflows into three distinct layers:

```
┌─────────────────────────────────────────────────────────────────┐
│ [1] Training Layer (Local or Vertex AI Pipelines)              │
│  ├── Notebook/Script: FT-Transformer & K-means training        │
│  ├── Model evaluation & comparison                             │
│  └── Model registration to Vertex AI Model Registry (GCS)      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ [2] Inference Layer (Vertex AI Endpoint) - OPTIONAL            │
│  ├── Managed model hosting & auto-scaling                      │
│  ├── Online prediction API                                     │
│  └── Requires custom container for PyTorch models (not used)   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ [3] Application Layer (FastAPI on Cloud Run) - LIGHTWEIGHT     │
│  ├── Data retrieval from BigQuery                              │
│  ├── Local K-means inference (default)                         │
│  ├── OR HTTP calls to Vertex AI Endpoint (optional)            │
│  └── No PyTorch/heavy ML dependencies in production            │
└─────────────────────────────────────────────────────────────────┘
```

#### Why This Architecture?

**2024-2025 Approach (Monolithic):**
- ❌ Training + Inference in FastAPI backend
- ❌ PyTorch in Cloud Run container (3.9GB image size)
- ❌ High memory usage and slow cold starts
- ❌ Tight coupling between training and serving

**2026 Approach (Separation of Concerns):**
- ✅ Training isolated in notebooks/scripts (`scripts/train_and_register_ft_transformer.py`)
- ✅ Models versioned in Vertex AI Model Registry (GCS storage, ~$0.002/month)
- ✅ Lightweight FastAPI backend (no PyTorch in production)
- ✅ Optional Vertex AI Endpoint for high-scale inference
- ✅ Easy rollback and A/B testing with model versions

#### Current Implementation

**Training:**
- Location: `scripts/train_and_register_ft_transformer.py`, `analysis/kmeans_vs_ft_transformer.ipynb`
- Run locally with PyTorch installed
- Registers models to Vertex AI Model Registry

**Inference:**
- Default: Local K-means clustering (lightweight, fast)
- Optional: Vertex AI Endpoint (via HTTP, switchable with env var `USE_VERTEX_AI_ENDPOINT`)
- Automatic fallback to local K-means if Vertex AI fails

**Cost Comparison:**
| Component | Current (Default) | Optional (Vertex AI) |
|-----------|------------------|----------------------|
| Model Storage | GCS: $0.002/month | GCS: $0.002/month |
| Compute | Cloud Run (included) | Endpoint: $73/month (24/7) |
| **Total** | **~$0** | **~$73/month** |

→ **Recommended**: Use default local K-means unless high-scale inference is required.

### Key Configuration System
- **`query_maps.py`**: Central configuration for all query types and metric mappings
- **`QUERY_TYPE_CONFIG`**: Maps query types to table schemas and column mappings
- **`METRIC_MAP`**: Translates semantic metric names to actual database column names
- Supports complex metric mappings across different split contexts

## 🛠 Technical Stack

### Frontend
- **React 19.1.1** - Modern React with latest features
- **Vite 7.1.2** - Fast build tool and development server
- **Firebase SDK** - Google Sign-In authentication
- **Tailwind CSS 4.1.11** - Utility-first CSS framework with dark mode
- **Lucide React 0.539.0** - Beautiful icon library
- **ESLint** - Code linting and formatting

### Backend
- **FastAPI** - Modern Python web framework
- **Uvicorn** - ASGI server for production deployment
- **Firebase Admin SDK** - Server-side authentication and token verification
- **MCP Server** - Model Context Protocol server for Claude Desktop/Cursor integration
- **Google Cloud BigQuery** - Data warehouse for MLB statistics
- **Google Cloud Storage** - Additional data storage
- **Gemini 2.5 Flash API** - AI-powered query processing
- **XGBoost** - Gradient boosting for Stuff+/Pitching+ pitch quality models

### Infrastructure
- **Docker** - Containerized deployment
- **Google Cloud Run** - Serverless container platform
- **Terraform** - Infrastructure as Code for GCP resources
- **Cloud Build** - CI/CD pipeline automation
- **GitHub Codespaces** - Cloud development environment support
- **Nginx** - Production web server (frontend)

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- Google Cloud Project with BigQuery access
- Gemini API key

### Environment Setup

Create a `.env` file in the backend directory:

```env
GCP_PROJECT_ID=<project-id>
BIGQUERY_DATASET_ID=<dataset_name>
BIGQUERY_BATTING_STATS_TABLE_ID=fact_batting_stats_with_risp
BIGQUERY_PITCHING_STATS_TABLE_ID=fact_pitching_stats
GEMINI_API_KEY=<your_gemini_api_key>
GOOGLE_APPLICATION_CREDENTIALS=<path_to_service_account_json>
```

Create a `.env` file in the frontend directory:

```env
VITE_FIREBASE_API_KEY=<your_firebase_api_key>
VITE_FIREBASE_AUTH_DOMAIN=<your_project>.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=<your_project_id>
VITE_FIREBASE_STORAGE_BUCKET=<your_project>.firebasestorage.app
VITE_FIREBASE_MESSAGING_SENDER_ID=<your_sender_id>
VITE_FIREBASE_APP_ID=<your_app_id>
```

### Development

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev          # Start development server (port 5173)
npm run build        # Build for production
npm run lint         # Run ESLint
npm run preview      # Preview production build
```

#### Backend Setup
```bash
cd backend
pip install -r requirements.txt
# For development with proper module resolution:
PYTHONPATH=/path/to/diamond-lens python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Deployment

#### Docker Build
```bash
# Frontend
cd frontend
docker build -t diamond-lens-frontend .

# Backend
cd backend  
docker build -t diamond-lens-backend .
```

#### Google Cloud Run with CI/CD
The project uses Cloud Build for automated CI/CD pipeline with integrated Terraform infrastructure management.

See [TERRAFORM_INTEGRATION_GUIDE.md](TERRAFORM_INTEGRATION_GUIDE.md) for detailed setup instructions.

## 📡 API Documentation

### Natural Language Q&A API

**POST** `/api/v1/qa/player-stats`

#### Request Format
```json
{
  "query": "大谷翔平の2024年の打率は？",
  "season": 2024
}
```

#### Response Format
```json
{
  "answer": "大谷翔平の2024年シーズンの打率は.310でした。",
  "isTable": false,
  "isTransposed": false,
  "tableData": null,
  "columns": null,
  "decimalColumns": [],
  "grouping": null,
  "stats": {
    "games": "150",
    "hits": "186",
    "at_bats": "600"
  }
}
```

---

### Autonomous Agent API (LangGraph)

**POST** `/api/v1/qa/agentic-stats`

Advanced multi-step analysis powered by LangGraph. Supports complex reasoning and automated visualization.

#### Request Format
```json
{
  "query": "Compare Shohei Ohtani and Aaron Judge's 2024 performance with a chart",
  "session_id": "optional-uuid"
}
```

#### Response Format
```json
{
  "query": "...",
  "answer": "...",
  "steps": [
    {"thought": "...", "tool_call": "...", "status": "planning"},
    {"thought": "...", "status": "executing"}
  ],
  "is_agentic": true,
  "isChart": true,
  "chartData": [...],
  "processing_time_ms": 12500
}
```

---

### Autonomous Agent Streaming API (Server-Sent Events)

**POST** `/api/v1/qa/agentic-stats-stream`

Real-time streaming version of the agent API. Uses Server-Sent Events (SSE) to stream agent reasoning steps and LLM tokens as they are generated.

#### Request Format
```json
{
  "query": "大谷翔平の2024年の打率は？",
  "session_id": "optional-uuid"
}
```

#### Response Format (SSE Stream)
```
event: session_start
data: {"type":"session_start","session_id":"...","query":"..."}

event: routing
data: {"type":"routing","agent_type":"batter","message":"batterエージェントにルーティングしました"}

event: state_update
data: {"type":"state_update","node":"oracle","status":"started","message":"質問を分析しています"}

event: token
data: {"type":"token","content":"大谷","node":"synthesizer"}

event: final_answer
data: {"type":"final_answer","answer":"大谷翔平選手は2024年シーズンに打率.310を記録しました。","isTable":false,...}

event: stream_end
data: {"type":"stream_end","message":"処理が完了しました"}
```

#### Event Types
- `session_start`: Session initialization
- `routing`: Agent routing decision
- `state_update`: Agent node state changes (oracle, executor, synthesizer)
- `tool_start/tool_end`: Tool execution events
- `token`: LLM token streaming (real-time response generation)
- `final_answer`: Complete response with metadata
- `stream_end`: Stream completion
- `error`: Error occurred during processing

#### Frontend Integration
```javascript
const response = await fetch('/api/v1/qa/agentic-stats-stream', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({query: "..."})
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const {done, value} = await reader.read();
  if (done) break;

  const text = decoder.decode(value);
  // Parse SSE format: "event: <type>\ndata: <json>\n\n"
}
```

---

### Statistical Analysis API

**GET** `/api/v1/statistics/predict-winrate`

Predict team win rate based on offensive and pitching metrics.

#### Query Parameters
- `team_ops` (float, required): Team OPS (On-base Plus Slugging), range 0.0-2.0
- `team_era` (float, required): Team ERA (Earned Run Average), range 0.0-10.0
- `team_hrs_allowed` (int, required): Home runs allowed, range 0-300

#### Response Format
```json
{
  "input_ops": 0.75,
  "input_era": 4.2,
  "input_hrs_allowed": 180,
  "predicted_win_rate": 0.5328,
  "expected_wins_per_season": 86,
  "model_metrics": {
    "r2_score": 0.942,
    "mse": 0.0,
    "mae": 0.0157
  },
  "interpretation": "OPS 0.750、ERA 4.200のチームは勝率0.533 (年間約86勝)を記録し、Playoff hopefulと予測されます。"
}
```

---

**GET** `/api/v1/statistics/model-summary`

Get regression model evaluation metrics and coefficients.

#### Response Format
```json
{
  "model_type": "Linear Regression",
  "metrics": {
    "r2_score": 0.942,
    "rmse": 0.0253,
    "mae": 0.0157
  },
  "regression_equation": {
    "coefficient_ops": 1.1793,
    "coefficient_era": -0.0932,
    "coefficient_hrs_allowed": -0.0002,
    "intercept": -0.3456,
    "formula": "win_rate = 1.1793 * ops + (-0.0932) * era + (-0.0002) * hrs_allowed + (-0.3456)"
  },
  "interpretation": {
    "ops_increase_0.01": "OPSが0.01増加すると、勝率は0.0118向上し、シーズン勝利数は約1.9勝増加します。",
    "era_increase_0.01": "ERAが0.01増加すると、勝率は-0.0009低下し、シーズン勝利数は約-0.2勝減少します。"
  }
}
```

---

**GET** `/api/v1/statistics/ops-sensitivity`

Analyze OPS impact on win rate with fixed ERA and home runs allowed.

#### Query Parameters (optional)
- `fixed_era` (float, default: 4.00): Fixed ERA value
- `fixed_hrs_allowed` (int, default: 180): Fixed home runs allowed

#### Response Format
```json
{
  "data": [
    {"ops": 0.650, "win_rate": 0.4523, "expected_wins": 73},
    {"ops": 0.660, "win_rate": 0.4635, "expected_wins": 75},
    ...
  ],
  "count": 21
}
```

---

#### Additional Endpoints
- **GET** `/health` - Health check endpoint
- **GET** `/debug/routes` - Debug route listing
- **GET** `/docs` - Swagger UI for API testing

## 🔧 Configuration

### Query Types Supported
- **Chat Mode**: Natural language processing for batting/pitching questions
- **Quick Questions**: Pre-configured queries for common statistics
- **Custom Analytics**: Advanced situational analysis with:
  - `batting_splits` - RISP, bases loaded, custom situations
  - `statcast_advanced` - Exit velocity, launch angle, hard hit rates
  - Career aggregation and YoY trend analysis

### BigQuery Integration
- **Singleton Pattern**: Efficient BigQuery client management in `bigquery_service.py`
- **Project**: Hardcoded to GCP project `your-project-id`
- **Authentication**: Service account based authentication required

### LLM Integration
- **Dual Usage**: Query parsing + response generation
- **Language**: Japanese language processing with English name normalization
- **Format**: Structured JSON response formatting with retry logic

## 🎨 UI Features

- **Dark Theme**: Permanent dark mode optimized for extended use
- **Responsive Design**: Mobile-friendly interface
- **Real-time Updates**: Live message updates with typing indicators
- **Firebase Authentication**: Google Sign-In with server-side token verification
- **Auto-scroll**: Automatic scrolling to latest messages
- **Loading States**: Visual feedback during API calls
- **Error Handling**: Graceful error display and recovery

## 🏗️ Infrastructure Management

### Terraform Configuration

This project uses Terraform to manage GCP infrastructure as code:

- **Cloud Run Services**: Backend and frontend service configurations
- **BigQuery Dataset**: MLB statistics data warehouse
- **IAM Permissions**: Service account roles and access control
- **State Management**: Remote state stored in GCS bucket

Infrastructure is organized as reusable modules:

```
terraform/
├── modules/
│   ├── cloud-run/         # Reusable Cloud Run module
│   ├── bigquery/          # BigQuery dataset module
│   ├── iam/               # IAM configuration module
│   └── secrets/           # Secret Manager module (not used)
└── environments/
    └── production/        # Production environment config
        └── main.tf        # Main Terraform configuration
```

### CI/CD Pipeline

The deployment pipeline is fully automated via Cloud Build with integrated testing:

```
git push → Cloud Build Trigger → cloudbuild.yaml execution
  ↓
┌─────────────────────────────────────┐
│ STEP 0: Unit Tests                  │
│  - Run pytest (49 tests)            │
│  - Test query_maps configuration    │
│  - Test SQL generation logic        │
│  ⚠️  If tests fail → Build stops    │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ STEP 1: Schema Validation GATE      │
│  - Validate query_maps.py config    │
│  - Compare with live BigQuery schema│
│  - Check column existence           │
│  ⚠️  If mismatch → Build stops      │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ STEP 1.5: LLM Evaluation GATE      │
│  - Run LLM against golden dataset   │
│  - Evaluate parse accuracy (≥80%)   │
│  - Check critical fields            │
│  ⚠️  If accuracy drops → Build stops │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ STEP 1.6: ML Data Drift Check GATE │
│  - Auto-detect baseline from        │
│    Model Registry active version    │
│  - PSI/KS test on model features    │
│  ⚠️  If critical drift → Build stops │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ STEP 2: Terraform (Infrastructure)  │
│  - terraform init                   │
│  - terraform plan                   │
│  - terraform apply (if changes)     │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ STEP 3: Backend Build & Push        │
│  - Docker build                     │
│  - Push to gcr.io                   │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ STEP 4: Backend Security Scan       │
│  - Trivy vulnerability scan         │
│  - Check HIGH/CRITICAL CVEs         │
│  ⚠️  If vulnerabilities → Build stops│
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ STEP 5: Backend Deploy              │
│  - Deploy to Cloud Run              │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ STEP 6-7: Frontend Build & Push     │
│  - Docker build                     │
│  - Push to gcr.io                   │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ STEP 8: Frontend Security Scan      │
│  - Trivy vulnerability scan         │
│  - Check HIGH/CRITICAL CVEs         │
│  ⚠️  If vulnerabilities → Build stops│
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ STEP 9: Frontend Deploy             │
│  - Deploy to Cloud Run              │
└─────────────────────────────────────┘
```

**Key Features:**
- **Automated testing:** Unit tests run before every deployment
- **Schema validation gate:** Ensures `query_maps.py` matches live BigQuery schema
- **LLM evaluation gate:** Validates LLM parse accuracy against golden dataset before deployment
- **ML drift check gate:** Detects critical data drift in ML model inputs using Model Registry auto-baseline
- **Security scanning:** Trivy scans Docker images for HIGH/CRITICAL vulnerabilities
- **Fail-fast approach:** Test, schema, LLM accuracy, or security failures prevent deployment
- Infrastructure changes are applied before application deployment
- Terraform only executes if infrastructure changes are detected
- Docker images are built and deployed after infrastructure updates
- Secrets are managed outside Terraform for security

### Security

The application implements multiple layers of security to protect against SQL injection, unauthorized access, and other attacks:

**Security Measures:**

0. **Firebase Authentication**:
   - Google Sign-In on the frontend via Firebase SDK (`signInWithPopup` + `GoogleAuthProvider`)
   - Server-side token verification via Firebase Admin SDK (`firebase-admin`)
   - Pure ASGI middleware (`FirebaseAuthMiddleware`) validates `Authorization: Bearer <token>` on all API requests
   - Public paths (`/health`, `/docs`, etc.) are excluded from authentication
   - User identity (`user_id`, `email`) is extracted and passed to endpoints for per-user logging
   - Content Security Policy (CSP) configured to allow Google/Firebase authentication domains

1. **Input Validation** (`_validate_query_params`):
   - Validates all LLM-generated parameters before SQL generation
   - Checks for SQL keywords (SELECT, UNION, DROP, etc.)
   - Enforces character whitelists for player names
   - Validates data types, ranges, and formats
   - Rejects malicious patterns (e.g., `' OR '1'='1`)

2. **Parameterized Queries**:
   - All user inputs are passed as BigQuery query parameters
   - SQL structure is separated from data values
   - Prevents injection attacks at the database level
   - Uses placeholders (e.g., `@player_name`) instead of string concatenation

3. **Whitelist-based ORDER BY**:
   - ORDER BY clauses use only pre-defined columns from `METRIC_MAP`
   - Direct user input never used in ORDER BY clauses

4. **Rate Limiting** (`RateLimitMiddleware` + `slowapi`):
   - Global rate limit (100 req/min) via custom ASGI middleware
   - Per-session rate limit (20 req/min) keyed by Firebase user_id, session ID, or IP
   - Per-endpoint rate limits via slowapi decorators with dynamic `.env` configuration
   - LLM token budget (daily cap) to prevent runaway API costs
   - All rejections logged to Cloud Monitoring and BigQuery `llm_interaction_logs`
   - In-memory storage (no Redis) — suitable for Cloud Run single-container deployment

**Test Coverage:**
- `test_security.py`: SQL injection attack patterns and input validation
- Tests validate both blocking malicious inputs and allowing legitimate ones

### Testing

The project includes comprehensive unit tests for critical business logic:

**Test Coverage (95+ tests):**
- `test_query_maps.py` (21 tests): Configuration validation and data structure integrity
- `test_build_dynamic_sql.py` (28 tests): SQL generation logic for all query types
- `test_security.py` (13 tests): SQL injection prevention and input validation
- `test_reflection_loop.py` (11 tests): Reflection loop self-correction logic, error classification, and executor empty result detection
- `test_data_drift.py` (17 tests): Data drift detection logic (PSI, KS test, severity determination)
- `test_ft_transformer.py` (5 tests): FT-Transformer encoder architecture and self-supervised training
- `test_model_registry.py` (5+ tests): Model registry service (train, register, load, promote with mocked GCS/BigQuery)

**Run tests locally:**
```bash
cd backend
pip install pytest pytest-asyncio
export PYTHONPATH=$(pwd)  # Linux/Mac
set PYTHONPATH=%cd%       # Windows
python -m pytest tests/ -v
```

**Test categories:**
- Query type configuration validation
- Metric mapping integrity
- SQL generation for season batting/pitching
- Career statistics queries
- Batting splits (RISP, bases loaded, inning-specific, etc.)
- Edge case handling and error validation

### Schema Validation

The Schema Validation GATE ensures data integrity between application configuration and database:

**What it validates:**
- All tables referenced in `query_maps.py` exist in BigQuery
- Required columns (`year_col`, `player_col`, `month_col`) exist in their respective tables
- All `available_metrics` columns exist in the actual table schemas
- All `METRIC_MAP` column mappings point to valid columns

**Run validation locally:**
```bash
cd backend
export GCP_PROJECT_ID=your-project-id
export BIGQUERY_DATASET_ID=your-dataset-id
python scripts/validate_schema_config.py
```

**When validation fails:**
- CI/CD pipeline stops immediately (before costly build steps)
- Error messages indicate which columns are missing
- Action required: Update `query_maps.py` or BigQuery schema to match

This gate prevents runtime errors from schema mismatches and catches configuration bugs early.

### Security Scanning

Container images are scanned for vulnerabilities before deployment using Trivy:

**What it scans:**
- Operating system packages (Debian, Alpine, etc.)
- Application dependencies (Python packages, npm packages)
- Known CVEs (Common Vulnerabilities and Exposures)
- Severity levels: HIGH and CRITICAL only

**Scan process:**
```
Docker Image Build → Push to GCR → Trivy Scan → Deploy (if no vulnerabilities)
```

**When vulnerabilities are found:**
- CI/CD pipeline stops immediately (before deployment)
- Trivy reports which packages have vulnerabilities
- Action required: Update base image or dependencies

**What's checked:**
- Backend image: Python dependencies, OS packages
- Frontend image: Node.js dependencies, nginx, OS packages

This ensures no known high-severity vulnerabilities reach production.

### Monitoring & Alerting

The application implements comprehensive monitoring across infrastructure and application layers:

#### Infrastructure Layer Monitoring

**Uptime Checks:**
- Backend `/health` endpoint: 60-second interval checks from 3 global regions (USA, EUROPE, ASIA_PACIFIC)
- Frontend `/` endpoint: 60-second interval checks from 3 global regions
- SSL validation and HTTPS enforcement

**Alert Policies:**
- **Service Down**: Triggered when uptime checks fail for 60 seconds continuously
- **High Memory Usage**: Alert when Cloud Run memory exceeds 80% for 5 minutes
- **High CPU Usage**: Alert when Cloud Run CPU exceeds 80% for 5 minutes
- **Notification**: Email alerts with 30-minute auto-close after resolution

**Terraform Configuration:**
```bash
cd terraform/environments/production
terraform apply -var="notification_email=your-email@example.com"
```

#### Application Layer Monitoring

**Custom Metrics tracked:**
- `api/latency`: Request latency per endpoint (ms)
- `api/errors`: Error count by endpoint and error type
- `query/processing_time`: Query processing duration by query type (ms)
- `bigquery/latency`: BigQuery execution time by query type (ms)
- `rate_limit/rejections`: Rate limit rejection count by endpoint and limit type (global, session, endpoint)

**Structured Logging:**
- JSON-formatted logs compatible with Google Cloud Logging
- Automatic parsing and indexing by Cloud Logging
- Searchable fields: `timestamp`, `severity`, `message`, `query_type`, `latency_ms`, `error_type`

**Error Classification:**
- `validation_error`: Input validation failures
- `bigquery_error`: Database query failures
- `llm_error`: AI model processing errors
- `null_response`: Empty response from services

**Log Severity Levels:**
- `DEBUG`: Detailed debugging information
- `INFO`: Normal operation events (requests, completions)
- `WARNING`: Non-critical issues
- `ERROR`: Error events that need attention
- `CRITICAL`: Critical failures requiring immediate action

**View logs and metrics:**
```bash
# Cloud Logging
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Cloud Monitoring Metrics Explorer
# Navigate to: Cloud Console → Monitoring → Metrics Explorer
# Custom metrics: custom.googleapis.com/diamond-lens/*
```

For detailed Terraform setup and integration instructions, see [TERRAFORM_INTEGRATION_GUIDE.md](TERRAFORM_INTEGRATION_GUIDE.md).

## 📁 Project Structure

```
diamond-lens/
├── frontend/                 # React frontend application
│   ├── src/
│   │   ├── App.jsx          # Main application component
│   │   ├── firebase.js      # Firebase SDK configuration
│   │   ├── hooks/useAuth.js # Google Sign-In authentication hook
│   │   ├── main.jsx         # Application entry point
│   │   └── index.css        # Global styles
│   ├── tailwind.config.js   # Tailwind CSS configuration
│   ├── package.json         # Frontend dependencies
│   └── Dockerfile           # Frontend container
├── backend/                  # FastAPI backend application
│   ├── app/
│   │   ├── main.py          # FastAPI application
│   │   ├── api/endpoints/   # API route handlers
│   │   ├── middleware/       # ASGI middleware
│   │   │   ├── firebase_auth.py    # Firebase token verification middleware
│   │   │   ├── rate_limit.py       # Global/Per-session rate limiting (in-memory)
│   │   │   └── request_id.py       # Request ID tracking
│   │   ├── services/        # Business logic services
│   │   │   ├── ai_service.py       # AI query processing
│   │   │   ├── bigquery_service.py # BigQuery client
│   │   │   ├── firebase_service.py # Firebase Admin SDK initialization
│   │   │   ├── llm_logger_service.py # LLM I/O logging to BigQuery (with user_id)
│   │   │   ├── data_drift_service.py  # Data drift detection (PSI, KS test)
│   │   │   ├── ml_monitoring_logger.py # ML monitoring logs to BigQuery
│   │   │   ├── ft_transformer.py          # FT-Transformer encoder for player segmentation
│   │   │   ├── model_registry_service.py # Model Registry & Versioning (GCS + BQ)
│   │   │   ├── stuff_plus_service.py    # Stuff+/Pitching+ inference & rankings
│   │   │   ├── monitoring_service.py # Custom metrics
│   │   │   └── token_budget_service.py # Daily LLM token budget (in-memory)
│   │   ├── prompts/         # Versioned LLM prompt templates
│   │   │   ├── parse_query_v1.txt  # Query parsing prompt
│   │   │   └── routing_v1.txt      # Agent routing prompt
│   │   ├── utils/           # Utility functions
│   │   │   └── structured_logger.py # JSON logging
│   │   ├── config/          # Configuration and mappings
│   │   │   ├── prompt_registry.py  # Prompt version management
│   │   │   └── settings.py        # App settings (rate limits, budgets, etc.)
│   │   └── api/
│   │       └── rate_limit.py      # slowapi per-endpoint rate limiter
│   ├── tests/               # Unit tests + golden dataset
│   │   ├── golden_dataset.json    # LLM evaluation test cases
│   │   └── pending_review.json    # HITL feedback pending human review
│   ├── scripts/             # Validation and evaluation scripts
│   │   ├── extract_golden_dataset.py  # Extract bad-rated queries from BigQuery
│   │   ├── approve_to_golden.py       # Promote reviewed cases to golden dataset
│   │   ├── evaluate_llm_accuracy.py   # CI/CD LLM accuracy gate
│   │   ├── check_data_drift.py        # CI/CD ML drift check gate
│   │   └── create_drift_monitoring_table.py # BigQuery table setup
│   ├── requirements.txt     # Python dependencies
├── scripts/                  # ML training scripts
│   └── train_stuff_plus.py  # Stuff+/Pitching+ training pipeline
│   └── Dockerfile           # Backend container
├── terraform/                # Infrastructure as Code
│   ├── modules/             # Reusable Terraform modules
│   │   ├── cloud-run/       # Cloud Run service module
│   │   ├── bigquery/        # BigQuery dataset module
│   │   ├── monitoring/      # Monitoring & alerting module
│   │   └── iam/             # IAM configuration module
│   └── environments/        # Environment-specific configs
│       └── production/      # Production environment
├── CLAUDE.md                # Development guidance
├── cloudbuild.yaml          # CI/CD pipeline config
├── TERRAFORM_INTEGRATION_GUIDE.md  # Terraform setup guide
└── README.md                # This file
```

## 🤝 Contributing

This project follows standard Git workflow:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📜 License

This project is for educational and demonstration purposes.

---

**MLB Stats Assistant v1.0** - Bringing AI-powered baseball analytics to your fingertips! 🔮⚾