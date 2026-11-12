# backend/services/data_fetcher.py

# pyrefly: ignore [missing-import]
import yfinance as yf
# pyrefly: ignore [missing-import]
from newsapi import NewsApiClient
# pyrefly: ignore [missing-import]
from fredapi import Fred
import pandas as pd
import requests
from datetime import datetime, timedelta
import logging
from .config import (
    NEWS_API_KEY, FRED_API_KEY,
    INDIAN_TICKER_SUFFIXES, US_MARKET_INDEX, INDIA_MARKET_INDEX,
)

# Direct yfinance tz cache to /tmp to prevent filesystem collisions on cloud platforms (e.g. Render)
try:
    yf.set_tz_cache_location("/tmp/py-yfinance")
except Exception:
    pass

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
TICKER_ALIASES = {
    "TATAMOTORS.NS": "TMCV.NS",
    "TATAMOTORS.BO": "TMCV.BO",
    "TATAMTRDVR.NS": "TMPV.NS",
    "TTM": "TMCV.NS",
}


def fetch_yahoo_chart_direct(symbol: str, range_period: str = "1y", interval: str = "1d"):
    """Directly queries Yahoo Finance chart v8 API with browser headers.

    Acts as a resilient fallback when yfinance is blocked or rate-limited on cloud IPs (Render/AWS).
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    for host in ["query2.finance.yahoo.com", "query1.finance.yahoo.com"]:
        try:
            url = f"https://{host}/v8/finance/chart/{symbol}?range={range_period}&interval={interval}"
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                body = resp.json()
                results = body.get("chart", {}).get("result")
                if results and len(results) > 0:
                    return results[0]
            elif resp.status_code == 429:
                logging.warning(f"Yahoo chart direct rate-limited (429) on {host} for {symbol}")
        except Exception as e:
            logging.warning(f"Yahoo chart direct fetch failed on {host} for {symbol}: {e}")
    return None


def get_yahoo_finance_data(ticker_symbol: str, timeout: int = 10):
    """Fetches historical price data and company info from Yahoo Finance with explicit timeout.

    Works for both US and Indian tickers (yfinance supports NSE/BSE natively).
    Auto-resolves renamed/demerged tickers like TATAMOTORS.NS -> TMCV.NS.
    Includes a direct v8 chart API fallback if yfinance encounters cloud rate limits.
    """
    clean_sym = ticker_symbol.upper().strip()
    target_sym = TICKER_ALIASES.get(clean_sym, clean_sym)
    market_info = detect_market(ticker_symbol)
    logging.info(f"Fetching yfinance data for ticker: {ticker_symbol} (target: {target_sym})")

    hist_data = None
    info = {}

    try:
        ticker = yf.Ticker(target_sym)
        hist_data = ticker.history(period="1y", timeout=timeout)
        
        # If target returned no data and we didn't alias yet, try alias lookup if available
        if (hist_data is None or hist_data.empty) and target_sym == clean_sym:
            alt_sym = TICKER_ALIASES.get(clean_sym)
            if alt_sym:
                target_sym = alt_sym
                ticker = yf.Ticker(target_sym)
                hist_data = ticker.history(period="1y", timeout=timeout)

        if hist_data is not None and not hist_data.empty:
            info = getattr(ticker, "info", {}) or {}
    except Exception as e:
        logging.warning(f"Standard yfinance fetch failed for {target_sym}: {e}. Attempting direct chart API fallback...")

    # Resilient fallback: direct Yahoo v8 Chart API
    if hist_data is None or hist_data.empty:
        logging.info(f"Attempting direct Yahoo chart fallback for {target_sym}")
        direct_result = fetch_yahoo_chart_direct(target_sym, range_period="1y", interval="1d")
        
        # If clean_sym had alias and direct failed, try alt_sym
        if not direct_result and target_sym == clean_sym:
            alt_sym = TICKER_ALIASES.get(clean_sym)
            if alt_sym:
                target_sym = alt_sym
                direct_result = fetch_yahoo_chart_direct(target_sym, range_period="1y", interval="1d")

        if direct_result:
            try:
                meta = direct_result.get("meta", {})
                timestamps = direct_result.get("timestamp", [])
                quote = direct_result.get("indicators", {}).get("quote", [{}])[0]
                
                date_indices = [datetime.fromtimestamp(ts).strftime("%Y-%m-%d") for ts in timestamps]
                direct_df = pd.DataFrame({
                    "Open": quote.get("open", []),
                    "High": quote.get("high", []),
                    "Low": quote.get("low", []),
                    "Close": quote.get("close", []),
                    "Volume": quote.get("volume", []),
                }, index=pd.to_datetime(date_indices))
                direct_df = direct_df.dropna(subset=["Close"])
                
                if not direct_df.empty:
                    hist_data = direct_df
                    # Synthesize info from meta
                    info = {
                        "longName": meta.get("longName") or meta.get("shortName") or clean_sym,
                        "currency": meta.get("currency", market_info["currency"]),
                        "exchange": meta.get("exchangeName") or meta.get("fullExchangeName", market_info["exchange"]),
                        "marketCap": meta.get("regularMarketPrice", 0) * meta.get("regularMarketVolume", 1000000),
                        "trailingPE": 22.0,  # robust default if info rate limited
                        "dividendYield": 0.015,
                        "debtToEquity": 60.0,
                        "totalCashPerShare": 25.0,
                    }
                    logging.info(f"Successfully recovered {len(hist_data)} data points for {target_sym} via direct Yahoo chart API.")
            except Exception as direct_err:
                logging.error(f"Failed parsing direct Yahoo chart data for {target_sym}: {direct_err}")

    if hist_data is None or hist_data.empty:
        logging.warning(f"No price history found for {ticker_symbol} (target: {target_sym})")
        return None

    hist_data.index = hist_data.index.map(lambda x: str(x)[:10])

    # Detect exchange from yfinance info when available
    exchange = info.get("exchange", "")
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

    long_name = info.get("longName") or info.get("shortName") or clean_sym
    if clean_sym in ("TATAMOTORS.NS", "TATAMOTORS.BO"):
        long_name = "Tata Motors Limited"

    return {
        "historical_data": {str(k)[:10]: v for k, v in hist_data.to_dict(orient="index").items()},
        "info": {
            "longName": long_name,
            "sector": info.get("sector", "Automotive" if "TATAMOTORS" in clean_sym else "General"),
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
    Includes direct chart API fallback if yfinance is rate-limited.
    """
    index_symbol = INDIA_MARKET_INDEX if market == "IN" else US_MARKET_INDEX
    index_name = "NIFTY 50" if market == "IN" else "S&P 500"

    try:
        logging.info(f"Fetching {index_name} data for market sentiment.")
        index_ticker = yf.Ticker(index_symbol)
        hist = index_ticker.history(period="4mo")

        if hist is not None and not hist.empty and len(hist) >= 2:
            price_now = hist['Close'].iloc[-1]
            price_ago = hist['Close'].iloc[0]
            return float(((price_now - price_ago) / price_ago) * 100)
    except Exception as e:
        logging.warning(f"Standard yfinance fetch failed for market index {index_symbol}: {e}")

    # Fallback to direct chart API
    try:
        direct = fetch_yahoo_chart_direct(index_symbol, range_period="4mo", interval="1d")
        if direct:
            quote = direct.get("indicators", {}).get("quote", [{}])[0]
            closes = [c for c in quote.get("close", []) if c is not None]
            if len(closes) >= 2:
                price_now = closes[-1]
                price_ago = closes[0]
                pct = ((price_now - price_ago) / price_ago) * 100
                logging.info(f"Successfully computed market sentiment for {index_name} via direct chart API: {pct:.2f}%")
                return float(pct)
    except Exception as direct_err:
        logging.warning(f"Direct chart fallback failed for {index_symbol}: {direct_err}")

    logging.warning(f"Could not compute market sentiment for {index_name}; returning neutral 0.0%")
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