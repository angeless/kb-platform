"""Tests for prompt construction."""

from orchestrator.prompts import build_propose_prompt, build_generate_doc_prompt


class TestBuildProposePrompt:
    def test_includes_chunks(self):
        """Prompt should contain chunk content."""
        chunks = [
            {"content_text": "退货政策说明：7天无理由退货"},
            {"content_text": "客服流程：先核实订单信息"},
        ]
        system, user = build_propose_prompt("Test Project", "retail", chunks)
        assert "退货政策" in user
        assert "客服流程" in user
        assert "Test Project" in user
        assert "retail" in user

    def test_empty_chunks(self):
        """No chunks should produce placeholder text."""
        system, user = build_propose_prompt("Empty", None, [])
        assert "无资料片段" in user

    def test_truncates_long_chunks(self):
        """Chunks exceeding max_chunk_chars should be truncated."""
        chunks = [{"content_text": "x" * 5000}, {"content_text": "y" * 5000}]
        system, user = build_propose_prompt("Big", None, chunks, max_chunk_chars=6000)
        # Should not contain full second chunk
        assert "yyyyy" not in user or "截断" in user

    def test_industry_hint_none(self):
        """When industry_hint is None, prompt should indicate it's unspecified."""
        chunks = [{"content_text": "some content"}]
        system, user = build_propose_prompt("P", None, chunks)
        assert "未指定" in user

    def test_system_prompt_not_empty(self):
        """System prompt should have content."""
        system, user = build_propose_prompt("P", None, [])
        assert len(system) > 50


class TestBuildGenerateDocPrompt:
    def test_includes_node_info(self):
        """Prompt should contain node name, type, and description."""
        chunks = [{"index": 0, "content_text": "退货政策：7天无理由退货"}]
        system, user = build_generate_doc_prompt(
            node_name="退款规则",
            node_type="topic",
            node_description="客服退款相关规则",
            node_level=2,
            chunks=chunks,
        )
        assert "退款规则" in user
        assert "topic" in user
        assert "客服退款相关规则" in user
        assert "退货政策" in user

    def test_includes_chunk_index(self):
        """Chunks should be labeled with their index."""
        chunks = [
            {"index": 0, "content_text": "内容A"},
            {"index": 1, "content_text": "内容B", "page_or_timestamp": "第3页"},
        ]
        system, user = build_generate_doc_prompt("Node", "topic", None, 1, chunks)
        assert "[片段0]" in user
        assert "[片段1]" in user
        assert "第3页" in user

    def test_empty_chunks(self):
        """No chunks should produce placeholder text."""
        system, user = build_generate_doc_prompt("Node", "topic", None, 1, [])
        assert "无相关资料片段" in user

    def test_truncates_long_chunks(self):
        """Chunks exceeding max_chunk_chars should be truncated."""
        chunks = [
            {"index": 0, "content_text": "x" * 5000},
            {"index": 1, "content_text": "y" * 5000},
        ]
        system, user = build_generate_doc_prompt(
            "Node", "topic", None, 1, chunks, max_chunk_chars=6000
        )
        assert "截断" in user

    def test_system_prompt_constraints(self):
        """System prompt should enforce source-based generation."""
        system, user = build_generate_doc_prompt("N", "topic", None, 1, [])
        assert "不得编造" in system
        assert "来源" in system

    def test_description_none_fallback(self):
        """When node_description is None, should show '未指定'."""
        system, user = build_generate_doc_prompt("N", "topic", None, 1, [])
        assert "未指定" in user
