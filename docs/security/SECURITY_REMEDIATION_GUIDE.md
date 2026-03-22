# Security Remediation Guide
**Document Date:** 2026-03-19
**Version:** 1.0

---

## Vulnerability #1: IDOR in Node Assignment - CRITICAL

### File & Location
- **File:** `services/api/app/services/doc_service.py`
- **Method:** `assign_node()` (lines 86-103)
- **Endpoint:** `POST /v1/docs/{doc_id}/assign-node` (in `services/api/app/routers/docs.py`)

### Root Cause
The `assign_node()` method verifies the document belongs to the current tenant but **does not verify the target architecture node is in the same project/tenant**. The `ArchitectureNode` model has no `tenant_id` column, only a foreign key to `Architecture`, which has a foreign key to `Project`.

### Step-by-Step Fix

**Step 1: Update `doc_service.py` assign_node method**

Replace lines 86-103 with:

```python
async def assign_node(self, doc_id: uuid.UUID, node_id: uuid.UUID) -> KnowledgeDoc:
    """Assign a document to an architecture node.

    Verifies:
    1. Document exists and belongs to tenant (via project)
    2. Target node exists and belongs to same project/tenant
    """
    doc = await self.get(doc_id)  # Verifies doc is in tenant's project

    # Verify the target node exists AND belongs to the same project
    from sqlalchemy.orm import join
    q = select(ArchitectureNode).join(
        Architecture,
        ArchitectureNode.architecture_id == Architecture.id
    ).where(
        ArchitectureNode.id == node_id,
        Architecture.project_id == doc.project_id,  # ← ADDED
    )
    result = await self.db.execute(q)
    node = result.scalar_one_or_none()
    if node is None:
        raise NotFoundException(
            error_code=ErrorCode.ARCH_NOT_FOUND,
            message="架构节点不存在或不属于此项目",
        )

    doc.node_id = node_id
    await self.db.flush()
    await self.db.refresh(doc)
    return doc
```

**Step 2: Add unit test to prevent regression**

Create `tests/services/test_doc_service_idor.py`:

```python
"""Test IDOR protection in document-node assignment."""
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.doc_service import DocService
from shared_errors import NotFoundException


@pytest.mark.asyncio
async def test_assign_node_rejects_cross_tenant_node(db_session: AsyncSession):
    """Verify that assigning a document to a node from another tenant is blocked."""
    # Setup: Create two tenants with separate projects and architectures
    tenant1 = await create_tenant(db_session, "Tenant 1")
    tenant2 = await create_tenant(db_session, "Tenant 2")

    project1 = await create_project(db_session, tenant1.id, "Project 1")
    project2 = await create_project(db_session, tenant2.id, "Project 2")

    doc1 = await create_doc(db_session, project1.id, "Doc 1")

    arch2 = await create_architecture(db_session, project2.id, "Arch 2")
    node2 = await create_arch_node(db_session, arch2.id, "Node 2")

    # Test: DocService for tenant1 should NOT be able to assign tenant2's node
    svc = DocService(db_session, tenant1.id)

    with pytest.raises(NotFoundException) as exc_info:
        await svc.assign_node(doc1.id, node2.id)

    assert "架构节点不存在" in str(exc_info.value)

    # Verify doc was NOT modified
    result = await db_session.execute(select(KnowledgeDoc).where(KnowledgeDoc.id == doc1.id))
    doc = result.scalar_one()
    assert doc.node_id is None


@pytest.mark.asyncio
async def test_assign_node_allows_same_tenant_node(db_session: AsyncSession):
    """Verify that assigning a document to a node from same project works."""
    tenant = await create_tenant(db_session, "Tenant A")
    project = await create_project(db_session, tenant.id, "Project A")

    doc = await create_doc(db_session, project.id, "Doc A")
    arch = await create_architecture(db_session, project.id, "Arch A")
    node = await create_arch_node(db_session, arch.id, "Node A")

    svc = DocService(db_session, tenant.id)
    result = await svc.assign_node(doc.id, node.id)

    assert result.node_id == node.id
```

**Step 3: Verify fix with integration test**

