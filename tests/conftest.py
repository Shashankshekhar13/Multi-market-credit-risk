# tests/conftest.py
"""Shared test fixtures for CredLens backend tests."""

# pyrefly: ignore [missing-import]
import pytest
import os
import sys

# Ensure the project root is on the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def sample_yf_data():
    """Sample Yahoo Finance data for testing."""
    return {
        "historical_data": {
            "2024-01-01": {"Open": 100, "High": 105, "Low": 99, "Close": 103, "Volume": 1000000},
            "2024-01-02": {"Open": 103, "High": 106, "Low": 102, "Close": 105, "Volume": 1100000},
            "2024-01-03": {"Open": 105, "High": 108, "Low": 104, "Close": 107, "Volume": 900000},
        },
        "info": {
            "longName": "Test Corp",
            "sector": "Technology",
            "industry": "Software",
            "marketCap": 2000000000000,
            "trailingPE": 25.5,
            "dividendYield": 0.005,
            "debtToEquity": 45.0,
            "totalCashPerShare": 12.5,
            "currency": "USD",
            "exchange": "NMS",
            "country": "United States",
        },
        "market_info": {
            "market": "US",
            "currency": "USD",
            "exchange": "NASDAQ",
            "market_index": "^GSPC",
            "country": "United States",
            "flag": "🇺🇸",
        },
    }


@pytest.fixture
def sample_indian_yf_data():
    """Sample Yahoo Finance data for an Indian company."""
    return {
        "historical_data": {
            "2024-01-01": {"Open": 2500, "High": 2550, "Low": 2480, "Close": 2530, "Volume": 5000000},
            "2024-01-02": {"Open": 2530, "High": 2570, "Low": 2520, "Close": 2560, "Volume": 4500000},
        },
        "info": {
            "longName": "Reliance Industries",
            "sector": "Energy",
            "industry": "Oil & Gas",
            "marketCap": 18000000000000,
            "trailingPE": 28.0,
            "dividendYield": 0.003,
            "debtToEquity": 35.0,
            "totalCashPerShare": 50.0,
            "currency": "INR",
            "exchange": "NSI",
            "country": "India",
        },
        "market_info": {
            "market": "IN",
            "currency": "INR",
            "exchange": "NSE",
            "market_index": "^NSEI",
            "country": "India",
            "flag": "🇮🇳",
        },
    }


@pytest.fixture
def sample_news_data():
    """Sample news articles for testing."""
    return [
        {"source": "Reuters", "title": "Test Corp reports strong quarterly earnings", "url": "https://example.com/1", "publishedAt": "2024-01-03T12:00:00Z", "content": "..."},
        {"source": "Bloomberg", "title": "Tech sector faces investigation over data practices", "url": "https://example.com/2", "publishedAt": "2024-01-02T10:00:00Z", "content": "..."},
        {"source": "CNBC", "title": "Market rally continues amid positive sentiment", "url": "https://example.com/3", "publishedAt": "2024-01-01T08:00:00Z", "content": "..."},
    ]


@pytest.fixture
def sample_score_result():
    """Sample score result from the scoring engine."""
    return {
        "stability_score": 72,
        "technical_score": 65,
        "fundamental_score": 85,
        "explanation": [
            {"feature": "Debt-to-Equity", "value": 45.0, "impact": 2.0},
            {"feature": "volatility_30d", "value": 12.5, "impact": -1.5},
            {"feature": "negative_event_count", "value": 1, "impact": 0.3},
        ],
        "assessment_type": "ML_Model",
        "model_source": "joblib",
        "latest_sentiment": 0.15,
    }
