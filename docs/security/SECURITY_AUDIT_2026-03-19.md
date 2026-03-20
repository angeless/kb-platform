# Security Code Audit Report
**Project:** knowledge_SQL
**Date:** 2026-03-19
**Auditor:** Security Team
**Scope:** Backend API services and frontend web application

---

## Executive Summary

This audit identified **1 CRITICAL** vulnerability, **2 HIGH** severity issues, and **3 MEDIUM** severity concerns across the codebase. The most critical finding is an **IDOR vulnerability in document-node assignment** that allows users to assign documents to architecture nodes from other tenants. Additionally, the **rate limiting middleware uses expired tokens** and **JWT expiry validation is disabled** in the rate limiter.

---

## Findings

### 1. CRITICAL: Insecure Direct Object Reference (IDOR) in Node Assignment

**Severity:** CRITICAL
**File:** `/sessions/nifty-eager-babbage/mnt/knowledge_SQL/services/api/app/services/doc_service.py`
**Lines:** 86-103
**CWE:** CWE-639 (Authorization Bypass Through User-Controlled Key)

**Vulnerability Description:**

The `assign_node()` method in `DocService` verifies that a document belongs to the tenant's project (via `_verify_project()` in line 88), but **does NOT verify that the target architecture node also belongs to the same project**. This allows an authenticated user to assign documents to architecture nodes from other tenants.

```python
async def assign_node(self, doc_id: uuid.UUID, node_id: uuid.UUID) -> KnowledgeDoc:
    """Assign a document to an architecture node."""
    doc = await self.get(doc_id)  # ✓ Verified to be in user's tenant

    # ✗ VULNERABILITY: No verification that node_id is in the same project/tenant
    q = select(ArchitectureNode).where(ArchitectureNode.id == node_id)
    result = await self.db.execute(q)
    node = result.scalar_one_or_none()
    if node is None:
        raise NotFoundException(...)

    doc.node_id = node_id  # ✗ Allows cross-tenant node assignment
    await self.db.flush()
    return doc
```

**Proof of Concept:**

1. Tenant A has Document D1 in Project P1
2. Tenant B has Architecture A2 with Nodes in Project P2
3. User from Tenant A performs:
   ```bash
   POST /v1/docs/{D1}/assign-node
   {
     "node_id": "{Node from Tenant B's architecture}"
   }
   ```
4. The assignment succeeds because `ArchitectureNode` table has no `tenant_id` column and no cross-table verification occurs
5. Document D1 (from Tenant A) is now linked to architecture node from Tenant B (data leakage via foreign key)

**Impact:**
- Cross-tenant data leakage via foreign key relationships
- Unauthorized linking of documents to other tenants' architectures
- Potential information disclosure about architecture structure of other tenants

**Recommended Fix:**

Verify that the target node's architecture belongs to the same project:

```python
async def assign_node(self, doc_id: uuid.UUID, node_id: uuid.UUID) -> KnowledgeDoc:
    """Assign a document to an architecture node."""
    doc = await self.get(doc_id)

    # Verify the target node exists AND belongs to same project
    q = select(ArchitectureNode).join(
        Architecture,
        ArchitectureNode.architecture_id == Architecture.id
    ).where(
        ArchitectureNode.id == node_id,
        Architecture.project_id == doc.project_id  # ← ADD THIS
    )
    result = await self.db.execute(q)
    node = result.scalar_one_or_none()
    if node is None:
        raise NotFoundException(...)

    doc.node_id = node_id
    await self.db.flush()
    return doc
```

---

### 2. HIGH: Authentication Bypass - Rate Limiter Accepts Expired Tokens

**Severity:** HIGH
**File:** `/sessions/nifty-eager-babbage/mnt/knowledge_SQL/services/api/app/middleware/rate_limit.py`
**Lines:** 50-69
**CWE:** CWE-613 (Insufficient Session Expiration)

**Vulnerability Description:**

The rate limiting middleware extracts the tenant ID from JWT tokens **without verifying token expiration**:

```python
def _extract_identity(self, request: Request) -> str:
    """Extract rate limit key: tenant_id from auth header, or client IP."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            import jwt
            settings = get_settings()
            payload = jwt.decode(
                auth[7:], settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
                options={"verify_exp": False},  # ✗ VULNERABILITY: Expiry not checked
            )
            tid = payload.get("tenant_id")
            if tid:
                return f"tenant:{tid}"
        except Exception:
            pass
    # Fallback to IP
    client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}"
```

**Proof of Concept:**

