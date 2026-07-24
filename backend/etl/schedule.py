# backend/etl/schedule.py
"""Prefect deployment schedules for automated data collection.

Schedules:
- US Market:    Daily at 5:00 PM ET (after market close) — 21:00 UTC
- India Market: Daily at 4:30 PM IST (after market close) — 11:00 UTC
- Macro Data:   Weekly on Sunday at 00:00 UTC

Usage:
    # Register deployments with Prefect
    python -m backend.etl.schedule

    # Or run manually
    python -m backend.etl.flows all
"""

import logging

logger = logging.getLogger(__name__)

try:
    from prefect.deployments import Deployment
    from prefect.server.schemas.schedules import CronSchedule
    PREFECT_AVAILABLE = True
except ImportError:
    PREFECT_AVAILABLE = False
    logger.warning("Prefect not installed. Schedules cannot be registered.")


def create_deployments():
    """Create Prefect deployments with cron schedules."""
    if not PREFECT_AVAILABLE:
        print("❌ Prefect is not installed. Install it with: pip install prefect")
        return

    from backend.etl.flows import (
        daily_us_collection_flow,
        daily_india_collection_flow,
        daily_full_collection_flow,
    )

    # US Market — Daily at 9:00 PM UTC (5:00 PM ET)
    us_deployment = Deployment.build_from_flow(
        flow=daily_us_collection_flow,
        name="daily-us-collection",
        schedule=CronSchedule(cron="0 21 * * 1-5", timezone="UTC"),
        tags=["production", "us-market"],
        description="Daily data collection for US-listed companies after market close.",
    )

    # India Market — Daily at 11:00 AM UTC (4:30 PM IST)
    india_deployment = Deployment.build_from_flow(
        flow=daily_india_collection_flow,
        name="daily-india-collection",
        schedule=CronSchedule(cron="0 11 * * 1-5", timezone="UTC"),
        tags=["production", "india-market"],
        description="Daily data collection for Indian-listed companies after market close.",
    )

    # Full Collection — Sunday at midnight UTC (for weekend catchup)
    full_deployment = Deployment.build_from_flow(
        flow=daily_full_collection_flow,
        name="weekly-full-collection",
        schedule=CronSchedule(cron="0 0 * * 0", timezone="UTC"),
        tags=["production", "all-markets"],
        description="Weekly full data collection for all markets.",
    )

    print("📋 Prefect Deployments:")
    print(f"  🇺🇸 US Market:    Mon-Fri at 9:00 PM UTC (5:00 PM ET)")
    print(f"  🇮🇳 India Market: Mon-Fri at 11:00 AM UTC (4:30 PM IST)")
    print(f"  🌍 Full Weekly:  Sunday at 00:00 UTC")
    print()

    us_deployment.apply()
    print("✅ US deployment registered")

    india_deployment.apply()
    print("✅ India deployment registered")

    full_deployment.apply()
    print("✅ Full weekly deployment registered")

    print("\n🎉 All deployments registered successfully!")
    print("Start the Prefect agent with: prefect agent start -q default")


if __name__ == "__main__":
    create_deployments()
