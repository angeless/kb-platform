"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared_config.settings import get_settings
from shared_errors import register_exception_handlers

from .middleware.rate_limit import RateLimitMiddleware
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
from .routers.ws import router as ws_router
from .routers.export import router as export_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="KB Platform API", version="0.35.0")

    # Middleware (order matters: first added = outermost)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # CORS middleware (outermost — added last so it wraps everything)
    settings = get_settings()
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
    )

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
    app.include_router(ws_router)
    app.include_router(export_router)

    return app


app = create_app()
