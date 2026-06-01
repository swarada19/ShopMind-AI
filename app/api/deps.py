"""
app/api/deps.py

FastAPI reusable dependencies injected into route handlers via Depends().
"""

from collections.abc import AsyncGenerator

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UserNotFoundError


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for the duration of a request."""
    from app.core.database import _get_session_factory
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_user(
    user_id: str,
    db: AsyncSession,
):
    """Validate user_id exists. In production this would validate a JWT."""
    try:
        from app.services.user_service import get_user_by_id
        return await get_user_by_id(db, user_id)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found. Create one via POST /users",
        )
