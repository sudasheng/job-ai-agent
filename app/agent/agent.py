"""LangGraph Agent 门面 —— 基于 LangGraph 主图 + AgentExecutor ReAct 的面试 Agent。

架构：
- ReAct Agent（AgentExecutor + 外置 Tool）：采集岗位信息
- LangGraph 主图：固定业务流程（岗位采集 → 10 轮出题 → 评分报告）
- 统一 State：主图完全共享上下文
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.agent.main_graph import _main_interview_graph
from app.agent.state import InterviewState
from app.llm.deepseek import get_default_llm
from app.llm.prompts import get_chat_prompt

logger = logging.getLogger(__name__)


class JobAIAgent:
    """求职 AI Agent（LangGraph + ReAct 架构）。

    提供两个核心能力：
    1. 面试会话：run_interview_session() —— 基于 LangGraph 状态图的完整面试流程
    2. 自由聊天：chat() —— 轻量 LLM 调用，处理求职相关咨询
    """

    def __init__(self) -> None:
        self._interview_graph = _main_interview_graph
        self._chat_llm = get_default_llm()

    # ==================== 面试会话（LangGraph 驱动） ====================

    async def run_interview_session(
        self,
        thread_id: str,
        user_input: str,
    ) -> dict[str, Any]:
        """执行一轮面试会话。

        根据 current_round 自动路由：
        - round=0：进入 ReAct 子图采集岗位信息
        - round=1~9：生成下一道面试题
        - round=10：生成最终评分报告

        Args:
            thread_id: 会话唯一标识（同一用户多次调用保持不变）
            user_input: 用户本轮输入（岗位描述 / 答题内容）

        Returns:
            {"type": "question", "round": N, "question": "..."} 或
            {"type": "report", "content": "..."} 或
            {"type": "hint", "msg": "..."}
        """
        config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}

        # 读取当前会话状态
        graph = self._interview_graph
        snapshot = graph.get_state(config)
        current_state = snapshot.values if snapshot else {}

        if not current_state:
            # 全新会话，初始化状态
            init_state: dict[str, Any] = {
                "thread_id": thread_id,
                "user_input": user_input,
                "job_info": None,
                "react_max_loop": 2,
                "react_history": [],
                "rag_knowledge": None,
                "question_list": [],
                "answer_list": [],
                "current_round": 0,
                "final_report": None,
                "tip_msg": None,
                "error": None,
            }
            await graph.ainvoke(init_state, config=config)
        else:
            # 已有会话，更新用户输入继续流程
            await graph.aupdate_state(config, {"user_input": user_input})
            await graph.ainvoke(None, config=config)

        final_snapshot = graph.get_state(config)
        final_state = final_snapshot.values if final_snapshot else {}

        return self._format_response(final_state)

    async def get_session_state(self, thread_id: str) -> dict[str, Any] | None:
        """获取指定会话的当前状态。"""
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = self._interview_graph.get_state(config)
        if snapshot and snapshot.values:
            return dict(snapshot.values)
        return None

    @staticmethod
    def _format_response(state: dict[str, Any]) -> dict[str, Any]:
        """将 State 格式化为对外返回结构。"""
        if state.get("error"):
            return {"type": "error", "msg": state["error"]}
        if state.get("tip_msg"):
            return {"type": "hint", "msg": state["tip_msg"]}
        if state.get("final_report"):
            return {"type": "report", "content": state["final_report"]}
        if state.get("question_list"):
            return {
                "type": "question",
                "round": state.get("current_round", 0),
                "question": state["question_list"][-1],
            }
        return {"type": "hint", "msg": "正在处理，请稍候..."}

    # ==================== 自由聊天（LLM 直接调用） ====================

    async def chat(
        self,
        user_input: str,
        chat_history: list[dict[str, str]] | None = None,
    ) -> str:
        """自由聊天模式 —— 处理求职咨询、面试技巧等非面试流程对话。

        Args:
            user_input: 用户输入
            chat_history: 历史对话 [{"role": "user/assistant", "content": "..."}]

        Returns:
            AI 回复文本
        """
        prompt = get_chat_prompt()
        response = await self._chat_llm.ainvoke(
            prompt.format(user_input=user_input)
        )
        return response.content if hasattr(response, "content") else str(response)
