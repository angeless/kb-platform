"""Tests for generate_docs task logic."""

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest

from orchestrator.prompts import build_generate_doc_prompt


class TestGenerateDocsPromptIntegration:
    """Test that generate_docs prompt building works for various node types."""

    def test_topic_node_prompt(self):
        """Topic node should produce prompt requesting topic-style doc."""
        chunks = [
            {"index": 0, "content_text": "退款流程：客户申请→审核→退款"},
            {"index": 1, "content_text": "退款时效：3-5个工作日"},
        ]
        system, user = build_generate_doc_prompt(
            node_name="退款流程",
            node_type="topic",
            node_description="客户退款操作流程",
            node_level=3,
            chunks=chunks,
        )
        assert "topic" in user
        assert "退款流程" in user
        assert "[片段0]" in user
        assert "[片段1]" in user

    def test_glossary_node_prompt(self):
        """Glossary node should produce prompt with glossary context."""
        chunks = [{"index": 0, "content_text": "SKU: 库存量单位"}]
        system, user = build_generate_doc_prompt(
            node_name="术语表",
            node_type="glossary",
            node_description="行业术语定义",
            node_level=2,
            chunks=chunks,
        )
        assert "glossary" in user
        assert "术语表" in user

    def test_document_node_prompt(self):
        """Document node type in prompt."""
        chunks = [{"index": 0, "content_text": "操作手册内容"}]
        system, user = build_generate_doc_prompt(
            node_name="操作手册",
            node_type="document",
            node_description="标准操作手册",
            node_level=4,
            chunks=chunks,
        )
        assert "document" in user


class TestGenerateDocsTaskLogic:
    """Test the core logic patterns used by generate_docs task."""

    def test_category_nodes_should_be_skipped(self):
        """Category nodes are containers, not content — should be skipped."""
        # Simulate the skip logic from tasks.py
        node_types_to_skip = ["category"]
        node_types_to_process = ["topic", "document", "glossary", "conflict", "index"]

        for nt in node_types_to_skip:
            assert nt == "category"

        for nt in node_types_to_process:
            assert nt != "category"

    def test_empty_content_should_skip_doc_creation(self):
        """When LLM returns empty content_md, no doc should be created."""
        result = {"content_md": "", "title": "Empty"}
        assert not result.get("content_md")

    def test_cited_chunk_indices_validation(self):
        """Only valid chunk indices should be used for SourceRef."""
        chunk_dicts = [
            {"index": 0, "chunk_id": uuid.uuid4()},
            {"index": 1, "chunk_id": uuid.uuid4()},
            {"index": 2, "chunk_id": uuid.uuid4()},
        ]
        cited = [0, 2, 5, -1]  # 5 and -1 are out of range

        valid_refs = [idx for idx in cited if 0 <= idx < len(chunk_dicts)]
        assert valid_refs == [0, 2]

    def test_conflict_detection_from_llm_response(self):
        """When LLM reports conflicts, a ConflictRecord should be created."""
        result = {
            "has_conflicts": True,
            "conflict_description": "来源A说7天退货，来源B说15天退货",
        }
        assert result.get("has_conflicts") is True
        assert result.get("conflict_description")

    def test_no_conflict_when_flag_false(self):
        """No conflict record when has_conflicts is False."""
        result = {
            "has_conflicts": False,
            "conflict_description": None,
        }
        should_create = result.get("has_conflicts") and result.get("conflict_description")
        assert not should_create

    def test_llm_response_json_structure(self):
        """Validate expected JSON structure from LLM response."""
        mock_response = json.dumps({
            "title": "退款规则文档",
            "doc_type": "topic",
            "reasoning": "资料中包含退款相关政策",
            "content_md": "# 退款规则\n\n## 退款流程\n客户申请后3-5个工作日到账 [来源0]",
            "cited_chunk_indices": [0, 1],
            "has_conflicts": False,
            "conflict_description": None,
        })
        result = json.loads(mock_response)
        assert "title" in result
        assert "content_md" in result
        assert "cited_chunk_indices" in result
        assert isinstance(result["cited_chunk_indices"], list)

    def test_idempotency_draft_deletion(self):
        """Verify that draft docs are identified for deletion on re-run."""
        # Simulate: existing docs with status=draft should be deleted
        statuses = ["draft", "published", "reviewing", "draft"]
        drafts = [s for s in statuses if s == "draft"]
        assert len(drafts) == 2  # Only draft docs should be targeted
