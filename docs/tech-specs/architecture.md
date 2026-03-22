# KB Platform -- Architecture & Module Boundaries

> **Version**: v0.39.0 | **Last Updated**: 2026-03-20 | **Maintainer**: KB Platform Team
>
> This document is the single source of truth for KB Platform's system architecture,
> module boundaries, and dependency rules. All developers and agents must read this
> before modifying any service or package.

---

## 0. Document Positioning & Scope

**Purpose**: Define the system architecture, service boundaries, dependency directions,
data flow, and infrastructure layout for KB Platform.

**Audience**: Developers, code review agents, Claude Code agents, DevOps.

**Scope**:
- System-level architecture and layering
- Service catalog and ownership boundaries
- Inter-service communication rules
- Data model overview and multi-tenancy
- Infrastructure and deployment topology
- Security architecture
- Configuration management

**Out of scope**: API field-level documentation (see OpenAPI specs), UI component library
details, individual algorithm implementations.

**Related documents**:
- `docs/tech-specs/dev-governance.md` -- Development governance workflow
- `docs/tech-specs/coding-standards.md` -- Coding standards and conventions
- `docs/tech-specs/testing-strategy.md` -- Testing strategy and requirements
- `docs/prd/01-产品PRD.md` -- Product requirements

---

## 1. System Overview

KB Platform (知识库平台) is a microservices monorepo that transforms multimodal raw
materials (PDF, text, audio, images) into a traceable, maintainable, AI-consumable
structured knowledge system. The platform ingests files, parses content via specialized
workers, runs a multi-stage knowledge pipeline with LLM assistance, and presents
structured knowledge through a web interface.

**Scale**: ~21,315 lines of code, 210 source files, 4 backend services, 4 shared packages,
1 frontend SPA.

```
Architecture Overview (ASCII)

 +------------------+
 |   apps/web/      |  Next.js 15 (React 19, TypeScript)
 |   Frontend SPA   |  Tailwind CSS + Zustand
 +--------+---------+
          | REST (HTTP/JSON) + WebSocket
          v
 +--------+---------+
 |   services/api/  |  FastAPI (Python 3.12)
 |   API Gateway     |  JWT Auth, RBAC, Rate Limiting
 +--+-----+------+--+
    |     |      |
    |     |      +---> Redis (cache, broker)
    |     |
    v     v                  Celery Task Queue
 +--+-----+------+------------------------------+
 |               |                               |
 | ingestion-    | pipeline-     ai-             |
 | worker        | worker        orchestrator    |
 | (parse files) | (7 stages)   (LLM calls)     |
 +-------+-------+--------+----------+----------+
         |                 |          |
         v                 v          v
 +-------+--------+ +-----+----+ +---+--------+
 | MinIO (S3)     | | PostgreSQL| | LLM APIs   |
 | File Storage   | | + pgvector| | (external) |
 +----------------+ +----------+ +------------+
```

---

## 2. Layered Architecture

The system follows a four-layer architecture with strict dependency direction
(upper layers depend on lower layers, never the reverse):

| Layer | Technology | Responsibility |
|-------|-----------|----------------|
| **L1 Presentation** | Next.js 15 (React 19, TypeScript) | UI rendering, routing, user interaction, state management |
| **L2 API Gateway** | FastAPI (Python 3.12) | Authentication, authorization, request validation, REST endpoints, WebSocket |
| **L3 Business Services** | Celery Workers (Python 3.12) | File parsing, knowledge pipeline, LLM orchestration |
| **L4 Data Layer** | PostgreSQL 16 + pgvector, Redis, MinIO | Persistent storage, caching, file storage, vector search |

**Dependency direction**: L1 -> L2 -> L3 -> L4. No reverse dependencies allowed.

- L1 communicates with L2 exclusively via REST API (`lib/api.ts`)
- L2 dispatches work to L3 via Celery task queue (Redis as broker)
- L3 reads/writes L4 directly via shared models and storage clients
- L2 also reads/writes L4 directly for synchronous operations

