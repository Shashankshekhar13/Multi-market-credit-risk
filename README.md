# CredLens — Multi-Market Credit Risk Platform

> AI-powered credit risk analysis for **US** 🇺🇸 and **Indian** 🇮🇳 companies with real-time scoring, ML model tracking, and proactive alerts.

---

## Features

| Feature | Description |
|---------|-------------|
| 🌍 **Multi-Market** | Analyze US (NYSE/NASDAQ) and Indian (NSE/BSE) stocks |
| 🤖 **ML Scoring** | XGBoost risk model with Optuna tuning and SHAP explanations |
| 📊 **Real-time Data** | Yahoo Finance, NewsAPI, FRED macro indicators |
| 🧪 **MLflow Tracking** | Experiment tracking, model registry, auto-promotion |
| 🔐 **JWT Auth** | User accounts, watchlists, personalized alerts |
| 🔔 **Alert System** | Score drops, volatile zones, news spikes, recovery alerts |
| ⚡ **Redis Caching** | Sub-200ms cached responses |
| 📦 **ETL Pipeline** | Prefect-powered automated data collection |
| 🐳 **Docker Ready** | One-command deployment with Docker Compose |

---

## Quick Start

```bash
# Clone
cd Credit-Risk-Project

# Backend
python -m venv venv
venv\Scripts\activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 🚀

---

## Architecture

```
React Frontend ──► FastAPI Backend ──► Yahoo Finance / NewsAPI / FRED
                        │
              ┌─────────┼─────────┐
              ▼         ▼         ▼
          PostgreSQL   Redis    MLflow
```

### Supported Tickers

| Market | Examples | Suffix |
|--------|----------|--------|
| 🇺🇸 US | AAPL, MSFT, NVDA, TSLA, JPM | None |
| 🇮🇳 India | RELIANCE.NS, TCS.NS, INFY.BO | `.NS` (NSE) or `.BO` (BSE) |

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/score/{ticker}` | GET | Credit risk analysis |
| `/api/v1/companies` | GET | List tracked companies |
| `/api/v1/companies/search?q=` | GET | Search companies |
| `/api/v1/auth/register` | POST | Create account |
| `/api/v1/auth/login` | POST | Get JWT token |
| `/api/v1/alerts` | GET/POST | Manage alert rules |
| `/api/v1/ratings/{ticker}` | GET | Credit agency rating |

Full API docs at http://localhost:8000/docs

---

## Tech Stack

- **Frontend**: React 18, Vite 5, Plotly.js
- **Backend**: FastAPI, SQLAlchemy, asyncpg
- **ML**: XGBoost, Optuna, SHAP, MLflow
- **Infrastructure**: PostgreSQL, Redis, Prefect, Docker

---

## Documentation

- [API Reference](docs/API.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)

---

## License

MIT
