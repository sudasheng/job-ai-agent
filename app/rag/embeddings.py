"""千问 Embedding 模型集成 —— 通过 OpenAI 兼容接口调用。"""

from __future__ import annotations

from langchain_openai import OpenAIEmbeddings

from app.core.config import get_settings

settings = get_settings()


def create_qwen_embeddings() -> OpenAIEmbeddings:
    """创建千问 Embedding 模型实例。

    千问通过阿里云 DashScope 提供 OpenAI 兼容的 embedding 接口。
    """
    return OpenAIEmbeddings(
        model=settings.QWEN_EMBEDDING_MODEL,
        api_key=settings.QWEN_API_KEY,
        base_url=settings.QWEN_BASE_URL,
        dimensions=1024,  # text-embedding-v3 默认维度
    )


# 单例缓存
_embeddings: OpenAIEmbeddings | None = None


def get_embeddings() -> OpenAIEmbeddings:
    """获取 Embedding 单例。"""
    global _embeddings
    if _embeddings is None:
        _embeddings = create_qwen_embeddings()
    return _embeddings