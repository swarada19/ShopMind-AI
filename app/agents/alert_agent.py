"""
app/agents/alert_agent.py

Alert Agent — checks watchlist items and sends WhatsApp notifications.

This agent is NOT part of the user-facing search graph.
It's invoked exclusively by the APScheduler daily job.

Flow:
1. Load all active watchlist items from PostgreSQL.
2. For each item: fetch the current price (SerpAPI or mock).
3. If current_price <= target_price: send WhatsApp alert via Twilio.
4. Log the alert in the AlertLog table.
5. Update watchlist item with last_checked_price.

Deduplication:
  We check if an alert was already sent today for this item before sending.
  This prevents the user from receiving the same alert every day
  when a price stays low.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_logger
from app.models.alert_log import AlertLog
from app.models.user import User
from app.models.watchlist import WatchlistItem
from app.tools.mock_data_tool import mock_search_products
from app.tools.twilio_tool import send_whatsapp_alert

logger = get_logger(__name__)


async def run_alert_check(db: AsyncSession) -> dict:
    """
    Main entry point called by APScheduler.

    Returns a summary dict with alerts_sent, items_checked, errors.
    """
    logger.info("[AlertAgent] Starting price check run")
    summary = {"items_checked": 0, "alerts_sent": 0, "errors": 0}

    # Load all active watchlist items with their users
    result = await db.execute(
        select(WatchlistItem, User)
        .join(User, User.id == WatchlistItem.user_id)
        .where(WatchlistItem.is_active == True)  # noqa: E712
    )
    items = result.fetchall()

    if not items:
        logger.info("[AlertAgent] No active watchlist items. Exiting.")
        return summary

    logger.info("[AlertAgent] Checking %d watchlist items", len(items))

    for watchlist_item, user in items:
        summary["items_checked"] += 1
        try:
            await _check_and_alert(db, watchlist_item, user, summary)
        except Exception as e:
            logger.error(
                "[AlertAgent] Error checking item %s: %s",
                watchlist_item.id,
                str(e),
            )
            summary["errors"] += 1

    logger.info(
        "[AlertAgent] Run complete | checked=%d | sent=%d | errors=%d",
        summary["items_checked"],
        summary["alerts_sent"],
        summary["errors"],
    )
    return summary


async def _check_and_alert(
    db: AsyncSession,
    item: WatchlistItem,
    user: User,
    summary: dict,
) -> None:
    """Check a single watchlist item and send alert if price threshold is met."""

    # Get current price from mock data (or SerpAPI in production)
    current_price = _fetch_current_price(item.product_query, item.product_title)

    if current_price is None:
        logger.debug("[AlertAgent] No price found for '%s'", item.product_title[:50])
        return

    # Update last_checked_price
    item.last_checked_price = current_price

    # Check if target price is met
    if item.target_price and current_price > item.target_price:
        logger.debug(
            "[AlertAgent] Price $%.2f > target $%.2f for '%s' — no alert",
            current_price,
            item.target_price,
            item.product_title[:40],
        )
        return

    # Check for deduplication — did we already alert today?
    if await _already_alerted_today(db, item.id):
        logger.debug("[AlertAgent] Already alerted today for item %s", item.id)
        return

    # No phone? Can't send WhatsApp
    if not user.phone:
        logger.warning("[AlertAgent] User %s has no phone — cannot send alert", user.id)
        return

    # Send alert
    twilio_sid = send_whatsapp_alert(
        to_phone=user.phone,
        product_title=item.product_title,
        current_price=current_price,
        target_price=item.target_price or current_price,
        product_url=item.product_url,
    )

    # Log to AlertLog
    alert_log = AlertLog(
        user_id=user.id,
        watchlist_item_id=item.id,
        product_title=item.product_title,
        triggered_price=current_price,
        target_price=item.target_price,
        phone_number=user.phone,
        message_body=f"Price alert: {item.product_title} is now ${current_price:.2f}",
        status="sent",
        twilio_sid=twilio_sid,
    )
    db.add(alert_log)

    item.alert_sent_count = (item.alert_sent_count or 0) + 1
    summary["alerts_sent"] += 1

    logger.info(
        "[AlertAgent] Alert sent | user=%s | product='%s' | price=$%.2f",
        user.id,
        item.product_title[:40],
        current_price,
    )


def _fetch_current_price(query: str, title: str) -> float | None:
    """Fetch the current price for a watchlist item (synchronous — no I/O in mock mode)."""
    try:
        # In dev mode, use mock data. In production, this would call SerpAPI.
        results = mock_search_products(query=query, max_results=5)
        for product in results:
            if any(word in product.title.lower() for word in title.lower().split()[:3]):
                return product.price
        # Fallback: return the first result's price
        if results:
            return results[0].price
    except Exception as e:
        logger.error("[AlertAgent] Price fetch error: %s", str(e))
    return None


async def _already_alerted_today(db: AsyncSession, watchlist_item_id: str) -> bool:
    """Return True if an alert was already sent today for this watchlist item."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(AlertLog.id)
        .where(AlertLog.watchlist_item_id == watchlist_item_id)
        .where(AlertLog.created_at >= today_start)
        .limit(1)
    )
    return result.scalar_one_or_none() is not None
