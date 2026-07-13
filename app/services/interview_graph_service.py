"""面试图谱服务 —— 封装 LangGraph + ReAct 面试流程。

提供基于 LangGraph 状态图的多轮面试会话管理：
- 岗位采集（ReAct 子图自动识别链接/文本）
- 10 轮交互出题
- 自动评分报告生成
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.agent import JobAIAgent
from app.core.exceptions import NotFoundError
from app.models.interview import InterviewQuestion, InterviewSession

logger = logging.getLogger(__name__)


class InterviewGraphService:
    """面试图谱服务 —— 基于 LangGraph 状态图的面试流程编排。

    区别于旧的 InterviewService，本服务：
    1. 使用 LangGraph 主图 + ReAct 子图替代 AgentExecutor
    2. 岗位采集由 ReAct 自动完成（无需预先抓取）
    3. 题目逐题生成（而非一次性批量生成）
    4. 内置 MemorySaver 支持断点恢复
    """

    MAX_QUESTIONS = 10  # 单次面试最多 10 题

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._agent = JobAIAgent()

    # ==================== 面试会话 ====================

    async def start_or_continue_session(
        self,
        user_id: str,
        user_input: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """开始或继续面试会话。

        Args:
            user_id: 用户 ID
            user_input: 用户本轮输入（岗位描述/答题内容）
            session_id: 已有会话 ID，新会话传 None

        Returns:
            {"type": "question"/"report"/"hint", ...}
        """
        if session_id:
            # 继续已有会话
            session = await self._get_session(session_id, user_id)
            thread_id = session.id  # 使用 session_id 作为 thread_id
        else:
            # 创建新会话
            thread_id = str(uuid.uuid4())
            session = InterviewSession(
                id=thread_id,
                user_id=user_id,
                title="AI 面试练习",
                direction="custom",
                total_questions=self.MAX_QUESTIONS,
                answered_questions=0,
                status="collecting",  # 新状态：收集中
                started_at=datetime.now(timezone.utc),
            )
            self._db.add(session)
            await self._db.flush()

        # 执行 LangGraph 流程
        result = await self._agent.run_interview_session(
            thread_id=thread_id,
            user_input=user_input,
        )

        # 根据结果更新数据库状态
        await self._update_session_for_result(session, result, user_input)

        return result

    async def get_session_detail(
        self,
        session_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """获取会话详情（含 LangGraph 当前状态）。"""
        session = await self._get_session(session_id, user_id)
        state = await self._agent.get_session_state(session_id)

        return {
            "session": {
                "id": session.id,
                "title": session.title,
                "status": session.status,
                "total_questions": session.total_questions,
                "answered_questions": session.answered_questions,
                "avg_score": session.avg_score,
                "started_at": session.started_at.isoformat() if session.started_at else None,
            },
            "state": state,
        }

    # ==================== 内部方法 ====================

    async def _update_session_for_result(
        self,
        session: InterviewSession,
        result: dict[str, Any],
        user_input: str,
    ) -> None:
        """根据 LangGraph 结果更新数据库会话状态。"""
        result_type = result.get("type")

        if result_type == "question":
            # 生成了一道新题目
            round_num = result.get("round", 1)
            if round_num == 1 and session.status == "collecting":
                session.status = "in_progress"
            # 更新已回答题目数（round>1 时上一轮已回答）
            session.answered_questions = max(session.answered_questions, round_num - 1)

        elif result_type == "report":
            # 面试完成
            session.status = "completed"
            session.answered_questions = self.MAX_QUESTIONS
            session.completed_at = datetime.now(timezone.utc)
            # 尝试从报告中提取总分
            avg = self._extract_score(result.get("content", ""))
            if avg is not None:
                session.avg_score = avg

        elif result_type == "hint":
            # 提示信息（通常是岗位采集阶段）
            if session.status == "collecting":
                pass  # 保持 collecting 状态
            # 可能采集失败，记录日志
            logger.info("会话 %s 收到提示: %s", session.id, result.get("msg"))

        await self._db.flush()

    async def _get_session(
        self,
        session_id: str,
        user_id: str,
    ) -> InterviewSession:
        """获取已有面试会话。"""
        stmt = select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user_id,
        )
        result = await self._db.execute(stmt)
        session = result.scalar_one_or_none()
        if not session:
            raise NotFoundError("面试会话不存在")
        return session

    @staticmethod
    def _extract_score(report: str) -> float | None:
        """从评分报告中提取总分。"""
        import re

        # 匹配 "总分：85" 或 "总分: 85.5" 或 "### 1. 总分（0-100）\n85"
        patterns = [
            r"总分[：:]\s*(\d+(?:\.\d+)?)",
            r"得分[：:]\s*(\d+(?:\.\d+)?)",
            r"评分[：:]\s*(\d+(?:\.\d+)?)",
        ]
        for p in patterns:
            match = re.search(p, report)
            if match:
                return float(match.group(1))
        return None
