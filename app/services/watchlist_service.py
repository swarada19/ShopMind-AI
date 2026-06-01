"""
app/services/watchlist_service.py

Database operations for the WatchlistItem model.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UserNotFoundError, WatchlistError
from app.models.watchlist import WatchlistItem
from app.schemas.watchlist import WatchlistUpdateRequest

logger = logging.getLogger(__name__)


async def get_user_watchlist(
    db: AsyncSession, user_id: str, active_only: bool = True
) -> list[WatchlistItem]:
    query = select(WatchlistItem).where(WatchlistItem.user_id == user_id)
    if active_only:
        query = query.where(WatchlistItem.is_active == True)  # noqa: E712
    query = query.order_by(WatchlistItem.created_at.desc())

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_watchlist_item(db: AsyncSession, item_id: str, user_id: str) -> WatchlistItem:
    result = await db.execute(
        select(WatchlistItem)
        .where(WatchlistItem.id == item_id)
        .where(WatchlistItem.user_id == user_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise WatchlistError(f"Watchlist item {item_id} not found")
    return item


async def update_watchlist_item(
    db: AsyncSession, item_id: str, user_id: str, data: WatchlistUpdateRequest
) -> WatchlistItem:
    item = await get_watchlist_item(db, item_id, user_id)
    if data.target_price is not None:
        item.target_price = data.target_price
    if data.is_active is not None:
        item.is_active = data.is_active
    await db.flush()
    return item


async def delete_watchlist_item(db: AsyncSession, item_id: str, user_id: str) -> None:
    item = await get_watchlist_item(db, item_id, user_id)
    await db.delete(item)
    await db.flush()
    logger.info("Deleted watchlist item %s for user %s", item_id, user_id)