1. User logs in, receives access token (valid for 30 minutes)
2. Token expires after 30 minutes
3. User attempts API request with expired token
4. API authentication (line 45 in `deps.py`) correctly rejects the expired token with 401
5. **HOWEVER:** If the request passes through the rate limiter before hitting the auth middleware, the rate limiter extracts `tenant_id` from the **expired token** and applies tenant-based rate limiting instead of IP-based fallback
6. This allows an attacker with an expired token to:
   - Apply rate limiting to a legitimate tenant's quota (DoS)
   - Extract tenant IDs from expired tokens and use them for reconnaissance

**Why This Matters:**

The rate limiter is a middleware that runs before route handlers. If a request with an expired token reaches the rate limiter BEFORE the actual endpoint's authentication check, the rate limiter will treat it as authenticated to that tenant.

**Impact:**
- Denial of Service against specific tenants using expired tokens
- Tenant ID enumeration/reconnaissance
- Rate limit quota depletion for targeted tenants

**Recommended Fix:**

Enable token expiration verification in rate limiter:

```python
def _extract_identity(self, request: Request) -> str:
    """Extract rate limit key: tenant_id from auth header, or client IP."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            import jwt
            settings = get_settings()
            payload = jwt.decode(
                auth[7:], settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
                # ✓ FIXED: Enable expiration verification
                options={"verify_exp": True},
            )
            tid = payload.get("tenant_id")
            if tid:
                return f"tenant:{tid}"
        except jwt.ExpiredSignatureError:
            # Token is expired, fall back to IP-based rate limiting
            pass
        except Exception:
            pass
    # Fallback to IP
    client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}"
```

---

### 3. HIGH: Rate Limiter Fails Open When Redis Unavailable

**Severity:** HIGH
**File:** `/sessions/nifty-eager-babbage/mnt/knowledge_SQL/services/api/app/middleware/rate_limit.py`
**Lines:** 78-81, 130-133
**CWE:** CWE-693 (Protection Mechanism Failure)

**Vulnerability Description:**

The rate limiter gracefully degrades when Redis is unavailable, but this "fail open" behavior means **no rate limiting occurs** during Redis outages:

```python
async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
    path = request.url.path

    if path in EXEMPT_PATHS:
        return await call_next(request)

    r = await self._get_redis()
    if r is None:
        # ✗ VULNERABILITY: No rate limiting if Redis unavailable
        return await call_next(request)

    # ... rate limit check ...

    try:
        pipe = r.pipeline()
        # ... rate limit operations ...
    except Exception as e:
        logger.warning("Rate limit check failed: %s", e)
        # ✗ VULNERABILITY: Also fails open on exceptions
        return await call_next(request)
```

**Proof of Concept:**

1. Redis server becomes unavailable (network partition, crash, maintenance)
2. Attacker sends 10,000 requests per second to the API
3. Rate limiter cannot connect to Redis, logs a warning, and **allows all requests through**
4. API is overwhelmed; legitimate users face degraded service or DoS

**Impact:**
- Complete bypass of rate limiting during Redis failures
- Exposure to brute force attacks on auth endpoints
- Resource exhaustion attacks
- Cascading system failures when rate limiting is critical defense

**Recommended Fix:**

Implement "fail closed" behavior with in-memory fallback or circuit breaker:

**Option A: Fail Closed (Reject requests)**
```python
async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
    path = request.url.path

    if path in EXEMPT_PATHS:
        return await call_next(request)

    r = await self._get_redis()
    if r is None:
        # ✓ FIXED: Fail closed - reject requests during outage
        return JSONResponse(
            status_code=503,
            content={
                "error_code": "SERVICE_UNAVAILABLE",
                "message": "Rate limiting service temporarily unavailable"
            }
        )
```

**Option B: Fallback to In-Memory Rate Limiting**
```python
# Add in-memory token bucket per IP during Redis downtime
# Requires thread-safe dictionary and periodic cleanup
```

---

### 4. MEDIUM: SSRF Protection Missing Localhost Alias (0.0.0.0)

**Severity:** MEDIUM
**File:** `/sessions/nifty-eager-babbage/mnt/knowledge_SQL/services/api/app/utils/url_fetcher.py`
**Lines:** 20-29
**CWE:** CWE-918 (Server-Side Request Forgery)

**Vulnerability Description:**

The SSRF blocklist does not include `0.0.0.0` or `[::]` (IPv6 all-zeros), which can be used as localhost aliases:

```python
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    # ✗ MISSING: 0.0.0.0/32 (IPv4) and ::/128 (IPv6)
]
```

