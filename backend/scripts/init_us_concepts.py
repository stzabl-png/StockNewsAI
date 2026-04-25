"""
美股市场概念体系 —— 对标A股行业与主题概念
覆盖 A股 85个行业 + 85个概念中在美股有对应标的的品种

运行: python scripts/init_us_concepts.py
"""
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import async_session

# ─────────────────────────────────────────────────────────────────────────────
# 完整美股概念列表（对标A股行业+概念体系）
# id:       唯一ID（从100开始，避免与旧数据冲突）
# name:     中文名称
# name_en:  英文名称
# icon:     emoji
# keywords: 相关关键词
# tickers:  代表性美股标的
# is_default: 是否默认显示（科技类优先）
# ─────────────────────────────────────────────────────────────────────────────
US_CONCEPTS_FULL = [
    # ======================== 科技（默认显示）========================
    {
        "id": 100, "name": "人工智能 AI", "name_en": "Artificial Intelligence",
        "icon": "🤖", "is_default": True,
        "keywords": ["artificial intelligence", "machine learning", "LLM", "AI", "foundation model"],
        "tickers": ["NVDA", "MSFT", "GOOGL", "META", "AMZN", "AMD", "IBM", "PLTR", "ORCL", "APP", "SMCI"],
    },
    {
        "id": 101, "name": "AIGC / 生成式AI", "name_en": "Generative AI",
        "icon": "✨", "is_default": True,
        "keywords": ["generative AI", "AIGC", "ChatGPT", "image generation", "text generation"],
        "tickers": ["MSFT", "GOOGL", "META", "ADBE", "AMZN", "AAPL", "ORCL", "SOUN", "AIXI"],
    },
    {
        "id": 102, "name": "半导体", "name_en": "Semiconductors",
        "icon": "🔬", "is_default": True,
        "keywords": ["semiconductor", "chip", "wafer", "foundry", "integrated circuit"],
        "tickers": ["NVDA", "AVGO", "AMD", "QCOM", "TXN", "INTC", "MU", "AMAT", "ARM", "MRVL", "KLAC", "LRCX"],
    },
    {
        "id": 103, "name": "云计算", "name_en": "Cloud Computing",
        "icon": "☁️", "is_default": True,
        "keywords": ["cloud computing", "SaaS", "IaaS", "PaaS", "cloud services"],
        "tickers": ["AMZN", "MSFT", "GOOGL", "CRM", "NOW", "SNOW", "NET", "DDOG", "WDAY", "ADBE"],
    },
    {
        "id": 104, "name": "网络安全", "name_en": "Cybersecurity",
        "icon": "🛡️", "is_default": True,
        "keywords": ["cybersecurity", "zero trust", "firewall", "endpoint security", "threat detection"],
        "tickers": ["CRWD", "PANW", "FTNT", "ZS", "OKTA", "S", "CYBR", "TENB", "RPD", "VRNT", "NET"],
    },
    {
        "id": 105, "name": "电动汽车 EV", "name_en": "Electric Vehicles",
        "icon": "⚡", "is_default": True,
        "keywords": ["electric vehicle", "EV", "battery", "charging", "autonomous driving"],
        "tickers": ["TSLA", "RIVN", "LCID", "GM", "F", "CHPT", "BLNK", "EVGO", "NIO", "LI", "XPEV"],
    },
    {
        "id": 106, "name": "生物科技", "name_en": "Biotechnology",
        "icon": "🧬", "is_default": True,
        "keywords": ["biotechnology", "gene therapy", "CRISPR", "mRNA", "biologics"],
        "tickers": ["MRNA", "REGN", "VRTX", "BIIB", "GILD", "AMGN", "CRSP", "BEAM", "NTLA", "EXAS"],
    },
    {
        "id": 107, "name": "机器人 & 自动化", "name_en": "Robotics & Automation",
        "icon": "🦾", "is_default": True,
        "keywords": ["robotics", "automation", "industrial robot", "autonomous", "drone"],
        "tickers": ["ISRG", "ROK", "ABB", "IRBT", "NVDA", "TSLA", "AMZN", "HON", "EMR", "PTC", "FANUY"],
    },

    # ======================== 更多科技 ========================
    {
        "id": 108, "name": "数据中心", "name_en": "Data Centers",
        "icon": "🏢", "is_default": False,
        "keywords": ["data center", "server", "colocation", "hyperscale", "infrastructure"],
        "tickers": ["EQIX", "DLR", "AMT", "SMCI", "DELL", "HPE", "NTAP", "NVDA", "AMD", "MSFT"],
    },
    {
        "id": 109, "name": "半导体设备", "name_en": "Semiconductor Equipment",
        "icon": "⚙️", "is_default": False,
        "keywords": ["semiconductor equipment", "lithography", "etch", "deposition", "wafer inspection"],
        "tickers": ["AMAT", "LRCX", "KLAC", "TER", "ONTO", "ENTG", "ASML", "CCMP", "AZTA"],
    },
    {
        "id": 110, "name": "光通信 CPO", "name_en": "Optical Communications",
        "icon": "📡", "is_default": False,
        "keywords": ["optical", "fiber", "CPO", "co-packaged optics", "transceiver", "photonics"],
        "tickers": ["COHR", "VIAV", "CIEN", "GLW", "LITE", "FNSR", "AAOI", "IIVI", "INPHI"],
    },
    {
        "id": 111, "name": "5G / 通信", "name_en": "5G & Telecom",
        "icon": "📶", "is_default": False,
        "keywords": ["5G", "telecom", "network", "spectrum", "base station", "wireless"],
        "tickers": ["QCOM", "CSCO", "ERIC", "NOK", "T", "VZ", "TMUS", "CIEN", "VIAV", "CALX", "AMT"],
    },
    {
        "id": 112, "name": "卫星互联网", "name_en": "Satellite Internet & Space",
        "icon": "🛸", "is_default": False,
        "keywords": ["satellite", "low earth orbit", "LEO", "space internet", "Starlink"],
        "tickers": ["ASTS", "RKLB", "IRDM", "VSAT", "GSAT", "SPCE", "MAXR", "SATS", "LMT", "NOC"],
    },
    {
        "id": 113, "name": "互联网 & 平台", "name_en": "Internet Platforms",
        "icon": "🌐", "is_default": False,
        "keywords": ["internet", "platform", "social media", "search", "e-commerce", "marketplace"],
        "tickers": ["GOOGL", "META", "AMZN", "NFLX", "SNAP", "PINS", "RDDT", "DASH", "ABNB", "UBER", "LYFT"],
    },
    {
        "id": 114, "name": "软件 SaaS", "name_en": "Enterprise Software",
        "icon": "💾", "is_default": False,
        "keywords": ["software", "SaaS", "enterprise", "CRM", "ERP", "application"],
        "tickers": ["MSFT", "CRM", "NOW", "ADBE", "WDAY", "INTU", "ANSS", "PTC", "TEAM", "HUBS", "DDOG"],
    },
    {
        "id": 115, "name": "存储 & 内存芯片", "name_en": "Memory & Storage",
        "icon": "💿", "is_default": False,
        "keywords": ["memory", "DRAM", "NAND", "flash storage", "HDD", "SSD"],
        "tickers": ["MU", "WDC", "STX", "NTAP", "PSTG", "SMCI"],
    },
    {
        "id": 116, "name": "区块链 & 加密", "name_en": "Blockchain & Crypto",
        "icon": "🔗", "is_default": False,
        "keywords": ["blockchain", "crypto", "bitcoin", "ethereum", "DeFi", "Web3"],
        "tickers": ["COIN", "MARA", "RIOT", "MSTR", "CLSK", "HIVE", "BTBT", "HUT", "IREN"],
    },
    {
        "id": 117, "name": "元宇宙 & VR/AR", "name_en": "Metaverse & XR",
        "icon": "🥽", "is_default": False,
        "keywords": ["metaverse", "virtual reality", "augmented reality", "XR", "spatial computing"],
        "tickers": ["META", "AAPL", "MSFT", "RBLX", "NVDA", "SNAP", "QCOM", "MTTR", "KOPN"],
    },
    {
        "id": 118, "name": "大数据 & 分析", "name_en": "Big Data & Analytics",
        "icon": "📊", "is_default": False,
        "keywords": ["big data", "analytics", "data warehouse", "BI", "intelligence"],
        "tickers": ["PLTR", "SNOW", "MDB", "DDOG", "SPLK", "CLDR", "VERI", "TDC", "SPGI", "IT"],
    },

    # ======================== 新能源 ========================
    {
        "id": 120, "name": "光伏太阳能", "name_en": "Solar Energy",
        "icon": "☀️", "is_default": False,
        "keywords": ["solar", "photovoltaic", "PV", "TOPCon", "HJT", "module"],
        "tickers": ["ENPH", "FSLR", "SEDG", "CSIQ", "SPWR", "ARRY", "NOVA", "RUN", "SHLS", "RSVR"],
    },
    {
        "id": 121, "name": "风电", "name_en": "Wind Energy",
        "icon": "💨", "is_default": False,
        "keywords": ["wind energy", "wind turbine", "offshore wind", "onshore wind"],
        "tickers": ["GEV", "BEP", "NEP", "CWEN", "NOVA", "VWSYF", "AY", "BEPC"],
    },
    {
        "id": 122, "name": "储能", "name_en": "Energy Storage",
        "icon": "🔋", "is_default": False,
        "keywords": ["energy storage", "battery storage", "grid storage", "BESS", "lithium"],
        "tickers": ["STEM", "NRGV", "FLUX", "BEEM", "ESS", "POWR", "FREYR", "QS", "SLDP", "ENVX"],
    },
    {
        "id": 123, "name": "EV充电桩", "name_en": "EV Charging",
        "icon": "🔌", "is_default": False,
        "keywords": ["EV charging", "charging station", "EVSE", "charger"],
        "tickers": ["CHPT", "BLNK", "EVGO", "WBX", "AMPX", "NXRT", "VLTA"],
    },
    {
        "id": 124, "name": "锂 & 新能源材料", "name_en": "Lithium & Battery Materials",
        "icon": "⚗️", "is_default": False,
        "keywords": ["lithium", "battery materials", "cathode", "anode", "electrolyte", "sodium battery"],
        "tickers": ["ALB", "SQM", "LAC", "LTHM", "PLL", "ENSG", "SGML", "ALTM"],
    },
    {
        "id": 125, "name": "电网设备 & 特高压", "name_en": "Grid & Power Equipment",
        "icon": "⚡", "is_default": False,
        "keywords": ["power grid", "transmission", "transformer", "ultra-high voltage", "substation"],
        "tickers": ["ETN", "PWR", "MYRG", "MTZ", "EMR", "GEV", "HUBB", "REZI", "AMSC"],
    },
    {
        "id": 126, "name": "清洁能源 & 核电", "name_en": "Clean Energy & Nuclear",
        "icon": "♻️", "is_default": False,
        "keywords": ["clean energy", "nuclear", "SMR", "uranium", "renewable"],
        "tickers": ["CEG", "VST", "NEE", "SO", "DUK", "CCJ", "UEC", "BWXT", "NUE", "LEU"],
    },

    # ======================== 医疗健康 ========================
    {
        "id": 130, "name": "创新药 & GLP-1", "name_en": "Innovative Drugs & GLP-1",
        "icon": "💊", "is_default": False,
        "keywords": ["innovative drug", "GLP-1", "obesity", "diabetes", "weight loss", "semaglutide"],
        "tickers": ["LLY", "NVO", "VKTX", "ZFOX", "AMT", "PFE", "MRK", "ABBV", "REGN", "HIMS", "NWBO"],
    },
    {
        "id": 131, "name": "CRO / CXO", "name_en": "Contract Research & Manufacturing",
        "icon": "🔬", "is_default": False,
        "keywords": ["CRO", "CXO", "contract research", "clinical trial", "CDMO", "outsourcing"],
        "tickers": ["IQV", "MEDP", "ICLR", "SYNH", "PRCT", "NEH", "DOCS", "WK"],
    },
    {
        "id": 132, "name": "医疗器械", "name_en": "Medical Devices",
        "icon": "🩺", "is_default": False,
        "keywords": ["medical device", "surgical robot", "implant", "diagnostic", "imaging"],
        "tickers": ["MDT", "ABT", "BSX", "ISRG", "ZBH", "SYK", "EW", "BDX", "PODD", "DXCM", "INMD"],
    },
    {
        "id": 133, "name": "疫苗 & 生物制品", "name_en": "Vaccines & Biologics",
        "icon": "💉", "is_default": False,
        "keywords": ["vaccine", "biologics", "antibody", "immunotherapy", "mRNA"],
        "tickers": ["MRNA", "BNTX", "PFE", "JNJ", "GSK", "AZN", "NVAX", "VXRT", "SNY"],
    },
    {
        "id": 134, "name": "宠物经济", "name_en": "Pet Economy",
        "icon": "🐾", "is_default": False,
        "keywords": ["pet", "animal health", "veterinary", "pet food"],
        "tickers": ["IDXX", "ZTS", "CHWY", "FRPT", "WOOF", "PETS", "HIMS"],
    },

    # ======================== 金融科技 ========================
    {
        "id": 140, "name": "金融科技 & 支付", "name_en": "Fintech & Payments",
        "icon": "💳", "is_default": False,
        "keywords": ["fintech", "payments", "digital wallet", "neobank", "payment processing"],
        "tickers": ["PYPL", "SQ", "V", "MA", "SOFI", "AFRM", "HOOD", "LC", "UPST", "NU", "MKTX"],
    },
    {
        "id": 141, "name": "银行 & 投行", "name_en": "Banks & Investment Banking",
        "icon": "🏦", "is_default": False,
        "keywords": ["bank", "investment banking", "commercial bank", "financial services"],
        "tickers": ["JPM", "BAC", "WFC", "C", "GS", "MS", "USB", "PNC", "TFC", "KEY", "RF"],
    },
    {
        "id": 142, "name": "保险", "name_en": "Insurance",
        "icon": "🛡️", "is_default": False,
        "keywords": ["insurance", "reinsurance", "property casualty", "life insurance"],
        "tickers": ["BRK.B", "AIG", "MET", "PRU", "AFL", "PGR", "ALL", "TRV", "CB", "AXS", "RNR"],
    },
    {
        "id": 143, "name": "券商 & 资管", "name_en": "Brokers & Asset Management",
        "icon": "📈", "is_default": False,
        "keywords": ["brokerage", "asset management", "wealth management", "fund"],
        "tickers": ["GS", "MS", "SCHW", "IBKR", "RJF", "LPL", "BLK", "APO", "KKR", "BX", "CG"],
    },

    # ======================== 工业制造 ========================
    {
        "id": 150, "name": "航空航天 & 军工", "name_en": "Aerospace & Defense",
        "icon": "✈️", "is_default": False,
        "keywords": ["aerospace", "defense", "missile", "fighter jet", "satellite", "munition"],
        "tickers": ["LMT", "RTX", "NOC", "GD", "BA", "HII", "LDOS", "CACI", "SAIC", "L3H"],
    },
    {
        "id": 151, "name": "工程机械 & 重工", "name_en": "Construction & Heavy Equipment",
        "icon": "🚜", "is_default": False,
        "keywords": ["construction equipment", "heavy machinery", "crane", "excavator"],
        "tickers": ["CAT", "DE", "PCAR", "OSK", "TEX", "WNC", "ALJ", "ACCO"],
    },
    {
        "id": 152, "name": "物流 & 快递", "name_en": "Logistics & Freight",
        "icon": "📦", "is_default": False,
        "keywords": ["logistics", "freight", "shipping", "express", "trucking", "last mile"],
        "tickers": ["UPS", "FDX", "JBHT", "XPO", "CHRW", "ODFL", "SAIA", "GXO", "ATSG", "AAWW"],
    },
    {
        "id": 153, "name": "轨道交通", "name_en": "Rail Transportation",
        "icon": "🚂", "is_default": False,
        "keywords": ["railway", "rail", "freight rail", "passenger rail"],
        "tickers": ["UNP", "CSX", "NSC", "CP", "CN", "WAB", "GBX", "RAIL"],
    },
    {
        "id": 154, "name": "航运 & 港口", "name_en": "Shipping & Ports",
        "icon": "🚢", "is_default": False,
        "keywords": ["shipping", "container", "bulker", "tanker", "port", "maritime"],
        "tickers": ["ZIM", "MATX", "SBLK", "DAC", "GOGL", "GSL", "EGLE", "CPLP", "GNK"],
    },
    {
        "id": 155, "name": "汽车 & 汽车零部件", "name_en": "Auto & Auto Parts",
        "icon": "🚗", "is_default": False,
        "keywords": ["automobile", "auto parts", "vehicle", "drivetrain", "LIDAR"],
        "tickers": ["TSLA", "GM", "F", "APTV", "BWA", "LEA", "GT", "VC", "ALSN", "FOXF", "MOD"],
    },
    {
        "id": 156, "name": "钢铁 & 金属", "name_en": "Steel & Metals",
        "icon": "🔩", "is_default": False,
        "keywords": ["steel", "aluminum", "copper", "metals", "iron ore", "mini mill"],
        "tickers": ["NUE", "STLD", "CLF", "X", "CMC", "SCHN", "ATI", "AA", "CENX", "FCX"],
    },

    # ======================== 资源能源 ========================
    {
        "id": 160, "name": "石油 & 天然气", "name_en": "Oil & Natural Gas",
        "icon": "🛢️", "is_default": False,
        "keywords": ["oil", "natural gas", "E&P", "upstream", "LNG", "shale", "offshore"],
        "tickers": ["XOM", "CVX", "COP", "OXY", "DVN", "EOG", "MRO", "APA", "EQT", "SWN", "RRC"],
    },
    {
        "id": 161, "name": "煤炭", "name_en": "Coal",
        "icon": "⛏️", "is_default": False,
        "keywords": ["coal", "thermal coal", "metallurgical coal", "mining"],
        "tickers": ["BTU", "ARCH", "CEIX", "AMR", "METC", "ARLP", "FANG"],
    },
    {
        "id": 162, "name": "铜 & 稀土金属", "name_en": "Copper & Rare Earth",
        "icon": "🪨", "is_default": False,
        "keywords": ["copper", "rare earth", "lithium", "cobalt", "nickel", "critical minerals"],
        "tickers": ["FCX", "SCCO", "MP", "NB", "LAC", "SQM", "ALB", "LTHM", "NOVV", "HL"],
    },
    {
        "id": 163, "name": "黄金 & 贵金属", "name_en": "Gold & Precious Metals",
        "icon": "🥇", "is_default": False,
        "keywords": ["gold", "silver", "precious metals", "mining", "royalty"],
        "tickers": ["NEM", "GOLD", "AEM", "WPM", "FNV", "PAAS", "HL", "CDE", "MAG", "OR"],
    },
    {
        "id": 164, "name": "化工 & 特种材料", "name_en": "Chemicals & Specialty Materials",
        "icon": "🧪", "is_default": False,
        "keywords": ["chemicals", "specialty materials", "polymers", "petrochemicals", "coatings"],
        "tickers": ["DOW", "LYB", "DD", "PPG", "SHW", "EMN", "RPM", "AXTA", "ECL", "APD", "LIN"],
    },
    {
        "id": 165, "name": "化肥 & 农业化工", "name_en": "Fertilizers & Agri-Chemicals",
        "icon": "🌱", "is_default": False,
        "keywords": ["fertilizer", "nitrogen", "phosphate", "potash", "crop protection"],
        "tickers": ["CF", "MOS", "NTR", "IPI", "CTVA", "FMC", "AMVAC"],
    },

    # ======================== 消费 ========================
    {
        "id": 170, "name": "食品饮料", "name_en": "Food & Beverages",
        "icon": "🍔", "is_default": False,
        "keywords": ["food", "beverage", "snacks", "packaged food", "soft drinks"],
        "tickers": ["PEP", "KO", "MDLZ", "GIS", "CPB", "HSY", "CAG", "SJM", "KHC", "MKC"],
    },
    {
        "id": 171, "name": "酒类", "name_en": "Alcoholic Beverages",
        "icon": "🍷", "is_default": False,
        "keywords": ["beer", "wine", "spirits", "alcoholic beverages", "distillery"],
        "tickers": ["STZ", "BUD", "TAP", "SAM", "BF.B", "MGPI", "CASK", "WEST"],
    },
    {
        "id": 172, "name": "美妆 & 医美", "name_en": "Beauty & Aesthetics",
        "icon": "💄", "is_default": False,
        "keywords": ["beauty", "cosmetics", "skincare", "aesthetics", "medical beauty"],
        "tickers": ["EL", "ULTA", "COTY", "SKIN", "INMD", "SBH", "ESTA", "REVG"],
    },
    {
        "id": 173, "name": "电商 & 新零售", "name_en": "E-Commerce & Retail",
        "icon": "🛒", "is_default": False,
        "keywords": ["e-commerce", "retail", "online shopping", "marketplace", "logistics"],
        "tickers": ["AMZN", "SHOP", "WMT", "TGT", "ETSY", "EBAY", "W", "BABA", "JD", "PDD"],
    },
    {
        "id": 174, "name": "游戏 & 娱乐", "name_en": "Gaming & Entertainment",
        "icon": "🎮", "is_default": False,
        "keywords": ["gaming", "video games", "esports", "entertainment", "streaming"],
        "tickers": ["RBLX", "EA", "TTWO", "MSFT", "SONY", "NFLX", "DIS", "PARA", "WBD", "SEGA"],
    },
    {
        "id": 175, "name": "旅游 & 酒店", "name_en": "Travel & Hotels",
        "icon": "✈️", "is_default": False,
        "keywords": ["travel", "hotel", "aviation", "online booking", "resort", "cruise"],
        "tickers": ["MAR", "HLT", "H", "BKNG", "EXPE", "ABNB", "DAL", "UAL", "AAL", "RCL", "CCL"],
    },
    {
        "id": 176, "name": "教育", "name_en": "Education",
        "icon": "📚", "is_default": False,
        "keywords": ["education", "ed-tech", "online learning", "vocational", "tutoring"],
        "tickers": ["CHGG", "COUR", "DUOL", "LRN", "UTI", "PRDO", "ATGE", "LOPE", "TWOU"],
    },

    # ======================== 房地产 & 基建 ========================
    {
        "id": 180, "name": "房地产 & REITs", "name_en": "Real Estate & REITs",
        "icon": "🏠", "is_default": False,
        "keywords": ["REIT", "real estate", "commercial property", "residential", "data center REIT"],
        "tickers": ["SPG", "O", "PLD", "PSA", "AMT", "EQIX", "CCI", "WELL", "EQR", "AVB", "CBRE"],
    },
    {
        "id": 181, "name": "房屋建造 & 建材", "name_en": "Homebuilders & Building Materials",
        "icon": "🏗️", "is_default": False,
        "keywords": ["homebuilder", "construction", "building materials", "renovation", "housing"],
        "tickers": ["DHI", "LEN", "PHM", "TOL", "NVR", "MLM", "VMC", "TREX", "MAS", "BLD", "SUM"],
    },
    {
        "id": 182, "name": "基建 & 工程建设", "name_en": "Infrastructure & Engineering",
        "icon": "🌉", "is_default": False,
        "keywords": ["infrastructure", "engineering", "construction", "EPC", "civil engineering"],
        "tickers": ["PWR", "MTZ", "MYRG", "FLR", "ACM", "J", "PRIM", "IEA", "DY", "MDU"],
    },
    {
        "id": 183, "name": "水务 & 环保", "name_en": "Water & Environment",
        "icon": "💧", "is_default": False,
        "keywords": ["water", "waste management", "recycling", "environmental", "pollution control"],
        "tickers": ["AWK", "WM", "RSG", "CLH", "ECOV", "HCCI", "PESI", "AWR", "WTRG", "SJW"],
    },

    # ======================== 公用事业 & 电力 ========================
    {
        "id": 190, "name": "电力 & 公用事业", "name_en": "Electric Power & Utilities",
        "icon": "💡", "is_default": False,
        "keywords": ["electric utility", "power generation", "electricity", "grid"],
        "tickers": ["NEE", "SO", "DUK", "D", "AEP", "EXC", "XEL", "ES", "PEG", "WEC", "ETR"],
    },
    {
        "id": 191, "name": "燃气 & 管线", "name_en": "Natural Gas Distribution",
        "icon": "🔥", "is_default": False,
        "keywords": ["natural gas distribution", "gas utility", "pipeline", "LNG"],
        "tickers": ["ATO", "NI", "SWX", "UGI", "NJR", "OGE", "WGL", "CMS", "LNG", "ET", "KINDER"],
    },

    # ======================== 农业 ========================
    {
        "id": 195, "name": "农业 & 粮食", "name_en": "Agriculture & Agribusiness",
        "icon": "🌾", "is_default": False,
        "keywords": ["agriculture", "grain", "crop", "seed", "farming", "agribusiness"],
        "tickers": ["ADM", "BG", "INGR", "VITL", "CTVA", "AGCO", "CNH", "LAND", "FPI", "ANDE"],
    },
    {
        "id": 196, "name": "碳中和 & ESG", "name_en": "Carbon Neutrality & ESG",
        "icon": "🌍", "is_default": False,
        "keywords": ["carbon neutral", "ESG", "sustainability", "net zero", "carbon offset"],
        "tickers": ["CEG", "VST", "NEE", "ENPH", "FSLR", "PLUG", "RUN", "HASI", "BEPC", "BEP"],
    },
]

