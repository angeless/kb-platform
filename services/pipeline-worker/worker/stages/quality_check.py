"""Stage 6: Quality check generated documents.

Performs basic quality validation on generated documents.
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared_models import KnowledgeDoc, KnowledgeDocVersion

logger = logging.getLogger(__name__)

# Minimum content length to pass quality check
MIN_CONTENT_LENGTH = 50


def quality_check(
    db: Session,
    doc_ids: list[uuid.UUID],
) -> dict:
    """Run quality checks on generated documents.

    Performs basic quality validation:
    - Content length check
    - Title presence check
    - Empty content detection

    Returns:
        {"passed": [doc_id, ...], "flagged": [{"doc_id": ..., "issues": [...]}, ...]}
    """
    passed = []
    flagged = []

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

        issues = []
        if version is None:
            issues.append("文档缺少版本内容")
        elif len(version.content_md.strip()) < MIN_CONTENT_LENGTH:
            issues.append(f"文档内容过短（{len(version.content_md.strip())}字符，最少{MIN_CONTENT_LENGTH}）")

        if not doc.title or doc.title.strip() == "":
            issues.append("文档缺少标题")

        if issues:
            flagged.append({"doc_id": str(doc_id), "issues": issues})
        else:
            passed.append(str(doc_id))

    return {"passed": passed, "flagged": flagged}
