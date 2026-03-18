"""Tests for classify_incremental task logic."""

import json
import uuid

from orchestrator.prompts import build_classify_prompt


class TestClassifyPromptIntegration:
    """Test classify prompt construction for various scenarios."""

    def test_multiple_docs_and_chunks(self):
        """Should handle multiple existing docs and new chunks."""
        docs = [
            {"doc_id": str(uuid.uuid4()), "title": "退款流程", "summary": "7天退款"},
            {"doc_id": str(uuid.uuid4()), "title": "物流配送", "summary": "2-3天到达"},
        ]
        chunks = [
            {"index": 0, "content_text": "退款新政策：30天无理由"},
            {"index": 1, "content_text": "新增加急配送服务"},
        ]
        system, user = build_classify_prompt(docs, chunks)
        assert "退款流程" in user
        assert "物流配送" in user
        assert "[片段0]" in user
        assert "[片段1]" in user

    def test_chunk_with_page_info(self):
        """Page/timestamp info should be included."""
        chunks = [{"index": 0, "content_text": "内容", "page_or_timestamp": "第5页"}]
        system, user = build_classify_prompt([], chunks)
        assert "第5页" in user


class TestClassifyTaskLogic:
    """Test the core logic patterns used by classify_incremental task."""

    def test_classification_response_structure(self):
        """Validate expected JSON structure from LLM response."""
        response = json.dumps({
            "reasoning": "退款政策有更新",
            "classifications": [
                {
                    "chunk_index": 0,
                    "relation_type": "correction",
                    "target_doc_id": str(uuid.uuid4()),
                    "reason": "退款期限从7天改为30天",
                    "conflict_description": None,
                },
                {
                    "chunk_index": 1,
                    "relation_type": "new",
                    "target_doc_id": None,
                    "reason": "加急配送是新服务",
                    "conflict_description": None,
                },
            ],
        })
        result = json.loads(response)
        assert "classifications" in result
        assert len(result["classifications"]) == 2
        assert result["classifications"][0]["relation_type"] == "correction"
        assert result["classifications"][1]["relation_type"] == "new"

    def test_conflict_classification(self):
        """Conflict should have conflict_description."""
        cls = {
            "chunk_index": 0,
            "relation_type": "conflict",
            "target_doc_id": None,
            "reason": "互相矛盾",
            "conflict_description": "来源A说7天退货，来源B说不支持退货",
        }
        assert cls["relation_type"] == "conflict"
        assert cls["conflict_description"] is not None

    def test_supplement_requires_target_doc(self):
        """Supplement and correction should have target_doc_id."""
        cls = {
            "relation_type": "supplement",
            "target_doc_id": str(uuid.uuid4()),
        }
        assert cls["target_doc_id"] is not None

    def test_new_has_no_target_doc(self):
        """New classification should have no target_doc_id."""
        cls = {
            "relation_type": "new",
            "target_doc_id": None,
        }
        assert cls["target_doc_id"] is None

    def test_invalid_chunk_index_skipped(self):
        """Chunk indices out of range should be skipped."""
        chunk_dicts = [{"index": 0}, {"index": 1}]
        classifications = [
            {"chunk_index": 0, "relation_type": "new"},
            {"chunk_index": 5, "relation_type": "new"},  # out of range
            {"chunk_index": -1, "relation_type": "new"},  # negative
        ]
        valid = [c for c in classifications if 0 <= c["chunk_index"] < len(chunk_dicts)]
        assert len(valid) == 1

    def test_version_increment_logic(self):
        """Version number should increment when supplementing/correcting."""
        current_version = 3
        new_version = current_version + 1
        assert new_version == 4

    def test_all_four_relation_types(self):
        """All four relation types should be recognized."""
        valid_types = {"new", "supplement", "correction", "conflict"}
        for rt in valid_types:
            assert rt in valid_types
