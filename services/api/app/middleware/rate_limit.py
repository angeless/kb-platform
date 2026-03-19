"""Redis sliding window rate limiting middleware."""

import time
import logging

import redis.asyncio as aioredis
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from shared_config.settings import get_settings

logger = logging.getLogger(__name__)

# Paths exempt from rate limiting
EXEMPT_PATHS = {"/healthz", "/readyz", "/docs", "/openapi.json", "/redoc"}

# Paths with stricter upload rate limits
UPLOAD_PATHS = {"/v1/assets/upload", "/v1/assets/import-url", "/v1/assets/import-archive"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiter using Redis sorted sets.

    Uses tenant_id from JWT for authenticated requests,
    falls back to client IP for unauthenticated requests.
    """

    def __init__(self, app, redis_client: aioredis.Redis | None = None) -> None:  # type: ignore[override]
        super().__init__(app)
        self._redis: aioredis.Redis | None = redis_client

    async def _get_redis(self) -> aioredis.Redis | None:
        if self._redis is None:
            try:
                settings = get_settings()
                self._redis = aioredis.from_url(settings.redis_url)
            except Exception as e:
                logger.warning("Rate limiter Redis unavailable: %s", e)
                return None
        return self._redis

    def _extract_identity(self, request: Request) -> str:
        """Extract rate limit key: tenant_id from auth header, or client IP."""
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            try:
                import jwt
                settings = get_settings()
                payload = jwt.decode(
                    auth[7:], settings.jwt_secret,
                    algorithms=[settings.jwt_algorithm],
                    options={"verify_exp": False},
                )
                tid = payload.get("tenant_id")
                if tid:
                    return f"tenant:{tid}"
            except Exception:
                pass
        # Fallback to IP
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # Skip exempt paths
        if path in EXEMPT_PATHS:
            return await call_next(request)

        r = await self._get_redis()
        if r is None:
            # Redis unavailable — fail open (allow request)
            return await call_next(request)

        settings = get_settings()
        identity = self._extract_identity(request)
        is_upload = path in UPLOAD_PATHS
        limit = settings.upload_rate_limit_per_minute if is_upload else settings.rate_limit_per_minute

        key = f"ratelimit:{identity}:{'upload' if is_upload else 'api'}"
        now = time.time()
        window_start = now - 60  # 1 minute window

        try:
            pipe = r.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)  # Remove old entries
            pipe.zadd(key, {str(now): now})  # Add current request
            pipe.zcard(key)  # Count requests in window
            pipe.expire(key, 120)  # TTL: 2 minutes (safety)
            results = await pipe.execute()
            count = results[2]

            if count > limit:
                retry_after = 60 - int(now - window_start)
                return JSONResponse(
                    status_code=429,
                    content={
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "message": f"请求过于频繁，每分钟最多 {limit} 次，请稍后再试",
                        "detail": {"limit": limit, "current": count, "retry_after": retry_after},
                    },
                    headers={"Retry-After": str(max(1, retry_after))},
                )

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, limit - count))
            return response

        except Exception as e:
            logger.warning("Rate limit check failed: %s", e)
            # Fail open
            return await call_next(request)
