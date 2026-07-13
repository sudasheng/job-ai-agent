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


# ---- LangGraph 面试流程专用 ----

class InterviewGraphStartRequest(BaseModel):
    """开始/继续 LangGraph 面试请求。"""

    user_input: str = Field(min_length=1, description="用户输入（岗位描述/答题内容）")
    session_id: str | None = Field(default=None, description="已有会话 ID，新会话传 None")


class InterviewGraphResponse(BaseModel):
    """LangGraph 面试响应。"""

    type: str = Field(description="响应类型：question / report / hint / error")
    round: int | None = Field(default=None, description="当前轮次（type=question 时有值）")
    question: str | None = Field(default=None, description="面试题目")
    content: str | None = Field(default=None, description="评分报告内容（type=report 时有值）")
    msg: str | None = Field(default=None, description="提示/错误消息")
    session_id: str | None = Field(default=None, description="会话 ID（新会话时返回）")

    model_config = {"from_attributes": True}