# ─────────────────────────────────────────────────────────────────────────────

async def main():
    print(f"\n🚀 导入美股概念体系 ({len(US_CONCEPTS_FULL)} 个概念)...")
    async with async_session() as session:
        ok = 0
        for c in US_CONCEPTS_FULL:
            try:
                await session.execute("""
                    -- dummy, will use text() below
                """ if False else "")
                await session.execute(
                    __import__('sqlalchemy').text("""
                        INSERT INTO concepts (id, name, keywords, related_tickers, is_active)
                        VALUES (:id, :name, :kw, :tickers, true)
                        ON CONFLICT (id) DO UPDATE SET
                            name = EXCLUDED.name,
                            keywords = EXCLUDED.keywords,
                            related_tickers = EXCLUDED.related_tickers,
                            is_active = true
                    """),
                    {
                        "id":      c["id"],
                        "name":    c["name"],
                        "kw":      c["keywords"],
                        "tickers": c["tickers"],
                    }
                )
                ok += 1
            except Exception as e:
                print(f"  ❌ {c['name']}: {e}")

        await session.commit()

    print(f"✅ 导入 {ok}/{len(US_CONCEPTS_FULL)} 个概念")
    default_count = sum(1 for c in US_CONCEPTS_FULL if c.get("is_default"))
    print(f"  默认显示: {default_count} 个 (科技类优先)")
    print(f"  扩展显示: {len(US_CONCEPTS_FULL) - default_count} 个")

if __name__ == "__main__":
    asyncio.run(main())
