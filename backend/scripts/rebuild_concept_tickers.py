"""
用概念关键词对全量5274家公司做名称/ticker/sector匹配,
将匹配到的ticker批量写入 concepts.related_tickers
运行: docker exec stocknews-backend python scripts/rebuild_concept_tickers.py
"""
import asyncio, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from app.database import async_session

# ── 额外的概念→sector 直接映射 (补充关键词不够的情况) ──────────────────
CONCEPT_SECTOR_MAP = {
    100: ["人工智能"],
    105: ["新能源汽车"],
    108: ["云计算", "互联网服务", "软件开发"],
    110: ["半导体", "芯片制造"],
    112: ["卫星互联网", "航空航天"],
    115: ["存储芯片", "计算机设备", "半导体"],
    118: ["云计算", "软件开发", "计算机设备"],
    120: ["基因工程", "生物制品", "基因检测"],
    123: ["医疗器械"],
    125: ["医疗服务"],
    128: ["化学制药", "生物制品"],
    130: ["新能源", "电力", "光伏"],
    133: ["储能", "电池", "新能源"],
    134: ["宠物经济"],
    136: ["消费零售", "商业百货"],
    137: ["旅游酒店"],
    139: ["金融科技"],
    140: ["多元金融", "银行类"],
    141: ["保险类"],
    142: ["银行类"],
    143: ["券商类"],
    145: ["房地产开发", "房地产服务"],
    148: ["大宗商品"],
    150: ["农牧饲渔"],
    151: ["工程机械"],
    153: ["铁路公路"],
    154: ["物流行业"],
    155: ["汽车整车", "汽车零部件"],
    157: ["航运港口"],
    158: ["航空机场"],
    160: ["石油类"],
    161: ["煤炭"],
    163: ["钢铁类"],
    165: ["有色"],
    167: ["化学制品", "化学原料"],
    168: ["化肥类"],
    170: ["食品饮料"],
    171: ["酒类"],
    175: ["游戏"],
    177: ["文化传媒"],
    178: ["教育"],
    180: ["电商零售", "商业百货"],
    181: ["房地产开发", "装修建材"],
    182: ["通信服务"],
    185: ["黄金矿业"],
    187: ["能源金属"],
    190: ["电力", "公用事业"],
}

