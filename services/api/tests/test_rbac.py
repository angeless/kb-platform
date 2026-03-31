"""Tests for role-based access control (RBAC)."""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from shared_config.settings import get_settings
from shared_models import KnowledgeDoc, Tenant, User
from app.utils.security import create_access_token, hash_password

settings = get_settings()


@pytest_asyncio.fixture(loop_scope="session")
async def viewer_headers(db_session: AsyncSession, auth_headers: dict) -> dict[str, str]:
    """Create a viewer user and return auth headers."""
    # Reuse tenant created by auth_headers fixture
    from sqlalchemy import select

    result = await db_session.execute(select(Tenant).limit(1))
    tenant = result.scalar_one()

    user = User(
        id=uuid.uuid4(),
        kb_id=tenant.id,
        email=f"viewer-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("test-password"),
        role="viewer",
        status="active",
    )
    db_session.add(user)
    await db_session.flush()

    token = create_access_token(
        data={"sub": str(user.id), "kb_id": str(tenant.id), "role": user.role},
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(loop_scope="session")
async def editor_headers(db_session: AsyncSession, auth_headers: dict) -> dict[str, str]:
    """Create an editor user and return auth headers."""
    from sqlalchemy import select

    result = await db_session.execute(select(Tenant).limit(1))
    tenant = result.scalar_one()

    user = User(
        id=uuid.uuid4(),
        kb_id=tenant.id,
        email=f"editor-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("test-password"),
        role="editor",
        status="active",
    )
    db_session.add(user)
    await db_session.flush()

    token = create_access_token(
        data={"sub": str(user.id), "kb_id": str(tenant.id), "role": user.role},
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(loop_scope="session")
async def rbac_project(client: AsyncClient, auth_headers: dict):
    """Create a project for RBAC tests (using admin user)."""
    resp = await client.post(
        "/v1/projects",
        json={"name": "RBAC Test Project"},
        headers=auth_headers,
    )
    return uuid.UUID(resp.json()["data"]["id"])


# --- Viewer should be forbidden from write operations ---


@pytest.mark.asyncio
async def test_viewer_cannot_upload(
    client: AsyncClient, viewer_headers: dict, rbac_project: uuid.UUID
):
    """Viewer should get 403 when trying to upload."""
    import io

    resp = await client.post(
        "/v1/assets/upload",
        data={"project_id": str(rbac_project), "asset_type": "text"},
        files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
        headers=viewer_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_review_doc(
    client: AsyncClient,
    viewer_headers: dict,
    db_session: AsyncSession,
    rbac_project: uuid.UUID,
):
    """Viewer should get 403 when trying to review a doc."""
    doc = KnowledgeDoc(
        id=uuid.uuid4(),
        project_id=rbac_project,
        doc_type="guide",
        title="RBAC Review Test",
        current_version=1,
        status="draft",
    )
    db_session.add(doc)
    await db_session.flush()

    resp = await client.post(f"/v1/docs/{doc.id}/review", headers=viewer_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_create_model_provider(
    client: AsyncClient, viewer_headers: dict
):
    """Viewer should get 403 when trying to create a model provider."""
    resp = await client.post(
        "/v1/model-providers",
        json={"provider_name": "openai", "api_key": "sk-test123", "base_url": "https://api.openai.com"},
        headers=viewer_headers,
    )
    assert resp.status_code == 403


# --- Editor should be forbidden from admin operations ---


@pytest.mark.asyncio
async def test_editor_cannot_publish_doc(
    client: AsyncClient,
    editor_headers: dict,
    db_session: AsyncSession,
    rbac_project: uuid.UUID,
):
    """Editor should get 403 when trying to publish (requires project_admin)."""
    doc = KnowledgeDoc(
        id=uuid.uuid4(),
        project_id=rbac_project,
        doc_type="guide",
        title="RBAC Publish Test",
        current_version=1,
        status="reviewing",
    )
    db_session.add(doc)
    await db_session.flush()

    resp = await client.post(f"/v1/docs/{doc.id}/publish", headers=editor_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_editor_cannot_invite_user(client: AsyncClient, editor_headers: dict):
    """Editor should get 403 when trying to invite users (requires tenant_admin)."""
    resp = await client.post(
        "/v1/users/invite",
        json={"email": "new@example.com", "role": "viewer"},
        headers=editor_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_editor_cannot_delete_project(
    client: AsyncClient, editor_headers: dict, rbac_project: uuid.UUID
):
    """Editor should get 403 when trying to delete a project (requires tenant_admin)."""
    resp = await client.delete(
        f"/v1/projects/{rbac_project}",
        headers=editor_headers,
    )
    assert resp.status_code == 403


# --- Viewer can still read ---


@pytest.mark.asyncio
async def test_viewer_can_list_projects(client: AsyncClient, viewer_headers: dict):
    """Viewer should be able to list projects (read-only)."""
    resp = await client.get("/v1/projects", headers=viewer_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_viewer_can_list_docs(
    client: AsyncClient, viewer_headers: dict, rbac_project: uuid.UUID
):
    """Viewer should be able to list docs (read-only)."""
    resp = await client.get(
        f"/v1/docs?project_id={rbac_project}",
        headers=viewer_headers,
    )
    assert resp.status_code == 200


# --- Admin (tenant_admin) can do everything ---


@pytest.mark.asyncio
async def test_admin_can_create_model_provider(
    client: AsyncClient, auth_headers: dict
):
    """Admin should be able to create a model provider."""
    resp = await client.post(
        "/v1/model-providers",
        json={"provider_name": "anthropic", "api_key": "sk-rbac-test", "base_url": "https://api.anthropic.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
