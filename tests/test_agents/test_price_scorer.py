"""
tests/test_agents/test_price_scorer.py

Unit tests for the price_scorer module.

These are pure function tests — no DB, no LLM, no network.
They run instantly and should always pass.
"""

import pytest

from app.tools.price_scorer import (
    compute_deal_score,
    compute_discount_pct,
    compute_final_score,
    compute_review_score,
    compute_trust_score,
)


class TestDealScore:
    def test_under_budget_positive_score(self):
        """Product at half the budget (no discount) should score > 0.4.
        Formula: budget_score=0.75, discount_score=0.0
        → 0.6*0.75 + 0.4*0.0 = 0.45"""
        score = compute_deal_score(price=50.0, original_price=None, budget=100.0)
        assert score > 0.4

    def test_over_budget_zero_score(self):
        """Product over budget should get 0 deal score."""
        score = compute_deal_score(price=150.0, original_price=None, budget=100.0)
        assert score == 0.0

    def test_no_budget_neutral_score(self):
        """No budget should give a neutral score (0.5 from budget component)."""
        score = compute_deal_score(price=100.0, original_price=None, budget=None)
        assert 0.3 <= score <= 0.7

    def test_with_discount_boosts_score(self):
        """A product with a significant discount should score higher."""
        score_no_discount = compute_deal_score(100.0, original_price=None, budget=200.0)
        score_with_discount = compute_deal_score(100.0, original_price=200.0, budget=200.0)
        assert score_with_discount > score_no_discount

    def test_no_price_returns_neutral(self):
        score = compute_deal_score(price=None, original_price=None, budget=100.0)
        assert score == 0.5


class TestReviewScore:
    def test_perfect_rating_many_reviews(self):
        score = compute_review_score(rating=5.0, review_count=100_000)
        assert score > 0.9

    def test_no_rating_returns_zero(self):
        score = compute_review_score(rating=None, review_count=None)
        assert score == 0.0

    def test_high_rating_low_reviews(self):
        """High rating with few reviews should score less than with many reviews."""
        few = compute_review_score(rating=5.0, review_count=5)
        many = compute_review_score(rating=5.0, review_count=10_000)
        assert many > few

    def test_scores_bounded(self):
        """Score must always be between 0 and 1."""
        for r, c in [(0.0, 0), (5.0, 1_000_000), (3.5, 500), (None, 100)]:
            score = compute_review_score(r, c)
            assert 0.0 <= score <= 1.0


class TestFinalScore:
    def test_weights_sum_correctly(self):
        """Final score formula: deal×0.4 + review×0.35 + relevance×0.25."""
        score = compute_final_score(1.0, 1.0, 1.0)
        assert abs(score - 1.0) < 0.001

    def test_all_zeros(self):
        score = compute_final_score(0.0, 0.0, 0.0)
        assert score == 0.0

    def test_deal_score_has_highest_weight(self):
        """Changing deal score should have more impact than review or relevance."""
        base = compute_final_score(0.5, 0.5, 0.5)
        with_deal = compute_final_score(1.0, 0.5, 0.5)
        with_review = compute_final_score(0.5, 1.0, 0.5)
        assert with_deal > with_review  # Deal weight (0.4) > review weight (0.35)


class TestDiscountPct:
    def test_50_pct_off(self):
        pct = compute_discount_pct(price=50.0, original_price=100.0)
        assert pct == 50.0

    def test_no_discount(self):
        pct = compute_discount_pct(price=100.0, original_price=100.0)
        assert pct is None

    def test_price_higher_than_original(self):
        pct = compute_discount_pct(price=110.0, original_price=100.0)
        assert pct is None


class TestTrustScore:
    def test_amazon_source_gets_full_weight(self):
        score_amazon = compute_trust_score(4.5, 10_000, "amazon")
        score_unknown = compute_trust_score(4.5, 10_000, "unknown_source")
        assert score_amazon > score_unknown

    def test_bounded(self):
        score = compute_trust_score(5.0, 1_000_000, "amazon")
        assert 0.0 <= score <= 1.0
