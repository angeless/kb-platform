"""Tests for T-36-03: IDOR prevention in doc_service.assign_node().

Verifies that the assign_node query joins Architecture to check project_id,
preventing cross-project node assignment.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared_errors import NotFoundException


def _make_doc(project_id: uuid.UUID) -> MagicMock:
    """Create a mock KnowledgeDoc."""
    doc = MagicMock()
    doc.id = uuid.uuid4()
    doc.project_id = project_id
    doc.node_id = None
    return doc


@pytest.mark.asyncio
async def test_assign_node_same_project_succeeds():
    """Node in the same project should be assignable."""
    from app.services.doc_service import DocService

    project_id = uuid.uuid4()
    doc = _make_doc(project_id)
    node_id = uuid.uuid4()
    fake_node = MagicMock()
    fake_node.id = node_id

    svc = DocService.__new__(DocService)
    svc.db = AsyncMock()
    svc.tenant_id = uuid.uuid4()

    # Mock self.get() to return the doc
    svc.get = AsyncMock(return_value=doc)

    # Mock db.execute for node query - returns a node (same project)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = fake_node
    svc.db.execute = AsyncMock(return_value=mock_result)
    svc.db.flush = AsyncMock()
    svc.db.refresh = AsyncMock()

    result = await svc.assign_node(doc.id, node_id)
    assert result.node_id == node_id
    svc.get.assert_awaited_once_with(doc.id)


@pytest.mark.asyncio
async def test_assign_node_different_project_raises_404():
    """Node in a different project should raise NotFoundException."""
    from app.services.doc_service import DocService

    project_id = uuid.uuid4()
    doc = _make_doc(project_id)
    other_node_id = uuid.uuid4()

    svc = DocService.__new__(DocService)
    svc.db = AsyncMock()
    svc.tenant_id = uuid.uuid4()

    svc.get = AsyncMock(return_value=doc)

    # Mock db.execute for node query - returns None (node not in same project)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    svc.db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(NotFoundException) as exc_info:
        await svc.assign_node(doc.id, other_node_id)

    assert exc_info.value.error_code == "ARCH_NODE_NOT_FOUND"
    assert "不属于当前项目" in str(exc_info.value.message)


@pytest.mark.asyncio
async def test_assign_node_nonexistent_raises_404():
    """Non-existent node_id should raise NotFoundException."""
    from app.services.doc_service import DocService

    project_id = uuid.uuid4()
    doc = _make_doc(project_id)
    fake_node_id = uuid.uuid4()

    svc = DocService.__new__(DocService)
    svc.db = AsyncMock()
    svc.tenant_id = uuid.uuid4()

    svc.get = AsyncMock(return_value=doc)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    svc.db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(NotFoundException) as exc_info:
        await svc.assign_node(doc.id, fake_node_id)

    assert exc_info.value.error_code == "ARCH_NODE_NOT_FOUND"


def test_assign_node_query_joins_architecture():
    """Verify the SQL query source code contains the Architecture JOIN."""
    import inspect
    from app.services.doc_service import DocService

    source = inspect.getsource(DocService.assign_node)

    # Must JOIN Architecture table
    assert "Architecture" in source
    assert "architecture_id" in source

    # Must check project_id match
    assert "project_id" in source

    # Error code should be ARCH_NODE_NOT_FOUND (not generic ARCH_NOT_FOUND)
    assert "ARCH_NODE_NOT_FOUND" in source
