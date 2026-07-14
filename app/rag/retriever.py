"""多路检索器 —— 整合 Query 改写、向量检索、重排序、混合检索。"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.output_parsers import StrOutputParser

from app.core.exceptions import RAGError
from app.llm.deepseek import get_default_llm
from app.llm.prompts import get_query_rewrite_prompt
from app.rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)


class MultiPathRetriever:
    """多路检索器。

    流程：
    1. Query 改写 —— 将用户输入拆分为多个检索视角
    2. 多路向量检索 —— 在多个向量集合中检索
    3. 结果去重与合并 —— 按相关性排序
    4. 返回 Top-K 结果
    """

    def __init__(self) -> None:
        self._vector_store = get_vector_store()
        self._llm = get_default_llm()
        self._rewrite_chain = get_query_rewrite_prompt() | self._llm | StrOutputParser()

    async def rewrite_query(self, user_input: str, direction: str = "") -> dict[str, Any]:
        """Query 改写 —— 生成多个检索查询。"""
        try:
            result = await self._rewrite_chain.ainvoke({
                "user_input": user_input,
                "direction": direction or "通用技术面试",
            })
            return self._parse_json(result)
        except Exception as e:
            logger.warning("Query 改写失败，使用原始查询: %s", e)
            return {
                "original": user_input,
                "rewritten_queries": [user_input],
                "keywords": [],
                "tech_stack": [],
            }

    async def retrieve(
        self,
        query: str,
        direction: str = "",
        top_k: int = 5,
        collection_names: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """执行多路检索。

        Args:
            query: 用户原始查询
            direction: 面试方向
            top_k: 返回结果数
            collection_names: 搜索的集合列表

        Returns:
            检索结果列表
        """
        try:
            # 1. Query 改写
            rewritten = await self.rewrite_query(query, direction)
            rewritten_queries: list[str] = rewritten.get("rewritten_queries", [query])

            # 2. 多路检索
            all_results: list[dict[str, Any]] = []
            seen_ids: set[str] = set()

            for rq in rewritten_queries[:3]:  # 最多 3 个改写查询
                results = self._vector_store.multi_search(
                    rq,
                    collections=collection_names,
                    k_per_collection=top_k,
                )
                for r in results:
                    doc_id = r["metadata"].get("id", r["content"][:50])
                    if doc_id not in seen_ids:
                        seen_ids.add(doc_id)
                        all_results.append(r)

            # 3. 按分数排序并截断
            all_results.sort(key=lambda x: x["score"])
            return all_results[:top_k]

        except Exception as e:
            logger.error("多路检索失败: %s", e)
            raise RAGError(f"知识检索失败: {e}") from e

    def retrieve_sync(
        self,
        query: str,
        top_k: int = 5,
        collection_names: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """同步检索（用于非异步场景）。"""
        return self._vector_store.multi_search(
            query,
            collections=collection_names,
            k_per_collection=top_k,
        )

    async def hybrid_retrieve(
        self,
        query: str,
        top_k: int = 5,
        collection_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """混合检索 —— BM25 + 向量语义检索，RRF 排名融合。

        比纯向量检索多了关键词精确匹配能力，
        适合岗位 JD 中包含专业术语的场景。

        Args:
            query: 用户查询
            top_k: 返回结果数
            collection_name: ChromaDB 集合名

        Returns:
            融合后的检索结果
        """
        try:
            from app.rag.hybrid_retriever import get_hybrid_retriever
            hybrid = get_hybrid_retriever()
            return await hybrid.hybrid_search(
                query=query,
                top_k=top_k,
                collection_name=collection_name,
            )
        except Exception as e:
            logger.warning("混合检索失败，回退到纯向量检索: %s", e)
            return self._vector_store.multi_search(
                query,
                collections=[collection_name] if collection_name else None,
                k_per_collection=top_k,
            )

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        """从 LLM 输出中提取 JSON。"""
        # 尝试直接解析
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        # 尝试从 markdown 代码块中提取
        import re
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return {"rewritten_queries": [raw]}


_retriever: MultiPathRetriever | None = None


def get_retriever() -> MultiPathRetriever:
    """获取检索器单例。"""
    global _retriever
    if _retriever is None:
        _retriever = MultiPathRetriever()
    return _retriever