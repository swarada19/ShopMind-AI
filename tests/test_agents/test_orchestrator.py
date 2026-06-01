"""
tests/test_agents/test_orchestrator.py

Tests for the Orchestrator Agent's mock classification logic.

Since we test with USE_MOCK_DATA=True, no LLM call is made.
These tests verify the regex/keyword classification works correctly.
"""

import pytest
import pytest_asyncio

from app.agents.orchestrator import _mock_classify


class TestMockClassification:
    def test_search_intent_default(self):
        result = _mock_classify("best wireless headphones")
        assert result.intent == "search"

    def test_watch_intent_keywords(self):
        for phrase in [
            "watch this laptop for me",
            "alert me when the price drops",
            "track Sony WH-1000XM5",
            "notify me if this gets cheaper",
            "monitor MacBook Pro price",
        ]:
            result = _mock_classify(phrase)
            assert result.intent == "watch", f"Expected watch for: '{phrase}'"

    def test_budget_extraction_dollar_sign(self):
        result = _mock_classify("headphones under $150")
        assert result.extracted_budget == 150.0

    def test_budget_extraction_text(self):
        result = _mock_classify("laptop less than 800 dollars")
        assert result.extracted_budget == 800.0

    def test_no_budget_returns_none(self):
        result = _mock_classify("best gaming headphones")
        assert result.extracted_budget is None

    def test_product_query_cleaned(self):
        result = _mock_classify("find me the best wireless headphones")
        # Stop words like "find", "me", "the", "best" should be removed
        query = result.product_query
        assert "find" not in query
        assert "me" not in query
        assert "wireless" in query or "headphones" in query

    def test_constraint_extraction(self):
        result = _mock_classify("wireless noise cancelling headphones")
        assert "wireless" in result.extracted_constraints or "noise" in result.extracted_constraints

    def test_returns_orchestrator_output_schema(self):
        from app.agents.orchestrator import OrchestratorOutput
        result = _mock_classify("gaming laptop under $1000")
        assert isinstance(result, OrchestratorOutput)
        assert result.intent in {"search", "watch", "unknown"}


@pytest.mark.asyncio
async def test_orchestrator_node_returns_updated_state():
    """Full node test with mock mode — verifies state fields are populated."""
    from app.agents.orchestrator import orchestrator_node
    from app.graph.state import GraphState

    initial_state: GraphState = {
        "user_id": "test_user",
        "raw_query": "wireless headphones under $100",
        "session_id": "test-session",
        "use_mock": True,
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

    result = await orchestrator_node(initial_state)

    assert result["intent"] in {"search", "watch", "unknown"}
    assert result["product_query"] != ""
    assert result["extracted_budget"] == 100.0
    assert result["error"] is None
