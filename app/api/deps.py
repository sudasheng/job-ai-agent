"""API 依赖注入 —— 认证中间件、获取当前用户。"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """获取当前登录用户（可选认证）。

    如果请求头中没有 Token，返回 None。
    如果有 Token 但无效，返回 None（不抛出异常，由业务层处理）。
    """
    if not credentials:
        return None

    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            return None
    except ValueError:
        return None

    stmt = select(User).where(User.id == user_id, User.is_active == True)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def require_user(
    current_user: User | None = Depends(get_current_user),
) -> User:
    """获取当前用户（必须登录）。

    如果未认证，抛出 401 异常。
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user