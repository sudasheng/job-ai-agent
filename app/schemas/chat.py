"""聊天相关 Schema。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ChatSendRequest(BaseModel):
    """发送聊天消息请求。"""

    content: str = Field(min_length=1, max_length=4096, description="消息内容")
    context_type: str | None = Field(
        default="general",
        description="上下文类型: general/interview/job_search",
    )
    context_id: str | None = Field(default=None, description="关联上下文 ID")
    history_limit: int = Field(default=10, ge=0, le=50, description="携带的历史消息数")


class ChatStreamRequest(BaseModel):
    """流式聊天请求。"""

    content: str = Field(min_length=1, max_length=4096, description="消息内容")
    context_type: str | None = Field(default="general")
    context_id: str | None = Field(default=None)
    history_limit: int = Field(default=10, ge=0, le=50)


class ChatRecordResponse(BaseModel):
    """聊天记录响应。"""

    id: str
    role: str
    content: str
    context_type: str | None = None
    context_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatHistoryResponse(BaseModel):
    """聊天历史响应。"""

    records: list[ChatRecordResponse]
    total: int