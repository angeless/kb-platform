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
from datetime import datetime, timezone

import redis
from sqlalchemy import select

from shared_config.settings import get_settings
from shared_models import Job
from shared_models.database import sync_session_factory
from shared_models.pipeline_stage_config import PipelineStageConfig
from shared_models.pipeline_stage_log import PipelineStageLog
from shared_schemas.pipeline_stage_config import DEFAULT_STAGE_PARAMS

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


def _log_stage_start(db, job_id: uuid.UUID, stage: str) -> PipelineStageLog:
    """Create a PipelineStageLog record with status='running'."""
    log = PipelineStageLog(
        job_id=job_id,
        stage_name=stage,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(log)
    db.commit()
    return log


def _log_stage_end(db, log: PipelineStageLog, status: str, token_usage: dict | None = None, error_message: str | None = None) -> None:
    """Update a PipelineStageLog record with final status."""
    log.status = status
    log.finished_at = datetime.now(timezone.utc)
    if token_usage:
        log.token_usage = token_usage
    if error_message:
        log.error_message = error_message
    db.commit()


def _log_stage_skip(db, job_id: uuid.UUID, stage: str) -> None:
    """Create a PipelineStageLog record for a skipped stage."""
    log = PipelineStageLog(
        job_id=job_id,
        stage_name=stage,
        status="skipped",
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
    )
    db.add(log)
    db.commit()


@celery_app.task(bind=True, name="pipeline.run_pipeline", max_retries=3, default_retry_delay=60)
def run_pipeline(self, project_id: str, job_id: str, asset_ids: list[str], user_id: str) -> dict:
    """Execute the full knowledge processing pipeline (stages 3-9).

    Called after ingestion-worker completes stages 1-2 (parsing).
    All AI Orchestrator calls are dispatched via Celery send_task (not HTTP).
    """
    pid = uuid.UUID(project_id)
    jid = uuid.UUID(job_id)
    uid = uuid.UUID(user_id)
    aids = [uuid.UUID(a) for a in asset_ids]

    db = sync_session_factory()
    current_stage = ""

    try:
        # M-10 idempotency: skip if job already completed/failed
        job = db.execute(select(Job).where(Job.id == jid)).scalar_one_or_none()
        if job and job.status in ("completed", "failed"):
            logger.warning("Pipeline job %s already %s, skipping", job_id, job.status)
            db.close()
            return {"status": "skipped", "reason": f"Job already {job.status}"}

        # Update job status
        if job:
            job.status = "running"
            db.commit()

        # Load per-project pipeline stage config (v0.46.2)
        stage_configs: dict[str, dict] = {}
        stage_enabled: dict[str, bool] = {}
        stage_order: dict[str, int] = {}
        stage_conditions: dict[str, dict | None] = {}
        config_rows = db.execute(
            select(PipelineStageConfig).where(PipelineStageConfig.project_id == pid)
        ).scalars().all()
        for row in config_rows:
            stage_configs[row.stage_name] = row.params
            stage_enabled[row.stage_name] = row.enabled
            stage_order[row.stage_name] = row.execution_order
            stage_conditions[row.stage_name] = row.condition

        # Reorder stages by execution_order if any non-zero order configured (v0.52.4)
        if any(v != 0 for v in stage_order.values()):
            ordered = sorted(
                STAGES,
                key=lambda s: stage_order.get(s, STAGES.index(s) * 10),
            )
        else:
            ordered = list(STAGES)

        # Track which stages actually ran (for condition evaluation)
        completed_stages: set[str] = set()

        def _is_enabled(stage: str) -> bool:
            return stage_enabled.get(stage, True)

        def _get_config(stage: str) -> dict:
            return stage_configs.get(stage, DEFAULT_STAGE_PARAMS.get(stage, {}))

        def _evaluate_condition(stage: str, context: dict) -> bool:
            """Evaluate stage condition JSONB. Returns True if stage should run.

            Supported conditions (v0.52.4 — Gap-4 fix):
              {"requires_stage": "classify"}  — skip if that stage didn't complete
              {"min_chunks": 5}               — skip if fewer chunks ingested
            """
            cond = stage_conditions.get(stage)
            if not cond:
                return True
            req = cond.get("requires_stage")
            if req and req not in completed_stages:
                logger.info("Stage %s skipped: requires_stage '%s' not completed", stage, req)
                return False
            min_c = cond.get("min_chunks")
            if min_c and context.get("chunk_count", 0) < min_c:
                logger.info("Stage %s skipped: min_chunks=%d, actual=%d", stage, min_c, context.get("chunk_count", 0))
                return False
            return True

        # Condition evaluation context (v0.52.4)
        cond_ctx = {"chunk_count": len(aids)}
        logger.info("Pipeline stage order: %s", ordered)

        # --- Stage 3: Classify ---
        current_stage = "classify"
        if not _is_enabled(current_stage) or not _evaluate_condition(current_stage, cond_ctx):
            logger.info("Stage 3 classify: SKIPPED by config/condition")
            _publish_event(pid, jid, current_stage, "skipped")
            _log_stage_skip(db, jid, current_stage)
            classification = {"new": [], "supplement": [], "correction": [], "conflict": []}
        else:
            _publish_event(pid, jid, current_stage, "running")
            stage_log = _log_stage_start(db, jid, current_stage)
            classification = classify_chunks(db, pid, aids, config=_get_config(current_stage))
            _log_stage_end(db, stage_log, "completed")
            _publish_event(pid, jid, current_stage, "completed")
            completed_stages.add(current_stage)
            logger.info("Stage 3 classify: new=%d, supplement=%d, correction=%d, conflict=%d",
                         len(classification.get("new", [])),
                         len(classification.get("supplement", [])),
                         len(classification.get("correction", [])),
                         len(classification.get("conflict", [])))

        # --- Stage 4: Architecture Draft ---
        current_stage = "architecture_draft"
        if not _is_enabled(current_stage) or not _evaluate_condition(current_stage, cond_ctx):
            logger.info("Stage 4 architecture_draft: SKIPPED by config/condition")
            _publish_event(pid, jid, current_stage, "skipped")
            _log_stage_skip(db, jid, current_stage)
            arch_id = None
        else:
            _publish_event(pid, jid, current_stage, "running")
            stage_log = _log_stage_start(db, jid, current_stage)
            arch_id = generate_architecture_draft(db, pid, classification, config=_get_config(current_stage))

            # Architecture quality gate
            from .stages.architecture_draft import validate_architecture
            arch_qc = validate_architecture(db, arch_id)
            if arch_qc["warnings"]:
                logger.warning("Architecture quality warnings: %s", arch_qc["warnings"])
            _log_stage_end(db, stage_log, "completed")
            _publish_event(pid, jid, current_stage, "completed")
            completed_stages.add(current_stage)

        # --- Stage 5: Document Generation ---
        current_stage = "doc_generate"
        if not _is_enabled(current_stage) or arch_id is None or not _evaluate_condition(current_stage, cond_ctx):
            logger.info("Stage 5 doc_generate: SKIPPED by config/condition (or no architecture)")
            _publish_event(pid, jid, current_stage, "skipped")
            _log_stage_skip(db, jid, current_stage)
            doc_ids = []
        else:
            _publish_event(pid, jid, current_stage, "running")
            stage_log = _log_stage_start(db, jid, current_stage)
            doc_ids = generate_documents(db, pid, arch_id, classification, uid, config=_get_config(current_stage))
            _log_stage_end(db, stage_log, "completed")
            _publish_event(pid, jid, current_stage, "completed")
            completed_stages.add(current_stage)
            logger.info("Stage 5: generated %d documents", len(doc_ids))

        # --- Stage 6: Quality Check ---
        current_stage = "quality_check"
        if not _is_enabled(current_stage) or not doc_ids or not _evaluate_condition(current_stage, cond_ctx):
            logger.info("Stage 6 quality_check: SKIPPED by config/condition (or no docs)")
            _publish_event(pid, jid, current_stage, "skipped")
            _log_stage_skip(db, jid, current_stage)
            qc_result = {"passed": [], "flagged": []}
        else:
            _publish_event(pid, jid, current_stage, "running")
            stage_log = _log_stage_start(db, jid, current_stage)
            qc_result = quality_check(db, doc_ids, config=_get_config(current_stage))
            _log_stage_end(db, stage_log, "completed")
            _publish_event(pid, jid, current_stage, "completed")
            completed_stages.add(current_stage)
            logger.info("Stage 6: %d passed, %d flagged",
                         len(qc_result.get("passed", [])),
                         len(qc_result.get("flagged", [])))

        # --- Stage 7: Conflict Detection ---
        current_stage = "conflict_detect"
        if not _is_enabled(current_stage) or not _evaluate_condition(current_stage, cond_ctx):
            logger.info("Stage 7 conflict_detect: SKIPPED by config/condition")
            _publish_event(pid, jid, current_stage, "skipped")
            _log_stage_skip(db, jid, current_stage)
            conflict_ids = []
        else:
            _publish_event(pid, jid, current_stage, "running")
            stage_log = _log_stage_start(db, jid, current_stage)
            conflict_ids = detect_conflicts(db, pid, classification, config=_get_config(current_stage))
            db.commit()
            _log_stage_end(db, stage_log, "completed")
            _publish_event(pid, jid, current_stage, "completed")
            completed_stages.add(current_stage)

        # --- Stage 8: Embedding ---
        current_stage = "embed"
        if not _is_enabled(current_stage) or not doc_ids or not _evaluate_condition(current_stage, cond_ctx):
            logger.info("Stage 8 embed: SKIPPED by config/condition (or no docs)")
            _publish_event(pid, jid, current_stage, "skipped")
            _log_stage_skip(db, jid, current_stage)
            embed_count = 0
        else:
            _publish_event(pid, jid, current_stage, "running")
            stage_log = _log_stage_start(db, jid, current_stage)
            embed_count = generate_embeddings(db, doc_ids, config=_get_config(current_stage))
            db.commit()
            _log_stage_end(db, stage_log, "completed")
            _publish_event(pid, jid, current_stage, "completed")
            completed_stages.add(current_stage)
            logger.info("Stage 8: embedded %d documents", embed_count)

        # --- Stage 9: Review Notification ---
        current_stage = "review_notify"
        if not _is_enabled(current_stage) or not _evaluate_condition(current_stage, cond_ctx):
            logger.info("Stage 9 review_notify: SKIPPED by config/condition")
            _publish_event(pid, jid, current_stage, "skipped")
            _log_stage_skip(db, jid, current_stage)
        else:
            _publish_event(pid, jid, current_stage, "running")
            stage_log = _log_stage_start(db, jid, current_stage)
            notify_review(db, pid, doc_ids, conflict_ids, config=_get_config(current_stage))
            _log_stage_end(db, stage_log, "completed")
            _publish_event(pid, jid, current_stage, "completed")
            completed_stages.add(current_stage)

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

        # Update job status and log stage failure in a new session to avoid stale state
        try:
            db.rollback()
            new_db = sync_session_factory()
            try:
                job = new_db.execute(select(Job).where(Job.id == jid)).scalar_one_or_none()
                if job:
                    job.status = "failed"
                    job.error_message = f"Stage '{current_stage}' failed: {exc}"

                # Log stage failure
                if current_stage:
                    fail_log = PipelineStageLog(
                        job_id=jid,
                        stage_name=current_stage,
                        status="failed",
                        started_at=datetime.now(timezone.utc),
                        finished_at=datetime.now(timezone.utc),
                        error_message=str(exc)[:2000],
                    )
                    new_db.add(fail_log)
                new_db.commit()
            finally:
                new_db.close()
        except Exception:
            pass

        _publish_event(pid, jid, current_stage, "failed")
        raise self.retry(exc=exc)

    finally:
        db.close()
