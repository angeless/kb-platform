"""Tests for v0.47.7 — Model API Key encryption docs + rotation API.

Uses source inspection to verify:
1. Rotate-key endpoint exists in model_providers router
2. Service has rotate_key method
3. Schema has RotateKeyRequest
4. Security documentation exists
5. Audit logging on rotation
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _read(relpath: str) -> str:
    return (ROOT / relpath).read_text()


# --- Schema tests ---

def test_rotate_key_schema_exists():
    src = _read("packages/shared-schemas/shared_schemas/model_config.py")
    assert "class ModelProviderRotateKeyRequest" in src
    assert "new_api_key" in src


# --- Service tests ---

def test_service_has_rotate_key_method():
    src = _read("services/api/app/services/model_provider_service.py")
    assert "async def rotate_key(" in src


def test_service_rotate_key_encrypts():
    src = _read("services/api/app/services/model_provider_service.py")
    idx = src.index("async def rotate_key(")
    method_body = src[idx:idx + 800]
    assert "encrypt(" in method_body


def test_service_rotate_key_checks_provider_exists():
    src = _read("services/api/app/services/model_provider_service.py")
    idx = src.index("async def rotate_key(")
    method_body = src[idx:idx + 800]
    assert "NotFoundException" in method_body


# --- Router tests ---

def test_router_has_rotate_key_endpoint():
    src = _read("services/api/app/routers/model_providers.py")
    assert "/rotate-key" in src
    assert "rotate_provider_key" in src


def test_router_rotate_requires_tenant_admin():
    src = _read("services/api/app/routers/model_providers.py")
    idx = src.index("def rotate_provider_key")
    func_section = src[max(0, idx - 400):idx + 300]
    assert 'require_role("tenant_admin")' in func_section


def test_router_rotate_logs_audit():
    src = _read("services/api/app/routers/model_providers.py")
    idx = src.index("def rotate_provider_key")
    func_section = src[idx:idx + 600]
    assert "audit.log" in func_section
    assert '"rotate_key"' in func_section


def test_router_imports_rotate_schema():
    src = _read("services/api/app/routers/model_providers.py")
    assert "ModelProviderRotateKeyRequest" in src


# --- Documentation tests ---

def test_security_doc_exists():
    doc = _read("docs/security/model-key-encryption.md")
    assert "AES-256-GCM" in doc
    assert "PBKDF2" in doc
    assert "rotate" in doc.lower()


def test_security_doc_covers_wire_format():
    doc = _read("docs/security/model-key-encryption.md")
    assert "KDF2" in doc
    assert "salt" in doc
    assert "nonce" in doc


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
