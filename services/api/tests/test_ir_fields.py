"""Unit tests for IR fields on AssetChunk model (v0.49.1)."""

from shared_models.asset import AssetChunk


class TestIRFields:
    """Verify AssetChunk has all 5 IR fields."""

    def test_model_has_ir_fields(self):
        """AC: AssetChunk model includes 5 new IR fields."""
        chunk = AssetChunk.__table__
        column_names = {c.name for c in chunk.columns}

        assert "original_format" in column_names
        assert "structure_type" in column_names
        assert "extraction_confidence" in column_names
        assert "semantic_boundaries" in column_names
        assert "language" in column_names

    def test_ir_fields_are_nullable(self):
        """AC: All IR fields are nullable (backward compatible)."""
        chunk = AssetChunk.__table__
        for field_name in ["original_format", "structure_type", "extraction_confidence",
                           "semantic_boundaries", "language"]:
            col = chunk.c[field_name]
            assert col.nullable is True, f"{field_name} should be nullable"

    def test_can_create_chunk_without_ir_fields(self):
        """AC: Old chunks without IR fields work (all None)."""
        import uuid
        chunk = AssetChunk(
            asset_id=uuid.uuid4(),
            chunk_index=0,
            content_text="test content",
        )
        assert chunk.original_format is None
        assert chunk.structure_type is None
        assert chunk.extraction_confidence is None
        assert chunk.semantic_boundaries is None
        assert chunk.language is None

    def test_can_create_chunk_with_ir_fields(self):
        """AC: New chunks can set IR field values."""
        import uuid
        chunk = AssetChunk(
            asset_id=uuid.uuid4(),
            chunk_index=0,
            content_text="test content",
            original_format="text",
            structure_type="paragraph",
            extraction_confidence=0.95,
            semantic_boundaries={"start_page": 1},
            language="zh",
        )
        assert chunk.original_format == "text"
        assert chunk.structure_type == "paragraph"
        assert chunk.extraction_confidence == 0.95
        assert chunk.semantic_boundaries == {"start_page": 1}
        assert chunk.language == "zh"
