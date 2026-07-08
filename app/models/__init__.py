"""模型聚合 —— 统一导入所有模型，用于 Alembic 自动发现。"""

from app.core.database import Base
from app.models.chat import ChatRecord
from app.models.interview import InterviewQuestion, InterviewSession
from app.models.job import Job
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Job",
    "InterviewSession",
    "InterviewQuestion",
    "ChatRecord",
]