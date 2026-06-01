"""
app/tools/mock_data_tool.py

Mock product search — returns realistic data without calling SerpAPI.

This is the dev-mode fallback used when:
- USE_MOCK_DATA=True in settings (auto-set when API keys are placeholders)
- Running tests

The search function does keyword matching against mock_data/products.json
and returns ranked results. Not a real search engine, but good enough to
demonstrate the full agent pipeline end-to-end.
"""

import json
import logging
from pathlib import Path

from app.schemas.product import ProductResult

logger = logging.getLogger(__name__)

_MOCK_DATA_PATH = Path(__file__).parent.parent.parent / "mock_data" / "products.json"
_mock_products: list[dict] | None = None


def _load_mock_data() -> list[dict]:
    """Load and cache mock products from disk."""
    global _mock_products
    if _mock_products is None:
        with open(_MOCK_DATA_PATH) as f:
            _mock_products = json.load(f)
        logger.debug("Loaded %d mock products from disk", len(_mock_products))
    return _mock_products


def mock_search_products(
    query: str,
    budget: float | None = None,
    max_results: int = 10,
) -> list[ProductResult]:
    """
    Search mock products by keyword matching.

    Scoring (simple, no LLM):
    - Title match: 3 pts per keyword found
    - Brand match: 5 pts if brand keyword matches
    - Category match: 4 pts if category keyword matches
    - Budget fit: only return products within budget (if set)

    Args:
        query: The natural language product query.
        budget: Optional maximum price filter.
        max_results: Maximum number of products to return.

    Returns:
        List of ProductResult sorted by relevance score (descending).
    """
    products = _load_mock_data()
    query_lower = query.lower()
    keywords = query_lower.split()

    scored: list[tuple[int, dict]] = []

    for product in products:
        score = 0
        title_lower = product["title"].lower()
        brand_lower = (product.get("brand") or "").lower()
        category_lower = (product.get("category") or "").lower()

        for kw in keywords:
            if kw in title_lower:
                score += 3
            if kw in brand_lower:
                score += 5
            if kw in category_lower:
                score += 4

        # Skip if score is too low (not relevant at all)
        if score == 0:
            continue

        # Budget filter
        price = product.get("price")
        if budget and price and price > budget:
            continue

        scored.append((score, product))

    # Sort by relevance score descending, then by rating as tiebreaker
    scored.sort(key=lambda x: (x[0], x[1].get("rating", 0)), reverse=True)

    results = []
    for _, product in scored[:max_results]:
        results.append(
            ProductResult(
                id=product["id"],
                title=product["title"],
                price=product.get("price"),
                original_price=product.get("original_price"),
                currency=product.get("currency", "USD"),
                rating=product.get("rating"),
                review_count=product.get("review_count"),
                brand=product.get("brand"),
                category=product.get("category"),
                url=product.get("url"),
                image_url=product.get("image_url"),
                source=product.get("source", "mock"),
                features=product.get("features", []),
            )
        )

    logger.debug("Mock search for '%s' returned %d results", query, len(results))
    return results
