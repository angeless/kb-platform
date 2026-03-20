"""Dead letter queue handler for Celery workers.

When a task exhausts all retries, this module captures the failure details
and stores them in a Redis list (dlq:{queue_name}) for later inspection.
Each queue retains at most DLQ_MAX_SIZE entries (FIFO, oldest trimmed first).
"""

import json
import logging
from datetime import datetime, timezone

import redis
from celery.signals import task_failure

from shared_config.settings import get_settings

logger = logging.getLogger(__name__)

DLQ_MAX_SIZE = 1000


def _get_redis_client() -> redis.Redis:
    settings = get_settings()
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def _resolve_queue_name(task_name: str, default_queue: str) -> str:
    """Derive the queue name from the task name prefix.

    Task names follow the pattern ``<service>.<module>.<func>`` — the first
    segment (ingestion / pipeline / orchestrator) maps to the queue.
    """
    prefix = task_name.split(".")[0] if task_name else ""
    queue_map = {
        "ingestion": "ingestion",
        "pipeline": "pipeline",
        "orchestrator": "ai",
    }
    return queue_map.get(prefix, default_queue)


@task_failure.connect
def handle_task_failure(sender=None, task_id=None, args=None, kwargs=None,
                        exception=None, traceback=None, einfo=None, **kw):
    """Write failed task information to the dead-letter Redis list.

    This signal fires on *every* failure (including intermediate retries).
    We only record the failure when all retries have been exhausted — i.e.
    ``sender.request.retries >= sender.max_retries``.
    """
    # Only capture final failures (retries exhausted)
    request = sender.request if sender else None
    max_retries = getattr(sender, "max_retries", 0) or 0
    current_retries = request.retries if request else 0
    if current_retries < max_retries:
        return

    task_name = sender.name if sender else "unknown"
    queue_name = _resolve_queue_name(task_name, "default")
    dlq_key = f"dlq:{queue_name}"

    entry = {
        "task_id": task_id,
        "task_name": task_name,
        "args": _safe_serialize(args),
        "kwargs": _safe_serialize(kwargs),
        "exception": str(exception) if exception else None,
        "traceback": str(einfo) if einfo else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        client = _get_redis_client()
        client.lpush(dlq_key, json.dumps(entry, default=str))
        client.ltrim(dlq_key, 0, DLQ_MAX_SIZE - 1)
        logger.warning(
            "Task %s[%s] moved to dead-letter queue %s",
            task_name, task_id, dlq_key,
        )
    except Exception:
        # DLQ recording must never break the worker itself
        logger.exception("Failed to write to dead-letter queue %s", dlq_key)


def _safe_serialize(obj):
    """Return a JSON-safe representation, falling back to str()."""
    if obj is None:
        return None
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)
