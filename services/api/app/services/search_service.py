"""Search service: full-text search across knowledge documents."""

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import ErrorCode, NotFoundException
from shared_models import KnowledgeDoc, KnowledgeDocVersion, Project


# Max chars for snippet context on each side of the match
SNIPPET_CONTEXT = 100


def _extract_snippet(text: str, query: str, context: int = SNIPPET_CONTEXT) -> str:
    """Extract a snippet around the first occurrence of query in text."""
    lower_text = text.lower()
    lower_query = query.lower()
    pos = lower_text.find(lower_query)
    if pos == -1:
        # Fallback: return beginning of text
        return text[:context * 2] + ("..." if len(text) > context * 2 else "")

    start = max(0, pos - context)
    end = min(len(text), pos + len(query) + context)

    snippet = ""
    if start > 0:
        snippet += "..."
    snippet += text[start:end]
    if end < len(text):
        snippet += "..."
    return snippet


class SearchService:
    """Full-text search across knowledge documents, scoped to tenant."""

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
                message="项目不存在",
            )
        return project

    async def text_search(
        self,
        project_id: uuid.UUID,
        query: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """Search knowledge documents by text matching in title and content.

        Returns (results, total_count).
        Each result is a dict with doc metadata + snippet.
        """
        await self._verify_project(project_id)

        pattern = f"%{query}%"

        # Join KnowledgeDoc with its latest version to search content
        base = (
            select(
                KnowledgeDoc.id.label("doc_id"),
                KnowledgeDoc.title,
                KnowledgeDoc.doc_type,
                KnowledgeDoc.status,
                KnowledgeDoc.node_id,
                KnowledgeDoc.created_at,
                KnowledgeDocVersion.content_md,
                KnowledgeDocVersion.version,
            )
            .join(
                KnowledgeDocVersion,
                KnowledgeDocVersion.doc_id == KnowledgeDoc.id,
            )
            .where(
                KnowledgeDoc.project_id == project_id,
                KnowledgeDocVersion.version == KnowledgeDoc.current_version,
                or_(
                    KnowledgeDoc.title.ilike(pattern),
                    KnowledgeDocVersion.content_md.ilike(pattern),
                ),
            )
        )

        # Count total matches
        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        # Paginated results
        q = base.order_by(KnowledgeDoc.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
        rows = (await self.db.execute(q)).all()

        results = []
        for row in rows:
            # Determine which field matched and extract snippet
            title_matches = query.lower() in row.title.lower()
            content_md = row.content_md or ""

            if title_matches:
                matched_field = "title"
                snippet = row.title
            else:
                matched_field = "content_md"
                snippet = _extract_snippet(content_md, query)

            results.append({
                "doc_id": row.doc_id,
                "title": row.title,
                "doc_type": row.doc_type,
                "status": row.status,
                "node_id": row.node_id,
                "snippet": snippet,
                "matched_field": matched_field,
                "version": row.version,
                "created_at": row.created_at,
            })

        return results, total
