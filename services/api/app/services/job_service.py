"""Job service: CRUD with tenant isolation via project chain."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import ConflictException, ErrorCode, NotFoundException
from shared_models import Job, Project


class JobService:
    """Operations for jobs, scoped to a single tenant via project ownership."""

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

    async def create(self, project_id: uuid.UUID, job_type: str) -> Job:
        """Create a new job for a project."""
        await self._verify_project(project_id)
        job = Job(
            id=uuid.uuid4(),
            project_id=project_id,
            job_type=job_type,
            status="pending",
            retry_count=0,
            created_by=self.user_id,
        )
        self.db.add(job)
        await self.db.flush()
        return job

    async def list(
        self, project_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[Job], int]:
        """Return paginated jobs for a project (verify project belongs to tenant)."""
        await self._verify_project(project_id)

        base = select(Job).where(Job.project_id == project_id)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = base.order_by(Job.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.execute(q)).scalars().all()

        return list(rows), total

    async def get(self, job_id: uuid.UUID) -> Job:
        """Get a single job by ID. Verify via project->tenant chain."""
        q = select(Job).where(Job.id == job_id)
        result = await self.db.execute(q)
        job = result.scalar_one_or_none()
        if job is None:
            raise NotFoundException(
                error_code=ErrorCode.JOB_NOT_FOUND,
                message="Job not found",
            )
        # Verify tenant ownership via project
        await self._verify_project(job.project_id)
        return job

    async def retry(self, job_id: uuid.UUID) -> Job:
        """Retry a failed job. Only allowed if status is 'failed'."""
        job = await self.get(job_id)
        if job.status != "failed":
            raise ConflictException(
                error_code=ErrorCode.JOB_ALREADY_RUNNING,
                message="Only failed jobs can be retried",
            )
        job.status = "pending"
        job.retry_count += 1
        job.error_message = None
        await self.db.flush()
        await self.db.refresh(job)
        return job
