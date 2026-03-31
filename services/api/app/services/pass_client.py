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

    async def _request(self, method: str, path: str, context: str, **kwargs) -> dict:
        """Send HTTP request to Pass with unified network error handling."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.request(method, f"{self._base_url}{path}", **kwargs)
        except httpx.HTTPError as e:
            logger.error("Pass API %s network error: %s", context, e)
            raise AppException(
                error_code=ErrorCode.AUTH_PASS_UNAVAILABLE,
                message="认证服务暂时不可用，请稍后重试",
                status_code=502,
            ) from e
        return self._handle_response(resp, context=context)

    async def login(self, email: str, password: str) -> dict:
        """POST /api/v1/pass/login → { passId, token, expiresAt, productBindings }"""
        return await self._request("POST", "/api/v1/pass/login", context="login", json={
            "productId": self._product_id, "email": email, "password": password,
        })

    async def register(self, email: str, password: str, display_name: str = "") -> dict:
        """POST /api/v1/pass/register → { passId, token, expiresAt, productBinding }"""
        body: dict = {
            "productId": self._product_id,
            "email": email,
            "password": password,
        }
        if display_name:
            body["displayName"] = display_name
        return await self._request("POST", "/api/v1/pass/register", context="register", json=body)

    async def refresh(self, token: str) -> dict:
        """POST /api/v1/pass/refresh → { token, expiresAt }"""
        return await self._request("POST", "/api/v1/pass/refresh", context="refresh",
                                   headers={"Authorization": f"Bearer {token}"})

    async def me(self, token: str) -> dict:
        """GET /api/v1/pass/me → { passId, email, phone, displayName, avatarUrl, productBindings }"""
        return await self._request("GET", "/api/v1/pass/me", context="me",
                                   headers={"Authorization": f"Bearer {token}"})

    # Required fields per endpoint for response validation
    _REQUIRED_FIELDS: dict[str, list[str]] = {
        "login": ["passId", "token"],
        "register": ["passId", "token"],
        "refresh": ["token"],
        "me": ["passId"],
    }

    def _handle_response(self, resp: httpx.Response, context: str) -> dict:
        """Map Pass HTTP responses to KB exceptions."""
        if resp.status_code in (200, 201):
            try:
                data = resp.json()
            except (ValueError, UnicodeDecodeError) as e:
                logger.error("Pass API %s: success status %s but invalid JSON: %s", context, resp.status_code, resp.text[:500])
                raise AppException(
                    error_code=ErrorCode.AUTH_PASS_UNAVAILABLE,
                    message="认证服务返回了无效响应",
                    status_code=502,
                ) from e
            # Validate required fields
            required = self._REQUIRED_FIELDS.get(context, [])
            missing = [f for f in required if f not in data]
            if missing:
                logger.error("Pass API %s: missing fields %s in response", context, missing)
                raise AppException(
                    error_code=ErrorCode.AUTH_PASS_UNAVAILABLE,
                    message="认证服务返回了不完整的响应",
                    status_code=502,
                )
            return data

        # Try to extract PA error code from response body
        pa_code = ""
        message = ""
        try:
            body = resp.json()
            pa_code = body.get("errorCode", body.get("code", ""))
            message = body.get("message", "")
        except (ValueError, KeyError):
            logger.warning("Pass API %s: could not parse error body (status=%s, body=%s)", context, resp.status_code, resp.text[:500])

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
