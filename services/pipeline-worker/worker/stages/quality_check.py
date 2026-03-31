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
    config: dict | None = None,
) -> dict:
    """Run quality checks on generated documents.

    Performs basic quality validation:
    - Content length check
    - Title presence check
    - Empty content detection

    Config params (via pipeline_stage_config):
    - min_content_length: int (default 50)
    - require_title: bool (default True)

    Returns:
        {"passed": [doc_id, ...], "flagged": [{"doc_id": ..., "issues": [...]}, ...]}
    """
    cfg = config or {}
    min_length = cfg.get("min_content_length", MIN_CONTENT_LENGTH)
    require_title = cfg.get("require_title", True)

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
        elif len(version.content_md.strip()) < min_length:
            issues.append(f"文档内容过短（{len(version.content_md.strip())}字符，最少{min_length}）")

        if require_title and (not doc.title or doc.title.strip() == ""):
            issues.append("文档缺少标题")

        if issues:
            flagged.append({"doc_id": str(doc_id), "issues": issues})
        else:
            passed.append(str(doc_id))

    return {"passed": passed, "flagged": flagged}
