"""Tests for architecture endpoints."""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from shared_models import Architecture


@pytest_asyncio.fixture(loop_scope="session")
async def architecture_fixture(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    """Create a project and architecture directly for testing."""
    proj_resp = await client.post(
        "/v1/projects",
        json={"name": "Arch Test Project"},
        headers=auth_headers,
    )
    project_id = uuid.UUID(proj_resp.json()["data"]["id"])

    arch = Architecture(
        id=uuid.uuid4(),
        project_id=project_id,
        name="Test Architecture",
        version="1.0.0",
        status="draft",
    )
    db_session.add(arch)
    await db_session.flush()

    return {"project_id": project_id, "arch_id": arch.id}


@pytest.mark.asyncio
async def test_list_architectures(
    client: AsyncClient, auth_headers: dict, architecture_fixture: dict
):
    project_id = architecture_fixture["project_id"]
    resp = await client.get(
        f"/v1/projects/{project_id}/architectures",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 1


@pytest.mark.asyncio
async def test_get_architecture(
    client: AsyncClient, auth_headers: dict, architecture_fixture: dict
):
    arch_id = architecture_fixture["arch_id"]
    resp = await client.get(f"/v1/architectures/{arch_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Test Architecture"


@pytest.mark.asyncio
async def test_publish_architecture(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, architecture_fixture: dict
):
    # Create a new draft architecture to publish
    project_id = architecture_fixture["project_id"]
    arch = Architecture(
        id=uuid.uuid4(),
        project_id=project_id,
        name="Publish Me",
        version="1.0.0",
        status="draft",
    )
    db_session.add(arch)
    await db_session.flush()

    resp = await client.post(f"/v1/architectures/{arch.id}/publish", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "published"


@pytest.mark.asyncio
async def test_create_node(
    client: AsyncClient, auth_headers: dict, architecture_fixture: dict
):
    arch_id = architecture_fixture["arch_id"]
    resp = await client.post(
        f"/v1/architectures/{arch_id}/nodes",
        json={"node_name": "Test Node", "node_type": "category", "level": 0},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["node_name"] == "Test Node"
    assert data["node_type"] == "category"


@pytest.mark.asyncio
async def test_update_node(
    client: AsyncClient, auth_headers: dict, architecture_fixture: dict
):
    arch_id = architecture_fixture["arch_id"]
    create_resp = await client.post(
        f"/v1/architectures/{arch_id}/nodes",
        json={"node_name": "Update Me", "node_type": "topic", "level": 1},
        headers=auth_headers,
    )
    node_id = create_resp.json()["data"]["id"]

    resp = await client.patch(
        f"/v1/architectures/{arch_id}/nodes/{node_id}",
        json={"node_name": "Updated Node"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["node_name"] == "Updated Node"


@pytest.mark.asyncio
async def test_list_nodes(
    client: AsyncClient, auth_headers: dict, architecture_fixture: dict
):
    arch_id = architecture_fixture["arch_id"]
    resp = await client.get(f"/v1/architectures/{arch_id}/nodes", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["data"], list)
    assert data["meta"]["total"] >= 0


@pytest.mark.asyncio
async def test_list_nodes_with_created_node(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, architecture_fixture: dict
):
    """After creating a node, list should include it."""
    from shared_models import ArchitectureNode
    arch_id = architecture_fixture["arch_id"]
    node = ArchitectureNode(
        id=uuid.uuid4(), architecture_id=arch_id,
        node_name="Listed Node", node_type="category", level=0, status="draft",
    )
    db_session.add(node)
    await db_session.flush()

    resp = await client.get(f"/v1/architectures/{arch_id}/nodes", headers=auth_headers)
    assert resp.status_code == 200
    names = [n["node_name"] for n in resp.json()["data"]]
    assert "Listed Node" in names


@pytest.mark.asyncio
async def test_fork_architecture(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, architecture_fixture: dict
):
    """Forking should create a new architecture with copied nodes."""
    arch_id = architecture_fixture["arch_id"]
    # Add a node first
    from shared_models import ArchitectureNode
    node = ArchitectureNode(
        id=uuid.uuid4(), architecture_id=arch_id,
        node_name="Fork Me", node_type="topic", level=1, status="draft",
    )
    db_session.add(node)
    await db_session.flush()

    resp = await client.post(f"/v1/architectures/{arch_id}/fork", headers=auth_headers)
    assert resp.status_code == 201
    new_arch = resp.json()["data"]
    assert new_arch["id"] != str(arch_id)
    assert new_arch["status"] == "draft"

    # New arch should have copied nodes
    nodes_resp = await client.get(f"/v1/architectures/{new_arch['id']}/nodes", headers=auth_headers)
    names = [n["node_name"] for n in nodes_resp.json()["data"]]
    assert "Fork Me" in names


@pytest.mark.asyncio
async def test_compare_architectures(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, architecture_fixture: dict
):
    """Compare should show differences between two architectures."""
    arch_id = architecture_fixture["arch_id"]
    # Fork first
    fork_resp = await client.post(f"/v1/architectures/{arch_id}/fork", headers=auth_headers)
    new_id = fork_resp.json()["data"]["id"]

    # Add a node to the new arch only
    await client.post(
        f"/v1/architectures/{new_id}/nodes",
        json={"node_name": "New Only Node", "node_type": "category", "level": 0},
        headers=auth_headers,
    )

    resp = await client.get(
        f"/v1/architectures/{arch_id}/compare/{new_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    diff = resp.json()["data"]
    assert "added" in diff
    assert "removed" in diff
    assert "modified" in diff
    added_names = [n["node_name"] for n in diff["added"]]
    assert "New Only Node" in added_names


@pytest.mark.asyncio
async def test_get_architecture_not_found(client: AsyncClient, auth_headers: dict):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/v1/architectures/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404
