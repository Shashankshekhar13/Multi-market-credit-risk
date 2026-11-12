# backend/main.py
"""CredLens API v2.0 — Application entry point with router-based architecture."""

# pyrefly: ignore [missing-import]
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from backend.routers import scores, companies, auth, alerts
from backend.services.database import init_db, close_db, check_db_health
from backend.services.cache import close_redis

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ─── App Lifecycle ───

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info("Starting CredLens API v2.0...")
    try:
        await init_db()
        logger.info("Database initialized.")
    except Exception as e:
        logger.warning(f"Database unavailable: {e}. Running in stateless mode.")

    yield

    # Shutdown
    logger.info("Shutting down CredLens API...")
    await close_db()
    await close_redis()
    logger.info("Shutdown complete.")


# ─── App Factory ───

app = FastAPI(
    title="CredLens AI API",
    description="Multi-market credit risk analysis platform supporting US and Indian companies.",
    version="2.0.0",
    lifespan=lifespan,
)

import os

default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://multi-market-credit-risk.vercel.app",
    "https://credlens-api.onrender.com",
    "https://credit-risk-hackathon-production.up.railway.app",
]

allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
if allowed_origins_env:
    for origin in allowed_origins_env.split(","):
        clean_origin = origin.strip()
        if clean_origin and clean_origin not in default_origins:
            default_origins.append(clean_origin)

is_wildcard = "*" in default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if is_wildcard else default_origins,
    allow_origin_regex=None if is_wildcard else r"https://.*\.vercel\.app",
    allow_credentials=not is_wildcard,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Register Routers ───

app.include_router(scores.router)
app.include_router(companies.router)
app.include_router(auth.router)
app.include_router(alerts.router)


# ─── Health Check ───

@app.get("/")
async def read_root():
    """Root endpoint for health checks."""
    db_healthy = False
    try:
        db_healthy = await check_db_health()
    except Exception:
        pass

    mlflow_available = False
    try:
        from backend.ml.mlflow_config import is_mlflow_available
        mlflow_available = is_mlflow_available()
    except Exception:
        pass

    auth_available = False
    try:
        from backend.services.auth import is_auth_available
        auth_available = is_auth_available()
    except Exception:
        pass

    return {
        "message": "CredLens API v2.0 is running.",
        "supported_markets": ["US", "IN"],
        "database_connected": db_healthy,
        "mlflow_enabled": mlflow_available,
        "auth_enabled": auth_available,
        "version": "2.0.0",
    }

