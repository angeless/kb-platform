"""Prometheus metrics collection middleware."""

import time

from prometheus_client import Counter, Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# --- HTTP metrics ---

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    labelnames=["method", "path", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

http_request_size_bytes = Histogram(
    "http_request_size_bytes",
    "HTTP request body size in bytes",
    labelnames=["method", "path"],
    buckets=(100, 1_000, 10_000, 100_000, 1_000_000),
)

http_response_size_bytes = Histogram(
    "http_response_size_bytes",
    "HTTP response body size in bytes",
    labelnames=["method", "path"],
    buckets=(100, 1_000, 10_000, 100_000, 1_000_000),
)

# --- LLM metrics (v0.49.8) ---

llm_calls_total = Counter(
    "llm_calls_total",
    "Total LLM API calls",
    labelnames=["model"],
)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total LLM tokens consumed",
    labelnames=["model", "type"],  # type: prompt | completion
)

active_connections = Gauge(
    "active_connections",
    "Number of active HTTP connections",
)

# Paths to skip from metrics collection (avoid high-cardinality)
_SKIP_PATHS = {"/metrics", "/healthz", "/readyz", "/docs", "/openapi.json", "/redoc"}


def _normalize_path(path: str) -> str:
    """Normalize path to reduce cardinality (replace UUIDs with {id})."""
    parts = path.split("/")
    normalized = []
    for part in parts:
        # UUID pattern: 8-4-4-4-12 hex chars or 32 hex chars
        if len(part) == 36 and part.count("-") == 4:
            normalized.append("{id}")
        elif len(part) == 32 and all(c in "0123456789abcdef" for c in part.lower()):
            normalized.append("{id}")
        else:
            normalized.append(part)
    return "/".join(normalized)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect Prometheus HTTP metrics for each request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        if path in _SKIP_PATHS:
            return await call_next(request)

        method = request.method
        normalized_path = _normalize_path(path)

        # Request size
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                http_request_size_bytes.labels(method=method, path=normalized_path).observe(int(content_length))
            except (ValueError, TypeError):
                pass

        active_connections.inc()
        start = time.monotonic()
        try:
            response = await call_next(request)
        finally:
            active_connections.dec()
        duration = time.monotonic() - start

        status = str(response.status_code)
        http_requests_total.labels(method=method, path=normalized_path, status=status).inc()
        http_request_duration_seconds.labels(method=method, path=normalized_path).observe(duration)

        # Response size
        resp_length = response.headers.get("content-length")
        if resp_length:
            try:
                http_response_size_bytes.labels(method=method, path=normalized_path).observe(int(resp_length))
            except (ValueError, TypeError):
                pass

        return response
