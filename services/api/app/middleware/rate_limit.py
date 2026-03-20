"""Redis sliding window rate limiting middleware with local memory fallback."""

import time
import logging
import threading

import redis.asyncio as aioredis
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from shared_config.settings import get_settings

logger = logging.getLogger(__name__)

# Paths exempt from rate limiting
EXEMPT_PATHS = {"/healthz", "/readyz", "/docs", "/openapi.json", "/redoc", "/api/health/ready", "/api/versions", "/metrics"}

# Paths with stricter upload rate limits
UPLOAD_PATHS = {"/v1/assets/upload", "/v1/assets/import-url", "/v1/assets/import-archive"}

# Auth endpoints with per-IP stricter rate limits (anti-brute-force)
AUTH_RATE_LIMITS: dict[str, str] = {
    "/v1/auth/login": "auth_login_rate_limit",
    "/v1/auth/register": "auth_register_rate_limit",
    "/v1/auth/refresh": "auth_refresh_rate_limit",
}

# Local memory fallback constants
_FALLBACK_MAX_KEYS = 10_000
_FALLBACK_CLEANUP_INTERVAL = 60  # seconds
_REDIS_LOG_INTERVAL = 60  # seconds — avoid log storms


class _LocalRateLimiter:
    """Fixed-window in-memory rate limiter used when Redis is unavailable.

    Thread-safe via a lock. Uses conservative limits (50% of normal).
    Automatically cleans up expired entries every 60 seconds.
    Caps stored keys at 10,000 to prevent OOM.
    """

    def __init__(self) -> None:
        self._counts: dict[str, tuple[int, float]] = {}  # key -> (count, window_start)
        self._lock = threading.Lock()
        self._last_cleanup = time.time()

    def check(self, key: str, limit: int) -> tuple[bool, int]:
        """Check if request is allowed under the fallback limiter.

        Args:
            key: Rate limit key (identity + category).
            limit: The *original* limit. Fallback uses 50% of this value.

        Returns:
            (allowed, current_count) tuple.
        """
        now = time.time()
        conservative_limit = max(1, limit // 2)

        with self._lock:
            # Periodic cleanup
            if now - self._last_cleanup > _FALLBACK_CLEANUP_INTERVAL:
                self._cleanup(now)

            entry = self._counts.get(key)
            if entry is None or now - entry[1] >= 60:
                # New window
                if len(self._counts) >= _FALLBACK_MAX_KEYS:
                    # Evict oldest entries to stay under cap
                    self._evict_oldest(len(self._counts) // 4)
                self._counts[key] = (1, now)
                return True, 1

            count, window_start = entry
            count += 1
            self._counts[key] = (count, window_start)

            if count > conservative_limit:
                return False, count
            return True, count

    def _cleanup(self, now: float) -> None:
        """Remove entries whose window has expired (> 60s old)."""
        expired = [k for k, (_, ws) in self._counts.items() if now - ws >= 60]
        for k in expired:
            del self._counts[k]
        self._last_cleanup = now

    def _evict_oldest(self, n: int) -> None:
        """Evict N oldest entries when at capacity."""
        sorted_keys = sorted(self._counts, key=lambda k: self._counts[k][1])
        for k in sorted_keys[:n]:
            del self._counts[k]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiter using Redis sorted sets.

    Uses tenant_id from JWT for authenticated requests,
    falls back to client IP for unauthenticated requests.

    When Redis is unavailable, degrades to a local in-memory fixed-window
    limiter with conservative thresholds (50% of normal limits).
    """

    def __init__(self, app, redis_client: aioredis.Redis | None = None) -> None:  # type: ignore[override]
        super().__init__(app)
        self._redis: aioredis.Redis | None = redis_client
        self._fallback = _LocalRateLimiter()
        self._last_redis_warning: float = 0.0

    async def _get_redis(self) -> aioredis.Redis | None:
        if self._redis is None:
            try:
                settings = get_settings()
                self._redis = aioredis.from_url(settings.redis_url)
            except Exception as e:
                self._log_redis_unavailable(e)
                return None
        return self._redis

    def _log_redis_unavailable(self, error: Exception) -> None:
        """Log Redis unavailability at most once per _REDIS_LOG_INTERVAL seconds."""
        now = time.time()
        if now - self._last_redis_warning >= _REDIS_LOG_INTERVAL:
            logger.warning("Rate limiter Redis unavailable, using local fallback: %s", error)
            self._last_redis_warning = now

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
                )
                tid = payload.get("tenant_id")
                if tid:
                    return f"tenant:{tid}"
            except Exception:
                pass
        # Fallback to IP
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    def _get_limit_and_identity(self, request: Request) -> tuple[int, str]:
        """Determine rate limit and identity key based on request path."""
        settings = get_settings()
        path = request.url.path
        identity = self._extract_identity(request)

        auth_setting = AUTH_RATE_LIMITS.get(path)
        if auth_setting:
            limit = getattr(settings, auth_setting)
            client_ip = request.client.host if request.client else "unknown"
            identity = f"ip:{client_ip}"
        elif path in UPLOAD_PATHS:
            limit = settings.upload_rate_limit_per_minute
        else:
            limit = settings.rate_limit_per_minute

        category = "auth" if auth_setting else ("upload" if path in UPLOAD_PATHS else "api")
        return limit, f"ratelimit:{identity}:{category}"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # Skip exempt paths
        if path in EXEMPT_PATHS:
            return await call_next(request)

        limit, key = self._get_limit_and_identity(request)

        r = await self._get_redis()
        if r is None:
            return await self._dispatch_with_fallback(request, call_next, key, limit)

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
            # Redis failed mid-operation — degrade to local fallback
            self._log_redis_unavailable(e)
            self._redis = None  # Force reconnect on next request
            return await self._dispatch_with_fallback(request, call_next, key, limit)

    async def _dispatch_with_fallback(
        self, request: Request, call_next: RequestResponseEndpoint, key: str, limit: int
    ) -> Response:
        """Handle request using local in-memory rate limiter."""
        allowed, count = self._fallback.check(key, limit)
        conservative_limit = max(1, limit // 2)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": f"请求过于频繁，每分钟最多 {conservative_limit} 次，请稍后再试",
                    "detail": {"limit": conservative_limit, "current": count, "retry_after": 60, "mode": "fallback"},
                },
                headers={"Retry-After": "60"},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(conservative_limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, conservative_limit - count))
        return response
