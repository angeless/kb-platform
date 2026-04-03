"""Integration tests for v0.47.8 — Architecture nodes CRUD.

Verifies CRUD endpoints, role enforcement, parent-child support,
and service layer integration via source inspection.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _read(relpath: str) -> str:
    return (ROOT / relpath).read_text()


# --- Node CRUD endpoints ---

def test_create_node_endpoint():
    """POST /v1/architectures/{arch_id}/nodes exists."""
    src = _read("services/api/app/routers/architectures.py")
    assert '"/v1/architectures/{arch_id}/nodes"' in src
    assert "def create_node(" in src


def test_update_node_endpoint():
    """PATCH /v1/architectures/{arch_id}/nodes/{node_id} exists."""
    src = _read("services/api/app/routers/architectures.py")
    assert "/v1/architectures/{arch_id}/nodes/{node_id}" in src
    assert "def update_node(" in src


def test_list_nodes_endpoint():
    """GET /v1/architectures/{arch_id}/nodes exists."""
    src = _read("services/api/app/routers/architectures.py")
    assert "def list_nodes(" in src


def test_create_node_requires_project_admin():
    """Node creation requires project_admin role."""
    src = _read("services/api/app/routers/architectures.py")
    idx = src.index("def create_node(")
    func_section = src[max(0, idx - 200):idx + 200]
    assert 'require_role("project_admin")' in func_section


def test_update_node_requires_project_admin():
    """Node update requires project_admin role."""
    src = _read("services/api/app/routers/architectures.py")
    idx = src.index("def update_node(")
    func_section = src[max(0, idx - 200):idx + 300]
    assert 'require_role("project_admin")' in func_section


# --- Schema supports parent-child ---

def test_node_create_schema_has_parent():
    """NodeCreate schema supports parent_id for tree structure."""
    src = _read("packages/shared-schemas/shared_schemas/architecture.py")
    assert "parent_id" in src


def test_node_out_schema():
    """NodeOut schema is used in list and create responses."""
    src = _read("services/api/app/routers/architectures.py")
    assert "NodeOut" in src


# --- Service layer ---

def test_architecture_service_scoped_by_kb_id():
    """ArchitectureService is created with kb_id for tenant isolation."""
    src = _read("services/api/app/routers/architectures.py")
    assert "ArchitectureService(db, kb_id)" in src


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
