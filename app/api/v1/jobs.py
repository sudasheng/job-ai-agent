"""岗位相关 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse, ResponseModel
from app.schemas.job import (
    JobListParams,
    JobListResponse,
    JobResponse,
    JobSearchRequest,
    JobSearchResponse,
)
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["岗位"])


@router.post("/search", response_model=ResponseModel[JobSearchResponse])
async def search_jobs(
    data: JobSearchRequest,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """搜索并抓取岗位信息。

    如果同时提供 url，则直接抓取单个岗位详情；
    否则根据 keyword 搜索岗位列表。
    """
    service = JobService(db)

    if data.url:
        job = await service.scrape_detail(data.url)
        return ResponseModel(
            message="岗位抓取成功",
            data=JobSearchResponse(
                task_id=job.id,
                status="completed",
                message="岗位详情已抓取",
            ),
        )

    jobs = await service.search_and_scrape(
        keyword=data.keyword,
        city=data.city,
        max_pages=data.page,
    )

    return ResponseModel(
        message=f"搜索完成，共找到 {len(jobs)} 个岗位",
        data=JobSearchResponse(
            task_id="",
            status="completed",
            message=f"共抓取 {len(jobs)} 个岗位",
        ),
    )


@router.get("", response_model=ResponseModel[PaginatedResponse[JobListResponse]])
async def list_jobs(
    keyword: str | None = Query(default=None, description="搜索关键词"),
    city: str | None = Query(default=None, description="城市"),
    source: str | None = Query(default=None, description="来源"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页大小"),
    current_user: User | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """分页查询岗位列表。"""
    service = JobService(db)
    params = JobListParams(
        keyword=keyword,
        city=city,
        source=source,
        page=page,
        page_size=page_size,
    )
    jobs, total = await service.list_jobs(params)

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return ResponseModel(
        data=PaginatedResponse(
            items=[JobListResponse.model_validate(j) for j in jobs],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )


@router.get("/{job_id}", response_model=ResponseModel[JobResponse])
async def get_job_detail(
    job_id: str,
    current_user: User | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取岗位详情。"""
    service = JobService(db)
    job = await service.get_job(job_id)
    return ResponseModel(data=JobResponse.model_validate(job))


@router.post("/{job_id}/vectorize", response_model=ResponseModel)
async def vectorize_job(
    job_id: str,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """将岗位信息向量化存入 ChromaDB。"""
    service = JobService(db)
    await service.vectorize_job(job_id)
    return ResponseModel(message="向量化成功")