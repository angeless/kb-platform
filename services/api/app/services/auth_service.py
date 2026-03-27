"""Authentication service: register, login, refresh, password reset."""

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import redis.asyncio as aioredis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared_config.settings import Settings
from shared_errors import AppException, ConflictException, ErrorCode, UnauthorizedException
from shared_models import Tenant, User, RefreshToken

from app.utils.security import (
    create_access_token,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)

# Login lockout constants (H-08)
_MAX_LOGIN_ATTEMPTS = 5
_LOCKOUT_SECONDS = 15 * 60  # 15 minutes


class AuthService:
    """Handles registration, login, and token refresh."""

    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis | None:
        """Lazy-connect to Redis. Returns None if unavailable."""
        if self._redis is None:
            try:
                self._redis = aioredis.from_url(self.settings.redis_url)
            except Exception:
                logger.warning("AuthService: Redis unavailable for login lockout")
                return None
        return self._redis

    async def register(
        self, tenant_name: str, email: str, password: str
    ) -> dict:
        """Create a new Tenant + admin User. Raises ConflictException if email exists."""
        result = await self.db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none() is not None:
            raise ConflictException(
                error_code=ErrorCode.AUTH_EMAIL_ALREADY_EXISTS,
                message="邮箱已注册",
            )

        tenant = Tenant(id=uuid.uuid4(), name=tenant_name, status="active")
        self.db.add(tenant)
        await self.db.flush()

        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            email=email,
            password_hash=hash_password(password),
            role="tenant_admin",
            status="active",
        )
        self.db.add(user)
        await self.db.flush()

        return {
            "tenant_id": tenant.id,
            "user_id": user.id,
            "email": user.email,
        }

    # Pre-computed bcrypt dummy hash for timing-attack protection.
    # Ensures verify_password runs even when user doesn't exist.
    _DUMMY_HASH = "$2b$12$LJ3m9ZOH0MkMNQan/GZVqeJUhOHQSEzFR0iEvEfVJmOYEah0jCzGi"

    async def _check_lockout(self, email: str) -> None:
        """Raise 423 if account is locked out. Fail-open if Redis unavailable."""
        r = await self._get_redis()
        if r is None:
            return
        try:
            ttl = await r.ttl(f"login:lockout:{email}")
            if ttl > 0:
                minutes_left = max(1, (ttl + 59) // 60)
                raise AppException(
                    error_code=ErrorCode.AUTH_ACCOUNT_LOCKED,
                    message=f"账户已临时锁定，请 {minutes_left} 分钟后重试",
                    status_code=423,
                )
        except AppException:
            raise
        except Exception:
            logger.warning("Redis lockout check failed, allowing login attempt")

    async def _record_failed_attempt(self, email: str) -> None:
        """Increment failed login counter. Lock account at threshold."""
        r = await self._get_redis()
        if r is None:
            return
        try:
            key = f"login:attempts:{email}"
            count = await r.incr(key)
            if count == 1:
                await r.expire(key, _LOCKOUT_SECONDS)
            if count >= _MAX_LOGIN_ATTEMPTS:
                await r.setex(f"login:lockout:{email}", _LOCKOUT_SECONDS, "1")
                await r.delete(key)
        except Exception:
            logger.warning("Redis failed attempt recording failed")

    async def _clear_login_attempts(self, email: str) -> None:
        """Clear failed login counters on successful login."""
        r = await self._get_redis()
        if r is None:
            return
        try:
            await r.delete(f"login:attempts:{email}", f"login:lockout:{email}")
        except Exception:
            pass

    async def login(self, email: str, password: str) -> dict:
        """Verify credentials and return access + refresh tokens.

        Constant-time: always runs bcrypt verify to prevent user enumeration
        via timing side-channel. Locks account after 5 consecutive failures (H-08).
        """
        # Check lockout before expensive bcrypt work
        await self._check_lockout(email)

        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        # Always run bcrypt verify regardless of user existence
        hash_to_check = user.password_hash if user else self._DUMMY_HASH
        password_valid = verify_password(password, hash_to_check)

        if user is None or not password_valid:
            await self._record_failed_attempt(email)
            raise UnauthorizedException(
                error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                message="邮箱或密码错误",
            )

        await self._clear_login_attempts(email)

        token_data = {
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "role": user.role,
        }

        access_token = create_access_token(
            data=token_data,
            secret=self.settings.jwt_secret,
            algorithm=self.settings.jwt_algorithm,
            expires_minutes=self.settings.access_token_expire_minutes,
        )
        refresh_token = create_access_token(
            data={**token_data, "type": "refresh"},
            secret=self.settings.jwt_secret,
            algorithm=self.settings.jwt_algorithm,
            expires_minutes=self.settings.refresh_token_expire_days * 24 * 60,
        )

        # Store refresh token hash in DB for revocation support
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        rt_record = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=self.settings.refresh_token_expire_days),
        )
        self.db.add(rt_record)
        await self.db.flush()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    async def forgot_password(self, email: str) -> dict:
        """Generate a password reset token for the given email.

        Always returns the same response regardless of whether the email exists,
        to prevent user enumeration attacks.

        In dev mode: returns the raw token in the response for testing.
        In production: would send an email (not yet implemented).
        """
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        # Fixed response message (same whether email exists or not)
        response_message = "如果该邮箱已注册，重置链接已发送"

        if user is None:
            return {"message": response_message}

        # Generate secure random token
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        # Store hash and expiry (1 hour)
        user.reset_token = token_hash
        user.reset_token_expires_at = datetime.now(timezone.utc).replace(
            microsecond=0
        ) + timedelta(hours=1)
        await self.db.flush()

        logger.info("Password reset token generated for user %s", user.id)

        # Only return raw token in development mode (for testing without email service)
        if self.settings.environment == "development":
            return {"message": response_message, "reset_token": raw_token}
        return {"message": response_message}

    async def reset_password(self, token: str, new_password: str) -> dict:
        """Reset a user's password using a valid reset token.

        Validates the token hash match and expiry, then updates the password.
        Token is single-use: cleared after successful reset.
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        result = await self.db.execute(
            select(User).where(
                User.reset_token == token_hash,
                User.reset_token_expires_at > datetime.now(timezone.utc),
            )
        )
        user = result.scalar_one_or_none()

        if user is None:
            raise AppException(
                error_code=ErrorCode.AUTH_RESET_TOKEN_INVALID,
                message="重置链接无效或已过期",
                status_code=400,
            )

        # Update password and clear reset token (single-use)
        user.password_hash = hash_password(new_password)
        user.reset_token = None
        user.reset_token_expires_at = None

        # Revoke all refresh tokens for this user (password changed)
        await self.revoke_all_user_tokens(user.id)
        await self.db.flush()

        logger.info("Password reset successful for user %s", user.id)
        return {"message": "密码重置成功"}

    async def refresh(self, refresh_token: str) -> dict:
        """Validate a refresh token and return a new access token.

        Checks both JWT validity AND database record (not revoked, not expired).
        """
        from app.utils.security import decode_access_token

        try:
            payload = decode_access_token(
                refresh_token,
                self.settings.jwt_secret,
                self.settings.jwt_algorithm,
            )
        except Exception:
            raise UnauthorizedException(
                error_code=ErrorCode.AUTH_REFRESH_TOKEN_INVALID,
                message="刷新令牌无效或已过期",
            )

        if payload.get("type") != "refresh":
            raise UnauthorizedException(
                error_code=ErrorCode.AUTH_REFRESH_TOKEN_INVALID,
                message="令牌类型错误（非刷新令牌）",
            )

        # Check DB record: token must exist, not be revoked, and not expired
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked == False,  # noqa: E712
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
        )
        rt_record = result.scalar_one_or_none()
        if rt_record is None:
            raise UnauthorizedException(
                error_code=ErrorCode.AUTH_REFRESH_TOKEN_INVALID,
                message="刷新令牌已吊销或不存在",
            )

        token_data = {
            "sub": payload["sub"],
            "tenant_id": payload["tenant_id"],
            "role": payload["role"],
        }

        access_token = create_access_token(
            data=token_data,
            secret=self.settings.jwt_secret,
            algorithm=self.settings.jwt_algorithm,
            expires_minutes=self.settings.access_token_expire_minutes,
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
        }

    async def revoke_refresh_token(self, refresh_token: str) -> None:
        """Revoke a specific refresh token (used on logout)."""
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .values(revoked=True)
        )
        await self.db.flush()

    async def revoke_all_user_tokens(self, user_id: uuid.UUID) -> None:
        """Revoke all refresh tokens for a user (used on password change)."""
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked == False)  # noqa: E712
            .values(revoked=True)
        )
        await self.db.flush()
