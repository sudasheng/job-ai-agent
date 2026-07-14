"""混合检索器 —— BM25 关键词检索 + 向量语义检索，RRF 排名融合。

两种检索方式互补：
- BM25（倒排索引 + TF-IDF）：擅长关键词精确匹配
- 向量检索（Embedding + HNSW）：擅长语义匹配

融合策略：RRF（Reciprocal Rank Fusion），不依赖原始分数绝对值，只看排名，更稳健。
"""

from __future__ import annotations

import logging
from typing import Any

import jieba
from rank_bm25 import BM25Okapi

from app.rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)


class HybridRetriever:
    """BM25 + 向量混合检索器。

    用法：
        retriever = HybridRetriever(alpha=0.6)
        retriever.build_bm25_index()          # 启动时构建一次
        results = await retriever.hybrid_search("Python后端面试题", top_k=5)

    依赖：
        pip install rank_bm25 jieba
    """

    def __init__(self, alpha: float = 0.6) -> None:
        """
        Args:
            alpha: 向量检索权重（0~1），(1-alpha) 为 BM25 权重。
                   alpha=0.6 表示向量占 60%，BM25 占 40%。
        """
        self._alpha = alpha
        self._vector_store = get_vector_store()
        self._bm25: BM25Okapi | None = None
        self._bm25_docs: list[dict[str, Any]] = []

    # ==================== BM25 索引构建 ====================

    def build_bm25_index(self, collection_name: str | None = None) -> None:
        """从 ChromaDB 加载文档，构建 BM25 倒排索引。

        建议在应用启动时或数据更新后调用一次。
        """
        collection = self._vector_store.get_collection(collection_name)
        result = collection._collection.get(include=["documents", "metadatas"])

        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])
        ids = result.get("ids", [])

        if not documents:
            logger.warning("BM25 索引构建：集合为空")
            return

        tokenized_docs = [self._tokenize(doc) for doc in documents]
        self._bm25 = BM25Okapi(tokenized_docs)
        self._bm25_docs = [
            {"content": doc, "metadata": meta or {}, "id": doc_id}
            for doc, meta, doc_id in zip(documents, metadatas, ids)
        ]
        logger.info("BM25 索引构建完成，共 %d 条文档", len(documents))

    def _tokenize(self, text: str) -> list[str]:
        """中文分词（jieba）+ 英文小写 + 去停用词。"""
        text = text.lower()
        tokens = list(jieba.cut(text))
        stop_words = {
            "的", "了", "在", "是", "和", "与", "及", "或", "有", "对",
            "等", "中", "为", "到", "从", "被", "把", "给", "用", "这",
            "那", "一", "不", "也", "都", "就", "要", "会", "能", "可",
            "上", "下", "个", "人", "大", "小", "多", "少",
        }
        return [t for t in tokens if len(t) > 1 and t not in stop_words]

    # ==================== 混合检索 ====================

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        collection_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """BM25 + 向量混合检索。

        Args:
            query: 用户查询
            top_k: 返回结果数
            collection_name: ChromaDB 集合名

        Returns:
            融合后的检索结果，按综合得分排序
        """
        vector_results = self._vector_store.search(
            query, k=top_k * 2, collection_name=collection_name
        )
        bm25_results = self._bm25_search(query, top_k * 2)
        fused = self._rrf_fusion(vector_results, bm25_results)
        return fused[:top_k]

    def _bm25_search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """BM25 关键词检索。"""
        if self._bm25 is None:
            logger.warning("BM25 索引未构建，返回空结果")
            return []

        tokenized_query = self._tokenize(query)
        scores = self._bm25.get_scores(tokenized_query)

        scored_docs = [
            {**self._bm25_docs[i], "bm25_score": float(scores[i])}
            for i in range(len(scores))
            if scores[i] > 0
        ]
        scored_docs.sort(key=lambda x: x["bm25_score"], reverse=True)
        return scored_docs[:top_k]

    # ==================== RRF 融合 ====================

    @staticmethod
    def _rrf_fusion(
        vector_results: list[dict[str, Any]],
        bm25_results: list[dict[str, Any]],
        k: int = 60,
    ) -> list[dict[str, Any]]:
        """RRF（Reciprocal Rank Fusion）排名融合。

        score(d) = Σ 1 / (k + rank_i(d))
        k=60 是论文推荐值。
        """
        doc_scores: dict[str, float] = {}
        doc_map: dict[str, dict[str, Any]] = {}

        def _get_doc_id(doc: dict[str, Any]) -> str:
            return doc.get("metadata", {}).get("id", doc["content"][:50])

        for rank, doc in enumerate(vector_results):
            doc_id = _get_doc_id(doc)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 1.0 / (k + rank + 1)
            doc_map[doc_id] = doc

        for rank, doc in enumerate(bm25_results):
            doc_id = doc.get("id") or _get_doc_id(doc)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 1.0 / (k + rank + 1)
            if doc_id not in doc_map:
                doc_map[doc_id] = doc

        sorted_ids = sorted(doc_scores.keys(), key=lambda x: doc_scores[x], reverse=True)
        return [
            {**doc_map[doc_id], "hybrid_score": doc_scores[doc_id]}
            for doc_id in sorted_ids
        ]


# 单例
_hybrid_retriever: HybridRetriever | None = None


def get_hybrid_retriever() -> HybridRetriever:
    """获取混合检索器单例。"""
    global _hybrid_retriever
    if _hybrid_retriever is None:
        _hybrid_retriever = HybridRetriever(alpha=0.6)
    return _hybrid_retriever
