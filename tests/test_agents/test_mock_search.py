"""
tests/test_agents/test_mock_search.py

Tests for the mock data search tool.
"""

import pytest

from app.tools.mock_data_tool import mock_search_products


def test_headphone_search_returns_results():
    results = mock_search_products("headphones")
    assert len(results) > 0
    for r in results:
        assert "headphone" in r.title.lower() or "airpod" in r.title.lower()


def test_laptop_search_returns_results():
    results = mock_search_products("laptop")
    assert len(results) > 0


def test_budget_filter_respected():
    """All results must be under the budget."""
    budget = 200.0
    results = mock_search_products("headphones", budget=budget)
    for r in results:
        assert r.price is None or r.price <= budget, (
            f"Product '{r.title}' priced at ${r.price} exceeds budget ${budget}"
        )


def test_max_results_respected():
    results = mock_search_products("electronics", max_results=3)
    assert len(results) <= 3


def test_irrelevant_query_returns_empty_or_few():
    results = mock_search_products("xyznonexistentproduct12345")
    assert len(results) == 0


def test_product_result_fields_populated():
    """Every result should have at minimum title and id."""
    results = mock_search_products("laptop")
    for r in results:
        assert r.id
        assert r.title
        assert r.source == "mock"
