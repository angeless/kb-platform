"""Tests for TenantService base class (T-FIX-01).

Verifies _verify_project behavior using a lightweight mock DB session.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import TenantService


def _make_service(result_row=None) -> TenantService:
    """Create a TenantService with a mocked db session."""
    mock_db = AsyncMock()
    # mock_db.execute() returns a result whose .scalar_one_or_none() gives result_row
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = result_row
    mock_db.execute.return_value = mock_result

    return TenantService(db=mock_db, kb_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_verify_project_found():
    """When project exists and belongs to tenant, return it."""
    fake_project = MagicMock()
    svc = _make_service(result_row=fake_project)

    result = await svc._verify_project(uuid.uuid4())
    assert result is fake_project
    svc.db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_verify_project_not_found():
    """When project does not exist, raise NotFoundException."""
    from shared_errors import NotFoundException

    svc = _make_service(result_row=None)

    with pytest.raises(NotFoundException) as exc_info:
        await svc._verify_project(uuid.uuid4())

    assert exc_info.value.error_code == "PROJECT_NOT_FOUND"
    assert "项目不存在" in str(exc_info.value.message)


@pytest.mark.asyncio
async def test_verify_project_wrong_tenant():
    """When project belongs to another tenant, it won't match the query → NotFoundException."""
    from shared_errors import NotFoundException

    # The query filters by kb_id, so a wrong-tenant project simply returns None
    svc = _make_service(result_row=None)

    with pytest.raises(NotFoundException):
        await svc._verify_project(uuid.uuid4())


@pytest.mark.asyncio
async def test_service_inheritance():
    """All 8 services that had _verify_project should inherit from TenantService."""
    from app.services.architecture_service import ArchitectureService
    from app.services.asset_service import AssetService
    from app.services.conflict_service import ConflictService
    from app.services.doc_service import DocService
    from app.services.embedding_service import EmbeddingService
    from app.services.export_service import ExportService
    from app.services.job_service import JobService
    from app.services.search_service import SearchService

    for cls in [
        DocService,
        ArchitectureService,
        AssetService,
        ConflictService,
        JobService,
        EmbeddingService,
        SearchService,
        ExportService,
    ]:
        assert issubclass(cls, TenantService), f"{cls.__name__} should inherit TenantService"
