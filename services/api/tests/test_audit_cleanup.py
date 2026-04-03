"""Tests for v0.47.5 — Audit log retention policy + cleanup.

Uses source inspection to verify:
1. Settings has audit_retention_days with default 90
2. audit_service.py has cleanup_old_audit_logs function with batch delete
3. audit router exposes POST /cleanup endpoint requiring tenant_admin
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _read(relpath: str) -> str:
    return (ROOT / relpath).read_text()


# --- Settings tests ---

def test_settings_has_audit_retention_days():
    src = _read("packages/shared-config/shared_config/settings.py")
    assert "audit_retention_days" in src
    assert "= 90" in src


# --- Service tests ---

def test_cleanup_function_exists():
    src = _read("services/api/app/services/audit_service.py")
    assert "async def cleanup_old_audit_logs(" in src


def test_cleanup_uses_batch_delete():
    src = _read("services/api/app/services/audit_service.py")
    assert "CLEANUP_BATCH_SIZE" in src
    assert "1000" in src


def test_cleanup_uses_retention_days():
    src = _read("services/api/app/services/audit_service.py")
    assert "audit_retention_days" in src
    assert "timedelta(days=" in src


def test_cleanup_uses_created_at_filter():
    src = _read("services/api/app/services/audit_service.py")
    assert "created_at" in src


def test_cleanup_logs_deletion_count():
    src = _read("services/api/app/services/audit_service.py")
    assert "logger.info" in src
    assert "deleted" in src.lower()


def test_cleanup_commits_per_batch():
    src = _read("services/api/app/services/audit_service.py")
    # Should have commit inside the while loop
    func_start = src.index("async def cleanup_old_audit_logs")
    func_body = src[func_start:]
    assert "await db.commit()" in func_body


# --- Router tests ---

def test_router_has_cleanup_endpoint():
    src = _read("services/api/app/routers/audit.py")
    assert '"/cleanup"' in src
    assert "cleanup_old_audit_logs" in src


def test_router_cleanup_requires_tenant_admin():
    src = _read("services/api/app/routers/audit.py")
    # Find the cleanup function
    idx = src.index("def cleanup_audit_logs")
    func_section = src[max(0, idx - 300):idx + 200]
    assert 'require_role("tenant_admin")' in func_section


def test_router_cleanup_returns_deleted_count():
    src = _read("services/api/app/routers/audit.py")
    idx = src.index("def cleanup_audit_logs")
    func_section = src[idx:idx + 200]
    assert "deleted_count" in func_section


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
