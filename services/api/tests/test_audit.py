"""Tests for audit log endpoint and audit log creation on key operations."""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_models import AuditLog, KnowledgeDoc


@pytest_asyncio.fixture(loop_scope="session")
async def audit_project(client: AsyncClient, auth_headers: dict):
    """Create a project for audit tests."""
    resp = await client.post(
        "/v1/projects",
        json={"name": "Audit Test Project"},
        headers=auth_headers,
    )
    return uuid.UUID(resp.json()["data"]["id"])


@pytest.mark.asyncio
async def test_review_creates_audit_log(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
    audit_project: uuid.UUID,
):
    """Reviewing a doc should create an audit log entry."""
    doc = KnowledgeDoc(
        id=uuid.uuid4(),
        project_id=audit_project,
        doc_type="guide",
        title="Audit Review Test",
        current_version=1,
        status="draft",
    )
    db_session.add(doc)
    await db_session.flush()

    resp = await client.post(f"/v1/docs/{doc.id}/review", headers=auth_headers)
    assert resp.status_code == 200

    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.resource_id == doc.id,
            AuditLog.action == "review",
        )
    )
    audit = result.scalar_one_or_none()
    assert audit is not None
    assert audit.resource_type == "knowledge_doc"
    assert audit.action == "review"


@pytest.mark.asyncio
async def test_publish_creates_audit_log(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
    audit_project: uuid.UUID,
):
    """Publishing a doc should create an audit log entry."""
    doc = KnowledgeDoc(
        id=uuid.uuid4(),
        project_id=audit_project,
        doc_type="guide",
        title="Audit Publish Test",
        current_version=1,
        status="reviewing",
    )
    db_session.add(doc)
    await db_session.flush()

    resp = await client.post(f"/v1/docs/{doc.id}/publish", headers=auth_headers)
    assert resp.status_code == 200

    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.resource_id == doc.id,
            AuditLog.action == "publish",
        )
    )
    audit = result.scalar_one_or_none()
    assert audit is not None
    assert audit.resource_type == "knowledge_doc"


@pytest.mark.asyncio
async def test_list_audit_logs(
    client: AsyncClient,
    auth_headers: dict,
    audit_project: uuid.UUID,
):
    """GET /v1/audit-logs should return audit entries for the tenant."""
    resp = await client.get(
        f"/v1/audit-logs?project_id={audit_project}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "meta" in data
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_list_audit_logs_filter_by_action(
    client: AsyncClient,
    auth_headers: dict,
    audit_project: uuid.UUID,
):
    """Filtering by action should narrow results."""
    resp = await client.get(
        f"/v1/audit-logs?project_id={audit_project}&action=review",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    for entry in resp.json()["data"]:
        assert entry["action"] == "review"
