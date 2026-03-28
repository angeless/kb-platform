"""Tests for pipeline worker stages."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from worker.stages.classify import classify_chunks
from worker.stages.conflict_detect import detect_conflicts
from worker.stages.quality_check import quality_check
from worker.stages.embed import generate_embeddings, _hash_embedding


class TestClassifyChunks:
    """Tests for the classification stage."""

    def test_empty_assets_returns_empty(self):
        db = MagicMock()
        db.execute.return_value.scalars.return_value.all.return_value = []
        result = classify_chunks(db, uuid.uuid4(), [])
        assert result == {"new": [], "supplement": [], "correction": [], "conflict": [], "restructure": []}

    @patch("worker.stages.classify.celery_app")
    def test_calls_orchestrator_via_celery(self, mock_celery):
        db = MagicMock()
        chunk = MagicMock()
        chunk.id = uuid.uuid4()
        chunk.content_text = "Test content"
        db.execute.return_value.scalars.return_value.all.return_value = [chunk]

        # Mock the Celery send_task → result.get() chain
        mock_result = MagicMock()
        mock_result.get.return_value = {
            "status": "success", "new": 1, "supplement": 0, "correction": 0, "conflict": 0,
        }
        mock_celery.send_task.return_value = mock_result

        result = classify_chunks(db, uuid.uuid4(), [uuid.uuid4()])
        assert str(chunk.id) in result["new"]
        mock_celery.send_task.assert_called_once()

    @patch("worker.stages.classify.celery_app")
    def test_fallback_on_failure(self, mock_celery):
        db = MagicMock()
        chunk = MagicMock()
        chunk.id = uuid.uuid4()
        chunk.content_text = "Test"
        db.execute.return_value.scalars.return_value.all.return_value = [chunk]

        mock_celery.send_task.side_effect = Exception("timeout")

        result = classify_chunks(db, uuid.uuid4(), [uuid.uuid4()])
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
    """Tests for quality check stage (local validation)."""

    def test_doc_passes_quality_check(self):
        db = MagicMock()
        doc_id = uuid.uuid4()
        doc = MagicMock()
        doc.current_version = 1
        doc.title = "Test Document"
        version = MagicMock()
        version.content_md = "A" * 100  # Exceeds MIN_CONTENT_LENGTH
        db.execute.return_value.scalar_one_or_none.side_effect = [doc, version]

        result = quality_check(db, [doc_id])
        assert str(doc_id) in result["passed"]

    def test_short_content_flagged(self):
        db = MagicMock()
        doc_id = uuid.uuid4()
        doc = MagicMock()
        doc.current_version = 1
        doc.title = "Test"
        version = MagicMock()
        version.content_md = "Short"  # Below MIN_CONTENT_LENGTH
        db.execute.return_value.scalar_one_or_none.side_effect = [doc, version]

        result = quality_check(db, [doc_id])
        assert len(result["flagged"]) == 1
        assert "过短" in result["flagged"][0]["issues"][0]

    def test_missing_title_flagged(self):
        db = MagicMock()
        doc_id = uuid.uuid4()
        doc = MagicMock()
        doc.current_version = 1
        doc.title = ""
        version = MagicMock()
        version.content_md = "A" * 100
        db.execute.return_value.scalar_one_or_none.side_effect = [doc, version]

        result = quality_check(db, [doc_id])
        assert len(result["flagged"]) == 1


class TestHashEmbedding:
    """Tests for the hash-based pseudo-embedding."""

    def test_deterministic(self):
        e1 = _hash_embedding("test text")
        e2 = _hash_embedding("test text")
        assert e1 == e2

    def test_correct_dimensions(self):
        e = _hash_embedding("test text", dimensions=128)
        assert len(e) == 128

    def test_values_in_range(self):
        e = _hash_embedding("test text")
        assert all(-1 <= v <= 1 for v in e)

    def test_different_texts_different_embeddings(self):
        e1 = _hash_embedding("text A")
        e2 = _hash_embedding("text B")
        assert e1 != e2


class TestPipelineStages:
    """Integration-level test for stage ordering."""

    def test_stages_list(self):
        from worker.tasks import STAGES
        assert len(STAGES) == 7  # Stages 3-9 (1-2 handled by ingestion-worker)
        assert STAGES[0] == "classify"
        assert STAGES[-1] == "review_notify"
