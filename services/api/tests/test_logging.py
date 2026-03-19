"""Tests for structured JSON logging configuration."""

import json
import logging
from io import StringIO

from app.logging_config import KBJsonFormatter, setup_logging


class TestJsonLogging:
    def test_json_formatter_produces_valid_json(self):
        """Log output should be valid JSON."""
        formatter = KBJsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
        handler = logging.StreamHandler(stream := StringIO())
        handler.setFormatter(formatter)

        logger = logging.getLogger("test.json_format")
        logger.handlers = [handler]
        logger.setLevel(logging.DEBUG)

        logger.info("Test message")
        output = stream.getvalue().strip()
        data = json.loads(output)

        assert data["message"] == "Test message"
        assert data["level"] == "INFO"
        assert data["logger"] == "test.json_format"

    def test_json_formatter_includes_extra_fields(self):
        """Extra fields like request_id should appear in JSON output."""
        formatter = KBJsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
        handler = logging.StreamHandler(stream := StringIO())
        handler.setFormatter(formatter)

        logger = logging.getLogger("test.extra_fields")
        logger.handlers = [handler]
        logger.setLevel(logging.DEBUG)

        logger.info("Request processed", extra={"request_id": "abc-123", "user_id": "user-456"})
        output = stream.getvalue().strip()
        data = json.loads(output)

        assert data["request_id"] == "abc-123"
        assert data["user_id"] == "user-456"

    def test_setup_logging_configures_root_logger(self):
        """setup_logging should configure the root logger with JSON handler."""
        setup_logging()
        root = logging.getLogger()
        assert len(root.handlers) >= 1
        handler = root.handlers[0]
        assert isinstance(handler.formatter, KBJsonFormatter)

    def test_error_level_includes_exc_info(self):
        """Error logs with exc_info should include exception details."""
        formatter = KBJsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
        handler = logging.StreamHandler(stream := StringIO())
        handler.setFormatter(formatter)

        logger = logging.getLogger("test.error_log")
        logger.handlers = [handler]
        logger.setLevel(logging.DEBUG)

        try:
            raise ValueError("test error")
        except ValueError:
            logger.exception("Something failed")

        output = stream.getvalue().strip()
        data = json.loads(output)
        assert data["level"] == "ERROR"
        assert "Something failed" in data["message"]
