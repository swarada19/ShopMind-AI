"""
app/models/__init__.py

Import all models here so that SQLAlchemy's metadata is populated
when alembic/create_tables runs. Without this, Alembic won't see your models.
"""

from app.models.alert_log import AlertLog
from app.models.preference import UserPreference
from app.models.product import Product
from app.models.search_history import SearchHistory
from app.models.user import User
from app.models.watchlist import WatchlistItem

__all__ = [
    "User",
    "UserPreference",
    "Product",
    "WatchlistItem",
    "SearchHistory",
    "AlertLog",
]
