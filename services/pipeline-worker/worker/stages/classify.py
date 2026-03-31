"""Stage 3: Classify asset chunks into knowledge categories.

Calls AI Orchestrator via Celery to determine: new content, supplement, correction, or conflict.
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared_models import AssetChunk

from ..celery_app import celery_app

logger = logging.getLogger(__name__)


def classify_chunks(
    db: Session,
    project_id: uuid.UUID,
    asset_ids: list[uuid.UUID],
    config: dict | None = None,
) -> dict:
    """Classify all chunks from the given assets.

    Dispatches orchestrator.classify_incremental via Celery and waits for the result.

    Returns:
        {"new": [...], "supplement": [...], "correction": [...], "conflict": [...]}
        Each list contains chunk_id strings.
    """
    # Gather all chunks from the assets
    chunks = []
    for asset_id in asset_ids:
        rows = db.execute(
            select(AssetChunk).where(AssetChunk.asset_id == asset_id)
            .order_by(AssetChunk.chunk_index)
        ).scalars().all()
        for c in rows:
            chunks.append({"chunk_id": str(c.id), "content": c.content_text[:2000]})

    if not chunks:
        return {"new": [], "supplement": [], "correction": [], "conflict": [], "restructure": []}

    # Call AI Orchestrator via Celery
    try:
        result = celery_app.send_task(
            "orchestrator.classify_incremental",
            args=[
                str(project_id),
                str(uuid.uuid4()),  # Temporary job_id for the orchestrator sub-task
                [str(aid) for aid in asset_ids],
            ],
            queue="ai",
        )
        response = result.get(timeout=120)

        if response.get("status") == "success":
            return _build_classification_from_chunks(chunks, response)

        logger.warning("Classification returned non-success: %s", response)
    except Exception as e:
        logger.error("Classification via Celery failed: %s", e)

    # Fallback: treat all as new
    return {
        "new": [c["chunk_id"] for c in chunks],
        "supplement": [],
        "correction": [],
        "conflict": [],
        "restructure": [],
    }


def _build_classification_from_chunks(chunks: list[dict], response: dict) -> dict:
    """Build classification result mapping chunk_ids to categories based on orchestrator counts."""
    new_count = response.get("new", 0)
    supplement_count = response.get("supplement", 0)
    correction_count = response.get("correction", 0)
    conflict_count = response.get("conflict", 0)
    restructure_count = response.get("restructure", 0)

    total = new_count + supplement_count + correction_count + conflict_count + restructure_count
    if total == 0:
        return {"new": [c["chunk_id"] for c in chunks], "supplement": [], "correction": [], "conflict": [], "restructure": []}

    result: dict[str, list[str]] = {"new": [], "supplement": [], "correction": [], "conflict": [], "restructure": []}
    idx = 0
    for category, count in [("new", new_count), ("supplement", supplement_count),
                             ("correction", correction_count), ("conflict", conflict_count),
                             ("restructure", restructure_count)]:
        for _ in range(count):
            if idx < len(chunks):
                result[category].append(chunks[idx]["chunk_id"])
                idx += 1

    # Any remaining chunks go to 'new'
    while idx < len(chunks):
        result["new"].append(chunks[idx]["chunk_id"])
        idx += 1

    return result
