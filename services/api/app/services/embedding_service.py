"""Embedding service: generate embeddings and perform semantic search."""

from __future__ import annotations

import logging
import uuid
from typing import Callable

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import ErrorCode, NotFoundException
from shared_models import DocEmbedding, KnowledgeDoc, KnowledgeDocVersion, Project

logger = logging.getLogger(__name__)

# Default embedding dimensions (OpenAI text-embedding-3-small)
DEFAULT_DIMENSIONS = 1536
DEFAULT_MODEL = "text-embedding-3-small"


async def _default_embed_fn(text_input: str) -> list[float]:
    """Call OpenAI embeddings API. Falls back to zero vector on failure."""
    try:
        import httpx
        from shared_config.settings import get_settings
        settings = get_settings()

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={"input": text_input[:8000], "model": DEFAULT_MODEL},
            )
            resp.raise_for_status()
            return resp.json()["data"][0]["embedding"]
    except Exception as e:
        logger.warning("Embedding API call failed: %s", e)
        return [0.0] * DEFAULT_DIMENSIONS


class EmbeddingService:
    """Generate document embeddings and perform semantic search."""

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        embed_fn: Callable | None = None,
    ) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.embed_fn = embed_fn or _default_embed_fn

    async def _verify_project(self, project_id: uuid.UUID) -> Project:
        q = select(Project).where(
            Project.id == project_id,
            Project.tenant_id == self.tenant_id,
            Project.status != "deleted",
        )
        result = await self.db.execute(q)
        project = result.scalar_one_or_none()
        if project is None:
            raise NotFoundException(error_code=ErrorCode.PROJECT_NOT_FOUND, message="项目不存在")
        return project

    async def embed_doc(self, doc_id: uuid.UUID) -> DocEmbedding:
        """Generate and store embedding for a document's latest version."""
        q = select(KnowledgeDoc).where(KnowledgeDoc.id == doc_id)
        doc = (await self.db.execute(q)).scalar_one_or_none()
        if doc is None:
            raise NotFoundException(error_code=ErrorCode.DOC_NOT_FOUND, message="文档不存在")
        await self._verify_project(doc.project_id)

        # Get latest version content
        ver_q = select(KnowledgeDocVersion).where(
            KnowledgeDocVersion.doc_id == doc_id,
        ).order_by(KnowledgeDocVersion.version.desc()).limit(1)
        ver = (await self.db.execute(ver_q)).scalar_one_or_none()

        content = f"{doc.title}\n\n{ver.content_md}" if ver else doc.title
        embedding = await self.embed_fn(content)

        # Upsert: delete existing then insert
        await self.db.execute(
            delete(DocEmbedding).where(DocEmbedding.doc_id == doc_id)
        )
        record = DocEmbedding(
            id=uuid.uuid4(),
            doc_id=doc_id,
            project_id=doc.project_id,
            version=doc.current_version,
            embedding=embedding,
            model_name=DEFAULT_MODEL,
            dimensions=len(embedding),
        )
        # Write to pgvector column as well (dual-write during migration)
        if hasattr(DocEmbedding, "embedding_vec") and DocEmbedding.embedding_vec is not None:
            record.embedding_vec = embedding
        self.db.add(record)
        await self.db.flush()
        return record

    async def semantic_search(
        self,
        project_id: uuid.UUID,
        query: str,
        top_k: int = 10,
    ) -> list[dict]:
        """Search documents by semantic similarity using pgvector."""
        await self._verify_project(project_id)

        # Generate query embedding
        query_embedding = await self.embed_fn(query)

        # Use pgvector cosine distance operator for fast vector search
        vec_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
        stmt = text("""
            SELECT e.doc_id,
                   d.title,
                   d.doc_type,
                   d.status,
                   (e.embedding_vec <=> :query_vec::vector) AS distance
            FROM doc_embedding e
            JOIN knowledge_doc d ON d.id = e.doc_id
            WHERE e.project_id = :project_id
              AND e.embedding_vec IS NOT NULL
            ORDER BY e.embedding_vec <=> :query_vec::vector
            LIMIT :top_k
        """)
        result = await self.db.execute(
            stmt,
            {"project_id": project_id, "query_vec": vec_str, "top_k": top_k},
        )
        rows = result.all()

        if rows:
            return [
                {
                    "doc_id": row.doc_id,
                    "title": row.title,
                    "doc_type": row.doc_type,
                    "status": row.status,
                    "score": round(1.0 - row.distance, 4),  # cosine similarity = 1 - distance
                }
                for row in rows
            ]

        # Fallback: if no pgvector data, use JSONB-based search
        return await self._semantic_search_jsonb_fallback(project_id, query_embedding, top_k)

    async def _semantic_search_jsonb_fallback(
        self,
        project_id: uuid.UUID,
        query_embedding: list[float],
        top_k: int,
    ) -> list[dict]:
        """Legacy JSONB-based semantic search (used when embedding_vec is null)."""
        import math

        emb_q = select(DocEmbedding).where(DocEmbedding.project_id == project_id)
        embeddings = (await self.db.execute(emb_q)).scalars().all()

        if not embeddings:
            return []

        scored = []
        for emb in embeddings:
            vec = emb.embedding
            dot = sum(x * y for x, y in zip(query_embedding, vec))
            norm_a = math.sqrt(sum(x * x for x in query_embedding))
            norm_b = math.sqrt(sum(x * x for x in vec))
            score = dot / (norm_a * norm_b) if norm_a and norm_b else 0.0
            scored.append((emb.doc_id, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:top_k]

        results = []
        for doc_id, score in top:
            doc_q = select(KnowledgeDoc).where(KnowledgeDoc.id == doc_id)
            doc = (await self.db.execute(doc_q)).scalar_one_or_none()
            if doc is None:
                continue
            results.append({
                "doc_id": doc.id,
                "title": doc.title,
                "doc_type": doc.doc_type,
                "status": doc.status,
                "score": round(score, 4),
            })

        return results
