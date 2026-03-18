"""Conflict service: list, get, resolve with tenant isolation."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import ConflictException, ErrorCode, NotFoundException
from shared_models import ConflictRecord, Project


class ConflictService:
    """Operations for conflict records, scoped to a single tenant."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def _verify_project(self, project_id: uuid.UUID) -> Project:
        """Verify project exists and belongs to tenant."""
        q = select(Project).where(
            Project.id == project_id,
            Project.tenant_id == self.tenant_id,
            Project.status != "deleted",
        )
        result = await self.db.execute(q)
        project = result.scalar_one_or_none()
        if project is None:
            raise NotFoundException(
                error_code=ErrorCode.PROJECT_NOT_FOUND,
                message="Project not found",
            )
        return project

    async def list(
        self, project_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[ConflictRecord], int]:
        """Return paginated conflicts for a project."""
        await self._verify_project(project_id)

        base = select(ConflictRecord).where(ConflictRecord.project_id == project_id)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = base.order_by(ConflictRecord.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.execute(q)).scalars().all()

        return list(rows), total

    async def get(self, conflict_id: uuid.UUID) -> ConflictRecord:
        """Get a single conflict by ID. Verify via project->tenant chain."""
        q = select(ConflictRecord).where(ConflictRecord.id == conflict_id)
        result = await self.db.execute(q)
        conflict = result.scalar_one_or_none()
        if conflict is None:
            raise NotFoundException(
                error_code=ErrorCode.CONFLICT_NOT_FOUND,
                message="Conflict not found",
            )
        await self._verify_project(conflict.project_id)
        return conflict

    async def resolve(self, conflict_id: uuid.UUID, resolution_note: str) -> ConflictRecord:
        """Resolve a conflict. Only if status is 'open'."""
        conflict = await self.get(conflict_id)
        if conflict.status != "open":
            raise ConflictException(
                error_code=ErrorCode.CONFLICT_ALREADY_RESOLVED,
                message="Conflict is already resolved",
            )
        conflict.status = "resolved"
        conflict.resolved_by = self.user_id
        conflict.resolved_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(conflict)
        return conflict
