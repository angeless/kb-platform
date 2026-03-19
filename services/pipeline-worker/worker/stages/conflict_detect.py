"""Stage 7: Detect conflicts between new content and existing knowledge.

Creates ConflictRecord entries for content flagged as contradictory.
"""

import logging
import uuid

from sqlalchemy.orm import Session

from shared_models import ConflictRecord

logger = logging.getLogger(__name__)


def detect_conflicts(
    db: Session,
    project_id: uuid.UUID,
    classification: dict,
) -> list[uuid.UUID]:
    """Create conflict records for chunks classified as conflicting.

    Returns:
        List of created ConflictRecord IDs.
    """
    conflict_chunk_ids = classification.get("conflict", [])
    if not conflict_chunk_ids:
        return []

    conflict_ids = []
    for chunk_id_str in conflict_chunk_ids:
        record = ConflictRecord(
            id=uuid.uuid4(),
            project_id=project_id,
            description=f"内容冲突检测：片段 {chunk_id_str} 与现有知识存在矛盾，需人工审核",
            status="open",
        )
        db.add(record)
        conflict_ids.append(record.id)

    db.flush()
    logger.info("Created %d conflict records for project %s", len(conflict_ids), project_id)
    return conflict_ids
