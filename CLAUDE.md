# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Frontend (React + Vite)
```bash
cd frontend
npm run dev          # Start development server (port 5173)
npm run build        # Build for production
npm run lint         # Run ESLint
npm run preview      # Preview production build
```

### Backend (FastAPI)
```bash
cd backend
# Set up Python virtual environment and install dependencies
pip install -r requirements.txt
# Run development server (typically port 8000)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Architecture Overview

### Core Data Processing Pipeline
The application follows a 4-step pipeline for natural language MLB queries:

1. **LLM Query Parsing** (`ai_service._parse_query_with_llm`)
   - Converts natural language (Japanese) to structured JSON parameters
   - Uses Gemini 2.5 Flash to extract player names, metrics, seasons, query types
   - Normalizes player names to English full names

2. **Dynamic SQL Generation** (`ai_service._build_dynamic_sql`)
   - Maps extracted parameters to BigQuery table schemas via `query_maps.py`
   - Handles multiple query types: `season_batting`, `season_pitching`, `batting_splits`
   - Supports situational splits (RISP, bases loaded, inning-specific, etc.)

3. **BigQuery Data Retrieval**
   - Executes generated SQL against MLB statistics tables in GCP project `tksm-dash-test-25`
   - Main tables: `fact_batting_stats_with_risp`, `fact_pitching_stats`
   - Specialized tables for splits: `tbl_batter_clutch_*`, `mart_batter_inning_stats`, etc.

4. **LLM Response Generation** (`ai_service._generate_final_response_with_llm`)
   - Converts structured data back to natural Japanese responses
   - Supports both narrative (`sentence`) and tabular (`table`) output formats

### Key Configuration System
- **`query_maps.py`**: Central configuration for all query types and metric mappings
  - `QUERY_TYPE_CONFIG`: Maps query types to table schemas and column mappings
  - `METRIC_MAP`: Translates semantic metric names to actual database column names
  - Supports complex metric mappings across different split contexts

### Frontend Integration
- **GitHub Codespaces Detection**: Frontend automatically detects Codespaces environment and adjusts API URLs
- **Real-time Chat Interface**: Manages message state, loading indicators, and API communication
- **Environment URL Mapping**: Converts frontend port 5173 to backend port 8000 for Codespaces

## Environment Requirements

### Required Environment Variables (.env)
```
GCP_PROJECT_ID=tksm-dash-test-25
BIGQUERY_DATASET_ID=<dataset_name>
BIGQUERY_BATTING_STATS_TABLE_ID=fact_batting_stats_with_risp
BIGQUERY_PITCHING_STATS_TABLE_ID=fact_pitching_stats
GEMINI_API_KEY=<your_gemini_api_key>
GOOGLE_APPLICATION_CREDENTIALS=<path_to_service_account_json>
```

### API Endpoints
- Main endpoint: `POST /api/v1/qa/player-stats`
- Health check: `GET /health`
- Debug routes: `GET /debug/routes`

## Development Notes

### BigQuery Client
- Singleton pattern implementation in `bigquery_service.py`
- Hardcoded to GCP project `tksm-dash-test-25`
- Requires proper service account authentication

### Query Type System
- **season_batting/pitching**: League-wide season statistics
- **batting_splits**: Situational performance metrics (RISP, vs LHP/RHP, by inning, etc.)
- Each query type has distinct table schemas and metric mappings

### LLM Integration
- Dual Gemini API usage: query parsing + response generation
- Japanese language processing with English name normalization
- Structured JSON response formatting with retry logic