"""
app/models/user.py

User model. For this portfolio project, auth is intentionally kept simple:
users are identified by a unique ID. In production you would add
password hashing, JWT tokens, and OAuth providers.
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Relationships
    preferences: Mapped["UserPreference"] = relationship(
        "UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    watchlist: Mapped[list["WatchlistItem"]] = relationship(
        "WatchlistItem", back_populates="user", cascade="all, delete-orphan"
    )
    search_history: Mapped[list["SearchHistory"]] = relationship(
        "SearchHistory", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
