"""
Polygon.io 新闻采集器
- 按 ticker 批量拉取最新新闻
- 速率控制：5 req/s（Starter 限制内）
- 自动去重、板块/概念标签化
"""
import asyncio
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.news import News
from app.models.company import Company
from app.services.dedup import is_duplicate, mark_seen
from data.sector_config import SECTOR_BY_NAME
from data.concept_config import match_concepts_for_news

logger = logging.getLogger(__name__)

POLYGON_BASE = "https://api.polygon.io"
RATE_LIMIT_DELAY = 0.2   # 5 req/s, 200ms between requests
MAX_NEWS_PER_TICKER = 10  # 每次拉取最多10条，防止成本失控


class PolygonNewsFetcher:
    """Polygon.io 新闻采集器"""

    def __init__(self, session: AsyncSession, redis=None):
        self.session = session
        self.redis = redis
        self.api_key = settings.POLYGON_API_KEY
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=30)
        return self

    async def __aexit__(self, *_):
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    # ─── 主入口：采集单只股票 ──────────────────────────────────────────────────

    async def fetch_ticker(self, company: Company, hours_back: int = 2) -> dict:
        """采集单只股票最新新闻，返回采集统计"""
        if not self.api_key:
            raise RuntimeError("POLYGON_API_KEY 未配置")

        since = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        url = f"{POLYGON_BASE}/v2/reference/news"
        params = {
            "ticker": company.ticker,
            "published_utc.gte": since,
            "order": "desc",
            "limit": MAX_NEWS_PER_TICKER,
            "apiKey": self.api_key,
        }

        try:
            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning(f"[Polygon] {company.ticker} HTTP {e.response.status_code}")
            return {"ticker": company.ticker, "fetched": 0, "new": 0, "error": str(e)}
        except Exception as e:
            logger.warning(f"[Polygon] {company.ticker} 请求失败: {e}")
            return {"ticker": company.ticker, "fetched": 0, "new": 0, "error": str(e)}

        articles = data.get("results", [])
        new_count = 0

        for article in articles:
            saved = await self._save_article(article, company)
            if saved:
                new_count += 1

        return {
            "ticker": company.ticker,
            "fetched": len(articles),
            "new": new_count,
            "error": None,
        }

    # ─── 批量采集所有 Watchlist 股票 ───────────────────────────────────────────

    async def fetch_all(self, hours_back: int = 2) -> dict:
        """批量采集所有活跃公司的新闻（带速率控制）"""
        from sqlalchemy import select
        result = await self.session.execute(
            select(Company).where(Company.is_active == True)  # noqa
        )
        companies = result.scalars().all()

        total_fetched = 0
        total_new = 0
        errors = 0

        for i, company in enumerate(companies):
            stat = await self.fetch_ticker(company, hours_back=hours_back)
            total_fetched += stat["fetched"]
            total_new += stat["new"]
            if stat["error"]:
                errors += 1
            # 每只股票处理完后提交，避免长事务
            if stat["new"] > 0:
                await self.session.commit()
            # 速率控制：每请求间隔 200ms
            await asyncio.sleep(RATE_LIMIT_DELAY)

        logger.info(
            f"[PolygonNews] 完成采集: {len(companies)} 家公司, "
            f"获取 {total_fetched} 条, 新增 {total_new} 条, 错误 {errors} 家"
        )
        return {
            "companies_processed": len(companies),
            "total_fetched": total_fetched,
            "new_articles": total_new,
            "errors": errors,
        }

    # ─── 私有：保存单条新闻 ────────────────────────────────────────────────────

    async def _save_article(self, article: dict, company: Company) -> bool:
        """
        解析并保存单条 Polygon 新闻。
        返回 True 表示成功新增，False 表示重复或失败。
        """
        title = article.get("title", "").strip()
        if not title:
            return False

        # 生成去重指纹（标题 + ticker）
        raw = f"{company.ticker}::{title}"
        fingerprint = hashlib.sha256(raw.encode()).hexdigest()

        # Redis 快速去重
        if self.redis and await is_duplicate(self.redis, fingerprint):
            return False

        # DB 二次检查（避免 Redis 重启后丢失）
        from sqlalchemy import select
        existing = await self.session.execute(
            select(News.id).where(News.fingerprint == fingerprint)
        )
        if existing.scalar():
            return False

        # 解析发布时间
        pub_str = article.get("published_utc", "")
        try:
            published_at = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
        except Exception:
            published_at = datetime.now(timezone.utc)

        # 拼接正文（description + keywords）
        content = article.get("description", "") or ""
        keywords = ", ".join(article.get("keywords", []))
        if keywords:
            content += f"\n\nKeywords: {keywords}"

        # 板块 ID
        sector_id = self._resolve_sector_id(company)

        # 概念 ID 列表
        full_text = f"{title} {content}"
        concept_ids = match_concepts_for_news(full_text, company.ticker)

        news = News(
            company_id=company.id,
            title=title,
            content=content[:5000] if content else None,
            summary=article.get("description", "")[:500] if article.get("description") else None,
            source="polygon",
            source_url=article.get("article_url"),
            fingerprint=fingerprint,
            published_at=published_at,
            sector_id=sector_id,
            concept_ids=concept_ids if concept_ids else None,
        )

        self.session.add(news)
        try:
            await self.session.flush()
            # Redis 标记（TTL 7天）
            if self.redis:
                await mark_seen(self.redis, fingerprint, ttl=604800)
            return True
        except Exception as e:
            logger.warning(f"[Polygon] 保存新闻失败 ({company.ticker}): {e}")
            await self.session.rollback()
            return False

    def _resolve_sector_id(self, company: Company) -> Optional[int]:
        """根据公司的 gics_sector 字段解析 sector_id"""
        sector_name = getattr(company, "gics_sector", None) or company.sector or ""
        sector = SECTOR_BY_NAME.get(sector_name)
        return sector["id"] if sector else None
