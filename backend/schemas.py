# backend/schemas.py
"""Pydantic models for typed API request/response schemas."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ─── Score Response Models ───

class ExplanationItem(BaseModel):
    feature: str
    value: float | str
    impact: float


class ScoreResult(BaseModel):
    stability_score: float | str
    fundamental_score: Optional[float] = None
    technical_score: Optional[float] = None
    explanation: list[ExplanationItem]
    assessment_type: str           # ML_Model or Heuristic
    latest_sentiment: float = 0.0
    all_features: Optional[dict] = None


class NewsArticleResponse(BaseModel):
    source: str
    title: str
    url: str
    publishedAt: str
    content: Optional[str] = None


class CompanyInfo(BaseModel):
    longName: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    marketCap: Optional[float] = None
    trailingPE: Optional[float] = None
    dividendYield: Optional[float] = None
    debtToEquity: Optional[float] = None
    totalCashPerShare: Optional[float] = None
    currency: Optional[str] = None
    exchange: Optional[str] = None
    country: Optional[str] = None


class ScoreResponse(BaseModel):
    """Full response from the /api/v1/score/{ticker} endpoint."""
    ticker: str
    company_name: str
    market: str                         # US or IN
    currency: str                       # USD or INR
    exchange: str                       # NYSE, NASDAQ, NSE, BSE
    country: str
    flag: str                           # 🇺🇸 or 🇮🇳
    agency_rating: str
    company_info: dict
    score_result: dict
    stock_history: Optional[dict] = None
    recent_news_for_context: list[dict] = []


# ─── Rating Response ───

class RatingResponse(BaseModel):
    ticker: str
    market: str
    rating: str
    agency: str


# ─── Company List Response ───

class CompanyListItem(BaseModel):
    ticker: str
    name: Optional[str] = None
    market: str
    exchange: Optional[str] = None
    currency: str
    sector: Optional[str] = None
    latest_score: Optional[float] = None
    last_updated: Optional[datetime] = None


class CompanyListResponse(BaseModel):
    companies: list[CompanyListItem]
    total: int


# ─── Score History Response ───

class ScoreHistoryItem(BaseModel):
    date: datetime
    stability_score: Optional[float] = None
    fundamental_score: Optional[float] = None
    technical_score: Optional[float] = None
    assessment_type: str


class ScoreHistoryResponse(BaseModel):
    ticker: str
    history: list[ScoreHistoryItem]


# ─── Health Check ───

class HealthResponse(BaseModel):
    message: str
    supported_markets: list[str]
    database_connected: bool = False
    version: str = "2.0.0"
