"""用户相关 Schema。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """用户注册请求。"""

    username: str = Field(min_length=3, max_length=64, description="用户名")
    email: EmailStr = Field(description="邮箱")
    password: str = Field(min_length=6, max_length=128, description="密码")
    nickname: str | None = Field(default=None, max_length=64, description="昵称")


class UserLogin(BaseModel):
    """用户登录请求。"""

    username: str = Field(description="用户名或邮箱")
    password: str = Field(description="密码")


class UserUpdate(BaseModel):
    """用户信息更新请求。"""

    nickname: str | None = Field(default=None, max_length=64)
    avatar_url: str | None = Field(default=None, max_length=512)
    bio: str | None = Field(default=None, max_length=1024)


class UserResponse(BaseModel):
    """用户信息响应。"""

    id: str
    username: str
    email: str
    nickname: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    is_active: bool = True
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """登录令牌响应。"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="过期时间(秒)")
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求。"""

    refresh_token: str = Field(description="Refresh Token")