"""Celery application configuration for the pipeline worker."""

from celery import Celery

from shared_config.settings import get_settings
import shared_config.dlq  # noqa: F401 — registers task_failure signal handler

settings = get_settings()

celery_app = Celery(
    "pipeline-worker",
    broker=settings.celery_broker_url,
    backend=settings.redis_url,
    include=["worker.tasks"],
)

celery_app.conf.update(
    broker_transport_options=settings.celery_broker_transport_options,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=60,
    task_max_retries=3,
    task_reject_on_worker_lost=True,
    task_routes={
        "ingestion.*": {"queue": "ingestion"},
        "pipeline.*": {"queue": "pipeline"},
        "orchestrator.*": {"queue": "ai"},
    },
)
