"""Job service: CRUD with tenant isolation via project chain."""

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import ConflictException, ErrorCode, NotFoundException
from shared_models import Asset, Job, Project

logger = logging.getLogger(__name__)

# Celery task dispatch — lazy import to avoid hard dependency
_celery_app = None


def _get_celery_app():
    """Lazy-load Celery app to avoid import errors when Celery is not installed."""
    global _celery_app
    if _celery_app is None:
        try:
            from celery import Celery
            from shared_config.settings import get_settings
            settings = get_settings()
            _celery_app = Celery(broker=settings.redis_url)
        except Exception:
            logger.warning("Celery not available, tasks will not be dispatched")
    return _celery_app


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

    async def create(
        self,
        project_id: uuid.UUID,
        job_type: str,
        asset_id: uuid.UUID | None = None,
        asset_ids: list[str] | None = None,
    ) -> Job:
        """Create a new job for a project.

        For 'ingest' jobs, asset_id is required.
        For 'incremental' jobs, asset_ids is required.
        """
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

        # Dispatch Celery task for ingest jobs
        if job_type == "ingest" and asset_id is not None:
            celery = _get_celery_app()
            if celery is not None:
                try:
                    result = celery.send_task(
                        "ingestion.parse_asset",
                        args=[str(asset_id), str(job.id)],
                    )
                    job.celery_task_id = result.id
                    await self.db.flush()
                    logger.info("Dispatched parse_asset task for asset %s, job %s", asset_id, job.id)
                except Exception as e:
                    logger.warning("Failed to dispatch Celery task: %s (job %s still created)", e, job.id)

        # Dispatch Celery task for architecture_draft jobs
        elif job_type == "architecture_draft":
            celery = _get_celery_app()
            if celery is not None:
                try:
                    result = celery.send_task(
                        "orchestrator.propose_architecture",
                        args=[str(project_id), str(job.id)],
                    )
                    job.celery_task_id = result.id
                    await self.db.flush()
                    logger.info("Dispatched propose_architecture task for project %s, job %s", project_id, job.id)
                except Exception as e:
                    logger.warning("Failed to dispatch Celery task: %s (job %s still created)", e, job.id)

        # Dispatch Celery task for kb_generate jobs
        elif job_type == "kb_generate":
            celery = _get_celery_app()
            if celery is not None:
                try:
                    result = celery.send_task(
                        "orchestrator.generate_docs",
                        args=[str(project_id), str(job.id)],
                    )
                    job.celery_task_id = result.id
                    await self.db.flush()
                    logger.info("Dispatched generate_docs task for project %s, job %s", project_id, job.id)
                except Exception as e:
                    logger.warning("Failed to dispatch Celery task: %s (job %s still created)", e, job.id)

        # Dispatch Celery task for incremental jobs
        elif job_type == "incremental" and asset_ids:
            celery = _get_celery_app()
            if celery is not None:
                try:
                    result = celery.send_task(
                        "orchestrator.classify_incremental",
                        args=[str(project_id), str(job.id), asset_ids],
                    )
                    job.celery_task_id = result.id
                    await self.db.flush()
                    logger.info("Dispatched classify_incremental task for project %s, job %s", project_id, job.id)
                except Exception as e:
                    logger.warning("Failed to dispatch Celery task: %s (job %s still created)", e, job.id)

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
        """Retry a failed job. Only allowed if status is 'failed'.

        Re-dispatches the corresponding Celery task after resetting status.
        """
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

        # Re-dispatch the Celery task
        self._dispatch_celery(job)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    def _dispatch_celery(self, job: Job) -> None:
        """Dispatch a Celery task for the given job. Silent on failure."""
        task_map = {
            "ingest": "ingestion.parse_asset",
            "architecture_draft": "orchestrator.propose_architecture",
            "kb_generate": "orchestrator.generate_docs",
            "incremental": "orchestrator.classify_incremental",
        }
        task_name = task_map.get(job.job_type)
        if task_name is None:
            return

        celery = _get_celery_app()
        if celery is None:
            return

        try:
            if job.job_type == "ingest":
                # For ingest, we need asset_id — stored in job context or we skip
                result = celery.send_task(task_name, args=[str(job.project_id), str(job.id)])
            elif job.job_type == "incremental":
                result = celery.send_task(task_name, args=[str(job.project_id), str(job.id), []])
            else:
                result = celery.send_task(task_name, args=[str(job.project_id), str(job.id)])
            job.celery_task_id = result.id
            logger.info("Re-dispatched %s task for job %s", task_name, job.id)
        except Exception as e:
            logger.warning("Failed to re-dispatch Celery task on retry: %s (job %s)", e, job.id)
