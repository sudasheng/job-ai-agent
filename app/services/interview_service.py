"""面试服务 —— 面试会话管理、问题生成、评分。"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import LLMError, NotFoundError
from app.llm.deepseek import get_default_llm
from app.llm.prompts import (
    get_interview_question_prompt,
    get_interview_score_prompt,
)
from app.models.interview import InterviewQuestion, InterviewSession
from app.models.job import Job
from app.rag.retriever import get_retriever
from app.schemas.interview import AnswerSubmitRequest, InterviewCreateRequest

logger = logging.getLogger(__name__)


class InterviewService:
    """面试服务。"""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_session(
        self,
        user_id: str,
        data: InterviewCreateRequest,
    ) -> InterviewSession:
        """创建面试会话 + 生成问题。"""
        # 获取岗位信息（如果有）
        job_info = ""
        if data.job_id:
            stmt = select(Job).where(Job.id == data.job_id)
            result = await self._db.execute(stmt)
            job = result.scalar_one_or_none()
            if job:
                job_info = job.to_search_text()

        # 创建会话
        session = InterviewSession(
            user_id=user_id,
            title=f"{data.direction} 面试练习",
            direction=data.direction,
            job_id=data.job_id,
            total_questions=data.question_count,
            answered_questions=0,
            status="in_progress",
            started_at=datetime.now(timezone.utc),
        )
        self._db.add(session)
        await self._db.flush()

        # 生成面试问题
        questions_data = await self._generate_questions(
            direction=data.direction,
            question_count=data.question_count,
            question_types=data.question_types,
            job_info=job_info,
        )

        # 保存问题
        questions: list[InterviewQuestion] = []
        for q_data in questions_data.get("questions", []):
            question = InterviewQuestion(
                session_id=session.id,
                sequence=q_data.get("sequence", len(questions) + 1),
                question_text=q_data.get("question_text", ""),
                question_type=q_data.get("question_type", "technical"),
                reference_answer=q_data.get("reference_answer"),
                knowledge_source=q_data.get("knowledge_source"),
            )
            self._db.add(question)
            questions.append(question)

        await self._db.flush()
        session.questions = questions
        return session

    async def get_session(self, session_id: str, user_id: str) -> InterviewSession:
        """获取面试会话详情。"""
        stmt = select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user_id,
        )
        result = await self._db.execute(stmt)
        session = result.scalar_one_or_none()
        if not session:
            raise NotFoundError("面试会话不存在")
        return session

    async def list_sessions(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[InterviewSession], int]:
        """分页查询用户的面试会话列表。"""
        from sqlalchemy import desc, func

        stmt = select(InterviewSession).where(
            InterviewSession.user_id == user_id
        ).order_by(desc(InterviewSession.created_at))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self._db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self._db.execute(stmt)
        sessions = list(result.scalars().all())

        return sessions, total

    async def submit_answer(
        self,
        session_id: str,
        user_id: str,
        data: AnswerSubmitRequest,
    ) -> InterviewQuestion:
        """提交答案并评分。"""
        # 获取问题
        stmt = select(InterviewQuestion).where(
            InterviewQuestion.id == data.question_id,
            InterviewQuestion.session_id == session_id,
        )
        result = await self._db.execute(stmt)
        question = result.scalar_one_or_none()
        if not question:
            raise NotFoundError("面试问题不存在")

        # 保存用户回答
        question.user_answer = data.user_answer
        question.answered_at = datetime.now(timezone.utc)

        # 评分
        try:
            score_data = await self._score_answer(
                question_text=question.question_text,
                user_answer=data.user_answer,
                reference_answer=question.reference_answer or "",
                knowledge_context=question.knowledge_source or "",
            )
            question.score = score_data.get("score", 0)
            question.score_comment = score_data.get("comment", "")
        except Exception as e:
            logger.error("评分失败: %s", e)
            question.score = 0
            question.score_comment = "评分服务暂时不可用"

        await self._db.flush()

        # 更新会话状态
        session = await self.get_session(session_id, user_id)
        answered = await self._count_answered(session_id)
        session.answered_questions = answered
        if answered >= session.total_questions:
            await self._complete_session(session)
        await self._db.flush()

        return question

    async def _generate_questions(
        self,
        direction: str,
        question_count: int,
        question_types: list[str],
        job_info: str = "",
    ) -> dict:
        """调用 LLM 生成面试问题。"""
        llm = get_default_llm()

        # 尝试 RAG 检索
        knowledge_context = ""
        try:
            retriever = get_retriever()
            results = await retriever.retrieve(
                query=direction,
                direction=direction,
                top_k=5,
            )
            if results:
                knowledge_context = "\n\n".join([
                    r["content"][:500] for r in results[:5]
                ])
        except Exception as e:
            logger.warning("RAG 检索失败: %s", e)

        prompt = get_interview_question_prompt(has_knowledge=bool(knowledge_context))
        chain = prompt | llm

        response = await chain.ainvoke({
            "job_info": job_info or f"面试方向: {direction}",
            "direction": direction,
            "question_count": question_count,
            "question_types": ", ".join(question_types),
            "difficulty": "medium",
            "knowledge_context": knowledge_context,
        })

        raw = response.content if hasattr(response, "content") else str(response)
        return self._parse_json(raw)

    async def _score_answer(
        self,
        question_text: str,
        user_answer: str,
        reference_answer: str,
        knowledge_context: str,
    ) -> dict:
        """调用 LLM 评分。"""
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
        return self._parse_json(raw)

    async def _count_answered(self, session_id: str) -> int:
        """统计已回答问题数。"""
        from sqlalchemy import func

        stmt = select(func.count()).select_from(InterviewQuestion).where(
            InterviewQuestion.session_id == session_id,
            InterviewQuestion.user_answer.isnot(None),
        )
        result = await self._db.execute(stmt)
        return result.scalar() or 0

    async def _complete_session(self, session: InterviewSession) -> None:
        """完成面试会话，计算平均分。"""
        stmt = select(InterviewQuestion).where(
            InterviewQuestion.session_id == session.id,
            InterviewQuestion.score.isnot(None),
        )
        result = await self._db.execute(stmt)
        scored_questions = result.scalars().all()

        if scored_questions:
            avg = sum(q.score for q in scored_questions) / len(scored_questions)
            session.avg_score = round(avg, 1)

        session.status = "completed"
        session.completed_at = datetime.now(timezone.utc)

    @staticmethod
    def _parse_json(raw: str) -> dict:
        """从 LLM 输出中解析 JSON。"""
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        import re
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return {"questions": []}