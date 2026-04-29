"""
新闻 API
- 新闻列表查询（支持筛选）
- 手动触发 RTPR / Polygon / EDGAR 采集
- 可扩展接入更多数据源
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
from app.services.analyzer import run_analysis_background

router = APIRouter(tags=["News"])


@router.get("/news", response_model=list[NewsResponse])
async def list_news(
    ticker: Optional[str] = Query(None, description="按股票代码筛选"),
    source: Optional[str] = Query(None, description="按数据来源筛选: rtpr/finnhub/polygon"),
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


# =====================================================
#  数据采集接口 — 多数据源
# =====================================================

@router.post("/fetch/polygon", response_model=NewsFetchResult)
async def fetch_polygon_news(
    request: Request,
    background_tasks: BackgroundTasks,
    ticker: Optional[str] = Query(None, description="只采集指定公司（可选）"),
    hours_back: int = Query(2, ge=1, le=48, description="往前抓取多少小时内的新闻"),
    auto_analyze: bool = Query(True, description="采集后是否自动触发 AI 分析"),
    db: AsyncSession = Depends(get_db),
):
    """
    手动触发 Polygon.io 新闻采集（主力数据源）—— 后台运行，立即返回
    """
    from app.services.fetchers.polygon_news import PolygonNewsFetcher
    from app.database import async_session

    redis = getattr(request.app.state, "redis", None)

    async def _run():
        async with async_session() as sess:
            fetcher = PolygonNewsFetcher(session=sess, redis=redis)
            if ticker:
                result2 = await sess.execute(
                    select(Company).where(Company.ticker == ticker.upper())
                )
                company = result2.scalar_one_or_none()
                if company:
                    stat = await fetcher.fetch_ticker(company, hours_back=hours_back)
                    await sess.commit()
                    new_cnt = stat.get("new", 0)
                else:
                    new_cnt = 0
            else:
                result_dict = await fetcher.fetch_all(hours_back=hours_back)
                new_cnt = result_dict.get("new_articles", 0)
            if auto_analyze and new_cnt > 0:
                await run_analysis_background()

    background_tasks.add_task(_run)
    return NewsFetchResult(
        companies_processed=0,
        total_fetched=0,
        new_articles=0,
        errors=[],
        message="采集任务已在后台启动，请稍后查看日志",
    )


@router.post("/fetch/rtpr", response_model=NewsFetchResult)
async def fetch_rtpr_news(
    request: Request,
    background_tasks: BackgroundTasks,
    ticker: Optional[str] = Query(None, description="只采集指定公司（可选）"),
    auto_analyze: bool = Query(True, description="采集后是否自动触发 AI 分析"),
    db: AsyncSession = Depends(get_db),
):
    """
    手动触发 RTPR 一手新闻稿采集 —— 后台运行，立即返回
    """
    from app.services.fetchers.rtpr import RTPRFetcher
    from app.database import async_session

    redis = getattr(request.app.state, "redis", None)
    tickers = [ticker] if ticker else None

    async def _run():
        async with async_session() as sess:
            fetcher = RTPRFetcher(session=sess, redis=redis)
            result = await fetcher.fetch_all(tickers=tickers)
            if auto_analyze and result.get("new_articles", 0) > 0:
                await run_analysis_background()

    background_tasks.add_task(_run)
    return NewsFetchResult(
        companies_processed=0,
        total_fetched=0,
        new_articles=0,
        errors=[],
        message="RTPR 采集已在后台启动，请稍后查看日志",
    )


@router.post("/fetch/edgar", response_model=NewsFetchResult)
async def fetch_edgar_news(
    request: Request,
    background_tasks: BackgroundTasks,
    ticker: Optional[str] = Query(None, description="只采集指定公司（可选）"),
    auto_analyze: bool = Query(True, description="采集后是否自动触发 AI 分析"),
    db: AsyncSession = Depends(get_db),
):
    """
    手动触发 SEC EDGAR 8-K 公告采集
    """
    from app.services.fetchers.edgar import EDGARFetcher

    tickers = [ticker] if ticker else None
    fetcher = EDGARFetcher(session=db, redis=request.app.state.redis)
    result = await fetcher.fetch_all(tickers=tickers)

    if auto_analyze and result["new_articles"] > 0:
        background_tasks.add_task(run_analysis_background)

    return NewsFetchResult(**result)


# 保留 Finnhub 兼容接口（指向 RTPR）
@router.post("/fetch/finnhub", response_model=NewsFetchResult)
async def fetch_finnhub_news(
    request: Request,
    background_tasks: BackgroundTasks,
    ticker: Optional[str] = Query(None),
    auto_analyze: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    [兼容旧接口] 已切换为 RTPR 数据源
    """
    return await fetch_rtpr_news(
        request=request,
        background_tasks=background_tasks,
        ticker=ticker,
        auto_analyze=auto_analyze,
        db=db,
    )
