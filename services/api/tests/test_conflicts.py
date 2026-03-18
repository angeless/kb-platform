"""Tests for conflict endpoints."""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from shared_models import ConflictRecord


@pytest_asyncio.fixture(loop_scope="session")
async def conflict_fixture(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    """Create a project and conflict record directly for testing."""
    proj_resp = await client.post(
        "/v1/projects",
        json={"name": "Conflict Test Project"},
        headers=auth_headers,
    )
    project_id = uuid.UUID(proj_resp.json()["data"]["id"])

    conflict = ConflictRecord(
        id=uuid.uuid4(),
        project_id=project_id,
        description="Test conflict description",
        status="open",
    )
    db_session.add(conflict)
    await db_session.flush()

    return {"project_id": project_id, "conflict_id": conflict.id}


@pytest.mark.asyncio
async def test_list_conflicts(
    client: AsyncClient, auth_headers: dict, conflict_fixture: dict
):
    project_id = conflict_fixture["project_id"]
    resp = await client.get(
        f"/v1/conflicts?project_id={project_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 1


@pytest.mark.asyncio
async def test_get_conflict(
    client: AsyncClient, auth_headers: dict, conflict_fixture: dict
):
    conflict_id = conflict_fixture["conflict_id"]
    resp = await client.get(f"/v1/conflicts/{conflict_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["description"] == "Test conflict description"


@pytest.mark.asyncio
async def test_resolve_conflict(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, conflict_fixture: dict
):
    # Create a new open conflict to resolve
    project_id = conflict_fixture["project_id"]
    conflict = ConflictRecord(
        id=uuid.uuid4(),
        project_id=project_id,
        description="Resolve me",
        status="open",
    )
    db_session.add(conflict)
    await db_session.flush()

    resp = await client.post(
        f"/v1/conflicts/{conflict.id}/resolve",
        json={"resolution_note": "Fixed by updating the doc"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "resolved"
    assert data["resolved_by"] is not None


@pytest.mark.asyncio
async def test_resolve_already_resolved(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, conflict_fixture: dict
):
    project_id = conflict_fixture["project_id"]
    conflict = ConflictRecord(
        id=uuid.uuid4(),
        project_id=project_id,
        description="Already resolved",
        status="resolved",
    )
    db_session.add(conflict)
    await db_session.flush()

    resp = await client.post(
        f"/v1/conflicts/{conflict.id}/resolve",
        json={"resolution_note": "Try again"},
        headers=auth_headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_conflict_not_found(client: AsyncClient, auth_headers: dict):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/v1/conflicts/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404
