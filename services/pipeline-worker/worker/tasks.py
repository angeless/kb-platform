"""Pipeline worker tasks: 9-stage knowledge processing pipeline.

Stage 1-2: Handled by ingestion-worker (parse_asset)
Stage 3: Classify chunks (new/supplement/correction/conflict)
Stage 4: Generate/update architecture draft
Stage 5: Generate knowledge documents
Stage 6: Quality check
Stage 7: Detect conflicts
Stage 8: Generate embeddings
Stage 9: Notify reviewers
"""

import json
import logging
import uuid

import redis
from sqlalchemy import select

from shared_config.settings import get_settings
from shared_models import Job
from shared_models.database import sync_session_factory

from .celery_app import celery_app
from .stages import (
    classify_chunks,
    detect_conflicts,
    generate_architecture_draft,
    generate_documents,
    generate_embeddings,
    notify_review,
    quality_check,
)

logger = logging.getLogger(__name__)

STAGES = [
    "classify",
    "architecture_draft",
    "doc_generate",
    "quality_check",
    "conflict_detect",
    "embed",
    "review_notify",
]


def _publish_event(project_id: uuid.UUID, job_id: uuid.UUID, stage: str, status: str) -> None:
    """Publish pipeline stage progress via Redis."""
    try:
        settings = get_settings()
        r = redis.from_url(settings.redis_url)
        event = {
            "type": "pipeline_stage",
            "job_id": str(job_id),
            "stage": stage,
            "status": status,
            "stage_index": STAGES.index(stage) + 3,  # Stages 3-9
            "total_stages": 9,
        }
        r.publish(f"job_events:{project_id}", json.dumps(event))
    except Exception as e:
        logger.warning("Failed to publish stage event: %s", e)


@celery_app.task(bind=True, name="pipeline.run_pipeline", max_retries=3, default_retry_delay=60)
def run_pipeline(self, project_id: str, job_id: str, asset_ids: list[str], user_id: str) -> dict:
    """Execute the full knowledge processing pipeline (stages 3-9).

    Called after ingestion-worker completes stages 1-2 (parsing).
    """
    pid = uuid.UUID(project_id)
    jid = uuid.UUID(job_id)
    uid = uuid.UUID(user_id)
    aids = [uuid.UUID(a) for a in asset_ids]

    settings = get_settings()
    orchestrator_url = f"http://ai-orchestrator:{settings.app_port}"

    db = sync_session_factory()
    current_stage = ""

    try:
        # Update job status
        job = db.execute(select(Job).where(Job.id == jid)).scalar_one_or_none()
        if job:
            job.status = "running"
            db.commit()

        # --- Stage 3: Classify ---
        current_stage = "classify"
        _publish_event(pid, jid, current_stage, "running")
        classification = classify_chunks(db, pid, aids, orchestrator_url)
        _publish_event(pid, jid, current_stage, "completed")
        logger.info("Stage 3 classify: new=%d, supplement=%d, correction=%d, conflict=%d",
                     len(classification.get("new", [])),
                     len(classification.get("supplement", [])),
                     len(classification.get("correction", [])),
                     len(classification.get("conflict", [])))

        # --- Stage 4: Architecture Draft ---
        current_stage = "architecture_draft"
        _publish_event(pid, jid, current_stage, "running")
        arch_id = generate_architecture_draft(db, pid, classification, orchestrator_url)
        _publish_event(pid, jid, current_stage, "completed")

        # --- Stage 5: Document Generation ---
        current_stage = "doc_generate"
        _publish_event(pid, jid, current_stage, "running")
        doc_ids = generate_documents(db, pid, arch_id, classification, orchestrator_url, uid)
        _publish_event(pid, jid, current_stage, "completed")
        logger.info("Stage 5: generated %d documents", len(doc_ids))

        # --- Stage 6: Quality Check ---
        current_stage = "quality_check"
        _publish_event(pid, jid, current_stage, "running")
        qc_result = quality_check(db, doc_ids, orchestrator_url)
        _publish_event(pid, jid, current_stage, "completed")
        logger.info("Stage 6: %d passed, %d flagged",
                     len(qc_result.get("passed", [])),
                     len(qc_result.get("flagged", [])))

        # --- Stage 7: Conflict Detection ---
        current_stage = "conflict_detect"
        _publish_event(pid, jid, current_stage, "running")
        conflict_ids = detect_conflicts(db, pid, classification)
        db.commit()
        _publish_event(pid, jid, current_stage, "completed")

        # --- Stage 8: Embedding ---
        current_stage = "embed"
        _publish_event(pid, jid, current_stage, "running")
        embed_count = generate_embeddings(db, doc_ids, orchestrator_url)
        db.commit()
        _publish_event(pid, jid, current_stage, "completed")
        logger.info("Stage 8: embedded %d documents", embed_count)

        # --- Stage 9: Review Notification ---
        current_stage = "review_notify"
        _publish_event(pid, jid, current_stage, "running")
        notify_review(db, pid, doc_ids, conflict_ids)
        _publish_event(pid, jid, current_stage, "completed")

        # Mark job completed
        if job:
            job.status = "completed"
            db.commit()

        return {
            "status": "completed",
            "documents_created": len(doc_ids),
            "conflicts_detected": len(conflict_ids),
            "embeddings_created": embed_count,
        }

    except Exception as exc:
        logger.error("Pipeline failed at stage '%s': %s", current_stage, exc)

        # Update job status
        try:
            if job:
                job.status = "failed"
                job.error_message = f"Stage '{current_stage}' failed: {exc}"
                db.commit()
        except Exception:
            db.rollback()

        _publish_event(pid, jid, current_stage, "failed")
        raise self.retry(exc=exc)

    finally:
        db.close()
