"""Health check endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz():
    """Liveness probe — always returns ok."""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(db: AsyncSession = Depends(get_db)):
    """Readiness probe — checks database connectivity."""
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}
