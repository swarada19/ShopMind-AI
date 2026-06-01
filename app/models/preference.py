"""
app/models/preference.py

User preference model — one-to-one with User.

JSONB vs JSON:
  The ORM uses SQLAlchemy's generic `JSON` type, which maps to:
    - JSONB in PostgreSQL (via the migration in migrations/versions/)
    - TEXT with JSON serialisation in SQLite (used by tests)
  Do not import `sqlalchemy.dialects.postgresql.JSONB` in model files —
  that type is PostgreSQL-only and breaks `create_all()` on SQLite.
"""

from sqlalchemy import Float, ForeignKey, JSON, String, Text
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
    preferred_brands: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    preferred_categories: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="preferences")

    def __repr__(self) -> str:
        return f"<UserPreference user_id={self.user_id} budget={self.max_budget}>"
