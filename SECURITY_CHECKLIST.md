# Security Audit Checklist
**Project:** knowledge_SQL | **Date:** 2026-03-19 | **Status:** 6 Issues Found

---

## Issues to Fix (Priority Order)

### 🔴 CRITICAL (Fix within 48 hours)

- [ ] **IDOR in Node Assignment**
  - [ ] Update `services/api/app/services/doc_service.py::assign_node()`
  - [ ] Add `Architecture.project_id == doc.project_id` check
  - [ ] Add unit test in `tests/services/test_doc_service_idor.py`
  - [ ] Run test: `pytest tests/services/test_doc_service_idor.py -v`
  - [ ] Deploy to staging and verify
  - **Time:** 1 hour
  - **Files:** 1 service file, 1 test file

---

### 🟠 HIGH (Fix within 1 week)

- [ ] **Rate Limiter Accepts Expired Tokens**
  - [ ] Update `services/api/app/middleware/rate_limit.py::_extract_identity()`
  - [ ] Change `options={"verify_exp": False}` to `{"verify_exp": True}`
  - [ ] Add exception handler for `jwt.ExpiredSignatureError`
  - [ ] Add unit test in `tests/middleware/test_rate_limit_security.py`
  - [ ] Run test: `pytest tests/middleware/test_rate_limit_security.py -v`
  - [ ] Deploy to staging
  - **Time:** 30 minutes
  - **Files:** 1 middleware file, 1 test file

- [ ] **Rate Limiter Fails Open**
  - [ ] Create `services/api/app/middleware/rate_limit_fallback.py` with in-memory limiter
  - [ ] Update `services/api/app/middleware/rate_limit.py::dispatch()` to use fallback
  - [ ] Update app initialization for cleanup task
  - [ ] Add unit tests in `tests/middleware/test_rate_limit_fallback.py`
  - [ ] Run tests: `pytest tests/middleware/test_rate_limit_fallback.py -v`
  - [ ] Integration test: Stop Redis and verify rate limiting still works
  - [ ] Deploy to staging
  - **Time:** 2 hours
  - **Files:** 1 new middleware file, 1 updated middleware file, 1 test file

---

### 🟡 MEDIUM (Fix within 2 weeks)

- [ ] **SSRF Missing Blocklist Entries**
  - [ ] Update `services/api/app/utils/url_fetcher.py::_BLOCKED_NETWORKS`
  - [ ] Add `ipaddress.ip_network("0.0.0.0/32")`
  - [ ] Add `ipaddress.ip_network("::/128")`
  - [ ] Add test cases in `tests/utils/test_url_fetcher_ssrf.py`
  - [ ] Run test: `pytest tests/utils/test_url_fetcher_ssrf.py -v`
  - **Time:** 15 minutes
  - **Files:** 1 utility file, 1 test file

- [ ] **ZIP Bomb Protection**
  - [ ] Update `services/api/app/services/asset_service.py::import_archive()`
  - [ ] Add `MAX_DECOMPRESSED_SIZE_SINGLE = 500 * 1024 * 1024` constant
  - [ ] Add `MAX_DECOMPRESSED_SIZE_TOTAL = 2 * 1024 * 1024 * 1024` constant
  - [ ] Add size check: `ZipInfo.file_size > MAX_DECOMPRESSED_SIZE_SINGLE`
  - [ ] Add total size tracking
  - [ ] Add unit tests in `tests/services/test_asset_service_zip_bomb.py`
  - [ ] Run tests: `pytest tests/services/test_asset_service_zip_bomb.py -v`
  - **Time:** 1 hour
  - **Files:** 1 service file, 1 test file

