"""
Watchlist 管理 API
- 增删查改关注公司列表
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.company import Company
from app.schemas.watchlist import CompanyCreate, CompanyUpdate, CompanyResponse

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])


@router.get("", response_model=list[CompanyResponse])
async def list_companies(
    active_only: bool = Query(True, description="是否只返回启用的公司"),
    db: AsyncSession = Depends(get_db),
):
    """获取 Watchlist 公司列表"""
    query = select(Company).order_by(Company.priority.desc(), Company.ticker)
    if active_only:
        query = query.where(Company.is_active == True)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/count")
async def get_company_count(db: AsyncSession = Depends(get_db)):
    """获取 Watchlist 公司数量"""
    result = await db.execute(
        select(func.count(Company.id)).where(Company.is_active == True)
    )
    return {"count": result.scalar()}


@router.get("/{ticker}", response_model=CompanyResponse)
async def get_company(ticker: str, db: AsyncSession = Depends(get_db)):
    """获取单个公司详情"""
    result = await db.execute(
        select(Company).where(Company.ticker == ticker.upper())
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail=f"公司 {ticker.upper()} 不在 Watchlist 中")
    return company


@router.post("", response_model=CompanyResponse, status_code=201)
async def add_company(data: CompanyCreate, db: AsyncSession = Depends(get_db)):
    """添加公司到 Watchlist"""
    # 检查是否已存在
    ticker_upper = data.ticker.upper()
    existing = await db.execute(
        select(Company).where(Company.ticker == ticker_upper)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"公司 {ticker_upper} 已在 Watchlist 中")

    company = Company(
        ticker=ticker_upper,
        name=data.name,
        sector=data.sector,
        therapeutic_area=data.therapeutic_area,
        priority=data.priority,
        track_fda=data.track_fda,
        track_trials=data.track_trials,
        notes=data.notes,
    )
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return company


@router.put("/{ticker}", response_model=CompanyResponse)
async def update_company(
    ticker: str,
    data: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新 Watchlist 公司信息"""
    result = await db.execute(
        select(Company).where(Company.ticker == ticker.upper())
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail=f"公司 {ticker.upper()} 不在 Watchlist 中")

    # 只更新非 None 的字段
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(company, field, value)

    await db.commit()
    await db.refresh(company)
    return company


@router.delete("/{ticker}")
async def remove_company(ticker: str, db: AsyncSession = Depends(get_db)):
    """从 Watchlist 删除公司"""
    result = await db.execute(
        select(Company).where(Company.ticker == ticker.upper())
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail=f"公司 {ticker.upper()} 不在 Watchlist 中")

    await db.delete(company)
    await db.commit()
    return {"message": f"已删除 {ticker.upper()}", "ticker": ticker.upper()}
