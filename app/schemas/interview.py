"""面试相关 Schema。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class InterviewCreateRequest(BaseModel):
    """创建面试练习请求。"""

    direction: str = Field(description="面试方向（如 Python后端开发）")
    question_count: int = Field(default=5, ge=1, le=20, description="问题数量")
    question_types: list[str] = Field(
        default_factory=lambda: ["technical", "behavioral"],
        description="问题类型: technical/behavioral/scenario/theory",
    )
    job_id: str | None = Field(default=None, description="关联岗位 ID（可选，用于针对性面试）")
    job_url: str | None = Field(default=None, description="岗位 URL（可选，抓取岗位信息后生成针对性面试）")


class InterviewSessionResponse(BaseModel):
    """面试会话响应。"""

    id: str
    title: str
    direction: str
    status: str
    total_questions: int
    answered_questions: int
    avg_score: float | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class InterviewQuestionResponse(BaseModel):
    """面试问题响应。"""

    id: str
    sequence: int
    question_text: str
    question_type: str
    reference_answer: str | None = None
    knowledge_source: str | None = None
    user_answer: str | None = None
    score: float | None = None
    score_comment: str | None = None
    answered_at: datetime | None = None

    model_config = {"from_attributes": True}


class InterviewSessionDetailResponse(InterviewSessionResponse):
    """面试会话详情（含问题列表）。"""

    questions: list[InterviewQuestionResponse] = Field(default_factory=list)


class AnswerSubmitRequest(BaseModel):
    """提交答案请求。"""

    question_id: str = Field(description="问题 ID")
    user_answer: str = Field(min_length=1, description="用户回答")


class AnswerScoreResponse(BaseModel):
    """答案评分响应。"""

    question_id: str
    score: float
    comment: str
    passed: bool = Field(description="是否通过（>= 60 分）")

    model_config = {"from_attributes": True}