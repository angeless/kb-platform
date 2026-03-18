"""Common schemas: pagination, response wrappers."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


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
