"""岗位抓取 Skill —— 根据用户输入抓取 Boss 直聘岗位信息。"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.tools import tool

from app.crawler.boss_crawler import BossZhipinCrawler

logger = logging.getLogger(__name__)


@tool
async def scrape_jobs_by_keyword(keyword: str, city: str | None = None, max_pages: int = 3) -> str:
    """根据关键词搜索并抓取 Boss 直聘的岗位信息。

    Args:
        keyword: 搜索关键词，如 "Python后端开发"、"前端开发"
        city: 城市编码，如 "101010100"(北京)，留空默认北京
        max_pages: 最大抓取页数，默认 3

    Returns:
        JSON 格式的岗位列表
    """
    crawler = BossZhipinCrawler()
    try:
        await crawler.start()
        is_logged = await crawler.check_login()
        if not is_logged:
            return json.dumps({
                "error": "未登录",
                "message": "请先扫码登录 Boss 直聘",
                "action": "login_required",
            }, ensure_ascii=False)

        jobs = await crawler.search_jobs(keyword, city=city, max_pages=max_pages)
        return json.dumps({
            "total": len(jobs),
            "keyword": keyword,
            "jobs": jobs,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("岗位抓取失败: %s", e)
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        await crawler.close()


@tool
async def scrape_job_detail_by_url(url: str) -> str:
    """根据 URL 抓取单个岗位的详细信息。

    Args:
        url: Boss 直聘岗位详情页 URL

    Returns:
        JSON 格式的岗位详情
    """
    crawler = BossZhipinCrawler()
    try:
        await crawler.start()
        is_logged = await crawler.check_login()
        if not is_logged:
            return json.dumps({
                "error": "未登录",
                "message": "请先扫码登录 Boss 直聘",
                "action": "login_required",
            }, ensure_ascii=False)

        detail = await crawler.get_job_detail(url)
        return json.dumps(detail, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("岗位详情抓取失败: %s", e)
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        await crawler.close()