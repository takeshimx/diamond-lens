# Diamond Lens - MLB Stats Assistant 🔮⚾

An AI-powered analytics interface for exploring Major League Baseball statistics through natural language queries and advanced custom analytics. Built with React, FastAPI, and Google Cloud BigQuery.

## 🌟 Features

### Core Modes
- **💬 Chat Mode**: Natural language queries in Japanese with AI-powered responses
- **⚡ Quick Questions**: Pre-defined common baseball queries for instant results
- **⚙️ Custom Query Builder**: Advanced analytics with custom situational filters

### Analytics Capabilities
- **Batting Statistics**: Season stats, splits, and advanced Statcast metrics
- **Pitching Statistics**: ERA, WHIP, strikeout rates, and advanced analytics
- **Situational Splits**: RISP performance, bases loaded, custom game situations
- **Career Analytics**: Multi-season trend analysis and career aggregation
- **Visual Charts**: YoY trend charts and KPI summary cards
- **Advanced Filters**: Inning-specific, count-specific, pitcher matchup analysis

### Technical Features
- **AI-Powered Processing**: Uses Gemini 2.5 Flash for query parsing and response generation
- **Real-time Interface**: Interactive experience with loading states and live updates
- **Case-insensitive Search**: Flexible player name matching
- **Dark Theme UI**: Modern, responsive interface optimized for extended use
- **Secure Access**: Password-protected interface for authorized users

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

#### Google Cloud Run
The project includes `cloudbuild.yaml` for automated deployment to Google Cloud Run.

## 📡 API Documentation

### Main Endpoint
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

#### Additional Endpoints
- **GET** `/health` - Health check endpoint
- **GET** `/debug/routes` - Debug route listing
- **GET** `/test` - Backend connectivity test
- **POST** `/test-post` - POST endpoint test

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
│   │   └── config/          # Configuration and mappings
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Backend container
├── CLAUDE.md                # Development guidance
├── cloudbuild.yaml          # GCP deployment config
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