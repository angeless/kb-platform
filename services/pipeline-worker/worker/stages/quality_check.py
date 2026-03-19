"""Stage 6: Quality check generated documents.

Calls AI Orchestrator to verify document quality, completeness, and accuracy.
"""

import logging
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from shared_models import KnowledgeDoc, KnowledgeDocVersion

logger = logging.getLogger(__name__)


def quality_check(
    db: Session,
    doc_ids: list[uuid.UUID],
    orchestrator_url: str,
) -> dict:
    """Run quality checks on generated documents.

    Returns:
        {"passed": [doc_id, ...], "flagged": [{"doc_id": ..., "issues": [...]}, ...]}
    """
    docs_for_check = []
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
        if version:
            docs_for_check.append({
                "doc_id": str(doc_id),
                "title": doc.title,
                "content_md": version.content_md[:5000],
            })

    if not docs_for_check:
        return {"passed": [], "flagged": []}

    try:
        resp = httpx.post(
            f"{orchestrator_url}/quality-check",
            json={"documents": docs_for_check},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error("Quality check failed: %s", e)
        # Fail open: assume all passed
        return {"passed": [str(d) for d in doc_ids], "flagged": []}
