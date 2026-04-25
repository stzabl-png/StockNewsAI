"""
初始化脚本：导入完整 S&P500 + NASDAQ100 公司数据
运行方式: python scripts/init_sp500_full.py
"""
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, select
from app.database import async_session
from app.models.company import Company
from data.sp500_nasdaq_full import SP500_NASDAQ, US_CONCEPTS


async def init_concepts(session):
    """更新概念表为美股专属体系"""
    for c in US_CONCEPTS:
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
    print(f"  ✅ 导入 {len(US_CONCEPTS)} 个美股主题概念")


async def init_companies(session):
    """批量导入/更新公司"""
    added = 0
    updated = 0

    for i, item in enumerate(SP500_NASDAQ, 1):
        if len(item) == 6:
            ticker, name, sector, sub_sector, market_cap_m, concepts = item
        else:
            continue

        market_cap = market_cap_m * 1e6  # convert from M to actual
        tier = "A" if market_cap_m >= 500 else ("B" if market_cap_m >= 100 else "C")

        result = await session.execute(
            select(Company).where(Company.ticker == ticker)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.name = name
            existing.gics_sector = sector
            existing.gics_sub_sector = sub_sector
            existing.sector = sector
            existing.market_cap = market_cap
            existing.tier = tier
            existing.sp500_rank = i
            existing.is_active = True
            updated += 1
        else:
            company = Company(
                ticker=ticker,
                name=name,
                sector=sector,
                gics_sector=sector,
                gics_sub_sector=sub_sector,
                market_cap=market_cap,
                tier=tier,
                sp500_rank=i,
                therapeutic_area="",
                priority="high" if tier == "A" else "medium",
                track_fda=(sector == "Health Care"),
                track_trials=(sector == "Health Care"),
                is_active=True,
            )
            session.add(company)
            added += 1

        if i % 50 == 0:
            await session.flush()
            print(f"  ... {i}/{len(SP500_NASDAQ)} 处理中")

    await session.commit()
    print(f"  ✅ 公司: 新增 {added} 家, 更新 {updated} 家")
    return added + updated


async def main():
    print("\n🚀 导入 S&P500 + NASDAQ100 完整数据...")
    async with async_session() as session:
        print("  💡 更新美股主题概念...")
        await init_concepts(session)
        await session.commit()

        print("  📈 导入公司数据...")
        total = await init_companies(session)

    print(f"\n✅ 完成！共 {total} 家公司")
    print(f"  - 覆盖所有 11 个 GICS 大板块")
    print(f"  - {len(US_CONCEPTS)} 个美股主题概念（{sum(1 for c in US_CONCEPTS if c['is_default'])} 个默认显示）")


if __name__ == "__main__":
    asyncio.run(main())
