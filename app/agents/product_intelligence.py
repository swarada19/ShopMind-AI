"""
app/agents/product_intelligence.py

Product Intelligence Agent — fetches, validates, and enriches product data.

Responsibilities:
1. Check PostgreSQL cache — if results for this query are fresh, return them.
2. Fetch from SerpAPI (or mock data in dev mode) if cache is stale/empty.
3. Calculate trust_score for each product.
4. Store new results in the cache.

Cache strategy (TTL):
  - Check if products with matching search_query exist in the DB.
  - If fetched_at is within PRODUCT_CACHE_TTL_HOURS, return cached results.
  - Otherwise, fetch fresh data, overwrite the cache, and return new results.

Trust Score:
  Measures how reliable a product listing is.
  Formula: trust_score = review_score × source_weight
  High trust = many reviews, high rating, from a known reliable source.
  Used downstream by the Recommendation Agent to filter noisy listings.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging_config import get_logger
from app.graph.state import GraphState
from app.models.product import Product
from app.schemas.product import ProductResult
from app.tools.mock_data_tool import mock_search_products
from app.tools.price_scorer import compute_trust_score
from app.tools.serp_tool import search_google_shopping

logger = get_logger(__name__)


async def product_intelligence_node(state: GraphState, db: AsyncSession) -> GraphState:
    """
    LangGraph node: fetch and enrich product data.

    Returns raw_products (list of dicts) and a cache_hit flag.
    """
    product_query = state.get("product_query") or state["raw_query"]
    prefs = state.get("user_preferences") or {}
    budget = prefs.get("max_budget")
    use_mock = state.get("use_mock", True) or settings.USE_MOCK_DATA

    logger.info("[ProductIntel] Fetching products for: '%s' | budget=%s", product_query, budget)

    # ── Step 1: Check cache ───────────────────────────────────────────────────
    cached = await _check_cache(db, product_query)
    if cached:
        logger.info("[ProductIntel] Cache HIT for '%s' (%d products)", product_query, len(cached))
        enriched = _enrich_products(cached)
        return {**state, "raw_products": enriched, "cache_hit": True}

    # ── Step 2: Fetch from source ─────────────────────────────────────────────
    try:
        if use_mock:
            products: list[ProductResult] = mock_search_products(
                query=product_query,
                budget=budget,
                max_results=settings.MAX_SEARCH_RESULTS,
            )
        else:
            products = search_google_shopping(
                query=product_query,
                budget=budget,
                max_results=settings.MAX_SEARCH_RESULTS,
            )
    except Exception as e:
        logger.error("[ProductIntel] Fetch failed: %s", str(e))
        # Graceful degradation: fall back to mock data
        logger.warning("[ProductIntel] Falling back to mock data after error")
        products = mock_search_products(product_query, budget, settings.MAX_SEARCH_RESULTS)

    if not products:
        logger.warning("[ProductIntel] No products found for '%s'", product_query)
        return {**state, "raw_products": [], "cache_hit": False}

    # ── Step 3: Compute trust scores + save to cache ──────────────────────────
    await _save_to_cache(db, product_query, products)

    enriched = _enrich_products([p.model_dump() for p in products])
    logger.info("[ProductIntel] Returning %d products for '%s'", len(enriched), product_query)
    return {**state, "raw_products": enriched, "cache_hit": False}


async def _check_cache(db: AsyncSession, query: str) -> list[dict] | None:
    """Return cached products if they exist and are within TTL."""
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.PRODUCT_CACHE_TTL_HOURS)

    result = await db.execute(
        select(Product)
        .where(Product.search_query == query)
        .where(Product.fetched_at >= cutoff)
        .order_by(Product.trust_score.desc().nullslast())
    )
    products = result.scalars().all()

    if not products:
        return None

    return [
        {
            "id": p.id,
            "title": p.title,
            "price": p.price,
            "original_price": p.original_price,
            "currency": p.currency,
            "rating": p.rating,
            "review_count": p.review_count,
            "brand": p.brand,
            "category": p.category,
            "url": p.url,
            "image_url": p.image_url,
            "source": p.source,
            "features": p.features,
            "trust_score": p.trust_score,
        }
        for p in products
    ]


async def _save_to_cache(
    db: AsyncSession, query: str, products: list[ProductResult]
) -> None:
    """Overwrite cached products for this query."""
    # Delete stale entries for this query
    await db.execute(delete(Product).where(Product.search_query == query))

    for product in products:
        trust = compute_trust_score(
            rating=product.rating,
            review_count=product.review_count,
            source=product.source,
        )
        db_product = Product(
            id=product.id[:36],
            external_id=product.id,
            title=product.title,
            price=product.price,
            original_price=product.original_price,
            currency=product.currency,
            rating=product.rating,
            review_count=product.review_count,
            brand=product.brand,
            category=product.category,
            url=product.url,
            image_url=product.image_url,
            source=product.source,
            features=product.features,
            trust_score=trust,
            search_query=query,
        )
        db.add(db_product)

    await db.flush()  # Write without committing — the outer transaction handles commit


def _enrich_products(products: list[dict]) -> list[dict]:
    """Add trust_score to products that don't already have one."""
    enriched = []
    for p in products:
        if not p.get("trust_score"):
            p["trust_score"] = compute_trust_score(
                rating=p.get("rating"),
                review_count=p.get("review_count"),
                source=p.get("source", "serpapi"),
            )
        enriched.append(p)
    return enriched
