"""Tests for knowledge doc endpoints."""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from shared_models import KnowledgeDoc, KnowledgeDocVersion


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
        content_md="# Test Content",
        change_reason="Initial version",
        created_by=user.id,
    )
    db_session.add(version)
    await db_session.flush()

    return {"project_id": project_id, "doc_id": doc.id, "user_id": user.id}


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
    assert resp.json()["data"]["title"] == "Test Doc"


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
async def test_get_doc_not_found(client: AsyncClient, auth_headers: dict):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/v1/docs/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404
