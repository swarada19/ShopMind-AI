"""
app/core/database.py

SQLAlchemy async engine, session factory, and declarative Base.

Design: engine and session factory are created lazily (on first use) rather
than at module import time. This lets tests override the DATABASE_URL by
calling `init_db()` with a different URL before the first DB call, without
requiring asyncpg to be installed in test environments that use SQLite.
"""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

# Module-level variables — populated by init_db() on first access
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker | None = None


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


def init_db(database_url: str | None = None) -> None:
    """
    Initialise (or re-initialise) the async engine and session factory.

    Args:
        database_url: Override the DATABASE_URL from settings.
                      Used by tests to substitute SQLite.
    """
    global _engine, _session_factory

    from app.core.config import settings

    url = database_url or settings.DATABASE_URL

    _engine = create_async_engine(
        url,
        echo=settings.APP_DEBUG,
        pool_pre_ping=True,
        # SQLite doesn't support pool_size — only set these for PostgreSQL
        **({} if url.startswith("sqlite") else {"pool_size": 10, "max_overflow": 20}),
    )

    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    logger.debug("Database engine initialised: %s", url.split("@")[-1])  # log host only


def _get_engine() -> AsyncEngine:
    if _engine is None:
        init_db()
    return _engine  # type: ignore[return-value]


def _get_session_factory() -> async_sessionmaker:
    if _session_factory is None:
        init_db()
    return _session_factory  # type: ignore[return-value]


# Make these accessible as module-level attributes for convenience
class _EngineProxy:
    def __getattr__(self, name: str):
        return getattr(_get_engine(), name)


AsyncSessionLocal = _get_session_factory  # callable that returns session factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: provides a DB session per request."""
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """Create all tables. For testing and initial setup."""
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")


async def drop_tables() -> None:
    """Drop all tables. For testing only."""
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.info("Database tables dropped")
