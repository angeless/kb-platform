"""Structured JSON logging configuration.

Configures Python's logging to output JSON-formatted log lines to stdout,
suitable for log aggregation systems (ELK, Loki, CloudWatch, etc.).
"""

import logging
import sys

from pythonjsonlogger.json import JsonFormatter as _JsonFormatter

from shared_config.settings import get_settings


class KBJsonFormatter(_JsonFormatter):
    """Custom JSON formatter that adds standard fields to every log record."""

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_record["user_id"] = record.user_id


def setup_logging() -> None:
    """Configure root logger with JSON formatter."""
    settings = get_settings()

    formatter = KBJsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
