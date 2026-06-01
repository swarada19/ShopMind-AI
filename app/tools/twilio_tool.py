"""
app/tools/twilio_tool.py

Twilio WhatsApp alert integration.

Sends a WhatsApp message to a user when their watchlist item hits the
target price. Uses the Twilio Sandbox for development
(no WhatsApp Business approval needed for testing).

Production setup requires:
1. A verified Twilio phone number with WhatsApp capability
2. WhatsApp Business API approval from Meta
"""

import logging

from app.core.config import settings
from app.core.exceptions import AlertError

logger = logging.getLogger(__name__)


def send_whatsapp_alert(
    to_phone: str,
    product_title: str,
    current_price: float,
    target_price: float,
    product_url: str | None = None,
) -> str | None:
    """
    Send a WhatsApp price-drop alert via Twilio.

    Args:
        to_phone: Recipient phone in E.164 format (e.g. "+1234567890")
        product_title: Name of the product.
        current_price: The price that triggered the alert.
        target_price: The user's target price.
        product_url: Optional link to the product listing.

    Returns:
        Twilio message SID on success, or None in mock mode.

    Raises:
        AlertError: If the Twilio call fails.
    """
    if settings.USE_MOCK_DATA:
        logger.info(
            "[MOCK] WhatsApp alert: '%s' now $%.2f (target $%.2f) → %s",
            product_title[:50],
            current_price,
            target_price,
            to_phone,
        )
        return "mock_message_sid"

    try:
        from twilio.rest import Client  # type: ignore[import]
    except ImportError as e:
        raise AlertError("twilio package not installed") from e

    body = _build_message(product_title, current_price, target_price, product_url)
    to_number = f"whatsapp:{to_phone}" if not to_phone.startswith("whatsapp:") else to_phone

    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=body,
            from_=settings.TWILIO_WHATSAPP_FROM,
            to=to_number,
        )
        logger.info(
            "WhatsApp alert sent to %s | SID=%s | product='%s'",
            to_phone,
            message.sid,
            product_title[:40],
        )
        return message.sid

    except Exception as e:
        logger.error("Twilio alert failed: %s", str(e))
        raise AlertError(f"WhatsApp alert failed: {e}") from e


def _build_message(
    product_title: str,
    current_price: float,
    target_price: float,
    product_url: str | None,
) -> str:
    """Build the WhatsApp message body."""
    lines = [
        "🛍️ *ShopMind AI Price Alert!*",
        "",
        f"*{product_title}*",
        f"💰 Current price: *${current_price:.2f}*",
        f"🎯 Your target: ${target_price:.2f}",
        f"✅ It's now ${current_price:.2f} — ${target_price - current_price:.2f} below your target!",
    ]
    if product_url:
        lines.extend(["", f"🔗 {product_url}"])
    lines.extend(["", "_Sent by ShopMind AI • Reply STOP to unsubscribe_"])
    return "\n".join(lines)
