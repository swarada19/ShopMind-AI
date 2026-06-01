"""
app/models/watchlist.py

Watchlist model — tracks products a user wants to monitor for price drops.

When a user says "alert me when this drops below $80", we create a WatchlistItem
with target_price=$80. The APScheduler job checks this table daily.
"""

from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class WatchlistItem(Base, TimestampMixin):
    __tablename__ = "watchlist"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # We store the product URL directly — the user may want to watch a
    # specific listing, not just a product category.
    product_title: Mapped[str] = mapped_column(String(500), nullable=False)
    product_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_query: Mapped[str] = mapped_column(String(500), nullable=False)
    current_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_checked_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    alert_sent_count: Mapped[int] = mapped_column(default=0, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="watchlist")

    def __repr__(self) -> str:
        return (
            f"<WatchlistItem id={self.id} "
            f"user={self.user_id} target={self.target_price}>"
        )
