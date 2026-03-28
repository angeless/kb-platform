"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from shared_config.settings import get_settings
from shared_errors import register_exception_handlers

from .logging_config import setup_logging
from .middleware.csrf import CsrfMiddleware
from .middleware.metrics import MetricsMiddleware
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
from .routers.qa import router as qa_router
from .routers.cross_refs import router as cross_refs_router
from .routers.api_keys import router as api_keys_router
from .routers.agent import router as agent_router
from .routers.graph import router as graph_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown hooks."""
    logger.info("KB Platform API starting up")
    yield
    # Shutdown: close DB pool, Redis, flush logs
    logger.info("KB Platform API shutting down — closing connections")
    from shared_models.database import engine
    if engine is not None:
        await engine.dispose()
        logger.info("Database connection pool closed")
    logging.shutdown()


def _read_version() -> str:
    """Read version from VERSION file, fallback to 0.0.0."""
    try:
        from pathlib import Path
        version_file = Path(__file__).resolve().parents[3] / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()
    except Exception:
        pass
    return "0.0.0"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    setup_logging()
    app = FastAPI(title="KB Platform API", version=_read_version(), lifespan=lifespan)

    # Middleware (order matters: first added = outermost)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(CsrfMiddleware)

    # CORS middleware (outermost — added last so it wraps everything)
    settings = get_settings()
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
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
    app.include_router(qa_router)
    app.include_router(cross_refs_router)
    app.include_router(api_keys_router)
    app.include_router(agent_router)
    app.include_router(graph_router)

    # Custom OpenAPI schema: add Bearer security scheme
    _PUBLIC_PATHS = {"/api/health", "/healthz", "/readyz", "/metrics", "/api/versions", "/api/health/ready"}

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description="KB Platform — AI 知识整理与知识系统构建平台 API",
            routes=app.routes,
        )
        schema.setdefault("components", {})["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT access token obtained from POST /v1/auth/login",
            }
        }
        # Apply BearerAuth to all paths except public ones
        for path, methods in schema.get("paths", {}).items():
            if path in _PUBLIC_PATHS:
                for method_detail in methods.values():
                    if isinstance(method_detail, dict):
                        method_detail["security"] = []
            else:
                for method_detail in methods.values():
                    if isinstance(method_detail, dict) and "security" not in method_detail:
                        method_detail["security"] = [{"BearerAuth": []}]
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi

    return app


app = create_app()
