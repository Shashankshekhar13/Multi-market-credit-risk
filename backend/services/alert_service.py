# backend/services/alert_service.py
"""Alert service — checks conditions and sends notifications."""

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


# ─── Alert Types ───

ALERT_TYPES = {
    "score_drop": {
        "label": "Score Drop",
        "description": "Triggers when stability score drops by more than a threshold",
        "default_threshold": 15,
    },
    "volatile": {
        "label": "Volatile Zone",
        "description": "Triggers when score enters volatile zone (below 50)",
        "default_threshold": 50,
    },
    "news_spike": {
        "label": "Negative News Spike",
        "description": "Triggers when negative news events exceed threshold in 24h",
        "default_threshold": 3,
    },
    "recovery": {
        "label": "Recovery",
        "description": "Triggers when score recovers above stable threshold",
        "default_threshold": 75,
    },
}


# ─── Notification History (in-memory for stateless mode) ───

_notification_history = []
MAX_HISTORY = 200


def get_notification_history(user_id: Optional[int] = None, limit: int = 50) -> list:
    """Get recent notification history."""
    history = _notification_history
    if user_id:
        history = [n for n in history if n.get("user_id") == user_id]
    return sorted(history, key=lambda x: x["timestamp"], reverse=True)[:limit]


def add_notification(user_id: int, ticker: str, alert_type: str, message: str,
                     channel: str = "in_app"):
    """Add a notification to history."""
    notification = {
        "id": len(_notification_history) + 1,
        "user_id": user_id,
        "ticker": ticker.upper(),
        "alert_type": alert_type,
        "message": message,
        "channel": channel,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "read": False,
    }
    _notification_history.append(notification)

    # Trim old notifications
    if len(_notification_history) > MAX_HISTORY:
        _notification_history.pop(0)

    logger.info(f"[Alert] {alert_type} for {ticker}: {message}")
    return notification


# ─── Alert Condition Checks ───

def check_score_drop(ticker: str, new_score: float, previous_score: float,
                     threshold: float = 15) -> Optional[str]:
    """Check if score dropped by more than threshold."""
    if previous_score is None or new_score is None:
        return None
    if isinstance(new_score, str) or isinstance(previous_score, str):
        return None

    drop = previous_score - new_score
    if drop >= threshold:
        return f"⚠️ {ticker} score dropped from {previous_score:.0f} to {new_score:.0f} (−{drop:.0f} points)"
    return None


def check_volatile_zone(ticker: str, score: float, threshold: float = 50) -> Optional[str]:
    """Check if score entered volatile zone."""
    if score is None or isinstance(score, str):
        return None
    if score < threshold:
        return f"🔴 {ticker} is now in Volatile zone (score: {score:.0f})"
    return None


def check_news_spike(ticker: str, negative_count: int, threshold: int = 3) -> Optional[str]:
    """Check for negative news spike."""
    if negative_count >= threshold:
        return f"📰 {negative_count} negative news events detected for {ticker}"
    return None


def check_recovery(ticker: str, new_score: float, previous_score: float,
                   threshold: float = 75) -> Optional[str]:
    """Check if score recovered above stable threshold."""
    if new_score is None or isinstance(new_score, str):
        return None
    if previous_score is not None and isinstance(previous_score, (int, float)):
        if previous_score < threshold and new_score >= threshold:
            return f"✅ {ticker} has recovered to Stable (score: {new_score:.0f})"
    return None


def evaluate_alerts(ticker: str, score_result: dict, previous_score: float = None,
                    alert_preferences: list = None) -> list:
    """Evaluate all alert conditions for a ticker and return triggered alerts.

    Args:
        ticker: Stock ticker symbol
        score_result: Current score result dict from scoring engine
        previous_score: Previous stability score (if known)
        alert_preferences: User's alert preference configs

    Returns:
        List of triggered alert messages
    """
    triggered = []
    current_score = score_result.get("stability_score")
    negative_count = 0

    # Count negative news events from explanation
    explanation = score_result.get("explanation", [])
    for item in explanation:
        if item.get("feature") == "negative_event_count":
            negative_count = int(item.get("value", 0))
            break

    # Default checks (no user prefs needed)
    checks = [
        ("score_drop", check_score_drop(ticker, current_score, previous_score)),
        ("volatile", check_volatile_zone(ticker, current_score)),
        ("news_spike", check_news_spike(ticker, negative_count)),
        ("recovery", check_recovery(ticker, current_score, previous_score)),
    ]

    for alert_type, message in checks:
        if message:
            triggered.append({
                "type": alert_type,
                "ticker": ticker,
                "message": message,
                "score": current_score,
            })

    return triggered


# ─── Email Sending (SMTP fallback) ───

def send_email_notification(to_email: str, subject: str, body: str) -> bool:
    """Send email notification via SMTP. Returns True on success."""
    try:
        import smtplib
        from email.mime.text import MIMEText
        import os

        smtp_host = os.getenv("SMTP_HOST", "")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_pass = os.getenv("SMTP_PASS", "")

        if not smtp_host or not smtp_user:
            logger.info(f"[Alert] Email skipped (SMTP not configured): {subject}")
            return False

        msg = MIMEText(body, "plain")
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = to_email

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        logger.info(f"[Alert] Email sent to {to_email}: {subject}")
        return True

    except Exception as e:
        logger.error(f"[Alert] Email failed: {e}")
        return False
