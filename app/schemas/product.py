"""
app/schemas/product.py

Pydantic schemas for product data throughout the system.

ProductResult is the canonical shape that flows from the Product Intelligence
Agent through to the Recommendation Agent and out through the API.
"""

from pydantic import BaseModel, ConfigDict, Field


class ProductResult(BaseModel):
    """A single product returned by the Product Intelligence Agent."""

    id: str
    title: str
    price: float | None = None
    original_price: float | None = None
    currency: str = "USD"
    rating: float | None = Field(None, ge=0, le=5)
    review_count: int | None = Field(None, ge=0)
    brand: str | None = None
    category: str | None = None
    url: str | None = None
    image_url: str | None = None
    source: str = "serpapi"
    features: list[str] = Field(default_factory=list)
    trust_score: float | None = Field(None, ge=0, le=1)


class ScoredProduct(ProductResult):
    """A product enriched with scoring after the Recommendation Agent."""

    deal_score: float = Field(0.0, ge=0, le=1)
    review_score: float = Field(0.0, ge=0, le=1)
    relevance_score: float = Field(0.0, ge=0, le=1)
    final_score: float = Field(0.0, ge=0, le=1)
    rank: int = 0
    explanation: str = ""
    discount_pct: float | None = None


class ProductCacheEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    price: float | None
    rating: float | None
    review_count: int | None
    brand: str | None
    url: str | None
    trust_score: float | None