- [ ] **Weak Key Derivation**
  - [ ] Update `services/api/app/utils/crypto.py` to use PBKDF2
  - [ ] Replace `_derive_key()` with PBKDF2 implementation (100k iterations)
  - [ ] Update `encrypt()` to use random salt
  - [ ] Update `decrypt()` to handle both old and new formats
  - [ ] Add backward compatibility for existing encrypted data
  - [ ] Create migration script: `services/api/scripts/migrate_encrypted_keys.py`
  - [ ] Add unit tests in `tests/utils/test_crypto_pbkdf2.py`
  - [ ] Run tests: `pytest tests/utils/test_crypto_pbkdf2.py -v`
  - [ ] Run migration on test data: `python services/api/scripts/migrate_encrypted_keys.py`
  - **Time:** 2 hours (+ migration)
  - **Files:** 1 utility file, 1 migration script, 1 test file

---

## Pre-Deployment Checklist

For each fix:

- [ ] Code changes reviewed by another developer
- [ ] All unit tests pass: `pytest -v`
- [ ] Integration tests pass
- [ ] No new security warnings from SAST (if enabled)
- [ ] Backward compatibility tested (if applicable)
- [ ] Performance impact assessed (< 5% overhead acceptable)
- [ ] Logging/monitoring added for fix
- [ ] Documentation updated
- [ ] Deployment plan reviewed
- [ ] Rollback procedure documented

---

## Deployment Order

```
1. CRITICAL: Node assignment IDOR fix         (Production first)
2. HIGH:     Expired token rate limit fix      (Next)
3. HIGH:     Rate limiter fallback             (Next)
4. MEDIUM:   SSRF blocklist entries           (Next sprint)
5. MEDIUM:   ZIP bomb protection              (Next sprint)
6. MEDIUM:   Crypto key derivation + migration (Next sprint)
```

---

## Testing Commands

```bash
# Run all security-related tests
cd services/api
pytest tests/ -k "security or ssrf or idor or rate_limit or crypto or zip" -v

# Run specific test suites
pytest tests/services/test_doc_service_idor.py -v
pytest tests/middleware/test_rate_limit_security.py -v
pytest tests/middleware/test_rate_limit_fallback.py -v
pytest tests/utils/test_url_fetcher_ssrf.py -v
pytest tests/services/test_asset_service_zip_bomb.py -v
pytest tests/utils/test_crypto_pbkdf2.py -v

# Run linter
flake8 app/

# Run type checker
mypy app/
```

---

## Monitoring After Deployment

### After Node Assignment Fix
- [ ] Monitor audit logs for `assign_node` operations
- [ ] Watch for 404 errors on node assignment endpoints
- [ ] Check that no cross-tenant assignments occur

### After Rate Limiter Fixes
- [ ] Monitor rate limiting errors in logs
- [ ] Alert if fallback mode is activated for >5 minutes
- [ ] Test rate limiting by sending many requests
- [ ] Verify Redis reconnection works after outage

### After SSRF Fix
- [ ] Monitor URL import feature usage
- [ ] Check access logs for attempts to 0.0.0.0 or ::
- [ ] No change in legitimate URL import volume

### After ZIP Bomb Fix
- [ ] Monitor archive imports
- [ ] Check for files rejected due to size limits
- [ ] Verify legitimate ZIPs still import successfully

### After Crypto Fix
- [ ] Verify all encrypted keys still decrypt correctly
- [ ] Check that new keys use salt-based encryption
- [ ] No errors in provider authentication

---

## Documentation Files

- **SECURITY_AUDIT_2026-03-19.md** - Full audit report with technical details
- **SECURITY_REMEDIATION_GUIDE.md** - Step-by-step fix procedures with code
- **SECURITY_AUDIT_SUMMARY.txt** - Executive summary
- **SECURITY_CHECKLIST.md** - This file (task tracking)

---

## Sign-Off

Audit Completed By: Security Team
Date: 2026-03-19
Next Audit: 2026-06-19 (quarterly)

---

## Notes

- All fixes include test cases to prevent regression
- Backward compatibility is maintained where applicable
- No breaking changes to public API
- All fixes follow OWASP and CWE guidelines
- Team should review SECURITY_REMEDIATION_GUIDE.md before starting work
