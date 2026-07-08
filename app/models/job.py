"""岗位信息模型。"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class Job(Base, UUIDMixin, TimestampMixin):
    """岗位信息表 —— 存储从 Boss 直聘等渠道抓取的岗位数据。"""

    __tablename__ = "jobs"

    # 来源信息
    source: Mapped[str] = mapped_column(
        String(32), default="boss_zhipin", index=True, comment="数据来源"
    )
    source_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True, index=True, comment="来源平台 ID"
    )
    source_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="来源 URL"
    )

    # 岗位基本信息
    title: Mapped[str] = mapped_column(
        String(256), nullable=False, index=True, comment="岗位名称"
    )
    company_name: Mapped[str] = mapped_column(
        String(256), nullable=False, index=True, comment="公司名称"
    )
    city: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True, comment="工作城市"
    )
    district: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="区域"
    )
    salary_min: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="最低薪资(K)"
    )
    salary_max: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="最高薪资(K)"
    )
    salary_desc: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="薪资描述原文"
    )

    # 岗位详情
    experience: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="经验要求"
    )
    education: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="学历要求"
    )
    job_description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="岗位描述"
    )
    job_requirements: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="岗位要求"
    )
    tags: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="标签，JSON 数组字符串"
    )

    # 公司信息
    company_industry: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="公司行业"
    )
    company_scale: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="公司规模"
    )
    company_logo: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="公司 Logo URL"
    )

    # 招聘者信息
    hr_name: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="HR/招聘者名称"
    )
    hr_title: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="HR 职位"
    )

    # 状态
    status: Mapped[str] = mapped_column(
        String(16), default="active", comment="状态: active/closed/deleted"
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="发布日期"
    )
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(), comment="抓取时间"
    )

    # 向量化标记
    is_vectorized: Mapped[bool] = mapped_column(
        default=False, comment="是否已向量化存入 ChromaDB"
    )

    def get_tags(self) -> list[str]:
        """解析 tags JSON 字段。"""
        if not self.tags:
            return []
        try:
            return json.loads(self.tags)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_tags(self, tags: list[str]) -> None:
        """设置 tags JSON 字段。"""
        self.tags = json.dumps(tags, ensure_ascii=False)

    def to_search_text(self) -> str:
        """拼接用于向量检索的文本。"""
        parts = [
            self.title or "",
            self.company_name or "",
            self.job_description or "",
            self.job_requirements or "",
            self.city or "",
            self.experience or "",
            self.education or "",
        ]
        return " ".join(filter(None, parts))

    def __repr__(self) -> str:
        return f"<Job(title={self.title}, company={self.company_name})>"