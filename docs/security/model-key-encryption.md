# Model API Key Encryption Scheme

**Version:** v0.47.7
**Date:** 2026-04-03

## Overview

Model provider API keys (e.g., OpenAI, Azure) are stored encrypted at rest in the `model_provider.api_key_encrypted` column using AES-256-GCM with PBKDF2 key derivation.

## Encryption Details

| Property | Value |
|----------|-------|
| Algorithm | AES-256-GCM |
| Key derivation | PBKDF2-HMAC-SHA256 |
| Iterations | 100,000 |
| Salt | 16 bytes, random per encryption (KDF2 format) |
| Nonce | 12 bytes, random per encryption |
| Master secret | `ENCRYPTION_KEY` environment variable (min 32 chars in production) |

### Wire Format

```
KDF2(4B) + salt(16B) + nonce(12B) + ciphertext(variable)
```

The result is base64-encoded before storing in PostgreSQL.

### Implementation

- Encrypt: `services/api/app/utils/crypto.py::encrypt()`
- Decrypt: `services/api/app/utils/crypto.py::decrypt()`
- Service: `services/api/app/services/model_provider_service.py`

### Legacy Format Support

The `decrypt()` function supports three formats for backward compatibility:
1. **KDF2** (current): random salt + PBKDF2
2. **KDF1** (legacy v1): deterministic salt + PBKDF2
3. **Legacy**: padded key, no KDF

New encryptions always use KDF2.

## Key Management

| Concern | Implementation |
|---------|---------------|
| Master secret storage | `ENCRYPTION_KEY` env var, validated non-default in production |
| Key rotation (provider keys) | `POST /v1/model-providers/{id}/rotate-key` (tenant_admin) |
| Key rotation (master secret) | Requires re-encryption migration (not automated) |
| Access control | tenant_admin role required for create/rotate operations |
| Audit trail | All create/rotate operations logged to `audit_log` table |

## Key Rotation Flow

1. Admin calls `POST /v1/model-providers/{provider_id}/rotate-key` with `{"new_api_key": "sk-..."}`.
2. Server encrypts the new key using `encrypt()` (AES-256-GCM, KDF2 format).
3. `api_key_encrypted` column is atomically updated.
4. Old key is immediately invalidated — next LLM call uses the new key.
5. Rotation event is written to `audit_log` (action: `rotate_key`).

## Security Constraints

- API keys are never returned in plaintext via API responses (masked to `****XXXX`).
- `ENCRYPTION_KEY` must be at least 32 characters in production (enforced by settings validator).
- Production rejects default encryption key values at startup.
