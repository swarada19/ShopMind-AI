"""
app/scheduler/jobs.py

APScheduler configuration and job definitions.

APScheduler runs background jobs on a schedule, independently of HTTP requests.
We use it for the daily price-check job that runs the Alert Agent.

Architecture note:
  The scheduler runs INSIDE the FastAPI process (in-process scheduling).
  Alternative: a separate worker process (Celery + Redis).
  We chose in-process because:
  - Simpler setup (no Redis needed)
  - Sufficient for a portfolio project
  - Easy to understand and explain
  Trade-off: if the FastAPI process restarts, in-flight jobs are lost.
  For production, move to Celery + Redis + persistent job store.
"""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _run_price_check_job() -> None:
    """
    The daily price check job.

    Creates a new DB session (outside the FastAPI request cycle),
    runs the Alert Agent, and logs the summary.
    """
    from app.agents.alert_agent import run_alert_check
    from app.core.database import AsyncSessionLocal

    logger.info("[Scheduler] Starting daily price check job")

    async with AsyncSessionLocal() as db:
        try:
            summary = await run_alert_check(db)
            await db.commit()
            logger.info("[Scheduler] Price check complete: %s", summary)
        except Exception as e:
            await db.rollback()
            logger.error("[Scheduler] Price check job failed: %s", str(e), exc_info=True)


def start_scheduler() -> None:
    """Start the APScheduler. Called on FastAPI startup."""
    global _scheduler

    _scheduler = AsyncIOScheduler(timezone="UTC")

    _scheduler.add_job(
        _run_price_check_job,
        trigger=CronTrigger(
            hour=settings.ALERT_SCHEDULE_HOUR,
            minute=settings.ALERT_SCHEDULE_MINUTE,
        ),
        id="daily_price_check",
        name="Daily Price Check & WhatsApp Alerts",
        replace_existing=True,
        misfire_grace_time=3600,  # Allow up to 1 hour late (e.g., server was down)
    )

    _scheduler.start()
    logger.info(
        "[Scheduler] Started | price check at %02d:%02d UTC daily",
        settings.ALERT_SCHEDULE_HOUR,
        settings.ALERT_SCHEDULE_MINUTE,
    )


def stop_scheduler() -> None:
    """Gracefully stop the scheduler. Called on FastAPI shutdown."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Stopped")


def trigger_price_check_now() -> None:
    """
    Manually trigger the price check job immediately.
    Useful for testing without waiting for the scheduled time.
    """
    if _scheduler:
        _scheduler.add_job(
            _run_price_check_job,
            id="manual_price_check",
            replace_existing=True,
        )
        logger.info("[Scheduler] Manual price check triggered")
