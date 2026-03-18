"""Tests for document export endpoints."""

import io
import uuid
import zipfile

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from shared_models import KnowledgeDoc, KnowledgeDocVersion


@pytest_asyncio.fixture(loop_scope="session")
async def export_fixture(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    """Create a project with docs for export testing."""
    proj_resp = await client.post(
        "/v1/projects",
        json={"name": "Export Test Project"},
        headers=auth_headers,
    )
    project_id = uuid.UUID(proj_resp.json()["data"]["id"])

    from sqlalchemy import select
    from shared_models import User
    users_result = await db_session.execute(select(User).limit(1))
    user = users_result.scalar_one()

    doc = KnowledgeDoc(
        id=uuid.uuid4(),
        project_id=project_id,
        doc_type="guide",
        title="Export Test Doc",
        current_version=1,
        status="published",
    )
    db_session.add(doc)
    await db_session.flush()

    ver = KnowledgeDocVersion(
        id=uuid.uuid4(),
        doc_id=doc.id,
        version=1,
        content_md="# Export Test\n\nThis is exported content.",
        change_reason="Initial",
        created_by=user.id,
    )
    db_session.add(ver)
    await db_session.flush()

    return {"project_id": project_id, "doc_id": doc.id}


@pytest.mark.asyncio
async def test_export_single_doc(
    client: AsyncClient, auth_headers: dict, export_fixture: dict
):
    """Exporting a single doc should return Markdown content."""
    doc_id = export_fixture["doc_id"]
    resp = await client.get(f"/v1/docs/{doc_id}/export", headers=auth_headers)
    assert resp.status_code == 200
    assert "text/markdown" in resp.headers["content-type"]
    assert "# Export Test" in resp.text
    assert "attachment" in resp.headers["content-disposition"]


@pytest.mark.asyncio
async def test_export_project_zip(
    client: AsyncClient, auth_headers: dict, export_fixture: dict
):
    """Exporting a project should return a valid ZIP file."""
    project_id = export_fixture["project_id"]
    resp = await client.get(f"/v1/projects/{project_id}/export", headers=auth_headers)
    assert resp.status_code == 200
    assert "application/zip" in resp.headers["content-type"]

    # Verify it's a valid ZIP
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    names = zf.namelist()
    assert any("index.md" in n for n in names)
    assert any("Export Test Doc.md" in n for n in names)
    zf.close()


@pytest.mark.asyncio
async def test_export_empty_project(
    client: AsyncClient, auth_headers: dict
):
    """Exporting a project with no docs should return a ZIP with just index."""
    proj_resp = await client.post(
        "/v1/projects",
        json={"name": "Empty Export Project"},
        headers=auth_headers,
    )
    project_id = proj_resp.json()["data"]["id"]

    resp = await client.get(f"/v1/projects/{project_id}/export", headers=auth_headers)
    assert resp.status_code == 200

    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    names = zf.namelist()
    assert any("index.md" in n for n in names)
    zf.close()
