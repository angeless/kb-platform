"""FastAPI application factory."""

from fastapi import FastAPI

from shared_errors import register_exception_handlers

from .middleware.request_id import RequestIdMiddleware
from .routers.health import router as health_router
from .routers.auth import router as auth_router
from .routers.projects import router as projects_router
from .routers.jobs import router as jobs_router
from .routers.assets import router as assets_router
from .routers.architectures import router as architectures_router
from .routers.docs import router as docs_router
from .routers.conflicts import router as conflicts_router
from .routers.model_providers import router as model_providers_router
from .routers.users import router as users_router
from .routers.search import router as search_router
from .routers.ingestion import router as ingestion_router
from .routers.audit import router as audit_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="KB Platform API", version="0.1.0")

    # Middleware
    app.add_middleware(RequestIdMiddleware)

    # Exception handlers
    register_exception_handlers(app)

    # Routers
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(projects_router)
    app.include_router(jobs_router)
    app.include_router(assets_router)
    app.include_router(architectures_router)
    app.include_router(docs_router)
    app.include_router(conflicts_router)
    app.include_router(model_providers_router)
    app.include_router(users_router)
    app.include_router(search_router)
    app.include_router(ingestion_router)
    app.include_router(audit_router)

    return app


app = create_app()
