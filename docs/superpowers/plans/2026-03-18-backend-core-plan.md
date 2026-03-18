# KB Platform 后端核心实施计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the backend core — API service + 4 shared packages + database migrations + docker-compose — as a fully testable, runnable system.

**Architecture:** Monorepo with shared packages installed via `pip install -e`. FastAPI async API service using SQLAlchemy 2.0 async ORM. PostgreSQL 16 + Redis 7 + MinIO via docker-compose. JWT auth with multi-tenant isolation.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy 2.0 (async), Alembic, Celery, PostgreSQL 16, Redis 7, MinIO, pytest, httpx

**Spec:** `docs/superpowers/specs/2026-03-18-backend-core-design.md`

---

## File Structure

### Root level
- `pyproject.toml` — workspace-level config (optional, for tooling like ruff/mypy)
- `docker-compose.yml` — already exists, keep as-is
- `.env.example` — already exists, keep as-is
- `.env` — local copy (gitignored)

### packages/shared-config/
- `pyproject.toml`
- `shared_config/__init__.py`
- `shared_config/settings.py` — pydantic-settings based config

### packages/shared-errors/
- `pyproject.toml`
- `shared_errors/__init__.py`
- `shared_errors/codes.py` — error code enums
- `shared_errors/exceptions.py` — AppException hierarchy + FastAPI handler

### packages/shared-models/
- `pyproject.toml`
- `shared_models/__init__.py`
- `shared_models/base.py` — Base model with id, created_at, updated_at
- `shared_models/database.py` — async engine + session factory
- `shared_models/tenant.py`
- `shared_models/user.py`
- `shared_models/project.py`
- `shared_models/asset.py` — asset + asset_chunk
- `shared_models/architecture.py` — architecture + architecture_node
- `shared_models/knowledge.py` — knowledge_doc + knowledge_doc_version + source_ref + conflict_record
- `shared_models/job.py`
- `shared_models/model_config.py` — model_provider + model_route
- `shared_models/audit.py` — audit_log

### packages/shared-schemas/
- `pyproject.toml`
- `shared_schemas/__init__.py`
- `shared_schemas/common.py` — pagination, response wrappers
- `shared_schemas/auth.py`
- `shared_schemas/project.py`
- `shared_schemas/asset.py`
- `shared_schemas/architecture.py`
- `shared_schemas/knowledge.py`
- `shared_schemas/job.py`
- `shared_schemas/model_config.py`
- `shared_schemas/user.py`

### infra/sql/
- `alembic.ini`
- `alembic/env.py`
- `alembic/versions/` — migration scripts

### services/api/
- `pyproject.toml`
- `app/__init__.py`
- `app/main.py` — FastAPI app, lifespan, middleware registration
- `app/deps.py` — dependency injection (get_db, get_current_user, get_tenant_id)
- `app/middleware/auth.py` — JWT verification
- `app/middleware/tenant.py` — tenant isolation
- `app/middleware/request_id.py` — request_id injection
- `app/routers/__init__.py`
- `app/routers/auth.py`
- `app/routers/projects.py`
- `app/routers/assets.py`
- `app/routers/jobs.py`
- `app/routers/architectures.py`
- `app/routers/docs.py`
- `app/routers/conflicts.py`
- `app/routers/model_providers.py`
- `app/routers/users.py`
- `app/routers/health.py`
- `app/services/auth_service.py`
- `app/services/project_service.py`
- `app/services/asset_service.py`
- `app/services/job_service.py`
- `app/services/architecture_service.py`
- `app/services/doc_service.py`
- `app/services/conflict_service.py`
- `app/services/model_provider_service.py`
- `app/services/user_service.py`
- `app/utils/crypto.py` — AES-256-GCM encrypt/decrypt
- `app/utils/security.py` — password hashing, JWT creation/verification
- `tests/conftest.py` — fixtures (test DB, client, auth headers)
- `tests/test_health.py`
- `tests/test_auth.py`
- `tests/test_projects.py`
- `tests/test_assets.py`
- `tests/test_jobs.py`
- `tests/test_architectures.py`
- `tests/test_docs.py`
- `tests/test_conflicts.py`
- `tests/test_model_providers.py`
- `tests/test_users.py`

---

## Chunk 1: Foundation — Scaffolding + Shared Packages

### Task 1: Initialize Git and Project Structure

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml` (root)
- Create: `.env` (local, gitignored)

- [ ] **Step 1: Initialize git repository**

```bash
cd /Users/angelwang/knowledge_SQL
git init
```

- [ ] **Step 2: Create .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.eggs/
*.egg

# Virtual environments
.venv/
venv/
env/

# IDE
.idea/
.vscode/
*.swp

# Environment
.env
.env.local

# Testing
.pytest_cache/
.coverage
htmlcov/

# OS
.DS_Store
Thumbs.db

# Alembic
alembic/versions/__pycache__/
```

- [ ] **Step 3: Create root pyproject.toml for shared tooling**

```toml
[project]
name = "kb-platform"
version = "0.1.0"
requires-python = ">=3.12"

[tool.ruff]
target-version = "py312"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["services/api/tests"]
```

- [ ] **Step 4: Copy .env.example to .env**

```bash
cp .env.example .env
```

- [ ] **Step 5: Create directory structure**

```bash
mkdir -p packages/shared-config/shared_config
mkdir -p packages/shared-errors/shared_errors
mkdir -p packages/shared-models/shared_models
mkdir -p packages/shared-schemas/shared_schemas
mkdir -p services/api/app/{routers,services,middleware,utils}
mkdir -p services/api/tests
mkdir -p infra/sql/alembic/versions
```

- [ ] **Step 6: Create all __init__.py files**

```bash
touch packages/shared-config/shared_config/__init__.py
touch packages/shared-errors/shared_errors/__init__.py
touch packages/shared-models/shared_models/__init__.py
touch packages/shared-schemas/shared_schemas/__init__.py
touch services/api/app/__init__.py
touch services/api/app/routers/__init__.py
touch services/api/app/services/__init__.py
touch services/api/app/middleware/__init__.py
touch services/api/app/utils/__init__.py
touch services/api/tests/__init__.py
```

- [ ] **Step 7: Commit**

```bash
git add .gitignore pyproject.toml .env.example docker-compose.yml manifest.json
git add packages/ services/api/app/ services/api/tests/ infra/
git add docs/ examples/ openapi/
git commit -m "chore: initialize project structure with directories and config"
```

---

### Task 2: shared-config Package

