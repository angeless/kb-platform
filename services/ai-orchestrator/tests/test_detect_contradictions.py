"""Tests for detect_contradictions task — v0.47.1 draft exclusion logic.

Validates the query filter by inspecting the source code directly,
avoiding the need for a live DB or Celery worker.
"""

import pathlib


def _read_task_source() -> str:
    """Read detect_contradictions source from tasks.py."""
    tasks_path = pathlib.Path(__file__).parent.parent / "orchestrator" / "tasks.py"
    return tasks_path.read_text(encoding="utf-8")


class TestContradictionDraftFilter:
    """Verify that detect_contradictions excludes draft documents (v0.47.1, audit C-3)."""

    def test_no_published_status_in_query(self):
        """'published' is not a valid KnowledgeDoc status — must not appear in the query."""
        source = _read_task_source()
        # Find the detect_contradictions function body
        func_start = source.index("def detect_contradictions")
        # Find the next top-level function or EOF
        next_func = source.find("\n@celery_app.task", func_start + 1)
        func_body = source[func_start:next_func] if next_func != -1 else source[func_start:]

        # The query should NOT reference 'published' status
        assert '["published"' not in func_body, (
            "Query references non-existent 'published' status"
        )
        assert '"published"' not in func_body.split('"""')[2] if func_body.count('"""') >= 3 else True, (
            "Query references non-existent 'published' status outside docstring"
        )

    def test_draft_excluded_via_not_equal(self):
        """Query should use `status != 'draft'` to exclude draft documents."""
        source = _read_task_source()
        func_start = source.index("def detect_contradictions")
        next_func = source.find("\n@celery_app.task", func_start + 1)
        func_body = source[func_start:next_func] if next_func != -1 else source[func_start:]

        assert '!= "draft"' in func_body or "!= 'draft'" in func_body, (
            "Expected `status != 'draft'` filter not found in detect_contradictions"
        )

    def test_no_closed_status_list_in_query(self):
        """Should use open filter (!=) not closed list (in_) for future-proofing."""
        source = _read_task_source()
        func_start = source.index("def detect_contradictions")
        next_func = source.find("\n@celery_app.task", func_start + 1)
        func_body = source[func_start:next_func] if next_func != -1 else source[func_start:]

        # Extract just the query portion (between "select" and "scalars")
        query_section = func_body[func_body.index("select(KnowledgeDoc)"):func_body.index(".scalars()")]
        assert "status.in_" not in query_section, (
            "Should use != 'draft' (open filter) not status.in_([...]) (closed filter)"
        )

    def test_docstring_mentions_non_draft(self):
        """Docstring should document the draft exclusion behavior."""
        source = _read_task_source()
        func_start = source.index("def detect_contradictions")
        # Get docstring (between first pair of triple quotes)
        doc_start = source.index('"""', func_start) + 3
        doc_end = source.index('"""', doc_start)
        docstring = source[doc_start:doc_end].lower()

        assert "non-draft" in docstring or "draft" in docstring, (
            "Docstring should mention draft exclusion"
        )
