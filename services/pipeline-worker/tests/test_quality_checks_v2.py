"""Unit tests for v0.49.4 quality check enhancements."""

import importlib.util
import os
import sys

# Direct import to avoid loading all stages (which need DB connections)
_spec = importlib.util.spec_from_file_location(
    "quality_check",
    os.path.join(os.path.dirname(__file__), "..", "worker", "stages", "quality_check.py"),
)
quality_check_mod = importlib.util.module_from_spec(_spec)
sys.modules["quality_check_mod"] = quality_check_mod
_spec.loader.exec_module(quality_check_mod)


class TestFormatConsistency:
    """Format consistency checks."""

    def test_heading_skip_detected(self):
        """H1 → H3 (skipping H2) produces format issue."""
        content = "# Title\n\nSome text\n\n### Subsection\n\nMore text"
        issues = quality_check_mod._check_format_consistency(content)
        assert len(issues) >= 1
        assert "标题层级跳跃" in issues[0]["message"]

    def test_valid_heading_hierarchy(self):
        """H1 → H2 → H3 produces no issues."""
        content = "# Title\n\n## Section\n\n### Subsection"
        issues = quality_check_mod._check_format_consistency(content)
        assert len(issues) == 0

    def test_no_headings_no_issues(self):
        """Document without headings → no format issues."""
        content = "Just regular text.\n\nAnother paragraph."
        issues = quality_check_mod._check_format_consistency(content)
        assert len(issues) == 0


class TestSourceReferences:
    """Source reference checks."""

    def test_assertive_without_refs(self):
        """Assertive statement without source refs produces issue."""
        content = "研究表明这种方法非常有效。数据显示增长率达到 50%。"
        issues = quality_check_mod._check_source_references(content, has_source_refs=False)
        assert len(issues) >= 1
        assert "断言性语句" in issues[0]["message"]

    def test_assertive_with_refs(self):
        """Assertive statement with source refs → no issue."""
        content = "研究表明这种方法非常有效。"
        issues = quality_check_mod._check_source_references(content, has_source_refs=True)
        assert len(issues) == 0

    def test_no_assertions(self):
        """No assertive statements → no issue regardless of refs."""
        content = "This is a simple description of the process."
        issues = quality_check_mod._check_source_references(content, has_source_refs=False)
        assert len(issues) == 0


class TestTerminologyConsistency:
    """Terminology consistency checks."""

    def test_mixed_terminology_detected(self):
        """Using both '机器学习' and 'ML' → terminology issue."""
        content = "机器学习是一种重要的技术。ML models are trained on data."
        issues = quality_check_mod._check_terminology_consistency(content)
        assert len(issues) >= 1
        assert "术语不一致" in issues[0]["message"]

    def test_consistent_terminology(self):
        """Using only Chinese terms → no issue."""
        content = "机器学习和深度学习是人工智能的核心技术。"
        issues = quality_check_mod._check_terminology_consistency(content)
        assert len(issues) == 0

    def test_empty_content(self):
        """Empty content → no issues."""
        issues = quality_check_mod._check_terminology_consistency("")
        assert len(issues) == 0
