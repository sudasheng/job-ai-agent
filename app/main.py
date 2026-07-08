"""FastAPI 应用入口 —— 应用工厂、中间件、生命周期管理。

启动方式:
    uv run uvicorn app.main:app --reload
    或
    python -m app.main
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.v1.router import router as api_v1_router
from app.core.config import get_settings
from app.core.database import close_db, init_db
from app.core.exceptions import AppException

# ---- 日志配置 ----
settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ---- 生命周期 ----
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    logger.info("=" * 60)
    logger.info("  %s v%s 启动中...", settings.APP_NAME, "1.0.0")
    logger.info("  环境: %s", settings.APP_ENV)
    logger.info("=" * 60)

    # 确保数据目录存在
    settings.ensure_data_dirs()

    # 初始化数据库表（开发环境）
    if settings.APP_ENV == "development":
        try:
            await init_db()
            logger.info("数据库表初始化完成")
        except Exception as e:
            logger.warning("数据库初始化跳过（可能 MySQL 未就绪）: %s", e)

    yield

    # 关闭数据库连接池
    await close_db()
    logger.info("应用已关闭")


# ---- 应用工厂 ----
def create_app() -> FastAPI:
    """创建 FastAPI 应用实例。"""
    app = FastAPI(
        title=settings.APP_NAME,
        description="AI-Powered Job Search Assistant System",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS 中间件 —— 支持前后端分离
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 全局异常处理
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.code,
            content={"code": exc.code, "message": exc.message, "data": None},
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception("未捕获的异常: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": "服务器内部错误", "data": None},
        )

    # 注册 API 路由
    app.include_router(api_v1_router)

    # 挂载静态文件
    static_dir = Path(__file__).parent.parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # 注册前端页面路由
    register_page_routes(app)

    return app


def register_page_routes(app: FastAPI) -> None:
    """注册前端页面路由（Jinja2 模板渲染）。"""
    template_dir = Path(__file__).parent / "templates"
    templates = Jinja2Templates(directory=str(template_dir))

    @app.get("/")
    async def index(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})

    @app.get("/job-search")
    async def job_search_page(request: Request):
        return templates.TemplateResponse("job_search.html", {"request": request})

    @app.get("/interview")
    async def interview_page(request: Request):
        return templates.TemplateResponse("interview.html", {"request": request})

    @app.get("/chat")
    async def chat_page(request: Request):
        return templates.TemplateResponse("chat.html", {"request": request})

    @app.get("/login")
    async def login_page(request: Request):
        return templates.TemplateResponse("login.html", {"request": request})


# ---- 应用实例 ----
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )