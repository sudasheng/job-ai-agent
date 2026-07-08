"""通用 Schema 定义：分页、响应包装。"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseModel(BaseModel, Generic[T]):
    """统一响应包装。"""

    code: int = Field(default=200, description="业务状态码")
    message: str = Field(default="success", description="提示信息")
    data: T | None = Field(default=None, description="响应数据")


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应。"""

    items: list[T] = Field(default_factory=list, description="数据列表")
    total: int = Field(default=0, description="总条数")
    page: int = Field(default=1, description="当前页")
    page_size: int = Field(default=20, description="每页大小")
    total_pages: int = Field(default=0, description="总页数")


class PaginationParams(BaseModel):
    """分页请求参数。"""

    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小")