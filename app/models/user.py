"""用户模型。"""

from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    """用户表。"""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True, comment="用户名"
    )
    email: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True, comment="邮箱"
    )
    hashed_password: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="密码哈希"
    )
    nickname: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="昵称"
    )
    avatar_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="头像 URL"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="是否激活"
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否超级管理员"
    )
    bio: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="个人简介"
    )

    # 关联
    interview_sessions: Mapped[list["InterviewSession"]] = relationship(
        back_populates="user", lazy="selectin"
    )
    chat_records: Mapped[list["ChatRecord"]] = relationship(
        back_populates="user", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"