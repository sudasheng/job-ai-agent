"""Boss 直聘爬虫 —— 基于 Playwright 的浏览器自动化抓取。

功能：
1. 二维码手动登录 + Cookie 持久化
2. 批量搜索岗位并抓取
3. 单个岗位详情抓取
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class BossZhipinCrawler:
    """Boss 直聘爬虫。

    使用 Playwright 驱动真实浏览器，支持：
    - 二维码扫码登录
    - Cookie 持久化，避免重复登录
    - 岗位搜索 + 列表抓取
    - 岗位详情抓取
    """

    BASE_URL = "https://www.zhipin.com"
    LOGIN_URL = "https://www.zhipin.com/web/user/?ka=header-login"
    SEARCH_URL = "https://www.zhipin.com/web/geek/job"

    def __init__(self) -> None:
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._cookie_dir = Path(settings.PROJECT_ROOT) / settings.PLAYWRIGHT_COOKIE_DIR
        self._cookie_dir.mkdir(parents=True, exist_ok=True)
        self._cookie_file = self._cookie_dir / "boss_cookies.json"

    async def start(self) -> None:
        """启动浏览器。"""
        playwright = await async_playwright().start()
        self._browser = await playwright.chromium.launch(
            headless=settings.PLAYWRIGHT_HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        # 加载已保存的 Cookie
        await self._load_cookies()

    async def close(self) -> None:
        """关闭浏览器。"""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()

    # ---- Cookie 管理 ----

    @property
    def cookie_file_path(self) -> Path:
        return self._cookie_file

    async def _save_cookies(self) -> None:
        """保存当前 Cookie 到文件。"""
        if not self._context:
            return
        cookies = await self._context.cookies()
        self._cookie_file.write_text(
            json.dumps(cookies, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Cookie 已保存到 %s", self._cookie_file)

    async def _load_cookies(self) -> bool:
        """从文件加载 Cookie。"""
        if not self._context or not self._cookie_file.exists():
            return False
        try:
            cookies = json.loads(self._cookie_file.read_text(encoding="utf-8"))
            await self._context.add_cookies(cookies)
            logger.info("Cookie 已加载（%d 条）", len(cookies))
            return True
        except Exception as e:
            logger.warning("Cookie 加载失败: %s", e)
            return False

    # ---- 登录 ----

    async def login_with_qr(self) -> bool:
        """使用二维码扫码登录。

        打开登录页面，等待用户扫码完成。
        扫码成功后自动保存 Cookie。
        """
        if not self._context:
            await self.start()

        page = await self._context.new_page()
        try:
            await page.goto(self.LOGIN_URL, wait_until="networkidle", timeout=60000)
            logger.info("请使用 Boss 直聘 App 扫描页面上的二维码登录...")

            # 等待扫码完成 —— 检测页面跳转到 web 首页或出现用户信息
            await page.wait_for_url(
                "**/web/geek/**",
                timeout=300000,  # 5 分钟超时
            )
            logger.info("登录成功！")

            await self._save_cookies()
            return True

        except Exception as e:
            logger.error("登录失败: %s", e)
            return False
        finally:
            await page.close()

    async def check_login(self) -> bool:
        """检查是否已登录。"""
        if not self._context:
            return False
        page = await self._context.new_page()
        try:
            await page.goto(self.BASE_URL + "/web/geek/job", wait_until="networkidle", timeout=30000)
            # 如果被重定向到登录页，说明未登录
            return "/web/user/" not in page.url
        except Exception:
            return False
        finally:
            await page.close()

    # ---- 岗位搜索 ----

    async def search_jobs(
        self,
        keyword: str,
        city: str | None = None,
        page_num: int = 1,
        max_pages: int = 3,
    ) -> list[dict[str, Any]]:
        """搜索岗位列表。

        Args:
            keyword: 搜索关键词（如 "Python后端"）
            city: 城市编码（如 "101010100" 表示北京）
            page_num: 起始页码
            max_pages: 最大抓取页数

        Returns:
            岗位信息列表
        """
        if not self._context:
            await self.start()

        all_jobs: list[dict[str, Any]] = []
        page = await self._context.new_page()

        try:
            for p in range(page_num, page_num + max_pages):
                url = self._build_search_url(keyword, city, p)
                logger.info("搜索岗位: %s (第%d页)", keyword, p)

                await page.goto(url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)  # 等待动态渲染

                # 解析岗位列表
                html = await page.content()
                jobs = self._parse_job_list(html)
                all_jobs.extend(jobs)

                if not jobs:
                    break  # 没有更多结果

                await asyncio.sleep(1.5)  # 反爬间隔

            logger.info("共抓取 %d 个岗位", len(all_jobs))
            return all_jobs

        except Exception as e:
            logger.error("岗位搜索失败: %s", e)
            raise
        finally:
            await page.close()

    async def get_job_detail(self, job_url: str) -> dict[str, Any]:
        """抓取单个岗位详情页。

        Args:
            job_url: 岗位详情页 URL

        Returns:
            岗位详细信息
        """
        if not self._context:
            await self.start()

        page = await self._context.new_page()
        try:
            await page.goto(job_url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)

            html = await page.content()
            return self._parse_job_detail(html, job_url)

        except Exception as e:
            logger.error("岗位详情抓取失败: %s", e)
            raise
        finally:
            await page.close()

    # ---- 解析方法 ----

    def _build_search_url(self, keyword: str, city: str | None = None, page: int = 1) -> str:
        """构建搜索 URL。"""
        import urllib.parse
        query = urllib.parse.quote(keyword)
        city_code = city or "101010100"  # 默认北京
        return f"{self.SEARCH_URL}?query={query}&city={city_code}&page={page}"

    def _parse_job_list(self, html: str) -> list[dict[str, Any]]:
        """解析岗位列表页 HTML。"""
        soup = BeautifulSoup(html, "lxml")
        jobs = []

        # Boss 直聘岗位卡片选择器（需要根据实际页面结构调整）
        job_cards = soup.select(".job-card-wrapper, .job-card-box, li.job-card-item")
        if not job_cards:
            job_cards = soup.select('[class*="job-card"]')

        for card in job_cards:
            try:
                job = self._extract_job_card_info(card)
                if job and job.get("title"):
                    jobs.append(job)
            except Exception as e:
                logger.debug("解析岗位卡片失败: %s", e)
                continue

        return jobs

    def _extract_job_card_info(self, card: Any) -> dict[str, Any] | None:
        """从单个岗位卡片提取信息。"""
        # 岗位名称
        title_el = card.select_one(".job-name, .job-title, [class*='job-name']")
        title = title_el.get_text(strip=True) if title_el else ""

        # 公司名称
        company_el = card.select_one(".company-name, .company-text, [class*='company-name']")
        company_name = company_el.get_text(strip=True) if company_el else ""

        # 薪资
        salary_el = card.select_one(".salary, .red, [class*='salary']")
        salary_desc = salary_el.get_text(strip=True) if salary_el else ""

        # 经验/学历
        info_el = card.select_one(".job-info, .tag-list, [class*='job-info']")
        info_text = info_el.get_text(strip=True) if info_el else ""

        # 标签
        tag_els = card.select(".tag-item, [class*='tag-item']")
        tags = [t.get_text(strip=True) for t in tag_els]

        # 链接
        link_el = card.select_one("a[href*='/job_detail/']")
        link = link_el.get("href", "") if link_el else ""
        if link and not link.startswith("http"):
            link = self.BASE_URL + link

        if not title or not company_name:
            return None

        salary_min, salary_max = self._parse_salary(salary_desc)

        return {
            "source": "boss_zhipin",
            "source_id": self._extract_job_id(link),
            "source_url": link,
            "title": title,
            "company_name": company_name,
            "salary_desc": salary_desc,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "experience": self._extract_experience(info_text),
            "education": self._extract_education(info_text),
            "tags": tags,
            "scraped_at": datetime.now(UTC).isoformat(),
        }

    def _parse_job_detail(self, html: str, url: str = "") -> dict[str, Any]:
        """解析岗位详情页 HTML。"""
        soup = BeautifulSoup(html, "lxml")

        # 岗位名称
        title_el = soup.select_one(".name, .job-name, h1")
        title = title_el.get_text(strip=True) if title_el else ""

        # 公司名称
        company_el = soup.select_one(".company-name, .name")
        company_name = company_el.get_text(strip=True) if company_el else ""

        # 薪资
        salary_el = soup.select_one(".salary, .badge")
        salary_desc = salary_el.get_text(strip=True) if salary_el else ""

        # 岗位描述
        desc_el = soup.select_one(".job-detail, .job-sec, .text, [class*='job-detail']")
        job_description = desc_el.get_text("\n", strip=True) if desc_el else ""

        # 岗位要求
        req_el = soup.select_one(".job-requirement, [class*='requirement']")
        job_requirements = req_el.get_text("\n", strip=True) if req_el else ""

        # 经验/学历
        info_el = soup.select_one(".job-banner, .job-primary, [class*='job-banner']")
        info_text = info_el.get_text(strip=True) if info_el else ""

        # 公司信息
        company_info_el = soup.select_one(".company-info, .sider-company, [class*='company-info']")
        company_info_text = company_info_el.get_text("\n", strip=True) if company_info_el else ""

        salary_min, salary_max = self._parse_salary(salary_desc)

        return {
            "source": "boss_zhipin",
            "source_id": self._extract_job_id(url),
            "source_url": url,
            "title": title,
            "company_name": company_name,
            "salary_desc": salary_desc,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "job_description": job_description,
            "job_requirements": job_requirements,
            "experience": self._extract_experience(info_text),
            "education": self._extract_education(info_text),
            "company_industry": self._extract_industry(company_info_text),
            "company_scale": self._extract_scale(company_info_text),
            "scraped_at": datetime.now(UTC).isoformat(),
        }

    # ---- 工具方法 ----

    @staticmethod
    def _parse_salary(salary_text: str) -> tuple[int | None, int | None]:
        """解析薪资文本，如 '15K-25K' -> (15, 25)。"""
        match = re.search(r"(\d+)\s*[Kk]?\s*-\s*(\d+)\s*[Kk]?", salary_text)
        if match:
            return int(match.group(1)), int(match.group(2))
        match = re.search(r"(\d+)\s*[Kk]", salary_text)
        if match:
            val = int(match.group(1))
            return val, val
        return None, None

    @staticmethod
    def _extract_experience(text: str) -> str | None:
        """提取经验要求。"""
        match = re.search(r"(\d+[-~]\d+年|经验不限|应届生|\d+年经验)", text)
        return match.group(1) if match else None

    @staticmethod
    def _extract_education(text: str) -> str | None:
        """提取学历要求。"""
        match = re.search(r"(博士|硕士|本科|大专|学历不限)", text)
        return match.group(1) if match else None

    @staticmethod
    def _extract_industry(text: str) -> str | None:
        """提取行业信息。"""
        match = re.search(r"行业[:：]\s*(.+?)(?:\n|$)", text)
        return match.group(1).strip() if match else None

    @staticmethod
    def _extract_scale(text: str) -> str | None:
        """提取公司规模。"""
        match = re.search(r"规模[:：]\s*(.+?)(?:\n|$)", text)
        return match.group(1).strip() if match else None

    @staticmethod
    def _extract_job_id(url: str) -> str | None:
        """从 URL 中提取岗位 ID。"""
        match = re.search(r"/job_detail/(\w+)\.html", url)
        return match.group(1) if match else None


# ============================================================
# Demo: 独立运行测试
# ============================================================

async def demo():
    """爬虫演示 —— 手动二维码登录后抓取岗位。"""
    crawler = BossZhipinCrawler()

    try:
        await crawler.start()

        # 检查是否已登录
        is_logged_in = await crawler.check_login()
        if not is_logged_in:
            print("未登录，请扫描二维码登录...")
            success = await crawler.login_with_qr()
            if not success:
                print("登录失败")
                return

        # 搜索岗位
        keyword = input("请输入搜索关键词（如 Python后端）: ").strip() or "Python后端"
        print(f"正在搜索「{keyword}」...")
        jobs = await crawler.search_jobs(keyword, max_pages=2)

        print(f"\n共找到 {len(jobs)} 个岗位:")
        for i, job in enumerate(jobs, 1):
            print(f"{i}. {job['title']} | {job['company_name']} | {job.get('salary_desc', '')}")

        # 抓取第一个岗位的详情
        if jobs and jobs[0].get("source_url"):
            print(f"\n正在抓取详情: {jobs[0]['title']}")
            detail = await crawler.get_job_detail(jobs[0]["source_url"])
            print(f"岗位描述: {detail.get('job_description', '')[:200]}...")

    finally:
        await crawler.close()


if __name__ == "__main__":
    asyncio.run(demo())