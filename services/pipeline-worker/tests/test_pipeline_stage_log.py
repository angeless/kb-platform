"""Tests for v0.47.6 — Pipeline per-stage execution log.

Uses source inspection to verify:
1. PipelineStageLog model has all required fields
2. Migration creates correct table schema
3. tasks.py integrates stage logging for all 7 stages
4. Error handler logs failed stage
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _read(relpath: str) -> str:
    return (ROOT / relpath).read_text()


# --- Model tests ---

def test_model_has_all_required_fields():
    src = _read("packages/shared-models/shared_models/pipeline_stage_log.py")
    required = ["job_id", "stage_name", "status", "started_at", "finished_at", "token_usage", "error_message"]
    for field in required:
        assert f"{field}:" in src or f"{field} =" in src, f"Missing field: {field}"


def test_model_job_id_is_foreign_key():
    src = _read("packages/shared-models/shared_models/pipeline_stage_log.py")
    assert 'ForeignKey("job.id")' in src


def test_model_has_job_id_index():
    src = _read("packages/shared-models/shared_models/pipeline_stage_log.py")
    assert "ix_stage_log_job_id" in src


def test_model_exported_from_init():
    src = _read("packages/shared-models/shared_models/__init__.py")
    assert "PipelineStageLog" in src


# --- Migration tests ---

def test_migration_creates_table():
    src = _read("infra/sql/alembic/versions/t9h0i1j2k3l4_create_pipeline_stage_log.py")
    assert '"pipeline_stage_log"' in src
    assert "ix_stage_log_job_id" in src


def test_migration_has_all_columns():
    src = _read("infra/sql/alembic/versions/t9h0i1j2k3l4_create_pipeline_stage_log.py")
    for col in ["job_id", "stage_name", "status", "started_at", "finished_at", "token_usage", "error_message"]:
        assert f'"{col}"' in src, f"Migration missing column: {col}"


def test_migration_chain():
    src = _read("infra/sql/alembic/versions/t9h0i1j2k3l4_create_pipeline_stage_log.py")
    assert 'down_revision = "s8g9h0i1j2k3"' in src


# --- Integration tests (tasks.py) ---

def test_tasks_imports_pipeline_stage_log():
    src = _read("services/pipeline-worker/worker/tasks.py")
    assert "from shared_models.pipeline_stage_log import PipelineStageLog" in src


def test_tasks_has_log_helpers():
    src = _read("services/pipeline-worker/worker/tasks.py")
    assert "def _log_stage_start(" in src
    assert "def _log_stage_end(" in src
    assert "def _log_stage_skip(" in src


def test_all_stages_have_log_calls():
    src = _read("services/pipeline-worker/worker/tasks.py")
    stages = ["classify", "architecture_draft", "doc_generate", "quality_check", "conflict_detect", "embed", "review_notify"]
    for stage in stages:
        # Each stage should have either _log_stage_skip or _log_stage_start
        stage_section = src[src.index(f'current_stage = "{stage}"'):]
        next_stage_idx = len(stage_section)
        for s in stages:
            if s != stage:
                idx = stage_section.find(f'current_stage = "{s}"')
                if idx > 0:
                    next_stage_idx = min(next_stage_idx, idx)
        stage_section = stage_section[:next_stage_idx]
        has_skip = "_log_stage_skip(" in stage_section
        has_start = "_log_stage_start(" in stage_section
        assert has_skip and has_start, f"Stage '{stage}' missing log calls (skip={has_skip}, start={has_start})"


def test_error_handler_logs_failed_stage():
    src = _read("services/pipeline-worker/worker/tasks.py")
    error_section = src[src.index("except Exception as exc"):]
    assert "PipelineStageLog(" in error_section
    assert 'status="failed"' in error_section


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
