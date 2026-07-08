"""面试评分 Skill —— 对用户回答进行专业评分。"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.tools import tool

from app.core.exceptions import LLMError
from app.llm.deepseek import get_default_llm
from app.llm.prompts import get_interview_score_prompt

logger = logging.getLogger(__name__)


@tool
async def score_interview_answer(
    question_text: str,
    user_answer: str,
    reference_answer: str = "",
    knowledge_context: str = "",
) -> str:
    """对用户的面试回答进行评分。

    根据问题、参考答案和相关知识，由 LLM 对用户回答进行
    多维度评分（准确性、深度、表达、实践），并给出改进建议。

    Args:
        question_text: 面试问题文本
        user_answer: 用户回答
        reference_answer: 参考答案（可选）
        knowledge_context: 相关知识上下文（可选，从 RAG 检索）

    Returns:
        JSON 格式的评分结果，包含总分、各维度分数、点评和改进建议
    """
    try:
        llm = get_default_llm()
        prompt = get_interview_score_prompt()
        chain = prompt | llm

        response = await chain.ainvoke({
            "question_text": question_text,
            "reference_answer": reference_answer or "暂无参考答案",
            "knowledge_context": knowledge_context or "暂无相关知识",
            "user_answer": user_answer,
        })

        raw = response.content if hasattr(response, "content") else str(response)
        return _extract_json(raw)

    except Exception as e:
        logger.error("面试评分失败: %s", e)
        raise LLMError(f"面试评分失败: {e}") from e


def _extract_json(raw: str) -> str:
    """从 LLM 输出中提取 JSON。"""
    try:
        parsed = json.loads(raw)
        return json.dumps(parsed, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        pass
    import re
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if match:
        try:
            parsed = json.loads(match.group(1))
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            pass
    return raw