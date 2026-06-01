"""
app/main.py

FastAPI application factory.

Startup/shutdown is handled via the `lifespan` async context manager —
the modern pattern replacing the deprecated `@app.on_event` hooks
(removed in FastAPI 0.112+, emits warnings since 0.93).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import health, search, users, watchlist
from app.core.config import settings
from app.core.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan: runs startup logic, yields to serve requests,
    then runs shutdown logic.

    This replaces the deprecated @app.on_event("startup"/"shutdown") pattern.
    """
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("  %s v%s  |  env=%s  |  mock=%s",
                settings.APP_NAME, settings.APP_VERSION,
                settings.APP_ENV, settings.USE_MOCK_DATA)
    logger.info("  API docs → http://localhost:8000/docs")
    logger.info("=" * 60)

    # Pre-compile the LangGraph so the first request isn't slow
    from app.graph.graph import get_compiled_graph
    get_compiled_graph()

    # Start APScheduler
    from app.scheduler.jobs import start_scheduler
    start_scheduler()

    yield  # ← application serves requests here

    # ── Shutdown ──────────────────────────────────────────────────────────────
    from app.scheduler.jobs import stop_scheduler
    stop_scheduler()
    logger.info("%s shut down cleanly.", settings.APP_NAME)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "AI-powered product recommendation and price intelligence platform. "
            "Multi-agent architecture using LangGraph, Groq LLM, SerpAPI, and Twilio."
        ),
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    # `allow_origins=["*"]` + `allow_credentials=True` is invalid per CORS spec.
    # Use explicit origins in development; set your real domain in production.
    dev_origins = [
        "http://localhost:8501",    # Streamlit
        "http://127.0.0.1:8501",
        "http://localhost:3000",    # Future React/Vue frontend
        "http://127.0.0.1:3000",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=dev_origins if settings.is_development else ["https://yourdomain.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(health.router)
    app.include_router(users.router)
    app.include_router(search.router)
    app.include_router(watchlist.router)

    # ── Global exception handler ──────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            "Unhandled exception | path=%s | error=%s",
            request.url.path, str(exc), exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error", "detail": str(exc)},
        )

    return app


app = create_app()
