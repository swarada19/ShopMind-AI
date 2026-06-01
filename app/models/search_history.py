"""
app/models/search_history.py

Search history — records every query a user makes.

This serves two purposes:
1. The Preference Agent reads recent searches to personalise future results.
2. The frontend can show users their search history.
"""

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class SearchHistory(Base, TimestampMixin):
    __tablename__ = "search_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    raw_query: Mapped[str] = mapped_column(String(500), nullable=False)
    product_query: Mapped[str | None] = mapped_column(String(500), nullable=True)
    intent: Mapped[str | None] = mapped_column(String(50), nullable=True)
    results_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Store top recommendation IDs for reference
    result_snapshot: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="search_history")

    def __repr__(self) -> str:
        return f"<SearchHistory user={self.user_id} query={self.raw_query[:40]}>"
