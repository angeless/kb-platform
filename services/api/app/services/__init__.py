"""Service layer base classes."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import ErrorCode, NotFoundException
from shared_models import Project


class TenantService:
    """Base service with tenant-scoped project verification.

    All services that operate within a project context should inherit
    from this class to avoid duplicating the _verify_project logic.
    """

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id

    async def _verify_project(self, project_id: uuid.UUID) -> Project:
        """Verify project exists and belongs to tenant.

        Returns the Project if valid, raises NotFoundException otherwise.
        """
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
                message="项目不存在",
            )
        return project
