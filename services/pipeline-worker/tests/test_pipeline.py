"""Tests for pipeline worker stages."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from worker.stages.classify import classify_chunks
from worker.stages.conflict_detect import detect_conflicts
from worker.stages.quality_check import quality_check


class TestClassifyChunks:
    """Tests for the classification stage."""

    def test_empty_assets_returns_empty(self):
        db = MagicMock()
        db.execute.return_value.scalars.return_value.all.return_value = []
        result = classify_chunks(db, uuid.uuid4(), [], "http://fake")
        assert result == {"new": [], "supplement": [], "correction": [], "conflict": []}

    @patch("worker.stages.classify.httpx.post")
    def test_calls_orchestrator(self, mock_post):
        db = MagicMock()
        chunk = MagicMock()
        chunk.id = uuid.uuid4()
        chunk.content_text = "Test content"
        db.execute.return_value.scalars.return_value.all.return_value = [chunk]

        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = {
            "new": [str(chunk.id)], "supplement": [], "correction": [], "conflict": [],
        }

        result = classify_chunks(db, uuid.uuid4(), [uuid.uuid4()], "http://fake")
        assert str(chunk.id) in result["new"]
        mock_post.assert_called_once()

    @patch("worker.stages.classify.httpx.post", side_effect=Exception("timeout"))
    def test_fallback_on_failure(self, mock_post):
        db = MagicMock()
        chunk = MagicMock()
        chunk.id = uuid.uuid4()
        chunk.content_text = "Test"
        db.execute.return_value.scalars.return_value.all.return_value = [chunk]

        result = classify_chunks(db, uuid.uuid4(), [uuid.uuid4()], "http://fake")
        assert str(chunk.id) in result["new"]


class TestConflictDetect:
    """Tests for conflict detection stage."""

    def test_no_conflicts(self):
        db = MagicMock()
        result = detect_conflicts(db, uuid.uuid4(), {"conflict": []})
        assert result == []

    def test_creates_conflict_records(self):
        db = MagicMock()
        classification = {"conflict": [str(uuid.uuid4()), str(uuid.uuid4())]}
        result = detect_conflicts(db, uuid.uuid4(), classification)
        assert len(result) == 2
        assert db.add.call_count == 2


class TestQualityCheck:
    """Tests for quality check stage."""

    @patch("worker.stages.quality_check.httpx.post")
    def test_returns_results(self, mock_post):
        db = MagicMock()
        doc_id = uuid.uuid4()
        doc = MagicMock()
        doc.current_version = 1
        doc.title = "Test"
        version = MagicMock()
        version.content_md = "# Test content"
        db.execute.return_value.scalar_one_or_none.side_effect = [doc, version]

        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = {
            "passed": [str(doc_id)], "flagged": [],
        }

        result = quality_check(db, [doc_id], "http://fake")
        assert str(doc_id) in result["passed"]

    @patch("worker.stages.quality_check.httpx.post", side_effect=Exception("timeout"))
    def test_fail_open(self, mock_post):
        db = MagicMock()
        doc_id = uuid.uuid4()
        doc = MagicMock()
        doc.current_version = 1
        doc.title = "Test"
        version = MagicMock()
        version.content_md = "content"
        db.execute.return_value.scalar_one_or_none.side_effect = [doc, version]

        result = quality_check(db, [doc_id], "http://fake")
        assert str(doc_id) in result["passed"]


class TestPipelineStages:
    """Integration-level test for stage ordering."""

    def test_stages_list(self):
        from worker.tasks import STAGES
        assert len(STAGES) == 7  # Stages 3-9 (1-2 handled by ingestion-worker)
        assert STAGES[0] == "classify"
        assert STAGES[-1] == "review_notify"
