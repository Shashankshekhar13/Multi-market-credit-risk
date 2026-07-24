# backend/etl/flows.py
"""Prefect flow definitions for automated data collection and scoring."""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from prefect import flow
except ImportError:
    def flow(*args, **kwargs):
        def decorator(fn):
            return fn
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator
    logger.warning("Prefect not installed. Flows will run as regular functions.")

from backend.etl.tasks import (
    fetch_stock_data, fetch_news_data, fetch_market_sentiment,
    fetch_macro_data, compute_features, compute_score,
    persist_company_sync, persist_score_sync, train_model,
)
from backend.services.data_fetcher import detect_market


# ─── Default Ticker Lists ───

US_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM",
    "V", "JNJ", "WMT", "PG", "MA", "UNH", "HD", "DIS", "NFLX", "BA",
    "SMCI", "BLK",
]

INDIA_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS",
    "LT.NS", "WIPRO.NS", "TATAMOTORS.NS", "TATASTEEL.NS", "MARUTI.NS",
    "BAJFINANCE.NS", "HCLTECH.NS", "SUNPHARMA.NS", "AXISBANK.NS", "ADANIENT.NS",
]


# ─── Single Ticker Flow ───

@flow(name="analyze_ticker", log_prints=True)
def analyze_ticker_flow(ticker: str):
    """Complete analysis pipeline for a single ticker."""
    market_info = detect_market(ticker)
    market = market_info["market"]

    print(f"{'='*50}")
    print(f"Analyzing: {ticker} | Market: {market} | {market_info['flag']}")
    print(f"{'='*50}")

    # Step 1: Fetch data
    yf_data = fetch_stock_data(ticker)
    if not yf_data:
        print(f"❌ Failed to fetch data for {ticker}. Skipping.")
        return None

    company_name = yf_data["info"].get("longName", ticker)
    market_sentiment = fetch_market_sentiment(market)
    fred_data = fetch_macro_data()
    news_data = fetch_news_data(company_name, market)

    # Step 2: Persist company info
    persist_company_sync(ticker, yf_data, market_info)

    # Step 3: Engineer features
    features = compute_features(yf_data, market_sentiment, fred_data, news_data or [])

    # Step 4: Compute score
    result = compute_score(ticker, yf_data, market_sentiment, fred_data, news_data or [])
    persist_score_sync(ticker, result)

    # Step 5: Train model (if enough data)
    if features is not None and not features.empty:
        train_model(features, ticker)

    score = result.get("stability_score", "N/A")
    print(f"✅ {ticker}: Score = {score} | Type = {result.get('assessment_type', 'Unknown')}")

    return {
        "ticker": ticker,
        "score": score,
        "assessment_type": result.get("assessment_type"),
        "company_name": company_name,
    }


# ─── Batch Flows ───

@flow(name="daily_us_collection", log_prints=True)
def daily_us_collection_flow(tickers: list = None):
    """Daily data collection for all US tickers."""
    tickers = tickers or US_TICKERS
    print(f"\n🇺🇸 Starting US Market Daily Collection — {len(tickers)} tickers")
    print(f"Time: {datetime.now().isoformat()}")

    results = []
    for ticker in tickers:
        try:
            result = analyze_ticker_flow(ticker)
            if result:
                results.append(result)
        except Exception as e:
            print(f"❌ Error processing {ticker}: {e}")

    print(f"\n{'='*50}")
    print(f"🇺🇸 US Collection Complete: {len(results)}/{len(tickers)} successful")
    print(f"{'='*50}")
    return results


@flow(name="daily_india_collection", log_prints=True)
def daily_india_collection_flow(tickers: list = None):
    """Daily data collection for all Indian tickers."""
    tickers = tickers or INDIA_TICKERS
    print(f"\n🇮🇳 Starting India Market Daily Collection — {len(tickers)} tickers")
    print(f"Time: {datetime.now().isoformat()}")

    results = []
    for ticker in tickers:
        try:
            result = analyze_ticker_flow(ticker)
            if result:
                results.append(result)
        except Exception as e:
            print(f"❌ Error processing {ticker}: {e}")

    print(f"\n{'='*50}")
    print(f"🇮🇳 India Collection Complete: {len(results)}/{len(tickers)} successful")
    print(f"{'='*50}")
    return results


@flow(name="daily_full_collection", log_prints=True)
def daily_full_collection_flow():
    """Complete daily data collection for all markets."""
    print(f"\n🌍 Starting Full Daily Collection")
    print(f"Time: {datetime.now().isoformat()}")
    print(f"US tickers: {len(US_TICKERS)} | India tickers: {len(INDIA_TICKERS)}")

    us_results = daily_us_collection_flow()
    india_results = daily_india_collection_flow()

    total = len(us_results) + len(india_results)
    expected = len(US_TICKERS) + len(INDIA_TICKERS)

    print(f"\n{'='*60}")
    print(f"🌍 Full Collection Complete: {total}/{expected} successful")
    print(f"{'='*60}")

    return {"us": us_results, "india": india_results, "total": total}


# ─── CLI Entry Point ───

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "us":
            daily_us_collection_flow()
        elif command == "india":
            daily_india_collection_flow()
        elif command == "all":
            daily_full_collection_flow()
        elif command.upper() == command or "." in command:
            # Treat as a ticker
            analyze_ticker_flow(command)
        else:
            print(f"Usage: python -m backend.etl.flows [us|india|all|TICKER]")
    else:
        print("Usage: python -m backend.etl.flows [us|india|all|TICKER]")
        print("Examples:")
        print("  python -m backend.etl.flows AAPL         # Single US ticker")
        print("  python -m backend.etl.flows RELIANCE.NS   # Single Indian ticker")
        print("  python -m backend.etl.flows us             # All US tickers")
        print("  python -m backend.etl.flows india           # All Indian tickers")
        print("  python -m backend.etl.flows all             # All tickers")
