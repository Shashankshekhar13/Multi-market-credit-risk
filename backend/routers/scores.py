# backend/routers/scores.py
"""Score-related API endpoints with caching and database persistence."""

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, BackgroundTasks, Depends
# pyrefly: ignore [missing-import]
from fastapi.responses import JSONResponse
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession
# pyrefly: ignore [missing-import]
from sqlalchemy import select, desc
from datetime import datetime, timezone, timedelta
import logging
import pandas as pd

from backend.services.data_fetcher import (
    get_yahoo_finance_data, get_market_sentiment_data,
    get_news_data, get_fred_data, detect_market,
)
from backend.services.scoring_engine import (
    get_score_and_explanation, train_technical_model, engineer_features,
)
from backend.services.config import US_AGENCY_RATINGS, INDIAN_AGENCY_RATINGS
from backend.services.cache import cache_get, cache_set
from backend.services.database import get_db
from backend.models import Company, Score

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["scores"])


def get_agency_rating(ticker: str, market: str) -> str:
    """Get the credit rating for a ticker from the appropriate ratings map."""
    ticker_upper = ticker.upper()
    if market == "IN":
        return INDIAN_AGENCY_RATINGS.get(ticker_upper, "N/A")
    return US_AGENCY_RATINGS.get(ticker_upper, "N/A")


def retrain_model_background(ticker: str):
    """Handles the background task for retraining the ML model."""
    logger.info(f"[BACKGROUND] Starting retraining process for {ticker}...")
    try:
        yf_data = get_yahoo_finance_data(ticker)
        if not yf_data:
            logger.error(f"[BACKGROUND] Failed to fetch yfinance data for {ticker}. Aborting.")
            return

        market_info = yf_data.get("market_info", detect_market(ticker))
        market = market_info["market"]

        company_name = yf_data["info"].get("longName", ticker)
        market_sentiment = get_market_sentiment_data(market=market)
        fred_data = get_fred_data()
        fred_data = fred_data if fred_data is not None else pd.Series(dtype='float64')
        news_data = get_news_data(query=company_name, market=market)

        all_features = engineer_features(yf_data, market_sentiment, fred_data, news_data or [])

        if not all_features.empty:
            train_technical_model(all_features, ticker)
            logger.info(f"[BACKGROUND] Retraining for {ticker} completed successfully.")
        else:
            logger.warning(f"[BACKGROUND] Not enough data to retrain model for {ticker}.")
    except Exception as e:
        logger.error(f"[BACKGROUND] An error occurred during retraining for {ticker}: {e}")


from backend.services.database import get_db, async_session, _db_available

async def _persist_score(ticker: str, market_info: dict,
                         company_info: dict, result: dict):
    """Persist score and company data to the database using an independent session."""
    if not _db_available or async_session is None:
        return
    try:
        async with async_session() as db:
            # Upsert company
            stmt = select(Company).where(Company.ticker == ticker.upper())
            existing = (await db.execute(stmt)).scalar_one_or_none()

            if existing:
                existing.name = company_info.get("longName", ticker)
                existing.market_cap = company_info.get("marketCap")
                existing.sector = company_info.get("sector")
                existing.industry = company_info.get("industry")
                existing.info_json = company_info
                existing.last_updated = datetime.now(timezone.utc).replace(tzinfo=None)
            else:
                company = Company(
                    ticker=ticker.upper(),
                    name=company_info.get("longName", ticker),
                    market=market_info["market"],
                    exchange=company_info.get("exchange", market_info["exchange"]),
                    currency=market_info["currency"],
                    sector=company_info.get("sector"),
                    industry=company_info.get("industry"),
                    market_cap=company_info.get("marketCap"),
                    info_json=company_info,
                )
                db.add(company)

            # Insert score record
            score_record = Score(
                ticker=ticker.upper(),
                stability_score=result.get("stability_score") if isinstance(result.get("stability_score"), (int, float)) else None,
                fundamental_score=result.get("fundamental_score"),
                technical_score=result.get("technical_score"),
                assessment_type=result.get("assessment_type", "Unknown"),
                latest_sentiment=result.get("latest_sentiment", 0.0),
                explanation_json=result.get("explanation"),
            )
            db.add(score_record)

            await db.commit()
            logger.info(f"Persisted score for {ticker.upper()} to database.")
    except Exception as e:
        logger.warning(f"Failed to persist score for {ticker}: {e}")


import asyncio

