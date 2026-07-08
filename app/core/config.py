"""应用配置管理 —— 基于 pydantic-settings 从环境变量 / .env 加载配置。"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局应用配置。

    所有配置项均通过环境变量注入，优先级：环境变量 > .env 文件 > 默认值。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- 应用 ----
    APP_NAME: str = "JobAIAgent"
    APP_ENV: str = "development"
    APP_DEBUG: bool = False
    APP_SECRET_KEY: str = "change-me"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # ---- 项目根目录 ----
    @property
    def PROJECT_ROOT(self) -> Path:
        return Path(__file__).resolve().parent.parent

    # ---- MySQL ----
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "job_ai_agent"
    MYSQL_POOL_SIZE: int = 20
    MYSQL_MAX_OVERFLOW: int = 40
    MYSQL_ECHO: bool = False

    @property
    def MYSQL_DATABASE_URL(self) -> str:
        return (
            f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

    @property
    def MYSQL_DATABASE_URL_SYNC(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

    # ---- ChromaDB ----
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    CHROMA_COLLECTION_NAME: str = "job_knowledge"

    # ---- DeepSeek LLM ----
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_TEMPERATURE: float = 0.7
    DEEPSEEK_MAX_TOKENS: int = 4096

    # ---- 千问 Embedding ----
    QWEN_API_KEY: str = ""
    QWEN_EMBEDDING_MODEL: str = "text-embedding-v3"
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # ---- Playwright ----
    PLAYWRIGHT_HEADLESS: bool = False
    PLAYWRIGHT_COOKIE_DIR: str = "./data/cookies"
    PLAYWRIGHT_TIMEOUT: int = 30000

    # ---- JWT ----
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ---- 日志 ----
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./data/logs/app.log"

    # ---- CORS ----
    CORS_ORIGINS: str = '["http://localhost:3000","http://localhost:8000"]'

    def get_cors_origins(self) -> list[str]:
        try:
            return json.loads(self.CORS_ORIGINS)
        except (json.JSONDecodeError, TypeError):
            return ["*"]

    # ---- 数据目录 ----
    def ensure_data_dirs(self) -> None:
        """确保运行时需要的目录存在。"""
        dirs = [
            self.PROJECT_ROOT / self.CHROMA_PERSIST_DIR,
            self.PROJECT_ROOT / self.PLAYWRIGHT_COOKIE_DIR,
            Path(self.LOG_FILE).parent,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()