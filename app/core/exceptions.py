"""
app/core/exceptions.py

Domain-specific exceptions for ShopMind AI.

Using custom exceptions instead of generic ones gives two benefits:
1. Callers can catch specific failure types and handle them differently.
2. Error messages become self-documenting — the exception class name
   tells you exactly what went wrong.
"""


class ShopMindError(Exception):
    """Base exception. Catch this to handle any ShopMind-specific error."""


class UserNotFoundError(ShopMindError):
    """Raised when a user_id doesn't exist in the database."""


class ProductNotFoundError(ShopMindError):
    """Raised when a product_id doesn't exist in the database."""


class WatchlistError(ShopMindError):
    """Raised when a watchlist operation fails (e.g., duplicate entry)."""


class LLMError(ShopMindError):
    """Raised when an LLM call (Groq) fails or returns unexpected output."""


class SearchError(ShopMindError):
    """Raised when a SerpAPI call fails."""


class AlertError(ShopMindError):
    """Raised when a Twilio WhatsApp alert cannot be sent."""


class PreferenceError(ShopMindError):
    """Raised when user preference operations fail."""
