"""
按公司名称关键词将5274家公司分配到85个行业和85个概念
同步更新 sector 字段 + 更新 concepts.related_tickers
"""
import asyncio, os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from app.database import async_session

# ─────────────────────────────────────────────────────────────────────────────
# 85 Chinese Sectors → keyword lists (match against company name)
# Priority order: earlier entries match first
# ─────────────────────────────────────────────────────────────────────────────
SECTOR_KEYWORDS = [
    # ── 科技 ──
    ("半导体",          ["semiconductor", "microchip", "chip", " ic ", "silicon", "wafer", "soc ", "fpga", "asic", "foundry"]),
    ("软件开发",         ["software", " saas", "platform", "digital twin", "cloud native", "devops", "erp ", "crm ", "data analytics", "analytics platform"]),
    ("互联网服务",       ["internet", "online", "digital", "web ", "cyber", "e-commerce", "marketplace", "portal", "social media", "search engine"]),
    ("通信设备",         ["telecom equipment", "network equipment", "router", "switch", "antenna", "wireless equipment", "5g equipment", "optical network"]),
    ("电子元件",         ["electronic component", "connector", "capacitor", "resistor", "pcb", "printed circuit", "passive component"]),
    ("光学光电子",       ["optical", "laser", "photonic", "lidar", "infrared", "lens", "fiber optic", "optoelectron"]),
    ("消费电子",         ["consumer electronic", "smartphone", "tablet", "wearable", "headphone", "speaker", "display", "television", "tv manufacture"]),
    ("计算机设备",       ["computer", "server", "storage system", "data storage", "hard drive", "solid state", "workstation"]),
    ("仪器仪表",         ["instrument", "measurement", "testing equipment", "analyzer", "sensor", "detector", "spectrometer"]),
    ("专业设备",         ["scientific instrument", "laboratory", "precision", "industrial equipment", "process control"]),

    # ── 半导体细分 ──
    ("光伏设备",         ["solar", "photovoltaic", "pv panel", "solar panel", "solar cell", "solar module", "solar energy system"]),
    ("电网设备",         ["power grid", "smart grid", "transformer", "substation", "electric utility equipment", "high voltage", "transmission equipment"]),
    ("电源设备",         ["power equipment", "generator", "ups ", "power supply", "inverter", "rectifier", "uninterruptible"]),
    ("风电设备",         ["wind turbine", "wind farm", "wind power", "offshore wind", "onshore wind"]),
    ("电机",             ["electric motor", "motor manufacturer", "motor drive", "servo motor"]),
    ("电池",             ["battery", "lithium battery", "energy storage solution", "cell manufacture", "electrochemical"]),
    ("通用设备",         ["industrial machinery", "general machinery", "pump manufacturer", "valve manufacturer", "compressor"]),
    ("工程机械",         ["construction machinery", "excavator", "crane", "bulldozer", "forklift", "heavy equipment"]),

    # ── 医疗 ──
    ("生物制品",         ["biologic", "biopharmaceutical", "monoclonal antibody", "antibody", "gene therapy", "mrna", "rna therapy", "aav"]),
    ("化学制药",         ["pharmaceutical", "pharma", "drug", "medicine", "therapeutics", "biotech" ]),
    ("医疗器械",         ["medical device", "medical equipment", "surgical", "implant", "catheter", "endoscope", "diagnostic device"]),
    ("医疗服务",         ["hospital", "clinic", "health care service", "healthcare provider", "outpatient", "nursing", "home health", "dialysis"]),
    ("农药兽药",         ["veterinary", "animal health", "pesticide", "herbicide", "fungicide", "crop protection", "agrochemical"]),
    ("医药商业",         ["drug distribution", "pharmacy", "drug store", "medical supply", "health supply", "pharmaceutical distribution"]),

    # ── 金融 ──
    ("银行类",           ["bank", "bancorp", "banc ", "financial corp", "savings bank", "credit union", "thrift", "federal savings"]),
    ("保险类",           ["insurance", "insurer", "reinsurance", "casualty", "life insurance", "annuity", "surety"]),
    ("券商类",           ["brokerage", "securities", "investment bank", "capital markets", "financial advisory", "asset management", "wealth management"]),
    ("多元金融",         ["financial services", "diversified financial", "consumer finance", "leasing", "factoring", "mortgage reit", "fintech"]),
    ("房地产服务",       ["real estate service", "property management", "real estate agent", "realty service", "property broker"]),

    # ── 能源 ──
    ("石油类",           ["oil", "petroleum", "crude", "refinery", "refining", "drilling", "upstream oil", "natural resource", "hydrocarbon"]),
    ("天然气",           ["natural gas", "lng", "pipeline", "gas distribution", "gas utility", "midstream"]),
    ("煤炭",             ["coal", "metallurgical coal", "thermal coal", "coal mining", "coal company"]),
    ("电力",             ["electric power", "electric utility", "power generation", "electricity", "nuclear power", "hydro power"]),
    ("燃气",             ["gas utility", "gas distribution", "natural gas utility", "gas company"]),
    ("公用事业",         ["utility", "water utility", "sanitation", "waste water", "combined utility"]),
    ("能源金属",         ["uranium", "lithium mining", "cobalt mining", "nickel mining", "rare earth mining"]),

    # ── 材料 ──
    ("钢铁类",           ["steel", "iron", "stainless", "flat-rolled", "long products steel", "mini mill"]),
    ("有色",             ["copper", "aluminum", "zinc", "lead", "nickel", "tin", "non-ferrous", "base metal", "metal mining"]),
    ("小金属",           ["rare metal", "titanium", "molybdenum", "tungsten", "specialty metal", "critical metal", "minor metal"]),
    ("黄金矿业",         ["gold", "silver", "precious metal", "gold mining", "silver mining"]),
    ("化学原料",         ["basic chemical", "commodity chemical", "industrial chemical", "chemical manufacturer"]),
    ("化学制品",         ["specialty chemical", "performance chemical", "fine chemical", "chemical products"]),
    ("电子化学品",       ["electronic chemical", "semiconductor material", "chemical mechanical", "photoresist", "etchant"]),
    ("化肥类",           ["fertilizer", "nitrogen", "ammonia", "phosphate", "potash", "crop nutrient"]),
    ("橡胶制品",         ["rubber", "tire", "tyre", "elastomer", "rubber product"]),
    ("塑料制品",         ["plastic", "polymer", "resin", "polyethylene", "polypropylene", "plastic product"]),
    ("非金属材料",       ["cement", "glass", "ceramic", "gypsum", "mineral material", "aggregate", "quarry"]),
    ("水泥建材",         ["cement", "concrete", "building material", "construction material", "aggregates"]),
    ("玻璃纤维",         ["glass fiber", "fiberglass", "composites", "carbon fiber", "insulation material"]),
    ("包装材料",         ["packaging", "container", "carton", "corrugated", "flexible packaging", "label", "film wrap"]),
    ("造纸印刷",         ["paper", "pulp", "printing", "publishing", "paperboard", "tissue", "newsprint"]),

    # ── 消费 & 零售 ──
    ("食品饮料",         ["food", "beverage", "snack", "dairy", "cereal", "bakery", "nutrition", "consumer food"]),
    ("酒类",             ["beer", "wine", "spirits", "brewery", "winery", "distill", "alcoholic beverage", "malt"]),
    ("美容护理",         ["beauty", "cosmetic", "skincare", "personal care", "haircare", "fragrance", "aesthetic"]),
    ("纺织服饰",         ["apparel", "clothing", "fashion", "textile", "garment", "sportswear", "footwear", "athletic wear"]),
    ("商业百货",         ["department store", "retail", "supermarket", "grocery", "hypermarket", "discount store", "variety store"]),
    ("家电类",           ["appliance", "home appliance", "refrigerator", "washing machine", "dishwasher", "hvac", "air conditioner"]),
    ("家用轻工",         ["household product", "home product", "cleaning product", "tissue", "detergent", "paper towel"]),
    ("珠宝首饰",         ["jewelry", "jewellery", "watch", "diamond", "gemstone", "gold retail"]),
    ("宠物经济",         ["pet ", "animal nutrition", "pet food", "pet care", "veterinary clinic", "pet supply"]),
    ("贸易行业",         ["trading", "distribution", "wholesale", "import export", "sourcing", "commodity trading"]),

    # ── 工业 ──
    ("航空航天",         ["aerospace", "defense", "missile", "satellite manufacture", "spacecraft", "military", "weapons system"]),
    ("船舶制造",         ["shipbuilding", "ship repair", "marine vessel", "naval", "offshore vessel", "boat manufacture"]),
    ("汽车整车",         ["automobile", "car manufacturer", "vehicle manufacturer", "automotive oem", "electric vehicle manufacturer"]),
    ("汽车零部件",       ["auto part", "automotive part", "automotive supplier", "drivetrain", "transmission", "brake", "exhaust"]),
    ("汽车服务",         ["auto dealer", "car dealer", "car rental", "vehicle service", "auto repair", "car wash"]),
    ("工程建设",         ["engineering construction", "heavy construction", "civil engineering", "infrastructure construction", "epc "]),
    ("工程咨询服务",     ["consulting", "advisory", "professional service", "management consulting", "it consulting", "engineering service"]),
    ("物流行业",         ["logistics", "freight", "trucking", "supply chain", "last mile", "fulfillment", "courier", "cargo", "shipping service"]),
    ("航运港口",         ["shipping", "container ship", "bulk carrier", "tanker", "port operator", "maritime"]),
    ("铁路公路",         ["railroad", "railway", "freight rail", "bus operator", "highway", "toll road", "transportation infrastructure"]),
    ("航空机场",         ["airline", "airport", "aviation service", "air freight", "air cargo", "flight"]),
    ("轨道交通",         ["mass transit", "metro", "subway", "rail transit", "commuter rail"]),
    ("交运设备",         ["rail car", "locomotive", "aircraft component", "marine engine", "transportation equipment"]),

    # ── 建筑地产 ──
    ("房地产开发",       ["homebuilder", "home builder", "real estate developer", "condominium", "residential development", "land developer"]),
    ("装修建材",         ["home improvement", "building products", "flooring", "roofing", "windows", "doors", "hardware store"]),
    ("装修装饰",         ["interior design", "decoration", "furniture", "home furnishing", "fitout"]),
    ("工程机械",         ["construction machinery", "earthmoving", "heavy machinery"]),

    # ── 农业 ──
    ("农牧饲渔",         ["agriculture", "farming", "livestock", "poultry", "aquaculture", "crop production", "grain", "meat packing"]),

    # ── 环保 ──
    ("环保类",           ["environmental", "waste management", "recycling", "clean water", "pollution control", "remediation", "clean energy service"]),
    ("水务",             ["water utility", "water treatment", "water purification", "wastewater"]),

    # ── 媒体文化 ──
    ("文化传媒",         ["media", "entertainment", "film", "movie", "music", "broadcasting", "streaming", "television network", "content"]),
    ("游戏",             ["gaming", "video game", "esport", "game developer", "game publisher", "interactive entertainment"]),
    ("教育",             ["education", "school", "university", "learning", "training", "tutoring", "edtech", "online course"]),
    ("旅游酒店",         ["hotel", "resort", "travel", "vacation", "lodging", "hospitality", "cruise", "tourism"]),

    # ── 其他 ──
    ("综合类",           ["holding company", "conglomerate", "diversified", "investment holding", "blank check"]),
]

