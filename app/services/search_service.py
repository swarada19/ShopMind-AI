"""
app/services/search_service.py

Orchestrates a full search by invoking the LangGraph and persisting the result.
This is the main "use case" service — it connects the API layer to the graph.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.graph.graph import get_compiled_graph
from app.graph.state import GraphState
from app.models.search_history import SearchHistory
from app.schemas.product import ScoredProduct
from app.schemas.search import SearchResponse, WatchResponse

logger = logging.getLogger(__name__)


async def execute_search(
    db: AsyncSession,
    user_id: str,
    raw_query: str,
) -> SearchResponse:
    """
    Run the full LangGraph search pipeline and return a SearchResponse.

    Steps:
    1. Build initial graph state.
    2. Invoke the graph (passes DB via LangGraph config).
    3. Persist search history.
    4. Return formatted response.
    """
    session_id = str(uuid.uuid4())

    initial_state: GraphState = {
        "user_id": user_id,
        "raw_query": raw_query,
        "session_id": session_id,
        "use_mock": settings.USE_MOCK_DATA,
        "intent": "",
        "product_query": "",
        "extracted_budget": None,
        "extracted_constraints": [],
        "user_preferences": None,
        "raw_products": [],
        "cache_hit": False,
        "recommendations": [],
        "watchlist_item_id": None,
        "error": None,
        "error_node": None,
    }

    # Pass DB session via LangGraph's configurable mechanism
    config = {"configurable": {"db": db}}

    logger.info(
        "[SearchService] Invoking graph | user=%s | query='%s' | session=%s",
        user_id, raw_query[:80], session_id,
    )

    graph = get_compiled_graph()
    final_state: GraphState = await graph.ainvoke(initial_state, config=config)

    # Parse recommendations
    recommendations = [
        ScoredProduct(**r) for r in (final_state.get("recommendations") or [])
    ]

    # Persist search history (best-effort — don't fail the request if this fails)
    try:
        history = SearchHistory(
            user_id=user_id,
            raw_query=raw_query,
            product_query=final_state.get("product_query") or raw_query,
            intent=final_state.get("intent"),
            results_count=len(recommendations),
            result_snapshot=[r.id for r in recommendations[:5]],
        )
        db.add(history)
        await db.flush()
    except Exception as e:
        logger.warning("[SearchService] Failed to save search history: %s", str(e))

    return SearchResponse(
        user_id=user_id,
        raw_query=raw_query,
        product_query=final_state.get("product_query") or raw_query,
        intent=final_state.get("intent") or "unknown",
        recommendations=recommendations,
        cache_hit=final_state.get("cache_hit", False),
        session_id=session_id,
        error=final_state.get("error"),
    )


async def execute_watch(
    db: AsyncSession,
    user_id: str,
    raw_query: str,
    product_title: str,
    product_url: str | None,
    target_price: float | None,
) -> WatchResponse:
    """Add a product to the user's watchlist via the graph."""
    from app.models.watchlist import WatchlistItem
    from app.models.base import generate_uuid

    item = WatchlistItem(
        id=generate_uuid(),
        user_id=user_id,
        product_title=product_title,
        product_url=product_url,
        product_query=raw_query,
        target_price=target_price,
        is_active=True,
    )
    db.add(item)
    await db.flush()

    logger.info(
        "[SearchService] Watchlist item created | id=%s | user=%s | product='%s'",
        item.id, user_id, product_title[:40],
    )

    return WatchResponse(
        watchlist_item_id=item.id,
        product_title=product_title,
        target_price=target_price,
        message=f"Watching '{product_title}'"
        + (f" — alert when price drops below ${target_price:.2f}" if target_price else ""),
    )
