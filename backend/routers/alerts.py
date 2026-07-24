# backend/routers/alerts.py
"""Alert management API endpoints — CRUD alert rules and notification history."""

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession
# pyrefly: ignore [missing-import]
from sqlalchemy import select, desc
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field
from typing import Optional
import logging

from backend.services.database import get_db
from backend.services.alert_service import (
    ALERT_TYPES, get_notification_history, add_notification,
)
from backend.models import UserAlertPreference
from backend.routers.auth import get_current_user, require_auth
from backend.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


# ─── Schemas ───

class CreateAlertRequest(BaseModel):
    ticker: str
    alert_type: str = Field(..., description="One of: score_drop, volatile, news_spike, recovery")
    threshold: Optional[float] = None
    channel: str = Field(default="in_app", description="Notification channel: in_app, email")


class AlertRuleResponse(BaseModel):
    id: int
    ticker: str
    alert_type: str
    threshold: Optional[float] = None
    channel: str
    is_active: bool


# ─── Endpoints ───

@router.get("/types")
async def get_alert_types():
    """Get available alert types and their descriptions."""
    return {"alert_types": ALERT_TYPES}


@router.get("")
async def list_alerts(
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's alert rules."""
    try:
        stmt = (
            select(UserAlertPreference)
            .where(UserAlertPreference.user_id == user.id)
            .order_by(desc(UserAlertPreference.created_at))
        )
        result = await db.execute(stmt)
        alerts = result.scalars().all()

        return {
            "alerts": [
                {
                    "id": a.id,
                    "ticker": a.ticker,
                    "alert_type": a.alert_type,
                    "threshold": a.threshold,
                    "channel": a.channel,
                    "is_active": a.is_active,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in alerts
            ],
            "count": len(alerts),
        }
    except Exception as e:
        logger.error(f"Error listing alerts: {e}")
        return {"alerts": [], "count": 0, "error": "Database unavailable"}


@router.post("", response_model=AlertRuleResponse)
async def create_alert(
    request: CreateAlertRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Create a new alert rule."""
    if request.alert_type not in ALERT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid alert type. Must be one of: {', '.join(ALERT_TYPES.keys())}",
        )

    try:
        # Use default threshold if not provided
        threshold = request.threshold
        if threshold is None:
            threshold = ALERT_TYPES[request.alert_type]["default_threshold"]

        alert = UserAlertPreference(
            user_id=user.id,
            ticker=request.ticker.upper(),
            alert_type=request.alert_type,
            threshold=threshold,
            channel=request.channel,
        )
        db.add(alert)
        await db.commit()
        await db.refresh(alert)

        logger.info(f"Alert created: {request.alert_type} for {request.ticker} (user: {user.email})")

        return AlertRuleResponse(
            id=alert.id,
            ticker=alert.ticker,
            alert_type=alert.alert_type,
            threshold=alert.threshold,
            channel=alert.channel,
            is_active=alert.is_active,
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to create alert. Database may be unavailable.")


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: int,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Delete an alert rule."""
    try:
        stmt = select(UserAlertPreference).where(
            UserAlertPreference.id == alert_id,
            UserAlertPreference.user_id == user.id,
        )
        result = await db.execute(stmt)
        alert = result.scalar_one_or_none()

        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found.")

        await db.delete(alert)
        await db.commit()

        return {"message": f"Alert #{alert_id} deleted."}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete alert.")


@router.patch("/{alert_id}/toggle")
async def toggle_alert(
    alert_id: int,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Toggle an alert rule active/inactive."""
    try:
        stmt = select(UserAlertPreference).where(
            UserAlertPreference.id == alert_id,
            UserAlertPreference.user_id == user.id,
        )
        result = await db.execute(stmt)
        alert = result.scalar_one_or_none()

        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found.")

        alert.is_active = not alert.is_active
        await db.commit()

        status = "activated" if alert.is_active else "deactivated"
        return {"message": f"Alert #{alert_id} {status}.", "is_active": alert.is_active}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to toggle alert.")


@router.get("/history")
async def get_alert_history(
    limit: int = 50,
    user: User = Depends(require_auth),
):
    """Get the user's notification history."""
    history = get_notification_history(user_id=user.id, limit=limit)
    return {"notifications": history, "count": len(history)}