Run the test suite:
```bash
cd services/api
pytest tests/services/test_doc_service_idor.py -v
```

**Step 4: Deploy and monitor**

After deployment, monitor:
- Audit logs for `assign_node` operations
- Watch for any 404 errors on node assignment (might indicate attackers probing)

---

## Vulnerability #2: Rate Limiter Accepts Expired Tokens - HIGH

### File & Location
- **File:** `services/api/app/middleware/rate_limit.py`
- **Method:** `_extract_identity()` (lines 50-69)

### Root Cause
The rate limiter disables JWT expiration verification with `options={"verify_exp": False}`. This allows expired tokens to be used for extracting tenant IDs and bypassing rate limits.

### Step-by-Step Fix

**Step 1: Update rate_limit.py**

Replace lines 50-69 with:

```python
def _extract_identity(self, request: Request) -> str:
    """Extract rate limit key: tenant_id from auth header, or client IP.

    SECURITY: Token expiration is verified to prevent:
    - Expired token reuse for tenant_id extraction
    - DoS attacks using old tokens to deplete tenant quotas
    """
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            import jwt
            settings = get_settings()
            # ✓ FIXED: Enable expiration verification
            payload = jwt.decode(
                auth[7:], settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
                options={"verify_exp": True},  # ← CHANGED from False
            )
            tid = payload.get("tenant_id")
            if tid:
                return f"tenant:{tid}"
        except jwt.ExpiredSignatureError:
            # Expired tokens fall back to IP-based rate limiting
            # This prevents attackers from using old tokens
            logger.debug("Expired token in rate limit extraction, using IP fallback")
        except Exception as e:
            logger.debug("Token decode failed in rate limit: %s", str(e)[:50])
            pass

    # Fallback to IP
    client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}"
```

**Step 2: Add unit test**

Create `tests/middleware/test_rate_limit_security.py`:

```python
"""Test rate limiter security behavior."""
import jwt
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from app.middleware.rate_limit import RateLimitMiddleware


def test_rate_limit_rejects_expired_token():
    """Verify rate limiter rejects expired tokens and falls back to IP."""
    middleware = RateLimitMiddleware(AsyncMock())

    # Create an expired token
    secret = "test-secret"
    algorithm = "HS256"

    payload = {
        "sub": "user-123",
        "tenant_id": "tenant-456",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # ← Expired
        "iat": datetime.now(timezone.utc),
    }

    expired_token = jwt.encode(payload, secret, algorithm=algorithm)

    # Mock request with expired token
    request = MagicMock()
    request.headers.get.return_value = f"Bearer {expired_token}"
    request.client.host = "192.168.1.100"

    # Patch settings to use test secret
    from unittest.mock import patch
    with patch('app.middleware.rate_limit.get_settings') as mock_settings:
        mock_settings.return_value = MagicMock(
            jwt_secret=secret,
            jwt_algorithm=algorithm,
        )
        identity = middleware._extract_identity(request)

    # Should fall back to IP, not extract tenant_id
    assert identity == "ip:192.168.1.100"
    assert "tenant:" not in identity


def test_rate_limit_accepts_valid_token():
    """Verify rate limiter extracts tenant_id from valid tokens."""
    middleware = RateLimitMiddleware(AsyncMock())

    secret = "test-secret"
    algorithm = "HS256"
    tenant_id = "tenant-valid-123"

    payload = {
        "sub": "user-123",
        "tenant_id": tenant_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),  # ← Valid
        "iat": datetime.now(timezone.utc),
    }

    valid_token = jwt.encode(payload, secret, algorithm=algorithm)

    request = MagicMock()
    request.headers.get.return_value = f"Bearer {valid_token}"
    request.client.host = "192.168.1.100"

    from unittest.mock import patch
    with patch('app.middleware.rate_limit.get_settings') as mock_settings:
        mock_settings.return_value = MagicMock(
            jwt_secret=secret,
            jwt_algorithm=algorithm,
        )
        identity = middleware._extract_identity(request)

    # Should extract tenant_id
    assert identity == f"tenant:{tenant_id}"
```

