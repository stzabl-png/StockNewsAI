"""
SEC EDGAR 数据采集器
- 获取 Watchlist 公司的 8-K 公告（重大事件）
- 完全免费，无需 API Key
- 无限历史，官方权威
"""
import hashlib
import logging
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.company import Company
from app.models.news import News
from app.services.dedup import DedupService

logger = logging.getLogger(__name__)

# EDGAR requires a descriptive User-Agent
USER_AGENT = "StockNewsAI/1.0 (stocknewsai@example.com)"

# CIK lookup: ticker -> CIK number (10-digit zero-padded)
# We'll auto-discover CIKs if not cached
CIK_CACHE: dict[str, str] = {}

# 8-K Item descriptions for better context
ITEM_DESCRIPTIONS = {
    "1.01": "Entry into Material Definitive Agreement",
    "1.02": "Termination of Material Definitive Agreement",
    "2.02": "Results of Operations and Financial Condition",
    "2.05": "Costs Associated with Exit or Disposal Activities",
    "2.06": "Material Impairments",
    "3.01": "Notice of Delisting",
    "5.01": "Changes in Control of Registrant",
    "5.02": "Departure/Election of Directors or Officers",
    "5.07": "Submission of Matters to a Vote of Security Holders",
    "7.01": "Regulation FD Disclosure",
    "8.01": "Other Events",
    "9.01": "Financial Statements and Exhibits",
}


class HTMLTextExtractor(HTMLParser):
    """从 SEC filing HTML 中提取纯文本"""
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script", "meta", "link"):
            self.skip = True

    def handle_endtag(self, tag):
        if tag in ("style", "script", "meta", "link"):
            self.skip = False
        if tag in ("p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4"):
            self.text_parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            text = data.strip()
            if text:
                self.text_parts.append(text)