---

## 3. Service Catalog

### Backend Services

| Service | Path | Runtime | Role | Key Modules |
|---------|------|---------|------|-------------|
| **api** | `services/api/` | FastAPI | REST API gateway, business logic | 15 routers, 13 services, 3 middleware, 4 utils |
| **ingestion-worker** | `services/ingestion-worker/` | Celery | File parsing (PDF, text, OCR, ASR) | 4 parsers |
| **ai-orchestrator** | `services/ai-orchestrator/` | Celery | LLM interaction orchestration | llm_client, prompts, tasks |
| **pipeline-worker** | `services/pipeline-worker/` | Celery | Multi-stage knowledge pipeline | 7 pipeline stages |

### Shared Packages

| Package | Path | Role | Key Modules |
|---------|------|------|-------------|
| **shared-models** | `packages/shared-models/` | SQLAlchemy ORM models | user, tenant, audit, model_config, asset, embedding, job, database, architecture, knowledge, project, base |
| **shared-schemas** | `packages/shared-schemas/` | Pydantic request/response schemas | auth, user, audit, model_config, asset, job, common, architecture, search, knowledge, project |
| **shared-config** | `packages/shared-config/` | Centralized configuration | Pydantic BaseSettings, DLQ config |
| **shared-errors** | `packages/shared-errors/` | Exception hierarchy and error codes | Unified error codes, exception classes |

### Frontend

| App | Path | Runtime | Role |
|-----|------|---------|------|
| **web** | `apps/web/` | Next.js 15 (App Router) | Single-page application |

---

## 4. Module Boundaries & Dependencies

### Service Ownership

Each service owns its internal modules exclusively. No service imports code from
another service.

| Service | Owns | Does NOT Touch |
|---------|------|---------------|
| **api** | Routers, services, middleware, utils | Worker task internals, LLM prompts |
| **ingestion-worker** | Parsers (pdf, text, ocr, asr) | API routers, pipeline stages, LLM client |
| **pipeline-worker** | Pipeline stages (classify, embed, doc_generate, architecture_draft, conflict_detect, quality_check, review_notify) | API routers, parsers, LLM client internals |
| **ai-orchestrator** | LLM client, prompt templates, AI tasks | API routers, parsers, pipeline stage logic |
| **web** | Pages, components, hooks, stores, API client | All backend internals |

### Dependency Direction Rules

```
 services/api  ───────┐
 services/ingestion  ──┤
 services/pipeline  ───┼──> packages/shared-models
 services/ai-orch  ────┤    packages/shared-schemas
                       │    packages/shared-config
                       │    packages/shared-errors
                       └──> (NO cross-service imports)

 apps/web ──> services/api (REST only, via lib/api.ts)
```

**Strict rules**:
1. Services import from `packages/*` only, never from other `services/*`
2. `packages/*` do not import from `services/*` or `apps/*`
3. Frontend communicates with backend exclusively via REST API
4. Workers communicate with API service only through shared database and Redis (no direct HTTP calls between workers and API)

---

## 5. API Interface Definitions

### Endpoint Groups

| Group | Prefix | Auth Required | Description |
|-------|--------|--------------|-------------|
| health | `/health` | No | Liveness/readiness probes |
| auth | `/auth` | Partial | Login, register, token refresh |
| users | `/users` | Yes | User CRUD, profile |
| projects | `/projects` | Yes | Workspace management |
| assets | `/assets` | Yes | File upload, metadata |
| ingestion | `/ingestion` | Yes | Trigger file parsing |
| jobs | `/jobs` | Yes | Pipeline job status |
| docs | `/docs` | Yes | Generated documents |
| architectures | `/architectures` | Yes | Knowledge graph nodes |
| conflicts | `/conflicts` | Yes | Conflict detection results |
| search | `/search` | Yes | Full-text and vector search |
| export | `/export` | Yes | Data export |
| model_providers | `/model_providers` | Yes | LLM provider configuration |
| audit | `/audit` | Yes | Audit trail |
| ws | `/ws` | Yes | WebSocket for real-time updates |

