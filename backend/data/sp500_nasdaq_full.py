"""
S&P 500 + NASDAQ 100 完整股票数据
约 530 家公司，含 GICS 分类、细分行业、主题概念标签
"""

# 概念ID映射（对应 concepts 表）
CONCEPT_IDS = {
    "AI":         1,   # AI & 大模型
    "CLOUD":      2,   # 云计算
    "SEMI":       3,   # 半导体
    "EV":         4,   # 电动车
    "BIOTECH":    5,   # 生物科技
    "CYBER":      6,   # 网络安全
    "ROBOT":      7,   # 机器人
    "SPACE":      8,   # 商业航天
    "GLP1":       9,   # GLP-1 减肥药
    "GENE":       10,  # 基因编辑
    "FINTECH":    11,  # 数字支付
    "QUANTUM":    12,  # 量子计算
    "AUTO":       13,  # 自动驾驶
    "AR_VR":      14,  # AR/VR
    "CLEAN":      15,  # 清洁能源
    "DEFENSE":    16,  # 航空国防
    "PHARMA":     17,  # 制药
    "REIT":       18,  # 房地产REITs
    "BANK":       19,  # 银行
    "MEDIA":      20,  # 流媒体娱乐
}

# ------------------------------------------------------------------
# 格式: (ticker, 公司名, GICS大板块, GICS细分行业, 市值_亿$, [概念标签])
# ------------------------------------------------------------------
SP500_NASDAQ = [

    # ================================================================
    # 信息技术 Information Technology
    # ================================================================

    # —— 半导体 Semiconductors ——
    ("NVDA",  "NVIDIA Corporation",               "Information Technology", "Semiconductors",     33000, ["AI","SEMI","AUTO","ROBOT"]),
    ("AVGO",  "Broadcom Inc.",                     "Information Technology", "Semiconductors",      8000, ["SEMI","AI","CLOUD"]),
    ("AMD",   "Advanced Micro Devices",            "Information Technology", "Semiconductors",      2500, ["SEMI","AI","CLOUD"]),
    ("QCOM",  "Qualcomm Inc.",                     "Information Technology", "Semiconductors",      1700, ["SEMI","AUTO"]),
    ("TXN",   "Texas Instruments",                 "Information Technology", "Semiconductors",      1700, ["SEMI"]),
    ("INTC",  "Intel Corporation",                 "Information Technology", "Semiconductors",       900, ["SEMI","AI"]),
    ("AMAT",  "Applied Materials",                 "Information Technology", "Semiconductor Equip",  1700, ["SEMI"]),
    ("LRCX",  "Lam Research",                      "Information Technology", "Semiconductor Equip",  1000, ["SEMI"]),
    ("KLAC",  "KLA Corporation",                   "Information Technology", "Semiconductor Equip",   900, ["SEMI"]),
    ("ADI",   "Analog Devices",                    "Information Technology", "Semiconductors",        900, ["SEMI"]),
    ("MCHP",  "Microchip Technology",              "Information Technology", "Semiconductors",        400, ["SEMI"]),
    ("ON",    "ON Semiconductor",                  "Information Technology", "Semiconductors",        300, ["SEMI","EV"]),
    ("MPWR",  "Monolithic Power Systems",          "Information Technology", "Semiconductors",        300, ["SEMI"]),
    ("MU",    "Micron Technology",                 "Information Technology", "Semiconductors",       1100, ["SEMI","AI"]),
    ("WDC",   "Western Digital",                   "Information Technology", "Semiconductors",        200, ["SEMI"]),
    ("STX",   "Seagate Technology",                "Information Technology", "Technology Hardware",   200, ["SEMI"]),
    ("SWKS",  "Skyworks Solutions",                "Information Technology", "Semiconductors",        150, ["SEMI"]),
    ("QRVO",  "Qorvo Inc.",                        "Information Technology", "Semiconductors",         80, ["SEMI"]),
    ("TER",   "Teradyne Inc.",                     "Information Technology", "Semiconductor Equip",   200, ["SEMI","ROBOT"]),
    ("ENTG",  "Entegris Inc.",                     "Information Technology", "Semiconductor Equip",   150, ["SEMI"]),
    ("WOLF",  "Wolfspeed",                         "Information Technology", "Semiconductors",         30, ["SEMI","EV"]),

    # —— 系统软件 Systems Software ——
    ("MSFT",  "Microsoft Corporation",             "Information Technology", "Systems Software",     31000, ["AI","CLOUD","CYBER","AR_VR","QUANTUM"]),
    ("ORCL",  "Oracle Corporation",                "Information Technology", "Systems Software",      4700, ["CLOUD","AI"]),
    ("IBM",   "IBM Corporation",                   "Information Technology", "IT Services",           1900, ["CLOUD","AI","QUANTUM"]),
    ("NOW",   "ServiceNow",                        "Information Technology", "Systems Software",      2000, ["CLOUD","AI"]),
    ("PANW",  "Palo Alto Networks",                "Information Technology", "Systems Software",      1200, ["CYBER","AI"]),
    ("FTNT",  "Fortinet Inc.",                     "Information Technology", "Systems Software",       500, ["CYBER"]),
    ("SNPS",  "Synopsys",                          "Information Technology", "Application Software",  1000, ["SEMI","AI"]),
    ("CDNS",  "Cadence Design Systems",            "Information Technology", "Application Software",   800, ["SEMI","AI"]),
    ("ANSS",  "Ansys Inc.",                        "Information Technology", "Application Software",   300, ["AI"]),
    ("ADSK",  "Autodesk",                          "Information Technology", "Application Software",   600, ["AI","ROBOT"]),

    # —— 应用软件 Application Software ——
    ("ADBE",  "Adobe Inc.",                        "Information Technology", "Application Software",  1900, ["AI","CLOUD"]),
    ("INTU",  "Intuit Inc.",                       "Information Technology", "Application Software",  1900, ["AI","CLOUD","FINTECH"]),
    ("CRM",   "Salesforce",                        "Information Technology", "Application Software",  2500, ["CLOUD","AI"]),
    ("WDAY",  "Workday",                           "Information Technology", "Application Software",   600, ["CLOUD"]),
    ("TEAM",  "Atlassian Corporation",             "Information Technology", "Application Software",   500, ["CLOUD"]),
    ("PAYC",  "Paycom Software",                   "Information Technology", "Application Software",   180, ["CLOUD"]),
    ("GWRE",  "Guidewire Software",                "Information Technology", "Application Software",   150, ["CLOUD"]),
    ("MANH",  "Manhattan Associates",              "Information Technology", "Application Software",   200, ["CLOUD"]),
    ("SMAR",  "Smartsheet",                        "Information Technology", "Application Software",    80, ["CLOUD"]),
    ("DDOG",  "Datadog Inc.",                      "Information Technology", "Application Software",   400, ["CLOUD","AI"]),
    ("SNOW",  "Snowflake Inc.",                    "Information Technology", "Application Software",   500, ["CLOUD","AI"]),
    ("ZS",    "Zscaler Inc.",                      "Information Technology", "Application Software",   300, ["CYBER","CLOUD"]),
    ("OKTA",  "Okta Inc.",                         "Information Technology", "Application Software",   200, ["CYBER","CLOUD"]),
    ("CRWD",  "CrowdStrike Holdings",              "Information Technology", "Application Software",   900, ["CYBER","AI"]),
    ("NET",   "Cloudflare Inc.",                   "Information Technology", "Application Software",   450, ["CYBER","CLOUD"]),
    ("BILL",  "Bill.com Holdings",                 "Information Technology", "Application Software",    80, ["FINTECH","CLOUD"]),
    ("GRAB",  "Grab Holdings",                     "Information Technology", "Application Software",    20, ["FINTECH"]),

    # —— IT 服务 IT Services ——
    ("ACN",   "Accenture",                         "Information Technology", "IT Services",           2200, ["AI","CLOUD"]),
    ("CTSH",  "Cognizant Technology",              "Information Technology", "IT Services",            400, ["AI","CLOUD"]),
    ("IT",    "Gartner Inc.",                      "Information Technology", "IT Services",            400, []),
    ("EPAM",  "EPAM Systems",                      "Information Technology", "IT Services",            130, []),
    ("WEX",   "WEX Inc.",                          "Information Technology", "IT Services",            100, ["FINTECH"]),

    # —— 硬件 Technology Hardware ——
    ("AAPL",  "Apple Inc.",                        "Information Technology", "Technology Hardware",   31000, ["AI","AR_VR","AUTO"]),
    ("DELL",  "Dell Technologies",                 "Information Technology", "Technology Hardware",    750, ["AI","CLOUD"]),
    ("HPE",   "Hewlett Packard Enterprise",        "Information Technology", "Technology Hardware",    250, ["CLOUD","AI"]),
    ("HPQ",   "HP Inc.",                           "Information Technology", "Technology Hardware",    380, []),
    ("NTAP",  "NetApp Inc.",                       "Information Technology", "Technology Hardware",    200, ["CLOUD"]),
    ("PSTG",  "Pure Storage",                      "Information Technology", "Technology Hardware",    150, ["CLOUD","AI"]),
    ("ZBRA",  "Zebra Technologies",                "Information Technology", "Technology Hardware",    170, []),
    ("TTWO",  "Take-Two Interactive",              "Information Technology", "Entertainment Software",  260, []),
    ("EA",    "Electronic Arts",                   "Information Technology", "Entertainment Software",  280, ["AI"]),
    ("RBLX",  "Roblox Corporation",               "Information Technology", "Entertainment Software",  300, ["AR_VR"]),

    # ================================================================
    # 医疗健康 Health Care
    # ================================================================

    # —— 生物科技 Biotechnology ——
    ("AMGN",  "Amgen Inc.",                        "Health Care", "Biotechnology",   1700, ["BIOTECH","PHARMA"]),
    ("GILD",  "Gilead Sciences",                   "Health Care", "Biotechnology",    900, ["BIOTECH","PHARMA"]),
    ("BIIB",  "Biogen Inc.",                       "Health Care", "Biotechnology",    360, ["BIOTECH","PHARMA"]),
    ("REGN",  "Regeneron Pharmaceuticals",         "Health Care", "Biotechnology",    850, ["BIOTECH","PHARMA"]),
    ("VRTX",  "Vertex Pharmaceuticals",            "Health Care", "Biotechnology",    760, ["BIOTECH","GENE"]),
    ("MRNA",  "Moderna Inc.",                      "Health Care", "Biotechnology",    150, ["BIOTECH","PHARMA"]),
    ("ILMN",  "Illumina Inc.",                     "Health Care", "Biotechnology",    150, ["GENE","BIOTECH"]),
    ("EXAS",  "Exact Sciences",                    "Health Care", "Biotechnology",     80, ["BIOTECH"]),
    ("BEAM",  "Beam Therapeutics",                 "Health Care", "Biotechnology",     20, ["GENE","BIOTECH"]),
    ("CRSP",  "CRISPR Therapeutics",              "Health Care", "Biotechnology",     30, ["GENE","BIOTECH"]),
    ("NTLA",  "Intellia Therapeutics",             "Health Care", "Biotechnology",     25, ["GENE","BIOTECH"]),

    # —— 制药 Pharmaceuticals ——
    ("LLY",   "Eli Lilly and Company",            "Health Care", "Pharmaceuticals",   8000, ["PHARMA","GLP1","BIOTECH"]),
    ("JNJ",   "Johnson & Johnson",                "Health Care", "Pharmaceuticals",   3900, ["PHARMA"]),
    ("MRK",   "Merck & Co.",                      "Health Care", "Pharmaceuticals",   2600, ["PHARMA","BIOTECH"]),
    ("PFE",   "Pfizer Inc.",                      "Health Care", "Pharmaceuticals",   1600, ["PHARMA","GLP1"]),
    ("ABBV",  "AbbVie Inc.",                      "Health Care", "Pharmaceuticals",   3100, ["PHARMA"]),
    ("BMY",   "Bristol-Myers Squibb",             "Health Care", "Pharmaceuticals",   1280, ["PHARMA","BIOTECH"]),
    ("NVO",   "Novo Nordisk",                     "Health Care", "Pharmaceuticals",   4500, ["PHARMA","GLP1"]),
    ("GSK",   "GSK plc",                          "Health Care", "Pharmaceuticals",    700, ["PHARMA"]),
    ("AZN",   "AstraZeneca",                      "Health Care", "Pharmaceuticals",   2500, ["PHARMA","BIOTECH"]),
    ("RPRX",  "Royalty Pharma",                   "Health Care", "Pharmaceuticals",    160, ["PHARMA"]),

    # —— 医疗设备 Medical Equipment ——
    ("MDT",   "Medtronic",                        "Health Care", "Medical Devices",    1100, ["ROBOT"]),
    ("ABT",   "Abbott Laboratories",              "Health Care", "Medical Devices",    2200, []),
    ("BSX",   "Boston Scientific",                "Health Care", "Medical Devices",     900, ["ROBOT"]),
    ("ISRG",  "Intuitive Surgical",               "Health Care", "Medical Devices",    1900, ["ROBOT","AI"]),
    ("ZBH",   "Zimmer Biomet",                    "Health Care", "Medical Devices",     180, []),
    ("EW",    "Edwards Lifesciences",             "Health Care", "Medical Devices",     350, []),
    ("BDX",   "Becton Dickinson",                 "Health Care", "Medical Devices",     600, []),
    ("SYK",   "Stryker Corporation",              "Health Care", "Medical Devices",    1200, ["ROBOT"]),
    ("BAX",   "Baxter International",             "Health Care", "Medical Devices",     115, []),
    ("DXCM",  "DexCom Inc.",                      "Health Care", "Medical Devices",     260, []),

    # —— 管理医疗 Managed Health Care ——
    ("UNH",   "UnitedHealth Group",               "Health Care", "Managed Health Care", 4500, ["AI"]),
    ("CVS",   "CVS Health",                       "Health Care", "Managed Health Care",  700, []),
    ("CI",    "Cigna Group",                      "Health Care", "Managed Health Care",  950, []),
    ("HUM",   "Humana Inc.",                      "Health Care", "Managed Health Care",  280, []),
    ("CNC",   "Centene Corporation",              "Health Care", "Managed Health Care",  250, []),
    ("ELV",   "Elevance Health",                  "Health Care", "Managed Health Care",  950, []),
    ("MOH",   "Molina Healthcare",               "Health Care", "Managed Health Care",  170, []),

    # —— 生命科学工具 Life Sciences ——
    ("TMO",   "Thermo Fisher Scientific",         "Health Care", "Life Sciences Tools",  2300, ["GENE","AI"]),
    ("DHR",   "Danaher Corporation",              "Health Care", "Life Sciences Tools",  1800, []),
    ("A",     "Agilent Technologies",             "Health Care", "Life Sciences Tools",   280, []),
    ("IQV",   "IQVIA Holdings",                   "Health Care", "Life Sciences Tools",   400, ["AI"]),
    ("MEDP",  "Medpace Holdings",                 "Health Care", "Life Sciences Tools",   120, []),
    ("QGEN",  "Qiagen",                           "Health Care", "Life Sciences Tools",    80, ["GENE"]),

    # ================================================================
    # 金融 Financials
    # ================================================================

    # —— 银行 Banks ——
    ("JPM",   "JPMorgan Chase",                   "Financials", "Diversified Banks",   7000, ["AI","FINTECH","BANK"]),
    ("BAC",   "Bank of America",                  "Financials", "Diversified Banks",   3500, ["AI","BANK"]),
    ("WFC",   "Wells Fargo",                      "Financials", "Diversified Banks",   2600, ["BANK"]),
    ("C",     "Citigroup",                        "Financials", "Diversified Banks",   1400, ["BANK"]),
    ("USB",   "U.S. Bancorp",                     "Financials", "Regional Banks",       600, ["BANK"]),
    ("TFC",   "Truist Financial",                 "Financials", "Regional Banks",       500, ["BANK"]),
    ("KEY",   "KeyCorp",                          "Financials", "Regional Banks",       170, ["BANK"]),
    ("FITB",  "Fifth Third Bancorp",              "Financials", "Regional Banks",       240, ["BANK"]),
    ("RF",    "Regions Financial",                "Financials", "Regional Banks",       190, ["BANK"]),
    ("HBAN",  "Huntington Bancshares",            "Financials", "Regional Banks",       210, ["BANK"]),
    ("MTB",   "M&T Bank Corporation",             "Financials", "Regional Banks",       260, ["BANK"]),
    ("CFG",   "Citizens Financial Group",         "Financials", "Regional Banks",       190, ["BANK"]),
    ("ZION",  "Zions Bancorporation",             "Financials", "Regional Banks",        90, ["BANK"]),
    ("CMA",   "Comerica Inc.",                    "Financials", "Regional Banks",        85, ["BANK"]),

    # —— 投资银行 Investment Banking ——
    ("GS",    "Goldman Sachs",                    "Financials", "Investment Banking",   1900, ["AI","FINTECH"]),
    ("MS",    "Morgan Stanley",                   "Financials", "Investment Banking",   2000, ["AI","FINTECH"]),
    ("BLK",   "BlackRock",                        "Financials", "Asset Management",     1400, ["AI","FINTECH"]),
    ("SCHW",  "Charles Schwab",                   "Financials", "Investment Banking",    900, ["FINTECH"]),
    ("AMP",   "Ameriprise Financial",             "Financials", "Asset Management",      500, []),
    ("TROW",  "T. Rowe Price",                    "Financials", "Asset Management",      240, []),
    ("RJF",   "Raymond James Financial",          "Financials", "Investment Banking",    200, []),
    ("IVZ",   "Invesco",                          "Financials", "Asset Management",       80, []),

    # —— 支付 Payment ——
    ("V",     "Visa Inc.",                        "Financials", "Transaction Processing", 6000, ["FINTECH","AI"]),
    ("MA",    "Mastercard",                       "Financials", "Transaction Processing", 5000, ["FINTECH","AI"]),
    ("AXP",   "American Express",                 "Financials", "Consumer Finance",       2200, ["FINTECH"]),
    ("DFS",   "Discover Financial Services",      "Financials", "Consumer Finance",        400, ["FINTECH"]),
    ("COF",   "Capital One Financial",            "Financials", "Consumer Finance",        600, ["AI","FINTECH"]),
    ("FIS",   "Fidelity National Info Svcs",      "Financials", "Transaction Processing",  400, ["FINTECH"]),
    ("FISV",  "Fiserv Inc.",                      "Financials", "Transaction Processing",  900, ["FINTECH"]),
    ("GPN",   "Global Payments",                  "Financials", "Transaction Processing",  200, ["FINTECH"]),
    ("PYPL",  "PayPal Holdings",                  "Financials", "Transaction Processing",  800, ["FINTECH","AI"]),
    ("SQ",    "Block Inc.",                       "Financials", "Transaction Processing",  500, ["FINTECH"]),
    ("AFRM",  "Affirm Holdings",                  "Financials", "Consumer Finance",         55, ["FINTECH"]),

    # —— 保险 Insurance ——
    ("BRK.B", "Berkshire Hathaway",               "Financials", "Multi-line Insurance",  10000, []),
    ("MET",   "MetLife",                          "Financials", "Life Insurance",          600, []),
    ("PRU",   "Prudential Financial",             "Financials", "Life Insurance",          500, []),
    ("AFL",   "Aflac",                            "Financials", "Life Insurance",          500, []),
    ("AIG",   "American International Group",     "Financials", "Multi-line Insurance",    500, []),
    ("ALL",   "Allstate Corporation",             "Financials", "P&C Insurance",           650, []),
    ("CB",    "Chubb Limited",                    "Financials", "P&C Insurance",          1200, []),
    ("TRV",   "Travelers Companies",              "Financials", "P&C Insurance",           500, []),
    ("PGR",   "Progressive Corporation",          "Financials", "P&C Insurance",          1550, []),
    ("HIG",   "Hartford Financial Services",      "Financials", "P&C Insurance",           290, []),

    # ================================================================
    # 通信服务 Communication Services
    # ================================================================
    ("META",  "Meta Platforms",                   "Communication Services", "Interactive Media",  16000, ["AI","CLOUD","AR_VR","MEDIA"]),
    ("GOOGL", "Alphabet Inc. (Google)",           "Communication Services", "Interactive Media",  20000, ["AI","CLOUD","AUTO","QUANTUM","MEDIA"]),
    ("GOOG",  "Alphabet Inc. Class C",            "Communication Services", "Interactive Media",  20000, ["AI","CLOUD","MEDIA"]),
    ("NFLX",  "Netflix Inc.",                     "Communication Services", "Movies & Entertainment", 4800, ["AI","MEDIA"]),
    ("DIS",   "Walt Disney Company",              "Communication Services", "Movies & Entertainment", 2200, ["AR_VR","MEDIA"]),
    ("SNAP",  "Snap Inc.",                        "Communication Services", "Interactive Media",    200, ["AR_VR"]),
    ("PINS",  "Pinterest Inc.",                   "Communication Services", "Interactive Media",    170, ["AI"]),
    ("SPOT",  "Spotify Technology",               "Communication Services", "Interactive Media",    900, ["AI"]),
    ("MTCH",  "Match Group",                      "Communication Services", "Interactive Media",     90, []),
    ("WBD",   "Warner Bros. Discovery",           "Communication Services", "Movies & Entertainment", 250, ["MEDIA"]),
    ("PARA",  "Paramount Global",                 "Communication Services", "Movies & Entertainment",  65, ["MEDIA"]),
    ("FOXA",  "Fox Corporation",                  "Communication Services", "Publishing",           230, []),
    ("OMC",   "Omnicom Group",                    "Communication Services", "Publishing",           200, []),
    ("IPG",   "Interpublic Group",                "Communication Services", "Publishing",           130, []),
    ("TTD",   "The Trade Desk",                   "Communication Services", "Interactive Media",    560, ["AI"]),
    ("T",     "AT&T Inc.",                        "Communication Services", "Integrated Telecom",  1700, []),
    ("VZ",    "Verizon Communications",           "Communication Services", "Integrated Telecom",  1800, []),
    ("TMUS",  "T-Mobile US",                      "Communication Services", "Wireless Telecom",    2900, []),
    ("CHTR",  "Charter Communications",           "Communication Services", "Integrated Telecom",   330, []),
    ("CMCSA", "Comcast Corporation",              "Communication Services", "Integrated Telecom",  1500, ["MEDIA"]),
    ("ASTS",  "AST SpaceMobile",                  "Communication Services", "Wireless Telecom",     120, ["SPACE"]),

    # ================================================================
    # 可选消费 Consumer Discretionary
    # ================================================================
    ("AMZN",  "Amazon.com Inc.",                  "Consumer Discretionary", "Internet Retail",    23000, ["AI","CLOUD","ROBOT","AUTO"]),
    ("TSLA",  "Tesla Inc.",                       "Consumer Discretionary", "Automobile Manufacturers", 10000, ["EV","AI","AUTO","SPACE","ROBOT"]),
    ("HD",    "Home Depot",                       "Consumer Discretionary", "Specialty Retail",    3800, []),
    ("MCD",   "McDonald's Corporation",           "Consumer Discretionary", "Restaurants",         2300, ["AI"]),
    ("LOW",   "Lowe's Companies",                 "Consumer Discretionary", "Specialty Retail",    1700, []),
    ("NKE",   "Nike Inc.",                        "Consumer Discretionary", "Apparel",             1100, []),
    ("SBUX",  "Starbucks Corporation",            "Consumer Discretionary", "Restaurants",         1000, ["AI"]),
    ("TJX",   "TJX Companies",                   "Consumer Discretionary", "Specialty Retail",    1600, []),
    ("ROST",  "Ross Stores",                      "Consumer Discretionary", "Specialty Retail",     500, []),
    ("GM",    "General Motors",                   "Consumer Discretionary", "Automobile Manufacturers", 500, ["EV","AUTO"]),
    ("F",     "Ford Motor Company",               "Consumer Discretionary", "Automobile Manufacturers", 600, ["EV","AUTO"]),
    ("CMG",   "Chipotle Mexican Grill",           "Consumer Discretionary", "Restaurants",         1100, []),
    ("YUM",   "Yum! Brands",                      "Consumer Discretionary", "Restaurants",          350, []),
    ("DRI",   "Darden Restaurants",              "Consumer Discretionary", "Restaurants",           200, []),
    ("MAR",   "Marriott International",           "Consumer Discretionary", "Hotels & Resorts",     800, []),
    ("HLT",   "Hilton Worldwide",                 "Consumer Discretionary", "Hotels & Resorts",     560, []),
    ("RCL",   "Royal Caribbean Group",            "Consumer Discretionary", "Hotels & Resorts",     600, []),
    ("CCL",   "Carnival Corporation",             "Consumer Discretionary", "Hotels & Resorts",     250, []),
    ("WYNN",  "Wynn Resorts",                     "Consumer Discretionary", "Hotels & Resorts",     120, []),
    ("MGM",   "MGM Resorts International",        "Consumer Discretionary", "Hotels & Resorts",     140, []),
    ("LVS",   "Las Vegas Sands",                  "Consumer Discretionary", "Hotels & Resorts",     280, []),
    ("LULU",  "Lululemon Athletica",              "Consumer Discretionary", "Apparel",              450, []),
    ("RIVN",  "Rivian Automotive",                "Consumer Discretionary", "Automobile Manufacturers", 160, ["EV"]),
    ("APTV",  "Aptiv PLC",                        "Consumer Discretionary", "Auto Components",      130, ["EV","AUTO"]),
    ("SHOP",  "Shopify Inc.",                     "Consumer Discretionary", "Internet Retail",     1500, ["AI","FINTECH"]),
    ("BKNG",  "Booking Holdings",                 "Consumer Discretionary", "Hotels & Resorts",    1700, ["AI"]),
    ("EXPE",  "Expedia Group",                    "Consumer Discretionary", "Hotels & Resorts",     230, []),
    ("UBER",  "Uber Technologies",                "Consumer Discretionary", "Ground Transportation", 1900, ["AUTO","AI","ROBOT"]),
    ("LYFT",  "Lyft Inc.",                        "Consumer Discretionary", "Ground Transportation",  80, ["AUTO"]),
    ("ABNB",  "Airbnb Inc.",                      "Consumer Discretionary", "Hotels & Resorts",     900, ["AI"]),

    # ================================================================
    # 必选消费 Consumer Staples
    # ================================================================
    ("WMT",   "Walmart Inc.",                     "Consumer Staples", "Hypermarkets",        7500, ["AI","ROBOT"]),
    ("COST",  "Costco Wholesale",                 "Consumer Staples", "Hypermarkets",        4400, []),
    ("PG",    "Procter & Gamble",                 "Consumer Staples", "Personal Products",   4100, []),
    ("KO",    "Coca-Cola Company",                "Consumer Staples", "Beverages",           3200, []),
    ("PEP",   "PepsiCo Inc.",                     "Consumer Staples", "Beverages",           2600, []),
    ("PM",    "Philip Morris International",      "Consumer Staples", "Tobacco",             1800, []),
    ("MO",    "Altria Group",                     "Consumer Staples", "Tobacco",              900, []),
    ("MDLZ",  "Mondelez International",           "Consumer Staples", "Food Products",       900, []),
    ("STZ",   "Constellation Brands",             "Consumer Staples", "Beverages",           500, []),
    ("CL",    "Colgate-Palmolive",                "Consumer Staples", "Personal Products",   700, []),
    ("GIS",   "General Mills",                    "Consumer Staples", "Food Products",       380, []),
    ("SYY",   "Sysco Corporation",                "Consumer Staples", "Food Distribution",   400, []),
    ("KR",    "Kroger Co.",                       "Consumer Staples", "Food Retail",         450, []),
    ("HRL",   "Hormel Foods",                     "Consumer Staples", "Food Products",       130, []),
    ("KHC",   "Kraft Heinz",                      "Consumer Staples", "Food Products",       300, []),
    ("MNST",  "Monster Beverage",                 "Consumer Staples", "Beverages",           600, []),
    ("CLX",   "Clorox Company",                   "Consumer Staples", "Personal Products",   120, []),
    ("CHD",   "Church & Dwight",                  "Consumer Staples", "Personal Products",   200, []),

    # ================================================================
    # 工业 Industrials
    # ================================================================

    # —— 航空航天与国防 Aerospace & Defense ——
    ("LMT",   "Lockheed Martin",                  "Industrials", "Aerospace & Defense",    1500, ["DEFENSE","SPACE"]),
    ("RTX",   "RTX Corporation",                  "Industrials", "Aerospace & Defense",    1800, ["DEFENSE","CYBER"]),
    ("NOC",   "Northrop Grumman",                 "Industrials", "Aerospace & Defense",     700, ["DEFENSE","SPACE"]),
    ("GD",    "General Dynamics",                  "Industrials", "Aerospace & Defense",     750, ["DEFENSE"]),
    ("BA",    "Boeing Company",                   "Industrials", "Aerospace & Defense",    1300, ["DEFENSE","AUTO"]),
    ("HII",   "Huntington Ingalls Industries",    "Industrials", "Aerospace & Defense",     120, ["DEFENSE"]),
    ("TDG",   "TransDigm Group",                  "Industrials", "Aerospace & Defense",     550, ["DEFENSE"]),
    ("HEICO", "HEICO Corporation",                "Industrials", "Aerospace & Defense",     270, ["DEFENSE"]),
    ("LDOS",  "Leidos Holdings",                  "Industrials", "Aerospace & Defense",     230, ["DEFENSE","AI"]),
    ("SAIC",  "Science & Applications Corp",      "Industrials", "Aerospace & Defense",     130, ["DEFENSE"]),
    ("KTOS",  "Kratos Defense & Security",        "Industrials", "Aerospace & Defense",      45, ["DEFENSE","SPACE"]),
    ("RKLB",  "Rocket Lab USA",                   "Industrials", "Aerospace & Defense",      90, ["SPACE"]),
    ("JOBY",  "Joby Aviation",                    "Industrials", "Aerospace & Defense",      50, ["AUTO","SPACE"]),

    # —— 工业集团 Industrials ——
    ("GE",    "GE Aerospace",                     "Industrials", "Aerospace & Defense",    2700, ["ROBOT","AI"]),
    ("HON",   "Honeywell International",          "Industrials", "Industrial Conglomerates", 1500, ["AI","ROBOT"]),
    ("MMM",   "3M Company",                       "Industrials", "Industrial Conglomerates",  500, []),
    ("ETN",   "Eaton Corporation",                "Industrials", "Electrical Equipment",      1400, ["EV","CLEAN"]),
    ("EMR",   "Emerson Electric",                 "Industrials", "Industrial Machinery",       750, ["ROBOT","AI"]),
    ("ROK",   "Rockwell Automation",              "Industrials", "Industrial Machinery",       300, ["ROBOT","AI"]),
    ("AME",   "AMETEK Inc.",                      "Industrials", "Industrial Machinery",       450, []),
    ("ROP",   "Roper Technologies",               "Industrials", "Industrial Machinery",       600, []),
    ("PH",    "Parker Hannifin",                  "Industrials", "Industrial Machinery",       700, []),
    ("CMI",   "Cummins Inc.",                     "Industrials", "Industrial Machinery",       400, ["EV"]),
    ("CARR",  "Carrier Global",                   "Industrials", "Building Products",          500, []),
    ("OTIS",  "Otis Worldwide",                   "Industrials", "Industrial Machinery",       360, []),
    ("IR",    "Ingersoll Rand",                   "Industrials", "Industrial Machinery",       380, []),
    ("XYL",   "Xylem Inc.",                       "Industrials", "Industrial Machinery",       250, []),

    # —— 运输 Transportation ——
    ("UPS",   "United Parcel Service",            "Industrials", "Air Freight & Logistics",   900, ["AI","ROBOT"]),
    ("FDX",   "FedEx Corporation",                "Industrials", "Air Freight & Logistics",   750, ["AI","ROBOT"]),
    ("CSX",   "CSX Corporation",                  "Industrials", "Railroads",                  650, []),
    ("UNP",   "Union Pacific",                    "Industrials", "Railroads",                 1600, []),
    ("NSC",   "Norfolk Southern",                 "Industrials", "Railroads",                  600, []),
    ("DAL",   "Delta Air Lines",                  "Industrials", "Airlines",                   300, []),
    ("UAL",   "United Airlines Holdings",         "Industrials", "Airlines",                   240, []),
    ("AAL",   "American Airlines Group",          "Industrials", "Airlines",                    80, []),
    ("LUV",   "Southwest Airlines",               "Industrials", "Airlines",                   180, []),
    ("JBHT",  "J.B. Hunt Transport Services",     "Industrials", "Trucking",                   220, []),
    ("LSTR",  "Landstar System",                  "Industrials", "Trucking",                   100, []),
    ("XPO",   "XPO Inc.",                         "Industrials", "Trucking",                   160, []),
    ("SAIA",  "Saia Inc.",                        "Industrials", "Trucking",                   100, []),
    ("EXPD",  "Expeditors International",         "Industrials", "Air Freight & Logistics",    220, []),
    ("CHRW",  "C.H. Robinson Worldwide",          "Industrials", "Air Freight & Logistics",    140, []),

    # —— 商业服务 Commercial Services ——
    ("ADP",   "Automatic Data Processing",        "Industrials", "Commercial Services",       1200, ["AI","CLOUD"]),
    ("CTAS",  "Cintas Corporation",               "Industrials", "Commercial Services",        850, []),
    ("WM",    "Waste Management",                 "Industrials", "Commercial Services",        900, []),
    ("RSG",   "Republic Services",                "Industrials", "Commercial Services",        600, []),
    ("FAST",  "Fastenal Company",                 "Industrials", "Commercial Services",        500, []),
    ("GWW",   "W.W. Grainger",                    "Industrials", "Commercial Services",        570, []),
    ("MSC",   "MSC Industrial Direct",            "Industrials", "Commercial Services",         55, []),
    ("VRSK",  "Verisk Analytics",                 "Industrials", "Commercial Services",        400, ["AI"]),
    ("INFO",  "IHS Markit (S&P Global)",          "Industrials", "Commercial Services",       1800, []),
    ("SPGI",  "S&P Global",                       "Industrials", "Commercial Services",       1600, ["AI"]),
    ("MCO",   "Moody's Corporation",              "Industrials", "Commercial Services",        900, ["AI"]),

    # ================================================================
    # 能源 Energy
    # ================================================================
    ("XOM",   "ExxonMobil Corporation",           "Energy", "Integrated Oil & Gas",         5400, []),
    ("CVX",   "Chevron Corporation",              "Energy", "Integrated Oil & Gas",          2800, []),
    ("COP",   "ConocoPhillips",                   "Energy", "E&P",                           1600, []),
    ("EOG",   "EOG Resources",                    "Energy", "E&P",                             800, []),
    ("DVN",   "Devon Energy",                     "Energy", "E&P",                             200, []),
    ("FANG",  "Diamondback Energy",               "Energy", "E&P",                             290, []),
    ("APA",   "APA Corporation",                  "Energy", "E&P",                              80, []),
    ("MRO",   "Marathon Oil",                     "Energy", "E&P",                             140, []),
    ("HES",   "Hess Corporation",                 "Energy", "E&P",                             480, []),
    ("OXY",   "Occidental Petroleum",             "Energy", "Integrated Oil & Gas",           500, []),
    ("SLB",   "SLB (Schlumberger)",               "Energy", "Energy Services",                800, ["AI"]),
    ("HAL",   "Halliburton Company",              "Energy", "Energy Services",                300, []),
    ("BKR",   "Baker Hughes",                     "Energy", "Energy Services",                280, []),
    ("KMI",   "Kinder Morgan",                    "Energy", "Midstream",                      230, []),
    ("WMB",   "Williams Companies",               "Energy", "Midstream",                      570, []),
    ("OKE",   "ONEOK Inc.",                       "Energy", "Midstream",                      480, []),
    ("PSX",   "Phillips 66",                      "Energy", "Refining",                       600, []),
    ("VLO",   "Valero Energy",                    "Energy", "Refining",                       500, []),
    ("MPC",   "Marathon Petroleum",               "Energy", "Refining",                       600, []),
    ("FSLR",  "First Solar",                      "Energy", "Renewable Energy",               300, ["CLEAN","EV"]),
    ("ENPH",  "Enphase Energy",                   "Energy", "Renewable Energy",               150, ["CLEAN","EV"]),
    ("CEG",   "Constellation Energy",             "Energy", "Renewable Energy",              1300, ["CLEAN","AI"]),
    ("VST",   "Vistra Corp",                      "Energy", "Renewable Energy",              1100, ["CLEAN","AI"]),

    # ================================================================
    # 材料 Materials
    # ================================================================
    ("LIN",   "Linde plc",                        "Materials", "Industrial Gases",           2500, []),
    ("SHW",   "Sherwin-Williams",                 "Materials", "Specialty Chemicals",         900, []),
    ("APD",   "Air Products & Chemicals",         "Materials", "Industrial Gases",            700, ["CLEAN"]),
    ("ECL",   "Ecolab Inc.",                      "Materials", "Specialty Chemicals",         600, []),
    ("DOW",   "Dow Inc.",                         "Materials", "Commodity Chemicals",         300, []),
    ("LYB",   "LyondellBasell Industries",        "Materials", "Commodity Chemicals",         180, []),
    ("EMN",   "Eastman Chemical",                 "Materials", "Specialty Chemicals",         100, []),
    ("PPG",   "PPG Industries",                   "Materials", "Specialty Chemicals",         300, []),
    ("CF",    "CF Industries",                    "Materials", "Agricultural Chemicals",      150, []),
    ("MOS",   "Mosaic Company",                   "Materials", "Agricultural Chemicals",      100, []),
    ("FCX",   "Freeport-McMoRan",                 "Materials", "Copper",                      690, []),
    ("NEM",   "Newmont Corporation",              "Materials", "Gold",                        420, []),
    ("GOLD",  "Barrick Gold",                     "Materials", "Gold",                        300, []),
    ("NUE",   "Nucor Corporation",                "Materials", "Steel",                       300, []),
    ("STLD",  "Steel Dynamics",                   "Materials", "Steel",                       220, []),
    ("X",     "U.S. Steel Corporation",           "Materials", "Steel",                        90, []),
    ("CLF",   "Cleveland-Cliffs",                 "Materials", "Steel",                        60, []),
    ("IP",    "International Paper",              "Materials", "Paper & Forest Products",     190, []),
    ("PKG",   "Packaging Corporation of America", "Materials", "Paper & Packaging",           200, []),
    ("BALL",  "Ball Corporation",                 "Materials", "Metal Containers",            110, []),
    ("MLM",   "Martin Marietta Materials",        "Materials", "Construction Materials",      350, []),
    ("VMC",   "Vulcan Materials",                 "Materials", "Construction Materials",      310, []),
    ("ALB",   "Albemarle Corporation",            "Materials", "Specialty Chemicals",          60, ["EV"]),

    # ================================================================
    # 公用事业 Utilities
    # ================================================================
    ("NEE",   "NextEra Energy",                   "Utilities", "Electric Utilities",          1600, ["CLEAN","AI"]),
    ("SO",    "Southern Company",                 "Utilities", "Electric Utilities",          1000, ["CLEAN"]),
    ("D",     "Dominion Energy",                  "Utilities", "Multi-Utilities",              450, []),
    ("DUK",   "Duke Energy",                      "Utilities", "Electric Utilities",           900, ["CLEAN"]),
    ("AEP",   "American Electric Power",          "Utilities", "Electric Utilities",           500, ["CLEAN"]),
    ("EXC",   "Exelon Corporation",               "Utilities", "Electric Utilities",           450, []),
    ("XEL",   "Xcel Energy",                      "Utilities", "Electric Utilities",           350, ["CLEAN"]),
    ("WEC",   "WEC Energy Group",                 "Utilities", "Multi-Utilities",              300, []),
    ("ES",    "Eversource Energy",                "Utilities", "Electric Utilities",           160, []),
    ("ETR",   "Entergy Corporation",              "Utilities", "Electric Utilities",           240, []),
    ("PPL",   "PPL Corporation",                  "Utilities", "Electric Utilities",           230, []),
    ("FE",    "FirstEnergy Corp",                 "Utilities", "Electric Utilities",           250, []),
    ("PCG",   "PG&E Corporation",                 "Utilities", "Electric Utilities",           320, []),
    ("EIX",   "Edison International",             "Utilities", "Electric Utilities",           170, []),
    ("CNP",   "CenterPoint Energy",               "Utilities", "Multi-Utilities",              200, []),
    ("AWK",   "American Water Works",             "Utilities", "Water Utilities",              250, []),
    ("ATO",   "Atmos Energy",                     "Utilities", "Gas Utilities",               220, []),
    ("NI",    "NiSource Inc.",                    "Utilities", "Multi-Utilities",              150, []),
    ("AES",   "AES Corporation",                  "Utilities", "Electric Utilities",           100, ["CLEAN"]),
    ("NRG",   "NRG Energy",                       "Utilities", "Electric Utilities",           110, []),
    ("EVRG",  "Evergy Inc.",                      "Utilities", "Electric Utilities",           120, []),
    ("OGE",   "OGE Energy Corp",                  "Utilities", "Electric Utilities",            70, []),
    ("PNW",   "Pinnacle West Capital",            "Utilities", "Electric Utilities",            80, []),

    # ================================================================
    # 房地产 Real Estate
    # ================================================================
    ("AMT",   "American Tower",                   "Real Estate", "Telecom Tower REITs",      1000, []),
    ("CCI",   "Crown Castle",                     "Real Estate", "Telecom Tower REITs",       500, []),
    ("EQIX",  "Equinix Inc.",                     "Real Estate", "Data Center REITs",         900, ["CLOUD","AI"]),
    ("PLD",   "Prologis Inc.",                    "Real Estate", "Industrial REITs",          1200, []),
    ("DLR",   "Digital Realty Trust",             "Real Estate", "Data Center REITs",         550, ["CLOUD","AI"]),
    ("PSA",   "Public Storage",                   "Real Estate", "Self-Storage REITs",         560, []),
    ("SPG",   "Simon Property Group",             "Real Estate", "Retail REITs",              620, []),
    ("O",     "Realty Income",                    "Real Estate", "Net Lease REITs",            520, []),
    ("VICI",  "VICI Properties",                  "Real Estate", "Hotel & Gaming REITs",       300, []),
    ("IRM",   "Iron Mountain",                    "Real Estate", "Diversified REITs",          250, ["AI"]),
    ("SBAC",  "SBA Communications",               "Real Estate", "Telecom Tower REITs",        220, []),
    ("CBRE",  "CBRE Group",                       "Real Estate", "Real Estate Services",       390, ["AI"]),
    ("JLL",   "Jones Lang LaSalle",               "Real Estate", "Real Estate Services",       110, []),
    ("EQR",   "Equity Residential",               "Real Estate", "Apartment REITs",            310, []),
    ("MAA",   "Mid-America Apartment",            "Real Estate", "Apartment REITs",            180, []),
    ("CPT",   "Camden Property Trust",            "Real Estate", "Apartment REITs",            110, []),
    ("BXP",   "BXP Inc.",                         "Real Estate", "Office REITs",               150, []),
    ("VNO",   "Vornado Realty Trust",             "Real Estate", "Office REITs",                60, []),
    ("KIM",   "Kimco Realty",                     "Real Estate", "Retail REITs",               140, []),
    ("REG",   "Regency Centers",                  "Real Estate", "Retail REITs",               130, []),
    ("EXR",   "Extra Space Storage",              "Real Estate", "Self-Storage REITs",          340, []),
    ("WY",    "Weyerhaeuser Company",             "Real Estate", "Timber REITs",               180, []),
    ("INVH",  "Invitation Homes",                 "Real Estate", "Single-Family REITs",        250, []),

    # ================================================================
    # NASDAQ 100 独有（非S&P500）关键科技股
    # ================================================================
    ("IONQ",  "IonQ Inc.",                        "Information Technology", "Quantum Computing",    30, ["QUANTUM","AI"]),
    ("RGTI",  "Rigetti Computing",                "Information Technology", "Quantum Computing",    10, ["QUANTUM"]),
    ("SOUN",  "SoundHound AI",                    "Information Technology", "Application Software", 20, ["AI"]),
    ("ARM",   "ARM Holdings",                     "Information Technology", "Semiconductors",    1700, ["SEMI","AI","AUTO"]),
    ("SMCI",  "Super Micro Computer",             "Information Technology", "Technology Hardware",  600, ["AI","CLOUD"]),
    ("PLTR",  "Palantir Technologies",            "Information Technology", "Application Software", 2800, ["AI","DEFENSE"]),
    ("APP",   "Applovin Corporation",             "Information Technology", "Application Software", 1500, ["AI"]),
    ("CRUS",  "Cirrus Logic",                     "Information Technology", "Semiconductors",        100, ["SEMI"]),
    ("MRVL",  "Marvell Technology",               "Information Technology", "Semiconductors",        900, ["SEMI","AI","CLOUD"]),
    ("COIN",  "Coinbase Global",                  "Financials", "Transaction Processing",    700, ["FINTECH"]),
    ("MSTR",  "MicroStrategy",                    "Financials", "Asset Management",          1300, ["FINTECH"]),
    ("SAMSARA", "Samsara Inc.",                   "Information Technology", "Application Software", 300, ["AI","ROBOT"]),
    ("AFRM",  "Affirm Holdings",                  "Financials", "Consumer Finance",           55, ["FINTECH"]),
    ("HOOD",  "Robinhood Markets",                "Financials", "Transaction Processing",    250, ["FINTECH"]),
    ("OPEN",  "Opendoor Technologies",            "Real Estate", "Real Estate Services",      10, []),
    ("RDFN",  "Redfin Corporation",               "Real Estate", "Real Estate Services",      10, []),
]

