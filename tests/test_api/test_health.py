"""
tests/test_api/test_health.py

Tests for the health check endpoints.
These should always be fast and reliable.
"""

import pytest
import pytest_asyncio


@pytest.mark.asyncio
async def test_liveness_check(client):
    """GET /health should return 200 with app info."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_readiness_check(client):
    """GET /health/ready should return 200 when DB is reachable."""
    response = await client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    # In test mode with SQLite, DB should be accessible
    assert "database" in data
