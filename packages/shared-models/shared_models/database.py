"""Async and sync database engine and session factory."""

from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from shared_config.settings import get_settings

settings = get_settings()

# Async engine (for FastAPI)
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=20,
    max_overflow=10,
)

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Sync engine (for Celery workers)
sync_engine = create_engine(
    settings.database_url_sync,
    echo=settings.debug,
    pool_size=10,
    max_overflow=5,
)

sync_session_factory = sessionmaker(sync_engine, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
