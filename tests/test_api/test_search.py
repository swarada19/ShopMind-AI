"""
tests/test_api/test_search.py

Integration tests for the core /search and /search/watch endpoints.
These are the most important endpoints in the system — they exercise
the full LangGraph pipeline in mock mode.
"""

import pytest


@pytest.mark.asyncio
async def test_search_returns_recommendations(client, test_user):
    """POST /search should run the full pipeline and return ranked products."""
    response = await client.post("/search", json={
        "user_id": test_user.id,
        "query": "wireless headphones",
    })
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["user_id"] == test_user.id
    assert data["raw_query"] == "wireless headphones"
    assert data["intent"] in {"search", "watch", "unknown"}
    assert isinstance(data["recommendations"], list)
    assert data["results_count"] == len(data["recommendations"])
    assert "session_id" in data


@pytest.mark.asyncio
async def test_search_with_budget_filters_products(client, test_user):
    """Products over budget should not appear in results when budget is set."""
    response = await client.post("/search", json={
        "user_id": test_user.id,
        "query": "headphones under $100",
    })
    assert response.status_code == 200
    data = response.json()
    # All returned products should be within the $100 budget
    for rec in data["recommendations"]:
        if rec.get("price") is not None:
            assert rec["price"] <= 100.0, (
                f"Product '{rec['title']}' priced at ${rec['price']} exceeds $100 budget"
            )


@pytest.mark.asyncio
async def test_search_response_has_scores(client, test_user):
    """Every recommendation must have all three scoring components."""
    response = await client.post("/search", json={
        "user_id": test_user.id,
        "query": "laptop",
    })
    assert response.status_code == 200
    for rec in response.json()["recommendations"]:
        assert 0.0 <= rec["final_score"] <= 1.0
        assert 0.0 <= rec["deal_score"] <= 1.0
        assert 0.0 <= rec["review_score"] <= 1.0
        assert rec["rank"] >= 1
        assert rec["explanation"] != ""


@pytest.mark.asyncio
async def test_search_recommendations_ranked_by_score(client, test_user):
    """Recommendations must be in descending final_score order."""
    response = await client.post("/search", json={
        "user_id": test_user.id,
        "query": "smartphone",
    })
    recs = response.json()["recommendations"]
    scores = [r["final_score"] for r in recs]
    assert scores == sorted(scores, reverse=True), "Results are not sorted by final_score"


@pytest.mark.asyncio
async def test_search_query_too_short_fails(client, test_user):
    """Queries shorter than 3 chars should be rejected by schema validation."""
    response = await client.post("/search", json={
        "user_id": test_user.id,
        "query": "ab",  # below min_length=3
    })
    assert response.status_code == 422  # Unprocessable Entity


@pytest.mark.asyncio
async def test_watch_creates_watchlist_item(client, test_user):
    """POST /search/watch should create a watchlist item and return its ID."""
    response = await client.post("/search/watch", json={
        "user_id": test_user.id,
        "query": "Sony WH-1000XM5",
        "product_title": "Sony WH-1000XM5 Wireless Headphones",
        "product_url": "https://www.amazon.com/dp/B09XS7JWHH",
        "target_price": 249.99,
    })
    assert response.status_code == 200, response.text
    data = response.json()
    assert "watchlist_item_id" in data
    assert data["watchlist_item_id"] is not None
    assert data["target_price"] == 249.99
    assert "249.99" in data["message"]


@pytest.mark.asyncio
async def test_watch_without_target_price(client, test_user):
    """Watching without a target_price should still succeed."""
    response = await client.post("/search/watch", json={
        "user_id": test_user.id,
        "query": "MacBook Pro",
        "product_title": "Apple MacBook Pro 14-inch",
    })
    assert response.status_code == 200
    assert response.json()["target_price"] is None
