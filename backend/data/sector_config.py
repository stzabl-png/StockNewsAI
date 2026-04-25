"""
板块分类体系 — 美股 GICS 11 大板块 + 55 细分行业
对标中国 A 股行业体系
"""

# ─── 11 大 GICS 板块 ───────────────────────────────────────────────────────────
SECTORS = [
    {"id": 1,  "name": "信息技术",  "name_en": "Information Technology",  "gics_code": "45", "etf": "XLK"},
    {"id": 2,  "name": "医疗健康",  "name_en": "Health Care",             "gics_code": "35", "etf": "XLV"},
    {"id": 3,  "name": "金融",      "name_en": "Financials",              "gics_code": "40", "etf": "XLF"},
    {"id": 4,  "name": "通信服务",  "name_en": "Communication Services",  "gics_code": "50", "etf": "XLC"},
    {"id": 5,  "name": "可选消费",  "name_en": "Consumer Discretionary",  "gics_code": "25", "etf": "XLY"},
    {"id": 6,  "name": "工业",      "name_en": "Industrials",             "gics_code": "20", "etf": "XLI"},
    {"id": 7,  "name": "必选消费",  "name_en": "Consumer Staples",        "gics_code": "30", "etf": "XLP"},
    {"id": 8,  "name": "能源",      "name_en": "Energy",                  "gics_code": "10", "etf": "XLE"},
    {"id": 9,  "name": "材料",      "name_en": "Materials",               "gics_code": "15", "etf": "XLB"},
    {"id": 10, "name": "公用事业",  "name_en": "Utilities",               "gics_code": "55", "etf": "XLU"},
    {"id": 11, "name": "房地产",    "name_en": "Real Estate",             "gics_code": "60", "etf": "XLRE"},
]

