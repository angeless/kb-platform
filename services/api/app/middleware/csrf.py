"""CSRF protection middleware using custom header verification.

Requires `X-Requested-With: XMLHttpRequest` on all state-changing requests
(POST, PUT, PATCH, DELETE). This prevents cross-site form submissions since
browsers enforce CORS preflight for requests with custom headers.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Methods that modify state and require CSRF protection
_PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Paths exempt from CSRF check (public endpoints, health checks)
_EXEMPT_PATHS = {
    "/healthz",
    "/readyz",
    "/health",
    "/health/deep",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/metrics",
}


class CsrfMiddleware(BaseHTTPMiddleware):
    """Reject state-changing requests without X-Requested-With header."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in _PROTECTED_METHODS:
            path = request.url.path.rstrip("/")
            if path not in _EXEMPT_PATHS:
                xrw = request.headers.get("X-Requested-With", "")
                if xrw != "XMLHttpRequest":
                    return JSONResponse(
                        status_code=403,
                        content={
                            "error_code": "CSRF_HEADER_MISSING",
                            "message": "缺少 CSRF 保护头",
                            "detail": {},
                        },
                    )

        return await call_next(request)
