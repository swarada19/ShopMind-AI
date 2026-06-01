"""
app/schemas/watchlist.py

Pydantic schemas for watchlist CRUD operations.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WatchlistItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    product_title: str
    product_url: str | None
    product_query: str
    current_price: float | None
    target_price: float | None
    is_active: bool
    last_checked_price: float | None
    alert_sent_count: int
    created_at: datetime


class WatchlistUpdateRequest(BaseModel):
    target_price: float | None = Field(None, gt=0)
    is_active: bool | None = None
