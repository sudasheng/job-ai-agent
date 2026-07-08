"""SQLAlchemy 模型基类 Mixin。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column


class UUIDMixin:
    """UUID 主键 Mixin。"""

    id: Mapped[str] = mapped_column(
        CHAR(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="UUID 主键",
    )


class TimestampMixin:
    """创建/更新时间戳 Mixin。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        comment="更新时间",
    )


class SoftDeleteMixin:
    """软删除 Mixin。"""

    is_deleted: Mapped[bool] = mapped_column(
        default=False,
        server_default="0",
        comment="是否已删除",
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
        comment="删除时间",
    )