"""
板块 API
- 获取所有板块（含公司数量）
- 按板块获取公司列表
- 按公司获取新闻列表
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models.company import Company
from app.models.news import News
from app.models.sector import Sector

router = APIRouter(tags=["Sectors"])

# 板块 ETF 映射（用于颜色区分）
SECTOR_COLORS = {
    "Information Technology": "#6366f1",
    "Health Care":            "#10b981",
    "Financials":             "#f59e0b",
    "Communication Services": "#3b82f6",
    "Consumer Discretionary": "#ec4899",
    "Industrials":            "#8b5cf6",
    "Consumer Staples":       "#06b6d4",
    "Energy":                 "#f97316",
    "Materials":              "#84cc16",
    "Utilities":              "#64748b",
    "Real Estate":            "#a855f7",
}

SECTOR_ICONS = {
    "Information Technology": "💻",
    "Health Care":            "🏥",
    "Financials":             "🏦",
    "Communication Services": "📡",
    "Consumer Discretionary": "🛒",
    "Industrials":            "🏭",
    "Consumer Staples":       "🛍️",
    "Energy":                 "⚡",
    "Materials":              "⚒️",
    "Utilities":              "💡",
    "Real Estate":            "🏢",
}


@router.get("/sectors")
async def list_sectors(db: AsyncSession = Depends(get_db)):
    """
    返回所有板块，含公司数量和当日新闻数量
    """
    # 所有板块
    result = await db.execute(select(Sector).order_by(Sector.id))
    sectors = result.scalars().all()

    # 每个板块的公司数
    company_counts = await db.execute(
        select(Company.gics_sector, func.count(Company.id))
        .where(Company.is_active == True)  # noqa
        .where(Company.gics_sector != None)  # noqa
        .group_by(Company.gics_sector)
    )
    company_count_map = {row[0]: row[1] for row in company_counts.all()}

    # 每个板块今日新闻数（用 sector_id 关联）
    news_counts = await db.execute(
        text("""
            SELECT s.id, COUNT(n.id)
            FROM sectors s
            LEFT JOIN news n ON n.sector_id = s.id
                AND n.published_at >= NOW() - INTERVAL '24 hours'
            GROUP BY s.id
        """)
    )
    news_count_map = {row[0]: row[1] for row in news_counts.all()}

    out = []
    for s in sectors:
        name_en = s.name_en
        company_count = company_count_map.get(name_en, 0)
        if company_count == 0:
            continue  # 跳过没有公司的板块
        out.append({
            "id": s.id,
            "name": s.name,
            "name_en": name_en,
            "gics_code": s.gics_code,
            "etf_ticker": s.etf_ticker,
            "icon": SECTOR_ICONS.get(name_en, "📊"),
            "color": SECTOR_COLORS.get(name_en, "#6366f1"),
            "company_count": company_count,
            "news_24h": news_count_map.get(s.id, 0),
        })

    return out


@router.get("/sectors/{sector_id}/companies")
async def sector_companies(sector_id: int, db: AsyncSession = Depends(get_db)):
    """
    旧接口（兼容保留）：按整数 ID 查板块公司
    """
    result = await db.execute(select(Sector).where(Sector.id == sector_id))
    sector = result.scalar_one_or_none()
    if not sector:
        raise HTTPException(status_code=404, detail="板块不存在")

    comp_result = await db.execute(
        select(Company)
        .where(Company.gics_sector == sector.name_en)
        .where(Company.is_active == True)  # noqa
        .order_by(Company.market_cap.desc().nullslast())
    )
    companies = comp_result.scalars().all()
    return _format_companies(companies, db)


@router.get("/sector-companies/{sector_name}")
async def sector_companies_by_name(sector_name: str, db: AsyncSession = Depends(get_db)):
    """
    新接口：按中文板块名称从 companies.sector 字段查公司
    """
    from urllib.parse import unquote
    sector_name = unquote(sector_name)

    comp_result = await db.execute(
        text("""
            SELECT
                c.id, c.ticker, c.name, c.sector, c.gics_sub_sector,
                c.market_cap, c.tier,
                COUNT(n.id) FILTER (
                    WHERE n.published_at >= NOW() - INTERVAL '24 hours'
                ) AS news_24h
            FROM companies c
            LEFT JOIN news n ON n.company_id = c.id
            WHERE c.sector = :sname AND c.is_active = true
            GROUP BY c.id
            ORDER BY c.market_cap DESC NULLS LAST
            LIMIT 300
        """),
        {"sname": sector_name}
    )
    rows = comp_result.fetchall()
    return [
        {
            "id":           r[0],
            "ticker":       r[1],
            "name":         r[2],
            "gics_sector":  r[3],
            "gics_sub_sector": r[4],
            "market_cap":   r[5],
            "tier":         r[6],
            "news_24h":     int(r[7] or 0),
        }
        for r in rows
    ]


async def _format_companies(companies, db):
    """Helper to format company list with news counts"""
    if not companies:
        return []
    ids = [c.id for c in companies]
    news_counts = await db.execute(
        text("""
            SELECT company_id, COUNT(*)
            FROM news WHERE company_id = ANY(:ids)
              AND published_at >= NOW() - INTERVAL '24 hours'
            GROUP BY company_id
        """),
        {"ids": ids},
    )
    news_map = {row[0]: row[1] for row in news_counts.all()}
    return [
        {
            "id":              c.id,
            "ticker":          c.ticker,
            "name":            c.name,
            "gics_sub_sector": c.gics_sub_sector,
            "market_cap":      c.market_cap,
            "tier":            c.tier,
            "news_24h":        news_map.get(c.id, 0),
        }
        for c in companies
    ]


@router.get("/sectors/{sector_id}/news")
async def sector_news(
    sector_id: int,
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
):
    """返回指定板块最新新闻（跨公司）"""
    result = await db.execute(
        select(News)
        .options(joinedload(News.company))
        .where(News.sector_id == sector_id)
        .order_by(News.published_at.desc().nullslast())
        .limit(limit)
    )
    news_list = result.unique().scalars().all()

    return [
        {
            "id": n.id,
            "ticker": n.company.ticker if n.company else "?",
            "company_name": n.company.name if n.company else "",
            "title": n.title,
            "summary": n.summary,
            "source": n.source,
            "source_url": n.source_url,
            "published_at": n.published_at.isoformat() if n.published_at else None,
            "concept_ids": n.concept_ids,
        }
        for n in news_list
    ]


# ─── 概念公司列表 ───────────────────────────────────────────────────────
@router.get("/concepts/{concept_id}/companies")
async def concept_companies(concept_id: int, db: AsyncSession = Depends(get_db)):
    """
    返回某个主题概念下的所有公司（基于 related_tickers 字段）
    包含最近24小时新闻数量
    """
    from sqlalchemy import text

    # Get concept's related tickers
    concept_result = await db.execute(
        text("SELECT related_tickers FROM concepts WHERE id = :id"),
        {"id": concept_id}
    )
    row = concept_result.fetchone()
    if not row or not row[0]:
        return []

    tickers = row[0]  # PostgreSQL array → Python list

    if not tickers:
        return []

    # Get company data for these tickers
    comp_result = await db.execute(
        text("""
            SELECT
                c.ticker, c.name, c.gics_sector, c.gics_sub_sector, c.market_cap, c.tier,
                COUNT(n.id) FILTER (
                    WHERE n.published_at >= NOW() - INTERVAL '24 hours'
                ) AS news_24h
            FROM companies c
            LEFT JOIN news n ON n.company_id = c.id
            WHERE c.ticker = ANY(:tickers) AND c.is_active = true
            GROUP BY c.id
            ORDER BY c.market_cap DESC NULLS LAST
        """),
        {"tickers": tickers}
    )
    rows = comp_result.fetchall()

    return [
        {
            "ticker":         r[0],
            "name":           r[1],
            "gics_sector":    r[2],
            "gics_sub_sector": r[3],
            "market_cap":     r[4],
            "tier":           r[5],
            "news_24h":       int(r[6] or 0),
        }
        for r in rows
    ]


@router.get("/concepts")
async def list_concepts(db: AsyncSession = Depends(get_db)):
    """返回所有主题概念列表"""
    from sqlalchemy import text
    result = await db.execute(text("""
        SELECT id, name, keywords, related_tickers, is_active
        FROM concepts WHERE is_active = true ORDER BY id
    """))
    rows = result.fetchall()
    return [
        {
            "id": r[0], "name": r[1],
            "keywords": r[2] or [], "tickers": r[3] or [],
            "is_active": r[4]
        }
        for r in rows
    ]
