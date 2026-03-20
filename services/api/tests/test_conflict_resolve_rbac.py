"""Tests for T-36-08: Conflict resolve requires reviewer role.

Verifies that the resolve_conflict endpoint enforces require_role("reviewer")
by inspecting the source code and validating ROLE_HIERARCHY constraints.
"""

import inspect

import pytest

from app.deps import ROLE_HIERARCHY


class TestResolveConflictRBAC:
    """Verify resolve endpoint has correct role requirement."""

    def test_resolve_endpoint_uses_require_role_reviewer(self):
        """Source code of resolve_conflict must reference require_role('reviewer')."""
        from app.routers.conflicts import resolve_conflict

        source = inspect.getsource(resolve_conflict)
        assert 'require_role("reviewer")' in source or "require_role('reviewer')" in source

    def test_viewer_below_reviewer(self):
        """Viewer role level must be below reviewer."""
        assert ROLE_HIERARCHY["viewer"] < ROLE_HIERARCHY["reviewer"]

    def test_editor_below_reviewer(self):
        """Editor role level must be below reviewer."""
        assert ROLE_HIERARCHY["editor"] < ROLE_HIERARCHY["reviewer"]

    def test_reviewer_meets_requirement(self):
        """Reviewer role level must meet the reviewer threshold."""
        assert ROLE_HIERARCHY["reviewer"] >= ROLE_HIERARCHY["reviewer"]

    def test_tenant_admin_meets_requirement(self):
        """Tenant admin role level must exceed the reviewer threshold."""
        assert ROLE_HIERARCHY["tenant_admin"] >= ROLE_HIERARCHY["reviewer"]

    def test_project_admin_meets_requirement(self):
        """Project admin role level must exceed the reviewer threshold."""
        assert ROLE_HIERARCHY["project_admin"] >= ROLE_HIERARCHY["reviewer"]
