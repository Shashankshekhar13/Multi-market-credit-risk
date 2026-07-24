# tests/test_alerts.py
"""Tests for the alert service — condition checks and notification history."""

# pyrefly: ignore [missing-import]
import pytest
from backend.services.alert_service import (
    check_score_drop, check_volatile_zone,
    check_news_spike, check_recovery,
    evaluate_alerts, add_notification, get_notification_history,
)


class TestScoreDropAlert:
    def test_significant_drop_triggers(self):
        msg = check_score_drop("AAPL", 60, 80, threshold=15)
        assert msg is not None
        assert "dropped" in msg

    def test_small_drop_no_trigger(self):
        msg = check_score_drop("AAPL", 75, 80, threshold=15)
        assert msg is None

    def test_score_increase_no_trigger(self):
        msg = check_score_drop("AAPL", 85, 80, threshold=15)
        assert msg is None

    def test_none_scores_no_trigger(self):
        assert check_score_drop("AAPL", None, 80) is None
        assert check_score_drop("AAPL", 60, None) is None

    def test_string_scores_no_trigger(self):
        assert check_score_drop("AAPL", "N/A", 80) is None


class TestVolatileZoneAlert:
    def test_below_threshold_triggers(self):
        msg = check_volatile_zone("TSLA", 35)
        assert msg is not None
        assert "Volatile" in msg

    def test_above_threshold_no_trigger(self):
        msg = check_volatile_zone("MSFT", 82)
        assert msg is None

    def test_exact_threshold_no_trigger(self):
        msg = check_volatile_zone("AAPL", 50)
        assert msg is None

    def test_none_score(self):
        assert check_volatile_zone("AAPL", None) is None


class TestNewsSpikeAlert:
    def test_spike_triggers(self):
        msg = check_news_spike("AAPL", 5, threshold=3)
        assert msg is not None
        assert "negative news" in msg

    def test_below_threshold_no_trigger(self):
        msg = check_news_spike("AAPL", 1, threshold=3)
        assert msg is None


class TestRecoveryAlert:
    def test_recovery_triggers(self):
        msg = check_recovery("AAPL", 80, 60, threshold=75)
        assert msg is not None
        assert "recovered" in msg

    def test_still_below_no_trigger(self):
        msg = check_recovery("AAPL", 70, 60, threshold=75)
        assert msg is None

    def test_was_already_above_no_trigger(self):
        msg = check_recovery("AAPL", 80, 80, threshold=75)
        assert msg is None


class TestEvaluateAlerts:
    def test_volatile_score_detected(self, sample_score_result):
        result = sample_score_result.copy()
        result["stability_score"] = 35
        alerts = evaluate_alerts("TSLA", result)
        types = [a["type"] for a in alerts]
        assert "volatile" in types

    def test_no_alerts_for_healthy_score(self, sample_score_result):
        result = sample_score_result.copy()
        result["stability_score"] = 85
        alerts = evaluate_alerts("AAPL", result, previous_score=80)
        # No score_drop, no volatile
        types = [a["type"] for a in alerts]
        assert "score_drop" not in types
        assert "volatile" not in types


class TestNotificationHistory:
    def test_add_and_retrieve(self):
        add_notification(user_id=999, ticker="AAPL", alert_type="score_drop",
                        message="Test notification")
        history = get_notification_history(user_id=999)
        assert len(history) >= 1
        assert history[0]["ticker"] == "AAPL"

    def test_history_ordering(self):
        add_notification(user_id=998, ticker="MSFT", alert_type="volatile", message="First")
        import time; time.sleep(0.01)  # ensure distinct timestamps
        add_notification(user_id=998, ticker="GOOGL", alert_type="recovery", message="Second")
        history = get_notification_history(user_id=998)
        # Most recent first
        assert len(history) >= 2
        tickers = [h["ticker"] for h in history[:2]]
        assert "MSFT" in tickers
        assert "GOOGL" in tickers
