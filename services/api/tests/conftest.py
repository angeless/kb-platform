"""Test fixtures for the API service."""

import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared_config.settings import get_settings
from shared_models import Base, Tenant, User

from app.deps import get_current_user, get_db
from app.main import create_app
from app.routers.assets import get_storage

from unittest.mock import patch

settings = get_settings()

def _make_test_db_url(url: str) -> str:
    """Append '_test' to database name, handling query params like ?ssl=require."""
    if "?" in url:
        base, query = url.rsplit("?", 1)
        return f"{base}_test?{query}"
    return url + "_test"

TEST_DB_URL = _make_test_db_url(settings.database_url)


@pytest.fixture(autouse=True)
def _disable_rate_limit(request):
    """Disable rate limit middleware in all tests."""

    async def _passthrough_dispatch(self, request, call_next):
        return await call_next(request)

    with patch("app.middleware.rate_limit.RateLimitMiddleware.dispatch", _passthrough_dispatch):
        yield


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_engine():
    """Create engine inside the session event loop."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    # Try to enable pgvector extension (available in Docker, may not be locally)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    except Exception:
        pass  # pgvector not installed locally — Docker tests will have it
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Yield a test database session that rolls back after each test.

    Uses a connection + savepoint so that even sessions created by the
    dependency override (inside BaseHTTPMiddleware's task-group) share the
    same underlying DBAPI connection and transaction.
    """
    conn = await test_engine.connect()
    txn = await conn.begin()

    session = AsyncSession(bind=conn, expire_on_commit=False)
    yield session

    await session.close()
    await txn.rollback()
    await conn.close()


# Shared test user for auth_headers fixture
_test_user: User | None = None


@pytest_asyncio.fixture(loop_scope="session")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with DB dependency override."""
    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    # Mock storage: return None so uploads skip MinIO in tests
    app.dependency_overrides[get_storage] = lambda: None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(loop_scope="session")
async def auth_headers(db_session: AsyncSession, client: AsyncClient) -> dict[str, str]:
    """Create a test tenant and user, return auth headers.

    Overrides get_current_user to return the test user directly,
    bypassing Pass /me verification (Pass is not available in tests).
    """
    global _test_user

    tenant = Tenant(id=uuid.uuid4(), name="Test Tenant", status="active")
    db_session.add(tenant)
    await db_session.flush()

    user = User(
        id=uuid.uuid4(),
        kb_id=tenant.id,
        pass_id=f"pass:{uuid.uuid4()}",
        email=f"test-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=None,
        role="admin",
        status="active",
    )
    db_session.add(user)
    await db_session.flush()

    _test_user = user

    # Override get_current_user to return our test user
    client._transport.app.dependency_overrides[get_current_user] = lambda: user  # type: ignore[union-attr]

    return {
        "Authorization": "Bearer test-token",
        "X-Requested-With": "XMLHttpRequest",
    }
