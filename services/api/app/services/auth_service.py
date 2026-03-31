"""Authentication service: register, login, refresh via PA Pass."""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from shared_config.settings import Settings
from shared_errors import AppException, ErrorCode, UnauthorizedException
from shared_models import Tenant, User

from app.services.pass_client import PassClient

logger = logging.getLogger(__name__)


class AuthService:
    """Handles registration, login, and token refresh via PA Pass."""

    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self._pass = PassClient(settings)

    async def register(self, email: str, password: str, display_name: str = "") -> dict:
        """Register via Pass, auto-create KB Tenant + User, return Pass token."""
        pass_resp = await self._pass.register(email, password, display_name)

        pass_id = pass_resp["passId"]
        token = pass_resp["token"]
        expires_at = pass_resp.get("expiresAt")

        # Create KB Tenant + User
        tenant = Tenant(id=uuid.uuid4(), name=display_name or email, status="active")
        self.db.add(tenant)
        await self.db.flush()

        user = User(
            id=uuid.uuid4(),
            kb_id=tenant.id,
            pass_id=pass_id,
            email=email,
            password_hash=None,
            role="tenant_admin",
            status="active",
        )
        self.db.add(user)
        await self.db.flush()

        return {
            "access_token": token,
            "expires_at": expires_at,
            "kb_id": str(tenant.id),
            "user_id": str(user.id),
            "email": email,
        }

    async def login(self, email: str, password: str) -> dict:
        """Login via Pass, auto-provision KB User on first login, return Pass token."""
        pass_resp = await self._pass.login(email, password)

        pass_id = pass_resp["passId"]
        token = pass_resp["token"]
        expires_at = pass_resp.get("expiresAt")

        # Look up or auto-create KB User
        user = await self._get_or_create_user(pass_id, email)

        return {
            "access_token": token,
            "expires_at": expires_at,
            "kb_id": str(user.kb_id),
            "user_id": str(user.id),
        }

    async def refresh(self, current_token: str) -> dict:
        """Refresh Pass token by proxying to Pass /refresh."""
        pass_resp = await self._pass.refresh(current_token)
        return {
            "access_token": pass_resp["token"],
            "expires_at": pass_resp.get("expiresAt"),
        }

    async def verify_token(self, token: str) -> User:
        """Verify Pass token via GET /pass/me, return KB User.

        Called by get_current_user() dependency on every request.
        Network errors are handled by PassClient._request (raises 502).
        """
        pass_info = await self._pass.me(token)
        pass_id = pass_info["passId"]

        result = await self.db.execute(select(User).where(User.pass_id == pass_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise UnauthorizedException(
                error_code=ErrorCode.AUTH_TOKEN_INVALID,
                message="用户未在 KB 平台注册",
            )

        return user

    async def _get_or_create_user(self, pass_id: str, email: str) -> User:
        """Find existing User by pass_id, or auto-create Tenant + User on first login.

        Handles race condition: if two concurrent logins try to create the same
        user, the unique index on pass_id causes one to fail with IntegrityError.
        We catch that and retry the SELECT.
        """
        result = await self.db.execute(select(User).where(User.pass_id == pass_id))
        user = result.scalar_one_or_none()
        if user is not None:
            return user

        # First Pass login → auto-provision
        try:
            tenant = Tenant(id=uuid.uuid4(), name=email, status="active")
            self.db.add(tenant)
            await self.db.flush()

            user = User(
                id=uuid.uuid4(),
                kb_id=tenant.id,
                pass_id=pass_id,
                email=email,
                password_hash=None,
                role="tenant_admin",
                status="active",
            )
            self.db.add(user)
            await self.db.flush()
        except IntegrityError:
            # Concurrent request already created this user — rollback and re-fetch
            await self.db.rollback()
            result = await self.db.execute(select(User).where(User.pass_id == pass_id))
            user = result.scalar_one_or_none()
            if user is None:
                raise  # Unexpected — re-raise the original error
            logger.info("Concurrent auto-provision resolved for pass_id=%s", pass_id)
            return user

        logger.info("Auto-provisioned KB user for pass_id=%s email=%s", pass_id, email)
        return user
