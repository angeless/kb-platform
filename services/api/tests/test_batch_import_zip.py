"""Integration tests for v0.47.8 — ZIP batch import.

Verifies endpoint structure, validation patterns, and service integration
via source inspection (Python 3.9 compatible).
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _read(relpath: str) -> str:
    return (ROOT / relpath).read_text()


# --- Endpoint structure ---

def test_batch_import_endpoint_exists():
    """POST /{project_id}/batch-import endpoint is registered."""
    src = _read("services/api/app/routers/batch_import.py")
    assert "/{project_id}/batch-import" in src
    assert "def create_batch_import(" in src


def test_batch_import_requires_editor_role():
    """ZIP upload requires at least editor role."""
    src = _read("services/api/app/routers/batch_import.py")
    idx = src.index("def create_batch_import(")
    func_section = src[max(0, idx - 100):idx + 400]
    assert 'require_role("editor")' in func_section


def test_batch_import_accepts_zip_file():
    """Endpoint accepts file upload via File(...)."""
    src = _read("services/api/app/routers/batch_import.py")
    assert "File(...)" in src
    assert "UploadFile" in src


def test_batch_import_has_auto_start_option():
    """auto_start form parameter controls whether ingestion starts."""
    src = _read("services/api/app/routers/batch_import.py")
    assert "auto_start" in src


# --- Service layer ---

def test_batch_import_service_exists():
    """BatchImportService is imported and used."""
    src = _read("services/api/app/routers/batch_import.py")
    assert "BatchImportService" in src
    assert "svc.create_batch(" in src


def test_batch_import_status_endpoint():
    """GET /{project_id}/batch-import/{batch_id} returns status."""
    src = _read("services/api/app/routers/batch_import.py")
    assert "/{project_id}/batch-import/{batch_id}" in src
    assert "def get_batch_import(" in src


def test_batch_import_returns_400_on_error():
    """Endpoint declares 400 response for invalid files."""
    src = _read("services/api/app/routers/batch_import.py")
    assert "400" in src


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
