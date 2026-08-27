# backend/routers/companies.py
"""Company-related API endpoints with database querying."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import Optional
import logging

from backend.services.database import get_db
from backend.models import Company, Score

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/companies", tags=["companies"])


MASTER_COMPANIES = [
    # US Companies (51)
    {"ticker": "AAPL", "name": "Apple", "market": "US", "exchange": "NASDAQ", "currency": "USD", "sector": "Tech"},
    {"ticker": "MSFT", "name": "Microsoft", "market": "US", "exchange": "NASDAQ", "currency": "USD", "sector": "Tech"},
    {"ticker": "GOOGL", "name": "Alphabet", "market": "US", "exchange": "NASDAQ", "currency": "USD", "sector": "Tech"},
    {"ticker": "AMZN", "name": "Amazon", "market": "US", "exchange": "NASDAQ", "currency": "USD", "sector": "Consumer/Tech"},
    {"ticker": "NVDA", "name": "Nvidia", "market": "US", "exchange": "NASDAQ", "currency": "USD", "sector": "Semiconductors"},
    {"ticker": "META", "name": "Meta Platforms", "market": "US", "exchange": "NASDAQ", "currency": "USD", "sector": "Tech"},
    {"ticker": "TSLA", "name": "Tesla", "market": "US", "exchange": "NASDAQ", "currency": "USD", "sector": "Auto"},
    {"ticker": "JPM", "name": "JPMorgan Chase", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Financials"},
    {"ticker": "V", "name": "Visa", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Financials"},
    {"ticker": "JNJ", "name": "Johnson & Johnson", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Healthcare"},
    {"ticker": "WMT", "name": "Walmart", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Retail"},
    {"ticker": "PG", "name": "Procter & Gamble", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Consumer"},
    {"ticker": "MA", "name": "Mastercard", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Financials"},
    {"ticker": "UNH", "name": "UnitedHealth", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Healthcare"},
    {"ticker": "HD", "name": "Home Depot", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Retail"},
    {"ticker": "DIS", "name": "Disney", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Media"},
    {"ticker": "NFLX", "name": "Netflix", "market": "US", "exchange": "NASDAQ", "currency": "USD", "sector": "Media"},
    {"ticker": "BA", "name": "Boeing", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Industrials"},
    {"ticker": "SMCI", "name": "Super Micro Computer", "market": "US", "exchange": "NASDAQ", "currency": "USD", "sector": "Tech"},
    {"ticker": "BLK", "name": "BlackRock", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Financials"},
    {"ticker": "BAC", "name": "Bank of America", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Financials"},
    {"ticker": "WFC", "name": "Wells Fargo", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Financials"},
    {"ticker": "GS", "name": "Goldman Sachs", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Financials"},
    {"ticker": "MS", "name": "Morgan Stanley", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Financials"},
    {"ticker": "C", "name": "Citigroup", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Financials"},
    {"ticker": "XOM", "name": "ExxonMobil", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Energy"},
    {"ticker": "CVX", "name": "Chevron", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Energy"},
    {"ticker": "KO", "name": "Coca-Cola", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Consumer"},
    {"ticker": "PEP", "name": "PepsiCo", "market": "US", "exchange": "NASDAQ", "currency": "USD", "sector": "Consumer"},
    {"ticker": "MCD", "name": "McDonald's", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Consumer"},
    {"ticker": "NKE", "name": "Nike", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Consumer"},
    {"ticker": "SBUX", "name": "Starbucks", "market": "US", "exchange": "NASDAQ", "currency": "USD", "sector": "Consumer"},
    {"ticker": "COST", "name": "Costco", "market": "US", "exchange": "NASDAQ", "currency": "USD", "sector": "Retail"},
    {"ticker": "PFE", "name": "Pfizer", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Healthcare"},
    {"ticker": "MRK", "name": "Merck", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Healthcare"},
    {"ticker": "ABBV", "name": "AbbVie", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Healthcare"},
    {"ticker": "LLY", "name": "Eli Lilly", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Healthcare"},
    {"ticker": "ABT", "name": "Abbott Labs", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Healthcare"},
    {"ticker": "INTC", "name": "Intel", "market": "US", "exchange": "NASDAQ", "currency": "USD", "sector": "Semiconductors"},
    {"ticker": "AMD", "name": "AMD", "market": "US", "exchange": "NASDAQ", "currency": "USD", "sector": "Semiconductors"},
    {"ticker": "CSCO", "name": "Cisco", "market": "US", "exchange": "NASDAQ", "currency": "USD", "sector": "Tech"},
    {"ticker": "ORCL", "name": "Oracle", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Tech"},
    {"ticker": "IBM", "name": "IBM", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Tech"},
    {"ticker": "QCOM", "name": "Qualcomm", "market": "US", "exchange": "NASDAQ", "currency": "USD", "sector": "Semiconductors"},
    {"ticker": "TXN", "name": "Texas Instruments", "market": "US", "exchange": "NASDAQ", "currency": "USD", "sector": "Semiconductors"},
    {"ticker": "T", "name": "AT&T", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Telecom"},
    {"ticker": "VZ", "name": "Verizon", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Telecom"},
    {"ticker": "CAT", "name": "Caterpillar", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Industrials"},
    {"ticker": "GE", "name": "General Electric", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Industrials"},
    {"ticker": "HON", "name": "Honeywell", "market": "US", "exchange": "NASDAQ", "currency": "USD", "sector": "Industrials"},
    {"ticker": "UPS", "name": "UPS", "market": "US", "exchange": "NYSE", "currency": "USD", "sector": "Logistics"},

    # India Companies (50)
    {"ticker": "RELIANCE.NS", "name": "Reliance Industries", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Energy/Conglomerate"},
    {"ticker": "TCS.NS", "name": "Tata Consultancy Services", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "IT"},
    {"ticker": "INFY.NS", "name": "Infosys", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "IT"},
    {"ticker": "HDFCBANK.NS", "name": "HDFC Bank", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Banking"},
    {"ticker": "ICICIBANK.NS", "name": "ICICI Bank", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Banking"},
    {"ticker": "HINDUNILVR.NS", "name": "Hindustan Unilever", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "FMCG"},
    {"ticker": "SBIN.NS", "name": "State Bank of India", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Banking"},
    {"ticker": "BHARTIARTL.NS", "name": "Bharti Airtel", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Telecom"},
    {"ticker": "ITC.NS", "name": "ITC Ltd", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "FMCG"},
    {"ticker": "KOTAKBANK.NS", "name": "Kotak Mahindra Bank", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Banking"},
    {"ticker": "LT.NS", "name": "Larsen & Toubro", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Infrastructure"},
    {"ticker": "WIPRO.NS", "name": "Wipro", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "IT"},
    {"ticker": "TATAMOTORS.NS", "name": "Tata Motors", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Auto"},
    {"ticker": "TATASTEEL.NS", "name": "Tata Steel", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Metals"},
    {"ticker": "MARUTI.NS", "name": "Maruti Suzuki", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Auto"},
    {"ticker": "BAJFINANCE.NS", "name": "Bajaj Finance", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "NBFC"},
    {"ticker": "HCLTECH.NS", "name": "HCL Technologies", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "IT"},
    {"ticker": "SUNPHARMA.NS", "name": "Sun Pharma", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Pharma"},
    {"ticker": "AXISBANK.NS", "name": "Axis Bank", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Banking"},
    {"ticker": "ADANIENT.NS", "name": "Adani Enterprises", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Conglomerate"},
    {"ticker": "ASIANPAINT.NS", "name": "Asian Paints", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Consumer"},
    {"ticker": "TITAN.NS", "name": "Titan Company", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Consumer"},
    {"ticker": "NESTLEIND.NS", "name": "Nestle India", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "FMCG"},
    {"ticker": "BRITANNIA.NS", "name": "Britannia Industries", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "FMCG"},
    {"ticker": "DABUR.NS", "name": "Dabur India", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "FMCG"},
    {"ticker": "GODREJCP.NS", "name": "Godrej Consumer Products", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "FMCG"},
    {"ticker": "PIDILITIND.NS", "name": "Pidilite Industries", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Chemicals"},
    {"ticker": "BAJAJFINSV.NS", "name": "Bajaj Finserv", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Financials"},
    {"ticker": "INDUSINDBK.NS", "name": "IndusInd Bank", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Banking"},
    {"ticker": "ADANIPORTS.NS", "name": "Adani Ports", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Infrastructure"},
    {"ticker": "POWERGRID.NS", "name": "Power Grid Corp", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Utility"},
    {"ticker": "NTPC.NS", "name": "NTPC Ltd", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Utility"},
    {"ticker": "ONGC.NS", "name": "Oil & Natural Gas Corp", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Energy"},
    {"ticker": "COALINDIA.NS", "name": "Coal India", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Mining"},
    {"ticker": "ULTRACEMCO.NS", "name": "UltraTech Cement", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Cement"},
    {"ticker": "GRASIM.NS", "name": "Grasim Industries", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Cement/Conglomerate"},
    {"ticker": "JSWSTEEL.NS", "name": "JSW Steel", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Metals"},
    {"ticker": "HINDALCO.NS", "name": "Hindalco Industries", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Metals"},
    {"ticker": "SHREECEM.NS", "name": "Shree Cement", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Cement"},
    {"ticker": "DRREDDY.NS", "name": "Dr. Reddy's Labs", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Pharma"},
    {"ticker": "CIPLA.NS", "name": "Cipla", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Pharma"},
    {"ticker": "DIVISLAB.NS", "name": "Divi's Laboratories", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Pharma"},
    {"ticker": "APOLLOHOSP.NS", "name": "Apollo Hospitals", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Healthcare"},
    {"ticker": "SIEMENS.NS", "name": "Siemens India", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Industrials"},
    {"ticker": "BOSCHLTD.NS", "name": "Bosch Ltd", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Auto Components"},
    {"ticker": "M&M.NS", "name": "Mahindra & Mahindra", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Auto"},
    {"ticker": "EICHERMOT.NS", "name": "Eicher Motors", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Auto"},
    {"ticker": "HEROMOTOCO.NS", "name": "Hero MotoCorp", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Auto"},
    {"ticker": "BAJAJ-AUTO.NS", "name": "Bajaj Auto", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "Auto"},
    {"ticker": "TECHM.NS", "name": "Tech Mahindra", "market": "IN", "exchange": "NSE", "currency": "INR", "sector": "IT"}
]


@router.get("")
async def list_companies(
    market: Optional[str] = Query(None, description="Filter by market: US or IN"),
    limit: int = Query(200, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List all tracked companies, optionally filtered by market."""
    try:
        stmt = select(Company).order_by(desc(Company.last_updated))

        if market:
            stmt = stmt.where(Company.market == market.upper())

        stmt = stmt.limit(limit).offset(offset)
        result = await db.execute(stmt)
        companies = result.scalars().all()

        if not companies:
            # Fallback to master catalog if DB is empty
            filtered = [
                c for c in MASTER_COMPANIES
                if not market or c["market"] == market.upper()
            ]
            return {
                "companies": filtered[offset:offset+limit],
                "total": len(filtered),
            }

        # Count total
        count_stmt = select(func.count()).select_from(Company)
        if market:
            count_stmt = count_stmt.where(Company.market == market.upper())
        total = (await db.execute(count_stmt)).scalar() or 0

        return {
            "companies": [
                {
                    "ticker": c.ticker,
                    "name": c.name,
                    "market": c.market,
                    "exchange": c.exchange,
                    "currency": c.currency,
                    "sector": c.sector,
                    "industry": c.industry,
                    "market_cap": c.market_cap,
                    "last_updated": c.last_updated.isoformat() if c.last_updated else None,
                }
                for c in companies
            ],
            "total": total,
        }
    except Exception as e:
        logger.error(f"Error listing companies: {e}")
        filtered = [
            c for c in MASTER_COMPANIES
            if not market or c["market"] == market.upper()
        ]
        return {"companies": filtered[offset:offset+limit], "total": len(filtered)}


