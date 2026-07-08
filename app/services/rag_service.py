"""RAG 服务 —— 知识库管理、文档索引、检索。"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RAGError
from app.models.job import Job
from app.rag.document_loader import get_document_loader
from app.rag.retriever import get_retriever
from app.rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)


class RAGService:
    """RAG（检索增强生成）服务。

    负责：
    - 知识库索引管理
    - 批量向量化岗位数据
    - 知识检索
    - 知识库统计
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def index_jobs(self, job_ids: list[str] | None = None) -> dict[str, Any]:
        """将岗位数据批量索引到向量库。

        Args:
            job_ids: 指定岗位 ID 列表，为空则索引全部未向量化的岗位

        Returns:
            索引结果统计
        """
        stmt = select(Job).where(Job.is_deleted == False)
        if job_ids:
            stmt = stmt.where(Job.id.in_(job_ids))
        else:
            stmt = stmt.where(Job.is_vectorized == False)

        result = await self._db.execute(stmt)
        jobs = result.scalars().all()

        if not jobs:
            return {"indexed": 0, "message": "没有需要索引的岗位"}

        vector_store = get_vector_store()
        loader = get_document_loader()

        indexed_count = 0
        for job in jobs:
            try:
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

                documents = [c["content"] for c in chunks]
                metadatas = [c["metadata"] for c in chunks]
                vector_store.add_documents(documents, metadatas)

                job.is_vectorized = True
                indexed_count += 1

            except Exception as e:
                logger.error("岗位 %s 向量化失败: %s", job.id, e)

        await self._db.flush()
        return {"indexed": indexed_count, "total": len(jobs)}

    async def search(
        self,
        query: str,
        direction: str = "",
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """知识检索 —— 多路检索。"""
        retriever = get_retriever()
        try:
            return await retriever.retrieve(
                query=query,
                direction=direction,
                top_k=top_k,
            )
        except Exception as e:
            logger.error("知识检索失败: %s", e)
            raise RAGError(f"知识检索失败: {e}") from e

    async def add_knowledge(
        self,
        texts: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        collection_name: str | None = None,
    ) -> list[str]:
        """手动添加知识到向量库。"""
        vector_store = get_vector_store()
        return vector_store.add_documents(
            documents=texts,
            metadatas=metadatas,
            collection_name=collection_name,
        )

    def get_stats(self) -> dict[str, Any]:
        """获取向量库统计信息。"""
        vector_store = get_vector_store()
        collections = vector_store.list_collections()
        stats = {}
        for col in collections:
            try:
                count = vector_store.get_collection_count(col)
                stats[col] = count
            except Exception:
                stats[col] = 0
        return {
            "collections": stats,
            "total_collections": len(collections),
        }