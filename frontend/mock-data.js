/**
 * StockNewsAI — Mock 数据
 * 前端开发者无需后端即可看到真实数据样貌
 * 当 API 不可用时自动启用
 */
const MOCK_DATA = {
    health: {
        status: "ok", db: "connected", redis: "connected",
        scheduler: "running", app: "NewsAnalysisForStock", version: "1.0.0"
    },
    newsStats: { total: 24, by_source: { finnhub: 24 } },
    analysisStats: {
        total: 24, high_impact: 1,
        by_sentiment: { bearish: 6, bullish: 12, neutral: 6 },
        by_impact: { medium: 17, high: 1, low: 6 }
    },
    watchlist: [
        { id: 3, ticker: "AMGN", name: "Amgen", sector: "Biotechnology", therapeutic_area: "", priority: "medium", track_fda: true, track_trials: true, is_active: true, notes: "" },
        { id: 2, ticker: "LLY", name: "Eli Lilly", sector: "Biotechnology", therapeutic_area: "", priority: "medium", track_fda: true, track_trials: true, is_active: true, notes: "" },
        { id: 1, ticker: "MRNA", name: "Moderna", sector: "Biotechnology", therapeutic_area: "", priority: "medium", track_fda: true, track_trials: true, is_active: true, notes: "" }
    ],
    news: [
        { id: 2, company_id: 2, ticker: "LLY", company_name: "Eli Lilly", title: "Eli Lilly Isn't Replacing Zepbound -- It's Building an Obesity Empire", summary: "And it's not too late to get in on the action.", source: "finnhub", source_url: "#", category: "general", published_at: "2026-04-11T14:50:00Z", created_at: "2026-04-12T10:01:56Z" },
        { id: 21, company_id: 3, ticker: "AMGN", company_name: "Amgen", title: "Assessing Amgen (AMGN) Valuation As TEPEZZA And MariTide Trial Results Draw Fresh Investor Focus", summary: "Why TEPEZZA and MariTide Are Back in Focus for Amgen (AMGN). Phase 3 data for subcutaneous TEPEZZA showed strong results.", source: "finnhub", source_url: "#", category: "clinical_trial", published_at: "2026-04-11T10:11:51Z", created_at: "2026-04-12T10:01:56Z" },
        { id: 3, company_id: 2, ticker: "LLY", company_name: "Eli Lilly", title: "Foundayo Explained: Lilly's New Weight Loss Pill And The Amazon Effect", summary: "Eli Lilly secures FDA approval for Foundayo, an oral GLP-1 therapy targeting obesity with significant advantages.", source: "finnhub", source_url: "#", category: "fda_approval", published_at: "2026-04-11T09:41:57Z", created_at: "2026-04-12T10:01:56Z" },
        { id: 4, company_id: 2, ticker: "LLY", company_name: "Eli Lilly", title: "Potential $5,000 Monthly Income: 12 Investments To Buy And Hold For The Next 10 Years", summary: "Diversified hands-off retirement portfolio: 12 funds targeting 6% yield + 6% dividend growth.", source: "finnhub", source_url: "#", category: "general", published_at: "2026-04-11T08:10:00Z", created_at: "2026-04-12T10:01:56Z" },
        { id: 5, company_id: 2, ticker: "LLY", company_name: "Eli Lilly", title: "Hims And Hers Confronts Amazon Threat While Advancing AI Weight Loss Plan", summary: "Amazon Pharmacy has entered the weight loss medication market with Eli Lilly's new GLP-1 drug.", source: "finnhub", source_url: "#", category: "general", published_at: "2026-04-11T02:09:23Z", created_at: "2026-04-12T10:01:56Z" },
        { id: 6, company_id: 2, ticker: "LLY", company_name: "Eli Lilly", title: "Trump policies, China's biotech boom are ending Europe's pharma powerhouse era", summary: "Companies have long lamented Europe's fragmented capital markets and uneven reimbursement policies.", source: "finnhub", source_url: "#", category: "general", published_at: "2026-04-11T01:54:00Z", created_at: "2026-04-12T10:01:56Z" },
        { id: 22, company_id: 3, ticker: "AMGN", company_name: "Amgen", title: "This Startup's Psoriasis Drug Studies Have Lifted Its Stock", summary: "Phase 1 studies showed that one shot of ORKA-001 lasted long enough to allow dosing twice-a-year.", source: "finnhub", source_url: "#", category: "clinical_trial", published_at: "2026-04-10T21:28:00Z", created_at: "2026-04-12T10:01:56Z" },
        { id: 7, company_id: 2, ticker: "LLY", company_name: "Eli Lilly", title: "India GLP 1 Generics Test Novo Nordisk Pricing Power And Valuation", summary: "Cheap semaglutide generics have launched in India following local loss of exclusivity.", source: "finnhub", source_url: "#", category: "general", published_at: "2026-04-10T21:12:40Z", created_at: "2026-04-12T10:01:56Z" },
        { id: 1, company_id: 1, ticker: "MRNA", company_name: "Moderna", title: "Study Showing 50% Drop In COVID ER Visits Thanks To The Vaccine Put On Hold By CDC", summary: "CDC delays reporting due to methodology concerns, potentially impacting vaccine perception.", source: "finnhub", source_url: "#", category: "regulatory", published_at: "2026-04-10T15:30:00Z", created_at: "2026-04-12T10:01:56Z" },
        { id: 8, company_id: 2, ticker: "LLY", company_name: "Eli Lilly", title: "Eli Lilly vs. Novo Nordisk: The Obesity Drug Race Has a New Leader", summary: "Lilly's tirzepatide franchise is accelerating. Novo is cutting jobs and warning of a sales decline.", source: "finnhub", source_url: "#", category: "general", published_at: "2026-04-10T16:09:04Z", created_at: "2026-04-12T10:01:56Z" }
    ],
    analysis: [
        { id: 1, news_id: 3, ticker: "LLY", company_name: "Eli Lilly", news_title: "Foundayo Explained: Lilly's New Weight Loss Pill And The Amazon Effect", level: 2, sentiment: "bullish", confidence: 0.95, impact_level: "high", impact_duration: "medium_term", summary_cn: "Eli Lilly获得FDA批准其口服GLP-1减肥药Foundayo，市场预期积极，可能推动公司股价上涨并提升营收预期。", detailed_analysis: { direct_impact: "FDA批准Foundayo可能导致Eli Lilly股价短期内上涨，因为这表明公司在肥胖治疗市场上取得了重要进展。", pipeline_impact: "Foundayo的批准增强了Eli Lilly在GLP-1治疗领域的产品线，可能带来长期的市场份额增长和品牌影响力提升。", competitive_landscape: "Foundayo的推出可能对Novo Nordisk等GLP-1领域的竞争对手构成压力，迫使其加快产品开发和市场策略调整。", revenue_impact: "Foundayo的市场潜力巨大，预计将显著增加Eli Lilly的营收。", risk_factors: ["市场竞争加剧", "药物安全性和长期效果的不确定性"] }, related_tickers: ["NVO", "PFE"], key_dates: ["Q2财报发布", "Foundayo市场推广活动启动日期"], created_at: "2026-04-12T10:23:07Z" },
        { id: 24, news_id: 20, ticker: "LLY", company_name: "Eli Lilly", news_title: "Amazon AI Chips And Foundayo Pill Reframe Growth And ESG Debate", level: 1, sentiment: "bullish", confidence: 0.7, impact_level: "medium", impact_duration: "medium_term", summary_cn: "亚马逊药房开始提供Eli Lilly的Foundayo减肥药，标志着其在直接面向患者的医疗服务领域的深入布局。", detailed_analysis: null, related_tickers: null, key_dates: null, created_at: "2026-04-12T17:56:22Z" },
        { id: 23, news_id: 19, ticker: "LLY", company_name: "Eli Lilly", news_title: "Eli Lilly market share drops, Novo Nordisk holds firm as generic weight-loss drugs flood India", level: 1, sentiment: "bearish", confidence: 0.7, impact_level: "medium", impact_duration: "short_term", summary_cn: "Eli Lilly在印度GLP-1市场份额下降，受到廉价仿制药的冲击。", detailed_analysis: null, related_tickers: null, key_dates: null, created_at: "2026-04-12T17:56:20Z" },
        { id: 20, news_id: 1, ticker: "MRNA", company_name: "Moderna", news_title: "Study Showing 50% Drop In COVID ER Visits Thanks To The Vaccine Put On Hold By CDC: Report", level: 1, sentiment: "bearish", confidence: 0.7, impact_level: "medium", impact_duration: "short_term", summary_cn: "CDC因方法论问题推迟报告，可能影响疫苗的公众认知和接受度。", detailed_analysis: null, related_tickers: null, key_dates: null, created_at: "2026-04-12T17:56:15Z" },
        { id: 17, news_id: 15, ticker: "LLY", company_name: "Eli Lilly", news_title: "Morgan Stanley Maintains Overweight on Eli Lilly, Raises Price Target to $1327", level: 1, sentiment: "bullish", confidence: 0.7, impact_level: "medium", impact_duration: "short_term", summary_cn: "摩根士丹利维持对Eli Lilly的增持评级，并将目标价上调至1327美元。", detailed_analysis: null, related_tickers: null, key_dates: null, created_at: "2026-04-12T17:56:09Z" },
        { id: 21, news_id: 24, ticker: "AMGN", company_name: "Amgen", news_title: "Is Amgen (AMGN) One of the Most Profitable Value Stocks to Buy Right Now?", level: 1, sentiment: "bullish", confidence: 0.7, impact_level: "medium", impact_duration: "medium_term", summary_cn: "Amgen在一项评估TEPEZZA的III期临床试验中宣布了积极的顶线结果。", detailed_analysis: null, related_tickers: null, key_dates: null, created_at: "2026-04-12T17:56:17Z" },
        { id: 15, news_id: 13, ticker: "LLY", company_name: "Eli Lilly", news_title: "Who Benefits From Amazon Pharmacy Stocking Eli Lilly's New Weight Loss Pill", level: 1, sentiment: "bullish", confidence: 0.7, impact_level: "medium", impact_duration: "medium_term", summary_cn: "亚马逊药房开始销售Eli Lilly的新减肥药，可能会提升其市场接触率。", detailed_analysis: null, related_tickers: null, key_dates: null, created_at: "2026-04-12T17:56:05Z" }
    ],
    schedulerJobs: {
        scheduler_running: true,
        jobs: [
            { id: "fetch_news", name: "📰 Finnhub 新闻采集", next_run: new Date(Date.now() + 3600000).toISOString(), trigger: "interval[1:00:00]", paused: false },
            { id: "analyze_pending", name: "🧠 未处理新闻分析", next_run: new Date(Date.now() + 7200000).toISOString(), trigger: "interval[2:00:00]", paused: false },
            { id: "cleanup_old_data", name: "🧹 旧数据清理", next_run: new Date(Date.now() + 86400000).toISOString(), trigger: "cron[hour='3', minute='0']", paused: false }
        ]
    }
};
