"""
app/tools/serp_tool.py

SerpAPI Google Shopping integration.

SerpAPI is a paid service that returns Google Shopping results in a clean
JSON format. We use it to find real-time product prices and availability.

Architecture decision: SerpAPI is wrapped in a function, not a LangChain Tool.
Reason: LangChain Tools add overhead for tool calling / ReAct loops that we
don't need here. The Product Intelligence Agent calls this function directly
as part of a deterministic node (not an autonomous agent loop).
"""

import logging

from app.core.config import settings
from app.core.exceptions import SearchError
from app.schemas.product import ProductResult

logger = logging.getLogger(__name__)


def search_google_shopping(
    query: str,
    budget: float | None = None,
    max_results: int = 10,
) -> list[ProductResult]:
    """
    Search Google Shopping via SerpAPI.

    Args:
        query: Product search query string.
        budget: Optional max price filter applied client-side.
        max_results: Maximum number of results to return.

    Returns:
        List of ProductResult parsed from SerpAPI response.

    Raises:
        SearchError: If the SerpAPI call fails.
    """
    try:
        from serpapi import GoogleSearch  # type: ignore[import]
    except ImportError as e:
        raise SearchError("google-search-results package not installed") from e

    try:
        params = {
            "engine": "google_shopping",
            "q": query,
            "api_key": settings.SERP_API_KEY,
            "num": max_results * 2,  # Over-fetch to allow budget filtering
            "gl": "us",
            "hl": "en",
        }

        logger.info("Calling SerpAPI for query: '%s'", query)
        search = GoogleSearch(params)
        data = search.get_dict()

        shopping_results = data.get("shopping_results", [])
        if not shopping_results:
            logger.warning("SerpAPI returned no results for query: '%s'", query)
            return []

        products = []
        for item in shopping_results:
            price = _parse_price(item.get("price"))
            original_price = _parse_price(item.get("old_price"))

            # Apply budget filter
            if budget and price and price > budget:
                continue

            products.append(
                ProductResult(
                    id=f"serp_{item.get('position', 0)}_{hash(item.get('title', ''))}"[:36],
                    title=item.get("title", "Unknown Product"),
                    price=price,
                    original_price=original_price,
                    currency="USD",
                    rating=float(item["rating"]) if item.get("rating") else None,
                    review_count=_parse_review_count(item.get("reviews")),
                    brand=item.get("source"),
                    category=None,
                    url=item.get("link"),
                    image_url=item.get("thumbnail"),
                    source="serpapi",
                    features=[],
                )
            )

            if len(products) >= max_results:
                break

        logger.info("SerpAPI returned %d results for '%s'", len(products), query)
        return products

    except SearchError:
        raise
    except Exception as e:
        logger.error("SerpAPI call failed: %s", str(e))
        raise SearchError(f"SerpAPI search failed: {e}") from e


def _parse_price(price_str: str | None) -> float | None:
    """Parse SerpAPI price string like '$299.99' to float."""
    if not price_str:
        return None
    try:
        cleaned = price_str.replace("$", "").replace(",", "").strip()
        return float(cleaned)
    except (ValueError, AttributeError):
        return None


def _parse_review_count(reviews_str: str | None) -> int | None:
    """Parse SerpAPI review string like '(1,234)' to int."""
    if not reviews_str:
        return None
    try:
        cleaned = str(reviews_str).replace(",", "").replace("(", "").replace(")", "").strip()
        return int(cleaned)
    except (ValueError, AttributeError):
        return None
