"""
app/graph/state.py

The GraphState TypedDict — the single most important design artifact
in a LangGraph project.

Every node in the graph reads from and writes to this shared state object.
Think of it as the "conveyor belt" that carries data through the pipeline.

Design principles:
1. Every field has a clear owner (which agent sets it).
2. Optional fields use `None` as default — never assume a field is populated
   unless your agent explicitly set it.
3. The `error` field is the graceful degradation mechanism — any node that
   fails sets this, and subsequent nodes check it before running.
4. `session_id` flows through for distributed tracing / LangSmith.

Field ownership map:
  user_id, raw_query, session_id, use_mock  → Set by API caller (input)
  intent, product_query, extracted_budget,
  extracted_constraints                     → Orchestrator Agent
  user_preferences                          → Preference Agent
  raw_products, cache_hit                   → Product Intelligence Agent
  recommendations                           → Recommendation Agent
  watchlist_item_id                         → Save Watchlist node
  error, error_node                         → Any node on failure
"""

from typing import Any, TypedDict


class GraphState(TypedDict):
    # ── Input (set by the API caller before graph.ainvoke()) ─────────────────
    user_id: str
    raw_query: str
    session_id: str
    use_mock: bool

    # ── Orchestrator Agent output ─────────────────────────────────────────────
    intent: str           # "search" | "watch" | "unknown"
    product_query: str    # cleaned, LLM-extracted query
    extracted_budget: float | None
    extracted_constraints: list[str]   # e.g. ["wireless", "under-ear", "USB-C"]

    # ── Preference Agent output ───────────────────────────────────────────────
    user_preferences: dict[str, Any] | None  # budget, brands, categories

    # ── Product Intelligence Agent output ─────────────────────────────────────
    raw_products: list[dict[str, Any]]
    cache_hit: bool

    # ── Recommendation Agent output ───────────────────────────────────────────
    recommendations: list[dict[str, Any]]

    # ── Save Watchlist node output ────────────────────────────────────────────
    watchlist_item_id: str | None

    # ── Error handling ────────────────────────────────────────────────────────
    error: str | None
    error_node: str | None
