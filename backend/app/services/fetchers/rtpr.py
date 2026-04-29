"""
RTPR (Real-Time Press Release) 新闻采集器
- 从 Business Wire / PR Newswire / GlobeNewswire / AccessWire 获取一手新闻稿
- 支持按 Watchlist 公司逐个拉取
- API 文档: https://rtpr.io/docs
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.company import Company
from app.models.news import News
from app.services.dedup import DedupService

logger = logging.getLogger(__name__)

RTPR_BASE_URL = "https://api.rtpr.io"


class RTPRFetcher:
    """RTPR 一手新闻稿采集器"""

    def __init__(self, session: AsyncSession, redis):
        self.session = session
        self.redis = redis
        self.dedup = DedupService(redis)
        self.api_key = settings.RTPR_API_KEY

    async def fetch_company_news(
        self, ticker: str, limit: int = 100
    ) -> list[dict]:
        """
        从 RTPR 获取指定公司的新闻稿
        - ticker: 股票代码
        - limit: 返回数量（最多 100）
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{RTPR_BASE_URL}/articles/{ticker}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                params={"limit": min(limit, 100)},
            )
            resp.raise_for_status()
            data = resp.json()

            articles = data.get("articles", [])
            logger.info(
                f"[RTPR] {ticker}: 获取到 {len(articles)} 条新闻稿"
            )
            return articles

    async def fetch_latest(self, limit: int = 100) -> list[dict]:
        """
        从 RTPR 获取最新的所有新闻稿（不按 ticker 过滤）
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{RTPR_BASE_URL}/articles",
                headers={"Authorization": f"Bearer {self.api_key}"},
                params={"limit": min(limit, 100)},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("articles", [])

    async def fetch_all(self, tickers: Optional[list[str]] = None) -> dict:
        """
        采集所有 Watchlist 公司的新闻稿

        Args:
            tickers: 可选，只采集指定公司。为 None 时采集全部活跃公司

        Returns:
            统计信息 dict
        """
        if not self.api_key:
            return {
                "companies_processed": 0,
                "total_fetched": 0,
                "new_articles": 0,
                "errors": ["RTPR_API_KEY 未配置，请在 .env 中设置"],
            }

        # 获取目标公司列表
        query = select(Company).where(Company.is_active == True)
        if tickers:
            query = query.where(Company.ticker.in_([t.upper() for t in tickers]))

        result = await self.session.execute(query)
        companies = result.scalars().all()

        if not companies:
            return {
                "companies_processed": 0,
                "total_fetched": 0,
                "new_articles": 0,
                "errors": ["Watchlist 为空，请先添加公司"],
            }

        total_fetched = 0
        total_new = 0
        errors = []

        for company in companies:
            try:
                articles = await self.fetch_company_news(company.ticker)
                total_fetched += len(articles)

                for item in articles:
                    saved = await self._save_article(item, company)
                    if saved:
                        total_new += 1

                await self.session.commit()

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    logger.warning(f"[RTPR] {company.ticker}: 429 限速，等待 60s 后继续...")
                    import asyncio
                    await asyncio.sleep(60)
                    errors.append(f"{company.ticker}: 429 rate limited")
                else:
                    error_msg = f"{company.ticker}: HTTP {e.response.status_code}"
                    logger.error(f"[RTPR] {error_msg}")
                    errors.append(error_msg)
            except Exception as e:
                error_msg = f"{company.ticker}: {str(e)}"
                logger.error(f"[RTPR] {error_msg}")
                errors.append(error_msg)

            # ── 限速：每次请求之间等待 0.5s（RTPR 免费套餐约 2 req/s）──────────
            import asyncio
            await asyncio.sleep(0.5)

        return {
            "companies_processed": len(companies),
            "total_fetched": total_fetched,
            "new_articles": total_new,
            "errors": errors,
        }

    async def _save_article(self, item: dict, company: Company) -> bool:
        """
        保存单条新闻稿到数据库
        返回 True 表示新文章，False 表示已存在
        """
        title = (item.get("title") or "").strip()
        if not title:
            return False

        # 生成去重指纹
        fingerprint = DedupService.generate_fingerprint(
            source=item.get("author", "rtpr"),
            url="",  # RTPR 没有提供 URL 字段
            headline=title,
        )

        # Redis 去重检查
        if await self.dedup.is_duplicate(fingerprint):
            return False

        # 解析发布时间
        published_at = self._parse_datetime(item.get("created"))

        # 新闻稿正文（RTPR 提供完整正文！）
        body = item.get("article_body", "")
        summary = body[:500] if body else title

        # 创建新闻记录
        news = News(
            company_id=company.id,
            title=title,
            content=body,  # 完整的一手新闻稿正文
            summary=summary,
            source="rtpr",
            source_url="",
            category="press_release",
            fingerprint=fingerprint,
            published_at=published_at,
        )

        try:
            self.session.add(news)
            await self.session.flush()
            return True
        except IntegrityError:
            await self.session.rollback()
            logger.debug(f"[RTPR] 重复新闻（DB 去重）: {title[:50]}")
            return False

    @staticmethod
    def _parse_datetime(date_str: Optional[str]) -> Optional[datetime]:
        """解析 RTPR 返回的时间字符串"""
        if not date_str:
            return None
        try:
            # RTPR 格式: "Mon, 28 Jul 2025 16:30:00 -0400" 或 ISO 格式
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except Exception:
            try:
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except Exception:
                return None
