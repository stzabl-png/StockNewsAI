"""
主题概念配置 — 50 大美股投资主题
对标 A 股概念板块，每个概念含关键词和代表股票
"""

CONCEPTS = [
    # ── AI & 算力 ──────────────────────────────────────────────────────────────
    {
        "id": 1, "name": "AI大模型",
        "keywords": ["large language model", "LLM", "GPT", "Gemini", "Claude", "foundation model", "generative AI"],
        "tickers": ["NVDA", "MSFT", "GOOGL", "META", "AAPL", "AMZN", "ORCL"],
    },
    {
        "id": 2, "name": "算力/数据中心",
        "keywords": ["data center", "GPU cluster", "AI infrastructure", "compute", "hyperscaler", "colocation"],
        "tickers": ["NVDA", "AMD", "SMCI", "VRT", "EQIX", "DLR", "AMT"],
    },
    {
        "id": 3, "name": "AI芯片",
        "keywords": ["AI chip", "neural processing", "NPU", "inference chip", "training chip", "accelerator"],
        "tickers": ["NVDA", "AMD", "INTC", "QCOM", "AVGO", "MRVL", "ARM"],
    },
    {
        "id": 4, "name": "半导体设备",
        "keywords": ["lithography", "etch", "CVD", "wafer", "fab equipment", "EUV", "deposition"],
        "tickers": ["AMAT", "KLAC", "LRCX", "ASML", "TER", "ONTO"],
    },
    {
        "id": 5, "name": "存储芯片",
        "keywords": ["HBM", "DRAM", "NAND", "memory", "flash storage", "high bandwidth memory"],
        "tickers": ["MU", "WDC", "STX", "SNDK"],
    },
    {
        "id": 6, "name": "光模块/CPO",
        "keywords": ["optical transceiver", "co-packaged optics", "CPO", "silicon photonics", "400G", "800G"],
        "tickers": ["CIEN", "LITE", "COHR", "ANET", "II-VI"],
    },
    {
        "id": 7, "name": "云计算/SaaS",
        "keywords": ["cloud computing", "SaaS", "PaaS", "IaaS", "AWS", "Azure", "Google Cloud", "cloud migration"],
        "tickers": ["AMZN", "MSFT", "GOOG", "CRM", "SNOW", "DDOG", "MDB"],
    },
    {
        "id": 8, "name": "网络安全",
        "keywords": ["cybersecurity", "zero trust", "endpoint security", "SASE", "firewall", "threat intelligence"],
        "tickers": ["CRWD", "PANW", "FTNT", "ZS", "S", "OKTA"],
    },
    {
        "id": 9, "name": "量子计算",
        "keywords": ["quantum computing", "qubit", "quantum advantage", "quantum error correction"],
        "tickers": ["IBM", "GOOGL", "MSFT", "IONQ", "RGTI", "QUBT"],
    },
    {
        "id": 10, "name": "机器人/人形",
        "keywords": ["humanoid robot", "robotics", "autonomous robot", "industrial automation", "Boston Dynamics"],
        "tickers": ["TSLA", "GOOGL", "ABB", "ISRG", "NVDA", "FANUC"],
    },
    # ── 新能源 & 清洁能源 ───────────────────────────────────────────────────────
    {
        "id": 11, "name": "新能源汽车",
        "keywords": ["electric vehicle", "EV", "battery electric", "BEV", "PHEV", "EV sales"],
        "tickers": ["TSLA", "RIVN", "LCID", "F", "GM", "NIO", "LI", "XPEV"],
    },
    {
        "id": 12, "name": "自动驾驶",
        "keywords": ["autonomous driving", "self-driving", "FSD", "LiDAR", "ADAS", "robotaxi"],
        "tickers": ["TSLA", "GOOGL", "GM", "MBLAI", "MBLY"],
    },
    {
        "id": 13, "name": "固态/锂电池",
        "keywords": ["solid state battery", "lithium battery", "EV battery", "battery technology", "cell chemistry"],
        "tickers": ["TSLA", "QS", "SLDP", "SES", "F", "GM", "PANASONIC"],
    },
    {
        "id": 14, "name": "光伏太阳能",
        "keywords": ["solar panel", "photovoltaic", "PV module", "solar installation", "rooftop solar", "utility solar"],
        "tickers": ["ENPH", "SEDG", "FSLR", "RUN", "ARRY", "CSIQ"],
    },
    {
        "id": 15, "name": "储能",
        "keywords": ["energy storage", "battery storage", "ESS", "grid storage", "Powerwall", "megapack"],
        "tickers": ["TSLA", "PLUG", "STEM", "NRGV", "FLNC", "BE"],
    },
    {
        "id": 16, "name": "碳中和/ESG",
        "keywords": ["carbon neutral", "net zero", "ESG", "carbon offset", "clean energy transition", "sustainability"],
        "tickers": ["NEE", "BEP", "PLUG", "ORSTED", "ENPH"],
    },
    {
        "id": 17, "name": "核能",
        "keywords": ["nuclear energy", "nuclear power", "SMR", "small modular reactor", "uranium", "fission"],
        "tickers": ["CCJ", "NNE", "LEU", "OKLO", "UEC"],
    },
    # ── 生物医药 & 医疗 ─────────────────────────────────────────────────────────
    {
        "id": 18, "name": "创新药/FDA",
        "keywords": ["FDA approval", "NDA", "BLA", "drug approval", "Phase 3", "clinical trial", "PDUFA"],
        "tickers": ["LLY", "MRNA", "REGN", "BIIB", "GILD", "ABBV", "AMGN", "BMY"],
    },
    {
        "id": 19, "name": "GLP-1/减肥药",
        "keywords": ["GLP-1", "obesity drug", "weight loss drug", "semaglutide", "tirzepatide", "Ozempic", "Wegovy", "Mounjaro"],
        "tickers": ["LLY", "NVO"],
    },
    {
        "id": 20, "name": "CRO/CDMO",
        "keywords": ["contract research", "CRO", "CDMO", "contract manufacturing", "clinical outsourcing"],
        "tickers": ["ICLR", "MEDP", "PRA", "SYNH", "IQVIA", "WCG"],
    },
    {
        "id": 21, "name": "癌症疗法",
        "keywords": ["oncology", "cancer treatment", "CAR-T", "immunotherapy", "ADC", "checkpoint inhibitor"],
        "tickers": ["REGN", "BMY", "MRK", "RARE", "KYMR", "LEGN"],
    },
    {
        "id": 22, "name": "医疗AI/数字健康",
        "keywords": ["digital health", "AI diagnostics", "medical AI", "health tech", "remote monitoring"],
        "tickers": ["ISRG", "VEEV", "TDOC", "NVCR", "PHR"],
    },
    # ── 金融科技 & 区块链 ──────────────────────────────────────────────────────
    {
        "id": 23, "name": "区块链/加密货币",
        "keywords": ["bitcoin", "crypto", "blockchain", "DeFi", "digital asset", "cryptocurrency", "Ethereum"],
        "tickers": ["COIN", "MSTR", "MARA", "RIOT", "HUT"],
    },
    {
        "id": 24, "name": "金融科技/支付",
        "keywords": ["fintech", "digital payment", "payment processing", "buy now pay later", "neobank"],
        "tickers": ["V", "MA", "PYPL", "SQ", "AFRM", "SOFI"],
    },
    # ── 消费 & 零售 ─────────────────────────────────────────────────────────────
    {
        "id": 25, "name": "电商/新零售",
        "keywords": ["e-commerce", "online retail", "marketplace", "same-day delivery", "omnichannel"],
        "tickers": ["AMZN", "SHOP", "WMT", "TGT", "EBAY"],
    },
    {
        "id": 26, "name": "流媒体/游戏",
        "keywords": ["streaming", "gaming", "video game", "esports", "subscription video"],
        "tickers": ["NFLX", "DIS", "EA", "TTWO", "RBLX", "U"],
    },
    {
        "id": 27, "name": "元宇宙/XR",
        "keywords": ["metaverse", "augmented reality", "virtual reality", "AR", "VR", "mixed reality", "spatial computing"],
        "tickers": ["META", "SNAP", "RBLX", "U", "AAPL"],
    },
    # ── 国防 & 航天 ─────────────────────────────────────────────────────────────
    {
        "id": 28, "name": "国防/军工",
        "keywords": ["defense contract", "military", "Pentagon", "DoD", "weapons system", "fighter jet", "missile"],
        "tickers": ["LMT", "RTX", "NOC", "GD", "BA", "L3HARRIS"],
    },
    {
        "id": 29, "name": "卫星互联网/航天",
        "keywords": ["satellite", "Starlink", "LEO", "low earth orbit", "space launch", "rocket"],
        "tickers": ["ASTS", "RKLB", "SPCE", "MAXR", "BKSY"],
    },
    # ── 大宗商品 & 资源 ─────────────────────────────────────────────────────────
    {
        "id": 30, "name": "石油天然气",
        "keywords": ["oil price", "crude oil", "natural gas", "LNG", "upstream", "downstream", "refinery", "OPEC"],
        "tickers": ["XOM", "CVX", "COP", "EOG", "PXD", "SLB"],
    },
    {
        "id": 31, "name": "稀土/有色金属",
        "keywords": ["rare earth", "copper", "lithium", "cobalt", "nickel", "REE", "critical minerals"],
        "tickers": ["MP", "FCX", "ALB", "LAC", "UUUU"],
    },
]

# ─── 快速查找 ──────────────────────────────────────────────────────────────────
CONCEPT_BY_ID = {c["id"]: c for c in CONCEPTS}

def match_concepts_for_news(text: str, ticker: str) -> list[int]:
    """
    根据新闻文本和 ticker，返回匹配的概念 ID 列表
    """
    text_lower = text.lower()
    matched = []
    for c in CONCEPTS:
        # 匹配关键词
        for kw in c["keywords"]:
            if kw.lower() in text_lower:
                matched.append(c["id"])
                break
        else:
            # 或 ticker 在代表股列表中
            if ticker.upper() in c["tickers"]:
                matched.append(c["id"])
    return list(set(matched))
