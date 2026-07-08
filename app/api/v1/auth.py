"""认证相关 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.common import ResponseModel
from app.schemas.user import (
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=ResponseModel[UserResponse], status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    """用户注册。"""
    service = UserService(db)
    user = await service.register(data)
    return ResponseModel(
        code=201,
        message="注册成功",
        data=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=ResponseModel[TokenResponse])
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    """用户登录。"""
    service = UserService(db)
    result = await service.login(data)
    return ResponseModel(
        message="登录成功",
        data=TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"],
            expires_in=result["expires_in"],
            user=UserResponse.model_validate(result["user"]),
        ),
    )


@router.post("/refresh", response_model=ResponseModel[TokenResponse])
async def refresh_token(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """刷新 Access Token。"""
    service = UserService(db)
    result = await service.refresh_token(data.refresh_token)
    return ResponseModel(
        message="Token 刷新成功",
        data=TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"],
            expires_in=result["expires_in"],
            user=UserResponse.model_validate(result["user"]),
        ),
    )


@router.get("/me", response_model=ResponseModel[UserResponse])
async def get_me(current_user: User = Depends(require_user)):
    """获取当前用户信息。"""
    return ResponseModel(data=UserResponse.model_validate(current_user))


@router.put("/me", response_model=ResponseModel[UserResponse])
async def update_me(
    data: UserUpdate,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """更新当前用户信息。"""
    service = UserService(db)
    user = await service.update_profile(current_user.id, data)
    return ResponseModel(
        message="更新成功",
        data=UserResponse.model_validate(user),
    )