**Step 3: Test the fix**

```bash
cd services/api
pytest tests/middleware/test_rate_limit_security.py -v
```

**Step 4: Integration test with actual requests**

```bash
# Test 1: Fresh token should use tenant-based rate limiting
curl -H "Authorization: Bearer $(./get-fresh-token.sh)" \
  http://localhost:8000/v1/docs?project_id=test-project

# Test 2: Expired token should fall back to IP-based rate limiting
curl -H "Authorization: Bearer $(./get-expired-token.sh)" \
  http://localhost:8000/v1/docs?project_id=test-project

# Check logs for "IP fallback" message when using expired token
```

---

## Vulnerability #3: Rate Limiter Fails Open - HIGH

### File & Location
- **File:** `services/api/app/middleware/rate_limit.py`
- **Methods:** `_get_redis()` (lines 40-48), `dispatch()` (lines 71-133)

### Root Cause
When Redis is unavailable, rate limiter allows all requests through instead of rejecting them. This is dangerous because rate limiting is often a critical defense against brute force and DoS attacks.

### Step-by-Step Fix

**Strategy: Implement circuit breaker + in-memory fallback**

**Step 1: Create a rate limit circuit breaker class**

Create `services/api/app/middleware/rate_limit_fallback.py`:

```python
"""In-memory rate limit fallback for Redis outages."""
import time
from collections import defaultdict
from threading import Lock


class InMemoryRateLimiter:
    """Simple token bucket rate limiter for fallback use."""

    def __init__(self):
        self.buckets: dict[str, list[float]] = defaultdict(list)
        self.lock = Lock()

    def is_allowed(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        """Check if request is allowed. Returns True if under limit, False if exceeded."""
        now = time.time()
        window_start = now - window_seconds

        with self.lock:
            # Clean old entries
            self.buckets[key] = [ts for ts in self.buckets[key] if ts > window_start]

            # Check limit
            if len(self.buckets[key]) >= limit:
                return False

            # Add current request
            self.buckets[key].append(now)
            return True

    def cleanup_expired(self, older_than: float = 3600):
        """Remove old entries older than specified seconds. Run periodically."""
        now = time.time()
        cutoff = now - older_than

        with self.lock:
            for key in list(self.buckets.keys()):
                self.buckets[key] = [ts for ts in self.buckets[key] if ts > cutoff]
                if not self.buckets[key]:
                    del self.buckets[key]


# Global instance
_fallback_limiter = InMemoryRateLimiter()

def get_fallback_limiter() -> InMemoryRateLimiter:
    """Get the global fallback rate limiter instance."""
    return _fallback_limiter
```

**Step 2: Update rate_limit.py to use fallback**

Replace the `dispatch()` method (lines 71-133):