### Authentication Strategy

- **Method**: JWT (JSON Web Tokens)
- **Token types**: Access token (short-lived) + Refresh token (long-lived)
- **Flow**: Login -> receive token pair -> attach access token to `Authorization: Bearer` header -> refresh when expired
- **Rate limiting**: General rate limits on all endpoints + stricter limits on auth endpoints

---

## 6. Data Model

### Key Entities and Relationships

```
tenant (multi-tenancy root)
  |
  +-- user (belongs to tenant)
  |     +-- audit (user actions log)
  |
  +-- project (workspace, belongs to tenant)
        |
        +-- asset (uploaded file, belongs to project)
        |     +-- embedding (vector via pgvector)
        |
        +-- job (processing pipeline run)
        |
        +-- knowledge (extracted knowledge units)
        |
        +-- architecture (structured graph nodes)
        |
        +-- model_config (LLM provider settings)
```

### Multi-Tenancy Model

- **Strategy**: Row-level isolation via `tenant_id` foreign key on all tenant-scoped tables
- **Enforcement**: API service filters all queries by the authenticated user's `tenant_id`
- **Shared tables**: None. All data is tenant-scoped.

### Vector Storage

- PostgreSQL `pgvector` extension stores embeddings alongside relational data
- Embedding table links to assets and knowledge units
- Supports similarity search via vector distance operations

---

## 7. Data Flow

The primary data flow is file ingestion through the knowledge pipeline:

```
Step 1: User uploads file via frontend
        [web] -> POST /ingestion -> [api]

Step 2: API stores file and creates records
        [api] -> MinIO (store file)
        [api] -> PostgreSQL (create Asset + Job records)

Step 3: API dispatches parsing task
        [api] -> Redis (Celery task) -> [ingestion-worker]

Step 4: Ingestion worker parses file
        [ingestion-worker] -> selects parser (PDF/text/OCR/ASR)
        [ingestion-worker] -> extracts raw content
        [ingestion-worker] -> PostgreSQL (store parsed content)

Step 5: Pipeline worker runs stages sequentially
        [pipeline-worker] stages:
          5a. classify     -- categorize content
          5b. embed        -- generate vector embeddings
          5c. doc_generate -- create structured documents
          5d. architecture_draft -- draft knowledge graph
          5e. conflict_detect   -- detect contradictions
          5f. quality_check     -- validate quality
          5g. review_notify     -- notify for human review

Step 6: AI orchestrator handles LLM calls
        [ai-orchestrator] <- called by pipeline stages via Celery
        [ai-orchestrator] -> external LLM APIs

Step 7: Results persisted
        [pipeline-worker] -> PostgreSQL (knowledge, architecture,
                             embedding tables)

Step 8: Frontend displays results
        [web] <- GET /architectures, /docs, /search <- [api]
        [web] renders tree views, graph views, search results
```

---

## 8. Infrastructure & Deployment

### Container Architecture

| Container | Dockerfile | Base |
|-----------|-----------|------|
| api | `infra/docker/Dockerfile.api` | Python 3.12 |
| ingestion-worker | `infra/docker/Dockerfile.ingestion-worker` | Python 3.12 |
| ai-orchestrator | `infra/docker/Dockerfile.ai-orchestrator` | Python 3.12 |
| pipeline-worker | `infra/docker/Dockerfile.pipeline-worker` | Python 3.12 |

All Dockerfiles run as non-root users (added in v0.39.0, T-39-02).

### External Services

| Service | Role | Configuration |
|---------|------|--------------|
| **PostgreSQL 16** | Primary datastore, with pgvector extension | `DATABASE_URL` env var |
| **Redis** | Celery broker + result backend, caching | `REDIS_URL` env var |
| **MinIO** | S3-compatible object storage for uploaded files | `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` |

### Database Migrations

- Tool: Alembic
- Migration files: `infra/sql/`
- 4 migrations applied to date
- Run via entrypoint scripts before service startup

