"""
tests/conftest.py

Pytest fixtures shared across all test modules.

SQLite in-memory is used for all tests — no PostgreSQL needed.
The database module is initialised with the SQLite URL BEFORE any model
imports so the engine is created with the right driver.
"""

import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ── Initialise the DB module with SQLite BEFORE app imports ──────────────────
# This ensures no PostgreSQL / asyncpg connection is attempted during tests.
from app.core import database as _db_module

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
_db_module.init_db(TEST_DATABASE_URL)

# Now it's safe to import app modules that use the DB
from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncSession:
    """Clean DB session per test, rolled back after each test."""
    factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncClient:
    """HTTP test client with DB dependency overridden to use test session."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    from app.models.user import User
    user = User(name="Test User", email="test@shopmind.ai", phone="+1234567890")
    db_session.add(user)
    await db_session.flush()
    return user