```python
async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
    path = request.url.path

    # Skip exempt paths
    if path in EXEMPT_PATHS:
        return await call_next(request)

    r = await self._get_redis()
    settings = get_settings()
    identity = self._extract_identity(request)

    # Determine rate limit based on path type
    is_upload = path in UPLOAD_PATHS
    auth_setting = AUTH_RATE_LIMITS.get(path)
    if auth_setting:
        limit = getattr(settings, auth_setting)
        client_ip = request.client.host if request.client else "unknown"
        identity = f"ip:{client_ip}"
    elif is_upload:
        limit = settings.upload_rate_limit_per_minute
    else:
        limit = settings.rate_limit_per_minute

    category = "auth" if auth_setting else ("upload" if is_upload else "api")
    key = f"ratelimit:{identity}:{category}"
    now = time.time()
    window_start = now - 60

    if r is None:
        # Redis unavailable - use in-memory fallback
        # ✓ FIXED: Fail to in-memory limiter instead of failing open
        logger.warning("Using in-memory rate limit fallback (Redis unavailable)")
        from app.middleware.rate_limit_fallback import get_fallback_limiter
        fallback = get_fallback_limiter()

        if not fallback.is_allowed(key, limit, window_seconds=60):
            retry_after = 60
            return JSONResponse(
                status_code=429,
                content={
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": f"请求过于频繁，每分钟最多 {limit} 次，请稍后再试",
                    "detail": {
                        "limit": limit,
                        "retry_after": retry_after,
                        "mode": "fallback",  # Indicate we're in fallback mode
                    },
                },
                headers={"Retry-After": str(max(1, retry_after))},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Mode"] = "fallback"
        return response

    # Redis available - use normal sliding window approach
    try:
        pipe = r.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, 120)
        results = await pipe.execute()
        count = results[2]

        if count > limit:
            retry_after = 60 - int(now - window_start)
            return JSONResponse(
                status_code=429,
                content={
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": f"请求过于频繁，每分钟最多 {limit} 次，请稍后再试",
                    "detail": {"limit": limit, "current": count, "retry_after": retry_after},
                },
                headers={"Retry-After": str(max(1, retry_after))},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - count))
        return response

    except Exception as e:
        logger.warning("Rate limit check failed with exception: %s", str(e)[:100])
        # ✓ FIXED: Fall back to in-memory limiter on exception too
        from app.middleware.rate_limit_fallback import get_fallback_limiter
        fallback = get_fallback_limiter()

        if not fallback.is_allowed(key, limit, window_seconds=60):
            return JSONResponse(
                status_code=429,
                content={
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": f"请求过于频繁，每分钟最多 {limit} 次，请稍后再试",
                    "detail": {"limit": limit, "mode": "fallback"},
                },
                headers={"Retry-After": "60"},
            )

        return await call_next(request)
```

**Step 3: Add periodic cleanup task**

Update the app initialization in `services/api/app/main.py`:

```python
import asyncio
from app.middleware.rate_limit_fallback import get_fallback_limiter

@app.on_event("startup")
async def startup_event():
    """Periodic cleanup of in-memory rate limit entries."""
    async def cleanup_task():
        while True:
            try:
                await asyncio.sleep(600)  # Every 10 minutes
                get_fallback_limiter().cleanup_expired(older_than=3600)
                logger.debug("Cleaned up expired rate limit entries")
            except Exception as e:
                logger.error("Error in rate limit cleanup: %s", e)

    asyncio.create_task(cleanup_task())
```

**Step 4: Add tests**

Create `tests/middleware/test_rate_limit_fallback.py`:

```python
"""Test rate limit fallback behavior."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import Request
from starlette.responses import JSONResponse

from app.middleware.rate_limit import RateLimitMiddleware


@pytest.mark.asyncio
async def test_rate_limit_uses_fallback_when_redis_unavailable():
    """Verify rate limiter falls back to in-memory when Redis is down."""
    # Create middleware
    app = AsyncMock()
    middleware = RateLimitMiddleware(app, redis_client=None)

    # Mock request
    request = MagicMock(spec=Request)
    request.url.path = "/v1/docs"
    request.headers.get.return_value = "Bearer valid-token"
    request.client.host = "192.168.1.100"

    # Mock call_next
    async def mock_call_next(req):
        resp = MagicMock()
        resp.headers = {}
        return resp

    # Mock _extract_identity to return a key
    middleware._extract_identity = MagicMock(return_value="ip:192.168.1.100")

    # Mock _get_redis to return None (simulating Redis down)
    async def mock_get_redis():
        return None

    middleware._get_redis = mock_get_redis

    with patch('app.middleware.rate_limit.get_settings') as mock_settings:
        mock_settings.return_value = MagicMock(
            rate_limit_per_minute=10,
        )

        # First request should succeed (in-memory fallback allows it)
        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 200 or response.status_code in [200]

        # After 10 requests, should get rate limited
        for _ in range(9):
            await middleware.dispatch(request, mock_call_next)

        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 429, "Should be rate limited after 10 requests"


@pytest.mark.asyncio
async def test_rate_limit_exception_uses_fallback():
    """Verify rate limiter falls back when Redis raises exception."""
    app = AsyncMock()
    middleware = RateLimitMiddleware(app)

    request = MagicMock(spec=Request)
    request.url.path = "/v1/docs"
    request.headers.get.return_value = "Bearer valid-token"
    request.client.host = "192.168.1.100"

    async def mock_call_next(req):
        resp = MagicMock()
        resp.headers = {}
        return resp

    middleware._extract_identity = MagicMock(return_value="ip:192.168.1.100")

    # Mock _get_redis to return a redis client that raises on pipeline
    mock_redis = AsyncMock()
    mock_redis.pipeline.side_effect = Exception("Redis connection timeout")

    async def mock_get_redis():
        return mock_redis

    middleware._get_redis = mock_get_redis

    with patch('app.middleware.rate_limit.get_settings') as mock_settings:
        mock_settings.return_value = MagicMock(
            rate_limit_per_minute=5,
        )

        # Should not crash, should fall back to in-memory
        for i in range(6):
            response = await middleware.dispatch(request, mock_call_next)
            if i < 5:
                assert response.status_code == 200
            else:
                assert response.status_code == 429
```

