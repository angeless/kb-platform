"""Knowledge document service: list, get, review, publish with tenant isolation."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import ConflictException, ErrorCode, NotFoundException
from shared_models import KnowledgeDoc, KnowledgeDocVersion, Project


class DocService:
    """Operations for knowledge documents, scoped to a single tenant."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id

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
    ) -> tuple[list[KnowledgeDoc], int]:
        """Return paginated docs for a project."""
        await self._verify_project(project_id)

        base = select(KnowledgeDoc).where(KnowledgeDoc.project_id == project_id)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = base.order_by(KnowledgeDoc.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.execute(q)).scalars().all()

        return list(rows), total

    async def get(self, doc_id: uuid.UUID) -> KnowledgeDoc:
        """Get doc with versions. Verify via project->tenant chain."""
        q = select(KnowledgeDoc).where(KnowledgeDoc.id == doc_id)
        result = await self.db.execute(q)
        doc = result.scalar_one_or_none()
        if doc is None:
            raise NotFoundException(
                error_code=ErrorCode.DOC_NOT_FOUND,
                message="Document not found",
            )
        await self._verify_project(doc.project_id)
        return doc

    async def get_version(self, doc_id: uuid.UUID, version: int) -> KnowledgeDocVersion:
        """Get a specific version of a document."""
        doc = await self.get(doc_id)
        q = select(KnowledgeDocVersion).where(
            KnowledgeDocVersion.doc_id == doc.id,
            KnowledgeDocVersion.version == version,
        )
        result = await self.db.execute(q)
        ver = result.scalar_one_or_none()
        if ver is None:
            raise NotFoundException(
                error_code=ErrorCode.DOC_NOT_FOUND,
                message=f"Version {version} not found",
            )
        return ver

    async def review(self, doc_id: uuid.UUID) -> KnowledgeDoc:
        """Transition doc status to 'reviewing'. Only from 'draft'."""
        doc = await self.get(doc_id)
        if doc.status != "draft":
            raise ConflictException(
                error_code=ErrorCode.DOC_ALREADY_PUBLISHED,
                message="Document can only be reviewed from draft status",
            )
        doc.status = "reviewing"
        await self.db.flush()
        await self.db.refresh(doc)
        return doc

    async def publish(self, doc_id: uuid.UUID) -> KnowledgeDoc:
        """Transition doc status to 'published'. Only from 'reviewing'."""
        doc = await self.get(doc_id)
        if doc.status != "reviewing":
            raise ConflictException(
                error_code=ErrorCode.DOC_ALREADY_PUBLISHED,
                message="Document can only be published from reviewing status",
            )
        doc.status = "published"
        await self.db.flush()
        await self.db.refresh(doc)
        return doc
