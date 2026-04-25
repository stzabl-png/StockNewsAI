"""
从 Polygon.io 批量导入全市场股票
覆盖: NYSE, NASDAQ, NYSE American (NYSEMKT)
过滤: 仅普通股 (type=CS), 活跃 (active=true)
运行: python scripts/init_full_market.py
修复: 每条记录独立事务，避免 InFailedSQLTransactionError 传染
"""
import asyncio, os, sys, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.basicConfig(level=logging.WARNING)

import httpx
from sqlalchemy import text
from app.database import async_session
from app.config import settings

# ── SIC → GICS ──────────────────────────────────────────────
SIC_GICS = [
    # (sic_min, sic_max, gics_sector, sub_sector)
    (7370, 7380, "Information Technology", "IT Services"),
    (7372, 7373, "Information Technology", "Application Software"),
    (3674, 3675, "Information Technology", "Semiconductors"),
    (3670, 3680, "Information Technology", "Electronic Equipment"),
    (3577, 3578, "Information Technology", "Computer Hardware"),
    (3571, 3572, "Information Technology", "Computer Hardware"),
    (2836, 2837, "Health Care", "Biotechnology"),
    (2830, 2836, "Health Care", "Pharmaceuticals"),
    (3841, 3846, "Health Care", "Medical Devices"),
    (8000, 8060, "Health Care", "Health Care Facilities"),
    (8060, 8100, "Health Care", "Managed Health Care"),
    (8090, 8100, "Health Care", "Health Care Services"),
    (5047, 5048, "Health Care", "Health Care Distributors"),
    (6020, 6030, "Financials", "Commercial Banks"),
    (6000, 6100, "Financials", "Commercial Banks"),
    (6110, 6200, "Financials", "Consumer Finance"),
    (6200, 6300, "Financials", "Capital Markets"),
    (6310, 6412, "Financials", "Insurance"),
    (6712, 6730, "Financials", "Diversified Financials"),
    (4800, 4900, "Communication Services", "Telecom"),
    (7810, 7820, "Communication Services", "Entertainment"),
    (2710, 2790, "Communication Services", "Media"),
    (7370, 7376, "Communication Services", "Interactive Media"),
    (5500, 5600, "Consumer Discretionary", "Auto Dealers"),
    (5600, 5700, "Consumer Discretionary", "Apparel Retail"),
    (5700, 5800, "Consumer Discretionary", "Home Furnishings"),
    (7010, 7020, "Consumer Discretionary", "Hotels & Resorts"),
    (5900, 5999, "Consumer Discretionary", "Specialty Retail"),
    (7900, 8000, "Consumer Discretionary", "Leisure"),
    (3710, 3720, "Consumer Discretionary", "Automobiles"),
    (2000, 2050, "Consumer Staples", "Food Products"),
    (2080, 2090, "Consumer Staples", "Beverages"),
    (2100, 2200, "Consumer Staples", "Tobacco"),
    (5400, 5500, "Consumer Staples", "Food & Drug Retail"),
    (5910, 5913, "Consumer Staples", "Drug Retail"),
    (2840, 2845, "Consumer Staples", "Household Products"),
    (3510, 3570, "Industrials", "Industrial Machinery"),
    (3400, 3500, "Industrials", "Fabricated Metals"),
    (3720, 3730, "Industrials", "Aerospace & Defense"),
    (3760, 3770, "Industrials", "Aerospace & Defense"),
    (4510, 4600, "Industrials", "Airlines"),
    (4210, 4220, "Industrials", "Trucking"),
    (4011, 4015, "Industrials", "Railroads"),
    (7380, 7390, "Industrials", "Commercial Services"),
    (8700, 8750, "Industrials", "Professional Services"),
    (1300, 1400, "Energy", "Oil & Gas E&P"),
    (2910, 2920, "Energy", "Oil & Gas Refining"),
    (1381, 1389, "Energy", "Oil & Gas Equipment"),
    (1000, 1100, "Materials", "Metals & Mining"),
    (2600, 2700, "Materials", "Paper & Packaging"),
    (2800, 2830, "Materials", "Chemicals"),
    (3300, 3400, "Materials", "Steel"),
    (1400, 1500, "Materials", "Mining"),
    (4900, 4942, "Utilities", "Electric Utilities"),
    (4942, 4960, "Utilities", "Gas Utilities"),
    (4941, 4942, "Utilities", "Water Utilities"),
    (6500, 6560, "Real Estate", "Real Estate Development"),
    (6798, 6800, "Real Estate", "REITs"),
    (6510, 6515, "Real Estate", "Real Estate Services"),
]

def sic_to_gics(sic_code: int):
    if not sic_code:
        return "Industrials", "General Industrials"
    for mn, mx, gics, sub in SIC_GICS:
        if mn <= sic_code < mx:
            return gics, sub
    return "Industrials", "General Industrials"


POLYGON_BASE = "https://api.polygon.io"

# Exchange codes Polygon uses
VALID_EXCHANGES = {"XNYS", "XNAS", "XASE"}  # NYSE, NASDAQ, NYSE American