@router.get("/search")
async def search_companies(
    q: str = Query(..., min_length=1, description="Search by name or ticker"),
    db: AsyncSession = Depends(get_db),
):
    """Search companies by name or ticker."""
    try:
        search_term = f"%{q.upper()}%"
        stmt = (
            select(Company)
            .where(
                (Company.ticker.ilike(search_term)) |
                (Company.name.ilike(search_term))
            )
            .order_by(Company.ticker)
            .limit(20)
        )
        result = await db.execute(stmt)
        companies = result.scalars().all()

        if not companies:
            # Fallback search against master list
            q_clean = q.strip().upper()
            matched = [
                c for c in MASTER_COMPANIES
                if q_clean in c["ticker"].upper() or q_clean in c["name"].upper()
            ][:20]
            return {"results": matched, "count": len(matched)}

        return {
            "results": [
                {
                    "ticker": c.ticker,
                    "name": c.name,
                    "market": c.market,
                    "exchange": c.exchange,
                }
                for c in companies
            ],
            "count": len(companies),
        }
    except Exception as e:
        logger.error(f"Error searching companies: {e}")
        q_clean = q.strip().upper()
        matched = [
            c for c in MASTER_COMPANIES
            if q_clean in c["ticker"].upper() or q_clean in c["name"].upper()
        ][:20]
        return {"results": matched, "count": len(matched)}


@router.get("/{ticker}/history")
async def get_score_history(
    ticker: str,
    limit: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Get score history for a specific ticker."""
    try:
        stmt = (
            select(Score)
            .where(Score.ticker == ticker.upper())
            .order_by(desc(Score.date))
            .limit(limit)
        )
        result = await db.execute(stmt)
        scores = result.scalars().all()

        return {
            "ticker": ticker.upper(),
            "history": [
                {
                    "date": s.date.isoformat() if s.date else None,
                    "stability_score": s.stability_score,
                    "fundamental_score": s.fundamental_score,
                    "technical_score": s.technical_score,
                    "assessment_type": s.assessment_type,
                    "latest_sentiment": s.latest_sentiment,
                }
                for s in scores
            ],
            "count": len(scores),
        }
    except Exception as e:
        logger.error(f"Error fetching score history for {ticker}: {e}")
        return {"ticker": ticker.upper(), "history": [], "count": 0, "error": "Database unavailable"}
