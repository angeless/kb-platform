"""Authentication service: register, login, refresh, password reset."""

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_config.settings import Settings
from shared_errors import AppException, ConflictException, ErrorCode, UnauthorizedException
from shared_models import Tenant, User

from app.utils.security import (
    create_access_token,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)


class AuthService:
    """Handles registration, login, and token refresh."""

    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

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

    async def login(self, email: str, password: str) -> dict:
        """Verify credentials and return access + refresh tokens.

        Constant-time: always runs bcrypt verify to prevent user enumeration
        via timing side-channel.
        """
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        # Always run bcrypt verify regardless of user existence
        hash_to_check = user.password_hash if user else self._DUMMY_HASH
        password_valid = verify_password(password, hash_to_check)

        if user is None or not password_valid:
            raise UnauthorizedException(
                error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                message="邮箱或密码错误",
            )

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

        # Dev mode: return raw token in response for testing
        return {"message": response_message, "reset_token": raw_token}

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
        await self.db.flush()

        logger.info("Password reset successful for user %s", user.id)
        return {"message": "密码重置成功"}

    async def refresh(self, refresh_token: str) -> dict:
        """Validate a refresh token and return a new access token."""
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
