"""
FastAPI 应用入口 — 生命周期管理 + 健康检查
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import redis.asyncio as aioredis
from sqlalchemy import text

from app.config import settings
from app.database import engine, async_session


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # ---- Startup ----
    # 连接 Redis
    app.state.redis = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )

    # 启动定时调度器
    from app.services.scheduler import init_scheduler, scheduler
    init_scheduler()

    # 后台预热行情缓存（不阻塞启动）
    import asyncio as _asyncio
    async def _warmup():
        await _asyncio.sleep(5)  # 等待DB连接稳定
        try:
            from app.api.market import get_market_overview
            await get_market_overview()
            print("✅ 行情缓存预热完成")
        except Exception as e:
            print(f"⚠️ 行情缓存预热失败: {e}")
    _asyncio.ensure_future(_warmup())

    yield

    # ---- Shutdown ----
    scheduler.shutdown(wait=False)
    await app.state.redis.close()
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    description="QuantNews — 美股生物医药新闻智能分析平台",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 中间件（开发阶段允许所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- 注册路由 ----
from app.api.watchlist import router as watchlist_router
from app.api.news import router as news_router
from app.api.analysis import router as analysis_router
from app.api.scheduler import router as scheduler_router
from app.api.notify import router as notify_router
from app.api.sectors import router as sectors_router
from app.api.market import router as market_router

app.include_router(watchlist_router, prefix="/api")
app.include_router(news_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(scheduler_router, prefix="/api")
app.include_router(notify_router, prefix="/api")
app.include_router(sectors_router, prefix="/api")
app.include_router(market_router, prefix="/api")

# ---- 前端静态文件 ----
import os
FRONTEND_DIR = "/app/frontend"
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
async def serve_dashboard():
    """服务前端 Dashboard"""
    return FileResponse(f"{FRONTEND_DIR}/index.html")


@app.get("/api/health")
async def health_check():
    """
    健康检查接口
    - 检测数据库连接
    - 检测 Redis 连接
    - 返回系统状态
    """
    # 检查数据库
    db_status = "connected"
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    # 检查 Redis
    redis_status = "connected"
    try:
        await app.state.redis.ping()
    except Exception as e:
        redis_status = f"error: {str(e)}"

    # 检查调度器
    from app.services.scheduler import scheduler
    scheduler_status = "running" if scheduler.running else "stopped"

    overall = "ok" if db_status == "connected" and redis_status == "connected" else "degraded"

    return {
        "status": overall,
        "db": db_status,
        "redis": redis_status,
        "scheduler": scheduler_status,
        "app": settings.APP_NAME,
        "version": "1.0.0",
    }
