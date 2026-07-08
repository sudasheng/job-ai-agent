"""面试相关模型：面试会话、面试问题、用户回答。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class InterviewSession(Base, UUIDMixin, TimestampMixin):
    """面试会话表 —— 一次完整的面试练习。"""

    __tablename__ = "interview_sessions"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户 ID"
    )
    title: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="面试标题"
    )
    direction: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True, comment="面试方向（如 Python后端、前端开发）"
    )
    job_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, comment="关联岗位 ID"
    )
    status: Mapped[str] = mapped_column(
        String(16), default="in_progress", comment="状态: in_progress/completed/abandoned"
    )
    total_questions: Mapped[int] = mapped_column(
        Integer, default=0, comment="总问题数"
    )
    answered_questions: Mapped[int] = mapped_column(
        Integer, default=0, comment="已回答数"
    )
    avg_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="平均得分"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="开始时间"
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="完成时间"
    )

    # 关联
    user: Mapped["User"] = relationship(back_populates="interview_sessions")
    questions: Mapped[list["InterviewQuestion"]] = relationship(
        back_populates="session",
        lazy="selectin",
        order_by="InterviewQuestion.sequence",
    )

    def __repr__(self) -> str:
        return f"<InterviewSession(title={self.title}, direction={self.direction})>"


class InterviewQuestion(Base, UUIDMixin, TimestampMixin):
    """面试问题表 —— 单次面试中的一个问题。"""

    __tablename__ = "interview_questions"

    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True, comment="面试会话 ID"
    )
    sequence: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="问题序号"
    )
    question_text: Mapped[str] = mapped_column(
        Text, nullable=False, comment="问题文本"
    )
    question_type: Mapped[str] = mapped_column(
        String(32), default="technical", comment="问题类型: technical/behavioral/scenario/theory"
    )
    reference_answer: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="参考答案"
    )
    knowledge_source: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="知识来源（RAG 检索到的文档 ID）"
    )
    user_answer: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="用户回答"
    )
    score: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="评分"
    )
    score_comment: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="评分备注"
    )
    answered_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="回答时间"
    )

    # 关联
    session: Mapped["InterviewSession"] = relationship(back_populates="questions")

    def __repr__(self) -> str:
        return f"<InterviewQuestion(seq={self.sequence}, question={self.question_text[:50]})>"