"""Tests for OpenAPI schema completeness (T-35-08).

These tests use a lightweight client that does NOT require a database
connection, since /openapi.json is generated purely from route definitions.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.deps import get_db
from app.main import create_app
from app.routers.assets import get_storage


# Public paths that should NOT have security requirements
PUBLIC_PATHS = {"/healthz", "/readyz", "/metrics", "/api/versions", "/api/health/ready"}


@pytest_asyncio.fixture(scope="module", loop_scope="session")
async def openapi_client():
    """Lightweight test client — no DB needed, only for /openapi.json access."""
    app = create_app()

    async def mock_db():
        yield None  # pragma: no cover

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[get_storage] = lambda: None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_openapi_schema_accessible(openapi_client: AsyncClient):
    """GET /openapi.json should return a valid OpenAPI 3.x schema."""
    resp = await openapi_client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "openapi" in schema
    assert schema["openapi"].startswith("3.")
    assert "paths" in schema
    assert "components" in schema


@pytest.mark.asyncio
async def test_all_endpoints_have_summary_and_description(openapi_client: AsyncClient):
    """Every endpoint in OpenAPI should have both summary and description."""
    resp = await openapi_client.get("/openapi.json")
    schema = resp.json()
    missing = []
    for path, methods in schema["paths"].items():
        for method, detail in methods.items():
            if method in ("parameters",):
                continue
            if not isinstance(detail, dict):
                continue
            if not detail.get("summary"):
                missing.append(f"{method.upper()} {path} missing summary")
            if not detail.get("description"):
                missing.append(f"{method.upper()} {path} missing description")
    assert missing == [], f"Endpoints missing summary/description:\n" + "\n".join(missing)


@pytest.mark.asyncio
async def test_all_endpoints_have_tags(openapi_client: AsyncClient):
    """Every endpoint should have at least one tag for grouping."""
    resp = await openapi_client.get("/openapi.json")
    schema = resp.json()
    missing = []
    for path, methods in schema["paths"].items():
        for method, detail in methods.items():
            if method in ("parameters",):
                continue
            if not isinstance(detail, dict):
                continue
            tags = detail.get("tags", [])
            if not tags:
                missing.append(f"{method.upper()} {path}")
    assert missing == [], f"Endpoints missing tags:\n" + "\n".join(missing)


@pytest.mark.asyncio
async def test_authenticated_endpoints_have_security(openapi_client: AsyncClient):
    """Non-public endpoints should have BearerAuth security requirement."""
    resp = await openapi_client.get("/openapi.json")
    schema = resp.json()
    missing = []
    for path, methods in schema["paths"].items():
        if path in PUBLIC_PATHS:
            continue
        for method, detail in methods.items():
            if method in ("parameters",):
                continue
            if not isinstance(detail, dict):
                continue
            security = detail.get("security")
            if security is None:
                missing.append(f"{method.upper()} {path}")
    assert missing == [], f"Authenticated endpoints missing security:\n" + "\n".join(missing)


@pytest.mark.asyncio
async def test_public_endpoints_have_empty_security(openapi_client: AsyncClient):
    """Public endpoints should explicitly have empty security (security: [])."""
    resp = await openapi_client.get("/openapi.json")
    schema = resp.json()
    problems = []
    for path in PUBLIC_PATHS:
        methods = schema["paths"].get(path, {})
        for method, detail in methods.items():
            if method in ("parameters",):
                continue
            if not isinstance(detail, dict):
                continue
            security = detail.get("security")
            if security != []:
                problems.append(f"{method.upper()} {path} security={security}")
    assert problems == [], f"Public endpoints should have security: []:\n" + "\n".join(problems)


@pytest.mark.asyncio
async def test_bearer_auth_security_scheme_defined(openapi_client: AsyncClient):
    """OpenAPI schema should define BearerAuth security scheme."""
    resp = await openapi_client.get("/openapi.json")
    schema = resp.json()
    schemes = schema.get("components", {}).get("securitySchemes", {})
    assert "BearerAuth" in schemes, "BearerAuth security scheme not defined"
    bearer = schemes["BearerAuth"]
    assert bearer["type"] == "http"
    assert bearer["scheme"] == "bearer"
    assert bearer["bearerFormat"] == "JWT"


@pytest.mark.asyncio
async def test_error_response_schema_defined(openapi_client: AsyncClient):
    """OpenAPI schema should include ErrorDetail in components/schemas."""
    resp = await openapi_client.get("/openapi.json")
    schema = resp.json()
    schemas = schema.get("components", {}).get("schemas", {})
    assert "ErrorDetail" in schemas, "ErrorDetail schema not in components/schemas"
    error_schema = schemas["ErrorDetail"]
    props = error_schema.get("properties", {})
    assert "error_code" in props
    assert "message" in props
    assert "detail" in props
    assert "meta" in props


@pytest.mark.asyncio
async def test_non_public_endpoints_have_error_responses(openapi_client: AsyncClient):
    """Authenticated endpoints should define at least one 4xx or 5xx error response."""
    resp = await openapi_client.get("/openapi.json")
    schema = resp.json()
    missing = []
    for path, methods in schema["paths"].items():
        if path in PUBLIC_PATHS:
            continue
        for method, detail in methods.items():
            if method in ("parameters",):
                continue
            if not isinstance(detail, dict):
                continue
            responses = detail.get("responses", {})
            error_codes = [k for k in responses if k.startswith(("4", "5"))]
            if not error_codes:
                missing.append(f"{method.upper()} {path}")
    assert missing == [], f"Endpoints missing error responses:\n" + "\n".join(missing)
