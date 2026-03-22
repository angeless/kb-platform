"""Custom exceptions and FastAPI exception handlers."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .codes import ErrorCode


class AppException(Exception):
    """Base exception for all business errors."""

    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        status_code: int = 400,
        detail: dict | None = None,
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(message)


class NotFoundException(AppException):
    def __init__(self, error_code: ErrorCode, message: str, detail: dict | None = None):
        super().__init__(error_code=error_code, message=message, status_code=404, detail=detail)


class ConflictException(AppException):
    def __init__(self, error_code: ErrorCode, message: str, detail: dict | None = None):
        super().__init__(error_code=error_code, message=message, status_code=409, detail=detail)


class ForbiddenException(AppException):
    def __init__(self, message: str = "权限不足", detail: dict | None = None):
        super().__init__(
            error_code=ErrorCode.AUTH_INSUFFICIENT_ROLE, message=message, status_code=403, detail=detail
        )


class UnauthorizedException(AppException):
    def __init__(self, error_code: ErrorCode = ErrorCode.AUTH_TOKEN_INVALID, message: str = "认证失败"):
        super().__init__(error_code=error_code, message=message, status_code=401)


class RateLimitedException(AppException):
    def __init__(self):
        super().__init__(
            error_code=ErrorCode.SYSTEM_RATE_LIMITED, message="请求过于频繁", status_code=429
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": exc.error_code,
                "message": exc.message,
                "detail": exc.detail,
                "meta": {"request_id": getattr(request.state, "request_id", None)},
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error_code": ErrorCode.VALIDATION_ERROR,
                "message": "提交的信息有误，请检查后重试",
                "detail": {},
                "meta": {"request_id": getattr(request.state, "request_id", None)},
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "error_code": ErrorCode.SYSTEM_INTERNAL_ERROR,
                "message": "系统开了个小差，请稍后重试",
                "detail": {},
                "meta": {"request_id": getattr(request.state, "request_id", None)},
            },
        )
