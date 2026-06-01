"""
app/api/routes/users.py

User management endpoints.

POST /users             — Create a new user
GET  /users/{user_id}   — Get user by ID
PUT  /users/{user_id}/preferences  — Update preferences
GET  /users/{user_id}/preferences  — Get preferences
GET  /users/{user_id}/history      — Search history
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.exceptions import UserNotFoundError
from app.models.search_history import SearchHistory
from app.schemas.user import PreferencesResponse, PreferencesUpsert, UserCreate, UserResponse
from app.services.user_service import (
    create_user,
    get_preferences,
    get_user_by_id,
    upsert_preferences,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_new_user(data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Create a new user account."""
    user = await create_user(db, data)
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve a user by ID."""
    try:
        return await get_user_by_id(db, user_id)
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/{user_id}/preferences", response_model=PreferencesResponse)
async def update_preferences(
    user_id: str,
    data: PreferencesUpsert,
    db: AsyncSession = Depends(get_db),
):
    """Create or update user preferences."""
    # Verify user exists
    try:
        await get_user_by_id(db, user_id)
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    prefs = await upsert_preferences(db, user_id, data)
    return prefs


@router.get("/{user_id}/preferences", response_model=PreferencesResponse | None)
async def get_user_preferences(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get user preferences."""
    return await get_preferences(db, user_id)


@router.get("/{user_id}/history")
async def get_search_history(
    user_id: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Return the user's last N search queries."""
    result = await db.execute(
        select(SearchHistory)
        .where(SearchHistory.user_id == user_id)
        .order_by(SearchHistory.created_at.desc())
        .limit(limit)
    )
    history = result.scalars().all()
    return [
        {
            "id": h.id,
            "query": h.raw_query,
            "intent": h.intent,
            "results_count": h.results_count,
            "created_at": h.created_at.isoformat(),
        }
        for h in history
    ]
