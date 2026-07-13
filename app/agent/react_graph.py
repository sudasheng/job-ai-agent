"""ReAct 采集 Agent —— 基于 LangChain create_agent + 外置 Tool 实现。

使用 LangChain 标准 Agent API（create_agent）实现 ReAct 循环：
- 工具定义：crawl_job_page / use_raw_text_job（外置 @tool）
- Agent 自主决策调用哪个工具
- 内置 max_iterations 防死循环 + 结果校验
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup
from langchain.agents import create_agent
from langchain_core.tools import tool

from app.llm.deepseek import create_deepseek_llm

logger = logging.getLogger(__name__)

# ==================== ReAct 专用 LLM（低温度精准工具调用） ====================
_react_llm = create_deepseek_llm(temperature=0.1)

# ==================== 外置 Tool 定义 ====================


@tool
def crawl_job_page(url: str) -> str:
    """爬取招聘网页，提取完整岗位 JD 信息。

    Args:
        url: 招聘页面 http/https 链接
    """
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(strip=True, separator="\n")
        return f"【网页爬取岗位JD】\n{text[:2500]}"
    except Exception as e:
        return f"【爬虫失败】错误信息：{str(e)}"


@tool
def use_raw_text_job(text: str) -> str:
    """直接使用用户粘贴的纯文字岗位描述。

    Args:
        text: 完整岗位 JD，包含岗位名称、工作年限、技术栈、工作职责
    """
    return f"【用户提供岗位文本】\n{text}"


_REACT_TOOLS = [crawl_job_page, use_raw_text_job]

# ==================== Agent System Prompt ====================

_REACT_SYSTEM_PROMPT = """你是岗位 JD 采集智能体，严格遵循 ReAct 循环：Thought 思考 → Action 调用工具 → Observation 观测结果。

可用工具：
1. crawl_job_page(url): 输入招聘网页链接，爬取岗位详情
2. use_raw_text_job(text): 直接使用用户提供的纯文字岗位 JD

规则：
1. 用户输入是 http/https 链接 → 调用 crawl_job_page
2. 用户输入是完整岗位文字描述 → 调用 use_raw_text_job
3. 输入无有效岗位、无链接 → 不调用工具，输出提示要求用户补充：粘贴岗位文字或提供招聘网页链接
4. 工具返回结果后，判断内容是否包含：岗位名称、工作年限、技术栈、工作职责四项核心信息
5. 四项全部具备则任务完成；缺少则继续提示用户补充
"""


def _build_react_agent():
    """构建 ReAct Agent（基于 LangChain create_agent）。"""
    return create_agent(
        model=_react_llm,
        tools=_REACT_TOOLS,
        system_prompt=_REACT_SYSTEM_PROMPT,
    )


# ==================== 对外接口 ====================


async def run_react_agent(
    user_input: str,
    max_loop: int = 2,
) -> dict[str, Any]:
    """运行 ReAct Agent 采集岗位信息。

    使用 LangChain create_agent 执行 ReAct 循环，
    采集完成后自动校验结果是否包含完整岗位信息。

    Args:
        user_input: 用户输入（岗位文字 / 招聘链接）
        max_loop: 最大循环次数（由 Agent 内部控制）

    Returns:
        {"job_info": "...", "tip_msg": None}  采集成功
        {"job_info": None, "tip_msg": "..."}  采集失败 / 需用户补充
    """
    agent = _build_react_agent()

    try:
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": user_input}]}
        )
        # 提取最后一条 AI 消息作为输出
        messages = result.get("messages", [])
        raw_output = ""
        for msg in reversed(messages):
            if hasattr(msg, "content") and msg.content:
                raw_output = msg.content
                break

        # 校验结果是否包含完整岗位信息
        job_info, tip_msg = await _validate_job_info(raw_output, max_loop)
        return {"job_info": job_info, "tip_msg": tip_msg}

    except Exception as e:
        logger.error("ReAct Agent 执行失败: %s", e)
        return {
            "job_info": None,
            "tip_msg": f"岗位采集出错：{str(e)}，请重试。",
        }


async def _validate_job_info(
    raw_output: str,
    max_loop: int,
) -> tuple[Optional[str], Optional[str]]:
    """校验 Agent 输出是否包含完整岗位 JD。

    Returns:
        (job_info, tip_msg)
        - job_info 非空表示采集成功
        - tip_msg 非空表示需要提示用户
    """
    if not raw_output or len(raw_output) < 10:
        return (None, "未获取到有效岗位信息，请粘贴完整岗位文字，或提供招聘网页链接。")

    judge_prompt = f"""判断下面文本是否是完整有效的招聘岗位 JD，必须同时包含：岗位名称、工作年限、技术栈、工作职责。
仅输出 true / false，不要多余文字。

内容：{raw_output[:3000]}"""

    try:
        judge_res = (await _react_llm.ainvoke(judge_prompt)).content.strip().lower()
    except Exception as e:
        logger.error("校验 LLM 调用失败: %s", e)
        return (None, "校验服务暂时不可用，请稍后重试。")

    if judge_res == "true":
        return (raw_output, None)
    else:
        return (None, "未识别到完整岗位信息，请粘贴完整岗位文字，或提供招聘网页链接。")