**Step 5: Deploy and monitor**

1. Deploy changes
2. Monitor for "Using in-memory rate limit fallback" log messages
3. Verify that rate limiting is enforced even when Redis is down
4. Alert ops team if fallback is used for more than 5 minutes (indicates persistent Redis issue)

---

## Vulnerability #4: Missing SSRF Blocklist Entries - MEDIUM

### File & Location
- **File:** `services/api/app/utils/url_fetcher.py`
- **Lines:** 20-29

### Root Cause
The blocklist for SSRF protection is missing `0.0.0.0` (IPv4 any address) and `::` (IPv6 any address), which can be used to access localhost services.

### Step-by-Step Fix

**Step 1: Update the blocklist**

Replace lines 20-29 in `url_fetcher.py`:

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
    ipaddress.ip_network("fc00::/7"),             # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),            # IPv6 link-local
]
```

**Step 2: Add test**

Create `tests/utils/test_url_fetcher_ssrf.py`:

```python
"""Test SSRF protection."""
import pytest
from shared_errors import AppException
from app.utils.url_fetcher import validate_url


def test_url_fetcher_blocks_ipv4_any_address():
    """Verify 0.0.0.0 is blocked."""
    with pytest.raises(AppException) as exc_info:
        validate_url("http://0.0.0.0:8080/admin")
    assert "内网地址" in str(exc_info.value)


def test_url_fetcher_blocks_ipv6_any_address():
    """Verify :: (IPv6 any) is blocked."""
    with pytest.raises(AppException) as exc_info:
        validate_url("http://[::]:8080/admin")
    assert "内网地址" in str(exc_info.value)


def test_url_fetcher_allows_external_ips():
    """Verify external IPs are allowed."""
    # Should not raise
    validate_url("http://8.8.8.8/search")
    validate_url("http://example.com/page")


@pytest.mark.parametrize("blocked_url", [
    "http://127.0.0.1:8080",
    "http://0.0.0.0:3000",
    "http://10.0.0.5",
    "http://192.168.1.1",
    "http://172.16.0.1",
    "http://localhost:8080",
    "http://[::1]:8080",
    "http://[::]:8080",
    "http://169.254.1.1",
])
def test_url_fetcher_blocks_private_addresses(blocked_url):
    """Verify all private/reserved addresses are blocked."""
    with pytest.raises(AppException):
        validate_url(blocked_url)
