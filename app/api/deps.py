"""
app/api/deps.py

FastAPI reusable dependencies injected into route handlers via Depends().

get_db is imported directly from app.core.database rather than re-defined
here. A single source of truth means test overrides work correctly:
    app.dependency_overrides[get_db] = override_get_db
applies everywhere the function is used, regardless of which module imports it.
"""

from fastapi import HTTPException, status

# Single get_db used across the entire app — routes import from here.
from app.core.database import get_db  # noqa: F401  (re-exported for route imports)
from app.core.exceptions import UserNotFoundError


async def get_current_user(user_id: str, db):
    """Validate user_id exists. In production this would validate a JWT."""
    try:
        from app.services.user_service import get_user_by_id
        return await get_user_by_id(db, user_id)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found. Create one via POST /users",
        )
