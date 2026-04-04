"""Unit tests for ReviewTask model and state machine (v0.50.1)."""

from shared_models.review_task import ReviewTask, validate_transition, VALID_TRANSITIONS


class TestReviewTaskStateMachine:
    """State machine transition validation."""

    def test_pending_to_assigned(self):
        assert validate_transition("pending", "assigned") is True

    def test_assigned_to_approved(self):
        assert validate_transition("assigned", "approved") is True

    def test_assigned_to_rejected(self):
        assert validate_transition("assigned", "rejected") is True

    def test_rejected_to_resubmitted(self):
        assert validate_transition("rejected", "resubmitted") is True

    def test_resubmitted_to_assigned(self):
        assert validate_transition("resubmitted", "assigned") is True

    def test_invalid_approved_to_pending(self):
        assert validate_transition("approved", "pending") is False

    def test_invalid_pending_to_approved(self):
        assert validate_transition("pending", "approved") is False

    def test_invalid_assigned_to_pending(self):
        assert validate_transition("assigned", "pending") is False

    def test_approved_is_terminal(self):
        assert VALID_TRANSITIONS["approved"] == set()


class TestReviewTaskModel:
    """Model field presence."""

    def test_has_required_columns(self):
        cols = {c.name for c in ReviewTask.__table__.columns}
        expected = {"id", "project_id", "doc_id", "reviewer_id", "status",
                    "assigned_at", "reviewed_at", "review_note", "created_by",
                    "created_at", "updated_at"}
        assert expected.issubset(cols)

    def test_status_column_has_default(self):
        col = ReviewTask.__table__.c["status"]
        assert col.default is not None or col.server_default is not None

    def test_reviewer_nullable(self):
        col = ReviewTask.__table__.c["reviewer_id"]
        assert col.nullable is True
