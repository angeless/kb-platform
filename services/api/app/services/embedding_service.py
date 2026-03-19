"""Embedding service: generate embeddings and perform semantic search."""

from __future__ import annotations

import logging
import math
import uuid
from typing import Callable

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import ErrorCode, NotFoundException
from shared_models import DocEmbedding, KnowledgeDoc, KnowledgeDocVersion, Project

logger = logging.getLogger(__name__)

# Default embedding dimensions (OpenAI text-embedding-3-small)
DEFAULT_DIMENSIONS = 1536
DEFAULT_MODEL = "text-embedding-3-small"


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def _default_embed_fn(text: str) -> list[float]:
    """Call OpenAI embeddings API. Falls back to zero vector on failure."""
    try:
        import httpx
        from shared_config.settings import get_settings
        settings = get_settings()

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={"input": text[:8000], "model": DEFAULT_MODEL},
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

        text = f"{doc.title}\n\n{ver.content_md}" if ver else doc.title
        embedding = await self.embed_fn(text)

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
        self.db.add(record)
        await self.db.flush()
        return record

    async def semantic_search(
        self,
        project_id: uuid.UUID,
        query: str,
        top_k: int = 10,
    ) -> list[dict]:
        """Search documents by semantic similarity."""
        await self._verify_project(project_id)

        # Generate query embedding
        query_embedding = await self.embed_fn(query)

        # Load all embeddings for this project
        emb_q = select(DocEmbedding).where(DocEmbedding.project_id == project_id)
        embeddings = (await self.db.execute(emb_q)).scalars().all()

        if not embeddings:
            return []

        # Compute similarities
        scored = []
        for emb in embeddings:
            score = cosine_similarity(query_embedding, emb.embedding)
            scored.append((emb.doc_id, score))

        # Sort by score descending, take top_k
        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:top_k]

        # Load doc metadata
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