**Proof of Concept:**

1. Attacker calls `/v1/assets/import-url` with `url=http://0.0.0.0:8080/admin`
2. System tries to fetch from `0.0.0.0:8080` (which resolves to localhost in some contexts)
3. Request succeeds, bypassing SSRF protection
4. Attacker gains access to internal admin interface

**Impact:**
- Bypass of SSRF protection via localhost aliases
- Access to internal services on `0.0.0.0` bindings
- Potential extraction of internal service metadata

**Recommended Fix:**

```python
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("0.0.0.0/32"),           # ✓ ADD: IPv4 any address
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("::/128"),               # ✓ ADD: IPv6 any address
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]
```

---

### 5. MEDIUM: ZIP Archive Import Missing Bomb Protection

**Severity:** MEDIUM
**File:** `/sessions/nifty-eager-babbage/mnt/knowledge_SQL/services/api/app/services/asset_service.py`
**Lines:** 153-247
**CWE:** CWE-409 (Improper Restriction of Rendered UI Layers or Frames)

**Vulnerability Description:**

The ZIP import function checks for path traversal but lacks protection against ZIP bombs (excessive decompression):

```python
async def import_archive(
    self, project_id: uuid.UUID, archive_content: bytes, archive_filename: str
) -> dict:
    """Import a ZIP archive: extract files and create individual Asset records."""
    import io
    import os
    import zipfile

    # ... validation ...

    with zipfile.ZipFile(io.BytesIO(archive_content), "r") as zf:
        entries = [e for e in zf.namelist() if not e.endswith("/")]
        if len(entries) > max_files:  # ✓ File count limit (good)
            raise AppException(...)

        # Security: check ALL entries for path traversal
        for entry_name in entries:
            normalized = os.path.normpath(entry_name)
            if ".." in normalized.split(os.sep) or normalized.startswith("/"):
                raise AppException(...)  # ✓ Path traversal protection (good)

        for entry_name in entries:
            # ✗ MISSING: No decompression size limit
            file_content = zf.read(entry_name)  # Can extract gigabytes from tiny ZIP
```

**Proof of Concept:**

1. Attacker creates ZIP bomb: 1 MB ZIP file containing 10 GB of zeros
2. Attacker uploads via `/v1/assets/import-archive`
3. System decompresses each file with `zf.read(entry_name)` without size limit
4. Server memory exhaustion or disk space exhaustion

**Impact:**
- Denial of Service via resource exhaustion
- Server crash from out-of-memory conditions
- Disk space exhaustion

**Recommended Fix:**

```python
MAX_DECOMPRESSED_SIZE = 500 * 1024 * 1024  # 500 MB per file
MAX_TOTAL_DECOMPRESSED = 2 * 1024 * 1024 * 1024  # 2 GB total

with zipfile.ZipFile(io.BytesIO(archive_content), "r") as zf:
    entries = [e for e in zf.namelist() if not e.endswith("/")]
    if len(entries) > max_files:
        raise AppException(...)

    # ... path traversal checks ...

    total_decompressed = 0
    for entry_name in entries:
        # Get uncompressed size before decompressing
        file_info = zf.getinfo(entry_name)
        if file_info.file_size > MAX_DECOMPRESSED_SIZE:
            raise AppException(
                error_code=ErrorCode.ASSET_TOO_LARGE,
                message=f"Archive member too large: {entry_name}"
            )

        total_decompressed += file_info.file_size
        if total_decompressed > MAX_TOTAL_DECOMPRESSED:
            raise AppException(
                error_code=ErrorCode.ASSET_TOO_LARGE,
                message="Total decompressed size exceeds limit"
            )

        # Now safe to decompress
        file_content = zf.read(entry_name)
```

---

### 6. MEDIUM: Encryption Key Derivation Weakness

**Severity:** MEDIUM
**File:** `/sessions/nifty-eager-babbage/mnt/knowledge_SQL/services/api/app/utils/crypto.py`
**Lines:** 8-13
**CWE:** CWE-326 (Inadequate Encryption Strength)

**Vulnerability Description:**

The key derivation function is weak and non-standard:

```python
def _derive_key(secret: str) -> bytes:
    """Derive a 32-byte key from a string secret (pad or truncate)."""
    key = secret.encode("utf-8")
    if len(key) < 32:
        key = key.ljust(32, b"\0")  # ✗ Pad with zeros (poor entropy)
    return key[:32]  # ✗ Truncate if too long (information loss)
```

**Problems:**