**Files:**
- Create: `packages/shared-config/pyproject.toml`
- Create: `packages/shared-config/shared_config/settings.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "shared-config"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "pydantic-settings>=2.0",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 2: Write settings.py**

Read `.env.example` for all variable names. Create a `pydantic-settings` class that reads them.

```python
"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "kb-platform"
    app_port: int = 8080
    debug: bool = False

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "kb_platform"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        """Sync URL for Alembic migrations."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # MinIO / S3
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "kb-assets"
    s3_region: str = "us-east-1"

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Encryption
    encryption_key: str = "change-me-32-byte-key-for-aes256"

    # Rate Limiting
    rate_limit_per_minute: int = 100
    upload_rate_limit_per_minute: int = 20

    # Upload
    max_upload_size_mb: int = 100

    # Logging
    log_level: str = "INFO"


def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 3: Verify import works**

```bash
cd /Users/angelwang/knowledge_SQL
pip install -e packages/shared-config
python -c "from shared_config.settings import get_settings; s = get_settings(); print(s.app_name)"
```

Expected: `kb-platform`

- [ ] **Step 4: Commit**

```bash
git add packages/shared-config/
git commit -m "feat: add shared-config package with pydantic-settings"
```

---

### Task 3: shared-errors Package

**Files:**
- Create: `packages/shared-errors/pyproject.toml`
- Create: `packages/shared-errors/shared_errors/codes.py`
- Create: `packages/shared-errors/shared_errors/exceptions.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "shared-errors"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.110",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 2: Write codes.py**

```python
"""Unified error codes for the KB Platform."""

from enum import StrEnum


class ErrorCode(StrEnum):
    # Auth
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"
    AUTH_INSUFFICIENT_ROLE = "AUTH_INSUFFICIENT_ROLE"
    AUTH_EMAIL_ALREADY_EXISTS = "AUTH_EMAIL_ALREADY_EXISTS"
    AUTH_REFRESH_TOKEN_INVALID = "AUTH_REFRESH_TOKEN_INVALID"

    # Project
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    PROJECT_NAME_DUPLICATE = "PROJECT_NAME_DUPLICATE"

    # Asset
    ASSET_NOT_FOUND = "ASSET_NOT_FOUND"
    ASSET_DUPLICATE_HASH = "ASSET_DUPLICATE_HASH"
    ASSET_TYPE_NOT_ALLOWED = "ASSET_TYPE_NOT_ALLOWED"
    ASSET_TOO_LARGE = "ASSET_TOO_LARGE"

    # Architecture
    ARCH_NOT_FOUND = "ARCH_NOT_FOUND"
    ARCH_NODE_NOT_FOUND = "ARCH_NODE_NOT_FOUND"
    ARCH_ALREADY_PUBLISHED = "ARCH_ALREADY_PUBLISHED"

    # Knowledge Doc
    DOC_NOT_FOUND = "DOC_NOT_FOUND"
    DOC_ALREADY_PUBLISHED = "DOC_ALREADY_PUBLISHED"

    # Job
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    JOB_ALREADY_RUNNING = "JOB_ALREADY_RUNNING"

    # Conflict
    CONFLICT_NOT_FOUND = "CONFLICT_NOT_FOUND"
    CONFLICT_ALREADY_RESOLVED = "CONFLICT_ALREADY_RESOLVED"

    # Model Config
    MODEL_PROVIDER_NOT_FOUND = "MODEL_PROVIDER_NOT_FOUND"
    MODEL_ROUTE_NOT_FOUND = "MODEL_ROUTE_NOT_FOUND"
    MODEL_PROVIDER_UNREACHABLE = "MODEL_PROVIDER_UNREACHABLE"

    # User
    USER_NOT_FOUND = "USER_NOT_FOUND"

    # System
    SYSTEM_INTERNAL_ERROR = "SYSTEM_INTERNAL_ERROR"
    SYSTEM_RATE_LIMITED = "SYSTEM_RATE_LIMITED"
    SYSTEM_SSRF_BLOCKED = "SYSTEM_SSRF_BLOCKED"
```

- [ ] **Step 3: Write exceptions.py**

```python
"""Custom exceptions and FastAPI exception handlers."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .codes import ErrorCode


class AppException(Exception):
    """Base exception for all business errors."""

    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        status_code: int = 400,
        detail: dict | None = None,
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(message)


class NotFoundException(AppException):
    def __init__(self, error_code: ErrorCode, message: str, detail: dict | None = None):
        super().__init__(error_code=error_code, message=message, status_code=404, detail=detail)


class ConflictException(AppException):
    def __init__(self, error_code: ErrorCode, message: str, detail: dict | None = None):
        super().__init__(error_code=error_code, message=message, status_code=409, detail=detail)


class ForbiddenException(AppException):
    def __init__(self, message: str = "权限不足", detail: dict | None = None):
        super().__init__(
            error_code=ErrorCode.AUTH_INSUFFICIENT_ROLE, message=message, status_code=403, detail=detail
        )


class UnauthorizedException(AppException):
    def __init__(self, error_code: ErrorCode = ErrorCode.AUTH_TOKEN_INVALID, message: str = "认证失败"):
        super().__init__(error_code=error_code, message=message, status_code=401)


class RateLimitedException(AppException):
    def __init__(self):
        super().__init__(
            error_code=ErrorCode.SYSTEM_RATE_LIMITED, message="请求过于频繁", status_code=429
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": exc.error_code,
                "message": exc.message,
                "detail": exc.detail,
                "meta": {"request_id": getattr(request.state, "request_id", None)},
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "error_code": ErrorCode.SYSTEM_INTERNAL_ERROR,
                "message": "内部服务器错误",
                "detail": {},
                "meta": {"request_id": getattr(request.state, "request_id", None)},
            },
        )
```

- [ ] **Step 4: Update __init__.py for convenient imports**

```python
# packages/shared-errors/shared_errors/__init__.py
from .codes import ErrorCode
from .exceptions import (
    AppException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
    RateLimitedException,
    UnauthorizedException,
    register_exception_handlers,
)

__all__ = [
    "ErrorCode",
    "AppException",
    "ConflictException",
    "ForbiddenException",
    "NotFoundException",
    "RateLimitedException",
    "UnauthorizedException",
    "register_exception_handlers",
]
```

- [ ] **Step 5: Verify import works**

```bash
pip install -e packages/shared-errors
python -c "from shared_errors import ErrorCode, AppException; print(ErrorCode.AUTH_INVALID_CREDENTIALS)"
```

Expected: `AUTH_INVALID_CREDENTIALS`

- [ ] **Step 6: Commit**

```bash
git add packages/shared-errors/
git commit -m "feat: add shared-errors package with error codes and exception handlers"
```

---

### Task 4: shared-models Package — Base and Database

**Files:**
- Create: `packages/shared-models/pyproject.toml`
- Create: `packages/shared-models/shared_models/base.py`
- Create: `packages/shared-models/shared_models/database.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "shared-models"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "shared-config",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 2: Write base.py**

```python
"""Base SQLAlchemy model with common fields."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models. Provides id, created_at, updated_at."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
```

- [ ] **Step 3: Write database.py**

```python
"""Async database engine and session factory."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared_config.settings import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=20,
    max_overflow=10,
)

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

- [ ] **Step 4: Verify import**

```bash
pip install -e packages/shared-models
python -c "from shared_models.base import Base; print(Base.__name__)"
```

Expected: `Base`

- [ ] **Step 5: Commit**

```bash
git add packages/shared-models/pyproject.toml packages/shared-models/shared_models/__init__.py
git add packages/shared-models/shared_models/base.py packages/shared-models/shared_models/database.py
git commit -m "feat: add shared-models base and database engine"
```

---

### Task 5: shared-models — All Entity Models

**Files:**
- Create: `packages/shared-models/shared_models/tenant.py`
- Create: `packages/shared-models/shared_models/user.py`
- Create: `packages/shared-models/shared_models/project.py`
- Create: `packages/shared-models/shared_models/asset.py`
- Create: `packages/shared-models/shared_models/architecture.py`
- Create: `packages/shared-models/shared_models/knowledge.py`
- Create: `packages/shared-models/shared_models/job.py`
- Create: `packages/shared-models/shared_models/model_config.py`
- Create: `packages/shared-models/shared_models/audit.py`

- [ ] **Step 1: Write tenant.py**

```python
"""Tenant model."""

