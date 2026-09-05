# tests/test_scoring.py
"""Tests for the scoring engine — feature engineering, fundamental score, heuristics."""

# pyrefly: ignore [missing-import]
import pytest
import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np
from backend.services.scoring_engine import (
    get_sentiment, engineer_features, get_fundamental_score,
    get_heuristic_assessment,
)


class TestSentiment:
    """Tests for sentiment analysis."""

    def test_positive_sentiment(self):
        score = get_sentiment("Company reports record-breaking profits and growth")
        assert score > 0

    def test_negative_sentiment(self):
        score = get_sentiment("Company faces major fraud investigation and scandal")
        assert score < 0

    def test_neutral_sentiment(self):
        score = get_sentiment("Company releases quarterly report")
        # neutral should be near 0
        assert -0.3 < score < 0.3

    def test_empty_string(self):
        assert get_sentiment("") == 0.0

    def test_none_input(self):
        assert get_sentiment(None) == 0.0

    def test_non_string_input(self):
        assert get_sentiment(123) == 0.0


class TestFundamentalScore:
    """Tests for the fundamental scoring function."""

    def test_healthy_company(self, sample_yf_data):
        score, explanation = get_fundamental_score(sample_yf_data)
        assert score > 50
        assert isinstance(explanation, list)

    def test_high_debt_penalty(self):
        data = {"info": {"debtToEquity": 200, "trailingPE": 20, "totalCashPerShare": 5}}
        score, explanation = get_fundamental_score(data)
        assert score <= 50  # Heavy penalty for high debt

    def test_negative_pe_penalty(self):
        data = {"info": {"debtToEquity": 50, "trailingPE": -5, "totalCashPerShare": 5}}
        score, explanation = get_fundamental_score(data)
        assert score < 100

    def test_missing_data_penalties(self):
        data = {"info": {}}
        score, explanation = get_fundamental_score(data)
        assert score < 50  # Multiple penalties for missing data
        assert len(explanation) >= 2  # Should have multiple explanation items

    def test_perfect_company(self):
        data = {"info": {"debtToEquity": 30, "trailingPE": 20, "totalCashPerShare": 10}}
        score, explanation = get_fundamental_score(data)
        assert score == 100


class TestFeatureEngineering:
    """Tests for the feature engineering pipeline."""

    def test_empty_data(self):
        result = engineer_features({}, 0, pd.Series(dtype='float64'), [])
        assert result.empty

    def test_missing_historical_data(self):
        result = engineer_features({"info": {}}, 0, pd.Series(dtype='float64'), [])
        assert result.empty

    def test_feature_columns_present(self, sample_yf_data):
        features = engineer_features(sample_yf_data, 5.0, pd.Series(dtype='float64'), [])
        if not features.empty:
            expected_cols = [
                'Close_raw', 'price_change_pct_7d', 'volatility_30d',
                'rsi_14d', 'avg_news_sentiment_30d', 'negative_event_count',
            ]
            for col in expected_cols:
                assert col in features.columns, f"Missing column: {col}"

    def test_news_features_with_data(self, sample_yf_data, sample_news_data):
        features = engineer_features(sample_yf_data, 5.0, pd.Series(dtype='float64'), sample_news_data)
        if not features.empty:
            assert features['news_volume_30d'].iloc[0] == len(sample_news_data)


class TestHeuristicAssessment:
    """Tests for the heuristic fallback assessment."""

    def test_heuristic_returns_correct_type(self, sample_yf_data):
        features = engineer_features(sample_yf_data, 5.0, pd.Series(dtype='float64'), [])
        if not features.empty:
            result = get_heuristic_assessment(features, sample_yf_data)
            assert result["assessment_type"] == "Heuristic"
            assert isinstance(result["stability_score"], (int, float))
            assert 0 <= result["stability_score"] <= 100
            assert "explanation" in result
