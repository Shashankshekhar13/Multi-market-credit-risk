# tests/test_validation.py
"""Unit tests for ticker validation and scoring impact display logic."""

# pyrefly: ignore [missing-import]
import pytest
import re

# We will test ticker validation rules that mirror the frontend validation logic.
def python_validate_ticker(ticker: str, market: str = "US", mode: str = "single"):
    if not ticker or not ticker.strip():
        return {"valid": False, "error": "Ticker is required."}
    
    if mode == "compare":
        parts = [p.strip() for p in ticker.split(",") if p.strip()]
        if len(parts) < 2:
            return {"valid": False, "error": "Please enter at least 2 tickers separated by commas."}
        if len(parts) > 3:
            return {"valid": False, "error": "Maximum of 3 tickers can be compared."}
        for part in parts:
            check = python_validate_ticker(part, market, "single")
            if not check["valid"]:
                return {"valid": False, "error": f"Ticker \"{part}\": {check['error']}"}
        return {"valid": True, "error": None}

    # Sanitization
    sanitized = re.sub(r"[^A-Za-z0-9.]", "", ticker).upper()
    if sanitized != ticker.upper():
        return {"valid": False, "error": "Ticker contains invalid characters. Only letters, numbers, and dots allowed."}
    
    if len(sanitized) > 20:
        return {"valid": False, "error": "Ticker is too long (max 20 characters)."}

    if market == "IN":
        in_regex = r"^[A-Z][A-Z0-9&]{0,19}\.(NS|BO)$"
        if not re.match(in_regex, sanitized):
            return {"valid": False, "error": "Indian tickers must end with .NS (NSE) or .BO (BSE). e.g. RELIANCE.NS"}
    else:
        us_regex = r"^[A-Z]{1,6}$"
        if not re.match(us_regex, sanitized):
            return {"valid": False, "error": "US tickers must be 1-6 uppercase letters. e.g. AAPL, MSFT"}

    return {"valid": True, "error": None}


class TestTickerValidation:
    """Tests for ticker validation patterns."""

    def test_valid_us_ticker(self):
        res = python_validate_ticker("AAPL", "US", "single")
        assert res["valid"] is True
        assert res["error"] is None

    def test_valid_indian_ticker(self):
        res = python_validate_ticker("RELIANCE.NS", "IN", "single")
        assert res["valid"] is True
        res = python_validate_ticker("TCS.BO", "IN", "single")
        assert res["valid"] is True

    def test_invalid_us_ticker(self):
        res = python_validate_ticker("AAPL123", "US", "single")
        assert res["valid"] is False
        assert "1-6 uppercase letters" in res["error"]

    def test_invalid_indian_ticker_no_suffix(self):
        res = python_validate_ticker("RELIANCE", "IN", "single")
        assert res["valid"] is False
        assert "must end with .NS" in res["error"]

    def test_ticker_injection_attempts(self):
        res = python_validate_ticker("AAPL; DROP TABLE scores;", "US", "single")
        assert res["valid"] is False
        assert "invalid characters" in res["error"]

    def test_compare_mode_valid(self):
        res = python_validate_ticker("AAPL, MSFT, TSLA", "US", "compare")
        assert res["valid"] is True

    def test_compare_mode_too_many(self):
        res = python_validate_ticker("AAPL, MSFT, TSLA, NVDA", "US", "compare")
        assert res["valid"] is False
        assert "Maximum of 3" in res["error"]

    def test_compare_mode_invalid_member(self):
        res = python_validate_ticker("AAPL, MSFT123, TSLA", "US", "compare")
        assert res["valid"] is False
        assert "Ticker \"MSFT123\"" in res["error"]
