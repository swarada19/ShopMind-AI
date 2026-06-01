"""
app/agents/recommendation_agent.py

Recommendation Agent — ranks products and generates natural language explanations.

This is the most complex agent in the system. It does three things:
1. Score each product using the price scorer (deal + review + relevance).
2. Rank products by final_score, respecting user preferences.
3. Generate a plain-English explanation for the top results using Groq LLM.

In MOCK mode: explanations are generated from templates, no LLM call.
In LIVE mode: Groq LLM generates one explanation per recommended product.

Scoring formula:
  final_score = deal_score × 0.40 + review_score × 0.35 + relevance_score × 0.25

Why generate explanations with LLM?
  Rule-based explanations are formulaic and boring.
  "Price: $279.99 | Rating: 4.8 | 70% off" is data, not insight.
  LLM-generated explanations say WHY this product is a good choice for THIS
  user's specific query — which is the core value proposition of ShopMind AI.
"""

from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings
from app.core.logging_config import get_logger
from app.graph.state import GraphState
from app.schemas.product import ScoredProduct
from app.tools.price_scorer import (
    compute_deal_score,
    compute_discount_pct,
    compute_final_score,
    compute_review_score,
)

logger = get_logger(__name__)

# ── LLM prompt ────────────────────────────────────────────────────────────────

_EXPLAIN_SYSTEM = """You are a concise product analyst. Write a 1-2 sentence explanation
of why a product is a good choice for the user's query. Focus on value, quality, and fit.
Be specific — mention the actual price, rating, and discount if relevant.
Do NOT start with "I" or "This product". Write directly and naturally."""

_EXPLAIN_HUMAN = """User query: {query}
Product: {title}
Price: ${price} (was ${original_price})
Rating: {rating}/5 from {review_count} reviews
Key features: {features}
Budget: ${budget}

Write the explanation:"""

_explain_prompt = ChatPromptTemplate.from_messages([
    ("system", _EXPLAIN_SYSTEM),
    ("human", _EXPLAIN_HUMAN),
])


def _get_llm():
    from langchain_groq import ChatGroq  # type: ignore[import]
    return ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.4,  # Slight creativity for natural explanations
        max_tokens=150,
    )


# ── Scoring ───────────────────────────────────────────────────────────────────

def _score_products(
    products: list[dict],
    budget: float | None,
    preferred_brands: list[str],
    query_keywords: list[str],
) -> list[ScoredProduct]:
    """Score and rank all products. Returns sorted list (best first)."""
    scored = []

    for p in products:
        deal = compute_deal_score(
            price=p.get("price"),
            original_price=p.get("original_price"),
            budget=budget,
        )
        review = compute_review_score(
            rating=p.get("rating"),
            review_count=p.get("review_count"),
        )

        # Relevance: trust_score base + keyword title match + preferred brand boost
        relevance = p.get("trust_score") or 0.5
        title_lower = (p.get("title") or "").lower()
        brand = (p.get("brand") or "").lower()

        # Boost relevance for each query keyword found in the product title
        keyword_hits = sum(1 for kw in query_keywords if kw and kw in title_lower)
        if query_keywords:
            relevance = min(relevance + (keyword_hits / len(query_keywords)) * 0.2, 1.0)

        # Additional boost for preferred brands
        if any(b.lower() in brand for b in preferred_brands):
            relevance = min(relevance + 0.15, 1.0)

        final = compute_final_score(deal, review, relevance)
        discount = compute_discount_pct(p.get("price"), p.get("original_price"))

        scored.append(
            ScoredProduct(
                id=p.get("id", ""),
                title=p.get("title", ""),
                price=p.get("price"),
                original_price=p.get("original_price"),
                currency=p.get("currency", "USD"),
                rating=p.get("rating"),
                review_count=p.get("review_count"),
                brand=p.get("brand"),
                category=p.get("category"),
                url=p.get("url"),
                image_url=p.get("image_url"),
                source=p.get("source", ""),
                features=p.get("features", []),
                trust_score=p.get("trust_score"),
                deal_score=deal,
                review_score=review,
                relevance_score=relevance,
                final_score=final,
                discount_pct=discount,
            )
        )

    scored.sort(key=lambda x: x.final_score, reverse=True)
    for i, product in enumerate(scored, start=1):
        product.rank = i

    return scored


# ── Mock explanations ─────────────────────────────────────────────────────────

def _mock_explain(product: ScoredProduct, query: str, budget: float | None) -> str:
    """Template-based explanation when LLM is not available."""
    parts = []

    if product.discount_pct and product.discount_pct > 10:
        parts.append(f"Currently {product.discount_pct:.0f}% off at ${product.price:.2f}")
    elif product.price:
        parts.append(f"Priced at ${product.price:.2f}")

    if budget and product.price and product.price <= budget:
        parts.append(f"fits within your ${budget:.0f} budget")

    if product.rating and product.rating >= 4.5:
        count = f"{product.review_count:,}" if product.review_count else "many"
        parts.append(f"highly rated at {product.rating}/5 from {count} reviews")

    if product.features:
        top_feature = product.features[0]
        parts.append(f"featuring {top_feature}")

    if not parts:
        return f"A solid choice for {query}."

    explanation = ", ".join(parts[:3])
    return explanation[0].upper() + explanation[1:] + "."


# ── Node function ─────────────────────────────────────────────────────────────

async def recommendation_node(state: GraphState) -> GraphState:
    """
    LangGraph node: score, rank, and explain product recommendations.
    """
    raw_products = state.get("raw_products", [])
    if not raw_products:
        logger.warning("[Recommendation] No products to rank")
        return {**state, "recommendations": []}

    prefs = state.get("user_preferences") or {}
    budget = prefs.get("max_budget") or state.get("extracted_budget")
    preferred_brands = prefs.get("preferred_brands", [])
    query = state.get("product_query") or state.get("raw_query", "")
    query_keywords = query.lower().split()
    use_mock = state.get("use_mock", True) or settings.USE_MOCK_DATA

    logger.info(
        "[Recommendation] Scoring %d products | budget=$%s | mock=%s",
        len(raw_products), budget, use_mock,
    )

    # Step 1: Score and rank
    scored = _score_products(raw_products, budget, preferred_brands, query_keywords)
    top_n = scored[:5]  # Generate explanations for top 5 only

    # Step 2: Generate explanations
    if use_mock:
        for product in top_n:
            product.explanation = _mock_explain(product, query, budget)
    else:
        llm = _get_llm()
        chain = _explain_prompt | llm
        for product in top_n:
            try:
                response = await chain.ainvoke({
                    "query": query,
                    "title": product.title,
                    "price": f"{product.price:.2f}" if product.price else "N/A",
                    "original_price": f"{product.original_price:.2f}" if product.original_price else "N/A",
                    "rating": product.rating or "N/A",
                    "review_count": f"{product.review_count:,}" if product.review_count else "N/A",
                    "features": ", ".join(product.features[:3]) if product.features else "N/A",
                    "budget": f"{budget:.0f}" if budget else "not specified",
                })
                product.explanation = response.content.strip()
            except Exception as e:
                logger.warning("[Recommendation] LLM explanation failed: %s", str(e))
                product.explanation = _mock_explain(product, query, budget)

    recommendations = [p.model_dump() for p in top_n]
    logger.info("[Recommendation] Returning %d recommendations", len(recommendations))
    return {**state, "recommendations": recommendations}
