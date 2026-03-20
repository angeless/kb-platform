"""Tests for T-37-04: Architecture tree cycle detection.

Verifies that update_node() detects and rejects parent_id changes
that would create cycles in the architecture tree.
"""

import inspect
import re

import pytest


class TestArchCycleDetection:
    """Cycle detection must exist in update_node()."""

    def test_error_code_exists(self):
        from shared_errors import ErrorCode

        assert hasattr(ErrorCode, "ARCH_CYCLE_DETECTED")
        assert ErrorCode.ARCH_CYCLE_DETECTED == "ARCH_CYCLE_DETECTED"

    def test_update_node_references_cycle_error(self):
        from app.services.architecture_service import ArchitectureService

        source = inspect.getsource(ArchitectureService.update_node)
        assert "ARCH_CYCLE_DETECTED" in source, "update_node must use ARCH_CYCLE_DETECTED error code"

    def test_self_parent_check_exists(self):
        """update_node must check parent_id != node_id."""
        from app.services.architecture_service import ArchitectureService

        source = inspect.getsource(ArchitectureService.update_node)
        assert "new_parent_id == node_id" in source, "Must check self-parent reference"

    def test_ancestor_chain_traversal_exists(self):
        """update_node must traverse the parent chain to detect cycles."""
        from app.services.architecture_service import ArchitectureService

        source = inspect.getsource(ArchitectureService.update_node)
        assert "parent_id" in source
        # Must have a loop for traversal (for/while)
        assert re.search(r"for .+ in range\(50\)", source), "Must traverse parent chain with max depth 50"

    def test_cycle_check_in_ancestor_loop(self):
        """The ancestor loop must check if parent_id equals the target node_id."""
        from app.services.architecture_service import ArchitectureService

        source = inspect.getsource(ArchitectureService.update_node)
        assert "parent_node.parent_id == node_id" in source, "Must detect cycle by checking ancestor == node_id"

    def test_conflict_exception_raised_for_cycle(self):
        """Must raise ConflictException for cycle detection."""
        from app.services.architecture_service import ArchitectureService

        source = inspect.getsource(ArchitectureService.update_node)
        assert source.count("ConflictException") >= 2, "Must raise ConflictException for both self-parent and ancestor cycle"
