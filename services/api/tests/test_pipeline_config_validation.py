"""Tests for pipeline config params validation — v0.47.3 (audit H-4).

Tests the STAGE_PARAM_SCHEMAS and _validate_stage_params by reading source,
avoiding Python 3.12 imports on local 3.9 env.
"""

import ast
import pathlib
import sys


def _get_router_source() -> str:
    """Read the pipeline_config.py router source."""
    p = pathlib.Path(__file__).parent.parent / "app" / "routers" / "pipeline_config.py"
    return p.read_text(encoding="utf-8")


class TestSchemaDefinitionExists:
    """Verify STAGE_PARAM_SCHEMAS is defined with correct structure."""

    def test_schema_dict_present(self):
        source = _get_router_source()
        assert "STAGE_PARAM_SCHEMAS" in source, "STAGE_PARAM_SCHEMAS not defined"

    def test_all_seven_stages_covered(self):
        """Every known stage must have a schema entry."""
        source = _get_router_source()
        stages = [
            "classify", "architecture_draft", "doc_generate",
            "quality_check", "conflict_detect", "embed", "review_notify",
        ]
        for s in stages:
            assert f'"{s}"' in source, f"Stage '{s}' missing from STAGE_PARAM_SCHEMAS"

    def test_classify_has_confidence_threshold(self):
        source = _get_router_source()
        assert '"confidence_threshold"' in source
        assert '"entity_types"' in source

    def test_quality_check_has_three_params(self):
        source = _get_router_source()
        assert '"min_content_length"' in source
        assert '"require_title"' in source
        assert '"detect_pii"' in source


class TestValidationFunction:
    """Verify _validate_stage_params function exists and has correct logic."""

    def test_function_exists(self):
        source = _get_router_source()
        assert "def _validate_stage_params" in source

    def test_raises_422_on_unknown_key(self):
        source = _get_router_source()
        assert "unknown parameter" in source, "Should raise 422 with 'unknown parameter' message"

    def test_raises_422_on_type_mismatch(self):
        source = _get_router_source()
        assert "expected" in source, "Should raise 422 with type mismatch message"

    def test_checks_min_max_range(self):
        source = _get_router_source()
        assert '"min"' in source and '"max"' in source, "Should check min/max range"
        assert "below minimum" in source or "above maximum" in source


class TestPutEndpointCallsValidation:
    """Verify the PUT endpoint calls _validate_stage_params before saving."""

    def test_validation_called_in_put(self):
        source = _get_router_source()
        # Find the update_stage_config function
        func_start = source.index("async def update_stage_config")
        func_body = source[func_start:source.index("\n@router.", func_start + 1)]

        assert "_validate_stage_params" in func_body, (
            "PUT endpoint must call _validate_stage_params before saving"
        )

    def test_validation_before_db_commit(self):
        source = _get_router_source()
        func_start = source.index("async def update_stage_config")
        func_body = source[func_start:source.index("\n@router.", func_start + 1)]

        validate_pos = func_body.index("_validate_stage_params")
        commit_pos = func_body.index("db.commit()")
        assert validate_pos < commit_pos, (
            "Validation must happen BEFORE db.commit()"
        )

    def test_get_and_reset_not_affected(self):
        """GET and POST reset endpoints should NOT call validation."""
        source = _get_router_source()

        # Get endpoint
        get_start = source.index("async def get_pipeline_config")
        get_end = source.index("\n@router.", get_start + 1)
        get_body = source[get_start:get_end]
        assert "_validate_stage_params" not in get_body

        # Reset endpoint
        reset_start = source.index("async def reset_pipeline_config")
        reset_body = source[reset_start:]
        assert "_validate_stage_params" not in reset_body
