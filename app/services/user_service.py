"""
app/services/user_service.py

Database operations for User and UserPreference models.

Services are the data access layer. API routes call services;
services call the database. This separation keeps route handlers thin
and database logic testable in isolation.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UserNotFoundError
from app.models.preference import UserPreference
from app.models.user import User
from app.schemas.user import PreferencesUpsert, UserCreate

logger = logging.getLogger(__name__)


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    user = User(name=data.name, email=data.email, phone=data.phone)
    db.add(user)
    await db.flush()
    logger.info("Created user id=%s email=%s", user.id, user.email)
    return user


async def get_user_by_id(db: AsyncSession, user_id: str) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise UserNotFoundError(f"User {user_id} not found")
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def upsert_preferences(
    db: AsyncSession, user_id: str, data: PreferencesUpsert
) -> UserPreference:
    """Create or update user preferences (upsert pattern)."""
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == user_id)
    )
    prefs = result.scalar_one_or_none()

    if prefs:
        prefs.max_budget = data.max_budget
        prefs.currency = data.currency
        prefs.preferred_brands = data.preferred_brands
        prefs.preferred_categories = data.preferred_categories
        prefs.notes = data.notes
    else:
        prefs = UserPreference(
            user_id=user_id,
            max_budget=data.max_budget,
            currency=data.currency,
            preferred_brands=data.preferred_brands,
            preferred_categories=data.preferred_categories,
            notes=data.notes,
        )
        db.add(prefs)

    await db.flush()
    return prefs


async def get_preferences(db: AsyncSession, user_id: str) -> UserPreference | None:
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == user_id)
    )
    return result.scalar_one_or_none()