async def fetch_all_tickers(api_key: str) -> list[dict]:
    tickers = []
    next_url = (
        f"{POLYGON_BASE}/v3/reference/tickers"
        f"?market=stocks&type=CS&active=true&limit=1000&apiKey={api_key}"
    )
    page = 0
    async with httpx.AsyncClient(timeout=60) as client:
        while next_url:
            try:
                resp = await client.get(next_url)
                if resp.status_code != 200:
                    print(f"  ⚠️ HTTP {resp.status_code}: {resp.text[:200]}")
                    break
                data = resp.json()
                batch = data.get("results", [])
                # Filter by primary exchange
                filtered = [
                    t for t in batch
                    if t.get("primary_exchange", "") in VALID_EXCHANGES
                ]
                tickers.extend(filtered)
                page += 1
                if page % 5 == 0:
                    print(f"  ... 已获取 {len(tickers)} 条 (第{page}页)")
                next_url = data.get("next_url")
                if next_url and "apiKey=" not in next_url:
                    next_url += f"&apiKey={api_key}"
                await asyncio.sleep(0.25)
            except Exception as e:
                print(f"  ⚠️ 分页错误 page{page}: {e}")
                break
    return tickers


async def upsert_one(session, ticker, name, gics_sector, gics_sub, mktcap, tier):
    """Each company in its own savepoint so one failure doesn't abort the whole tx"""
    async with session.begin_nested():  # SAVEPOINT
        row = (await session.execute(
            text("SELECT id FROM companies WHERE ticker=:t"), {"t": ticker}
        )).fetchone()
        if row:
            await session.execute(text("""
                UPDATE companies SET
                    name=:name, gics_sector=:sector, gics_sub_sector=:sub,
                    sector=:sector, market_cap=:cap, tier=:tier, is_active=true,
                    updated_at=now()
                WHERE ticker=:t
            """), {"name": name, "sector": gics_sector, "sub": gics_sub,
                   "cap": int(mktcap), "tier": tier, "t": ticker})
            return "updated"
        else:
            await session.execute(text("""
                INSERT INTO companies
                    (ticker, name, sector, gics_sector, gics_sub_sector,
                     market_cap, tier, therapeutic_area, priority,
                     track_fda, track_trials, is_active, notes)
                VALUES
                    (:t, :name, :s, :s, :sub,
                     :cap, :tier, '', 'medium', :fda, :tri, true, '')
                ON CONFLICT (ticker) DO UPDATE SET
                    name=EXCLUDED.name, gics_sector=EXCLUDED.gics_sector,
                    gics_sub_sector=EXCLUDED.gics_sub_sector,
                    sector=EXCLUDED.sector, market_cap=EXCLUDED.market_cap,
                    tier=EXCLUDED.tier, is_active=true
            """), {
                "t": ticker, "name": name, "s": gics_sector, "sub": gics_sub,
                "cap": int(mktcap), "tier": tier,
                "fda": gics_sector == "Health Care",
                "tri": gics_sector == "Health Care",
            })
            return "added"


async def main():
    api_key = settings.POLYGON_API_KEY
    if not api_key:
        print("❌ POLYGON_API_KEY 未配置")
        return

    print(f"\n🚀 从 Polygon 获取全市场股票 (NYSE + NASDAQ + NYSE American)...")
    tickers = await fetch_all_tickers(api_key)
    print(f"✅ 获取到 {len(tickers)} 只符合条件的股票\n")

    added = updated = skipped = errors = 0

    async with async_session() as session:
        # Begin outer transaction
        async with session.begin():
            for i, t in enumerate(tickers, 1):
                ticker = (t.get("ticker") or "").strip()
                name   = (t.get("name") or "").strip()
                sic    = t.get("sic_code")
                sic_int = int(sic) if sic else 0
                mktcap  = t.get("market_cap") or 0

                # Filters
                if not ticker or not name:
                    skipped += 1; continue
                if len(ticker) > 10:  # skip weird tickers
                    skipped += 1; continue
                # Accept even $0 mktcap — Polygon sometimes doesn't have it
                # Only skip if explicitly very small
                if mktcap and mktcap < 1_000_000:  # < $1M
                    skipped += 1; continue

                gics_sector, gics_sub = sic_to_gics(sic_int)
                tier = "A" if mktcap >= 5e9 else ("B" if mktcap >= 500e6 else "C")

                try:
                    result = await upsert_one(
                        session, ticker, name, gics_sector, gics_sub, mktcap, tier
                    )
                    if result == "added":   added   += 1
                    else:                   updated += 1
                except Exception as e:
                    errors += 1
                    if errors <= 10:
                        print(f"  ❌ {ticker}: {str(e)[:80]}")

                if i % 500 == 0:
                    print(f"  💾 {i}/{len(tickers)}: +{added} 新 / ≈{updated} 更新 / {errors} 错")

    total = added + updated
    print(f"\n✅ 完成!")
    print(f"  新增: {added} 家")
    print(f"  更新: {updated} 家")
    print(f"  跳过: {skipped} 家 (无效ticker/太小)")
    print(f"  错误: {errors} 条")
    print(f"  总计: {total} 家活跃公司进入数据库")


if __name__ == "__main__":
    asyncio.run(main())
