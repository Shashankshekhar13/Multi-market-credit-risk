import os
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- API Keys ---
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
FRED_API_KEY = os.getenv("FRED_API_KEY")

# --- Database ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://credlens:credlens@localhost:5432/credlens")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# --- Auth ---
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# --- Market Configuration ---
INDIAN_TICKER_SUFFIXES = (".NS", ".BO")
US_MARKET_INDEX = "^GSPC"       # S&P 500
INDIA_MARKET_INDEX = "^NSEI"    # NIFTY 50

# --- Indian Credit Ratings (CRISIL/ICRA) ---
INDIAN_AGENCY_RATINGS = {
    "RELIANCE.NS": "CRISIL AAA",
    "TCS.NS": "CRISIL AAA",
    "INFY.NS": "CRISIL AAA",
    "HDFCBANK.NS": "CRISIL AAA",
    "ICICIBANK.NS": "CRISIL AAA",
    "HINDUNILVR.NS": "CRISIL AAA",
    "SBIN.NS": "CRISIL AA+",
    "BHARTIARTL.NS": "CRISIL AAA",
    "ITC.NS": "CRISIL AAA",
    "KOTAKBANK.NS": "CRISIL AAA",
    "LT.NS": "CRISIL AAA",
    "WIPRO.NS": "CRISIL AA+",
    "ADANIENT.NS": "ICRA AA",
    "TATAMOTORS.NS": "CRISIL AA-",
    "TMPV.NS": "CRISIL AA-",
    "TATASTEEL.NS": "CRISIL AA",
    "MARUTI.NS": "CRISIL AAA",
    "BAJFINANCE.NS": "CRISIL AAA",
    "HCLTECH.NS": "CRISIL AAA",
    "SUNPHARMA.NS": "CRISIL AA",
    "AXISBANK.NS": "CRISIL AA+",
    "RELIANCE.BO": "CRISIL AAA",
    "TCS.BO": "CRISIL AAA",
    "INFY.BO": "CRISIL AAA",
}

# --- US Credit Ratings (S&P) ---
US_AGENCY_RATINGS = {
    "AAPL": "AA+",
    "MSFT": "AAA",
    "GOOGL": "AA+",
    "NVDA": "A-",
    "JPM": "A-",
    "TSLA": "BB+",
    "AMZN": "AA",
    "META": "AA-",
    "BRK-B": "AA",
    "V": "AA-",
    "JNJ": "AAA",
    "WMT": "AA",
    "PG": "AA-",
    "MA": "A+",
    "UNH": "A+",
    "HD": "A",
    "DIS": "A-",
    "NFLX": "BBB+",
    "BA": "BBB-",
    "SMCI": "N/A",
}
