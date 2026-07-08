"""岗位相关 Schema。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import PaginationParams


class JobSearchRequest(BaseModel):
    """岗位搜索请求 —— 通过浏览器抓取。"""

    keyword: str = Field(description="搜索关键词/面试方向")
    city: str | None = Field(default=None, description="城市")
    page: int = Field(default=1, ge=1, description="页码")
    url: str | None = Field(default=None, description="直接抓取的岗位 URL")


class JobSearchResponse(BaseModel):
    """岗位搜索结果。"""

    task_id: str = Field(description="抓取任务 ID")
    status: str = Field(description="任务状态: pending/running/completed/failed")
    message: str = Field(default="任务已提交", description="状态消息")


class JobResponse(BaseModel):
    """岗位信息响应。"""

    id: str
    source: str
    source_id: str | None = None
    source_url: str | None = None
    title: str
    company_name: str
    city: str | None = None
    district: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_desc: str | None = None
    experience: str | None = None
    education: str | None = None
    job_description: str | None = None
    job_requirements: str | None = None
    tags: list[str] = Field(default_factory=list)
    company_industry: str | None = None
    company_scale: str | None = None
    company_logo: str | None = None
    hr_name: str | None = None
    hr_title: str | None = None
    status: str
    published_at: datetime | None = None
    scraped_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class JobListParams(PaginationParams):
    """岗位列表查询参数。"""

    keyword: str | None = Field(default=None, description="搜索关键词")
    city: str | None = Field(default=None, description="城市")
    direction: str | None = Field(default=None, description="面试方向")
    source: str | None = Field(default=None, description="来源")


class JobListResponse(BaseModel):
    """岗位列表响应（简化版）。"""

    id: str
    title: str
    company_name: str
    city: str | None = None
    salary_desc: str | None = None
    experience: str | None = None
    education: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}