"""岗位服务 —— 岗位搜索、存储、查询。"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.crawler.boss_crawler import BossZhipinCrawler
from app.models.job import Job
from app.rag.document_loader import get_document_loader
from app.rag.vector_store import get_vector_store
from app.schemas.job import JobListParams

logger = logging.getLogger(__name__)


class JobService:
    """岗位服务。"""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def search_and_scrape(
        self,
        keyword: str,
        city: str | None = None,
        max_pages: int = 3,
    ) -> list[Job]:
        """搜索并抓取岗位，保存到数据库。"""
        crawler = BossZhipinCrawler()
        try:
            await crawler.start()
            is_logged = await crawler.check_login()
            if not is_logged:
                logger.warning("Boss 直聘未登录，请先扫码登录")
                return []

            raw_jobs = await crawler.search_jobs(
                keyword=keyword,
                city=city,
                max_pages=max_pages,
            )

            saved_jobs = []
            for raw in raw_jobs:
                # 检查是否已存在
                source_id = raw.get("source_id")
                if source_id:
                    stmt = select(Job).where(Job.source_id == source_id)
                    result = await self._db.execute(stmt)
                    existing = result.scalar_one_or_none()
                    if existing:
                        saved_jobs.append(existing)
                        continue

                job = Job(
                    source=raw.get("source", "boss_zhipin"),
                    source_id=source_id,
                    source_url=raw.get("source_url"),
                    title=raw.get("title", ""),
                    company_name=raw.get("company_name", ""),
                    salary_desc=raw.get("salary_desc"),
                    salary_min=raw.get("salary_min"),
                    salary_max=raw.get("salary_max"),
                    experience=raw.get("experience"),
                    education=raw.get("education"),
                    tags=json.dumps(raw.get("tags", []), ensure_ascii=False),
                    scraped_at=datetime.now(timezone.utc),
                )
                self._db.add(job)
                saved_jobs.append(job)

            await self._db.flush()
            return saved_jobs

        finally:
            await crawler.close()

    async def scrape_detail(self, url: str) -> Job:
        """抓取单个岗位详情。"""
        crawler = BossZhipinCrawler()
        try:
            await crawler.start()
            detail = await crawler.get_job_detail(url)

            source_id = detail.get("source_id")
            if source_id:
                stmt = select(Job).where(Job.source_id == source_id)
                result = await self._db.execute(stmt)
                existing = result.scalar_one_or_none()
                if existing:
                    # 更新已有记录
                    existing.job_description = detail.get("job_description")
                    existing.job_requirements = detail.get("job_requirements")
                    existing.company_industry = detail.get("company_industry")
                    existing.company_scale = detail.get("company_scale")
                    await self._db.flush()
                    return existing

            job = Job(
                **{
                    k: v for k, v in detail.items()
                    if k in Job.__table__.columns.keys()
                },
                tags=json.dumps(detail.get("tags", []), ensure_ascii=False),
            )
            self._db.add(job)
            await self._db.flush()
            await self._db.refresh(job)
            return job

        finally:
            await crawler.close()

    async def list_jobs(self, params: JobListParams) -> tuple[list[Job], int]:
        """分页查询岗位列表。"""
        stmt = select(Job).where(Job.is_deleted == False)

        if params.keyword:
            stmt = stmt.where(
                (Job.title.contains(params.keyword))
                | (Job.company_name.contains(params.keyword))
                | (Job.job_description.contains(params.keyword))
            )
        if params.city:
            stmt = stmt.where(Job.city == params.city)
        if params.source:
            stmt = stmt.where(Job.source == params.source)

        # 总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self._db.execute(count_stmt)
        total = count_result.scalar() or 0

        # 分页
        stmt = stmt.order_by(desc(Job.created_at))
        stmt = stmt.offset((params.page - 1) * params.page_size).limit(params.page_size)
        result = await self._db.execute(stmt)
        jobs = list(result.scalars().all())

        return jobs, total

    async def get_job(self, job_id: str) -> Job:
        """获取单个岗位详情。"""
        stmt = select(Job).where(Job.id == job_id, Job.is_deleted == False)
        result = await self._db.execute(stmt)
        job = result.scalar_one_or_none()
        if not job:
            raise NotFoundError("岗位不存在")
        return job

    async def vectorize_job(self, job_id: str) -> None:
        """将岗位信息向量化存入 ChromaDB。"""
        job = await self.get_job(job_id)

        loader = get_document_loader()
        chunks = loader.load_job({
            "id": job.id,
            "title": job.title,
            "company_name": job.company_name,
            "city": job.city or "",
            "experience": job.experience or "",
            "education": job.education or "",
            "salary_desc": job.salary_desc or "",
            "job_description": job.job_description or "",
            "job_requirements": job.job_requirements or "",
        })

        vector_store = get_vector_store()
        documents = [c["content"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        vector_store.add_documents(documents, metadatas)

        job.is_vectorized = True
        await self._db.flush()