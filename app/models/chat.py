"""聊天记录模型。"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class ChatRecord(Base, UUIDMixin, TimestampMixin):
    """聊天记录表 —— 用户与 AI 的对话历史。"""

    __tablename__ = "chat_records"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户 ID"
    )
    role: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="角色: user/assistant/system"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="消息内容"
    )
    context_type: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="上下文类型: general/interview/job_search"
    )
    context_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, comment="关联上下文 ID（如面试会话 ID）"
    )
    token_count: Mapped[int | None] = mapped_column(
        nullable=True, comment="Token 消耗量"
    )

    # 关联
    user: Mapped["User"] = relationship(back_populates="chat_records")

    def __repr__(self) -> str:
        return f"<ChatRecord(role={self.role}, content={self.content[:50]})>"