@router.get("/score/{ticker}")
async def get_credit_score(
    ticker: str,
    db: AsyncSession = Depends(get_db),
):
    """Analyzes a stock ticker and returns its creditworthiness score.

    Supports both US tickers (e.g., AAPL) and Indian tickers (e.g., RELIANCE.NS, TCS.BO).

    Flow:
    1. Check Redis cache → return if fresh
    2. Fetch live data (offloaded to thread) → compute score (offloaded to thread)
    3. Persist to DB + cache in Redis
    """
    logger.info(f"Received request for ticker: {ticker.upper()}")
    market_info = detect_market(ticker)
    market = market_info["market"]

    # Step 1: Check cache
    cached = await cache_get("score", ticker)
    if cached:
        logger.info(f"Returning cached score for {ticker.upper()}")
        return cached

    # Step 2: Fetch live data asynchronously via thread worker pool in parallel
    try:
        yf_task = asyncio.to_thread(get_yahoo_finance_data, ticker)
        sentiment_task = asyncio.to_thread(get_market_sentiment_data, market)
        fred_task = asyncio.to_thread(get_fred_data)

        yf_data, market_sentiment, fred_data = await asyncio.gather(
            yf_task, sentiment_task, fred_task, return_exceptions=True
        )

        if isinstance(yf_data, Exception) or not yf_data or not yf_data.get("info") or yf_data.get("historical_data") is None:
            logger.warning(f"Invalid ticker or not enough data returned for {ticker}.")
            return JSONResponse(status_code=404, content={"error": True, "type": "INVALID_TICKER"})

        market_sentiment = 0.0 if isinstance(market_sentiment, Exception) or market_sentiment is None else market_sentiment
        fred_data = pd.Series(dtype='float64') if isinstance(fred_data, Exception) or fred_data is None else fred_data

        company_info = yf_data.get("info", {})
        company_name = company_info.get("longName", ticker)

        try:
            news_data = await asyncio.to_thread(get_news_data, company_name, market)
        except Exception:
            news_data = []

    except Exception as e:
        logger.error(f"Data fetching failed: {e}")
        return JSONResponse(status_code=500, content={"error": True, "detail": "Failed to fetch data."})

    # Compute score offloaded to thread pool to keep API event loop non-blocking
    result = await asyncio.to_thread(
        get_score_and_explanation,
        ticker, yf_data, market_sentiment, fred_data, news_data or []
    )

    # Fetch sector average stability score based on latest score per company in sector
    sector = company_info.get("sector")
    sector_average = 68.0
    if sector:
        try:
            # Query latest score per company in the sector to avoid historical row clutter
            subq = select(
                Score.ticker,
                Score.stability_score,
                Score.date
            ).order_by(Score.ticker, desc(Score.date)).subquery()

            stmt = select(subq.c.stability_score).join(
                Company, Company.ticker == subq.c.ticker
            ).where(Company.sector == sector)

            sector_scores = (await db.execute(stmt)).scalars().all()
            valid_scores = [s for s in sector_scores if s is not None]
            if valid_scores:
                sector_average = round(sum(valid_scores) / len(valid_scores), 1)
        except Exception as se:
            logger.warning(f"Failed to calculate sector average for {sector}: {se}")

    # Load model registry metadata from MLflow safely
    model_metadata = None
    try:
        from backend.ml.registry import get_production_run_metadata
        model_metadata = await asyncio.to_thread(get_production_run_metadata, ticker)
    except Exception:
        model_metadata = None

    # Build response
    response = {
        "ticker": ticker.upper(),
        "company_name": company_name,
        "market": market_info["market"],
        "currency": market_info["currency"],
        "exchange": company_info.get("exchange", market_info["exchange"]),
        "country": market_info["country"],
        "flag": market_info["flag"],
        "agency_rating": get_agency_rating(ticker, market),
        "company_info": company_info,
        "score_result": result,
        "stock_history": yf_data.get("historical_data"),
        "recent_news_for_context": news_data[:5] if news_data else [],
        "model_metadata": model_metadata,
        "sector_average": sector_average,
        "rating_last_updated": "per internal registry",
    }

    # Sanitize NaN/Inf values for 100% strict JSON compliance
    def _sanitize_nans(obj):
        import math
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        elif isinstance(obj, dict):
            return {str(k): _sanitize_nans(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_sanitize_nans(v) for v in obj]
        return obj

    response = _sanitize_nans(response)

    # Step 3: Cache + non-blocking background persistence
    await cache_set("score", ticker, response)
    asyncio.create_task(_persist_score(ticker, market_info, company_info, result))

    return response


@router.get("/ratings/{ticker}")
async def get_rating(ticker: str):
    """Returns the credit agency rating for a ticker."""
    market_info = detect_market(ticker)
    rating = get_agency_rating(ticker, market_info["market"])
    return {
        "ticker": ticker.upper(),
        "market": market_info["market"],
        "rating": rating,
        "agency": "CRISIL/ICRA" if market_info["market"] == "IN" else "S&P",
    }