### Celery Configuration

- Broker: Redis
- Result backend: Redis
- Three worker processes: ingestion-worker, pipeline-worker, ai-orchestrator
- Each worker has its own Celery app configuration in `worker/celery_app.py`

---

## 9. Security Architecture

### Authentication & Authorization

| Mechanism | Implementation |
|-----------|---------------|
| **JWT Auth** | Access tokens (short-lived) + refresh tokens (long-lived) |
| **RBAC** | Role-based access control enforced at API layer |
| **Tenant Isolation** | All queries scoped by `tenant_id` |

### Data Protection

| Mechanism | Implementation |
|-----------|---------------|
| **Encryption at rest** | AES-256 for sensitive configuration (model provider keys) |
| **Secret validation** | Production environment validates required secrets on startup |
| **CORS** | Whitelist-based CORS policy |

### Rate Limiting

| Scope | Strategy |
|-------|---------|
| **General** | Per-IP rate limiting on all endpoints |
| **Auth endpoints** | Stricter rate limits on login/register |
| Implementation: middleware in `services/api/middleware/rate_limit.py` |

### Request Tracing

- Request ID middleware assigns unique ID to every request
- ID propagated through logs for end-to-end tracing
- Implementation: `services/api/middleware/request_id.py`

---

## 10. Configuration Management

### Strategy

All configuration uses Pydantic `BaseSettings` with environment variable loading:

```
packages/shared-config/shared_config/settings.py
  -> reads from .env file or environment variables
  -> validates types and constraints at startup
  -> shared across all backend services
```

### Configuration Categories

| Category | Key Variables | Description |
|----------|-------------|-------------|
| **Database** | `DATABASE_URL` | PostgreSQL connection string |
| **Redis** | `REDIS_URL` | Redis connection for cache + Celery |
| **MinIO** | `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` | Object storage |
| **JWT** | `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE` | Authentication |
| **Encryption** | `ENCRYPTION_KEY` | AES-256 key for sensitive data |
| **Rate Limits** | `RATE_LIMIT_*` | Request rate limiting thresholds |
| **Upload** | `MAX_UPLOAD_SIZE` | File upload size limits |
| **CORS** | `CORS_ORIGINS` | Allowed frontend origins |
| **Logging** | `LOG_LEVEL` | Application log level |

---

## 11. Cross-Cutting Concerns

### Logging

- Structured logging across all services
- Log level configurable via `LOG_LEVEL` environment variable
- Request ID included in all log entries for traceability

### Metrics

- Metrics middleware in `services/api/middleware/metrics.py`
- Tracks request counts, latency, and error rates

### Request Tracing

- Unique request ID assigned at API gateway
- Propagated through Celery task headers to workers
- Enables end-to-end request tracking across services

### Error Handling

- Centralized error hierarchy in `packages/shared-errors/`
- Unified error codes across all services
- API returns structured error responses with error code, message, and details
- DLQ (Dead Letter Queue) configuration in `packages/shared-config/` for failed Celery tasks

---

## 12. Development Conventions

### Directory Structure

```
knowledge_SQL/                    # Repository root
+-- services/
|   +-- api/                      # FastAPI API service
|   |   +-- routers/              # Route handlers
|   |   +-- services/             # Business logic
|   |   +-- middleware/           # Request middleware
|   |   +-- utils/                # Utility functions
|   +-- ingestion-worker/         # File parsing worker
|   |   +-- worker/parsers/       # Parser implementations
|   +-- pipeline-worker/          # Knowledge pipeline worker
|   |   +-- worker/stages/        # Pipeline stage implementations
|   +-- ai-orchestrator/          # LLM orchestration worker
|       +-- orchestrator/         # LLM client, prompts, tasks
+-- packages/
|   +-- shared-models/            # SQLAlchemy models
|   +-- shared-schemas/           # Pydantic schemas
|   +-- shared-config/            # Centralized configuration
|   +-- shared-errors/            # Error codes and exceptions
+-- apps/
|   +-- web/                      # Next.js frontend
|       +-- src/
|           +-- app/(dashboard)/  # Route groups
|           +-- components/       # React components
|           +-- hooks/            # Custom hooks
|           +-- stores/           # Zustand stores
|           +-- lib/              # API client, utilities
+-- infra/
|   +-- docker/                   # Dockerfiles + entrypoint scripts
|   +-- sql/                      # Alembic migrations
+-- docs/
    +-- prd/                      # Product requirements
    +-- dev-plans/                # Development plans
    +-- tech-specs/               # Technical specifications (this file)
    +-- versions/                 # Audit records and test reports
```

