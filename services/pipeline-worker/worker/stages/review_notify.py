"""Stage 9: Notify reviewers about pending documents.

Publishes review-ready event via Redis Pub/Sub for WebSocket subscribers.
"""

import json
import logging
import uuid

import redis
from sqlalchemy.orm import Session

from shared_config.settings import get_settings

logger = logging.getLogger(__name__)


def notify_review(
    db: Session,
    project_id: uuid.UUID,
    doc_ids: list[uuid.UUID],
    conflict_ids: list[uuid.UUID],
    config: dict | None = None,
) -> None:
    """Publish notification about documents ready for review."""
    settings = get_settings()

    event = {
        "type": "pipeline_complete",
        "project_id": str(project_id),
        "docs_pending_review": len(doc_ids),
        "conflicts_detected": len(conflict_ids),
        "doc_ids": [str(d) for d in doc_ids],
    }

    try:
        r = redis.from_url(settings.redis_url)
        channel = f"job_events:{project_id}"
        r.publish(channel, json.dumps(event))
        logger.info(
            "Pipeline complete for project %s: %d docs, %d conflicts",
            project_id, len(doc_ids), len(conflict_ids),
        )
    except Exception as e:
        logger.warning("Failed to publish review notification: %s", e)
