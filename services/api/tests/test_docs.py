"""Tests for knowledge doc endpoints."""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from shared_models import Asset, AssetChunk, KnowledgeDoc, KnowledgeDocVersion, SourceRef


@pytest_asyncio.fixture(loop_scope="session")
async def doc_fixture(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    """Create a project, doc, and doc version directly for testing."""
    proj_resp = await client.post(
        "/v1/projects",
        json={"name": "Doc Test Project"},
        headers=auth_headers,
    )
    project_id = uuid.UUID(proj_resp.json()["data"]["id"])

    # Get user_id from the token by looking at the user we created
    from sqlalchemy import select
    from shared_models import User

    users_result = await db_session.execute(select(User).limit(1))
    user = users_result.scalar_one()

    doc = KnowledgeDoc(
        id=uuid.uuid4(),
        project_id=project_id,
        doc_type="api_reference",
        title="Test Doc",
        current_version=1,
        status="draft",
    )
    db_session.add(doc)
    await db_session.flush()

    version = KnowledgeDocVersion(
        id=uuid.uuid4(),
        doc_id=doc.id,
        version=1,
        content_md="# Test Content\n\nSome text [来源0]",
        change_reason="Initial version",
        created_by=user.id,
    )
    db_session.add(version)
    await db_session.flush()

    # Create an asset + chunk + source_ref for traceability testing
    asset = Asset(
        id=uuid.uuid4(),
        project_id=project_id,
        asset_type="text",
        filename="test.txt",
        parse_status="parsed",
        uploaded_by=user.id,
    )
    db_session.add(asset)
    await db_session.flush()

    chunk = AssetChunk(
        id=uuid.uuid4(),
        asset_id=asset.id,
        chunk_index=0,
        content_text="Original source text",
    )
    db_session.add(chunk)
    await db_session.flush()

    source_ref = SourceRef(
        id=uuid.uuid4(),
        doc_version_id=version.id,
        asset_chunk_id=chunk.id,
        location_hint="page 1",
    )
    db_session.add(source_ref)
    await db_session.flush()

    # Add a second version for diff testing
    version2 = KnowledgeDocVersion(
        id=uuid.uuid4(),
        doc_id=doc.id,
        version=2,
        content_md="# Test Content\n\nUpdated paragraph with new info",
        change_reason="Supplemented with new info",
        created_by=user.id,
    )
    db_session.add(version2)
    doc.current_version = 2
    await db_session.flush()

    return {
        "project_id": project_id,
        "doc_id": doc.id,
        "user_id": user.id,
        "version_id": version.id,
        "chunk_id": chunk.id,
    }


@pytest.mark.asyncio
async def test_list_docs(client: AsyncClient, auth_headers: dict, doc_fixture: dict):
    project_id = doc_fixture["project_id"]
    resp = await client.get(
        f"/v1/docs?project_id={project_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 1


@pytest.mark.asyncio
async def test_get_doc_with_versions(
    client: AsyncClient, auth_headers: dict, doc_fixture: dict
):
    doc_id = doc_fixture["doc_id"]
    resp = await client.get(f"/v1/docs/{doc_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["title"] == "Test Doc"
    # Should include versions with content
    assert "versions" in data
    assert len(data["versions"]) >= 1
    ver = data["versions"][0]
    assert "content_md" in ver
    assert "# Test Content" in ver["content_md"]
    # Should include source_refs in version
    assert "source_refs" in ver
    assert len(ver["source_refs"]) >= 1
    ref = ver["source_refs"][0]
    assert ref["location_hint"] == "page 1"
    assert ref["asset_chunk_id"] == str(doc_fixture["chunk_id"])


@pytest.mark.asyncio
async def test_get_doc_version(
    client: AsyncClient, auth_headers: dict, doc_fixture: dict
):
    doc_id = doc_fixture["doc_id"]
    resp = await client.get(f"/v1/docs/{doc_id}/versions/1", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["version"] == 1
    assert "# Test Content" in data["content_md"]
    assert len(data["source_refs"]) >= 1


@pytest.mark.asyncio
async def test_get_doc_version_not_found(
    client: AsyncClient, auth_headers: dict, doc_fixture: dict
):
    doc_id = doc_fixture["doc_id"]
    resp = await client.get(f"/v1/docs/{doc_id}/versions/999", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_review_doc(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, doc_fixture: dict
):
    # Create a new draft doc to review
    project_id = doc_fixture["project_id"]
    user_id = doc_fixture["user_id"]
    doc = KnowledgeDoc(
        id=uuid.uuid4(),
        project_id=project_id,
        doc_type="guide",
        title="Review Me",
        current_version=1,
        status="draft",
    )
    db_session.add(doc)
    await db_session.flush()

    resp = await client.post(f"/v1/docs/{doc.id}/review", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "reviewing"


@pytest.mark.asyncio
async def test_publish_doc(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, doc_fixture: dict
):
    project_id = doc_fixture["project_id"]
    doc = KnowledgeDoc(
        id=uuid.uuid4(),
        project_id=project_id,
        doc_type="guide",
        title="Publish Me",
        current_version=1,
        status="reviewing",
    )
    db_session.add(doc)
    await db_session.flush()

    resp = await client.post(f"/v1/docs/{doc.id}/publish", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "published"


@pytest.mark.asyncio
async def test_invalid_transition(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, doc_fixture: dict
):
    project_id = doc_fixture["project_id"]
    doc = KnowledgeDoc(
        id=uuid.uuid4(),
        project_id=project_id,
        doc_type="guide",
        title="Already Published",
        current_version=1,
        status="published",
    )
    db_session.add(doc)
    await db_session.flush()

    # Try to review a published doc
    resp = await client.post(f"/v1/docs/{doc.id}/review", headers=auth_headers)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_diff_versions(
    client: AsyncClient, auth_headers: dict, doc_fixture: dict
):
    doc_id = doc_fixture["doc_id"]
    resp = await client.get(
        f"/v1/docs/{doc_id}/diff?from_version=1&to_version=2",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["from_version"] == 1
    assert data["to_version"] == 2
    assert data["from_change_reason"] == "Initial version"
    assert data["to_change_reason"] == "Supplemented with new info"
    assert len(data["diff_lines"]) > 0
    assert data["stats"]["added"] >= 1 or data["stats"]["removed"] >= 1


@pytest.mark.asyncio
async def test_diff_same_version(
    client: AsyncClient, auth_headers: dict, doc_fixture: dict
):
    doc_id = doc_fixture["doc_id"]
    resp = await client.get(
        f"/v1/docs/{doc_id}/diff?from_version=1&to_version=1",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["stats"]["added"] == 0
    assert data["stats"]["removed"] == 0


@pytest.mark.asyncio
async def test_diff_version_not_found(
    client: AsyncClient, auth_headers: dict, doc_fixture: dict
):
    doc_id = doc_fixture["doc_id"]
    resp = await client.get(
        f"/v1/docs/{doc_id}/diff?from_version=1&to_version=999",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_doc_not_found(client: AsyncClient, auth_headers: dict):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/v1/docs/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404
