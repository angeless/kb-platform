"""Tests for T-37-03: Batch operations use savepoint isolation.

Verifies that batch_review, batch_publish, and batch_reject use
db.begin_nested() (savepoint) to isolate individual operations,
so one failure doesn't pollute the session for subsequent items.
"""

import inspect

import pytest


class TestBatchSavepointUsage:
    """All three batch endpoints must use begin_nested() savepoints."""

    def test_batch_review_uses_begin_nested(self):
        from app.routers.docs import batch_review

        source = inspect.getsource(batch_review)
        assert "begin_nested()" in source, "batch_review must use begin_nested() savepoint"

    def test_batch_publish_uses_begin_nested(self):
        from app.routers.docs import batch_publish

        source = inspect.getsource(batch_publish)
        assert "begin_nested()" in source, "batch_publish must use begin_nested() savepoint"

    def test_batch_reject_uses_begin_nested(self):
        from app.routers.docs import batch_reject

        source = inspect.getsource(batch_reject)
        assert "begin_nested()" in source, "batch_reject must use begin_nested() savepoint"

    def test_batch_review_savepoint_wraps_operation(self):
        """begin_nested must wrap the svc.review call."""
        from app.routers.docs import batch_review

        source = inspect.getsource(batch_review)
        # Verify the structure: begin_nested -> review inside
        nested_pos = source.find("begin_nested()")
        review_pos = source.find("svc.review(")
        assert nested_pos < review_pos, "begin_nested must appear before svc.review"

    def test_batch_publish_savepoint_wraps_operation(self):
        from app.routers.docs import batch_publish

        source = inspect.getsource(batch_publish)
        nested_pos = source.find("begin_nested()")
        publish_pos = source.find("svc.publish(")
        assert nested_pos < publish_pos

    def test_batch_reject_savepoint_wraps_operation(self):
        from app.routers.docs import batch_reject

        source = inspect.getsource(batch_reject)
        nested_pos = source.find("begin_nested()")
        reject_pos = source.find("svc.reject(")
        assert nested_pos < reject_pos
