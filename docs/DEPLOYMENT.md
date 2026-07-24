# Deployment Guide

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (optional, for full infrastructure)

---

## Quick Start (Development)

### 1. Clone and Setup

```bash
git clone https://github.com/HarshitK2814/Credit-Risk-Project.git
cd Credit-Risk-Project
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac
```

### 2. Install Dependencies

```bash
# Backend
pip install -r backend/requirements.txt

# Frontend
cd frontend
npm install
cd ..
```

### 3. Environment Variables

Create a `.env` file in the project root:

```env
# Required
NEWS_API_KEY=your_newsapi_key
FRED_API_KEY=your_fred_api_key

# Optional (defaults work for development)
DATABASE_URL=postgresql+asyncpg://credlens:credlens@localhost:5432/credlens
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-super-secret-key
MLFLOW_TRACKING_URI=sqlite:///backend/mlflow.db

# Optional (for email alerts)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
```

### 4. Run

```bash
# Terminal 1 — Backend
venv\Scripts\activate
uvicorn backend.main:app --reload

# Terminal 2 — Frontend
cd frontend
npm run dev
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Docker Deployment

### Full Stack

```bash
docker-compose up -d
```

This starts:
- PostgreSQL 16 on port 5432
- Redis 7 on port 6379
- FastAPI backend on port 8000
- React frontend on port 5173

### Infrastructure Only

```bash
docker-compose up -d postgres redis
```

Then run backend/frontend locally while using Docker for databases.

---

## Production Checklist

- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Set `DATABASE_URL` to production PostgreSQL
- [ ] Set `REDIS_URL` to production Redis
- [ ] Configure SMTP for email alerts
- [ ] Run Alembic migrations: `alembic upgrade head`
- [ ] Set up MLflow tracking server
- [ ] Register Prefect deployments: `python -m backend.etl.schedule`
- [ ] Start Prefect agent: `prefect agent start -q default`
- [ ] Configure CORS origins (replace `*` with frontend URL)
- [ ] Enable HTTPS

---

## Running Tests

```bash
venv\Scripts\activate
pip install pytest
pytest tests/ -v
```

---

## ETL Commands

```bash
# Single ticker
python -m backend.etl.flows AAPL
python -m backend.etl.flows RELIANCE.NS

# Batch
python -m backend.etl.flows us      # All US tickers
python -m backend.etl.flows india    # All Indian tickers
python -m backend.etl.flows all      # Everything
```

---

## MLflow Dashboard

```bash
mlflow ui --backend-store-uri sqlite:///backend/mlflow.db
# Open http://localhost:5000
```
