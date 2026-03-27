"""Common schemas: pagination, response wrappers."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Error response schema for OpenAPI documentation."""

    error_code: str = Field(..., max_length=50, description="Machine-readable error code", examples=["DOCUMENT_NOT_FOUND"])
    message: str = Field(..., max_length=500, description="Human-readable error message", examples=["文档不存在"])
    detail: dict[str, Any] = Field(default_factory=dict, description="Additional error details")
    meta: dict[str, Any] = Field(default_factory=dict, description="Request metadata", examples=[{"request_id": "abc-123"}])


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginationMeta(BaseModel):
    request_id: str | None = None
    page: int
    page_size: int
    total: int


class SingleMeta(BaseModel):
    request_id: str | None = None


class DataResponse(BaseModel, Generic[T]):
    data: T
    meta: SingleMeta = SingleMeta()


class ListResponse(BaseModel, Generic[T]):
    data: list[T]
    meta: PaginationMeta


# Standard OpenAPI error responses for endpoint decorators
ERROR_RESPONSES_AUTH = {
    401: {"description": "Unauthorized — missing or invalid JWT token", "model": ErrorDetail},
    403: {"description": "Forbidden — insufficient role permissions", "model": ErrorDetail},
}

ERROR_RESPONSES_NOT_FOUND = {
    404: {"description": "Resource not found", "model": ErrorDetail},
}

ERROR_RESPONSES_CONFLICT = {
    409: {"description": "Business conflict (e.g., duplicate, invalid state transition)", "model": ErrorDetail},
}

ERROR_RESPONSES_VALIDATION = {
    422: {"description": "Validation error — invalid request parameters"},
}

ERROR_RESPONSES_SERVER = {
    500: {"description": "Internal server error", "model": ErrorDetail},
}