# 概念定义（与 UI 展示直接对应）
US_CONCEPTS = [
    # 科技优先 8 个（默认显示）
    {
        "id": 1, "name": "AI & 大模型",
        "icon": "🤖", "name_en": "AI & LLM",
        "keywords": ["artificial intelligence","machine learning","LLM","GPT","foundation model","generative AI"],
        "tickers": ["NVDA","MSFT","GOOGL","META","AMZN","AMD","IBM","ORCL","PLTR","APP","SMCI"],
        "is_default": True
    },
    {
        "id": 2, "name": "云计算",
        "icon": "☁️", "name_en": "Cloud Computing",
        "keywords": ["cloud","SaaS","platform","AWS","Azure","GCP","cloud infrastructure"],
        "tickers": ["MSFT","AMZN","GOOGL","CRM","NOW","WDAY","DDOG","SNOW","NET","EQIX","DLR"],
        "is_default": True
    },
    {
        "id": 3, "name": "半导体",
        "icon": "🔬", "name_en": "Semiconductors",
        "keywords": ["semiconductor","chip","wafer","fab","silicon","GPU","CPU","memory"],
        "tickers": ["NVDA","AVGO","AMD","QCOM","TXN","INTC","AMAT","LRCX","KLAC","MU","ARM","MRVL"],
        "is_default": True
    },
    {
        "id": 4, "name": "电动车 EV",
        "icon": "⚡", "name_en": "Electric Vehicle",
        "keywords": ["electric vehicle","EV","battery","lithium","charging","autonomous"],
        "tickers": ["TSLA","GM","F","RIVN","APTV","ON","ALB","ENPH","CEG"],
        "is_default": True
    },
    {
        "id": 5, "name": "生物科技",
        "icon": "🧬", "name_en": "Biotechnology",
        "keywords": ["biotech","clinical trial","FDA","drug","therapy","gene","mRNA"],
        "tickers": ["AMGN","GILD","BIIB","REGN","VRTX","MRNA","ILMN","CRSP","BEAM","NTLA"],
        "is_default": True
    },
    {
        "id": 6, "name": "网络安全",
        "icon": "🛡️", "name_en": "Cybersecurity",
        "keywords": ["cybersecurity","security","firewall","zero trust","threat detection","SIEM","SOC"],
        "tickers": ["PANW","CRWD","FTNT","ZS","OKTA","NET","CYBR"],
        "is_default": True
    },
    {
        "id": 7, "name": "机器人",
        "icon": "🤖", "name_en": "Robotics & Automation",
        "keywords": ["robot","automation","manufacturing","autonomous","humanoid","cobot"],
        "tickers": ["ISRG","ROK","EMR","TSLA","AMZN","HON","TER","ABB"],
        "is_default": True
    },
    {
        "id": 8, "name": "商业航天",
        "icon": "🚀", "name_en": "Commercial Space",
        "keywords": ["space","satellite","rocket","orbital","launch","defense space"],
        "tickers": ["RKLB","LMT","RTX","NOC","GD","BA","KTOS","ASTS","JOBY"],
        "is_default": True
    },
    # 更多（展开后显示）
    {
        "id": 9, "name": "GLP-1 减肥药",
        "icon": "💊", "name_en": "GLP-1 Drugs",
        "keywords": ["GLP-1","obesity","weight loss","semaglutide","tirzepatide","Ozempic","Wegovy"],
        "tickers": ["NVO","LLY","PFE","AZN"],
        "is_default": False
    },
    {
        "id": 10, "name": "基因编辑",
        "icon": "🧬", "name_en": "Gene Editing",
        "keywords": ["CRISPR","gene editing","gene therapy","genetic","genomics","DNA","RNA"],
        "tickers": ["CRSP","BEAM","NTLA","ILMN","TMO","VRTX"],
        "is_default": False
    },
    {
        "id": 11, "name": "数字支付",
        "icon": "💳", "name_en": "Digital Payments",
        "keywords": ["payment","fintech","digital wallet","transaction","cryptocurrency","blockchain"],
        "tickers": ["V","MA","PYPL","SQ","AXP","COIN","HOOD"],
        "is_default": False
    },
    {
        "id": 12, "name": "量子计算",
        "icon": "⚛️", "name_en": "Quantum Computing",
        "keywords": ["quantum","qubit","quantum computing","quantum processor"],
        "tickers": ["IBM","IONQ","RGTI","MSFT","GOOGL"],
        "is_default": False
    },
    {
        "id": 13, "name": "自动驾驶",
        "icon": "🚗", "name_en": "Autonomous Driving",
        "keywords": ["autonomous","self-driving","ADAS","lidar","autopilot","robotaxi"],
        "tickers": ["TSLA","GOOGL","UBER","GM","APTV","MOBILEYE","QCOM","NVDA"],
        "is_default": False
    },
    {
        "id": 14, "name": "AR / VR",
        "icon": "🥽", "name_en": "Augmented & Virtual Reality",
        "keywords": ["augmented reality","virtual reality","mixed reality","spatial computing","metaverse","headset"],
        "tickers": ["META","AAPL","MSFT","SNAP","QCOM","RBLX"],
        "is_default": False
    },
    {
        "id": 15, "name": "清洁能源",
        "icon": "🌱", "name_en": "Clean Energy",
        "keywords": ["clean energy","renewable","solar","wind","nuclear","hydrogen","carbon"],
        "tickers": ["NEE","FSLR","ENPH","CEG","VST","ETN","APD"],
        "is_default": False
    },
    {
        "id": 16, "name": "航空国防",
        "icon": "✈️", "name_en": "Aerospace & Defense",
        "keywords": ["defense","military","aerospace","weapons","missile","fighter","navy","army"],
        "tickers": ["LMT","RTX","NOC","GD","BA","HII","TDG","LDOS","KTOS"],
        "is_default": False
    },
    {
        "id": 17, "name": "数据中心",
        "icon": "🏭", "name_en": "Data Centers",
        "keywords": ["data center","colocation","server","infrastructure","hyperscale"],
        "tickers": ["EQIX","DLR","AMT","CCI","SMCI","NVDA","IRM"],
        "is_default": False
    },
    {
        "id": 18, "name": "高股息/价值",
        "icon": "💰", "name_en": "Dividend / Value",
        "keywords": ["dividend","value","yield","income","defensive"],
        "tickers": ["JNJ","PG","KO","MO","VZ","T","O","NEE"],
        "is_default": False
    },
    {
        "id": 19, "name": "黄金/贵金属",
        "icon": "🥇", "name_en": "Gold & Precious Metals",
        "keywords": ["gold","silver","precious metals","mining","bullion"],
        "tickers": ["NEM","GOLD","AEM","WPM","FCX"],
        "is_default": False
    },
    {
        "id": 20, "name": "流媒体 / 娱乐",
        "icon": "🎬", "name_en": "Streaming & Entertainment",
        "keywords": ["streaming","entertainment","content","subscription","studio","OTT"],
        "tickers": ["NFLX","DIS","PARA","SPOT","WBD","CMCSA"],
        "is_default": False
    },
]
