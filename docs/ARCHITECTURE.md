# CredLens Architecture

## System Overview

CredLens is a multi-market credit risk analysis platform that combines real-time financial data, ML-powered risk scoring, and news sentiment analysis.

```
┌──────────────────────────────────────────────────────────────────┐
│                        Frontend (React + Vite)                   │
│  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ Dashboard │ │ Auth Pages│ │ Alerts   │ │ Market Toggle    │  │
│  │ (Charts)  │ │ Login/Reg │ │ Manager  │ │ 🇺🇸 US | 🇮🇳 India │  │
│  └──────────┘ └───────────┘ └──────────┘ └──────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                              │ HTTP/REST
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI v2.0)                        │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Routers: /scores  /companies  /auth  /alerts               │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ Scoring  │  │ Data     │  │ Auth     │  │ Alert    │        │
│  │ Engine   │  │ Fetcher  │  │ Service  │  │ Service  │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│       │              │                                           │
│  ┌──────────┐  ┌──────────┐                                    │
│  │ ML/      │  │ Cache    │                                    │
│  │ MLflow   │  │ (Redis)  │                                    │
│  └──────────┘  └──────────┘                                    │
└──────────────────────────────────────────────────────────────────┘
        │              │              │
        ▼              ▼              ▼
   ┌─────────┐   ┌─────────┐   ┌──────────────┐
   │ MLflow  │   │ Redis   │   │ PostgreSQL   │
   │ (SQLite)│   │ Cache   │   │ (Async)      │
   └─────────┘   └─────────┘   └──────────────┘
```

## Data Flow

### Score Request Pipeline

```
1. Frontend sends GET /api/v1/score/{ticker}
2. Backend checks Redis cache (TTL: 15 min)
   └─ Cache HIT → return immediately (<50ms)
3. Backend checks PostgreSQL scores table
   └─ DB HIT (< 1 hour old) → return from DB (<200ms)
4. Backend fetches live data:
   ├─ Yahoo Finance (price + company info)
   ├─ FRED (US treasury rate)
   ├─ Market Index (S&P 500 or NIFTY 50)
   └─ NewsAPI (recent articles)
5. Scoring Engine:
   ├─ Engineer 17 features
   ├─ Load model (MLflow Registry → joblib → train new)
   ├─ Compute risk probability + SHAP explanations
   └─ Calculate stability score
6. Persist results:
   ├─ Cache in Redis
   ├─ Store in PostgreSQL
   └─ Log to MLflow
7. Return response (<5s for live fetch)
```

### Market Detection

```
Ticker input → detect_market()
├─ Ends with .NS → Indian (NSE)
├─ Ends with .BO → Indian (BSE)
└─ Otherwise    → US (NYSE/NASDAQ)
```

## Directory Structure

```
Credit-Risk-Project/
├── backend/
│   ├── main.py                 # FastAPI app factory + lifespan
│   ├── models.py               # SQLAlchemy ORM models
│   ├── schemas.py              # Pydantic response schemas
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── routers/
│   │   ├── scores.py           # Score analysis endpoints
│   │   ├── companies.py        # Company list/search
│   │   ├── auth.py             # JWT auth + watchlist
│   │   └── alerts.py           # Alert rules + history
│   ├── services/
│   │   ├── config.py           # All configuration
│   │   ├── data_fetcher.py     # Yahoo, FRED, NewsAPI
│   │   ├── scoring_engine.py   # ML scoring + SHAP
│   │   ├── database.py         # Async DB connection
│   │   ├── cache.py            # Redis caching
│   │   ├── auth.py             # JWT + bcrypt
│   │   └── alert_service.py    # Alert conditions
│   ├── ml/
│   │   ├── mlflow_config.py    # MLflow setup
│   │   ├── tracker.py          # Experiment tracking
│   │   └── registry.py         # Model registry
│   ├── etl/
│   │   ├── tasks.py            # Prefect tasks
│   │   ├── flows.py            # Data collection flows
│   │   └── schedule.py         # Cron schedules
│   └── ml_models/              # Saved model files
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Main app + auth flow
│   │   ├── App.css             # All styles
│   │   ├── components/
│   │   │   ├── Sidebar.jsx     # Market toggle + ticker input
│   │   │   ├── MetricCard.jsx  # Score/metric display
│   │   │   ├── ScoreStatus.jsx # Score status banner
│   │   │   ├── DriversChart.jsx # SHAP explanations
│   │   │   ├── StockChart.jsx  # Price history chart
│   │   │   ├── NewsSection.jsx # News articles
│   │   │   ├── MarketBadge.jsx # 🇺🇸/🇮🇳 badge
│   │   │   ├── AuthProvider.jsx # JWT context
│   │   │   ├── AlertManager.jsx # Alert rules panel
│   │   │   ├── NotificationBell.jsx
│   │   │   └── Footer.jsx
│   │   └── pages/
│   │       ├── Login.jsx
│   │       └── Register.jsx
│   └── Dockerfile
├── tests/
│   ├── conftest.py
│   ├── test_data_fetcher.py
│   ├── test_scoring.py
│   ├── test_alerts.py
│   └── test_config.py
├── docs/
│   ├── API.md
│   └── ARCHITECTURE.md
├── docker-compose.yml
└── README.md
```

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Frontend | React 18 + Vite 5 |
| Backend | FastAPI + Uvicorn |
| Database | PostgreSQL 16 (async via asyncpg) |
| Cache | Redis 7 |
| ML Framework | XGBoost + Optuna + SHAP |
| MLOps | MLflow 3.x |
| ETL | Prefect 3.x |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Charts | Plotly.js |
| Containerization | Docker + Docker Compose |
