"""
数据库连接管理 — 异步 SQLAlchemy + AsyncPG
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
)

# 创建异步 Session 工厂
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """所有模型的基类"""
    pass


async def get_db():
    """FastAPI 依赖注入 — 获取数据库 Session"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
