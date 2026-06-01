"""
app/models/preference.py

User preference model — one-to-one with User.

Stores a user's shopping preferences so the Preference Agent can personalise
every search without requiring them to repeat themselves.

JSONB columns (preferred_brands, preferred_categories) are used for list data
because they allow efficient querying and are more flexible than separate
junction tables for a portfolio project of this scale.
"""

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class UserPreference(Base, TimestampMixin):
    __tablename__ = "user_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    max_budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    preferred_brands: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    preferred_categories: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="preferences")

    def __repr__(self) -> str:
        return f"<UserPreference user_id={self.user_id} budget={self.max_budget}>"
