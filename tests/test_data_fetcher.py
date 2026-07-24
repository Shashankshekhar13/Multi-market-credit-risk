# tests/test_data_fetcher.py
"""Tests for the data fetcher module — market detection and data source integration."""

# pyrefly: ignore [missing-import]
import pytest
from backend.services.data_fetcher import detect_market, is_indian_ticker


class TestMarketDetection:
    """Tests for detect_market() and is_indian_ticker()."""

    def test_us_ticker_detection(self):
        result = detect_market("AAPL")
        assert result["market"] == "US"
        assert result["currency"] == "USD"
        assert result["flag"] == "🇺🇸"

    def test_nse_ticker_detection(self):
        result = detect_market("RELIANCE.NS")
        assert result["market"] == "IN"
        assert result["currency"] == "INR"
        assert result["exchange"] == "NSE"
        assert result["flag"] == "🇮🇳"

    def test_bse_ticker_detection(self):
        result = detect_market("TCS.BO")
        assert result["market"] == "IN"
        assert result["currency"] == "INR"
        assert result["exchange"] == "BSE"

    def test_case_insensitive_detection(self):
        result = detect_market("reliance.ns")
        assert result["market"] == "IN"

    def test_is_indian_ticker_true(self):
        assert is_indian_ticker("RELIANCE.NS") is True
        assert is_indian_ticker("TCS.BO") is True
        assert is_indian_ticker("INFY.NS") is True

    def test_is_indian_ticker_false(self):
        assert is_indian_ticker("AAPL") is False
        assert is_indian_ticker("MSFT") is False
        assert is_indian_ticker("GOOGL") is False

    def test_market_index_us(self):
        result = detect_market("NVDA")
        assert result["market_index"] == "^GSPC"

    def test_market_index_india(self):
        result = detect_market("HDFCBANK.NS")
        assert result["market_index"] == "^NSEI"
