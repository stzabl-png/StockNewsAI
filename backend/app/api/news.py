"""
新闻 API
- 新闻列表查询（支持筛选）
- 手动触发 Finnhub 采集
"""
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models.company import Company
from app.models.news import News
from app.schemas.news import NewsResponse, NewsFetchResult
from app.services.fetchers.finnhub import FinnhubFetcher
from app.services.analyzer import run_analysis_background

router = APIRouter(tags=["News"])


@router.get("/news", response_model=list[NewsResponse])
async def list_news(
    ticker: Optional[str] = Query(None, description="按股票代码筛选"),
    source: Optional[str] = Query(None, description="按数据来源筛选: finnhub/fda/sec/clinical_trials"),
    limit: int = Query(50, ge=1, le=200, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取新闻列表
    - 支持按公司 ticker、数据来源筛选
    - 按发布时间倒序排列
    """
    query = select(News).options(joinedload(News.company))

    if ticker:
        query = query.join(Company).where(Company.ticker == ticker.upper())
    if source:
        query = query.where(News.source == source)

    query = query.order_by(News.published_at.desc().nullslast()).offset(offset).limit(limit)

    result = await db.execute(query)
    news_items = result.unique().scalars().all()

    # 构建响应（带 ticker 和 company_name）
    return [
        NewsResponse(
            id=item.id,
            company_id=item.company_id,
            ticker=item.company.ticker,
            company_name=item.company.name,
            title=item.title,
            summary=item.summary,
            source=item.source,
            source_url=item.source_url,
            category=item.category,
            published_at=item.published_at,
            created_at=item.created_at,
        )
        for item in news_items
    ]


@router.get("/news/stats")
async def news_stats(db: AsyncSession = Depends(get_db)):
    """新闻统计概览"""
    total = await db.execute(select(func.count(News.id)))
    by_source = await db.execute(
        select(News.source, func.count(News.id)).group_by(News.source)
    )

    return {
        "total": total.scalar(),
        "by_source": {row[0]: row[1] for row in by_source.all()},
    }


@router.get("/news/{news_id}", response_model=NewsResponse)
async def get_news(news_id: int, db: AsyncSession = Depends(get_db)):
    """获取单条新闻详情"""
    result = await db.execute(
        select(News).options(joinedload(News.company)).where(News.id == news_id)
    )
    item = result.unique().scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="新闻不存在")

    return NewsResponse(
        id=item.id,
        company_id=item.company_id,
        ticker=item.company.ticker,
        company_name=item.company.name,
        title=item.title,
        summary=item.summary,
        source=item.source,
        source_url=item.source_url,
        category=item.category,
        published_at=item.published_at,
        created_at=item.created_at,
    )


@router.post("/fetch/finnhub", response_model=NewsFetchResult)
async def fetch_finnhub_news(
    request: Request,
    background_tasks: BackgroundTasks,
    ticker: Optional[str] = Query(None, description="只采集指定公司（可选）"),
    auto_analyze: bool = Query(True, description="采集后是否自动触发 AI 分析"),
    db: AsyncSession = Depends(get_db),
):
    """
    手动触发 Finnhub 新闻采集
    - 不传 ticker: 采集 Watchlist 全部活跃公司
    - 传 ticker: 只采集指定公司
    - auto_analyze=true: 采集后自动在后台触发 LLM 分析
    """
    tickers = [ticker] if ticker else None
    fetcher = FinnhubFetcher(session=db, redis=request.app.state.redis)
    result = await fetcher.fetch_all(tickers=tickers)

    # 有新文章时自动触发后台分析
    if auto_analyze and result["new_articles"] > 0:
        background_tasks.add_task(run_analysis_background)

    return NewsFetchResult(**result)
