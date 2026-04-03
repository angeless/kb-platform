"""Integration tests for v0.47.8 — Cross-tenant isolation.

Verifies that tenant isolation is enforced across all major service layers
and routers via source inspection. Each service must scope queries by kb_id.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _read(relpath: str) -> str:
    return (ROOT / relpath).read_text()


# --- Deps layer: kb_id extraction ---

def test_get_kb_id_from_current_user():
    """get_kb_id dependency extracts kb_id from authenticated user."""
    src = _read("services/api/app/deps.py")
    assert "def get_kb_id(" in src
    assert "current_user.kb_id" in src


# --- Service layer tenant scoping ---

def test_project_service_scoped_by_kb_id():
    """ProjectService queries are scoped by kb_id."""
    src = _read("services/api/app/services/project_service.py")
    assert "kb_id" in src
    assert "self.kb_id" in src


def test_audit_service_scoped_by_kb_id():
    """AuditService queries are scoped by kb_id."""
    src = _read("services/api/app/services/audit_service.py")
    assert "AuditLog.kb_id == self.kb_id" in src


def test_model_provider_service_scoped_by_kb_id():
    """ModelProviderService queries are scoped by kb_id."""
    src = _read("services/api/app/services/model_provider_service.py")
    assert "ModelProvider.kb_id == self.kb_id" in src


def test_cross_ref_service_scoped_by_kb_id():
    """CrossRefService queries are scoped by kb_id."""
    src = _read("services/api/app/services/cross_ref_service.py")
    assert "kb_id" in src


# --- Router layer: kb_id injected via Depends ---

def test_projects_router_uses_get_kb_id():
    """Projects router injects kb_id from authenticated user."""
    src = _read("services/api/app/routers/projects.py")
    assert "get_kb_id" in src


def test_assets_router_uses_get_kb_id():
    """Assets router injects kb_id from authenticated user."""
    src = _read("services/api/app/routers/assets.py")
    assert "get_kb_id" in src


def test_architectures_router_uses_get_kb_id():
    """Architectures router injects kb_id from authenticated user."""
    src = _read("services/api/app/routers/architectures.py")
    assert "get_kb_id" in src


def test_batch_import_router_uses_get_kb_id():
    """Batch import router injects kb_id from authenticated user."""
    src = _read("services/api/app/routers/batch_import.py")
    assert "get_kb_id" in src


def test_model_providers_router_uses_get_kb_id():
    """Model providers router injects kb_id from authenticated user."""
    src = _read("services/api/app/routers/model_providers.py")
    assert "get_kb_id" in src


# --- Model layer: kb_id on key models ---

def test_model_provider_has_kb_id_column():
    """ModelProvider model has kb_id FK to tenant."""
    src = _read("packages/shared-models/shared_models/model_config.py")
    assert "kb_id" in src
    assert 'ForeignKey("tenant.id")' in src


def test_project_has_kb_id_column():
    """Project model has kb_id for tenant scoping."""
    src = _read("packages/shared-models/shared_models/project.py")
    assert "kb_id" in src


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
