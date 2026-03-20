"""Search service: full-text search across knowledge documents."""

import re
import uuid

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import ErrorCode, NotFoundException
from shared_models import KnowledgeDoc, KnowledgeDocVersion

from . import TenantService


# Max chars for snippet context on each side of the match
SNIPPET_CONTEXT = 100


def _extract_snippet(text_str: str, query: str, context: int = SNIPPET_CONTEXT) -> str:
    """Extract a snippet around the first occurrence of query in text."""
    lower_text = text_str.lower()
    lower_query = query.lower()
    pos = lower_text.find(lower_query)
    if pos == -1:
        # Fallback: return beginning of text
        return text_str[:context * 2] + ("..." if len(text_str) > context * 2 else "")

    start = max(0, pos - context)
    end = min(len(text_str), pos + len(query) + context)

    snippet = ""
    if start > 0:
        snippet += "..."
    snippet += text_str[start:end]
    if end < len(text_str):
        snippet += "..."
    return snippet


# Characters that are tsquery operators and must be stripped from user input
_TSQUERY_OPERATOR_RE = re.compile(r"[&|!():<>*]")


def _sanitize_tsquery_input(query: str) -> str:
    """Sanitize user input for safe use with plainto_tsquery.

    - Removes tsquery operator characters: & | ! ( ) : < > *
    - Strips leading/trailing whitespace
    - Collapses multiple spaces into one
    """
    cleaned = _TSQUERY_OPERATOR_RE.sub(" ", query)
    cleaned = " ".join(cleaned.split())  # collapse whitespace
    return cleaned


def _build_tsquery(query: str) -> str:
    """Sanitize user input and return cleaned text for plainto_tsquery.

    Returns empty string if input contains only operators/whitespace.
    The returned text is passed to plainto_tsquery('simple', ...) which
    handles tokenization and AND-joining automatically.
    """
    return _sanitize_tsquery_input(query)


class SearchService(TenantService):
    """Full-text search across knowledge documents, scoped to tenant."""

    async def text_search(
        self,
        project_id: uuid.UUID,
        query: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """Search knowledge documents using tsvector + GIN index with ILIKE fallback.

        Returns (results, total_count).
        """
        await self._verify_project(project_id)

        tsquery_str = _build_tsquery(query)

        # Try tsvector search first (fast path with GIN index)
        if tsquery_str:
            results, total = await self._tsvector_search(
                project_id, query, tsquery_str, page, page_size,
            )
            if total > 0:
                return results, total

        # Fallback to ILIKE when tsvector has no matches
        return await self._ilike_search(project_id, query, page, page_size)

    async def _tsvector_search(
        self,
        project_id: uuid.UUID,
        query: str,
        tsquery_str: str,
        page: int,
        page_size: int,
    ) -> tuple[list[dict], int]:
        """Search using PostgreSQL tsvector + GIN index."""
        # Use raw SQL for tsvector operations (ts_rank, @@, plainto_tsquery)
        count_stmt = text("""
            SELECT count(*)
            FROM knowledge_doc d
            JOIN knowledge_doc_version v ON v.doc_id = d.id AND v.version = d.current_version
            WHERE d.project_id = :project_id
              AND (
                  d.search_vector @@ plainto_tsquery('simple', :tsquery)
                  OR v.search_vector @@ plainto_tsquery('simple', :tsquery)
              )
        """)
        total = (await self.db.execute(
            count_stmt, {"project_id": project_id, "tsquery": tsquery_str},
        )).scalar_one()

        if total == 0:
            return [], 0

        search_stmt = text("""
            SELECT d.id AS doc_id,
                   d.title,
                   d.doc_type,
                   d.status,
                   d.node_id,
                   d.created_at,
                   v.content_md,
                   v.version,
                   GREATEST(
                       ts_rank(coalesce(d.search_vector, ''::tsvector), plainto_tsquery('simple', :tsquery)),
                       ts_rank(coalesce(v.search_vector, ''::tsvector), plainto_tsquery('simple', :tsquery))
                   ) AS rank
            FROM knowledge_doc d
            JOIN knowledge_doc_version v ON v.doc_id = d.id AND v.version = d.current_version
            WHERE d.project_id = :project_id
              AND (
                  d.search_vector @@ plainto_tsquery('simple', :tsquery)
                  OR v.search_vector @@ plainto_tsquery('simple', :tsquery)
              )
            ORDER BY rank DESC, d.created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        rows = (await self.db.execute(search_stmt, {
            "project_id": project_id,
            "tsquery": tsquery_str,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        })).all()

        results = []
        for row in rows:
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

    async def _ilike_search(
        self,
        project_id: uuid.UUID,
        query: str,
        page: int,
        page_size: int,
    ) -> tuple[list[dict], int]:
        """Fallback ILIKE search when tsvector has no matches."""
        pattern = f"%{query}%"

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

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = base.order_by(KnowledgeDoc.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
        rows = (await self.db.execute(q)).all()

        results = []
        for row in rows:
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
