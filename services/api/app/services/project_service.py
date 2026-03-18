"""Project service: CRUD with tenant isolation."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import ErrorCode, NotFoundException
from shared_models import Project


class ProjectService:
    """CRUD operations for projects, scoped to a single tenant."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id

    async def create(self, name: str, industry_hint: str | None = None) -> Project:
        """Create a new project."""
        project = Project(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            name=name,
            industry_hint=industry_hint,
            status="active",
        )
        self.db.add(project)
        await self.db.flush()
        return project

    async def list(self, page: int = 1, page_size: int = 20) -> tuple[list[Project], int]:
        """Return paginated projects (excluding deleted) for the tenant."""
        base = select(Project).where(
            Project.tenant_id == self.tenant_id,
            Project.status != "deleted",
        )

        # Total count
        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        # Paginated results
        q = base.order_by(Project.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.execute(q)).scalars().all()

        return list(rows), total

    async def get(self, project_id: uuid.UUID) -> Project:
        """Get a single project by ID. Raises NotFoundException."""
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

    async def update(self, project_id: uuid.UUID, **kwargs) -> Project:
        """Update project fields (only non-None values)."""
        project = await self.get(project_id)
        for key, value in kwargs.items():
            if value is not None:
                setattr(project, key, value)
        await self.db.flush()
        await self.db.refresh(project)
        return project

    async def delete(self, project_id: uuid.UUID) -> Project:
        """Soft-delete a project by setting status to 'deleted'."""
        project = await self.get(project_id)
        project.status = "deleted"
        await self.db.flush()
        return project
