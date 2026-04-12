# 🧬 StockNewsAI

**美股生物医药新闻智能分析系统** — 7×24 小时自动采集、AI 分析、微信推送

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![GPT-4o](https://img.shields.io/badge/AI-GPT--4o-blueviolet)](https://openai.com)

---

## 📌 项目简介

StockNewsAI 自动追踪生物医药行业（LLY、AMGN、MRNA 等）的新闻动态，利用 GPT-4o 进行两级智能分析（初筛 + 深度分析），并将高影响事件（FDA 批准、临床数据、重大并购）实时推送到微信。

### 核心功能

| 功能 | 说明 |
|:---|:---|
| 📰 **自动采集** | 每小时从 Finnhub 抓取关注公司的最新新闻 |
| 🧠 **AI 双级分析** | L1 GPT-4o-mini 全量初筛 → L2 GPT-4o 高影响事件深度分析 |
| 📊 **Web Dashboard** | 暗色主题仪表盘，实时展示新闻流、情感分析、关注列表 |
| 📱 **微信推送** | 高影响事件自动推送到微信（Server酱） |
| ⏰ **自动调度** | APScheduler 定时采集/分析/清理，无需人工干预 |

---

## 🏗️ 技术架构

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Finnhub    │────▶│   FastAPI     │────▶│  PostgreSQL  │
│  News API   │     │   Backend    │     │  Database    │
└─────────────┘     │              │     └─────────────┘
                    │  ┌─────────┐ │     ┌─────────────┐
                    │  │ GPT-4o  │ │────▶│    Redis     │
                    │  │ 分析引擎 │ │     │  去重缓存    │
                    │  └─────────┘ │     └─────────────┘
                    │              │     ┌─────────────┐
                    │  ┌─────────┐ │────▶│   Server酱   │
                    │  │ 调度器  │ │     │  微信推送    │
                    │  └─────────┘ │     └─────────────┘
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  Web Dashboard│
                    │  (HTML/CSS/JS)│
                    └──────────────┘
```

---

## 🚀 快速启动

### 前置条件
- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- API Keys（见下方）

### 一键启动
```bash
git clone git@github.com:stzabl-png/StockNewsAI.git
cd StockNewsAI

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 API Keys（找项目负责人获取）

# 启动所有服务
docker compose up -d --build

# 打开浏览器
open http://localhost:8000
```

### 需要的 API Keys

| Key | 用途 | 获取方式 |
|:---|:---|:---|
| `FINNHUB_API_KEY` | 新闻数据源 | [finnhub.io](https://finnhub.io) 注册 |
| `OPENAI_API_KEY` | AI 分析引擎 | [platform.openai.com](https://platform.openai.com) |
| `WECHAT_SENDKEY` | 微信推送 | [sct.ftqq.com](https://sct.ftqq.com) 注册 |

---

## 📁 项目结构

```
StockNewsAI/
├── frontend/                  ← 前端代码
│   ├── index.html             ← 页面结构
│   ├── style.css              ← 暗色主题样式
│   ├── app.js                 ← 交互逻辑 + API 调用
│   └── mock-data.js           ← Mock 数据（无后端时自动加载）
├── backend/                   ← 后端 API
│   ├── app/
│   │   ├── main.py            ← FastAPI 入口
│   │   ├── config.py          ← 配置管理
│   │   ├── models.py          ← 数据库模型
│   │   ├── database.py        ← 异步数据库连接
│   │   ├── api/               ← API 路由
│   │   │   ├── watchlist.py   ← 关注列表 CRUD
│   │   │   ├── news.py        ← 新闻查询 + 采集
│   │   │   ├── analysis.py    ← AI 分析
│   │   │   ├── scheduler.py   ← 调度器管理
│   │   │   └── notify.py      ← 推送测试
│   │   └── services/          ← 业务逻辑
│   │       ├── analyzer.py    ← GPT-4o 双级分析引擎
│   │       ├── notifier.py    ← 微信推送（Server酱）
│   │       ├── scheduler.py   ← APScheduler 定时任务
│   │       ├── dedup.py       ← Redis 新闻去重
│   │       └── fetchers/      ← 数据采集器
│   ├── requirements.txt       ← Python 依赖
│   └── Dockerfile
├── docker-compose.yml         ← 服务编排
├── .env.example               ← 环境变量模板
├── FRONTEND_GUIDE.md          ← 前端开发协作指南
└── README.md                  ← 本文件
```

---

## 📊 Dashboard 功能

| 页面 | 功能 |
|:---|:---|
| 📊 **概览** | 统计卡片（新闻总数/利好/利空/高影响）+ 高影响事件列表 |
| 📰 **新闻流** | 全部新闻详情 + 按公司/来源筛选 |
| 🔍 **AI 分析** | 情感标签（利好/利空/中性）+ 展开深度分析详情 |
| 📋 **关注列表** | 添加/删除关注公司，管理 Watchlist |
| ⚙️ **系统** | 健康状态 + 定时任务控制（执行/暂停/恢复） |

---

## 🔧 前端开发（协作者）

**前端开发不需要 Docker！** 请查看 [FRONTEND_GUIDE.md](FRONTEND_GUIDE.md)。

```bash
# 最简启动
cd StockNewsAI/frontend
python3 -m http.server 3000
# 打开 http://localhost:3000
```

页面会自动加载 Mock 示例数据，包含真实的新闻和分析结果。左下角显示 "Mock 模式"。

改完 push 到 GitHub，后端负责人 `git pull` 即可同步上线。

---

## 🔌 API 接口

完整接口文档: `http://localhost:8000/docs` (Swagger UI)

| 接口 | 方法 | 说明 |
|:---|:---|:---|
| `/api/health` | GET | 系统健康检查 |
| `/api/watchlist` | GET/POST | 关注列表管理 |
| `/api/news` | GET | 新闻查询 |
| `/api/news/stats` | GET | 新闻统计 |
| `/api/analysis` | GET | 分析结果查询 |
| `/api/analysis/{id}` | POST | 触发单条分析 |
| `/api/fetch/finnhub` | POST | 手动采集新闻 |
| `/api/notify/test` | POST | 测试微信推送 |
| `/api/scheduler/jobs` | GET | 查看定时任务 |

---

## 📅 开发计划

- [x] Phase 1: 项目基础 & 数据库
- [x] Phase 2: Finnhub 新闻采集
- [x] Phase 3: GPT-4o 双级分析引擎
- [x] Phase 4: APScheduler 自动调度
- [x] Phase 5: 微信推送（Server酱）
- [x] Phase 6: Web Dashboard + Mock 模式
- [ ] Phase 7: 行情数据 & 催化剂日历
- [ ] Phase 8: 生产部署 & 监控

---

## 📝 License

Private Project