### New Module Isolation Path

When adding new features, follow these isolation paths:

| Change Type | Path |
|------------|------|
| New backend service | `services/{service-name}/` |
| New shared package | `packages/{package-name}/` |
| New frontend page | `apps/web/src/app/(dashboard)/{feature}/` |
| New frontend component | `apps/web/src/components/{feature}/` |
| New API router | `services/api/routers/{feature}.py` |
| New API service | `services/api/services/{feature}_service.py` |
| New pipeline stage | `services/pipeline-worker/worker/stages/{stage}.py` |
| New parser | `services/ingestion-worker/worker/parsers/{parser}.py` |

---

## 13. Known Limitations & Technical Debt

| Item | Description | Impact | Priority |
|------|------------|--------|----------|
| Single-region deployment | No multi-region or HA configuration | Availability risk for production | Medium |
| No API versioning | Endpoints are unversioned (`/projects` not `/v1/projects`) | Breaking changes affect all clients | Low (pre-production) |
| Synchronous pipeline dispatch | API blocks briefly while dispatching Celery tasks | Minor latency on upload endpoint | Low |
| No circuit breaker | LLM API failures propagate without backoff pattern | Pipeline reliability under LLM outage | Medium |
| No OpenAPI spec generation tests | API contract not validated in CI | Schema drift risk | Low |
| Monorepo without workspace tooling | No nx/turborepo for frontend; no Python monorepo tool | Build/test coordination is manual | Low |

---

## 14. Document Relationships

```
                    +---------------------------+
                    |  CLAUDE.md                |
                    |  (project entry point)    |
                    +--+------------------------+
                       |
          +------------+------------+
          |            |            |
          v            v            v
+---------+--+ +------+------+ +---+----------------+
| architecture | | dev-        | | coding-           |
| .md          | | governance  | | standards.md      |
| (this file)  | | .md         | | (index -> parts)  |
+--------------+ +------+------+ +---+----------------+
                        |            |
                        v            v
                 +------+------+ +---+----------------+
                 | part0..partN | | P0 (must-read)     |
                 | (governance  | | P1..PN (conditional)|
                 |  phases)     | +--------------------+
                 +-------------+
                                  +--------------------+
                                  | testing-strategy   |
                                  | .md                |
                                  +--------------------+
```

This document (`architecture.md`) is referenced by:
- `CLAUDE.md` -- as one of four required tech-spec reads
- `dev-governance.md` -- Phase 1 requires reading architecture before coding
- `coding-standards.md` -- references layering rules and module boundaries

---

<!-- ARCHITECTURE SELF-CHECK (for agents and reviewers)

Before modifying this document, verify:

1. [ ] All services listed in Service Catalog match actual directories in services/
2. [ ] All shared packages listed match actual directories in packages/
3. [ ] Dependency direction rules are consistent with actual imports
4. [ ] Data flow steps match the actual pipeline stages in pipeline-worker
5. [ ] Security mechanisms listed are implemented in the codebase
6. [ ] Configuration variables listed exist in shared-config settings
7. [ ] Directory structure matches the actual repository layout
8. [ ] Known limitations are still accurate and not yet resolved
9. [ ] Version number matches VERSION file
10. [ ] Document relationships diagram is accurate

Last verified: v0.39.0 (2026-03-20)
-->
