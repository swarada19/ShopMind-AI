"""
app/api/routes/watchlist.py

Watchlist CRUD endpoints.

GET    /watchlist/{user_id}          — List all watchlist items
PATCH  /watchlist/{user_id}/{item_id} — Update target price or active status
DELETE /watchlist/{user_id}/{item_id} — Remove from watchlist
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.exceptions import WatchlistError
from app.schemas.watchlist import WatchlistItemResponse, WatchlistUpdateRequest
from app.services.watchlist_service import (
    delete_watchlist_item,
    get_user_watchlist,
    get_watchlist_item,
    update_watchlist_item,
)

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])


@router.get("/{user_id}", response_model=list[WatchlistItemResponse])
async def list_watchlist(
    user_id: str,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Return the user's watchlist items."""
    return await get_user_watchlist(db, user_id, active_only=active_only)


@router.get("/{user_id}/{item_id}", response_model=WatchlistItemResponse)
async def get_item(
    user_id: str,
    item_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific watchlist item."""
    try:
        return await get_watchlist_item(db, item_id, user_id)
    except WatchlistError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{user_id}/{item_id}", response_model=WatchlistItemResponse)
async def update_item(
    user_id: str,
    item_id: str,
    data: WatchlistUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a watchlist item's target price or active status."""
    try:
        return await update_watchlist_item(db, item_id, user_id, data)
    except WatchlistError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{user_id}/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    user_id: str,
    item_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Remove a product from the watchlist."""
    try:
        await delete_watchlist_item(db, item_id, user_id)
    except WatchlistError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
