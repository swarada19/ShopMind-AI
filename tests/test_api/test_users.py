"""
tests/test_api/test_users.py

API tests for the /users endpoints.
"""

import pytest


@pytest.mark.asyncio
async def test_create_user(client):
    """POST /users should create a user and return their ID."""
    response = await client.post("/users", json={
        "name": "Alice",
        "email": "alice@test.com",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Alice"
    assert data["email"] == "alice@test.com"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_user(client, test_user):
    """GET /users/{id} should return the user."""
    response = await client.get(f"/users/{test_user.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["email"] == test_user.email


@pytest.mark.asyncio
async def test_get_nonexistent_user(client):
    """GET /users/nonexistent should return 404."""
    response = await client.get("/users/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_upsert_preferences(client, test_user):
    """PUT /users/{id}/preferences should save preferences."""
    response = await client.put(
        f"/users/{test_user.id}/preferences",
        json={
            "max_budget": 500.0,
            "currency": "USD",
            "preferred_brands": ["Apple", "Sony"],
            "preferred_categories": ["headphones"],
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["max_budget"] == 500.0
    assert "Apple" in data["preferred_brands"]


@pytest.mark.asyncio
async def test_get_preferences_empty(client, test_user):
    """GET preferences before setting any should return null."""
    response = await client.get(f"/users/{test_user.id}/preferences")
    # Returns null or an empty preferences object
    assert response.status_code == 200
