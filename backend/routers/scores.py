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


async def _persist_score(db: AsyncSession, ticker: str, market_info: dict,
                         company_info: dict, result: dict):
    """Persist score and company data to the database (best-effort)."""
    try:
        # Upsert company
        stmt = select(Company).where(Company.ticker == ticker.upper())
        existing = (await db.execute(stmt)).scalar_one_or_none()

        if existing:
            existing.name = company_info.get("longName", ticker)
            existing.market_cap = company_info.get("marketCap")
            existing.sector = company_info.get("sector")
            existing.industry = company_info.get("industry")
            existing.info_json = company_info
            existing.last_updated = datetime.now(timezone.utc)
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
        await db.rollback()
        logger.warning(f"Failed to persist score for {ticker}: {e}")


@router.get("/score/{ticker}")
async def get_credit_score(
    ticker: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Analyzes a stock ticker and returns its creditworthiness score.

    Supports both US tickers (e.g., AAPL) and Indian tickers (e.g., RELIANCE.NS, TCS.BO).

    Flow:
    1. Check Redis cache → return if fresh
    2. Fetch live data → compute score
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

    # Step 2: Fetch live data
    try:
        yf_data = get_yahoo_finance_data(ticker)

        if not yf_data or not yf_data.get("info") or yf_data.get("historical_data") is None:
            logger.warning(f"Invalid ticker or not enough data returned for {ticker}.")
            return JSONResponse(status_code=404, content={"error": True, "type": "INVALID_TICKER"})

        company_info = yf_data.get("info", {})
        company_name = company_info.get("longName", ticker)
        market_sentiment = get_market_sentiment_data(market=market)
        fred_data = get_fred_data()
        fred_data = fred_data if fred_data is not None else pd.Series(dtype='float64')
        news_data = get_news_data(query=company_name, market=market)

    except Exception as e:
        logger.error(f"Data fetching failed: {e}")
        return JSONResponse(status_code=500, content={"error": True, "detail": "Failed to fetch data."})

    result = get_score_and_explanation(
        ticker=ticker, yf_data=yf_data,
        market_sentiment=market_sentiment,
        fred_data=fred_data,
        news_data=news_data or []
    )

    # Fetch sector average stability score from database (live peer statistics)
    sector = company_info.get("sector")
    sector_average = 68.0
    if sector:
        try:
            stmt = select(Score.stability_score).join(Company, Company.ticker == Score.ticker).where(Company.sector == sector)
            sector_scores = (await db.execute(stmt)).scalars().all()
            valid_scores = [s for s in sector_scores if s is not None]
            if valid_scores:
                sector_average = round(sum(valid_scores) / len(valid_scores), 1)
        except Exception as se:
            logger.warning(f"Failed to calculate sector average for {sector}: {se}")

    # Load model registry metadata from MLflow
    from backend.ml.registry import get_production_run_metadata
    model_metadata = get_production_run_metadata(ticker)

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
        "rating_last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }

    # Step 3: Cache + persist
    await cache_set("score", ticker, response)
    await _persist_score(db, ticker, market_info, company_info, result)

    if "error" not in result and result.get('assessment_type') != 'Heuristic':
        background_tasks.add_task(retrain_model_background, ticker)
        logger.info(f"Scheduled background retraining for {ticker}.")

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
