"""用户服务 —— 注册、登录、信息管理。"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserUpdate

logger = logging.getLogger(__name__)


class UserService:
    """用户服务。"""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def register(self, data: UserCreate) -> User:
        """用户注册。"""
        # 检查用户名是否已存在
        stmt = select(User).where(User.username == data.username)
        result = await self._db.execute(stmt)
        if result.scalar_one_or_none():
            raise ConflictError("用户名已被注册")

        # 检查邮箱是否已存在
        stmt = select(User).where(User.email == data.email)
        result = await self._db.execute(stmt)
        if result.scalar_one_or_none():
            raise ConflictError("邮箱已被注册")

        user = User(
            username=data.username,
            email=data.email,
            hashed_password=hash_password(data.password),
            nickname=data.nickname or data.username,
        )
        self._db.add(user)
        await self._db.flush()
        await self._db.refresh(user)
        return user

    async def login(self, data: UserLogin) -> dict:
        """用户登录，返回 token。"""
        # 支持用户名或邮箱登录
        stmt = select(User).where(
            (User.username == data.username) | (User.email == data.username)
        )
        result = await self._db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not verify_password(data.password, user.hashed_password):
            raise UnauthorizedError("用户名或密码错误")

        if not user.is_active:
            raise UnauthorizedError("账号已被禁用")

        token_data = {"sub": user.id, "username": user.username}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 60 * 60,  # 默认 1 小时
            "user": user,
        }

    async def refresh_token(self, refresh_token: str) -> dict:
        """刷新 Access Token。"""
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise UnauthorizedError("无效的刷新令牌")
        except ValueError as e:
            raise UnauthorizedError(str(e)) from e

        user_id = payload.get("sub")
        user = await self.get_by_id(user_id)
        if not user:
            raise UnauthorizedError("用户不存在")

        token_data = {"sub": user.id, "username": user.username}
        access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": 60 * 60,
            "user": user,
        }

    async def get_by_id(self, user_id: str) -> User | None:
        """根据 ID 获取用户。"""
        stmt = select(User).where(User.id == user_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """根据用户名获取用户。"""
        stmt = select(User).where(User.username == username)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_profile(self, user_id: str, data: UserUpdate) -> User:
        """更新用户信息。"""
        user = await self.get_by_id(user_id)
        if not user:
            raise NotFoundError("用户不存在")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        user.updated_at = datetime.now(UTC)
        await self._db.flush()
        await self._db.refresh(user)
        return user