# ── 额外的概念→ticker 直接映射 (知名公司补充) ──────────────────────────
CONCEPT_TICKER_EXTRAS = {
    100: ["NVDA","MSFT","GOOGL","META","AMZN","AAPL","ORCL","CRM","IBM","PLTR","AI","C3AI","BBAI","SOUN","CIEN"],
    105: ["TSLA","RIVN","LCID","NIO","LI","XPEV","GM","F","BMW","STLA","CHPT","BLNK","EVGO","NKLA"],
    108: ["AMZN","MSFT","GOOGL","CRM","NOW","SNOW","DDOG","MDB","NET","CFLT","ESTC","GTLB","ZS","OKTA","HUBS"],
    110: ["NVDA","AMD","INTC","TSM","AVGO","QCOM","MU","TXN","AMAT","KLAC","LRCX","ASML","ON","MRVL","SWKS","MCHP"],
    112: ["SATS","MAXR","ASTS","RKLB","SPCE","IRDM","GSAT","VSAT","LHX","BA","NOC"],
    115: ["MU","WDC","SNDK","STX","SIMO","MRAM","NAND","KOXW","SMCI","NTAP","PSTG"],
    118: ["SNOW","PLTR","DBX","DDOG","MDB","SPLK","FIVN","ESTC","NICE","VEEV","WDAY"],
    120: ["CRSP","EDIT","NTLA","BEAM","NVAX","MRNA","REGN","VRTX","BIIB","AMGN","GILD","ILMN","PACB","CDNA"],
    123: ["ISRG","MDT","ABT","BSX","ZBH","SYK","EW","HOLX","DXCM","INMD","NVCR"],
    125: ["UNH","CVS","HCA","THC","CNC","MOH","ELV","DVA","RDNT","ACAD"],
    128: ["PFE","JNJ","MRK","LLY","BMY","ABBV","AZN","NVO","GSK","SNY","RGEN","EXEL"],
    130: ["ENPH","FSLR","SEDG","RUN","ARRY","CSIQ","MAXN","JKS","DAQO","GCO"],
    133: ["TSLA","ALB","LTHM","LAC","SQM","FMC","NXPI","TE","RKLB"],
    134: ["CHWY","FRPT","TRUP","CENT","CENTA","IDXX","PETS","WOOF"],
    136: ["AMZN","WMT","TGT","COST","HD","LOW","BBY","M","KSS","JWN","ETSY","EBAY","W"],
    137: ["MAR","HLT","H","WH","CHH","NCLH","CCL","RCL","UAL","DAL","AAL","LUV","BKNG","EXPE","ABNB"],
    139: ["SQ","PYPL","V","MA","AFRM","UPST","SOFI","NRDS","NU","RELY","FICO","FIS","FISV","GPN"],
    140: ["JPM","BAC","WFC","C","GS","MS","USB","PNC","TFC","KEY","RF","CFG","HBAN","MTB","ZION"],
    141: ["BRK.B","MET","PRU","AFL","PGR","TRV","HIG","CB","ALL","L","AIG","LNC","GL","RNR"],
    142: ["JPM","BAC","WFC","C","USB","PNC","TFC","KEY","RF","CFG","HBAN","MTB","FITB","ZION","EWBC","BOKF"],
    143: ["GS","MS","SCHW","RJF","LPL","LPLA","VIRT","IBKR","HOOD","MKTX","BGC"],
    145: ["AMT","PLD","SPG","O","WELL","EQR","AVB","ESS","MAA","UDR","CPT","NNN","STAG"],
    148: ["FCX","NEM","GOLD","AEM","WPM","BHP","RIO","VALE","AA","CLF","X","NUE","SCCO","TECK"],
    150: ["ADM","BG","MOS","CF","NTR","INGR","DAR","CALM","TSN","HRL","PPC","SAFM"],
    151: ["CAT","DE","PCAR","CMI","TEX","AGCO","CNH","OSK","ITW","IR","ROK","PH"],
    153: ["UNP","CSX","NSC","KSU","CP","CN","GATX","WAB","TRN","RAIL"],
    154: ["UPS","FDX","XPO","GXO","ODFL","SAIA","WERN","KNX","CHRW","EXPD","JBHT","ECHO"],
    155: ["TSLA","GM","F","TM","HMC","VWAGY","STLA","TD","LEA","BWA","APTV","DAN","MGA","VC","ALV"],
    157: ["ZIM","DAC","MATX","GLBS","SBLK","GOGL","GNK","EGLE","SALT","DSX","EDRY"],
    158: ["UAL","DAL","AAL","LUV","JBLU","ALK","HA","SAVE","SKYW","MESA","RJET"],
    160: ["XOM","CVX","COP","EOG","PXD","OXY","HES","MRO","DVN","FANG","APA","PSX","VLO","MPC","PBF"],
    161: ["BTU","ARCH","AMR","CEIX","CONSOL","HCC","METC","RAMCO","ARLP","FORESIGHT"],
    163: ["NUE","STLD","X","CLF","RS","CMC","USCO","AKS","WOR","ZEKH","IIIN"],
    165: ["FCX","AA","CENX","KALU","ATI","VALE","SCO","MP","NEM","AEM","GOLD"],
    167: ["LIN","APD","ALB","EMN","PPG","RPM","FMC","CC","TROX","OLIN","HUN","ASH","WLK","LYB"],
    168: ["MOS","CF","NTR","SMG","YARA","ICL","UAN","CFTC"],
    170: ["KO","PEP","MCD","SBUX","YUM","QSR","KHC","GIS","K","CAG","CPB","SJM","HRL","POST","LANC"],
    171: ["BUD","TAP","SAM","COORS","DEO","BF.B","MGPI","EAST","FIZZ"],
    175: ["ATVI","EA","TTWO","RBLX","U","GAMESTOP","DKNG","LNW","PENN","RSI","EVRI","AGS"],
    177: ["DIS","CMCSA","NFLX","PARA","WBD","LGF.A","AMC","CNK","IMAX","NYT","GCI","MCS"],
    178: ["CHGG","2U","PRDO","STRA","COUR","LAUR","UTI","LRN","LESI","ARCO"],
    180: ["AMZN","BABA","JD","PDD","SE","MELI","ETSY","EBAY","WISH","REAL","OSTK"],
    181: ["LEN","DHI","PHM","TOL","NVR","KBH","MDC","MHO","TMHC","SKY","BECN","BLDR","FBHS"],
    182: ["T","VZ","TMUS","LUMN","CCOI","SHEN","USMO","DISH","SATS","ATUS","CNSL"],
    185: ["NEM","GOLD","AEM","WPM","KGC","HL","AG","EXK","CDE","PAAS","SILV","MAG","SSRM"],
    187: ["ALB","LAC","LTHM","SQM","SGML","PLL","MP","UUUU","NXE","UEC","CCJ","DNN"],
    190: ["NEE","SO","DUK","AEP","EXC","D","PCG","SRE","XEL","ES","EIX","AWK","RSG","WM","CVA"],
}

