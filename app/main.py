"""
app/main.py

FastAPI application entry point.

This file:
1. Creates the FastAPI application instance
2. Registers all routers
3. Adds global exception handlers
4. Adds CORS middleware (required for Streamlit ↔ FastAPI)
5. Sets up startup/shutdown lifecycle hooks
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import health, search, users, watchlist
from app.core.config import settings
from app.core.logging_config import setup_logging

# Configure logging before anything else
setup_logging()
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "AI-powered product recommendation and price intelligence platform. "
            "Built with LangGraph multi-agent architecture, FastAPI, and Groq LLM."
        ),
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ────────────────────────────────────────────────────────────────────
    # Allow Streamlit (running on localhost:8501) to call the API.
    # In production, replace "*" with your actual frontend domain.
    # allow_origins=["*"] and allow_credentials=True cannot be combined per CORS spec —
    # browsers reject such responses. In dev, list explicit localhost origins instead.
    dev_origins = [
        "http://localhost:8501",   # Streamlit default
        "http://127.0.0.1:8501",
        "http://localhost:3000",   # Future React/Vue frontend
        "http://127.0.0.1:3000",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=dev_origins if settings.is_development else ["https://yourdomain.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ──────────────────────────────────────────────────────────────────
    app.include_router(health.router)
    app.include_router(users.router)
    app.include_router(search.router)
    app.include_router(watchlist.router)

    # ── Global exception handlers ─────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception on %s: %s", request.url.path, str(exc), exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error", "detail": str(exc)},
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    @app.on_event("startup")
    async def startup():
        logger.info("=" * 60)
        logger.info("  %s v%s starting up", settings.APP_NAME, settings.APP_VERSION)
        logger.info("  Environment : %s", settings.APP_ENV)
        logger.info("  Mock mode   : %s", settings.USE_MOCK_DATA)
        logger.info("  Docs        : http://localhost:8000/docs")
        logger.info("=" * 60)

        # Pre-compile the LangGraph so first request isn't slow
        from app.graph.graph import get_compiled_graph
        get_compiled_graph()

        # Start the APScheduler
        from app.scheduler.jobs import start_scheduler
        start_scheduler()

    @app.on_event("shutdown")
    async def shutdown():
        from app.scheduler.jobs import stop_scheduler
        stop_scheduler()
        logger.info("%s shut down cleanly", settings.APP_NAME)

    return app


app = create_app()