# ─────────────────────────────────────────────────────────────────────────────
# 85 Concepts → keyword lists for company name matching
# ─────────────────────────────────────────────────────────────────────────────
CONCEPT_KEYWORD_MAP = {
    # Tech
    100: ("人工智能 AI",       ["artificial intelligence", "machine learning", "deep learning", "neural network", "ai platform", "llm", "generative ai", "foundation model"]),
    101: ("AIGC / 生成式AI",   ["generative", "aigc", "content generation", "image generation", "synthetic data", "diffusion"]),
    102: ("半导体",             ["semiconductor", "microchip", "chip design", "silicon", "wafer", "soc", "fpga", "asic"]),
    103: ("云计算",             ["cloud computing", "cloud service", "cloud platform", "cloud infrastructure", "saas", "iaas", "paas"]),
    104: ("网络安全",           ["cybersecurity", "information security", "zero trust", "firewall", "endpoint security", "threat detection", "siem"]),
    105: ("电动汽车 EV",        ["electric vehicle", "ev ", "battery electric", "autonomous vehicle", "ev charging", "electric car"]),
    106: ("生物科技",           ["biotechnology", "biopharmaceutical", "genomics", "proteomics", "gene editing", "cell therapy"]),
    107: ("机器人 & 自动化",    ["robot", "automation", "cobotic", "industrial robot", "autonomous", "drone manufacture"]),
    108: ("数据中心",           ["data center", "colocation", "hyperscale", "server farm", "cloud infrastructure"]),
    109: ("半导体设备",         ["semiconductor equipment", "etch system", "deposition", "lithography", "wafer inspection", "cmp"]),
    110: ("光通信 CPO",         ["optical transceiver", "optical module", "co-packaged optic", "photonic integrated", "fiber optic"]),
    111: ("5G / 通信",          ["5g", "wireless network", "base station", "telecom network", "radio access"]),
    112: ("卫星互联网",         ["satellite", "low earth orbit", "leo satellite", "satellite internet", "space internet"]),
    113: ("互联网 & 平台",      ["internet platform", "social network", "search engine", "marketplace platform", "e-commerce platform"]),
    114: ("软件 SaaS",          ["saas", "cloud software", "subscription software", "enterprise software", "platform software"]),
    115: ("存储 & 内存芯片",    ["memory", "dram", "nand", "flash storage", "solid state drive", "storage semiconductor"]),
    116: ("区块链 & 加密",      ["blockchain", "cryptocurrency", "bitcoin", "digital asset", "crypto exchange", "web3"]),
    117: ("元宇宙 & VR/AR",     ["metaverse", "virtual reality", "augmented reality", "mixed reality", "spatial computing", "vr headset"]),
    118: ("大数据 & 分析",      ["big data", "data analytics", "business intelligence", "data warehouse", "data lake", "analytics"]),
    # Clean energy
    120: ("光伏太阳能",         ["solar", "photovoltaic", "pv module", "solar panel", "solar cell", "solar energy"]),
    121: ("风电",               ["wind energy", "wind power", "wind turbine", "offshore wind"]),
    122: ("储能",               ["energy storage", "battery storage", "grid storage", "bess", "stationary storage"]),
    123: ("EV充电桩",           ["ev charging", "charging station", "charging network", "evse", "charge point"]),
    124: ("锂 & 新能源材料",    ["lithium", "battery material", "cathode material", "anode", "electrolyte", "energy metal"]),
    125: ("电网设备 & 特高压",  ["power grid", "smart grid", "electric transmission", "high voltage", "grid equipment", "transformer"]),
    126: ("清洁能源 & 核电",    ["clean energy", "nuclear energy", "nuclear power", "uranium", "renewable energy"]),
    # Pharma/health
    130: ("创新药 & GLP-1",     ["drug discovery", "innovative drug", "glp-1", "obesity treatment", "weight loss drug", "novel therapy"]),
    131: ("CRO / CXO",          ["contract research", "clinical research organization", "cro ", "cdmo", "contract manufacturing"]),
    132: ("医疗器械",           ["medical device", "surgical robot", "implant", "medical imaging", "diagnostic equipment"]),
    133: ("疫苗 & 生物制品",    ["vaccine", "mrna vaccine", "biologic", "antigen", "immunization", "biologics manufacturer"]),
    134: ("宠物经济",           ["pet health", "animal health", "veterinary", "pet food", "pet care"]),
    # Finance
    140: ("金融科技 & 支付",    ["payment processing", "digital payment", "fintech", "neobank", "payment platform", "mobile payment"]),
    141: ("银行 & 投行",        ["bank", "investment banking", "commercial banking", "financial institution"]),
    142: ("保险",               ["insurance", "reinsurance", "underwriting", "insurer"]),
    143: ("券商 & 资管",        ["brokerage", "asset management", "wealth management", "investment management", "fund management"]),
    # Industrial
    150: ("航空航天 & 军工",    ["aerospace", "defense contractor", "military", "missile", "aircraft manufacturer", "space"]),
    151: ("工程机械 & 重工",    ["construction equipment", "heavy equipment", "earthmoving", "crane", "industrial machinery"]),
    152: ("物流 & 快递",        ["logistics", "freight", "express delivery", "supply chain", "warehouse", "fulfillment"]),
    153: ("轨道交通",           ["railroad", "freight rail", "passenger rail", "railway"]),
    154: ("航运 & 港口",        ["ocean shipping", "container shipping", "bulk shipping", "tanker", "port"]),
    155: ("汽车 & 零部件",      ["automobile", "auto part", "automotive supplier", "electric vehicle maker", "car manufacturer"]),
    156: ("钢铁 & 金属",        ["steel", "aluminum", "copper", "iron", "metal", "alloy"]),
    # Resources
    160: ("石油 & 天然气",      ["oil", "natural gas", "lng", "petroleum", "crude", "drilling", "upstream", "midstream"]),
    161: ("煤炭",               ["coal", "coal mining", "thermal coal", "metallurgical coal"]),
    162: ("铜 & 稀土",          ["copper", "rare earth", "lithium", "cobalt", "critical mineral", "mining"]),
    163: ("黄金 & 贵金属",      ["gold", "silver", "precious metal", "gold mine", "royalty"]),
    164: ("化工 & 特种材料",    ["specialty chemical", "industrial chemical", "coatings", "adhesive", "polymer"]),
    165: ("化肥 & 农化",        ["fertilizer", "nitrogen", "ammonia", "crop protection", "agrochemical"]),
    # Consumer
    170: ("食品饮料",           ["food", "beverage", "snack", "dairy", "nutrition", "packaged food"]),
    171: ("酒类",               ["beer", "wine", "spirits", "brewery", "distill", "alcoholic"]),
    172: ("美妆 & 医美",        ["beauty", "cosmetic", "skincare", "aesthetic", "personal care"]),
    173: ("电商 & 新零售",      ["e-commerce", "online retail", "digital commerce", "marketplace", "direct-to-consumer"]),
    174: ("游戏 & 娱乐",        ["gaming", "video game", "entertainment", "streaming", "content"]),
    175: ("旅游 & 酒店",        ["hotel", "travel", "hospitality", "cruise", "resort", "tourism"]),
    176: ("教育",               ["education", "edtech", "elearning", "online learning", "tutoring"]),
    # Real estate
    180: ("房地产 & REITs",     ["reit", "real estate investment", "property trust", "real estate fund"]),
    181: ("房屋建造 & 建材",    ["homebuilder", "home builder", "building product", "construction material"]),
    182: ("基建 & 工程建设",    ["infrastructure", "construction service", "civil engineering", "utility construction"]),
    183: ("水务 & 环保",        ["water", "waste management", "environmental service", "recycling", "pollution"]),
    # Utilities
    190: ("电力 & 公用事业",    ["electric utility", "power generation", "electricity provider", "electric company"]),
    191: ("燃气 & 管线",        ["gas utility", "natural gas distribution", "gas pipeline", "lng terminal"]),
    # Agri
    195: ("农业 & 粮食",        ["agriculture", "farming", "crop", "grain", "agribusiness", "seed"]),
    196: ("碳中和 & ESG",       ["carbon neutral", "net zero", "clean energy", "sustainable", "esg", "green energy"]),
}

