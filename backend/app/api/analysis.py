"""
分析结果 API
- 查看分析结果列表
- 手动触发分析
- 获取单条新闻的分析详情
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models.news import News
from app.models.analysis import Analysis
from app.schemas.analysis import AnalysisResponse, AnalyzeBatchResult
from app.services.analyzer import NewsAnalyzer, run_analysis_background

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.get("", response_model=list[AnalysisResponse])
async def list_analyses(
    ticker: Optional[str] = Query(None, description="按股票代码筛选"),
    sentiment: Optional[str] = Query(None, description="按情感筛选: bullish/bearish/neutral"),
    impact_level: Optional[str] = Query(None, description="按影响级别筛选: high/medium/low"),
    level: Optional[int] = Query(None, description="按分析级别筛选: 1=初筛, 2=深度"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """获取分析结果列表"""
    query = (
        select(Analysis)
        .join(News)
        .options(joinedload(Analysis.news).joinedload(News.company))
    )

    if ticker:
        from app.models.company import Company
        query = query.join(Company, News.company_id == Company.id).where(
            Company.ticker == ticker.upper()
        )
    if sentiment:
        query = query.where(Analysis.sentiment == sentiment)
    if impact_level:
        query = query.where(Analysis.impact_level == impact_level)
    if level:
        query = query.where(Analysis.level == level)

    query = query.order_by(Analysis.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    analyses = result.unique().scalars().all()

    return [
        AnalysisResponse(
            id=a.id,
            news_id=a.news_id,
            ticker=a.news.company.ticker,
            company_name=a.news.company.name,
            news_title=a.news.title,
            level=a.level,
            sentiment=a.sentiment,
            confidence=a.confidence,
            impact_level=a.impact_level,
            impact_duration=a.impact_duration,
            summary_cn=a.summary_cn,
            detailed_analysis=a.detailed_analysis,
            related_tickers=a.related_tickers,
            key_dates=a.key_dates,
            created_at=a.created_at,
        )
        for a in analyses
    ]


@router.get("/stats")
async def analysis_stats(db: AsyncSession = Depends(get_db)):
    """分析统计概览"""
    total = await db.execute(select(func.count(Analysis.id)))
    by_sentiment = await db.execute(
        select(Analysis.sentiment, func.count(Analysis.id)).group_by(Analysis.sentiment)
    )
    by_impact = await db.execute(
        select(Analysis.impact_level, func.count(Analysis.id)).group_by(Analysis.impact_level)
    )
    high_impact = await db.execute(
        select(func.count(Analysis.id)).where(Analysis.impact_level == "high")
    )

    return {
        "total": total.scalar(),
        "high_impact": high_impact.scalar(),
        "by_sentiment": {row[0]: row[1] for row in by_sentiment.all()},
        "by_impact": {row[0]: row[1] for row in by_impact.all()},
    }


@router.get("/{news_id}", response_model=AnalysisResponse)
async def get_analysis(news_id: int, db: AsyncSession = Depends(get_db)):
    """获取单条新闻的分析结果"""
    result = await db.execute(
        select(Analysis)
        .where(Analysis.news_id == news_id)
        .options(joinedload(Analysis.news).joinedload(News.company))
    )
    analysis = result.unique().scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail=f"新闻 {news_id} 的分析结果不存在")

    return AnalysisResponse(
        id=analysis.id,
        news_id=analysis.news_id,
        ticker=analysis.news.company.ticker,
        company_name=analysis.news.company.name,
        news_title=analysis.news.title,
        level=analysis.level,
        sentiment=analysis.sentiment,
        confidence=analysis.confidence,
        impact_level=analysis.impact_level,
        impact_duration=analysis.impact_duration,
        summary_cn=analysis.summary_cn,
        detailed_analysis=analysis.detailed_analysis,
        related_tickers=analysis.related_tickers,
        key_dates=analysis.key_dates,
        created_at=analysis.created_at,
    )


@router.post("/batch", response_model=AnalyzeBatchResult)
async def analyze_batch(
    background_tasks: BackgroundTasks,
    sync: bool = Query(False, description="是否同步执行（等待分析完成再返回）"),
    db: AsyncSession = Depends(get_db),
):
    """
    批量分析所有未分析的新闻
    - sync=false (默认): 后台异步执行，立即返回
    - sync=true: 同步执行，等待全部分析完成
    """
    if sync:
        # 同步模式 — 等待分析完成
        analyzer = NewsAnalyzer(session=db)
        result = await analyzer.analyze_batch()
        return AnalyzeBatchResult(**result)
    else:
        # 异步模式 — 后台执行
        background_tasks.add_task(run_analysis_background)
        return AnalyzeBatchResult(total=-1, analyzed=0, high_impact=0, errors=0)


@router.post("/{news_id}", response_model=AnalysisResponse)
async def analyze_single(
    news_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    分析指定新闻（如已有分析结果会先删除再重新分析）
    """
    # 获取新闻
    result = await db.execute(
        select(News).where(News.id == news_id).options(joinedload(News.company))
    )
    news = result.unique().scalar_one_or_none()
    if not news:
        raise HTTPException(status_code=404, detail=f"新闻 {news_id} 不存在")

    # 删除已有分析
    existing = await db.execute(
        select(Analysis).where(Analysis.news_id == news_id)
    )
    old = existing.scalar_one_or_none()
    if old:
        await db.delete(old)
        await db.commit()

    # 执行分析
    analyzer = NewsAnalyzer(session=db)
    analysis = await analyzer.analyze_news(news)

    if not analysis:
        raise HTTPException(status_code=500, detail="分析失败，请检查 API Key 配置")

    return AnalysisResponse(
        id=analysis.id,
        news_id=analysis.news_id,
        ticker=news.company.ticker,
        company_name=news.company.name,
        news_title=news.title,
        level=analysis.level,
        sentiment=analysis.sentiment,
        confidence=analysis.confidence,
        impact_level=analysis.impact_level,
        impact_duration=analysis.impact_duration,
        summary_cn=analysis.summary_cn,
        detailed_analysis=analysis.detailed_analysis,
        related_tickers=analysis.related_tickers,
        key_dates=analysis.key_dates,
        created_at=analysis.created_at,
    )
