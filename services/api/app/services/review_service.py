"""Review service: approval workflow operations with state machine enforcement."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import AppException, ErrorCode, ForbiddenException, NotFoundException
from shared_models import KnowledgeDoc, User
from shared_models.review_task import ReviewTask, validate_transition

from . import TenantService


class ReviewService(TenantService):
    """Approval workflow operations, scoped to tenant via project."""

    async def create(
        self, project_id: uuid.UUID, doc_id: uuid.UUID, created_by: uuid.UUID
    ) -> ReviewTask:
        """Create a review task for a document."""
        await self._verify_project(project_id)

        doc = await self._get_doc(doc_id, project_id)
        if doc.status not in ("draft", "pending"):
            raise AppException(
                error_code=ErrorCode.VALIDATION_ERROR,
                message=f"文档状态 '{doc.status}' 不允许创建审批（需要 draft 或 pending）",
            )

        task = ReviewTask(
            id=uuid.uuid4(),
            project_id=project_id,
            doc_id=doc_id,
            status="pending",
            created_by=created_by,
        )
        self.db.add(task)
        await self.db.flush()
        return task

    async def assign(
        self, project_id: uuid.UUID, review_id: uuid.UUID, reviewer_id: uuid.UUID
    ) -> ReviewTask:
        """Assign a reviewer to a review task."""
        task = await self._get_review(review_id, project_id)
        self._assert_transition(task, "assigned")

        # Verify reviewer exists
        reviewer = (await self.db.execute(
            select(User).where(User.id == reviewer_id)
        )).scalar_one_or_none()
        if reviewer is None:
            raise NotFoundException(
                error_code=ErrorCode.USER_NOT_FOUND,
                message="审批人不存在",
            )

        task.status = "assigned"
        task.reviewer_id = reviewer_id
        task.assigned_at = datetime.now(timezone.utc)
        await self.db.flush()
        return task

    async def approve(
        self, project_id: uuid.UUID, review_id: uuid.UUID, user_id: uuid.UUID, note: str | None = None
    ) -> ReviewTask:
        """Approve a review task. Also updates doc.status to approved."""
        task = await self._get_review(review_id, project_id)
        self._assert_transition(task, "approved")
        self._assert_reviewer(task, user_id)

        task.status = "approved"
        task.reviewed_at = datetime.now(timezone.utc)
        if note:
            task.review_note = note

        # Sync doc status
        doc = await self._get_doc(task.doc_id, project_id)
        doc.status = "approved"

        await self.db.flush()
        return task

    async def reject(
        self, project_id: uuid.UUID, review_id: uuid.UUID, user_id: uuid.UUID, note: str
    ) -> ReviewTask:
        """Reject a review task. Note is required."""
        if not note or not note.strip():
            raise AppException(
                error_code=ErrorCode.VALIDATION_ERROR,
                message="驳回原因不能为空",
            )

        task = await self._get_review(review_id, project_id)
        self._assert_transition(task, "rejected")
        self._assert_reviewer(task, user_id)

        task.status = "rejected"
        task.reviewed_at = datetime.now(timezone.utc)
        task.review_note = note

        await self.db.flush()
        return task

    async def resubmit(
        self, project_id: uuid.UUID, review_id: uuid.UUID, user_id: uuid.UUID
    ) -> ReviewTask:
        """Resubmit a rejected review. Auto-reassigns to original reviewer."""
        task = await self._get_review(review_id, project_id)
        self._assert_transition(task, "resubmitted")

        if task.created_by != user_id:
            raise ForbiddenException(
                message="仅创建者可重新提交",
            )

        task.status = "assigned"  # resubmitted → assigned (auto-reassign)
        task.reviewed_at = None
        task.review_note = None
        await self.db.flush()
        return task

    async def list_reviews(
        self, project_id: uuid.UUID, status: str | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[ReviewTask], int]:
        """List review tasks for a project with optional status filter."""
        await self._verify_project(project_id)

        base = select(ReviewTask).where(ReviewTask.project_id == project_id)
        if status:
            base = base.where(ReviewTask.status == status)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = base.order_by(ReviewTask.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.execute(q)).scalars().all()
        return list(rows), total

    # --- Private helpers ---

    async def _get_review(self, review_id: uuid.UUID, project_id: uuid.UUID) -> ReviewTask:
        task = (await self.db.execute(
            select(ReviewTask).where(ReviewTask.id == review_id, ReviewTask.project_id == project_id)
        )).scalar_one_or_none()
        if task is None:
            raise NotFoundException(error_code=ErrorCode.VALIDATION_ERROR, message="审批任务不存在")
        return task

    async def _get_doc(self, doc_id: uuid.UUID, project_id: uuid.UUID) -> KnowledgeDoc:
        doc = (await self.db.execute(
            select(KnowledgeDoc).where(KnowledgeDoc.id == doc_id, KnowledgeDoc.project_id == project_id)
        )).scalar_one_or_none()
        if doc is None:
            raise NotFoundException(error_code=ErrorCode.DOC_NOT_FOUND, message="文档不存在")
        return doc

    @staticmethod
    def _assert_transition(task: ReviewTask, target: str) -> None:
        if not validate_transition(task.status, target):
            raise AppException(
                error_code=ErrorCode.VALIDATION_ERROR,
                message=f"不允许从 '{task.status}' 转换到 '{target}'",
            )

    @staticmethod
    def _assert_reviewer(task: ReviewTask, user_id: uuid.UUID) -> None:
        if task.reviewer_id != user_id:
            raise ForbiddenException(
                message="仅审批人可执行此操作",
            )
