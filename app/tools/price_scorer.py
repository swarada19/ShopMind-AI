"""
app/tools/price_scorer.py

Pure-Python scoring logic — no LLM, no external API calls.

This is intentionally a simple module of functions, not a class.
Each function does one calculation. This makes it trivially testable.

Scoring formula (from architecture design):
  final_score = deal_score × 0.40 + review_score × 0.35 + relevance_score × 0.25

  deal_score   — How good is the price? (budget fit + discount)
  review_score — How trustworthy are the reviews? (rating + volume)
  relevance    — How relevant is it to the query? (set by the LLM or keyword match)
"""

import math


def compute_deal_score(
    price: float | None,
    original_price: float | None,
    budget: float | None,
) -> float:
    """
    Calculate a deal score between 0 and 1.

    Two components:
    1. Budget fit (0.6 weight): How much of the budget is unused?
       - Under budget → score proportional to how much room there is.
       - Over budget → score 0.
    2. Discount (0.4 weight): Is the current price lower than the original?
       - Max discount (>50%) → 1.0
       - No discount → 0.0

    Returns 0.5 (neutral) when price data is unavailable.
    """
    if price is None:
        return 0.5

    # Budget component
    budget_score = 0.5  # neutral when no budget set
    if budget and budget > 0:
        if price > budget:
            budget_score = 0.0
        else:
            # How much headroom under budget (as a ratio)?
            headroom = (budget - price) / budget
            budget_score = min(headroom * 1.5, 1.0)  # amplified slightly

    # Discount component
    discount_score = 0.0
    if original_price and original_price > price:
        discount_pct = (original_price - price) / original_price
        # Cap at 50% discount = max score
        discount_score = min(discount_pct / 0.5, 1.0)

    return round(0.6 * budget_score + 0.4 * discount_score, 4)


def compute_review_score(
    rating: float | None,
    review_count: int | None,
) -> float:
    """
    Calculate a review score between 0 and 1.

    Two components:
    1. Rating (0.6 weight): Normalised from 5-star scale.
    2. Volume (0.4 weight): Logarithmic scale — 10,000 reviews ≈ full score.
       Log scale prevents a product with 1M reviews unfairly dominating
       one with 10K reviews.

    Returns 0.0 when no review data is available.
    """
    if rating is None and review_count is None:
        return 0.0

    rating_score = (rating / 5.0) if rating else 0.0

    # log10(10001) ≈ 4 → normalise to 1.0
    volume_score = 0.0
    if review_count and review_count > 0:
        volume_score = min(math.log10(review_count + 1) / 4.0, 1.0)

    return round(0.6 * rating_score + 0.4 * volume_score, 4)


def compute_trust_score(
    rating: float | None,
    review_count: int | None,
    source: str = "serpapi",
) -> float:
    """
    How reliable is this product listing?

    Trust score factors:
    - Rating quality and consistency
    - Review volume (more reviews = more reliable average)
    - Source reliability (amazon/official sources score higher)

    Used by the Product Intelligence Agent to filter low-trust listings.
    """
    source_weights = {
        "amazon": 1.0,
        "apple": 1.0,
        "dell": 0.95,
        "best_buy": 0.95,
        "walmart": 0.9,
        "serpapi": 0.85,
        "mock": 0.8,
    }

    review_score = compute_review_score(rating, review_count)
    source_weight = source_weights.get(source.lower(), 0.75)

    return round(review_score * source_weight, 4)


def compute_final_score(
    deal_score: float,
    review_score: float,
    relevance_score: float,
) -> float:
    """
    Combine all scores into a single final score.

    Weights (from architecture design document):
      deal_score   × 0.40
      review_score × 0.35
      relevance    × 0.25

    Rationale:
    - Deal score has the highest weight because ShopMind is a price intelligence
      tool — finding value for money is the core proposition.
    - Review score is second because user satisfaction data is the most reliable
      proxy for product quality.
    - Relevance is third because by the time we're scoring, pre-filtering has
      already ensured products are broadly relevant.
    """
    return round(
        deal_score * 0.40 + review_score * 0.35 + relevance_score * 0.25,
        4,
    )


def compute_discount_pct(price: float | None, original_price: float | None) -> float | None:
    """Return the percentage discount, or None if not applicable."""
    if price and original_price and original_price > price:
        return round((original_price - price) / original_price * 100, 1)
    return None
