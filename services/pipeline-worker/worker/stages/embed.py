"""Stage 8: Generate embeddings for newly created documents.

Calls AI Orchestrator to produce vector embeddings for semantic search.
"""

import logging
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from shared_models import DocEmbedding, KnowledgeDoc, KnowledgeDocVersion

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "text-embedding-3-small"


def generate_embeddings(
    db: Session,
    doc_ids: list[uuid.UUID],
    orchestrator_url: str,
) -> int:
    """Generate embeddings for the given documents.

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

        try:
            resp = httpx.post(
                f"{orchestrator_url}/embed",
                json={"text": text[:8000]},
                timeout=30,
            )
            resp.raise_for_status()
            embedding = resp.json().get("embedding", [])
        except Exception as e:
            logger.warning("Embedding failed for doc %s: %s", doc_id, e)
            continue

        if not embedding:
            continue

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
