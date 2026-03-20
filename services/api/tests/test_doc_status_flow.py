"""Tests for T-36-04: Document status flow validation.

Verifies that publish/review/reject/update_content enforce correct
status preconditions and return DOC_STATUS_INVALID on violation.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from shared_errors import ConflictException


def _make_doc_service(doc_status: str):
    """Create a DocService instance with a mocked doc in the given status."""
    from app.services.doc_service import DocService

    doc = MagicMock()
    doc.id = uuid.uuid4()
    doc.project_id = uuid.uuid4()
    doc.status = doc_status
    doc.current_version = 1

    svc = DocService.__new__(DocService)
    svc.db = AsyncMock()
    svc.tenant_id = uuid.uuid4()
    svc.get = AsyncMock(return_value=doc)
    svc.db.flush = AsyncMock()
    svc.db.refresh = AsyncMock()

    return svc, doc


class TestPublishStatusCheck:
    """publish() must only accept 'reviewing' status."""

    @pytest.mark.asyncio
    async def test_publish_from_reviewing_succeeds(self):
        svc, doc = _make_doc_service("reviewing")
        result = await svc.publish(doc.id)
        assert result.status == "published"

    @pytest.mark.asyncio
    async def test_publish_from_draft_raises_409(self):
        svc, doc = _make_doc_service("draft")
        with pytest.raises(ConflictException) as exc_info:
            await svc.publish(doc.id)
        assert exc_info.value.error_code == "DOC_STATUS_INVALID"
        assert "必须先进入审核状态" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_publish_from_published_raises_409(self):
        svc, doc = _make_doc_service("published")
        with pytest.raises(ConflictException) as exc_info:
            await svc.publish(doc.id)
        assert exc_info.value.error_code == "DOC_STATUS_INVALID"


class TestReviewStatusCheck:
    """review() must only accept 'draft' status."""

    @pytest.mark.asyncio
    async def test_review_from_draft_succeeds(self):
        svc, doc = _make_doc_service("draft")
        result = await svc.review(doc.id)
        assert result.status == "reviewing"

    @pytest.mark.asyncio
    async def test_review_from_reviewing_raises_409(self):
        svc, doc = _make_doc_service("reviewing")
        with pytest.raises(ConflictException) as exc_info:
            await svc.review(doc.id)
        assert exc_info.value.error_code == "DOC_STATUS_INVALID"

    @pytest.mark.asyncio
    async def test_review_from_published_raises_409(self):
        svc, doc = _make_doc_service("published")
        with pytest.raises(ConflictException) as exc_info:
            await svc.review(doc.id)
        assert exc_info.value.error_code == "DOC_STATUS_INVALID"


class TestRejectStatusCheck:
    """reject() must only accept 'reviewing' status."""

    @pytest.mark.asyncio
    async def test_reject_from_reviewing_succeeds(self):
        svc, doc = _make_doc_service("reviewing")
        result = await svc.reject(doc.id)
        assert result.status == "draft"

    @pytest.mark.asyncio
    async def test_reject_from_draft_raises_409(self):
        svc, doc = _make_doc_service("draft")
        with pytest.raises(ConflictException) as exc_info:
            await svc.reject(doc.id)
        assert exc_info.value.error_code == "DOC_STATUS_INVALID"


class TestUpdateContentStatusCheck:
    """update_content() must only accept 'draft' status."""

    @pytest.mark.asyncio
    async def test_update_from_draft_succeeds(self):
        svc, doc = _make_doc_service("draft")
        svc.db.add = MagicMock()
        result = await svc.update_content(doc.id, "new content", "reason", uuid.uuid4())
        assert result.current_version == 2

    @pytest.mark.asyncio
    async def test_update_from_published_raises_409(self):
        svc, doc = _make_doc_service("published")
        with pytest.raises(ConflictException) as exc_info:
            await svc.update_content(doc.id, "content", "reason", uuid.uuid4())
        assert exc_info.value.error_code == "DOC_STATUS_INVALID"

    @pytest.mark.asyncio
    async def test_update_from_reviewing_raises_409(self):
        svc, doc = _make_doc_service("reviewing")
        with pytest.raises(ConflictException) as exc_info:
            await svc.update_content(doc.id, "content", "reason", uuid.uuid4())
        assert exc_info.value.error_code == "DOC_STATUS_INVALID"
