# backend/models.py
"""SQLAlchemy ORM models for the CredLens database."""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, Boolean,
    JSON, Date, UniqueConstraint, Index, ForeignKey,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime, timezone


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class Company(Base):
    """Company master data — both US and Indian listed companies."""
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    market = Column(String(5), nullable=False, default="US")    # US or IN
    exchange = Column(String(20), nullable=True)                # NYSE, NASDAQ, NSE, BSE
    currency = Column(String(5), nullable=False, default="USD") # USD or INR
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    market_cap = Column(Float, nullable=True)
    info_json = Column(JSON, nullable=True)  # Full yfinance info blob
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    price_history = relationship("PriceHistory", back_populates="company", cascade="all, delete-orphan")
    scores = relationship("Score", back_populates="company", cascade="all, delete-orphan")
    news_articles = relationship("NewsArticle", back_populates="company", cascade="all, delete-orphan")
    features = relationship("FeatureSnapshot", back_populates="company", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Company(ticker={self.ticker}, market={self.market})>"


class PriceHistory(Base):
    """Daily OHLCV price data for each company."""
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), ForeignKey("companies.ticker", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    open = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("ticker", "date", name="uq_price_ticker_date"),
        Index("ix_price_ticker_date", "ticker", "date"),
    )

    company = relationship("Company", back_populates="price_history")

    def __repr__(self):
        return f"<PriceHistory(ticker={self.ticker}, date={self.date}, close={self.close})>"


class Score(Base):
    """Credit stability score history for each company."""
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), ForeignKey("companies.ticker", ondelete="CASCADE"), nullable=False)
    date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    stability_score = Column(Float, nullable=True)
    fundamental_score = Column(Float, nullable=True)
    technical_score = Column(Float, nullable=True)
    assessment_type = Column(String(20), nullable=False)  # ML_Model or Heuristic
    latest_sentiment = Column(Float, nullable=True)
    explanation_json = Column(JSON, nullable=True)  # SHAP explanations

    __table_args__ = (
        Index("ix_scores_ticker_date", "ticker", "date"),
    )

    company = relationship("Company", back_populates="scores")

    def __repr__(self):
        return f"<Score(ticker={self.ticker}, score={self.stability_score}, type={self.assessment_type})>"


class NewsArticle(Base):
    """Cached news articles with sentiment scores."""
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), ForeignKey("companies.ticker", ondelete="CASCADE"), nullable=False)
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)
    published_at = Column(DateTime, nullable=True)
    sentiment_score = Column(Float, nullable=True)
    content = Column(Text, nullable=True)
    fetched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_news_ticker_published", "ticker", "published_at"),
    )

    company = relationship("Company", back_populates="news_articles")

    def __repr__(self):
        return f"<NewsArticle(ticker={self.ticker}, title={self.title[:50]})>"


class FeatureSnapshot(Base):
    """Engineered feature snapshots for ML model inputs."""
    __tablename__ = "feature_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), ForeignKey("companies.ticker", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    feature_json = Column(JSON, nullable=False)  # All 17+ engineered features

    __table_args__ = (
        UniqueConstraint("ticker", "date", name="uq_feature_ticker_date"),
        Index("ix_features_ticker_date", "ticker", "date"),
    )

    company = relationship("Company", back_populates="features")

    def __repr__(self):
        return f"<FeatureSnapshot(ticker={self.ticker}, date={self.date})>"


class MacroIndicator(Base):
    """Macroeconomic indicators from FRED, RBI, etc."""
    __tablename__ = "macro_indicators"

    id = Column(Integer, primary_key=True, autoincrement=True)
    indicator_id = Column(String(50), nullable=False)  # e.g., DGS10, REPO_RATE
    date = Column(Date, nullable=False)
    value = Column(Float, nullable=True)
    source = Column(String(20), nullable=False, default="FRED")  # FRED, RBI

    __table_args__ = (
        UniqueConstraint("indicator_id", "date", name="uq_macro_indicator_date"),
        Index("ix_macro_indicator_date", "indicator_id", "date"),
    )

    def __repr__(self):
        return f"<MacroIndicator(id={self.indicator_id}, date={self.date}, value={self.value})>"


# ─── Phase 2 Models (Auth) ───

class User(Base):
    """User accounts for authentication and personalized features."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    watchlist = relationship("UserWatchlist", back_populates="user", cascade="all, delete-orphan")
    alert_preferences = relationship("UserAlertPreference", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(email={self.email})>"


class UserWatchlist(Base):
    """User watchlists for tracking specific tickers."""
    __tablename__ = "user_watchlists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ticker = Column(String(20), nullable=False)
    added_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("user_id", "ticker", name="uq_watchlist_user_ticker"),
    )

    user = relationship("User", back_populates="watchlist")


class UserAlertPreference(Base):
    """User alert preferences for proactive notifications."""
    __tablename__ = "user_alert_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ticker = Column(String(20), nullable=False)
    alert_type = Column(String(50), nullable=False)  # score_drop, volatile, news_spike, recovery
    threshold = Column(Float, nullable=True)
    channel = Column(String(20), nullable=False, default="email")  # email, sms, in_app
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="alert_preferences")
