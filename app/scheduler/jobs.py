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
  Production upgrade path: Celery + Redis + persistent job store.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _run_price_check_job() -> None:
    """
    The daily price check job.

    Uses get_async_session() — the correct way to acquire a DB session
    outside of FastAPI's dependency injection system. The old code used
    `async with AsyncSessionLocal() as db:` which crashed at runtime because
    AsyncSessionLocal is a function returning the factory, not the factory
    itself. get_async_session() is an explicit async context manager that
    handles acquire, commit, and rollback correctly.
    """
    from app.agents.alert_agent import run_alert_check
    from app.core.database import get_async_session

    logger.info("[Scheduler] Starting daily price check job")

    async with get_async_session() as db:
        summary = await run_alert_check(db)
        logger.info("[Scheduler] Price check complete: %s", summary)


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
        "[Scheduler] Started | price check scheduled at %02d:%02d UTC daily",
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
    Call via: POST /health/trigger-alerts (admin only in production).
    """
    if _scheduler:
        _scheduler.add_job(
            _run_price_check_job,
            id="manual_price_check",
            replace_existing=True,
        )
        logger.info("[Scheduler] Manual price check triggered")