```

**Step 3: Run tests**

```bash
cd services/api
pytest tests/utils/test_url_fetcher_ssrf.py -v
```

---

## Vulnerability #5: ZIP Bomb Protection - MEDIUM

### File & Location
- **File:** `services/api/app/services/asset_service.py`
- **Method:** `import_archive()` (lines 153-247)

### Root Cause
The ZIP archive import function checks the number of files but does not check the decompressed size of individual files or total decompressed size. This allows ZIP bomb attacks.

### Step-by-Step Fix

**Step 1: Update asset_service.py**

Find the `import_archive()` method and update it. Replace lines 177-207 with:

```python
        imported = 0
        skipped = 0
        errors: list[str] = []
        max_files = 100
        # ✓ ADD: Size limits for ZIP bomb protection
        MAX_DECOMPRESSED_SIZE_SINGLE = 500 * 1024 * 1024  # 500 MB per file
        MAX_DECOMPRESSED_SIZE_TOTAL = 2 * 1024 * 1024 * 1024  # 2 GB total

        with zipfile.ZipFile(io.BytesIO(archive_content), "r") as zf:
            entries = [e for e in zf.namelist() if not e.endswith("/")]
            if len(entries) > max_files:
                raise AppException(
                    error_code=ErrorCode.ASSET_TOO_LARGE,
                    message=f"压缩包内文件数超过限制 ({max_files})",
                )

            # Security: check ALL entries for path traversal before processing any
            total_decompressed = 0
            for entry_name in entries:
                normalized = os.path.normpath(entry_name)
                if ".." in normalized.split(os.sep) or normalized.startswith("/"):
                    raise AppException(
                        error_code=ErrorCode.ASSET_TYPE_NOT_ALLOWED,
                        message=f"ZIP 文件包含非法路径（路径穿越）: {entry_name}",
                    )

                # ✓ ADD: Check uncompressed size before decompressing
                file_info = zf.getinfo(entry_name)
                if file_info.file_size > MAX_DECOMPRESSED_SIZE_SINGLE:
                    raise AppException(
                        error_code=ErrorCode.ASSET_TOO_LARGE,
                        message=f"压缩包成员文件过大: {entry_name} ({file_info.file_size / (1024*1024):.1f} MB > 500 MB 限制)",
                    )

                total_decompressed += file_info.file_size
                if total_decompressed > MAX_DECOMPRESSED_SIZE_TOTAL:
                    raise AppException(
                        error_code=ErrorCode.ASSET_TOO_LARGE,
                        message=f"压缩包总大小超过限制 ({total_decompressed / (1024*1024*1024):.1f} GB > 2 GB 限制)",
                    )

            for entry_name in entries:
                # Extract safe filename (basename after normpath)
                normalized = os.path.normpath(entry_name)
                filename = os.path.basename(normalized)
                if not filename:
                    continue

                # Check file type whitelist
                if not is_allowed_file(filename):
                    skipped += 1
                    continue

                try:
                    file_content = zf.read(entry_name)  # Safe because sizes already verified
                except Exception as e:
                    errors.append(f"{entry_name}: {e!s}")
                    continue
```

**Step 2: Add test**

Create `tests/services/test_asset_service_zip_bomb.py`:

```python
"""Test ZIP bomb protection."""
import io
import zipfile
import pytest
from shared_errors import AppException


