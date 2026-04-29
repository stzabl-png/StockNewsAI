"""
定时任务调度器
- 每小时采集 RTPR 一手新闻稿
- 采集后自动分析未处理新闻
- 每天凌晨 3 点清理 30 天前的低影响新闻
"""
import logging
from datetime import datetime, timedelta, timezone

import redis.asyncio as aioredis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, delete, func

from app.config import settings
from app.database import async_session
from app.models.news import News
from app.models.analysis import Analysis
from app.services.fetchers.rtpr import RTPRFetcher
from app.services.fetchers.edgar import EDGARFetcher
from app.services.fetchers.polygon_news import PolygonNewsFetcher
from app.services.fetchers.polygon_market import PolygonMarketFetcher
from app.services.analyzer import run_analysis_background
from app.services.backtester import run_backtest_fill

logger = logging.getLogger(__name__)

# 全局调度器实例
scheduler = AsyncIOScheduler(timezone="America/New_York")


# =====================================================
#  定时任务函数
# =====================================================

async def job_fetch_news():
    """
    定时采集任务 — 每小时执行
    从 RTPR 获取所有 Watchlist 公司的一手新闻稿
    """
    logger.info("[Scheduler] ⏰ 开始定时采集 (RTPR)...")
    try:
        redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        async with async_session() as session:
            fetcher = RTPRFetcher(session=session, redis=redis)
            result = await fetcher.fetch_all()
            logger.info(
                f"[Scheduler] ✅ 采集完成: "
                f"处理 {result['companies_processed']} 家公司, "
                f"获取 {result['total_fetched']} 条, "
                f"新增 {result['new_articles']} 条"
            )

            # 有新文章则自动触发分析
            if result["new_articles"] > 0:
                logger.info("[Scheduler] 🧠 触发自动分析...")
                await run_analysis_background()

        await redis.close()
    except Exception as e:
        logger.error(f"[Scheduler] ❌ RTPR 采集任务失败: {e}")


async def job_fetch_polygon_news():
    """
    Polygon.io 新闻采集 — 每 30 分钟执行（Tier A 核心股）
    """
    logger.info("[Scheduler] ⏰ 开始 Polygon 新闻采集...")
    try:
        redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        async with async_session() as session:
            fetcher = PolygonNewsFetcher(session=session, redis=redis)
            result = await fetcher.fetch_all(hours_back=1)
            logger.info(
                f"[Scheduler] ✅ Polygon 采集完成: "
                f"{result['companies_processed']} 家, "
                f"新增 {result['new_articles']} 条"
            )
            if result["new_articles"] > 0:
                logger.info("[Scheduler] 🧠 触发自动分析...")
                await run_analysis_background()
        await redis.close()
    except Exception as e:
        logger.error(f"[Scheduler] ❌ Polygon 新闻采集失败: {e}")


async def job_fetch_market_snapshots():
    """
    每日行情快照 — 美东时间 20:30（收盘后4小时）执行
    """
    logger.info("[Scheduler] 📊 开始每日行情快照采集...")
    try:
        async with async_session() as session:
            fetcher = PolygonMarketFetcher(session=session)
            result = await fetcher.fetch_all_daily()
            logger.info(
                f"[Scheduler] ✅ 行情快照完成: 保存 {result['saved']} 条, 错误 {result['errors']} 条"
            )
            await fetcher.close()
    except Exception as e:
        logger.error(f"[Scheduler] ❌ 行情快照任务失败: {e}")


async def job_backtest_fill():
    """
    回测价格回填 — 美东 21:00（收盘后4小时）执行
    为所有 HIGH 影响事件回填后续价格表现数据
    """
    logger.info("[Scheduler] 📈 开始回测数据回填...")
    try:
        result = await run_backtest_fill()
        logger.info(f"[Scheduler] ✅ 回测回填完成: {result}")
    except Exception as e:
        logger.error(f"[Scheduler] ❌ 回测回填任务失败: {e}")


async def job_fetch_edgar():
    """
    定时采集 SEC EDGAR 8-K 公告 — 每 2 小时执行
    完全免费，无限历史
    """
    logger.info("[Scheduler] ⏰ 开始定时采集 (EDGAR)...")
    try:
        redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        async with async_session() as session:
            fetcher = EDGARFetcher(session=session, redis=redis)
            result = await fetcher.fetch_all()
            logger.info(
                f"[Scheduler] ✅ EDGAR 采集完成: "
                f"处理 {result['companies_processed']} 家公司, "
                f"获取 {result['total_fetched']} 条, "
                f"新增 {result['new_articles']} 条"
            )

            if result["new_articles"] > 0:
                logger.info("[Scheduler] 🧠 触发自动分析...")
                await run_analysis_background()

        await redis.close()
    except Exception as e:
        logger.error(f"[Scheduler] ❌ EDGAR 采集任务失败: {e}")


