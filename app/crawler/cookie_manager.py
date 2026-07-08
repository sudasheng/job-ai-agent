"""Cookie 管理器 —— 持久化、校验、过期处理。"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class CookieManager:
    """Cookie 管理器。

    负责：
    - 保存和加载 Cookie 文件
    - 校验 Cookie 是否过期
    - 清理过期 Cookie
    """

    def __init__(self, cookie_dir: str | None = None) -> None:
        self._cookie_dir = Path(
            settings.PROJECT_ROOT / (cookie_dir or settings.PLAYWRIGHT_COOKIE_DIR)
        )
        self._cookie_dir.mkdir(parents=True, exist_ok=True)

    def get_cookie_path(self, platform: str = "boss_zhipin") -> Path:
        """获取指定平台的 Cookie 文件路径。"""
        return self._cookie_dir / f"{platform}_cookies.json"

    def save_cookies(self, cookies: list[dict[str, Any]], platform: str = "boss_zhipin") -> None:
        """保存 Cookie 到文件。"""
        file_path = self.get_cookie_path(platform)
        data = {
            "cookies": cookies,
            "saved_at": datetime.now(UTC).isoformat(),
            "platform": platform,
        }
        file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Cookie 已保存: %s (%d 条)", file_path, len(cookies))

    def load_cookies(self, platform: str = "boss_zhipin") -> list[dict[str, Any]]:
        """加载 Cookie 文件。"""
        file_path = self.get_cookie_path(platform)
        if not file_path.exists():
            return []
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            return data.get("cookies", [])
        except Exception as e:
            logger.warning("Cookie 加载失败: %s", e)
            return []

    def is_cookie_valid(self, platform: str = "boss_zhipin", max_age_days: int = 7) -> bool:
        """检查 Cookie 是否仍然有效（未过期）。"""
        file_path = self.get_cookie_path(platform)
        if not file_path.exists():
            return False
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            saved_at = datetime.fromisoformat(data["saved_at"])
            return datetime.now(UTC) - saved_at < timedelta(days=max_age_days)
        except Exception:
            return False

    def delete_cookies(self, platform: str = "boss_zhipin") -> None:
        """删除指定平台的 Cookie 文件。"""
        file_path = self.get_cookie_path(platform)
        if file_path.exists():
            file_path.unlink()
            logger.info("Cookie 已删除: %s", file_path)


_cookie_manager: CookieManager | None = None


def get_cookie_manager() -> CookieManager:
    """获取 Cookie 管理器单例。"""
    global _cookie_manager
    if _cookie_manager is None:
        _cookie_manager = CookieManager()
    return _cookie_manager