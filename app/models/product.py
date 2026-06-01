"""
app/models/product.py

Product cache model.

Products are fetched from SerpAPI and stored here with a fetched_at timestamp.
The Product Intelligence Agent checks this table first (TTL cache pattern)
before calling SerpAPI, preventing redundant API calls and improving latency.

Why store in PostgreSQL and not Redis?
- PostgreSQL is already in the stack.
- Product data is richer than a simple key-value cache.
- We need to query across products (e.g., "find all cached Sony headphones").
- For this scale, PostgreSQL's performance is more than sufficient.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    # External identifier (from SerpAPI) — unique per source
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="serpapi", nullable=False)
    features: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    trust_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # The search query that produced this product — used for TTL cache lookup
    search_query: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Product id={self.id} title={self.title[:40]}>"