import uuid

from sqlalchemy import Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Tenant(Base):
    __tablename__ = "tenant"
    __table_args__ = (
        Index("ix_tenant_status", "status"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    # Relationships
    users = relationship("User", back_populates="tenant", lazy="selectin")
    projects = relationship("Project", back_populates="tenant", lazy="selectin")
```

- [ ] **Step 2: Write user.py**

```python
"""User model."""

import uuid

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class User(Base):
    __tablename__ = "user"
    __table_args__ = (
        Index("ix_user_tenant_status", "tenant_id", "status"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="viewer")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
```

- [ ] **Step 3: Write project.py**

```python
"""Project model."""

import uuid

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Project(Base):
    __tablename__ = "project"
    __table_args__ = (
        Index("ix_project_tenant_status", "tenant_id", "status"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    industry_hint: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    # Relationships
    tenant = relationship("Tenant", back_populates="projects")
```

- [ ] **Step 4: Write asset.py**

```python
"""Asset and AssetChunk models."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Asset(Base):
    __tablename__ = "asset"
    __table_args__ = (
        Index("ix_asset_project_parse_status", "project_id", "parse_status"),
        UniqueConstraint("project_id", "file_hash", name="uq_asset_project_file_hash"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project.id"), nullable=False
    )
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    object_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    parse_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=False
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    chunks = relationship("AssetChunk", back_populates="asset", lazy="selectin")


class AssetChunk(Base):
    __tablename__ = "asset_chunk"

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    page_or_timestamp: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    asset = relationship("Asset", back_populates="chunks")
```

- [ ] **Step 5: Write architecture.py**

```python
"""Architecture and ArchitectureNode models."""

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Architecture(Base):
    __tablename__ = "architecture"
    __table_args__ = (
        Index("ix_architecture_project_status", "project_id", "status"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="0.1.0")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    levels_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    nodes = relationship("ArchitectureNode", back_populates="architecture", lazy="selectin")


class ArchitectureNode(Base):
    __tablename__ = "architecture_node"
    __table_args__ = (
        Index("ix_arch_node_arch_level", "architecture_id", "level"),
        Index("ix_arch_node_parent", "parent_id"),
    )

    architecture_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("architecture.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("architecture_node.id"), nullable=True
    )
    node_name: Mapped[str] = mapped_column(String(200), nullable=False)
    node_type: Mapped[str] = mapped_column(String(30), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    accept_types: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    reject_types: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    update_policy: Mapped[str | None] = mapped_column(String(30), nullable=True)
    review_policy: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")

    # Relationships
    architecture = relationship("Architecture", back_populates="nodes")
    children = relationship("ArchitectureNode", back_populates="parent", lazy="selectin")
    parent = relationship("ArchitectureNode", back_populates="children", remote_side="ArchitectureNode.id")
```

- [ ] **Step 6: Write knowledge.py**

```python
"""Knowledge document models: KnowledgeDoc, KnowledgeDocVersion, SourceRef, ConflictRecord."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class KnowledgeDoc(Base):
    __tablename__ = "knowledge_doc"
    __table_args__ = (
        Index("ix_knowledge_doc_project_status", "project_id", "status"),
        Index("ix_knowledge_doc_node", "node_id"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project.id"), nullable=False
    )
    node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("architecture_node.id"), nullable=True
    )
    doc_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")

    # Relationships
    versions = relationship("KnowledgeDocVersion", back_populates="doc", lazy="selectin")


class KnowledgeDocVersion(Base):
    __tablename__ = "knowledge_doc_version"
    __table_args__ = (
        Index("ix_doc_version_doc_version", "doc_id", "version"),
    )

    doc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_doc.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=False
    )

    # Relationships
    doc = relationship("KnowledgeDoc", back_populates="versions")
    source_refs = relationship("SourceRef", back_populates="doc_version", lazy="selectin")


class SourceRef(Base):
    __tablename__ = "source_ref"

    doc_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_doc_version.id", ondelete="CASCADE"), nullable=False
    )
    asset_chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset_chunk.id"), nullable=False
    )
    location_hint: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Relationships
    doc_version = relationship("KnowledgeDocVersion", back_populates="source_refs")


class ConflictRecord(Base):
    __tablename__ = "conflict_record"
    __table_args__ = (
        Index("ix_conflict_project_status", "project_id", "status"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project.id"), nullable=False
    )
    node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("architecture_node.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
```

- [ ] **Step 7: Write job.py**

```python
"""Job model for async task tracking."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Job(Base):
    __tablename__ = "job"
    __table_args__ = (
        Index("ix_job_project_status", "project_id", "status"),
        Index("ix_job_celery_task", "celery_task_id"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project.id"), nullable=False
    )
    job_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    celery_task_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 8: Write model_config.py**

```python
"""Model provider and model route configuration models."""

import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ModelProvider(Base):
    __tablename__ = "model_provider"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False
    )
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    max_context: Mapped[int] = mapped_column(Integer, nullable=False, default=4096)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    # Relationships
    routes = relationship("ModelRoute", back_populates="provider", lazy="selectin")


class ModelRoute(Base):
    __tablename__ = "model_route"
    __table_args__ = (
        Index("ix_model_route_tenant_task", "tenant_id", "task_type"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False
    )
    task_type: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_provider.id"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_limit_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Relationships
    provider = relationship("ModelProvider", back_populates="routes")
```

- [ ] **Step 9: Write audit.py**

```python
"""Audit log model — intentionally no foreign keys for durability."""

import uuid

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_tenant_created", "tenant_id", "created_at"),
        Index("ix_audit_log_resource", "resource_type", "resource_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
```

- [ ] **Step 10: Update __init__.py to export all models**

```python
# packages/shared-models/shared_models/__init__.py
from .base import Base
from .tenant import Tenant
from .user import User
from .project import Project
from .asset import Asset, AssetChunk
from .architecture import Architecture, ArchitectureNode
from .knowledge import KnowledgeDoc, KnowledgeDocVersion, SourceRef, ConflictRecord
from .job import Job
from .model_config import ModelProvider, ModelRoute
from .audit import AuditLog
from .database import engine, async_session_factory, get_db_session

__all__ = [
    "Base",
    "Tenant", "User", "Project",
    "Asset", "AssetChunk",
    "Architecture", "ArchitectureNode",
    "KnowledgeDoc", "KnowledgeDocVersion", "SourceRef", "ConflictRecord",
    "Job",
    "ModelProvider", "ModelRoute",
    "AuditLog",
    "engine", "async_session_factory", "get_db_session",
]
```

- [ ] **Step 11: Verify all models import cleanly**

```bash
pip install -e packages/shared-models
python -c "from shared_models import Base, Tenant, User, Project, Asset, Job; print('All models OK')"
```

Expected: `All models OK`

- [ ] **Step 12: Commit**

```bash
git add packages/shared-models/
git commit -m "feat: add all SQLAlchemy entity models (tenant, user, project, asset, architecture, knowledge, job, model_config, audit)"
```

---

### Task 6: shared-schemas Package

**Files:**
- Create: `packages/shared-schemas/pyproject.toml`
- Create: `packages/shared-schemas/shared_schemas/common.py`
- Create: `packages/shared-schemas/shared_schemas/auth.py`
- Create: `packages/shared-schemas/shared_schemas/project.py`
- Create: `packages/shared-schemas/shared_schemas/asset.py`
- Create: `packages/shared-schemas/shared_schemas/architecture.py`
- Create: `packages/shared-schemas/shared_schemas/knowledge.py`
- Create: `packages/shared-schemas/shared_schemas/job.py`
- Create: `packages/shared-schemas/shared_schemas/model_config.py`
- Create: `packages/shared-schemas/shared_schemas/user.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "shared-schemas"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.0",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 2: Write common.py — pagination and response wrappers**

```python
"""Common schemas: pagination, response wrappers."""

from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginationMeta(BaseModel):
    request_id: str | None = None
    page: int
    page_size: int
    total: int


class SingleMeta(BaseModel):
    request_id: str | None = None


class DataResponse(BaseModel, Generic[T]):
    data: T
    meta: SingleMeta = SingleMeta()


class ListResponse(BaseModel, Generic[T]):
    data: list[T]
    meta: PaginationMeta
```

- [ ] **Step 3: Write auth.py**

```python
"""Auth request/response schemas."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    tenant_name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class RegisterResponse(BaseModel):
    tenant_id: UUID
    user_id: UUID
    email: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str
```

- [ ] **Step 4: Write project.py**

```python
"""Project schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    industry_hint: str | None = Field(None, max_length=100)


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    industry_hint: str | None = Field(None, max_length=100)
    status: str | None = Field(None, pattern="^(active|archived)$")


class ProjectOut(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    industry_hint: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 5: Write asset.py**

```python
"""Asset schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class AssetOut(BaseModel):
    id: UUID
    project_id: UUID
    asset_type: str
    filename: str
    source_url: str | None
    file_hash: str | None
    file_size: int | None
    parse_status: str
    uploaded_by: UUID
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class ImportUrlRequest(BaseModel):
    project_id: UUID
    url: HttpUrl


class ImportArchiveRequest(BaseModel):
    project_id: UUID
```

- [ ] **Step 6: Write architecture.py**

```python
"""Architecture schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ArchitectureOut(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    version: str
    status: str
    levels_json: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NodeCreate(BaseModel):
    parent_id: UUID | None = None
    node_name: str = Field(..., min_length=1, max_length=200)
    node_type: str = Field(..., pattern="^(category|topic|document|glossary|conflict|index)$")
    level: int = Field(default=0, ge=0)
    description: str | None = None
    accept_types: dict | None = None
    reject_types: dict | None = None
    update_policy: str | None = None
    review_policy: str | None = None


class NodeUpdate(BaseModel):
    node_name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    accept_types: dict | None = None
    reject_types: dict | None = None
    update_policy: str | None = None
    review_policy: str | None = None
    status: str | None = Field(None, pattern="^(draft|reviewing|published|deprecated)$")


class NodeOut(BaseModel):
    id: UUID
    architecture_id: UUID
    parent_id: UUID | None
    node_name: str
    node_type: str
    level: int
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 7: Write knowledge.py**

```python
"""Knowledge document schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class KnowledgeDocOut(BaseModel):
    id: UUID
    project_id: UUID
    node_id: UUID | None
    doc_type: str
    title: str
    current_version: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocVersionOut(BaseModel):
    id: UUID
    doc_id: UUID
    version: int
    content_md: str
    change_reason: str | None
    created_by: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class ConflictOut(BaseModel):
    id: UUID
    project_id: UUID
    node_id: UUID | None
    description: str
    status: str
    resolved_by: UUID | None
    resolved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConflictResolveRequest(BaseModel):
    resolution_note: str = Field(..., min_length=1)
```

- [ ] **Step 8: Write job.py**

```python
"""Job schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    project_id: UUID
    job_type: str = Field(
        ..., pattern="^(ingest|classify|architecture_draft|kb_generate|review_publish)$"
    )


class JobOut(BaseModel):
    id: UUID
    project_id: UUID
    job_type: str
    status: str
    error_message: str | None
    retry_count: int
    celery_task_id: str | None
    created_by: UUID
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 9: Write model_config.py**

```python
"""Model provider and route schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ModelProviderCreate(BaseModel):
    provider_name: str = Field(..., min_length=1, max_length=50)
    api_key: str = Field(..., min_length=1)
    base_url: str | None = Field(None, max_length=500)
    timeout_seconds: int = Field(default=60, ge=1, le=600)
    max_context: int = Field(default=4096, ge=1)


class ModelProviderOut(BaseModel):
    id: UUID
    tenant_id: UUID
    provider_name: str
    api_key_masked: str  # e.g. "sk-****xxxx"
    base_url: str | None
    timeout_seconds: int
    max_context: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ModelProviderTestRequest(BaseModel):
    provider_id: UUID


class ModelRouteCreate(BaseModel):
    task_type: str = Field(..., min_length=1, max_length=30)
    provider_id: UUID
    model_name: str = Field(..., min_length=1, max_length=100)
    priority: int = Field(default=0, ge=0)
    cost_limit_usd: Decimal | None = Field(None, ge=0)


class ModelRouteUpdate(BaseModel):
    model_name: str | None = Field(None, min_length=1, max_length=100)
    priority: int | None = Field(None, ge=0)
    cost_limit_usd: Decimal | None = Field(None, ge=0)


class ModelRouteOut(BaseModel):
    id: UUID
    tenant_id: UUID
    task_type: str
    provider_id: UUID
    model_name: str
    priority: int
    cost_limit_usd: Decimal | None
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 10: Write user.py**

```python
"""User management schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserInviteRequest(BaseModel):
    email: EmailStr
    role: str = Field(
        default="viewer",
        pattern="^(tenant_admin|project_admin|editor|reviewer|viewer)$",
    )


class UserUpdate(BaseModel):
    role: str | None = Field(
        None, pattern="^(tenant_admin|project_admin|editor|reviewer|viewer)$"
    )
    status: str | None = Field(None, pattern="^(active|disabled)$")


class UserOut(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    role: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 11: Update __init__.py**

```python
# packages/shared-schemas/shared_schemas/__init__.py
from .common import DataResponse, ListResponse, PaginationMeta, PaginationParams, SingleMeta

__all__ = [
    "DataResponse", "ListResponse", "PaginationMeta", "PaginationParams", "SingleMeta",
]
```

- [ ] **Step 12: Verify**

```bash
pip install -e packages/shared-schemas
python -c "from shared_schemas.auth import RegisterRequest; print(RegisterRequest.model_fields.keys())"
```

Expected: `dict_keys(['tenant_name', 'email', 'password'])`

- [ ] **Step 13: Commit**

```bash
git add packages/shared-schemas/
git commit -m "feat: add shared-schemas package with all Pydantic request/response schemas"
```

---

## Chunk 2: Database Migrations + API Core

### Task 7: Alembic Setup and Initial Migration

**Files:**
- Create: `infra/sql/alembic.ini`
- Create: `infra/sql/alembic/env.py`
- Create: `infra/sql/alembic/script.py.mako`

- [ ] **Step 1: Install alembic**

```bash
pip install alembic asyncpg psycopg2-binary
```

- [ ] **Step 2: Create alembic.ini**

```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql://postgres:postgres@localhost:5432/kb_platform

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 3: Create env.py**

```python
"""Alembic environment configuration."""

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add project root to path so shared packages are importable
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root / "packages" / "shared-models"))
sys.path.insert(0, str(project_root / "packages" / "shared-config"))

from shared_config.settings import get_settings
from shared_models import Base  # noqa: E402 — imports all models via __init__

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override URL from settings
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url_sync)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Create script.py.mako**

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 5: Start Docker services**

```bash
cd /Users/angelwang/knowledge_SQL
docker-compose up -d postgres redis minio
```

- [ ] **Step 6: Generate initial migration**

```bash
cd /Users/angelwang/knowledge_SQL/infra/sql
alembic revision --autogenerate -m "initial schema: all tables"
```

- [ ] **Step 7: Run migration**

```bash
cd /Users/angelwang/knowledge_SQL/infra/sql
alembic upgrade head
```

- [ ] **Step 8: Verify tables exist**

```bash
docker exec -it kb-postgres psql -U postgres -d kb_platform -c "\dt"
```

Expected: All 14 tables listed (tenant, user, project, asset, asset_chunk, architecture, architecture_node, knowledge_doc, knowledge_doc_version, source_ref, conflict_record, job, model_provider, model_route, audit_log)

- [ ] **Step 9: Commit**

```bash
git add infra/sql/
git commit -m "feat: add Alembic setup and initial migration with all tables"
```

---

### Task 8: API Service — Utilities (crypto + security)

**Files:**
- Create: `services/api/app/utils/crypto.py`
- Create: `services/api/app/utils/security.py`
- Create: `services/api/tests/test_utils.py`

- [ ] **Step 1: Write test for crypto**

```python
# services/api/tests/test_utils.py
"""Tests for crypto and security utilities."""

import pytest


class TestCrypto:
    def test_encrypt_decrypt_roundtrip(self):
        from app.utils.crypto import decrypt, encrypt

        key = "a" * 32  # 32-byte key
        plaintext = "sk-abc123secret"
        encrypted = encrypt(plaintext, key)
        assert encrypted != plaintext
        decrypted = decrypt(encrypted, key)
        assert decrypted == plaintext

    def test_mask_api_key(self):
        from app.utils.crypto import mask_api_key

        assert mask_api_key("sk-abc123xyz789") == "sk-a****9789"
        assert mask_api_key("short") == "****"
        assert mask_api_key("") == "****"


class TestSecurity:
    def test_password_hash_verify(self):
        from app.utils.security import hash_password, verify_password

        password = "MySecret123!"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False

    def test_jwt_create_decode(self):
        from app.utils.security import create_access_token, decode_token

        data = {"user_id": "123", "tenant_id": "456", "role": "editor"}
        token = create_access_token(data, secret="test-secret")
        decoded = decode_token(token, secret="test-secret")
        assert decoded["user_id"] == "123"
        assert decoded["tenant_id"] == "456"
        assert decoded["role"] == "editor"
        assert decoded["type"] == "access"
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd /Users/angelwang/knowledge_SQL
python -m pytest services/api/tests/test_utils.py -v
```

Expected: ImportError / FAIL

- [ ] **Step 3: Write crypto.py**

```python
"""AES-256-GCM encryption for API keys and sensitive data."""

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def encrypt(plaintext: str, key: str) -> str:
    """Encrypt plaintext with AES-256-GCM. Returns base64-encoded ciphertext."""
    key_bytes = key.encode("utf-8")[:32].ljust(32, b"\0")
    aesgcm = AESGCM(key_bytes)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def decrypt(encrypted: str, key: str) -> str:
    """Decrypt base64-encoded AES-256-GCM ciphertext."""
    key_bytes = key.encode("utf-8")[:32].ljust(32, b"\0")
    aesgcm = AESGCM(key_bytes)
    raw = base64.b64decode(encrypted)
    nonce, ciphertext = raw[:12], raw[12:]
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")


def mask_api_key(api_key: str) -> str:
    """Mask API key for display: show first 4 and last 4 chars."""
    if len(api_key) <= 8:
        return "****"
    return f"{api_key[:4]}****{api_key[-4:]}"
```

- [ ] **Step 4: Write security.py**

```python
"""Password hashing and JWT token management."""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(
    data: dict,
    secret: str,
    algorithm: str = "HS256",
    expires_minutes: int = 30,
) -> str:
    payload = {
        **data,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def create_refresh_token(
    data: dict,
    secret: str,
    algorithm: str = "HS256",
    expires_days: int = 7,
) -> str:
    payload = {
        **data,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=expires_days),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_token(token: str, secret: str, algorithm: str = "HS256") -> dict:
    return jwt.decode(token, secret, algorithms=[algorithm])
```

- [ ] **Step 5: Create api pyproject.toml**

```toml
[project]
name = "kb-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi[standard]>=0.110",
    "uvicorn[standard]>=0.27",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "redis>=5.0",
    "celery[redis]>=5.3",
    "bcrypt>=4.0",
    "PyJWT>=2.8",
    "cryptography>=42.0",
    "boto3>=1.34",
    "httpx>=0.27",
    "pydantic[email]>=2.0",
    "shared-config",
    "shared-errors",
    "shared-models",
    "shared-schemas",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 6: Install and run tests**

```bash
cd /Users/angelwang/knowledge_SQL
pip install -e services/api[dev]
python -m pytest services/api/tests/test_utils.py -v
```

Expected: 4 tests PASS

- [ ] **Step 7: Commit**

```bash
git add services/api/
git commit -m "feat: add crypto and security utilities with tests"
```

---

### Task 9: API Service — Core (main.py, deps.py, middleware, health)

**Files:**
- Create: `services/api/app/middleware/request_id.py`
- Create: `services/api/app/middleware/auth.py`
- Create: `services/api/app/deps.py`
- Create: `services/api/app/main.py`
- Create: `services/api/app/routers/health.py`
- Create: `services/api/tests/conftest.py`
- Create: `services/api/tests/test_health.py`

- [ ] **Step 1: Write test_health.py**

```python
"""Test health check endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_healthz(client: AsyncClient):
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_readyz(client: AsyncClient):
    resp = await client.get("/readyz")
    # May be 200 or 503 depending on DB availability in test
    assert resp.status_code in (200, 503)
```

- [ ] **Step 2: Write conftest.py**

```python
"""Shared test fixtures."""

import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared_config.settings import get_settings
from shared_models import Base

settings = get_settings()

# Use a separate test database
TEST_DB_URL = settings.database_url + "_test"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
test_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    """Create all tables in test DB, drop after tests."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    from app.deps import get_db
    from app.main import create_app

    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def auth_headers(db_session: AsyncSession) -> dict:
    """Create a test tenant + user, return auth headers."""
    from shared_models import Tenant, User

    from app.utils.security import create_access_token, hash_password

    tenant = Tenant(name="Test Tenant")
    db_session.add(tenant)
    await db_session.flush()

    user = User(
        tenant_id=tenant.id,
        email=f"test-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("testpass123"),
        role="tenant_admin",
    )
    db_session.add(user)
    await db_session.flush()

    token = create_access_token(
        {"user_id": str(user.id), "tenant_id": str(tenant.id), "role": user.role},
        secret=settings.jwt_secret,
    )
    return {"Authorization": f"Bearer {token}"}
```

- [ ] **Step 3: Write request_id.py middleware**

```python
"""Request ID middleware — attaches a unique ID to every request."""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response
```

- [ ] **Step 4: Write deps.py**

```python
"""FastAPI dependency injection."""

from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_config.settings import Settings, get_settings
from shared_errors import UnauthorizedException
from shared_models import User
from shared_models.database import get_db_session

from .utils.security import decode_token


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


def get_settings_dep() -> Settings:
    return get_settings()


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> User:
    """Extract and validate JWT from Authorization header, return User."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise UnauthorizedException()

    token = auth_header.split(" ", 1)[1]
    try:
        payload = decode_token(token, secret=settings.jwt_secret)
    except Exception:
        raise UnauthorizedException()

    if payload.get("type") != "access":
        raise UnauthorizedException()

    user_id = payload.get("user_id")
    if not user_id:
        raise UnauthorizedException()

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or user.status != "active":
        raise UnauthorizedException()

    return user


def get_tenant_id(user: User = Depends(get_current_user)) -> UUID:
    """Extract tenant_id from the current user for query filtering."""
    return user.tenant_id
```

- [ ] **Step 5: Write health.py router**

```python
"""Health check endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz():
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"status": "unavailable", "db": "disconnected"})
```

- [ ] **Step 6: Write main.py**

```python
"""FastAPI application factory."""

from fastapi import FastAPI

from shared_errors import register_exception_handlers

from .middleware.request_id import RequestIdMiddleware
from .routers import health


def create_app() -> FastAPI:
    app = FastAPI(
        title="KB Platform API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Middleware
    app.add_middleware(RequestIdMiddleware)

    # Exception handlers
    register_exception_handlers(app)

    # Routers
    app.include_router(health.router)

    return app


app = create_app()
```

- [ ] **Step 7: Run health tests**

```bash
cd /Users/angelwang/knowledge_SQL
python -m pytest services/api/tests/test_health.py -v
```

Expected: 2 tests PASS (healthz passes, readyz may pass or report 503)

- [ ] **Step 8: Commit**

```bash
git add services/api/
git commit -m "feat: add API core — main.py, deps, middleware, health endpoints with tests"
```

---

### Task 10: Auth Router + Service

**Files:**
- Create: `services/api/app/services/auth_service.py`
- Create: `services/api/app/routers/auth.py`
- Create: `services/api/tests/test_auth.py`

- [ ] **Step 1: Write test_auth.py**

```python
"""Test auth endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post("/v1/auth/register", json={
        "tenant_name": "Acme Corp",
        "email": "admin@acme.com",
        "password": "SecurePass123!",
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["email"] == "admin@acme.com"
    assert "tenant_id" in data
    assert "user_id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {
        "tenant_name": "Dup Corp",
        "email": "dup@example.com",
        "password": "SecurePass123!",
    }
    await client.post("/v1/auth/register", json=payload)
    resp = await client.post("/v1/auth/register", json=payload)
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "AUTH_EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    # Register first
    await client.post("/v1/auth/register", json={
        "tenant_name": "Login Corp",
        "email": "login@example.com",
        "password": "SecurePass123!",
    })
    # Login
    resp = await client.post("/v1/auth/login", json={
        "email": "login@example.com",
        "password": "SecurePass123!",
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/v1/auth/register", json={
        "tenant_name": "Wrong Corp",
        "email": "wrong@example.com",
        "password": "SecurePass123!",
    })
    resp = await client.post("/v1/auth/login", json={
        "email": "wrong@example.com",
        "password": "WrongPassword!",
    })
    assert resp.status_code == 401
    assert resp.json()["error_code"] == "AUTH_INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    await client.post("/v1/auth/register", json={
        "tenant_name": "Refresh Corp",
        "email": "refresh@example.com",
        "password": "SecurePass123!",
    })
    login_resp = await client.post("/v1/auth/login", json={
        "email": "refresh@example.com",
        "password": "SecurePass123!",
    })
    refresh_token = login_resp.json()["data"]["refresh_token"]
    resp = await client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()["data"]
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
python -m pytest services/api/tests/test_auth.py -v
```

- [ ] **Step 3: Write auth_service.py**

```python
"""Authentication business logic."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_config.settings import Settings
from shared_errors import ConflictException, ErrorCode, UnauthorizedException
from shared_models import Tenant, User

from app.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class AuthService:
    def __init__(self, db: AsyncSession, settings: Settings):
        self.db = db
        self.settings = settings

    async def register(self, tenant_name: str, email: str, password: str) -> dict:
        # Check email uniqueness
        existing = await self.db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise ConflictException(
                error_code=ErrorCode.AUTH_EMAIL_ALREADY_EXISTS,
                message="该邮箱已被注册",
            )

        # Create tenant
        tenant = Tenant(name=tenant_name)
        self.db.add(tenant)
        await self.db.flush()

        # Create admin user
        user = User(
            tenant_id=tenant.id,
            email=email,
            password_hash=hash_password(password),
            role="tenant_admin",
        )
        self.db.add(user)
        await self.db.flush()

        return {"tenant_id": tenant.id, "user_id": user.id, "email": user.email}

    async def login(self, email: str, password: str) -> dict:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedException(
                error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                message="邮箱或密码错误",
            )

        if user.status != "active":
            raise UnauthorizedException(message="账户已被禁用")

        token_data = {
            "user_id": str(user.id),
            "tenant_id": str(user.tenant_id),
            "role": user.role,
        }
        access_token = create_access_token(
            token_data,
            secret=self.settings.jwt_secret,
            expires_minutes=self.settings.access_token_expire_minutes,
        )
        refresh_token = create_refresh_token(
            token_data,
            secret=self.settings.jwt_secret,
            expires_days=self.settings.refresh_token_expire_days,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    async def refresh(self, refresh_token: str) -> dict:
        try:
            payload = decode_token(refresh_token, secret=self.settings.jwt_secret)
        except Exception:
            raise UnauthorizedException(
                error_code=ErrorCode.AUTH_REFRESH_TOKEN_INVALID,
                message="Refresh Token 无效或已过期",
            )

        if payload.get("type") != "refresh":
            raise UnauthorizedException(
                error_code=ErrorCode.AUTH_REFRESH_TOKEN_INVALID,
                message="Token 类型不正确",
            )

        token_data = {
            "user_id": payload["user_id"],
            "tenant_id": payload["tenant_id"],
            "role": payload["role"],
        }
        new_access = create_access_token(
            token_data,
            secret=self.settings.jwt_secret,
            expires_minutes=self.settings.access_token_expire_minutes,
        )
        new_refresh = create_refresh_token(
            token_data,
            secret=self.settings.jwt_secret,
            expires_days=self.settings.refresh_token_expire_days,
        )

        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "bearer",
        }
```

- [ ] **Step 4: Write auth.py router**

```python
"""Auth router: register, login, refresh."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared_config.settings import Settings
from shared_schemas.auth import LoginRequest, RefreshRequest, RegisterRequest
from shared_schemas.common import DataResponse

from app.deps import get_db, get_settings_dep
from app.services.auth_service import AuthService

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/register")
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    service = AuthService(db, settings)
    result = await service.register(body.tenant_name, body.email, body.password)
    return DataResponse(data=result)


@router.post("/login")
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    service = AuthService(db, settings)
    result = await service.login(body.email, body.password)
    return DataResponse(data=result)


@router.post("/refresh")
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    service = AuthService(db, settings)
    result = await service.refresh(body.refresh_token)
    return DataResponse(data=result)
```

- [ ] **Step 5: Register router in main.py**

Add to `create_app()` in `services/api/app/main.py`:

```python
from .routers import health, auth

# ... in create_app():
app.include_router(auth.router)
```

- [ ] **Step 6: Run auth tests**

```bash
python -m pytest services/api/tests/test_auth.py -v
```

Expected: 5 tests PASS

- [ ] **Step 7: Commit**

```bash
git add services/api/app/services/auth_service.py services/api/app/routers/auth.py
git add services/api/tests/test_auth.py services/api/app/main.py
git commit -m "feat: add auth endpoints — register, login, refresh with tests"
```

---

## Chunk 3: Business API Routers

### Task 11: Projects Router + Service

**Files:**
- Create: `services/api/app/services/project_service.py`
- Create: `services/api/app/routers/projects.py`
- Create: `services/api/tests/test_projects.py`

- [ ] **Step 1: Write test_projects.py**

```python
"""Test project CRUD endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/v1/projects",
        json={"name": "Test KB", "industry_hint": "retail"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["name"] == "Test KB"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_list_projects(client: AsyncClient, auth_headers: dict):
    await client.post("/v1/projects", json={"name": "P1"}, headers=auth_headers)
    await client.post("/v1/projects", json={"name": "P2"}, headers=auth_headers)
    resp = await client.get("/v1/projects", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 2


@pytest.mark.asyncio
async def test_get_project(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post("/v1/projects", json={"name": "Detail"}, headers=auth_headers)
    project_id = create_resp.json()["data"]["id"]
    resp = await client.get(f"/v1/projects/{project_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Detail"


@pytest.mark.asyncio
async def test_get_project_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/v1/projects/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_project(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post("/v1/projects", json={"name": "Old"}, headers=auth_headers)
    project_id = create_resp.json()["data"]["id"]
    resp = await client.patch(
        f"/v1/projects/{project_id}",
        json={"name": "New Name"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_project(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post("/v1/projects", json={"name": "ToDelete"}, headers=auth_headers)
    project_id = create_resp.json()["data"]["id"]
    resp = await client.delete(f"/v1/projects/{project_id}", headers=auth_headers)
    assert resp.status_code == 200

    resp = await client.get(f"/v1/projects/{project_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_no_auth(client: AsyncClient):
    resp = await client.get("/v1/projects")
    assert resp.status_code == 401
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
python -m pytest services/api/tests/test_projects.py -v
```

- [ ] **Step 3: Write project_service.py**

```python
"""Project CRUD business logic."""

from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import ErrorCode, NotFoundException
from shared_models import Project


class ProjectService:
    def __init__(self, db: AsyncSession, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    async def create(self, name: str, industry_hint: str | None = None) -> Project:
        project = Project(tenant_id=self.tenant_id, name=name, industry_hint=industry_hint)
        self.db.add(project)
        await self.db.flush()
        return project

    async def list(self, page: int = 1, page_size: int = 20) -> tuple[list[Project], int]:
        base_query = select(Project).where(
            Project.tenant_id == self.tenant_id, Project.status != "deleted"
        )
        count_result = await self.db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar() or 0

        result = await self.db.execute(
            base_query.order_by(Project.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get(self, project_id: UUID) -> Project:
        result = await self.db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.tenant_id == self.tenant_id,
                Project.status != "deleted",
            )
        )
        project = result.scalar_one_or_none()
        if not project:
            raise NotFoundException(ErrorCode.PROJECT_NOT_FOUND, "项目不存在")
        return project

    async def update(self, project_id: UUID, **kwargs) -> Project:
        project = await self.get(project_id)
        for key, value in kwargs.items():
            if value is not None:
                setattr(project, key, value)
        await self.db.flush()
        return project

    async def delete(self, project_id: UUID) -> None:
        project = await self.get(project_id)
        project.status = "deleted"
        await self.db.flush()
```

- [ ] **Step 4: Write projects.py router**

```python
"""Projects CRUD router."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared_schemas.common import DataResponse, ListResponse, PaginationMeta
from shared_schemas.project import ProjectCreate, ProjectOut, ProjectUpdate

from app.deps import get_current_user, get_db, get_tenant_id
from app.services.project_service import ProjectService

router = APIRouter(prefix="/v1/projects", tags=["projects"])


@router.post("")
async def create_project(
    body: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
):
    service = ProjectService(db, tenant_id)
    project = await service.create(body.name, body.industry_hint)
    return DataResponse(data=ProjectOut.model_validate(project))


@router.get("")
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
):
    service = ProjectService(db, tenant_id)
    projects, total = await service.list(page, page_size)
    return ListResponse(
        data=[ProjectOut.model_validate(p) for p in projects],
        meta=PaginationMeta(page=page, page_size=page_size, total=total),
    )


@router.get("/{project_id}")
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
):
    service = ProjectService(db, tenant_id)
    project = await service.get(project_id)
    return DataResponse(data=ProjectOut.model_validate(project))


@router.patch("/{project_id}")
async def update_project(
    project_id: UUID,
    body: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
):
    service = ProjectService(db, tenant_id)
    project = await service.update(
        project_id,
        name=body.name,
        industry_hint=body.industry_hint,
        status=body.status,
    )
    return DataResponse(data=ProjectOut.model_validate(project))


@router.delete("/{project_id}")
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
):
    service = ProjectService(db, tenant_id)
    await service.delete(project_id)
    return DataResponse(data={"deleted": True})
```

- [ ] **Step 5: Register router in main.py**

Add import and include: `from .routers import health, auth, projects`

```python
app.include_router(projects.router)
```

- [ ] **Step 6: Run tests**

```bash
python -m pytest services/api/tests/test_projects.py -v
```

Expected: 7 tests PASS

- [ ] **Step 7: Commit**

```bash
git add services/api/app/services/project_service.py services/api/app/routers/projects.py
git add services/api/tests/test_projects.py services/api/app/main.py
git commit -m "feat: add project CRUD endpoints with tenant isolation and tests"
```

---

### Task 12: Jobs Router + Service

**Files:**
- Create: `services/api/app/services/job_service.py`
- Create: `services/api/app/routers/jobs.py`
- Create: `services/api/tests/test_jobs.py`

Pattern identical to Task 11. The service creates Job records, associates with project_id. The router exposes POST/GET/retry. Test covers create, list, get, retry, and not-found cases.

- [ ] **Step 1: Write test_jobs.py** — test create job, list by project, get by id, retry failed, 404 not found
- [ ] **Step 2: Run tests — expect FAIL**
- [ ] **Step 3: Write job_service.py** — create (validates project exists), list (filter by project_id+tenant), get, retry (resets status to pending, increments retry_count)
- [ ] **Step 4: Write jobs.py router** — POST /v1/jobs, GET /v1/jobs, GET /v1/jobs/{id}, POST /v1/jobs/{id}/retry
- [ ] **Step 5: Register router in main.py**
- [ ] **Step 6: Run tests — expect PASS**
- [ ] **Step 7: Commit**

```bash
git commit -m "feat: add job management endpoints with tests"
```

---

### Task 13: Assets Router + Service (Upload, List, Get)

**Files:**
- Create: `services/api/app/services/asset_service.py`
- Create: `services/api/app/routers/assets.py`
- Create: `services/api/tests/test_assets.py`

Upload endpoint accepts multipart file, computes SHA-256 hash, stores metadata in DB (MinIO upload stubbed for now). List and get filter by project_id + tenant.

- [ ] **Step 1: Write test_assets.py** — test upload, list by project, get by id, duplicate hash rejection, 404
- [ ] **Step 2: Run tests — expect FAIL**
- [ ] **Step 3: Write asset_service.py** — upload (hash check, create Asset record), list, get
- [ ] **Step 4: Write assets.py router** — POST /v1/assets/upload, GET /v1/assets, GET /v1/assets/{id}
- [ ] **Step 5: Register router in main.py**
- [ ] **Step 6: Run tests — expect PASS**
- [ ] **Step 7: Commit**

```bash
git commit -m "feat: add asset upload and listing endpoints with tests"
```

---

### Task 14: Architectures Router + Service

**Files:**
- Create: `services/api/app/services/architecture_service.py`
- Create: `services/api/app/routers/architectures.py`
- Create: `services/api/tests/test_architectures.py`

Covers: list architectures by project, get detail, publish, create node, update node.

- [ ] **Step 1: Write test_architectures.py** — test list by project, get detail, publish, create node, update node, 404
- [ ] **Step 2: Run tests — expect FAIL**
- [ ] **Step 3: Write architecture_service.py** — list, get, publish (status transition), create_node, update_node
- [ ] **Step 4: Write architectures.py router**
- [ ] **Step 5: Register router in main.py**
- [ ] **Step 6: Run tests — expect PASS**
- [ ] **Step 7: Commit**

```bash
git commit -m "feat: add architecture management endpoints with tests"
```

---

### Task 15: Knowledge Docs Router + Service

**Files:**
- Create: `services/api/app/services/doc_service.py`
- Create: `services/api/app/routers/docs.py`
- Create: `services/api/tests/test_docs.py`

Covers: list docs by project, get detail (with versions), submit review, publish.

- [ ] **Step 1-7: Same TDD pattern** — test → fail → implement → pass → commit

```bash
git commit -m "feat: add knowledge document endpoints with tests"
```

---

### Task 16: Conflicts Router + Service

**Files:**
- Create: `services/api/app/services/conflict_service.py`
- Create: `services/api/app/routers/conflicts.py`
- Create: `services/api/tests/test_conflicts.py`

Covers: list conflicts by project, get detail, resolve.

- [ ] **Step 1-7: Same TDD pattern**

```bash
git commit -m "feat: add conflict resolution endpoints with tests"
```

---

### Task 17: Model Providers + Routes Router + Service

**Files:**
- Create: `services/api/app/services/model_provider_service.py`
- Create: `services/api/app/routers/model_providers.py`
- Create: `services/api/tests/test_model_providers.py`

Covers: create provider (encrypt API key), list (mask key), test connectivity (stub), CRUD model routes.

- [ ] **Step 1-7: Same TDD pattern**

```bash
git commit -m "feat: add model provider and route management endpoints with tests"
```

---

### Task 18: Users Router + Service

**Files:**
- Create: `services/api/app/services/user_service.py`
- Create: `services/api/app/routers/users.py`
- Create: `services/api/tests/test_users.py`

Covers: list users in tenant, invite (create with temporary password), update role/status, disable.

- [ ] **Step 1-7: Same TDD pattern**

```bash
git commit -m "feat: add user management endpoints with tests"
```

---

## Chunk 4: Final Integration + Docker

### Task 19: Register All Routers in main.py

**Files:**
- Modify: `services/api/app/main.py`

- [ ] **Step 1: Update main.py with all router imports**

```python
from .routers import (
    auth, projects, assets, jobs,
    architectures, docs, conflicts,
    model_providers, users, health,
)

# In create_app():
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(assets.router)
app.include_router(jobs.router)
app.include_router(architectures.router)
app.include_router(docs.router)
app.include_router(conflicts.router)
app.include_router(model_providers.router)
app.include_router(users.router)
app.include_router(health.router)
```

- [ ] **Step 2: Run all tests**

```bash
python -m pytest services/api/tests/ -v
```

Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git commit -m "feat: register all routers in main.py"
```

---

### Task 20: Dockerfile and docker-compose Integration

**Files:**
- Create: `infra/docker/api.Dockerfile`
- Modify: `docker-compose.yml` — add api service

- [ ] **Step 1: Create api.Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install shared packages
COPY packages/ /packages/
RUN pip install -e /packages/shared-config \
    && pip install -e /packages/shared-errors \
    && pip install -e /packages/shared-models \
    && pip install -e /packages/shared-schemas

# Install API service
COPY services/api/ /app/
RUN pip install -e /app/

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

- [ ] **Step 2: Add api service to docker-compose.yml**

Add to services section:

```yaml
  api:
    build:
      context: .
      dockerfile: infra/docker/api.Dockerfile
    ports:
      - "${APP_PORT:-8080}:8080"
    env_file:
      - .env
    depends_on:
      - postgres
      - redis
      - minio
    restart: unless-stopped
```

- [ ] **Step 3: Build and test**

```bash
docker-compose build api
docker-compose up -d
curl http://localhost:8080/healthz
```

Expected: `{"status":"ok"}`

- [ ] **Step 4: Commit**

```bash
git add infra/docker/ docker-compose.yml
git commit -m "feat: add API Dockerfile and docker-compose integration"
```

---

### Task 21: Final Verification

- [ ] **Step 1: Run full test suite**

```bash
python -m pytest services/api/tests/ -v --tb=short
```

- [ ] **Step 2: Start all services**

```bash
docker-compose up -d
```

- [ ] **Step 3: Verify API docs**

```bash
curl http://localhost:8080/docs
```

- [ ] **Step 4: Run Alembic migration in container**

```bash
docker-compose exec api alembic -c /infra/sql/alembic.ini upgrade head
```

- [ ] **Step 5: Test end-to-end flow**

```bash
# Register
curl -X POST http://localhost:8080/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"tenant_name":"Demo","email":"demo@test.com","password":"SecurePass123!"}'

# Login
curl -X POST http://localhost:8080/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@test.com","password":"SecurePass123!"}'

# Create project (use token from login response)
curl -X POST http://localhost:8080/v1/projects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"name":"My First KB","industry_hint":"retail"}'
```

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "chore: final verification and cleanup"
```
