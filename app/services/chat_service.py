"""聊天服务 —— 对话管理、历史记录、LLM 调用。"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.deepseek import get_default_llm
from app.llm.prompts import get_chat_prompt
from app.models.chat import ChatRecord

logger = logging.getLogger(__name__)


class ChatService:
    """聊天服务。"""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def send_message(
        self,
        user_id: str,
        content: str,
        context_type: str = "general",
        context_id: str | None = None,
        history_limit: int = 10,
    ) -> dict[str, Any]:
        """发送消息并获取 AI 回复。"""
        # 保存用户消息
        user_msg = ChatRecord(
            user_id=user_id,
            role="user",
            content=content,
            context_type=context_type,
            context_id=context_id,
        )
        self._db.add(user_msg)

        # 获取历史消息
        history = await self.get_history(
            user_id=user_id,
            context_type=context_type,
            context_id=context_id,
            limit=history_limit,
        )

        # 构建对话上下文
        messages = self._build_messages(history, content)

        # 调用 LLM
        llm = get_default_llm()
        prompt = get_chat_prompt()
        chain = prompt | llm
        response = await chain.ainvoke({
            "user_input": content,
            "chat_history": messages,
        })

        reply_text = response.content if hasattr(response, "content") else str(response)

        # 保存 AI 回复
        assistant_msg = ChatRecord(
            user_id=user_id,
            role="assistant",
            content=reply_text,
            context_type=context_type,
            context_id=context_id,
        )
        self._db.add(assistant_msg)
        await self._db.flush()

        return {
            "user_message": {
                "id": user_msg.id,
                "role": "user",
                "content": content,
            },
            "assistant_message": {
                "id": assistant_msg.id,
                "role": "assistant",
                "content": reply_text,
            },
        }

    async def send_message_stream(
        self,
        user_id: str,
        content: str,
        context_type: str = "general",
        context_id: str | None = None,
        history_limit: int = 10,
    ):
        """流式发送消息（生成器）。"""
        # 保存用户消息
        user_msg = ChatRecord(
            user_id=user_id,
            role="user",
            content=content,
            context_type=context_type,
            context_id=context_id,
        )
        self._db.add(user_msg)

        history = await self.get_history(
            user_id=user_id,
            context_type=context_type,
            context_id=context_id,
            limit=history_limit,
        )

        messages = self._build_messages(history, content)

        llm = get_default_llm(streaming=True)
        prompt = get_chat_prompt()

        full_reply = ""
        async for chunk in llm.astream(prompt.format(user_input=content)):
            chunk_text = chunk.content if hasattr(chunk, "content") else str(chunk)
            if chunk_text:
                full_reply += chunk_text
                yield chunk_text

        # 保存 AI 回复
        assistant_msg = ChatRecord(
            user_id=user_id,
            role="assistant",
            content=full_reply,
            context_type=context_type,
            context_id=context_id,
        )
        self._db.add(assistant_msg)
        await self._db.flush()

    async def get_history(
        self,
        user_id: str,
        context_type: str | None = None,
        context_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ChatRecord], int]:
        """获取聊天历史。"""
        stmt = select(ChatRecord).where(ChatRecord.user_id == user_id)

        if context_type:
            stmt = stmt.where(ChatRecord.context_type == context_type)
        if context_id:
            stmt = stmt.where(ChatRecord.context_id == context_id)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self._db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.order_by(desc(ChatRecord.created_at)).offset(offset).limit(limit)
        result = await self._db.execute(stmt)
        records = list(result.scalars().all())

        return records, total

    def _build_messages(
        self,
        history: tuple[list[ChatRecord], int],
        current_content: str,
    ) -> list[dict[str, str]]:
        """构建 LLM 对话消息列表。"""
        records, _ = history
        messages: list[dict[str, str]] = []
        # 按时间正序排列
        for record in reversed(records):
            messages.append({"role": record.role, "content": record.content})
        return messages