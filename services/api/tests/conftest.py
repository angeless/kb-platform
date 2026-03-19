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

from app.deps import get_db
from app.main import create_app
from app.routers.assets import get_storage
from app.utils.security import create_access_token, hash_password

settings = get_settings()

TEST_DB_URL = settings.database_url + "_test"


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
async def auth_headers(db_session: AsyncSession) -> dict[str, str]:
    """Create a test tenant and user, return auth headers with valid JWT."""
    tenant = Tenant(id=uuid.uuid4(), name="Test Tenant", status="active")
    db_session.add(tenant)
    await db_session.flush()

    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"test-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("test-password"),
        role="admin",
        status="active",
    )
    db_session.add(user)
    await db_session.flush()

    token = create_access_token(
        data={"sub": str(user.id), "tenant_id": str(tenant.id), "role": user.role},
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    return {"Authorization": f"Bearer {token}"}
