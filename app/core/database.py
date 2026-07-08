"""MySQL 数据库连接管理 —— 异步 SQLAlchemy 引擎与会话工厂。"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

# ---- 异步引擎 ----
engine = create_async_engine(
    settings.MYSQL_DATABASE_URL,
    pool_size=settings.MYSQL_POOL_SIZE,
    max_overflow=settings.MYSQL_MAX_OVERFLOW,
    echo=settings.MYSQL_ECHO,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# ---- 会话工厂 ----
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类。"""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入用 —— 获取数据库会话，请求结束后自动关闭。"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """创建所有表（开发环境用，生产请使用 Alembic 迁移）。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """关闭数据库引擎连接池。"""
    await engine.dispose()