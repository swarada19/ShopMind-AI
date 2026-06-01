"""
app/schemas/search.py

Pydantic schemas for the /search endpoint — the primary API surface.
"""

from pydantic import BaseModel, Field

from app.schemas.product import ScoredProduct


class SearchRequest(BaseModel):
    user_id: str = Field(..., description="ID of the user performing the search")
    query: str = Field(..., min_length=3, max_length=500, description="Natural language product query")

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "user-123",
                "query": "best wireless headphones under $100",
            }
        }
    }


class SearchResponse(BaseModel):
    user_id: str
    raw_query: str
    product_query: str
    intent: str
    recommendations: list[ScoredProduct]
    cache_hit: bool = False
    results_count: int = 0
    session_id: str
    error: str | None = None

    def model_post_init(self, __context: object) -> None:
        object.__setattr__(self, "results_count", len(self.recommendations))


class WatchRequest(BaseModel):
    user_id: str = Field(..., description="ID of the user")
    query: str = Field(..., min_length=3, max_length=500)
    product_title: str = Field(..., min_length=1, max_length=500)
    product_url: str | None = None
    target_price: float | None = Field(None, gt=0)

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "user-123",
                "query": "Sony WH-1000XM5",
                "product_title": "Sony WH-1000XM5 Wireless Headphones",
                "product_url": "https://www.amazon.com/dp/B09XS7JWHH",
                "target_price": 249.99,
            }
        }
    }


class WatchResponse(BaseModel):
    watchlist_item_id: str
    product_title: str
    target_price: float | None
    message: str
