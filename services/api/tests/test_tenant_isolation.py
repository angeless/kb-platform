"""Cross-tenant isolation tests.

T-34-07: Verifies tenant A cannot see/modify/delete tenant B's data.
These tests use the FastAPI TestClient with real database sessions.
"""

import uuid

import pytest
from httpx import AsyncClient


# --- Helpers ---


async def _register_tenant(client: AsyncClient, name: str) -> dict:
    """Register a new tenant and return {access_token, kb_id, user_id}."""
    email = f"{name}-{uuid.uuid4().hex[:6]}@test.com"
    resp = await client.post(
        "/v1/auth/register",
        json={"tenant_name": name, "email": email, "password": "Secure@test123"},
    )
    assert resp.status_code == 201
    data = resp.json()["data"]

    # Login to get access token
    login = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": "Secure@test123"},
    )
    assert login.status_code == 200
    token = login.json()["data"]["access_token"]

    return {"access_token": token, "headers": {"Authorization": f"Bearer {token}"}}


async def _create_project(client: AsyncClient, headers: dict) -> str:
    """Create a project and return its ID."""
    resp = await client.post(
        "/v1/projects",
        json={"name": f"Project-{uuid.uuid4().hex[:6]}"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


# --- Tests ---


@pytest.mark.asyncio
async def test_tenant_cannot_access_other_project(
    client: AsyncClient,
):
    """Tenant A's project should be invisible to Tenant B."""
    tenant_a = await _register_tenant(client, "TenantA")
    tenant_b = await _register_tenant(client, "TenantB")

    project_a = await _create_project(client, tenant_a["headers"])

    # Tenant B tries to access Tenant A's project
    resp = await client.get(f"/v1/projects/{project_a}", headers=tenant_b["headers"])
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_tenant_cannot_list_other_assets(
    client: AsyncClient,
):
    """Tenant B should not see Tenant A's assets via project scoping."""
    tenant_a = await _register_tenant(client, "TenantA")
    tenant_b = await _register_tenant(client, "TenantB")

    project_a = await _create_project(client, tenant_a["headers"])

    # Upload a file as Tenant A
    await client.post(
        "/v1/assets/upload",
        data={"project_id": project_a, "asset_type": "text"},
        files={"file": ("test.txt", b"Hello from Tenant A", "text/plain")},
        headers=tenant_a["headers"],
    )

    # Tenant B tries to list assets for Tenant A's project
    resp = await client.get(
        f"/v1/assets?project_id={project_a}",
        headers=tenant_b["headers"],
    )
    # Should fail because project verification blocks cross-tenant access
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_tenant_cannot_access_other_docs(
    client: AsyncClient,
):
    """Tenant B should not see Tenant A's docs."""
    tenant_a = await _register_tenant(client, "TenantA")
    tenant_b = await _register_tenant(client, "TenantB")

    project_a = await _create_project(client, tenant_a["headers"])

    # Tenant B tries to list docs for Tenant A's project
    resp = await client.get(
        f"/v1/docs?project_id={project_a}",
        headers=tenant_b["headers"],
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_tenant_cannot_access_other_architectures(
    client: AsyncClient,
):
    """Tenant B should not see Tenant A's architectures."""
    tenant_a = await _register_tenant(client, "TenantA")
    tenant_b = await _register_tenant(client, "TenantB")

    project_a = await _create_project(client, tenant_a["headers"])

    resp = await client.get(
        f"/v1/architectures?project_id={project_a}",
        headers=tenant_b["headers"],
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_tenant_cannot_access_other_jobs(
    client: AsyncClient,
):
    """Tenant B should not see Tenant A's jobs."""
    tenant_a = await _register_tenant(client, "TenantA")
    tenant_b = await _register_tenant(client, "TenantB")

    project_a = await _create_project(client, tenant_a["headers"])

    resp = await client.get(
        f"/v1/jobs?project_id={project_a}",
        headers=tenant_b["headers"],
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_tenant_cannot_access_other_conflicts(
    client: AsyncClient,
):
    """Tenant B should not see Tenant A's conflicts."""
    tenant_a = await _register_tenant(client, "TenantA")
    tenant_b = await _register_tenant(client, "TenantB")

    project_a = await _create_project(client, tenant_a["headers"])

    resp = await client.get(
        f"/v1/conflicts?project_id={project_a}",
        headers=tenant_b["headers"],
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_tenant_cannot_search_other_project(
    client: AsyncClient,
):
    """Tenant B should not be able to search in Tenant A's project."""
    tenant_a = await _register_tenant(client, "TenantA")
    tenant_b = await _register_tenant(client, "TenantB")

    project_a = await _create_project(client, tenant_a["headers"])

    resp = await client.get(
        f"/v1/search?project_id={project_a}&q=test",
        headers=tenant_b["headers"],
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_tenant_cannot_export_other_project(
    client: AsyncClient,
):
    """Tenant B should not be able to export Tenant A's project."""
    tenant_a = await _register_tenant(client, "TenantA")
    tenant_b = await _register_tenant(client, "TenantB")

    project_a = await _create_project(client, tenant_a["headers"])

    resp = await client.post(
        f"/v1/exports?project_id={project_a}",
        json={"format": "markdown"},
        headers=tenant_b["headers"],
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_tenant_isolation_bidirectional(
    client: AsyncClient,
):
    """Both tenants should only see their own projects."""
    tenant_a = await _register_tenant(client, "TenantA")
    tenant_b = await _register_tenant(client, "TenantB")

    project_a = await _create_project(client, tenant_a["headers"])
    project_b = await _create_project(client, tenant_b["headers"])

    # A lists projects — should only see A's
    resp_a = await client.get("/v1/projects", headers=tenant_a["headers"])
    assert resp_a.status_code == 200
    ids_a = {p["id"] for p in resp_a.json()["data"]}
    assert project_a in ids_a
    assert project_b not in ids_a

    # B lists projects — should only see B's
    resp_b = await client.get("/v1/projects", headers=tenant_b["headers"])
    assert resp_b.status_code == 200
    ids_b = {p["id"] for p in resp_b.json()["data"]}
    assert project_b in ids_b
    assert project_a not in ids_b
