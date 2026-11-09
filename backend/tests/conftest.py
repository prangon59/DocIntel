"""Pytest fixtures and configuration with in-memory database override."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db_session
from app.main import app

# Test SQLite in-memory engine
test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    future=True,
)

test_async_session = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(autouse=True)
def mock_celery_and_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock Celery task dispatching and Redis progress calls during unit tests."""
    from unittest.mock import MagicMock

    mock_task = MagicMock()
    mock_task.id = "mock-task-id-12345"
    monkeypatch.setattr(
        "app.api.v1.documents.process_document_task.delay",
        lambda *args, **kwargs: mock_task,
    )
    monkeypatch.setattr(
        "app.api.v1.documents.get_redis_progress",
        lambda *args, **kwargs: {
            "stage": "INGESTION",
            "status": "PROCESSING",
            "pages_done": 0,
            "pages_total": 1,
            "percentage": 0.0,
        },
    )


@pytest.fixture(scope="function", autouse=True)
async def setup_test_db() -> AsyncGenerator[None, None]:
    """Create and drop all database tables per test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an isolated test session."""
    async with test_async_session() as session:
        yield session


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async test client bound to FastAPI application with test db override."""

    async def _override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with test_async_session() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db_session] = _override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
