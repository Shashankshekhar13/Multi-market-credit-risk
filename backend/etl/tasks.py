# backend/etl/tasks.py
"""Individual Prefect tasks for data collection, transformation, and loading."""

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from prefect import task
except ImportError:
    # Graceful fallback: if Prefect is not installed, tasks are regular functions
    def task(*args, **kwargs):
        def decorator(fn):
            return fn
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator
    logger.warning("Prefect not installed. ETL tasks will run as regular functions.")


# ─── Data Fetching Tasks ───

@task(name="fetch_stock_data", retries=2, retry_delay_seconds=30)
def fetch_stock_data(ticker: str) -> Optional[dict]:
    """Fetch historical price data and company info from Yahoo Finance."""
    from backend.services.data_fetcher import get_yahoo_finance_data
    logger.info(f"[ETL] Fetching stock data for {ticker}")
    data = get_yahoo_finance_data(ticker)
    if data:
        logger.info(f"[ETL] Stock data fetched for {ticker}: {len(data.get('historical_data', {}))} days")
    else:
        logger.warning(f"[ETL] Failed to fetch stock data for {ticker}")
    return data


@task(name="fetch_news_data", retries=2, retry_delay_seconds=30)
def fetch_news_data(company_name: str, market: str = "US") -> Optional[list]:
    """Fetch recent news articles from NewsAPI."""
    from backend.services.data_fetcher import get_news_data
    logger.info(f"[ETL] Fetching news for {company_name} (market: {market})")
    return get_news_data(query=company_name, market=market)


@task(name="fetch_market_sentiment")
def fetch_market_sentiment(market: str = "US") -> float:
    """Fetch broad market sentiment data."""
    from backend.services.data_fetcher import get_market_sentiment_data
    logger.info(f"[ETL] Fetching market sentiment for {market}")
    return get_market_sentiment_data(market=market)


@task(name="fetch_macro_data")
def fetch_macro_data(series_id: str = "DGS10"):
    """Fetch macroeconomic data from FRED."""
    from backend.services.data_fetcher import get_fred_data
    import pandas as pd
    logger.info(f"[ETL] Fetching FRED data for {series_id}")
    data = get_fred_data(series_id)
    return data if data is not None else pd.Series(dtype='float64')


# ─── Feature Engineering Task ───

@task(name="engineer_features")
def compute_features(yf_data: dict, market_sentiment: float, fred_data, news_data: list):
    """Engineer all features from raw data."""
    from backend.services.scoring_engine import engineer_features
    logger.info("[ETL] Engineering features...")
    return engineer_features(yf_data, market_sentiment, fred_data, news_data)


# ─── Scoring Task ───

@task(name="compute_score")
def compute_score(ticker: str, yf_data: dict, market_sentiment: float, fred_data, news_data: list) -> dict:
    """Run the full scoring pipeline for a ticker."""
    from backend.services.scoring_engine import get_score_and_explanation
    logger.info(f"[ETL] Computing score for {ticker}")
    return get_score_and_explanation(
        ticker=ticker, yf_data=yf_data,
        market_sentiment=market_sentiment,
        fred_data=fred_data,
        news_data=news_data or []
    )


# ─── Database Persistence Tasks ───

@task(name="persist_company")
def persist_company_sync(ticker: str, yf_data: dict, market_info: dict):
    """Persist company data to the database (sync version for Prefect tasks)."""
    logger.info(f"[ETL] Persisting company data for {ticker}")
    # This would use a sync DB session in Prefect context
    # For now, log intent — actual persistence happens via the API
    info = yf_data.get("info", {})
    logger.info(f"[ETL] Company: {info.get('longName', ticker)} | Market: {market_info['market']} | Exchange: {market_info['exchange']}")


@task(name="persist_score")
def persist_score_sync(ticker: str, result: dict):
    """Persist score result to the database (sync version for Prefect tasks)."""
    score = result.get("stability_score", "N/A")
    assessment = result.get("assessment_type", "Unknown")
    logger.info(f"[ETL] Score for {ticker}: {score} ({assessment})")


# ─── Model Training Task ───

@task(name="train_model", retries=1)
def train_model(features, ticker: str):
    """Train/retrain the ML model for a ticker."""
    from backend.services.scoring_engine import train_technical_model
    logger.info(f"[ETL] Training model for {ticker}")
    if not features.empty:
        model = train_technical_model(features.copy(), ticker)
        if model:
            logger.info(f"[ETL] Model trained successfully for {ticker}")
        else:
            logger.warning(f"[ETL] Model training returned None for {ticker}")
    else:
        logger.warning(f"[ETL] Cannot train model — empty features for {ticker}")
