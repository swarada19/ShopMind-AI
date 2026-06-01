"""
app/models/alert_log.py

Audit trail for every WhatsApp alert sent.

This is important for:
- Debugging: know exactly what was sent, when, and to whom.
- Preventing duplicate alerts: check this table before sending.
- Analytics: track which watchlist items trigger the most alerts.
"""

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class AlertLog(Base, TimestampMixin):
    __tablename__ = "alert_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    watchlist_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("watchlist.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_title: Mapped[str] = mapped_column(String(500), nullable=False)
    triggered_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    message_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="sent", nullable=False)
    # Twilio message SID for reference
    twilio_sid: Mapped[str | None] = mapped_column(String(100), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<AlertLog user={self.user_id} "
            f"item={self.watchlist_item_id} status={self.status}>"
        )
