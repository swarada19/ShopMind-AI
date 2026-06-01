"""
app/graph/graph.py

LangGraph StateGraph construction for ShopMind AI.

Graph topology:

  START → [orchestrator] → route_intent()
    ├─ "search" → [preference] → [product_intelligence] → [recommendation] → END
    ├─ "watch"  → [save_watchlist] → END
    └─ "end"    → END  (unknown intent or orchestrator failure)

Key design decisions:
1. DB sessions: nodes that need DB access receive an AsyncSession via
   LangGraph's RunnableConfig: config["configurable"]["db"].
   RunnableConfig is the correct type annotation — using `dict` causes
   LangGraph to skip config injection entirely (confirmed bug in 0.2.x).

2. Graph singleton: compiled once at startup, reused across requests.
   The compiled graph is stateless — state lives entirely in the dict
   passed to ainvoke(), so concurrent requests never interfere.

3. Error propagation: no node raises unhandled exceptions. Failures set
   state["error"] and state["error_node"]; downstream nodes degrade
   gracefully rather than crashing.
"""

import logging

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from app.agents.orchestrator import orchestrator_node
from app.agents.preference_agent import preference_node
from app.agents.product_intelligence import product_intelligence_node
from app.agents.recommendation_agent import recommendation_node
from app.graph.state import GraphState

logger = logging.getLogger(__name__)


# ── Node wrappers ─────────────────────────────────────────────────────────────
# LangGraph only injects `config` when it is typed as RunnableConfig.
# Using `dict` silently skips the injection, causing a missing-argument error.

async def _preference_node_wrapper(
    state: GraphState, config: RunnableConfig
) -> GraphState:
    db = config["configurable"]["db"]
    return await preference_node(state, db)


async def _product_intelligence_wrapper(
    state: GraphState, config: RunnableConfig
) -> GraphState:
    db = config["configurable"]["db"]
    return await product_intelligence_node(state, db)


async def save_watchlist_node(
    state: GraphState, config: RunnableConfig
) -> GraphState:
    """LangGraph node: save a product to the user's watchlist."""
    from sqlalchemy import select

    from app.models.base import generate_uuid
    from app.models.user import User
    from app.models.watchlist import WatchlistItem

    db = config["configurable"]["db"]
    user_id = state["user_id"]
    raw_query = state["raw_query"]
    product_query = state.get("product_query") or raw_query
    budget = state.get("extracted_budget")

    logger.info("[SaveWatchlist] Adding to watchlist for user %s", user_id)

    try:
        # Validate user exists — prevents FK constraint error from PostgreSQL
        user_result = await db.execute(select(User).where(User.id == user_id))
        if user_result.scalar_one_or_none() is None:
            return {
                **state,
                "watchlist_item_id": None,
                "recommendations": [],
                "error": f"User '{user_id}' not found — create an account first",
                "error_node": "save_watchlist",
            }

        item = WatchlistItem(
            id=generate_uuid(),
            user_id=user_id,
            product_title=product_query,
            product_query=product_query,
            target_price=budget,
            is_active=True,
        )
        db.add(item)
        await db.flush()

        return {**state, "watchlist_item_id": item.id, "recommendations": []}

    except Exception as e:
        logger.error("[SaveWatchlist] Failed: %s", str(e))
        return {
            **state,
            "watchlist_item_id": None,
            "recommendations": [],
            "error": f"Watchlist save failed: {e}",
            "error_node": "save_watchlist",
        }


# ── Router ────────────────────────────────────────────────────────────────────

def route_intent(state: GraphState) -> str:
    """Conditional edge: determine next node from Orchestrator output."""
    if state.get("error") and state.get("error_node") == "orchestrator":
        logger.warning("[Router] Orchestrator failed — routing to END")
        return "end"

    intent = state.get("intent", "unknown")
    if intent == "watch":
        return "watch"
    elif intent == "search":
        return "search"
    else:
        logger.info("[Router] Unknown intent: '%s'", state.get("raw_query", ""))
        return "end"


# ── Graph construction ────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Build the ShopMind AI StateGraph."""
    graph = StateGraph(GraphState)

    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("preference", _preference_node_wrapper)
    graph.add_node("product_intelligence", _product_intelligence_wrapper)
    graph.add_node("recommendation", recommendation_node)
    graph.add_node("save_watchlist", save_watchlist_node)

    graph.set_entry_point("orchestrator")

    graph.add_conditional_edges(
        "orchestrator",
        route_intent,
        {"search": "preference", "watch": "save_watchlist", "end": END},
    )

    graph.add_edge("preference", "product_intelligence")
    graph.add_edge("product_intelligence", "recommendation")
    graph.add_edge("recommendation", END)
    graph.add_edge("save_watchlist", END)

    return graph


_compiled_graph = None


def get_compiled_graph():
    """Return the compiled graph singleton (built once, reused per request)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph().compile()
        logger.info("LangGraph compiled and ready")
    return _compiled_graph