async def job_analyze_pending():
    """
    定时分析任务 — 分析所有未处理的新闻
    作为采集任务的补充，确保没有遗漏
    """
    logger.info("[Scheduler] 🧠 开始定时分析...")
    try:
        result = await run_analysis_background()
        logger.info(f"[Scheduler] ✅ 分析完成: {result}")
    except Exception as e:
        logger.error(f"[Scheduler] ❌ 分析任务失败: {e}")


async def job_cleanup_old_data():
    """
    定时清理任务 — 每天凌晨执行
    清理 30 天前的低影响新闻及其分析结果
    保留 HIGH 和 MEDIUM 影响级别的新闻
    """
    logger.info("[Scheduler] 🧹 开始数据清理...")
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)

        async with async_session() as session:
            # 找出 30 天前的低影响新闻 ID
            old_news_query = (
                select(News.id)
                .outerjoin(Analysis)
                .where(News.published_at < cutoff)
                .where(
                    # 没有分析结果，或分析结果为 low impact
                    (Analysis.id == None) | (Analysis.impact_level == "low")  # noqa: E711
                )
            )
            result = await session.execute(old_news_query)
            old_ids = [row[0] for row in result.all()]

            if not old_ids:
                logger.info("[Scheduler] 🧹 没有需要清理的旧数据")
                return

            # 先删除关联的分析结果
            await session.execute(
                delete(Analysis).where(Analysis.news_id.in_(old_ids))
            )
            # 再删除新闻
            deleted = await session.execute(
                delete(News).where(News.id.in_(old_ids))
            )
            await session.commit()

            logger.info(
                f"[Scheduler] ✅ 清理完成: 删除 {deleted.rowcount} 条旧新闻"
            )
    except Exception as e:
        logger.error(f"[Scheduler] ❌ 清理任务失败: {e}")


# =====================================================
#  调度器初始化 & 管理
# =====================================================

def init_scheduler():
    """初始化并启动调度器"""
    # 1. Polygon.io 新闻采集 — 每 30 分钟（主力数据源）
    scheduler.add_job(
        job_fetch_polygon_news,
        trigger=IntervalTrigger(minutes=30),
        id="fetch_polygon_news",
        name="📰 Polygon 新闻采集",
        replace_existing=True,
        max_instances=1,
    )

    # 2. RTPR 一手新闻稿 — 每小时（补充）
    scheduler.add_job(
        job_fetch_news,
        trigger=IntervalTrigger(hours=1, start_date=datetime.now() + timedelta(minutes=2)),
        id="fetch_news",
        name="📰 RTPR 新闻稿采集",
        replace_existing=True,
        max_instances=1,
    )

    # 3. SEC EDGAR 8-K — 每 2 小时
    scheduler.add_job(
        job_fetch_edgar,
        trigger=IntervalTrigger(hours=2, start_date=datetime.now() + timedelta(minutes=5)),
        id="fetch_edgar",
        name="📋 SEC EDGAR 8-K 采集",
        replace_existing=True,
        max_instances=1,
    )

    # 4. 每日行情快照 — 美东 20:30（收盘后）
    scheduler.add_job(
        job_fetch_market_snapshots,
        trigger=CronTrigger(hour=20, minute=30, timezone="America/New_York"),
        id="fetch_market_snapshots",
        name="📊 每日行情快照",
        replace_existing=True,
        max_instances=1,
    )

    # 5. 每 2 小时补充分析（确保无遗漏）
    scheduler.add_job(
        job_analyze_pending,
        trigger=IntervalTrigger(hours=2, start_date=datetime.now() + timedelta(minutes=10)),
        id="analyze_pending",
        name="🧠 未处理新闻分析",
        replace_existing=True,
        max_instances=1,
    )

    # 6. 每天凌晨 3 点清理旧数据
    scheduler.add_job(
        job_cleanup_old_data,
        trigger=CronTrigger(hour=3, minute=0),
        id="cleanup_old_data",
        name="🧹 旧数据清理",
        replace_existing=True,
        max_instances=1,
    )

    # 7. 回测价格回填 — 美东 21:00（收盘后4小时）
    scheduler.add_job(
        job_backtest_fill,
        trigger=CronTrigger(hour=21, minute=0, timezone="America/New_York"),
        id="backtest_fill",
        name="📈 回测数据回填",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.start()
    logger.info("[Scheduler] ⏰ 调度器已启动，已注册 7 个定时任务")


def get_jobs_info() -> list[dict]:
    """获取所有任务的状态信息"""
    jobs = []
    for job in scheduler.get_jobs():
        next_run = job.next_run_time
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": next_run.isoformat() if next_run else None,
            "trigger": str(job.trigger),
            "paused": next_run is None,
        })
    return jobs
