"""HTTP client for PA Pass (central authentication) API."""

import logging

import httpx

from shared_config.settings import Settings
from shared_errors import (
    AppException,
    ConflictException,
    ErrorCode,
    ForbiddenException,
    UnauthorizedException,
)

logger = logging.getLogger(__name__)

# PA error codes
_PA_ACCOUNT_NOT_FOUND = "PA-7001"
_PA_ALREADY_REGISTERED = "PA-7003"
_PA_ACCOUNT_BANNED = "PA-7004"


class PassClient:
    """Thin wrapper around PA Pass REST API."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.pass_base_url.rstrip("/")
        self._product_id = settings.kb_product_id
        self._timeout = 10.0

    async def login(self, email: str, password: str) -> dict:
        """POST /api/v1/pass/login → { passId, token, expiresAt, productBindings }"""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/api/v1/pass/login",
                json={"productId": self._product_id, "email": email, "password": password},
            )
        return self._handle_response(resp, context="login")

    async def register(self, email: str, password: str, display_name: str = "") -> dict:
        """POST /api/v1/pass/register → { passId, token, expiresAt, productBinding }"""
        body: dict = {
            "productId": self._product_id,
            "email": email,
            "password": password,
        }
        if display_name:
            body["displayName"] = display_name
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._base_url}/api/v1/pass/register", json=body)
        return self._handle_response(resp, context="register")

    async def refresh(self, token: str) -> dict:
        """POST /api/v1/pass/refresh → { token, expiresAt }"""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/api/v1/pass/refresh",
                headers={"Authorization": f"Bearer {token}"},
            )
        return self._handle_response(resp, context="refresh")

    async def me(self, token: str) -> dict:
        """GET /api/v1/pass/me → { passId, email, phone, displayName, avatarUrl, productBindings }"""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{self._base_url}/api/v1/pass/me",
                headers={"Authorization": f"Bearer {token}"},
            )
        return self._handle_response(resp, context="me")

    def _handle_response(self, resp: httpx.Response, context: str) -> dict:
        """Map Pass HTTP responses to KB exceptions."""
        if resp.status_code in (200, 201):
            return resp.json()

        # Try to extract PA error code from response body
        pa_code = ""
        message = ""
        try:
            body = resp.json()
            pa_code = body.get("errorCode", body.get("code", ""))
            message = body.get("message", "")
        except Exception:
            pass

        if pa_code == _PA_ACCOUNT_BANNED or resp.status_code == 403:
            raise ForbiddenException(
                error_code=ErrorCode.AUTH_ACCOUNT_BANNED,
                message="账号已被封禁，请联系管理员",
            )

        if pa_code == _PA_ALREADY_REGISTERED or resp.status_code == 409:
            raise ConflictException(
                error_code=ErrorCode.AUTH_EMAIL_ALREADY_EXISTS,
                message="邮箱已注册",
            )

        if resp.status_code == 401:
            raise UnauthorizedException(
                error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                message="邮箱或密码错误" if context == "login" else "令牌无效或已过期",
            )

        # Unexpected error from Pass
        logger.error("Pass API %s error: status=%s pa_code=%s msg=%s", context, resp.status_code, pa_code, message)
        raise AppException(
            error_code=ErrorCode.AUTH_PASS_UNAVAILABLE,
            message="认证服务暂时不可用，请稍后重试",
            status_code=502,
        )
