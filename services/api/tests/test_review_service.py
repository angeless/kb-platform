"""Unit tests for ReviewService — approval workflow API logic (v0.50.2)."""

import uuid
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from app.services.review_service import ReviewService
from shared_models.review_task import ReviewTask


def _make_task(status="pending", reviewer_id=None, created_by=None):
    task = MagicMock(spec=ReviewTask)
    task.id = uuid.uuid4()
    task.project_id = uuid.uuid4()
    task.doc_id = uuid.uuid4()
    task.status = status
    task.reviewer_id = reviewer_id
    task.created_by = created_by or uuid.uuid4()
    task.assigned_at = None
    task.reviewed_at = None
    task.review_note = None
    task.created_at = MagicMock(isoformat=MagicMock(return_value="2026-04-03T00:00:00"))
    return task


def _make_doc(status="draft"):
    doc = MagicMock()
    doc.id = uuid.uuid4()
    doc.status = status
    return doc


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def svc(mock_db):
    kb_id = uuid.uuid4()
    service = ReviewService(mock_db, kb_id)
    service._verify_project = AsyncMock()
    return service


class TestCreateReview:
    @pytest.mark.asyncio
    async def test_creates_pending_task(self, svc, mock_db):
        doc = _make_doc("draft")
        svc._get_doc = AsyncMock(return_value=doc)
        task = await svc.create(uuid.uuid4(), doc.id, uuid.uuid4())
        assert mock_db.add.called

    @pytest.mark.asyncio
    async def test_rejects_approved_doc(self, svc):
        doc = _make_doc("approved")
        svc._get_doc = AsyncMock(return_value=doc)
        from shared_errors import AppException
        with pytest.raises(AppException):
            await svc.create(uuid.uuid4(), doc.id, uuid.uuid4())


class TestAssign:
    @pytest.mark.asyncio
    async def test_assigns_reviewer(self, svc, mock_db):
        task = _make_task("pending")
        svc._get_review = AsyncMock(return_value=task)
        reviewer = MagicMock()
        reviewer.id = uuid.uuid4()
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=reviewer)))
        result = await svc.assign(uuid.uuid4(), task.id, reviewer.id)
        assert result.status == "assigned"


class TestApprove:
    @pytest.mark.asyncio
    async def test_approves_and_syncs_doc(self, svc):
        reviewer_id = uuid.uuid4()
        task = _make_task("assigned", reviewer_id=reviewer_id)
        doc = _make_doc("pending")
        svc._get_review = AsyncMock(return_value=task)
        svc._get_doc = AsyncMock(return_value=doc)
        result = await svc.approve(uuid.uuid4(), task.id, reviewer_id)
        assert result.status == "approved"
        assert doc.status == "approved"

    @pytest.mark.asyncio
    async def test_rejects_non_reviewer(self, svc):
        task = _make_task("assigned", reviewer_id=uuid.uuid4())
        svc._get_review = AsyncMock(return_value=task)
        from shared_errors import AppException
        with pytest.raises(AppException, match="仅审批人"):
            await svc.approve(uuid.uuid4(), task.id, uuid.uuid4())


class TestReject:
    @pytest.mark.asyncio
    async def test_rejects_with_note(self, svc):
        reviewer_id = uuid.uuid4()
        task = _make_task("assigned", reviewer_id=reviewer_id)
        svc._get_review = AsyncMock(return_value=task)
        result = await svc.reject(uuid.uuid4(), task.id, reviewer_id, "需要修改")
        assert result.status == "rejected"

    @pytest.mark.asyncio
    async def test_rejects_empty_note(self, svc):
        reviewer_id = uuid.uuid4()
        task = _make_task("assigned", reviewer_id=reviewer_id)
        svc._get_review = AsyncMock(return_value=task)
        from shared_errors import AppException
        with pytest.raises(AppException, match="不能为空"):
            await svc.reject(uuid.uuid4(), task.id, reviewer_id, "")


class TestResubmit:
    @pytest.mark.asyncio
    async def test_resubmits_and_reassigns(self, svc):
        creator = uuid.uuid4()
        task = _make_task("rejected", reviewer_id=uuid.uuid4(), created_by=creator)
        svc._get_review = AsyncMock(return_value=task)
        result = await svc.resubmit(uuid.uuid4(), task.id, creator)
        assert result.status == "assigned"

    @pytest.mark.asyncio
    async def test_rejects_non_creator(self, svc):
        task = _make_task("rejected", created_by=uuid.uuid4())
        svc._get_review = AsyncMock(return_value=task)
        from shared_errors import AppException
        with pytest.raises(AppException, match="仅创建者"):
            await svc.resubmit(uuid.uuid4(), task.id, uuid.uuid4())
