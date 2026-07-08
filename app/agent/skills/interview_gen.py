"""面试问题生成 Skill —— 基于 RAG 检索 + LLM 生成面试问题。"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.tools import tool

from app.core.exceptions import LLMError
from app.llm.deepseek import get_default_llm
from app.llm.prompts import get_interview_question_prompt
from app.rag.retriever import get_retriever

logger = logging.getLogger(__name__)


@tool
async def generate_interview_questions(
    direction: str,
    question_count: int = 5,
    question_types: str = "technical,behavioral",
    difficulty: str = "medium",
    job_info: str = "",
    use_rag: bool = True,
) -> str:
    """生成面试问题。

    根据面试方向和岗位信息，使用 RAG 检索相关知识后，
    由 LLM 生成高质量的面试问题和参考答案。

    Args:
        direction: 面试方向，如 "Python后端开发"
        question_count: 问题数量，默认 5
        question_types: 问题类型，逗号分隔，如 "technical,behavioral,scenario"
        difficulty: 难度：easy/medium/hard
        job_info: 岗位信息（可选，JSON 或文本）
        use_rag: 是否使用 RAG 检索知识库，默认 True

    Returns:
        JSON 格式的面试问题列表
    """
    try:
        types_list = [t.strip() for t in question_types.split(",") if t.strip()]
        llm = get_default_llm()

        knowledge_context = ""
        if use_rag:
            retriever = get_retriever()
            # 尝试从向量库检索相关知识
            try:
                results = await retriever.retrieve(
                    query=direction,
                    direction=direction,
                    top_k=5,
                )
                if results:
                    knowledge_context = "\n\n".join([
                        f"[来源: {r.get('collection', '')}] {r['content'][:500]}"
                        for r in results[:5]
                    ])
            except Exception as e:
                logger.warning("RAG 检索失败，跳过知识增强: %s", e)

        has_knowledge = bool(knowledge_context)
        prompt = get_interview_question_prompt(has_knowledge=has_knowledge)

        chain = prompt | llm
        response = await chain.ainvoke({
            "job_info": job_info or f"面试方向: {direction}",
            "direction": direction,
            "question_count": question_count,
            "question_types": ", ".join(types_list),
            "difficulty": difficulty,
            "knowledge_context": knowledge_context,
        })

        return _extract_json(response.content if hasattr(response, "content") else str(response))

    except Exception as e:
        logger.error("面试问题生成失败: %s", e)
        raise LLMError(f"面试问题生成失败: {e}") from e


@tool
async def generate_interview_questions_without_rag(
    direction: str,
    question_count: int = 5,
    question_types: str = "technical,behavioral",
    difficulty: str = "medium",
    job_info: str = "",
) -> str:
    """生成面试问题（不使用 RAG，仅基于 LLM 知识）。

    当向量库中没有相关知识时使用此方法。

    Args:
        direction: 面试方向
        question_count: 问题数量
        question_types: 问题类型
        difficulty: 难度
        job_info: 岗位信息

    Returns:
        JSON 格式的面试问题列表
    """
    return await generate_interview_questions(
        direction=direction,
        question_count=question_count,
        question_types=question_types,
        difficulty=difficulty,
        job_info=job_info,
        use_rag=False,
    )


def _extract_json(raw: str) -> str:
    """从 LLM 输出中提取 JSON。"""
    # 尝试直接解析
    try:
        parsed = json.loads(raw)
        return json.dumps(parsed, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        pass
    # 尝试从 markdown 代码块中提取
    import re
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if match:
        try:
            parsed = json.loads(match.group(1))
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            pass
    return raw