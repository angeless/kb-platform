"""Celery tasks for the ingestion worker."""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from shared_config.settings import get_settings
from shared_models import Asset, AssetChunk, Job

from .celery_app import celery_app
from .parsers import get_parser

logger = logging.getLogger(__name__)

settings = get_settings()

# Sync engine for Celery tasks (Celery workers are sync)
_sync_engine = create_engine(settings.database_url_sync, pool_size=5, max_overflow=5)


def _get_sync_session() -> Session:
    return Session(_sync_engine)


def _download_from_storage(object_path: str) -> bytes:
    """Download file from MinIO/S3. Returns file bytes."""
    import boto3

    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )
    response = client.get_object(Bucket=settings.s3_bucket, Key=object_path)
    return response["Body"].read()


@celery_app.task(bind=True, name="ingestion.parse_asset")
def parse_asset(self, asset_id: str, job_id: str) -> dict:
    """Parse an asset: download from storage, run parser, write chunks to DB.

    This task is idempotent: re-running it will delete old chunks first.
    """
    asset_uuid = uuid.UUID(asset_id)
    job_uuid = uuid.UUID(job_id)

    with _get_sync_session() as session:
        # Load asset
        asset = session.execute(
            select(Asset).where(Asset.id == asset_uuid)
        ).scalar_one_or_none()

        if asset is None:
            logger.error("Asset %s not found", asset_id)
            _update_job_failed(session, job_uuid, f"Asset {asset_id} not found")
            return {"status": "error", "message": "Asset not found"}

        # Update status to parsing
        asset.parse_status = "parsing"
        _update_job_running(session, job_uuid)
        session.commit()

        try:
            # Get parser for this asset type
            parser = get_parser(asset.asset_type)
            if parser is None:
                asset.parse_status = "unsupported"
                _update_job_completed(session, job_uuid)
                session.commit()
                logger.info("No parser for asset_type %s — marked unsupported", asset.asset_type)
                return {"status": "unsupported", "asset_type": asset.asset_type}

            # Download file content from MinIO
            try:
                file_content = _download_from_storage(asset.object_path)
            except Exception as e:
                raise RuntimeError(f"Failed to download from storage: {e!s}")

            # Parse
            chunks = parser.parse(file_content, asset.filename)

            # Idempotent: delete old chunks first
            session.execute(
                delete(AssetChunk).where(AssetChunk.asset_id == asset_uuid)
            )

            # Write new chunks
            for i, chunk_data in enumerate(chunks):
                chunk = AssetChunk(
                    id=uuid.uuid4(),
                    asset_id=asset_uuid,
                    chunk_index=i,
                    content_text=chunk_data["content_text"],
                    page_or_timestamp=chunk_data.get("page_or_timestamp"),
                    tags=chunk_data.get("tags"),
                )
                session.add(chunk)

            # Update asset status
            asset.parse_status = "parsed"
            _update_job_completed(session, job_uuid)
            session.commit()

            logger.info("Parsed asset %s: %d chunks created", asset_id, len(chunks))

            # Trigger pipeline worker to process parsed chunks
            _trigger_pipeline(session, asset, job_uuid)

            return {"status": "success", "chunks": len(chunks)}

        except Exception as e:
            session.rollback()
            session.close()

            # Use a fresh session for error status updates (T-33-10 fix)
            with _get_sync_session() as err_session:
                asset = err_session.execute(
                    select(Asset).where(Asset.id == asset_uuid)
                ).scalar_one_or_none()
                if asset:
                    asset.parse_status = "failed"
                _update_job_failed(err_session, job_uuid, str(e))
                err_session.commit()

            logger.error("Failed to parse asset %s: %s", asset_id, e)
            return {"status": "error", "message": str(e)}


def _trigger_pipeline(session: Session, asset: Asset, ingest_job_id: uuid.UUID) -> None:
    """After ingestion completes, create and dispatch a pipeline job."""
    try:
        # Create a pipeline job
        pipeline_job = Job(
            id=uuid.uuid4(),
            project_id=asset.project_id,
            job_type="kb_generate",
            status="pending",
            retry_count=0,
            created_by=asset.uploaded_by,
        )
        session.add(pipeline_job)
        session.commit()

        # Dispatch to pipeline-worker
        celery_app.send_task(
            "pipeline.run_pipeline",
            args=[
                str(asset.project_id),
                str(pipeline_job.id),
                [str(asset.id)],
                str(asset.uploaded_by),
            ],
            queue="pipeline",
        )
        logger.info(
            "Triggered pipeline for asset %s, pipeline job %s",
            asset.id, pipeline_job.id,
        )
    except Exception as e:
        logger.warning("Failed to trigger pipeline after ingestion: %s", e)


def _publish_job_event(job: Job, error_message: str | None = None) -> None:
    """Publish job status change to Redis for WebSocket subscribers."""
    try:
        import redis
        r = redis.from_url(settings.redis_url)
        import json
        event = json.dumps({
            "event": "job_status_changed",
            "job_id": str(job.id),
            "project_id": str(job.project_id),
            "status": job.status,
            "job_type": job.job_type,
            "error_message": error_message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        r.publish(f"job_events:{job.project_id}", event)
        r.close()
    except Exception as e:
        logger.debug("Failed to publish job event: %s", e)


def _update_job_running(session: Session, job_id: uuid.UUID) -> None:
    job = session.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
    if job:
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        _publish_job_event(job)


def _update_job_completed(session: Session, job_id: uuid.UUID) -> None:
    job = session.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
    if job:
        job.status = "completed"
        job.finished_at = datetime.now(timezone.utc)
        _publish_job_event(job)


def _update_job_failed(session: Session, job_id: uuid.UUID, error_message: str) -> None:
    job = session.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
    if job:
        job.status = "failed"
        job.error_message = error_message
        job.finished_at = datetime.now(timezone.utc)
        _publish_job_event(job, error_message)
