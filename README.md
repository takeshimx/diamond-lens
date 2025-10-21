# Diamond Lens - MLB Stats Assistant 🔮⚾

An AI-powered analytics interface for exploring Major League Baseball statistics through natural language queries and advanced custom analytics. Built with React, FastAPI, and Google Cloud BigQuery.

## 🌟 Features

### 1. Natural Language Q&A Interface (Full Stack)
**Status**: ✅ Production-ready with frontend UI

- **💬 Chat Mode**: Natural language queries in Japanese with AI-powered responses
- **⚡ Quick Questions**: Pre-defined common baseball queries for instant results
- **⚙️ Custom Query Builder**: Advanced analytics with custom situational filters

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

**Technologies**: React, Recharts, scikit-learn, pandas, FastAPI

**Analysis Notebooks**:
- `analysis/player_segmentation.ipynb` - K-means clustering analysis with visualizations

**Business Applications**:
- **Roster Construction**: Identify player archetypes for targeted acquisitions
- **Platoon Optimization**: Match player types to game situations
- **Trade Analysis**: Evaluate fit within team composition
- **Scouting Efficiency**: Categorize prospects by performance profile

### Technical Features
- **AI-Powered Processing**: Uses Gemini 2.5 Flash for query parsing and response generation
- **Real-time Interface**: Interactive experience with loading states and live updates
- **Case-insensitive Search**: Flexible player name matching
- **Dark Theme UI**: Modern, responsive interface optimized for extended use
- **Secure Access**: Password-protected interface for authorized users
- **SQL Injection Protection**: Multi-layered security with input validation and parameterized queries

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
   - Specialized tables for splits: `tbl_batter_clutch_*`, `tbl_batter_inning_stats`, etc.

4. **💬 LLM Response Generation** (`ai_service._generate_final_response_with_llm`)
   - Converts structured data back to natural Japanese responses
   - Supports both narrative (`sentence`) and tabular (`table`) output formats

### Key Configuration System
- **`query_maps.py`**: Central configuration for all query types and metric mappings
- **`QUERY_TYPE_CONFIG`**: Maps query types to table schemas and column mappings
- **`METRIC_MAP`**: Translates semantic metric names to actual database column names
- Supports complex metric mappings across different split contexts

## 🛠 Technical Stack

### Frontend
- **React 19.1.1** - Modern React with latest features
- **Vite 7.1.2** - Fast build tool and development server
- **Tailwind CSS 4.1.11** - Utility-first CSS framework with dark mode
- **Lucide React 0.539.0** - Beautiful icon library
- **ESLint** - Code linting and formatting

### Backend
- **FastAPI** - Modern Python web framework
- **Uvicorn** - ASGI server for production deployment
- **Google Cloud BigQuery** - Data warehouse for MLB statistics
- **Google Cloud Storage** - Additional data storage
- **Gemini 2.5 Flash API** - AI-powered query processing

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
VITE_APP_PASSWORD=<your_app_password>
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
- **Password Protection**: Secure access control
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
- **Security scanning:** Trivy scans Docker images for HIGH/CRITICAL vulnerabilities
- **Fail-fast approach:** Test, schema, or security failures prevent deployment
- Infrastructure changes are applied before application deployment
- Terraform only executes if infrastructure changes are detected
- Docker images are built and deployed after infrastructure updates
- Secrets are managed outside Terraform for security

### Security

The application implements multiple layers of security to protect against SQL injection and other attacks:

**Security Measures:**
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

**Test Coverage:**
- `test_security.py`: SQL injection attack patterns and input validation
- Tests validate both blocking malicious inputs and allowing legitimate ones

### Testing

The project includes comprehensive unit tests for critical business logic:

**Test Coverage (62 tests):**
- `test_query_maps.py` (21 tests): Configuration validation and data structure integrity
- `test_build_dynamic_sql.py` (28 tests): SQL generation logic for all query types
- `test_security.py` (13 tests): SQL injection prevention and input validation

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
│   │   ├── main.jsx         # Application entry point
│   │   └── index.css        # Global styles
│   ├── tailwind.config.js   # Tailwind CSS configuration
│   ├── package.json         # Frontend dependencies
│   └── Dockerfile           # Frontend container
├── backend/                  # FastAPI backend application
│   ├── app/
│   │   ├── main.py          # FastAPI application
│   │   ├── api/endpoints/   # API route handlers
│   │   ├── services/        # Business logic services
│   │   │   ├── ai_service.py       # AI query processing
│   │   │   ├── bigquery_service.py # BigQuery client
│   │   │   └── monitoring_service.py # Custom metrics
│   │   ├── utils/           # Utility functions
│   │   │   └── structured_logger.py # JSON logging
│   │   └── config/          # Configuration and mappings
│   ├── tests/               # Unit tests (49 tests)
│   ├── scripts/             # Validation and utility scripts
│   ├── requirements.txt     # Python dependencies
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