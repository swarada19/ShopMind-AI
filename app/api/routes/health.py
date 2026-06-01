"""
app/api/routes/health.py

Health check endpoints.

GET /health         — simple liveness check (is the process running?)
GET /health/ready   — readiness check (can it serve traffic? DB connected?)

These are used by Docker, Kubernetes, and load balancers to know whether
to route traffic to this instance. Always include them in production apps.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", summary="Liveness check")
async def health_check():
    """Returns 200 if the process is alive."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "env": settings.APP_ENV,
        "mock_mode": settings.USE_MOCK_DATA,
    }


@router.get("/ready", summary="Readiness check")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Returns 200 if the app can serve traffic (database is reachable)."""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
    }
