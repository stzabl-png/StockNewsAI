"""
初始化脚本：将 Tier A（50只核心股）导入数据库
并填充 sectors / sub_sectors / concepts 参考表
运行方式: python scripts/init_tier_a.py (在 backend/ 目录下)
"""
import asyncio
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, text
from app.database import async_session
from app.models.company import Company
from data.sector_config import SECTORS, SUB_SECTORS
from data.concept_config import CONCEPTS


async def init_sectors(session):
    """填充板块参考表"""
    for s in SECTORS:
        await session.execute(text("""
            INSERT INTO sectors (id, name, name_en, gics_code, etf_ticker)
            VALUES (:id, :name, :name_en, :gics_code, :etf)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                name_en = EXCLUDED.name_en,
                gics_code = EXCLUDED.gics_code,
                etf_ticker = EXCLUDED.etf_ticker
        """), {"id": s["id"], "name": s["name"], "name_en": s["name_en"],
               "gics_code": s["gics_code"], "etf": s["etf"]})
    print(f"  ✅ 导入 {len(SECTORS)} 个大板块")


async def init_sub_sectors(session):
    """填充细分行业参考表"""
    for s in SUB_SECTORS:
        await session.execute(text("""
            INSERT INTO sub_sectors (id, sector_id, name, name_en)
            VALUES (:id, :sector_id, :name, :name_en)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                name_en = EXCLUDED.name_en
        """), s)
    print(f"  ✅ 导入 {len(SUB_SECTORS)} 个细分行业")


async def init_concepts(session):
    """填充主题概念参考表"""
    for c in CONCEPTS:
        await session.execute(text("""
            INSERT INTO concepts (id, name, keywords, related_tickers, is_active)
            VALUES (:id, :name, :keywords, :tickers, true)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                keywords = EXCLUDED.keywords,
                related_tickers = EXCLUDED.related_tickers
        """), {
            "id": c["id"],
            "name": c["name"],
            "keywords": c["keywords"],
            "tickers": c["tickers"],
        })
    print(f"  ✅ 导入 {len(CONCEPTS)} 个主题概念")


async def init_companies(session):
    """导入/更新 Tier A 50只核心股"""
    data_path = os.path.join(os.path.dirname(__file__), "../data/sp500_tier_a.json")
    with open(data_path) as f:
        stocks = json.load(f)

    added = 0
    updated = 0

    for i, stock in enumerate(stocks, 1):
        ticker = stock["ticker"]
        result = await session.execute(
            select(Company).where(Company.ticker == ticker)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.name = stock["name"]
            existing.gics_sector = stock["sector"]
            existing.gics_sub_sector = stock["sub_sector"]
            existing.market_cap = stock["market_cap"]
            existing.tier = stock["tier"]
            existing.sp500_rank = i
            existing.is_active = True
            # 保留原有的 sector 字段（旧系统兼容）
            existing.sector = stock["sector"]
            updated += 1
        else:
            company = Company(
                ticker=ticker,
                name=stock["name"],
                sector=stock["sector"],            # 旧字段兼容
                gics_sector=stock["sector"],
                gics_sub_sector=stock["sub_sector"],
                market_cap=stock["market_cap"],
                tier=stock["tier"],
                sp500_rank=i,
                therapeutic_area="",
                priority="high" if stock["tier"] == "A" else "medium",
                track_fda=stock["sector"] in ("Health Care",),
                track_trials=stock["sector"] in ("Health Care",),
                is_active=True,
            )
            session.add(company)
            added += 1

    await session.commit()
    print(f"  ✅ Tier A 公司: 新增 {added} 家, 更新 {updated} 家")


async def main():
    print("\n🚀 初始化板块数据库...")
    async with async_session() as session:
        print("  📁 填充板块参考表...")
        await init_sectors(session)
        await init_sub_sectors(session)
        await init_concepts(session)
        await session.commit()

        print("  📈 导入 Tier A 核心股票...")
        await init_companies(session)

    print("\n✅ 初始化完成！")
    print("  - sectors: 11 个大板块")
    print("  - sub_sectors: 55+ 细分行业")
    print("  - concepts: 31 个主题概念")
    print("  - companies(Tier A): 50 只核心股")


if __name__ == "__main__":
    asyncio.run(main())
