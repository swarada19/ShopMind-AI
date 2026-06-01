"""
app/graph/graph.py

LangGraph StateGraph construction for ShopMind AI.

This file wires all agents into a directed graph with conditional routing.

Graph topology:

  START
    │
    ▼
  [orchestrator] ──── conditional edge ──────────────┐
    │                                                 │
    │ intent="search"                   intent="watch"│
    ▼                                                 ▼
  [preference] ──► [product_intelligence] ──► [recommendation]
                                                      │
                                                  [save_watchlist]
                                                      │
                                                     END

Key design decisions:
1. Database sessions: Nodes that need DB access receive a session via
   LangGraph's `RunnableConfig`. We pass `db` in config["configurable"]["db"].
2. The graph is compiled ONCE at startup and reused for all requests.
   LangGraph compiled graphs are stateless and thread-safe.
3. Error field: if any node sets `error`, the graph continues but downstream
   nodes check it. This gives graceful degradation rather than hard crashes.
"""

import logging
from functools import partial

from langgraph.graph import END, StateGraph

from app.agents.orchestrator import orchestrator_node
from app.agents.preference_agent import preference_node
from app.agents.product_intelligence import product_intelligence_node
from app.agents.recommendation_agent import recommendation_node
from app.graph.state import GraphState

logger = logging.getLogger(__name__)

# ── Node wrappers ─────────────────────────────────────────────────────────────
# LangGraph nodes receive only `state` by default.
# We wrap DB-dependent nodes to extract `db` from LangGraph's config object.


async def _preference_node_wrapper(state: GraphState, config: dict) -> GraphState:
    db = config["configurable"]["db"]
    return await preference_node(state, db)


async def _product_intelligence_wrapper(state: GraphState, config: dict) -> GraphState:
    db = config["configurable"]["db"]
    return await product_intelligence_node(state, db)


# ── Router ────────────────────────────────────────────────────────────────────

def route_intent(state: GraphState) -> str:
    """
    Conditional edge function: determine next node based on Orchestrator output.

    Returns a string key that maps to the next node name.
    LangGraph matches this string against the dict passed to
    `add_conditional_edges`.
    """
    intent = state.get("intent", "unknown")

    if state.get("error") and state.get("error_node") == "orchestrator":
        logger.warning("[Router] Orchestrator failed — routing to END")
        return "end"

    if intent == "watch":
        return "watch"
    elif intent == "search":
        return "search"
    else:
        logger.info("[Router] Unknown intent for query: '%s'", state.get("raw_query", ""))
        return "end"


# ── Save watchlist node ───────────────────────────────────────────────────────

async def save_watchlist_node(state: GraphState, config: dict) -> GraphState:
    """
    LangGraph node: save a product to the user's watchlist.

    Extracts the watch target from the raw_query and saves it to DB.
    This is a simple node — it does one DB insert and returns.
    """
    from app.models.watchlist import WatchlistItem
    from app.models.base import generate_uuid

    db = config["configurable"]["db"]
    user_id = state["user_id"]
    raw_query = state["raw_query"]
    product_query = state.get("product_query") or raw_query
    budget = state.get("extracted_budget")

    logger.info("[SaveWatchlist] Adding to watchlist for user %s", user_id)

    try:
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

        return {
            **state,
            "watchlist_item_id": item.id,
            "recommendations": [],
        }

    except Exception as e:
        logger.error("[SaveWatchlist] Failed: %s", str(e))
        return {
            **state,
            "watchlist_item_id": None,
            "error": f"Watchlist save failed: {e}",
            "error_node": "save_watchlist",
        }


# ── Graph construction ────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Build and compile the ShopMind AI StateGraph."""

    graph = StateGraph(GraphState)

    # Register nodes
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("preference", _preference_node_wrapper)
    graph.add_node("product_intelligence", _product_intelligence_wrapper)
    graph.add_node("recommendation", recommendation_node)
    graph.add_node("save_watchlist", save_watchlist_node)

    # Entry point
    graph.set_entry_point("orchestrator")

    # Conditional routing from orchestrator
    graph.add_conditional_edges(
        "orchestrator",
        route_intent,
        {
            "search": "preference",
            "watch": "save_watchlist",
            "end": END,
        },
    )

    # Linear search path
    graph.add_edge("preference", "product_intelligence")
    graph.add_edge("product_intelligence", "recommendation")
    graph.add_edge("recommendation", END)

    # Watch path ends after saving
    graph.add_edge("save_watchlist", END)

    return graph


# Module-level compiled graph (built once, reused per request)
_compiled_graph = None


def get_compiled_graph():
    """
    Return the compiled graph singleton.

    Using a singleton avoids rebuilding the graph on every request.
    The compiled graph is stateless — all state lives in the `state` dict
    passed to ainvoke(), so concurrent requests don't interfere.
    """
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph().compile()
        logger.info("LangGraph compiled and ready")
    return _compiled_graph
