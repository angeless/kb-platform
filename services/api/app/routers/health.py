"""Health check endpoints."""

import asyncio
import time

import boto3
import redis.asyncio as aioredis
from botocore.exceptions import ClientError, EndpointConnectionError
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from shared_config.settings import get_settings

router = APIRouter(tags=["health"])

# Per-check timeout in seconds
_CHECK_TIMEOUT = 1.0


@router.get(
    "/healthz",
    summary="Liveness probe",
    description="Lightweight liveness check. Always returns ok. Used by container orchestrators (e.g., K8s livenessProbe).",
    responses={200: {"description": "Service is alive"}},
)
async def healthz():
    """Liveness probe — always returns ok."""
    return {"status": "ok"}


@router.get(
    "/readyz",
    summary="Readiness probe",
    description="Checks database connectivity via SELECT 1. Used by load balancers and K8s readinessProbe.",
    responses={
        200: {"description": "Service is ready to accept traffic"},
        500: {"description": "Database connection failed"},
    },
)
async def readyz(db: AsyncSession = Depends(get_db)):
    """Readiness probe — checks database connectivity."""
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}


@router.get(
    "/api/versions",
    summary="List supported API versions",
    description="Returns the list of API versions supported by this instance, including their status and deprecation dates.",
    responses={200: {"description": "Version list returned successfully"}},
)
async def api_versions():
    """Return supported API versions."""
    return {
        "versions": [
            {"version": "v1", "status": "active", "deprecation_date": None}
        ]
    }


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Exposes application metrics in Prometheus text exposition format. Scraped by Prometheus at configured intervals.",
    responses={200: {"description": "Prometheus metrics in text format"}},
)
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# --- Deep health check ---


async def _check_postgres(db: AsyncSession) -> dict:
    """Check PostgreSQL connectivity via SELECT 1."""
    start = time.monotonic()
    try:
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=_CHECK_TIMEOUT)
        latency = int((time.monotonic() - start) * 1000)
        return {"status": "ok", "latency_ms": latency, "message": "Connected"}
    except asyncio.TimeoutError:
        latency = int((time.monotonic() - start) * 1000)
        return {"status": "error", "latency_ms": latency, "message": "Timeout"}
    except Exception as e:
        latency = int((time.monotonic() - start) * 1000)
        return {"status": "error", "latency_ms": latency, "message": str(e)[:200]}


async def _check_redis() -> dict:
    """Check Redis connectivity via PING."""
    settings = get_settings()
    start = time.monotonic()
    try:
        r = aioredis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            socket_connect_timeout=_CHECK_TIMEOUT,
            socket_timeout=_CHECK_TIMEOUT,
        )
        try:
            pong = await asyncio.wait_for(r.ping(), timeout=_CHECK_TIMEOUT)
            latency = int((time.monotonic() - start) * 1000)
            if pong:
                return {"status": "ok", "latency_ms": latency, "message": "PING successful"}
            return {"status": "error", "latency_ms": latency, "message": "PING returned False"}
        finally:
            await r.aclose()
    except asyncio.TimeoutError:
        latency = int((time.monotonic() - start) * 1000)
        return {"status": "error", "latency_ms": latency, "message": "Timeout"}
    except Exception as e:
        latency = int((time.monotonic() - start) * 1000)
        return {"status": "error", "latency_ms": latency, "message": str(e)[:200]}


async def _check_minio() -> dict:
    """Check MinIO/S3 connectivity via head_bucket."""
    settings = get_settings()
    start = time.monotonic()
    try:

        def _do_check():
            client = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
                region_name=settings.s3_region,
            )
            client.head_bucket(Bucket=settings.s3_bucket)

        await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, _do_check),
            timeout=_CHECK_TIMEOUT,
        )
        latency = int((time.monotonic() - start) * 1000)
        return {"status": "ok", "latency_ms": latency, "message": "Bucket access OK"}
    except asyncio.TimeoutError:
        latency = int((time.monotonic() - start) * 1000)
        return {"status": "error", "latency_ms": latency, "message": "Timeout"}
    except (ClientError, EndpointConnectionError, Exception) as e:
        latency = int((time.monotonic() - start) * 1000)
        return {"status": "error", "latency_ms": latency, "message": str(e)[:200]}


@router.get(
    "/api/health/ready",
    summary="Deep health check",
    description="Checks PostgreSQL, Redis, and MinIO connectivity concurrently. Returns overall status: ok (all services up), degraded (PG up but Redis/MinIO down), or unhealthy (PG down, returns 503).",
    responses={
        200: {"description": "All services ok, or degraded (PG up but non-critical services down)"},
        503: {"description": "Unhealthy — PostgreSQL is unreachable"},
    },
)
async def health_ready(db: AsyncSession = Depends(get_db)):
    """Deep health check — checks PostgreSQL, Redis, and MinIO connectivity."""
    pg_result, redis_result, minio_result = await asyncio.gather(
        _check_postgres(db),
        _check_redis(),
        _check_minio(),
    )

    # Determine overall status
    if pg_result["status"] == "error":
        overall = "unhealthy"
    elif redis_result["status"] == "error" or minio_result["status"] == "error":
        overall = "degraded"
    else:
        overall = "ok"

    body = {
        "status": overall,
        "version": "0.35.0",
        "checks": {
            "postgres": pg_result,
            "redis": redis_result,
            "minio": minio_result,
        },
    }

    status_code = 503 if overall == "unhealthy" else 200
    return JSONResponse(content=body, status_code=status_code)
