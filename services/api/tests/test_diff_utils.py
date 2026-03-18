"""Unit tests for version diff logic."""

import difflib


def compute_diff_stats(from_text: str, to_text: str) -> dict:
    """Mirror the diff logic from doc_service.diff_versions for testing."""
    from_lines = from_text.splitlines(keepends=False)
    to_lines = to_text.splitlines(keepends=False)

    diff_lines = []
    added = 0
    removed = 0
    unchanged = 0

    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
        None, from_lines, to_lines
    ).get_opcodes():
        if tag == "equal":
            for line in from_lines[i1:i2]:
                diff_lines.append({"type": "context", "content": line})
                unchanged += 1
        elif tag == "replace":
            for line in from_lines[i1:i2]:
                diff_lines.append({"type": "removed", "content": line})
                removed += 1
            for line in to_lines[j1:j2]:
                diff_lines.append({"type": "added", "content": line})
                added += 1
        elif tag == "delete":
            for line in from_lines[i1:i2]:
                diff_lines.append({"type": "removed", "content": line})
                removed += 1
        elif tag == "insert":
            for line in to_lines[j1:j2]:
                diff_lines.append({"type": "added", "content": line})
                added += 1

    return {
        "diff_lines": diff_lines,
        "stats": {"added": added, "removed": removed, "unchanged": unchanged},
    }


class TestDiffLogic:
    def test_identical_content(self):
        """Same content should have no added/removed lines."""
        result = compute_diff_stats("# Title\nContent", "# Title\nContent")
        assert result["stats"]["added"] == 0
        assert result["stats"]["removed"] == 0
        assert result["stats"]["unchanged"] == 2

    def test_added_lines(self):
        """New lines in to_version should be marked as added."""
        result = compute_diff_stats("# Title", "# Title\nNew line")
        assert result["stats"]["added"] == 1
        assert result["stats"]["removed"] == 0

    def test_removed_lines(self):
        """Lines missing in to_version should be marked as removed."""
        result = compute_diff_stats("# Title\nOld line", "# Title")
        assert result["stats"]["removed"] == 1
        assert result["stats"]["added"] == 0

    def test_replaced_lines(self):
        """Changed lines should show as removed + added."""
        result = compute_diff_stats(
            "# Title\n退款时效：3-5天",
            "# Title\n退款时效：1-3天"
        )
        assert result["stats"]["removed"] == 1
        assert result["stats"]["added"] == 1
        assert result["stats"]["unchanged"] == 1

    def test_diff_line_types(self):
        """Diff lines should have correct type labels."""
        result = compute_diff_stats("A\nB", "A\nC")
        types = [line["type"] for line in result["diff_lines"]]
        assert "context" in types  # "A" is unchanged
        assert "removed" in types  # "B" removed
        assert "added" in types  # "C" added

    def test_empty_from(self):
        """Diff from empty should show all lines as added."""
        result = compute_diff_stats("", "New content\nLine 2")
        assert result["stats"]["added"] == 2
        assert result["stats"]["removed"] == 0

    def test_empty_to(self):
        """Diff to empty should show all lines as removed."""
        result = compute_diff_stats("Old content\nLine 2", "")
        assert result["stats"]["removed"] == 2
        assert result["stats"]["added"] == 0

    def test_multiline_chinese(self):
        """Should handle Chinese text correctly."""
        result = compute_diff_stats(
            "# 退款规则\n\n退款时效：7天\n适用范围：全品类",
            "# 退款规则\n\n退款时效：30天\n适用范围：全品类\n新增：特殊商品除外"
        )
        assert result["stats"]["added"] >= 1
        assert result["stats"]["removed"] >= 1
        assert result["stats"]["unchanged"] >= 2
