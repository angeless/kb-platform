"""Knowledge document service: list, get, review, publish, diff with tenant isolation."""

from __future__ import annotations

import difflib
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import ConflictException, ErrorCode, NotFoundException
from shared_models import ArchitectureNode, KnowledgeDoc, KnowledgeDocVersion, Project


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

    async def list_pending(
        self, project_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[KnowledgeDoc], int]:
        """Return docs with node_id=NULL (pending node assignment)."""
        await self._verify_project(project_id)

        base = select(KnowledgeDoc).where(
            KnowledgeDoc.project_id == project_id,
            KnowledgeDoc.node_id.is_(None),
        )

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = base.order_by(KnowledgeDoc.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
        rows = (await self.db.execute(q)).scalars().all()

        return list(rows), total

    async def assign_node(self, doc_id: uuid.UUID, node_id: uuid.UUID) -> KnowledgeDoc:
        """Assign a document to an architecture node."""
        doc = await self.get(doc_id)

        # Verify the target node exists
        q = select(ArchitectureNode).where(ArchitectureNode.id == node_id)
        result = await self.db.execute(q)
        node = result.scalar_one_or_none()
        if node is None:
            raise NotFoundException(
                error_code=ErrorCode.ARCH_NOT_FOUND,
                message="Architecture node not found",
            )

        doc.node_id = node_id
        await self.db.flush()
        await self.db.refresh(doc)
        return doc

    async def diff_versions(self, doc_id: uuid.UUID, from_version: int, to_version: int) -> dict:
        """Compute line-level diff between two versions of a document."""
        ver_from = await self.get_version(doc_id, from_version)
        ver_to = await self.get_version(doc_id, to_version)

        from_lines = ver_from.content_md.splitlines(keepends=False)
        to_lines = ver_to.content_md.splitlines(keepends=False)

        diff_lines = []
        added = 0
        removed = 0
        unchanged = 0

        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
            None, from_lines, to_lines
        ).get_opcodes():
            if tag == "equal":
                for line in from_lines[i1:i2]:
                    diff_lines.append({"type": "context", "content": line})
                    unchanged += 1
            elif tag == "replace":
                for line in from_lines[i1:i2]:
                    diff_lines.append({"type": "removed", "content": line})
                    removed += 1
                for line in to_lines[j1:j2]:
                    diff_lines.append({"type": "added", "content": line})
                    added += 1
            elif tag == "delete":
                for line in from_lines[i1:i2]:
                    diff_lines.append({"type": "removed", "content": line})
                    removed += 1
            elif tag == "insert":
                for line in to_lines[j1:j2]:
                    diff_lines.append({"type": "added", "content": line})
                    added += 1

        return {
            "doc_id": doc_id,
            "from_version": from_version,
            "to_version": to_version,
            "from_change_reason": ver_from.change_reason,
            "to_change_reason": ver_to.change_reason,
            "diff_lines": diff_lines,
            "stats": {"added": added, "removed": removed, "unchanged": unchanged},
        }

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
