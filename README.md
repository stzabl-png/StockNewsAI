# 🧬 NewsAnalysisForStock

美股生物医药新闻智能分析系统 — 7×24 小时自动运行

## 功能特性

- 📰 **实时采集** — Finnhub、FDA、ClinicalTrials.gov、SEC EDGAR 四大数据源
- 🧠 **AI 深度分析** — GPT-4o-mini 初筛 + Claude Sonnet 深度分析
- 📊 **可视化面板** — Web Dashboard 实时查看新闻流、情感趋势、催化剂日历
- 📱 **即时推送** — 微信 (WxPusher) + Telegram Bot 分级通知

## 快速启动

### 1. 环境准备

```bash
cp .env.example .env
# 编辑 .env，填入 API Keys
```

### 2. 启动服务

```bash
docker-compose up -d
```

### 3. 验证

```bash
# 健康检查
curl http://localhost:8000/api/health

# API 文档
# 浏览器打开 http://localhost:8000/docs
```

## 技术栈

| 层级 | 技术 |
|:---|:---|
| 后端 | Python + FastAPI |
| 数据库 | PostgreSQL 16 |
| 缓存/去重 | Redis 7 |
| 前端 | Next.js 14 + shadcn/ui |
| 容器化 | Docker Compose |

## 项目结构

```
StockNews/
├── docker-compose.yml          # 服务编排
├── .env.example                # 环境变量模板
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── main.py             # 入口
│   │   ├── config.py           # 配置
│   │   ├── database.py         # 数据库
│   │   ├── models/             # 数据模型
│   │   ├── services/           # 业务逻辑
│   │   ├── api/                # REST API
│   │   └── ws/                 # WebSocket
│   └── alembic/                # 数据库迁移
├── frontend/                   # Next.js 前端
├── nginx/                      # 反向代理
└── scripts/                    # 部署脚本
```

## License

Private - For internal use only.