# ─────────────────────────────────────────────────────────────────────────────

def match_sector(name_lower: str) -> str:
    for sector, keywords in SECTOR_KEYWORDS:
        for kw in keywords:
            if kw in name_lower:
                return sector
    return "综合类"


def match_concepts(name_lower: str) -> list[int]:
    matched = []
    for cid, (cname, keywords) in CONCEPT_KEYWORD_MAP.items():
        for kw in keywords:
            if kw in name_lower:
                matched.append(cid)
                break
    return matched


async def main():
    print("\n\U0001f680 开始对 5274 家公司进行行业/概念分配...\n")

    async with async_session() as session:
        # Fetch all companies
        rows = (await session.execute(text(
            "SELECT id, ticker, name FROM companies WHERE is_active=true ORDER BY id"
        ))).fetchall()
        print(f"\U0001f4ca 从数据库读取 {len(rows)} 家公司")

        # Phase 1: keyword classification in memory
        sector_map: dict[str, list[str]] = {}
        concept_map: dict[int, list[str]] = {cid: [] for cid in CONCEPT_KEYWORD_MAP}
        updates = []

        for company_id, ticker, name in rows:
            name_lower = (name or ticker).lower()
            sector = match_sector(name_lower)
            sector_map.setdefault(sector, []).append(ticker)
            for cid in match_concepts(name_lower):
                concept_map[cid].append(ticker)
            updates.append((sector, company_id))

        # Phase 2: Batch update company sectors (commits every 1000)
        print(f"\U0001f4be 更新公司 sector 字段...")
        batch_size = 1000
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i+batch_size]
            for sector, company_id in batch:
                await session.execute(
                    text("UPDATE companies SET sector=:s WHERE id=:id"),
                    {"s": sector, "id": company_id}
                )
            await session.commit()
            print(f"   {min(i+batch_size, len(updates))}/{len(updates)} 已更新")

        # Print sector distribution
        print("\n\U0001f4ca 行业分布:")
        sorted_sectors = sorted(sector_map.items(), key=lambda x: -len(x[1]))
        for sector, tickers in sorted_sectors[:40]:
            print(f"   {sector}: {len(tickers)} 家")
        remaining = sum(len(v) for k,v in sorted_sectors[40:])
        if remaining:
            print(f"   ... 其余 {len(sorted_sectors)-40} 个行业共 {remaining} 家")

        # Phase 3: Update concept related_tickers
        print("\n\U0001f4be 更新概念关联公司...")
        for cid, tickers in concept_map.items():
            if not tickers:
                continue
            placeholders = ','.join(f"'{t}'" for t in tickers[:500])
            result = await session.execute(text(f"""
                SELECT ticker FROM companies 
                WHERE ticker IN ({placeholders}) AND is_active=true
                ORDER BY COALESCE(market_cap, 0) DESC LIMIT 200
            """))
            final_tickers = [r[0] for r in result.fetchall()]
            await session.execute(
                text("UPDATE concepts SET related_tickers=:t WHERE id=:id"),
                {"t": final_tickers, "id": cid}
            )
            cname = CONCEPT_KEYWORD_MAP[cid][0]
            if final_tickers:
                print(f"   {cname}: {len(final_tickers)} 家")
        await session.commit()

    print("\n\u2705 完成!")

if __name__ == "__main__":
    asyncio.run(main())
