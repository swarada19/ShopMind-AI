"""
app/schemas/user.py

Pydantic request/response models for User and UserPreference endpoints.

Note on Pydantic v2: use `model_config = ConfigDict(from_attributes=True)`
instead of `class Config: orm_mode = True` (the v1 pattern).
"""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str | None = Field(None, pattern=r"^\+?[\d\s\-]{7,20}$")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    phone: str | None


class PreferencesUpsert(BaseModel):
    max_budget: float | None = Field(None, gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    preferred_brands: list[str] = Field(default_factory=list)
    preferred_categories: list[str] = Field(default_factory=list)
    notes: str | None = None


class PreferencesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    max_budget: float | None
    currency: str
    preferred_brands: list[str]
    preferred_categories: list[str]
    notes: str | None
