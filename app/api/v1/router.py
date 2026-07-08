"""API v1 路由聚合。"""

from fastapi import APIRouter

from app.api.v1 import auth, chat, interview, jobs

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(jobs.router)
router.include_router(interview.router)
router.include_router(chat.router)