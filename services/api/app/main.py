"""FastAPI application factory."""

from fastapi import FastAPI

from shared_errors import register_exception_handlers

from .middleware.request_id import RequestIdMiddleware
from .routers.health import router as health_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="KB Platform API", version="0.1.0")

    # Middleware
    app.add_middleware(RequestIdMiddleware)

    # Exception handlers
    register_exception_handlers(app)

    # Routers
    app.include_router(health_router)

    return app


app = create_app()
