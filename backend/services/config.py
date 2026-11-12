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
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
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
    "TATAMOTORS.NS": "CRISIL AA-",
    "TATASTEEL.NS": "CRISIL AA",
    "MARUTI.NS": "CRISIL AAA",
    "BAJFINANCE.NS": "CRISIL AAA",
    "HCLTECH.NS": "CRISIL AAA",
    "SUNPHARMA.NS": "CRISIL AA+",
    "AXISBANK.NS": "CRISIL AA+",
    "ADANIENT.NS": "ICRA AA",
    "ASIANPAINT.NS": "CRISIL AAA",
    "TITAN.NS": "CRISIL AA+",
    "NESTLEIND.NS": "CRISIL AAA",
    "BRITANNIA.NS": "CRISIL AAA",
    "DABUR.NS": "CRISIL AAA",
    "GODREJCP.NS": "CRISIL AAA",
    "PIDILITIND.NS": "CRISIL AAA",
    "BAJAJFINSV.NS": "CRISIL AAA",
    "INDUSINDBK.NS": "CRISIL AA+",
    "ADANIPORTS.NS": "ICRA AA+",
    "POWERGRID.NS": "CRISIL AAA",
    "NTPC.NS": "CRISIL AAA",
    "ONGC.NS": "CRISIL AAA",
    "COALINDIA.NS": "CRISIL AAA",
    "ULTRACEMCO.NS": "CRISIL AAA",
    "GRASIM.NS": "CRISIL AAA",
    "JSWSTEEL.NS": "CRISIL AA",
    "HINDALCO.NS": "CRISIL AA",
    "SHREECEM.NS": "CRISIL AA+",
    "DRREDDY.NS": "CRISIL AA+",
    "CIPLA.NS": "CRISIL AA+",
    "DIVISLAB.NS": "CRISIL AA+",
    "APOLLOHOSP.NS": "CRISIL AA+",
    "SIEMENS.NS": "CRISIL AAA",
    "BOSCHLTD.NS": "CRISIL AAA",
    "M&M.NS": "CRISIL AAA",
    "EICHERMOT.NS": "CRISIL AA+",
    "HEROMOTOCO.NS": "CRISIL AAA",
    "BAJAJ-AUTO.NS": "CRISIL AAA",
    "TECHM.NS": "CRISIL AA+",
    "TMPV.NS": "CRISIL AA-",
    "RELIANCE.BO": "CRISIL AAA",
    "TCS.BO": "CRISIL AAA",
    "INFY.BO": "CRISIL AAA",
}

# --- US Credit Ratings (S&P) ---
US_AGENCY_RATINGS = {
    "AAPL": "AA+",
    "MSFT": "AAA",
    "GOOGL": "AA+",
    "AMZN": "AA",
    "NVDA": "A-",
    "META": "AA-",
    "TSLA": "BB+",
    "JPM": "A-",
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
    "BLK": "AA-",
    "BAC": "A-",
    "WFC": "BBB+",
    "GS": "BBB+",
    "MS": "A-",
    "C": "BBB+",
    "XOM": "AA-",
    "CVX": "AA-",
    "KO": "A+",
    "PEP": "A+",
    "MCD": "BBB+",
    "NKE": "A",
    "SBUX": "BBB+",
    "COST": "A+",
    "PFE": "A",
    "MRK": "A+",
    "ABBV": "A-",
    "LLY": "A+",
    "ABT": "A+",
    "INTC": "BBB+",
    "AMD": "A-",
    "CSCO": "AA-",
    "ORCL": "BBB",
    "IBM": "A-",
    "QCOM": "A",
    "TXN": "A+",
    "T": "BBB",
    "VZ": "BBB+",
    "CAT": "A",
    "GE": "BBB+",
    "HON": "A",
    "UPS": "A",
}
