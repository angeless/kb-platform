"""Stage 8: Generate embeddings for newly created documents.

Uses deterministic hash-based pseudo-embeddings as a placeholder.
Real semantic embeddings will be added in v0.34 (pgvector upgrade).
"""

import hashlib
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared_models import DocEmbedding, KnowledgeDoc, KnowledgeDocVersion

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "text-embedding-3-small"
FALLBACK_DIMENSIONS = 256


def generate_embeddings(
    db: Session,
    doc_ids: list[uuid.UUID],
    config: dict | None = None,
) -> int:
    """Generate embeddings for the given documents.

    Uses deterministic hash-based pseudo-embeddings that enable the pipeline
    to run end-to-end. Real embeddings will be added in v0.34.

    Returns:
        Number of embeddings created.
    """
    count = 0
    for doc_id in doc_ids:
        doc = db.execute(
            select(KnowledgeDoc).where(KnowledgeDoc.id == doc_id)
        ).scalar_one_or_none()
        if doc is None:
            continue

        version = db.execute(
            select(KnowledgeDocVersion).where(
                KnowledgeDocVersion.doc_id == doc_id,
                KnowledgeDocVersion.version == doc.current_version,
            )
        ).scalar_one_or_none()
        text = f"{doc.title}\n\n{version.content_md}" if version else doc.title

        embedding = _hash_embedding(text)

        # Upsert
        existing = db.execute(
            select(DocEmbedding).where(DocEmbedding.doc_id == doc_id)
        ).scalar_one_or_none()
        if existing:
            existing.embedding = embedding
            existing.version = doc.current_version
            existing.dimensions = len(embedding)
        else:
            record = DocEmbedding(
                id=uuid.uuid4(),
                doc_id=doc_id,
                project_id=doc.project_id,
                version=doc.current_version,
                embedding=embedding,
                model_name=DEFAULT_MODEL,
                dimensions=len(embedding),
            )
            db.add(record)

        count += 1

    db.flush()
    return count


def _hash_embedding(text: str, dimensions: int = FALLBACK_DIMENSIONS) -> list[float]:
    """Generate a deterministic pseudo-embedding from text using SHA-256.

    NOT a real semantic embedding — placeholder for end-to-end pipeline flow.
    """
    result = []
    chunk = text[:8000].encode("utf-8")
    for i in range(dimensions):
        h = hashlib.sha256(chunk + i.to_bytes(4, "big")).digest()
        val = int.from_bytes(h[:4], "big") / (2**32) * 2 - 1
        result.append(round(val, 6))
    return result