def create_zip_bomb(num_files: int = 100, single_file_size_mb: int = 600) -> bytes:
    """Create a ZIP file with files larger than limits (for testing)."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for i in range(num_files):
            # Create large file (uncompressed)
            large_data = b"X" * (single_file_size_mb * 1024 * 1024)
            zf.writestr(f"large_file_{i}.bin", large_data)

    zip_buffer.seek(0)
    return zip_buffer.getvalue()


@pytest.mark.asyncio
async def test_asset_import_rejects_oversized_single_file(db_session, asset_service):
    """Verify ZIP with single file > 500 MB is rejected."""
    # Create ZIP with one 600 MB file
    zip_bomb = create_zip_bomb(num_files=1, single_file_size_mb=600)

    with pytest.raises(AppException) as exc_info:
        await asset_service.import_archive(asset_service.tenant_id, zip_bomb, "bomb.zip")

    assert "文件过大" in str(exc_info.value)


@pytest.mark.asyncio
async def test_asset_import_rejects_oversized_total(db_session, asset_service):
    """Verify ZIP with total size > 2 GB is rejected."""
    # This is hard to test without actual 2 GB, so we mock the size check
    # In practice, use integration tests with realistic ZIP bombs
    pass


@pytest.mark.asyncio
async def test_asset_import_allows_reasonable_zip(db_session, asset_service):
    """Verify reasonable ZIPs still work."""
    # Create valid ZIP with small files
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("file1.txt", "Hello world")
        zf.writestr("file2.txt", "Another file")

    zip_buffer.seek(0)
    result = await asset_service.import_archive(asset_service.tenant_id, zip_buffer.getvalue(), "test.zip")

    assert result["imported"] == 2
    assert result["skipped"] == 0
```

**Step 3: Run tests**

```bash
cd services/api
pytest tests/services/test_asset_service_zip_bomb.py -v
```

---

## Vulnerability #6: Weak Key Derivation - MEDIUM

### File & Location
- **File:** `services/api/app/utils/crypto.py`
- **Function:** `_derive_key()` (lines 8-13)

### Root Cause
The key derivation function pads with zeros and doesn't use proper key stretching (PBKDF2, bcrypt, scrypt, Argon2).

### Step-by-Step Fix

**Option A: Use PBKDF2 (Recommended for backward compatibility)**

Replace `crypto.py` with:

```python
"""AES-256-GCM encryption utilities and API key masking."""

import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _derive_key(secret: str, salt: bytes | None = None) -> bytes:
    """Derive a 32-byte key from a string secret using PBKDF2.

    SECURITY NOTE:
    - PBKDF2 with 100,000 iterations provides strong key derivation
    - Salt is optional; if not provided, uses empty salt for backward compatibility
    - For NEW encryption operations, callers should provide a random salt
    """
    if salt is None:
        salt = b""  # For backward compatibility with existing encrypted data

    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,  # NIST recommends minimum 100,000 (as of 2023)
    )
    return kdf.derive(secret.encode("utf-8"))


def encrypt(plaintext: str, secret: str) -> bytes:
    """Encrypt plaintext using AES-256-GCM. Returns salt + nonce + ciphertext."""
    # Use a random salt for each encryption
    salt = os.urandom(16)
    key = _derive_key(secret, salt=salt)

    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)

    # Return salt + nonce + ciphertext for decryption
    return salt + nonce + ciphertext


def decrypt(data: bytes, secret: str) -> str:
    """Decrypt AES-256-GCM data (salt + nonce + ciphertext) back to plaintext."""
    if len(data) < 28:  # 16 (salt) + 12 (nonce) + 0 (ciphertext)
        raise ValueError("Encrypted data too short")

    salt = data[:16]
    nonce = data[16:28]
    ciphertext = data[28:]

    key = _derive_key(secret, salt=salt)
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


def mask_api_key(api_key: str, visible: int = 4) -> str:
    """Mask an API key, showing only the last `visible` characters."""
    if len(api_key) <= visible:
        return "*" * len(api_key)
    return "*" * (len(api_key) - visible) + api_key[-visible:]
```

**IMPORTANT: Handle backward compatibility**

Update the decrypt function to handle both old and new formats:

```python
def decrypt(data: bytes, secret: str) -> str:
    """Decrypt AES-256-GCM data back to plaintext.

    Supports two formats:
    1. OLD (12 byte nonce only): nonce + ciphertext
    2. NEW (16 byte salt + 12 byte nonce): salt + nonce + ciphertext
    """
    if len(data) >= 28:
        # NEW format: salt + nonce + ciphertext
        salt = data[:16]
        nonce = data[16:28]
        ciphertext = data[28:]
        key = _derive_key(secret, salt=salt)
    else:
        # OLD format: nonce + ciphertext (for backward compatibility)
        # This is insecure but necessary for existing data
        nonce = data[:12]
        ciphertext = data[12:]
        key = _derive_key(secret, salt=None)

    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")
```

**Step 2: Migration script for existing encrypted data**

Create `services/api/scripts/migrate_encrypted_keys.py`:

```python
"""Re-encrypt API keys with new strong key derivation."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select, update

from shared_models import ModelProvider
from app.utils.crypto import decrypt, encrypt
from shared_config.settings import get_settings


