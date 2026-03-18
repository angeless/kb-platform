"""Test fixtures for the API service."""

import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared_config.settings import get_settings
from shared_models import Base, Tenant, User

from app.deps import get_db
from app.main import create_app
from app.utils.security import create_access_token, hash_password

settings = get_settings()

TEST_DB_URL = settings.database_url + "_test"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionFactory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for all tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def setup_database():
    """Create all tables before tests, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """Yield a test database session that rolls back after each test."""
    async with TestSessionFactory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with DB dependency override."""
    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
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
