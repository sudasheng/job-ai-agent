"""DeepSeek LLM 集成 —— 通过 OpenAI 兼容接口调用。"""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.core.config import get_settings

settings = get_settings()


def create_deepseek_llm(
    temperature: float | None = None,
    max_tokens: int | None = None,
    streaming: bool = False,
) -> ChatOpenAI:
    """创建 DeepSeek LLM 实例。

    DeepSeek 提供 OpenAI 兼容的 API 接口，通过 langchain-openai 的 ChatOpenAI 调用。
    """
    return ChatOpenAI(
        model=settings.DEEPSEEK_MODEL,
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
        temperature=temperature or settings.DEEPSEEK_TEMPERATURE,
        max_tokens=max_tokens or settings.DEEPSEEK_MAX_TOKENS,
        streaming=streaming,
        timeout=60,
        max_retries=3,
    )


def get_default_llm() -> ChatOpenAI:
    """获取默认 LLM 实例（单例）。"""
    return create_deepseek_llm()