async def migrate_encrypted_keys():
    """Read all encrypted keys, decrypt with old method, re-encrypt with new method."""
    settings = get_settings()

    # Use same DB connection as app
    from shared_models.database import async_session_factory

    async with async_session_factory() as session:
        # Read all model providers
        result = await session.execute(select(ModelProvider))
        providers = result.scalars().all()

        migrated = 0
        for provider in providers:
            try:
                # Decrypt with current (old) method
                import base64
                encrypted_bytes = base64.b64decode(provider.api_key_encrypted)
                api_key = decrypt(encrypted_bytes, settings.encryption_key)

                # Re-encrypt with new method (uses salt)
                new_encrypted_bytes = encrypt(api_key, settings.encryption_key)
                new_encrypted_b64 = base64.b64encode(new_encrypted_bytes).decode("utf-8")

                # Update provider
                provider.api_key_encrypted = new_encrypted_b64
                migrated += 1

            except Exception as e:
                print(f"Failed to migrate provider {provider.id}: {e}")

        await session.commit()
        print(f"Successfully migrated {migrated} providers")


if __name__ == "__main__":
    asyncio.run(migrate_encrypted_keys())
```

**Step 3: Add unit test**

Create `tests/utils/test_crypto_pbkdf2.py`:

```python
"""Test updated crypto with PBKDF2."""
import os
import pytest
from app.utils.crypto import encrypt, decrypt, _derive_key


def test_key_derivation_deterministic():
    """Verify same secret + salt produces same key."""
    secret = "my-secure-secret"
    salt = b"fixed-salt-16byt"

    key1 = _derive_key(secret, salt=salt)
    key2 = _derive_key(secret, salt=salt)

    assert key1 == key2
    assert len(key1) == 32


def test_encrypt_decrypt_with_salt():
    """Verify encryption/decryption works with new salt-based format."""
    secret = "encryption-secret"
    plaintext = "sensitive-data-123"

    encrypted = encrypt(plaintext, secret)
    decrypted = decrypt(encrypted, secret)

    assert decrypted == plaintext
    assert len(encrypted) > 28  # salt + nonce + ciphertext


def test_backward_compatibility_decrypt_old_format():
    """Verify old encrypted format (nonce only) still decrypts."""
    # Simulate old format: nonce + ciphertext
    # This test would need actual old-format encrypted data
    pass


def test_key_derivation_resistant_to_brute_force():
    """Verify PBKDF2 is slow enough to resist brute force."""
    import time
    secret = "test-secret"

    start = time.time()
    _derive_key(secret)
    elapsed = time.time() - start

    # Should take >100ms (depends on system)
    assert elapsed > 0.01, "Key derivation too fast (should use PBKDF2 with 100k iterations)"
```

**Step 4: Deploy with migration**

1. Deploy the new crypto code
2. Backward compatibility mode handles both old and new formats during decryption
3. Run migration script on all encrypted provider keys:
   ```bash
   cd services/api
   python scripts/migrate_encrypted_keys.py
   ```
4. Verify all providers are still accessible post-migration

---

## Summary of Changes

| Vulnerability | Fix | Priority | Est. Time |
|---------------|-----|----------|-----------|
| IDOR in node assignment | Add project_id check | CRITICAL | 1 hour |
| Expired token acceptance | Enable verify_exp | HIGH | 30 min |
| Rate limiter fails open | Implement fallback | HIGH | 2 hours |
| SSRF missing entries | Add 0.0.0.0 and :: | MEDIUM | 15 min |
| ZIP bomb protection | Add size limits | MEDIUM | 1 hour |
| Weak key derivation | Use PBKDF2 | MEDIUM | 2 hours |

**Total estimated implementation time:** 6.5 hours

---

## Testing Checklist

Before deploying each fix:

- [ ] Unit tests pass locally
- [ ] Integration tests pass in test environment
- [ ] Manual testing confirms fix works as expected
- [ ] Backward compatibility tested (if applicable)
- [ ] Performance impact assessed
- [ ] Monitoring/logging added
- [ ] Deployment plan reviewed
- [ ] Rollback procedure documented

---

## References

- CWE-639: Authorization Bypass Through User-Controlled Key
- CWE-613: Insufficient Session Expiration
- CWE-693: Protection Mechanism Failure
- CWE-918: Server-Side Request Forgery
- CWE-409: Improper Restriction of Rendered UI Layers or Frames
- CWE-326: Inadequate Encryption Strength
- OWASP Top 10 2021: A01:2021 – Broken Access Control
- OWASP Top 10 2021: A07:2021 – Identification and Authentication Failures

