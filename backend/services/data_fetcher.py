# backend/services/data_fetcher.py

# pyrefly: ignore [missing-import]
import yfinance as yf
# pyrefly: ignore [missing-import]
from newsapi import NewsApiClient
# pyrefly: ignore [missing-import]
from fredapi import Fred
import pandas as pd
from datetime import datetime, timedelta
import logging
from .config import (
    NEWS_API_KEY, FRED_API_KEY,
    INDIAN_TICKER_SUFFIXES, US_MARKET_INDEX, INDIA_MARKET_INDEX,
)

newsapi = NewsApiClient(api_key=NEWS_API_KEY) if NEWS_API_KEY else None

fred = None
if FRED_API_KEY:
    try:
        fred = Fred(api_key=FRED_API_KEY)
    except Exception as e:
        logging.error(f"Failed to initialize FRED client: {e}")


# ─────────────────────────────────────────────
# Market Detection
# ─────────────────────────────────────────────

def detect_market(ticker: str) -> dict:
    """Detect whether a ticker belongs to the Indian or US market.

    Returns a dict with market, currency, exchange info.
    yfinance uses .NS for NSE and .BO for BSE.
    """
    ticker_upper = ticker.upper()

    if ticker_upper.endswith(".NS"):
        return {
            "market": "IN",
            "currency": "INR",
            "exchange": "NSE",
            "market_index": INDIA_MARKET_INDEX,
            "country": "India",
            "flag": "🇮🇳",
        }
    elif ticker_upper.endswith(".BO"):
        return {
            "market": "IN",
            "currency": "INR",
            "exchange": "BSE",
            "market_index": INDIA_MARKET_INDEX,
            "country": "India",
            "flag": "🇮🇳",
        }
    else:
        return {
            "market": "US",
            "currency": "USD",
            "exchange": "NYSE/NASDAQ",
            "market_index": US_MARKET_INDEX,
            "country": "United States",
            "flag": "🇺🇸",
        }


def is_indian_ticker(ticker: str) -> bool:
    """Check if the ticker belongs to the Indian market."""
    return ticker.upper().endswith(INDIAN_TICKER_SUFFIXES)


# ─────────────────────────────────────────────
# Yahoo Finance Data
# ─────────────────────────────────────────────

def get_yahoo_finance_data(ticker_symbol: str):
    """Fetches historical price data and company info from Yahoo Finance.

    Works for both US and Indian tickers (yfinance supports NSE/BSE natively).
    """
    logging.info(f"Fetching yfinance data for ticker: {ticker_symbol}")
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist_data = ticker.history(period="1y")
        if hist_data.empty:
            return None

        hist_data.index = hist_data.index.map(lambda x: x.strftime('%Y-%m-%d'))
        info = ticker.info

        # Detect exchange from yfinance info when available
        exchange = info.get("exchange", "")
        market_info = detect_market(ticker_symbol)

        # Refine exchange name from yfinance data
        if exchange:
            exchange_map = {
                "NSI": "NSE",
                "NSE": "NSE",
                "BOM": "BSE",
                "BSE": "BSE",
                "NMS": "NASDAQ",
                "NYQ": "NYSE",
                "NGM": "NASDAQ",
            }
            detected_exchange = exchange_map.get(exchange, market_info["exchange"])
        else:
            detected_exchange = market_info["exchange"]

        return {
            "historical_data": hist_data.to_dict(orient="index"),
            "info": {
                "longName": info.get("longName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "marketCap": info.get("marketCap"),
                "trailingPE": info.get("trailingPE"),
                "dividendYield": info.get("dividendYield"),
                "debtToEquity": info.get("debtToEquity"),
                "totalCashPerShare": info.get("totalCashPerShare"),
                "currency": info.get("currency", market_info["currency"]),
                "exchange": detected_exchange,
                "country": info.get("country", market_info["country"]),
            },
            "market_info": market_info,
        }
    except Exception as e:
        logging.error(f"yfinance error for {ticker_symbol}: {e}")
        return None


# ─────────────────────────────────────────────
# FRED / Macro Data
# ─────────────────────────────────────────────

def get_fred_data(series_id='DGS10'):
    """Fetches US Treasury rate data from FRED.

    For Indian market, this still provides useful global context.
    """
    if not fred:
        logging.warning("FRED API key not configured or initialization failed. Skipping FRED data fetch.")
        return None
    try:
        logging.info(f"Fetching FRED data for series: {series_id}")
        end_date = datetime.now()
        start_date = end_date - pd.DateOffset(years=1)
        series_data = fred.get_series(series_id, start_date=start_date, end_date=end_date)
        return series_data
    except Exception as e:
        logging.error(f"Could not fetch FRED data for {series_id}: {e}")
        return None


# ─────────────────────────────────────────────
# Market Sentiment
# ─────────────────────────────────────────────

def get_market_sentiment_data(market: str = "US"):
    """Fetches broad market sentiment using the relevant market index.

    US: S&P 500 (^GSPC)
    India: NIFTY 50 (^NSEI)
    """
    index_symbol = INDIA_MARKET_INDEX if market == "IN" else US_MARKET_INDEX
    index_name = "NIFTY 50" if market == "IN" else "S&P 500"

    try:
        logging.info(f"Fetching {index_name} data for market sentiment.")
        index_ticker = yf.Ticker(index_symbol)
        hist = index_ticker.history(period="4mo")

        if hist.empty or len(hist) < 2:
            logging.warning(f"Not enough {index_name} data.")
            return 0.0

        price_now = hist['Close'].iloc[-1]
        price_ago = hist['Close'].iloc[0]
        return ((price_now - price_ago) / price_ago) * 100

    except Exception as e:
        logging.error(f"Could not fetch market sentiment data from {index_name}: {e}")
        return 0.0


# ─────────────────────────────────────────────
# News Data
# ─────────────────────────────────────────────

def get_news_data(query: str, market: str = "US"):
    """Fetches news articles from NewsAPI.

    For Indian companies, appends 'India' to the search query
    for better relevance in results.
    """
    if not newsapi or not NEWS_API_KEY or NEWS_API_KEY == "YOUR_API_KEY":
        logging.warning("NewsAPI key not configured.")
        return None

    logging.info(f"Fetching news from NewsAPI for query: '{query}' (market: {market})")

    try:
        # For Indian companies, add context to improve relevance
        search_query = query
        if market == "IN":
            search_query = f"{query} India stock"

        from_date = (datetime.now() - timedelta(days=29)).strftime('%Y-%m-%d')

        all_articles = newsapi.get_everything(
            q=search_query,
            language='en',
            sort_by='relevancy',
            from_param=from_date,
            page_size=20,
        )

        return [
            {
                "source": article["source"]["name"],
                "title": article["title"],
                "url": article["url"],
                "publishedAt": article["publishedAt"],
                "content": article.get("content", ""),
            }
            for article in all_articles["articles"]
        ]

    except Exception as e:
        logging.error(f"NewsAPI error for query '{query}': {e}")
        return None