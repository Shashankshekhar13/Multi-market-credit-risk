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


@router.get("")
async def list_companies(
    market: Optional[str] = Query(None, description="Filter by market: US or IN"),
    limit: int = Query(50, ge=1, le=200),
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
        return {"companies": [], "total": 0, "error": "Database unavailable"}


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
        return {"results": [], "count": 0, "error": "Database unavailable"}


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
