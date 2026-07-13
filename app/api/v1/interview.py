"""面试相关 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse, ResponseModel
from app.schemas.interview import (
    AnswerScoreResponse,
    AnswerSubmitRequest,
    InterviewCreateRequest,
    InterviewGraphResponse,
    InterviewGraphStartRequest,
    InterviewSessionDetailResponse,
    InterviewSessionResponse,
)
from app.services.interview_graph_service import InterviewGraphService
from app.services.interview_service import InterviewService

router = APIRouter(prefix="/interview", tags=["面试"])


@router.post("/sessions", response_model=ResponseModel[InterviewSessionResponse])
async def create_session(
    data: InterviewCreateRequest,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """创建面试练习会话。"""
    service = InterviewService(db)
    session = await service.create_session(current_user.id, data)
    return ResponseModel(
        message="面试会话创建成功",
        data=InterviewSessionResponse.model_validate(session),
    )


@router.get("/sessions", response_model=ResponseModel[PaginatedResponse[InterviewSessionResponse]])
async def list_sessions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """获取面试会话列表。"""
    service = InterviewService(db)
    sessions, total = await service.list_sessions(current_user.id, page, page_size)

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return ResponseModel(
        data=PaginatedResponse(
            items=[InterviewSessionResponse.model_validate(s) for s in sessions],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )


@router.get("/sessions/{session_id}", response_model=ResponseModel[InterviewSessionDetailResponse])
async def get_session(
    session_id: str,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """获取面试会话详情（含问题列表）。"""
    service = InterviewService(db)
    session = await service.get_session(session_id, current_user.id)
    return ResponseModel(
        data=InterviewSessionDetailResponse.model_validate(session),
    )


@router.post("/sessions/{session_id}/answer", response_model=ResponseModel[AnswerScoreResponse])
async def submit_answer(
    session_id: str,
    data: AnswerSubmitRequest,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """提交面试答案并获取评分。"""
    service = InterviewService(db)
    question = await service.submit_answer(session_id, current_user.id, data)
    return ResponseModel(
        message="评分完成",
        data=AnswerScoreResponse(
            question_id=question.id,
            score=question.score or 0,
            comment=question.score_comment or "",
            passed=(question.score or 0) >= 60,
        ),
    )


# ==================== LangGraph + ReAct 面试流程 API ====================

@router.post("/graph/start", response_model=ResponseModel[InterviewGraphResponse])
async def start_graph_interview(
    data: InterviewGraphStartRequest,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """启动/继续 LangGraph 面试会话。

    首次调用：传入岗位描述（文字/链接），ReAct 子图自动采集岗位信息。
    后续调用：传入答题内容，主图自动生成下一题或最终报告。
    """
    service = InterviewGraphService(db)
    result = await service.start_or_continue_session(
        user_id=current_user.id,
        user_input=data.user_input,
        session_id=data.session_id,
    )
    return ResponseModel(
        message="处理完成",
        data=InterviewGraphResponse(**result),
    )


@router.get("/graph/{session_id}", response_model=ResponseModel)
async def get_graph_session(
    session_id: str,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 LangGraph 面试会话详情（含状态图当前状态）。"""
    service = InterviewGraphService(db)
    detail = await service.get_session_detail(session_id, current_user.id)
    return ResponseModel(data=detail)