1. **Null padding:** If secret is 16 bytes, the resulting key is `[16 bytes] + [16 zero bytes]`. Zeros have no entropy.
2. **No key stretching:** Does not use PBKDF2, bcrypt, scrypt, or Argon2
3. **Truncation:** If secret > 32 bytes, bytes are lost
4. **Predictable:** Adversaries can brute-force short secrets quickly

**Proof of Concept:**

If `encryption_key = "mysecret"` (8 bytes):
```
key = "mysecret" → 8 bytes
padded key = "mysecret" + 24 zero bytes → 32 bytes
Entropy: ~53 bits (8 ASCII chars) instead of ~256 bits
```

Attacker can brute-force all 8-character secrets: 94^8 ≈ 6 trillion (feasible with GPU)

**Impact:**
- Weak encryption keys
- Encrypted model provider API keys can be brute-forced
- All encrypted data becomes recoverable

**Recommended Fix:**

Use proper key derivation:

```python
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

def _derive_key(secret: str, salt: bytes | None = None) -> bytes:
    """Derive a 32-byte key using PBKDF2."""
    if salt is None:
        salt = b""  # Or store per-value

    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return kdf.derive(secret.encode("utf-8"))
```

**Or require key to be pre-derived:**
```python
# In settings: require encryption_key to be 32 bytes (base64 encoded)
# Validate in __init__: assert len(encryption_key) == 32
```

---

## Summary Table

| ID | Type | Severity | File | Issue | Status |
|----|------|----------|------|-------|--------|
| 1 | IDOR | CRITICAL | doc_service.py | Node assignment without tenant verification | Requires Fix |
| 2 | AuthN Bypass | HIGH | rate_limit.py | Rate limiter accepts expired tokens | Requires Fix |
| 3 | DoS | HIGH | rate_limit.py | Rate limiter fails open | Requires Fix |
| 4 | SSRF | MEDIUM | url_fetcher.py | Missing 0.0.0.0 in blocklist | Requires Fix |
| 5 | ZIP Bomb | MEDIUM | asset_service.py | No decompression size limit | Requires Fix |
| 6 | Crypto | MEDIUM | crypto.py | Weak key derivation | Requires Fix |

---

## Items Verified (No Issues Found)

✓ **SQL Injection:** Search service uses parameterized queries with SQLAlchemy and PostgreSQL `text()` with bound parameters
✓ **JWT Expiry (main auth):** `/deps.py` correctly calls `decode_access_token()` without disabling verification
✓ **Path Traversal (ZIP):** `os.path.normpath()` correctly detects `..` sequences
✓ **XSS in Frontend:** No `dangerouslySetInnerHTML` usage in app source; uses `ReactMarkdown` which is safe
✓ **API Authentication:** All routes require `Depends(get_current_user)` or `Depends(get_tenant_id)`
✓ **Tenant Isolation (models):** All queries correctly filter by `tenant_id` in models (Project, ModelProvider, ModelRoute)
✓ **Sensitive Data Logging:** Logging configuration does not log request/response bodies, passwords, or tokens
✓ **WebSocket Auth:** Uses JWT validation before `websocket.accept()`
✓ **File Upload Validation:** Extension whitelist properly restricts file types
✓ **Password Hashing:** Uses bcrypt with proper salt generation

---

## Recommendations

**Immediate Actions (next 48 hours):**
1. Fix IDOR in node assignment (CRITICAL)
2. Enable token expiration verification in rate limiter (HIGH)
3. Implement rate limit circuit breaker or fail-closed behavior (HIGH)

**Short-term Actions (next sprint):**
4. Add 0.0.0.0 and :: to SSRF blocklist
5. Implement ZIP bomb protection with file size limits
6. Replace weak key derivation with PBKDF2

**Additional Recommendations:**
- Add automated security scanning (SAST) to CI/CD pipeline
- Implement rate limiting at infrastructure level (WAF/load balancer) as defense-in-depth
- Regular penetration testing (quarterly)
- Security code review checklist for team

---

## Audit Scope & Limitations

**Scope Covered:**
- Backend authentication, authorization, and rate limiting
- Database query patterns for SQL injection
- File upload and ZIP handling
- Encryption implementation
- JWT token handling
- Frontend XSS vectors

**Out of Scope:**
- Infrastructure configuration (Docker, K8s, network security)
- External service integrations (S3/MinIO, Redis)
- Dependent library vulnerabilities (covered by dependabot)
- Testing security (test data exposure)
- API rate limiting at infrastructure layer

---

**Report prepared:** 2026-03-19
**Next audit recommended:** 2026-06-19