class EDGARFetcher:
    """SEC EDGAR 8-K Filing 采集器"""

    def __init__(self, session: AsyncSession, redis=None):
        self.session = session
        self.redis = redis
        self.dedup = DedupService(redis) if redis else None

    async def _get_cik(self, ticker: str) -> Optional[str]:
        """查找公司的 CIK 编号"""
        ticker_upper = ticker.upper()

        # Check cache first
        if ticker_upper in CIK_CACHE:
            return CIK_CACHE[ticker_upper]

        try:
            async with httpx.AsyncClient() as client:
                # Use SEC's company tickers JSON
                resp = await client.get(
                    "https://www.sec.gov/files/company_tickers.json",
                    headers={"User-Agent": USER_AGENT},
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()

                for entry in data.values():
                    if entry.get("ticker", "").upper() == ticker_upper:
                        cik = str(entry["cik_str"]).zfill(10)
                        CIK_CACHE[ticker_upper] = cik
                        logger.info(f"[EDGAR] {ticker_upper} -> CIK {cik}")
                        return cik

                logger.warning(f"[EDGAR] 未找到 {ticker_upper} 的 CIK")
                return None

        except Exception as e:
            logger.error(f"[EDGAR] CIK 查找失败: {e}")
            return None

    async def _get_filings(
        self, cik: str, form_type: str = "8-K", limit: int = 20
    ) -> list[dict]:
        """获取公司最近的 filing 列表"""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://data.sec.gov/submissions/CIK{cik}.json",
                    headers={"User-Agent": USER_AGENT},
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()

                filings = data["filings"]["recent"]
                results = []

                for i in range(len(filings["form"])):
                    if filings["form"][i] == form_type:
                        accession = filings["accessionNumber"][i].replace("-", "")
                        cik_num = cik.lstrip("0") or "0"
                        doc = filings["primaryDocument"][i]

                        results.append({
                            "filing_date": filings["filingDate"][i],
                            "form": filings["form"][i],
                            "accession": filings["accessionNumber"][i],
                            "primary_doc": doc,
                            "description": filings.get("primaryDocDescription", [""])[i] if i < len(filings.get("primaryDocDescription", [])) else "",
                            "items": filings.get("items", [""])[i] if i < len(filings.get("items", [])) else "",
                            "url": f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{accession}/{doc}",
                        })

                        if len(results) >= limit:
                            break

                return results

        except Exception as e:
            logger.error(f"[EDGAR] 获取 filing 列表失败 (CIK {cik}): {e}")
            return []

    async def _fetch_filing_text(self, url: str, max_chars: int = 10000) -> str:
        """下载并解析 filing HTML，提取纯文本"""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    url,
                    headers={"User-Agent": USER_AGENT},
                    timeout=30,
                    follow_redirects=True,
                )
                resp.raise_for_status()
                html = resp.text

                parser = HTMLTextExtractor()
                parser.feed(html)
                text = " ".join(parser.text_parts)

                # Skip XBRL header junk - find the actual content
                markers = [
                    "CURRENT REPORT",
                    "FORM 8-K",
                    "Date of Report",
                ]
                best_start = 0
                for marker in markers:
                    idx = text.find(marker)
                    if idx > 0:
                        best_start = max(best_start, idx)

                if best_start > 0:
                    text = text[best_start:]

                return text[:max_chars].strip()

        except Exception as e:
            logger.error(f"[EDGAR] Filing 内容下载失败: {e}")
            return ""

    def _build_title(self, filing: dict, company_name: str) -> str:
        """为 8-K filing 生成可读标题"""
        items = filing.get("items", "")
        if items:
            item_list = [i.strip() for i in items.split(",")]
            descriptions = []
            for item in item_list:
                if item in ITEM_DESCRIPTIONS:
                    descriptions.append(ITEM_DESCRIPTIONS[item])
            if descriptions:
                return f"[SEC 8-K] {company_name}: {'; '.join(descriptions[:2])}"

        return f"[SEC 8-K] {company_name} - Filed {filing['filing_date']}"

    async def fetch_company(self, ticker: str, company_id: int) -> dict:
        """采集单个公司的 EDGAR 8-K filings"""
        cik = await self._get_cik(ticker)
        if not cik:
            return {"ticker": ticker, "fetched": 0, "new": 0}

        filings = await self._get_filings(cik, limit=10)
        logger.info(f"[EDGAR] {ticker}: 获取到 {len(filings)} 个 8-K filing")

        fetched = 0
        new_count = 0

        for filing in filings:
            fetched += 1
            # Generate fingerprint for dedup
            fingerprint = hashlib.sha256(
                f"edgar:{filing['accession']}".encode()
            ).hexdigest()

            # Check dedup
            if self.dedup and await self.dedup.is_duplicate(fingerprint):
                continue

            # Also check DB
            existing = await self.session.execute(
                select(News).where(News.fingerprint == fingerprint)
            )
            if existing.scalar_one_or_none():
                continue

            # Get company info for title
            company = await self.session.get(Company, company_id)
            company_name = company.name if company else ticker

            # Fetch full text
            content = await self._fetch_filing_text(filing["url"])
            title = self._build_title(filing, company_name)

            # Parse date
            try:
                pub_date = datetime.strptime(
                    filing["filing_date"], "%Y-%m-%d"
                ).replace(tzinfo=timezone.utc)
            except ValueError:
                pub_date = datetime.now(timezone.utc)

            # Build summary from items
            items_str = filing.get("items", "")
            summary = f"SEC 8-K Filing | Items: {items_str}" if items_str else "SEC 8-K Filing"

            news = News(
                company_id=company_id,
                title=title,
                content=content or summary,
                summary=summary,
                source="sec_edgar",
                source_url=filing["url"],
                category="regulatory",
                fingerprint=fingerprint,
                published_at=pub_date,
            )
            self.session.add(news)
            new_count += 1

            logger.info(f"[EDGAR] {ticker}: 新增 8-K ({filing['filing_date']})")

        if new_count > 0:
            await self.session.commit()

        return {"ticker": ticker, "fetched": fetched, "new": new_count}

    async def fetch_all(self, tickers: list[str] = None) -> dict:
        """采集所有 Watchlist 公司的 EDGAR 8-K filings"""
        # Get active companies from watchlist
        query = select(Company).where(Company.is_active == True)
        if tickers:
            query = query.where(Company.ticker.in_([t.upper() for t in tickers]))

        result = await self.session.execute(query)
        companies = result.scalars().all()

        if not companies:
            return {
                "source": "sec_edgar",
                "companies_processed": 0,
                "total_fetched": 0,
                "new_articles": 0,
            }

        total_fetched = 0
        total_new = 0

        for company in companies:
            try:
                result = await self.fetch_company(company.ticker, company.id)
                total_fetched += result["fetched"]
                total_new += result["new"]
            except Exception as e:
                logger.error(f"[EDGAR] {company.ticker} 采集失败: {e}")

        logger.info(
            f"[EDGAR] 采集完成: {len(companies)} 家公司, "
            f"获取 {total_fetched} 条, 新增 {total_new} 条"
        )

        return {
            "source": "sec_edgar",
            "companies_processed": len(companies),
            "total_fetched": total_fetched,
            "new_articles": total_new,
        }
