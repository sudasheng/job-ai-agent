"""ChromaDB 向量存储管理。"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma

from app.core.config import get_settings
from app.rag.embeddings import get_embeddings

settings = get_settings()


class VectorStoreManager:
    """ChromaDB 向量存储管理器。

    负责向量数据库的生命周期管理，包括：
    - 存储面试知识库（技术文档、面试题、参考答案等）
    - 存储岗位描述信息
    - 支持多集合管理
    """

    def __init__(self) -> None:
        persist_dir = str(Path(settings.PROJECT_ROOT) / settings.CHROMA_PERSIST_DIR)
        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._embeddings = get_embeddings()

    def get_collection(self, name: str | None = None) -> Chroma:
        """获取或创建向量集合。"""
        collection_name = name or settings.CHROMA_COLLECTION_NAME
        return Chroma(
            client=self._client,
            collection_name=collection_name,
            embedding_function=self._embeddings,
        )

    def add_documents(
        self,
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids: list[str] | None = None,
        collection_name: str | None = None,
    ) -> list[str]:
        """向向量库添加文档。"""
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]
        collection = self.get_collection(collection_name)
        return collection.add_texts(
            texts=documents,
            metadatas=metadatas,
            ids=ids,
        )

    def search(
        self,
        query: str,
        k: int = 5,
        collection_name: str | None = None,
        filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """向量相似度检索。"""
        collection = self.get_collection(collection_name)
        results = collection.similarity_search_with_score(
            query,
            k=k,
            filter=filter,
        )
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": score,
            }
            for doc, score in results
        ]

    def multi_search(
        self,
        query: str,
        collections: list[str] | None = None,
        k_per_collection: int = 3,
    ) -> list[dict[str, Any]]:
        """多路检索 —— 从多个集合中检索并合并结果。"""
        if collections is None:
            collections = [settings.CHROMA_COLLECTION_NAME]

        all_results: list[dict[str, Any]] = []
        for col_name in collections:
            results = self.search(query, k=k_per_collection, collection_name=col_name)
            for r in results:
                r["collection"] = col_name
            all_results.extend(results)

        # 按相似度分数排序（分数越低越相似）
        all_results.sort(key=lambda x: x["score"])
        return all_results

    def delete_collection(self, name: str) -> None:
        """删除集合。"""
        try:
            self._client.delete_collection(name)
        except ValueError:
            pass

    def list_collections(self) -> list[str]:
        """列出所有集合。"""
        return [col.name for col in self._client.list_collections()]

    def get_collection_count(self, name: str | None = None) -> int:
        """获取集合中的文档数量。"""
        collection = self.get_collection(name)
        return collection._collection.count()


# 全局单例
_vector_store: VectorStoreManager | None = None


def get_vector_store() -> VectorStoreManager:
    """获取向量存储管理器单例。"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreManager()
    return _vector_store