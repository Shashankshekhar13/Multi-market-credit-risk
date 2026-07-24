# tests/test_config.py
"""Tests for configuration — market ratings, config values."""

# pyrefly: ignore [missing-import]
import pytest
from backend.services.config import (
    US_AGENCY_RATINGS, INDIAN_AGENCY_RATINGS,
    INDIAN_TICKER_SUFFIXES, US_MARKET_INDEX, INDIA_MARKET_INDEX,
)


class TestRatings:
    def test_us_ratings_populated(self):
        assert len(US_AGENCY_RATINGS) > 0
        assert "AAPL" in US_AGENCY_RATINGS
        assert "MSFT" in US_AGENCY_RATINGS

    def test_indian_ratings_populated(self):
        assert len(INDIAN_AGENCY_RATINGS) > 0
        assert "RELIANCE.NS" in INDIAN_AGENCY_RATINGS
        assert "TCS.NS" in INDIAN_AGENCY_RATINGS

    def test_us_ratings_format(self):
        for ticker, rating in US_AGENCY_RATINGS.items():
            assert isinstance(rating, str)
            assert len(rating) > 0

    def test_indian_ratings_have_agency_prefix(self):
        for ticker, rating in INDIAN_AGENCY_RATINGS.items():
            assert "CRISIL" in rating or "ICRA" in rating


class TestMarketConfig:
    def test_indian_suffixes(self):
        assert ".NS" in INDIAN_TICKER_SUFFIXES
        assert ".BO" in INDIAN_TICKER_SUFFIXES

    def test_market_indices(self):
        assert US_MARKET_INDEX == "^GSPC"
        assert INDIA_MARKET_INDEX == "^NSEI"
