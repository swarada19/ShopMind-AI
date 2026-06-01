"""
app/agents/preference_agent.py

Preference Agent — enriches the graph state with stored user preferences.

This agent has NO LLM call. It's a pure database read operation.
It loads the user's saved preferences (budget, brands, categories) and
merges them with anything the Orchestrator already extracted from the query.

Merge strategy:
  - Query-extracted budget takes precedence over stored budget
    (the user is being specific right now)
  - Stored brands/categories are added as context, not hard filters

Why is this a separate agent and not just part of the Orchestrator?
  The Orchestrator handles language understanding (routing + extraction).
  The Preference Agent handles data enrichment from persistent storage.
  Keeping them separate means you can evolve each independently —
  e.g., make Preference Agent smarter with ML-based profile inference
  without touching the Orchestrator's routing logic.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_logger
from app.graph.state import GraphState
from app.models.preference import UserPreference
from app.models.search_history import SearchHistory

logger = get_logger(__name__)


async def preference_node(state: GraphState, db: AsyncSession) -> GraphState:
    """
    LangGraph node: load user preferences from DB and merge with query context.

    The database session is injected via LangGraph's configurable mechanism.
    See graph.py for how this is wired.
    """
    user_id = state["user_id"]
    logger.info("[Preference] Loading preferences for user: %s", user_id)

    try:
        # Load user preferences
        result = await db.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        prefs = result.scalar_one_or_none()

        # Load recent search history (last 5) for context
        history_result = await db.execute(
            select(SearchHistory.raw_query)
            .where(SearchHistory.user_id == user_id)
            .order_by(SearchHistory.created_at.desc())
            .limit(5)
        )
        recent_searches = [row[0] for row in history_result.fetchall()]

        # Build preference dict — merge stored prefs with query-extracted budget
        stored_budget = prefs.max_budget if prefs else None
        query_budget = state.get("extracted_budget")

        effective_budget = query_budget or stored_budget  # Query-time takes precedence

        user_preferences = {
            "max_budget": effective_budget,
            "currency": prefs.currency if prefs else "USD",
            "preferred_brands": prefs.preferred_brands if prefs else [],
            "preferred_categories": prefs.preferred_categories if prefs else [],
            "recent_searches": recent_searches,
        }

        logger.debug(
            "[Preference] User %s | budget=$%s | brands=%s",
            user_id,
            effective_budget,
            user_preferences["preferred_brands"],
        )

        return {**state, "user_preferences": user_preferences}

    except Exception as e:
        logger.error("[Preference] Failed for user %s: %s", user_id, str(e))
        # Graceful degradation: continue with no preferences
        return {
            **state,
            "user_preferences": {
                "max_budget": state.get("extracted_budget"),
                "currency": "USD",
                "preferred_brands": [],
                "preferred_categories": [],
                "recent_searches": [],
            },
            "error": f"Preference load failed: {e}",
            "error_node": "preference",
        }