# ─── 55 细分行业 ───────────────────────────────────────────────────────────────
SUB_SECTORS = [
    # 信息技术 (sector_id=1)
    {"id": 101, "sector_id": 1, "name": "半导体",     "name_en": "Semiconductors"},
    {"id": 102, "sector_id": 1, "name": "软件",       "name_en": "Software"},
    {"id": 103, "sector_id": 1, "name": "半导体设备", "name_en": "Semiconductor Equipment"},
    {"id": 104, "sector_id": 1, "name": "IT硬件",     "name_en": "Technology Hardware"},
    {"id": 105, "sector_id": 1, "name": "电子元件",   "name_en": "Electronic Components"},
    # 医疗健康 (sector_id=2)
    {"id": 201, "sector_id": 2, "name": "生物制药",   "name_en": "Biotechnology"},
    {"id": 202, "sector_id": 2, "name": "化学制药",   "name_en": "Pharmaceuticals"},
    {"id": 203, "sector_id": 2, "name": "医疗器械",   "name_en": "Medical Devices"},
    {"id": 204, "sector_id": 2, "name": "医疗服务",   "name_en": "Health Care Services"},
    {"id": 205, "sector_id": 2, "name": "医疗AI",     "name_en": "Digital Health"},
    # 金融 (sector_id=3)
    {"id": 301, "sector_id": 3, "name": "银行",       "name_en": "Banks"},
    {"id": 302, "sector_id": 3, "name": "保险",       "name_en": "Insurance"},
    {"id": 303, "sector_id": 3, "name": "资产管理",   "name_en": "Asset Management"},
    {"id": 304, "sector_id": 3, "name": "券商/投行",  "name_en": "Capital Markets"},
    {"id": 305, "sector_id": 3, "name": "多元金融",   "name_en": "Diversified Financials"},
    # 通信服务 (sector_id=4)
    {"id": 401, "sector_id": 4, "name": "互联网服务", "name_en": "Internet Services"},
    {"id": 402, "sector_id": 4, "name": "媒体/娱乐",  "name_en": "Media & Entertainment"},
    {"id": 403, "sector_id": 4, "name": "通信运营商", "name_en": "Telecom Services"},
    # 可选消费 (sector_id=5)
    {"id": 501, "sector_id": 5, "name": "电商/零售",  "name_en": "E-Commerce & Retail"},
    {"id": 502, "sector_id": 5, "name": "汽车整车",   "name_en": "Automobiles"},
    {"id": 503, "sector_id": 5, "name": "餐饮/休闲",  "name_en": "Hotels, Restaurants & Leisure"},
    {"id": 504, "sector_id": 5, "name": "家居建材",   "name_en": "Home Improvement"},
    {"id": 505, "sector_id": 5, "name": "奢侈品/服饰","name_en": "Textiles & Apparel"},
    # 工业 (sector_id=6)
    {"id": 601, "sector_id": 6, "name": "航空航天/国防","name_en": "Aerospace & Defense"},
    {"id": 602, "sector_id": 6, "name": "工程机械",   "name_en": "Industrial Machinery"},
    {"id": 603, "sector_id": 6, "name": "航空/运输",  "name_en": "Airlines & Transportation"},
    {"id": 604, "sector_id": 6, "name": "物流",       "name_en": "Logistics"},
    {"id": 605, "sector_id": 6, "name": "工程服务",   "name_en": "Engineering Services"},
    # 必选消费 (sector_id=7)
    {"id": 701, "sector_id": 7, "name": "食品饮料",   "name_en": "Food & Beverages"},
    {"id": 702, "sector_id": 7, "name": "日化/个护",  "name_en": "Personal Care"},
    {"id": 703, "sector_id": 7, "name": "零售超市",   "name_en": "Food & Drug Retailing"},
    {"id": 704, "sector_id": 7, "name": "烟草",       "name_en": "Tobacco"},
    # 能源 (sector_id=8)
    {"id": 801, "sector_id": 8, "name": "石油天然气", "name_en": "Oil & Gas"},
    {"id": 802, "sector_id": 8, "name": "能源设备服务","name_en": "Energy Equipment & Services"},
    {"id": 803, "sector_id": 8, "name": "新能源",     "name_en": "Renewable Energy"},
    # 材料 (sector_id=9)
    {"id": 901, "sector_id": 9, "name": "化工",       "name_en": "Chemicals"},
    {"id": 902, "sector_id": 9, "name": "金属矿业",   "name_en": "Metals & Mining"},
    {"id": 903, "sector_id": 9, "name": "包装材料",   "name_en": "Containers & Packaging"},
    {"id": 904, "sector_id": 9, "name": "建材",       "name_en": "Construction Materials"},
    # 公用事业 (sector_id=10)
    {"id": 1001, "sector_id": 10, "name": "电力",     "name_en": "Electric Utilities"},
    {"id": 1002, "sector_id": 10, "name": "天然气",   "name_en": "Gas Utilities"},
    {"id": 1003, "sector_id": 10, "name": "水务",     "name_en": "Water Utilities"},
    # 房地产 (sector_id=11)
    {"id": 1101, "sector_id": 11, "name": "工业REIT", "name_en": "Industrial REITs"},
    {"id": 1102, "sector_id": 11, "name": "通信REIT", "name_en": "Specialized REITs"},
    {"id": 1103, "sector_id": 11, "name": "住宅REIT", "name_en": "Residential REITs"},
    {"id": 1104, "sector_id": 11, "name": "商业REIT", "name_en": "Retail REITs"},
    {"id": 1105, "sector_id": 11, "name": "医疗REIT", "name_en": "Health Care REITs"},
]

# ─── 快速查找辅助 ──────────────────────────────────────────────────────────────
SECTOR_BY_ID   = {s["id"]: s for s in SECTORS}
SECTOR_BY_NAME = {s["name_en"]: s for s in SECTORS}
SUB_SECTOR_BY_ID = {s["id"]: s for s in SUB_SECTORS}
