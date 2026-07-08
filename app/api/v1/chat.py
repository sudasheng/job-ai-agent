"""聊天相关 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.chat import ChatHistoryResponse, ChatRecordResponse, ChatSendRequest
from app.schemas.common import ResponseModel
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["聊天"])


@router.post("/send", response_model=ResponseModel)
async def send_message(
    data: ChatSendRequest,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """发送消息并获取 AI 回复。"""
    service = ChatService(db)
    result = await service.send_message(
        user_id=current_user.id,
        content=data.content,
        context_type=data.context_type or "general",
        context_id=data.context_id,
        history_limit=data.history_limit,
    )
    return ResponseModel(data=result, message="回复成功")


@router.post("/stream")
async def send_message_stream(
    data: ChatSendRequest,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """流式发送消息并获取 AI 回复（SSE）。"""
    service = ChatService(db)

    async def event_generator():
        async for chunk in service.send_message_stream(
            user_id=current_user.id,
            content=data.content,
            context_type=data.context_type or "general",
            context_id=data.context_id,
            history_limit=data.history_limit,
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history", response_model=ResponseModel[ChatHistoryResponse])
async def get_history(
    context_type: str | None = Query(default=None, description="上下文类型"),
    context_id: str | None = Query(default=None, description="关联上下文 ID"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """获取聊天历史。"""
    service = ChatService(db)
    records, total = await service.get_history(
        user_id=current_user.id,
        context_type=context_type,
        context_id=context_id,
        limit=limit,
        offset=offset,
    )
    return ResponseModel(
        data=ChatHistoryResponse(
            records=[ChatRecordResponse.model_validate(r) for r in records],
            total=total,
        ),
    )