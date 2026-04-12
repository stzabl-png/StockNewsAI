"""
Finnhub 新闻采集器
- 按 Watchlist 公司逐个拉取最新新闻
- 去重后存入数据库
- API 文档: https://finnhub.io/docs/api/company-news
"""
import logging
from datetime import datetime, timedelta, timezone
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

FINNHUB_BASE_URL = "https://finnhub.io/api/v1"


class FinnhubFetcher:
    """Finnhub 新闻采集器"""

    def __init__(self, session: AsyncSession, redis):
        self.session = session
        self.redis = redis
        self.dedup = DedupService(redis)
        self.api_key = settings.FINNHUB_API_KEY

    async def fetch_company_news(
        self, ticker: str, days_back: int = 2
    ) -> list[dict]:
        """
        从 Finnhub 获取指定公司的新闻
        - ticker: 股票代码
        - days_back: 往前查几天（默认 2 天）
        """
        now = datetime.now(timezone.utc)
        to_date = now.strftime("%Y-%m-%d")
        from_date = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{FINNHUB_BASE_URL}/company-news",
                params={
                    "symbol": ticker,
                    "from": from_date,
                    "to": to_date,
                    "token": self.api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            # Finnhub 可能返回空列表或错误
            if isinstance(data, list):
                return data
            else:
                logger.warning(f"Finnhub unexpected response for {ticker}: {data}")
                return []

    async def fetch_all(self, tickers: Optional[list[str]] = None) -> dict:
        """
        采集所有 Watchlist 公司的新闻

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
                "errors": ["FINNHUB_API_KEY 未配置，请在 .env 中设置"],
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
                raw_news = await self.fetch_company_news(company.ticker)
                total_fetched += len(raw_news)
                logger.info(
                    f"[Finnhub] {company.ticker}: 获取到 {len(raw_news)} 条新闻"
                )

                for item in raw_news:
                    # 生成去重指纹
                    fingerprint = DedupService.generate_fingerprint(
                        source=item.get("source", ""),
                        url=item.get("url", ""),
                        headline=item.get("headline", ""),
                    )

                    # Redis 去重检查
                    if await self.dedup.is_duplicate(fingerprint):
                        continue

                    # 解析发布时间（Finnhub 返回 Unix 时间戳）
                    pub_timestamp = item.get("datetime", 0)
                    published_at = (
                        datetime.fromtimestamp(pub_timestamp, tz=timezone.utc)
                        if pub_timestamp
                        else None
                    )

                    # 创建新闻记录
                    news = News(
                        company_id=company.id,
                        title=item.get("headline", "").strip(),
                        content=item.get("summary", ""),
                        summary=item.get("summary", ""),
                        source="finnhub",
                        source_url=item.get("url", ""),
                        category=item.get("category", "company"),
                        fingerprint=fingerprint,
                        published_at=published_at,
                    )

                    try:
                        self.session.add(news)
                        await self.session.flush()
                        total_new += 1
                    except IntegrityError:
                        # 数据库层面去重兜底（fingerprint UNIQUE 约束）
                        await self.session.rollback()
                        logger.debug(
                            f"[Finnhub] 重复新闻（DB 去重）: {item.get('headline', '')[:50]}"
                        )

                await self.session.commit()

            except httpx.HTTPStatusError as e:
                error_msg = f"{company.ticker}: HTTP {e.response.status_code}"
                logger.error(f"[Finnhub] {error_msg}")
                errors.append(error_msg)
            except Exception as e:
                error_msg = f"{company.ticker}: {str(e)}"
                logger.error(f"[Finnhub] {error_msg}")
                errors.append(error_msg)

        return {
            "companies_processed": len(companies),
            "total_fetched": total_fetched,
            "new_articles": total_new,
            "errors": errors,
        }
