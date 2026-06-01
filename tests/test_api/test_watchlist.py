"""
tests/test_api/test_watchlist.py

Integration tests for the /watchlist CRUD endpoints.
"""

import pytest


async def _create_watchlist_item(client, user_id: str, title: str = "Test Product") -> str:
    """Helper: create a watchlist item and return its ID."""
    r = await client.post("/search/watch", json={
        "user_id": user_id,
        "query": title,
        "product_title": title,
        "target_price": 99.99,
    })
    assert r.status_code == 200, r.text
    return r.json()["watchlist_item_id"]


@pytest.mark.asyncio
async def test_list_watchlist_empty(client, test_user):
    """GET /watchlist/{user_id} should return empty list for new user."""
    response = await client.get(f"/watchlist/{test_user.id}")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_watchlist_after_adding(client, test_user):
    """Watchlist should contain item after POST /search/watch."""
    await _create_watchlist_item(client, test_user.id, "Sony Headphones")
    response = await client.get(f"/watchlist/{test_user.id}")
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 1
    assert any(i["product_title"] == "Sony Headphones" for i in items)


@pytest.mark.asyncio
async def test_get_single_watchlist_item(client, test_user):
    """GET /watchlist/{user_id}/{item_id} should return the item."""
    item_id = await _create_watchlist_item(client, test_user.id, "MacBook Pro")
    response = await client.get(f"/watchlist/{test_user.id}/{item_id}")
    assert response.status_code == 200
    assert response.json()["id"] == item_id


@pytest.mark.asyncio
async def test_get_nonexistent_watchlist_item(client, test_user):
    """GET with unknown item_id should return 404."""
    response = await client.get(f"/watchlist/{test_user.id}/nonexistent-item")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_target_price(client, test_user):
    """PATCH should update the target price."""
    item_id = await _create_watchlist_item(client, test_user.id, "iPhone")
    response = await client.patch(
        f"/watchlist/{test_user.id}/{item_id}",
        json={"target_price": 799.00},
    )
    assert response.status_code == 200
    assert response.json()["target_price"] == 799.00


@pytest.mark.asyncio
async def test_deactivate_watchlist_item(client, test_user):
    """PATCH with is_active=False should deactivate the item."""
    item_id = await _create_watchlist_item(client, test_user.id, "iPad Pro")
    response = await client.patch(
        f"/watchlist/{test_user.id}/{item_id}",
        json={"is_active": False},
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    # Should not appear in active-only list
    list_response = await client.get(f"/watchlist/{test_user.id}?active_only=true")
    ids = [i["id"] for i in list_response.json()]
    assert item_id not in ids


@pytest.mark.asyncio
async def test_delete_watchlist_item(client, test_user):
    """DELETE should remove the item; subsequent GET should return 404."""
    item_id = await _create_watchlist_item(client, test_user.id, "Samsung TV")
    delete_response = await client.delete(f"/watchlist/{test_user.id}/{item_id}")
    assert delete_response.status_code == 204

    get_response = await client.get(f"/watchlist/{test_user.id}/{item_id}")
    assert get_response.status_code == 404
