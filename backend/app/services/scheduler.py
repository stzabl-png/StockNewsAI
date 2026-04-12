"""
定时任务调度器
- 每小时采集 Finnhub 新闻
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
from app.services.fetchers.finnhub import FinnhubFetcher
from app.services.analyzer import run_analysis_background

logger = logging.getLogger(__name__)

# 全局调度器实例
scheduler = AsyncIOScheduler(timezone="America/New_York")


# =====================================================
#  定时任务函数
# =====================================================

async def job_fetch_news():
    """
    定时采集任务 — 每小时执行
    从 Finnhub 获取所有 Watchlist 公司的最新新闻
    """
    logger.info("[Scheduler] ⏰ 开始定时采集...")
    try:
        redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        async with async_session() as session:
            fetcher = FinnhubFetcher(session=session, redis=redis)
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
        logger.error(f"[Scheduler] ❌ 采集任务失败: {e}")


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
    # 1. 每小时采集新闻
    scheduler.add_job(
        job_fetch_news,
        trigger=IntervalTrigger(hours=1),
        id="fetch_news",
        name="📰 Finnhub 新闻采集",
        replace_existing=True,
        max_instances=1,
    )

    # 2. 每 2 小时补充分析（确保无遗漏）
    scheduler.add_job(
        job_analyze_pending,
        trigger=IntervalTrigger(hours=2, start_date=datetime.now() + timedelta(minutes=10)),
        id="analyze_pending",
        name="🧠 未处理新闻分析",
        replace_existing=True,
        max_instances=1,
    )

    # 3. 每天凌晨 3 点清理旧数据
    scheduler.add_job(
        job_cleanup_old_data,
        trigger=CronTrigger(hour=3, minute=0),
        id="cleanup_old_data",
        name="🧹 旧数据清理",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.start()
    logger.info("[Scheduler] ⏰ 调度器已启动，已注册 3 个定时任务")


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
