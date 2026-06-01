"""
app/api/routes/search.py

Core search and watch endpoints — the primary API surface of ShopMind AI.

POST /search  — Run the full multi-agent search pipeline
POST /watch   — Add a product to the user's watchlist
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.search import SearchRequest, SearchResponse, WatchRequest, WatchResponse
from app.services.search_service import execute_search, execute_watch

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("", response_model=SearchResponse, summary="Search for products")
async def search_products(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Run the full ShopMind AI multi-agent pipeline:

    1. **Orchestrator** classifies intent and extracts product query
    2. **Preference Agent** loads user preferences from DB
    3. **Product Intelligence** fetches products (cached or live)
    4. **Recommendation Agent** scores, ranks, and explains results

    Returns ranked product recommendations with deal scores and explanations.
    """
    try:
        return await execute_search(
            db=db,
            user_id=request.user_id,
            raw_query=request.query,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search pipeline failed: {str(e)}",
        )


@router.post("/watch", response_model=WatchResponse, summary="Watch a product for price drops")
async def watch_product(
    request: WatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Add a product to the user's watchlist.

    The Alert Agent will check the price daily and send a WhatsApp alert
    via Twilio when the price drops below `target_price`.
    """
    try:
        return await execute_watch(
            db=db,
            user_id=request.user_id,
            raw_query=request.query,
            product_title=request.product_title,
            product_url=request.product_url,
            target_price=request.target_price,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Watch operation failed: {str(e)}",
        )
