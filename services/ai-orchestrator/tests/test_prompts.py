"""Tests for prompt construction."""

from orchestrator.prompts import build_propose_prompt


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
