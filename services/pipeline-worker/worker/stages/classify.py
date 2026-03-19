"""Stage 3: Classify asset chunks into knowledge categories.

Calls AI Orchestrator to determine: new content, supplement, correction, or conflict.
"""

import logging
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from shared_models import AssetChunk

logger = logging.getLogger(__name__)


def classify_chunks(
    db: Session,
    project_id: uuid.UUID,
    asset_ids: list[uuid.UUID],
    orchestrator_url: str,
) -> dict:
    """Classify all chunks from the given assets.

    Returns:
        {"new": [...], "supplement": [...], "correction": [...], "conflict": [...]}
        Each list contains chunk_id UUIDs.
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
        return {"new": [], "supplement": [], "correction": [], "conflict": []}

    # Call AI Orchestrator for classification
    try:
        resp = httpx.post(
            f"{orchestrator_url}/classify",
            json={"project_id": str(project_id), "chunks": chunks},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error("Classification failed: %s", e)
        # Fallback: treat all as new
        return {
            "new": [c["chunk_id"] for c in chunks],
            "supplement": [],
            "correction": [],
            "conflict": [],
        }