async def main():
    async with async_session() as session:
        # Load all companies
        companies = (await session.execute(text(
            "SELECT ticker, name, sector FROM companies WHERE is_active=true"
        ))).fetchall()
        print(f"📦 总公司数: {len(companies)}")

        # Load all concepts
        concepts = (await session.execute(text(
            "SELECT id, name, keywords FROM concepts WHERE is_active=true"
        ))).fetchall()
        print(f"🏷️  概念数: {len(concepts)}")

        valid_ids = {c[0] for c in concepts}

        # Build concept → matched tickers (only for IDs that exist in DB)
        concept_tickers: dict[int, set] = {c[0]: set() for c in concepts}

        # 1. Keyword matching against company name + ticker
        for cid, cname, keywords in concepts:
            if not keywords:
                continue
            kws = [k.lower().strip() for k in keywords if k.strip()]
            for ticker, name, sector in companies:
                name_lower = (name or "").lower()
                ticker_lower = (ticker or "").lower()
                for kw in kws:
                    if kw and (kw in name_lower or kw in ticker_lower):
                        concept_tickers[cid].add(ticker)
                        break

        # 2. Sector mapping (only valid IDs)
        for cid, sectors in CONCEPT_SECTOR_MAP.items():
            if cid not in valid_ids:
                continue
            for ticker, name, sector in companies:
                if sector in sectors:
                    concept_tickers[cid].add(ticker)

        # 3. Extra hand-curated tickers (only valid IDs)
        for cid, tickers in CONCEPT_TICKER_EXTRAS.items():
            if cid not in valid_ids:
                continue
            concept_tickers[cid].update(tickers)

        # 4. Update DB in batches
        total_updated = 0
        for cid, tickers in concept_tickers.items():
            if not tickers:
                continue
            # Sort by ticker for stability, limit to 500 per concept
            t_list = sorted(tickers)[:500]
            await session.execute(
                text("UPDATE concepts SET related_tickers=:t WHERE id=:id"),
                {"t": t_list, "id": cid}
            )
            total_updated += 1
            # Find concept name for logging
            cname = next((c[1] for c in concepts if c[0] == cid), str(cid))
            print(f"  [{cid}] {cname}: {len(t_list)} 家")

        await session.commit()
        print(f"\n✅ 更新了 {total_updated} 个概念的公司列表")

if __name__ == "__main__":
    asyncio.run(main())
