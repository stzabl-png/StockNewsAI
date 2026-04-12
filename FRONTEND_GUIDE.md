# StockNewsAI — 前端开发协作指南

## 📁 项目结构

```
StockNews/
├── frontend/                  ← 前端代码（改这里）
│   ├── index.html             ← 页面结构
│   ├── style.css              ← 样式（暗色主题）
│   └── app.js                 ← 交互逻辑 + API 调用
├── backend/                   ← 后端 API（Python，一般不用动）
├── docker-compose.yml         ← 服务编排
└── .env                       ← 配置文件（API Keys）
```

## 🚀 快速启动

### ⭐ 前端开发（最简方式，不需要 Docker）
```bash
git clone git@github.com:stzabl-png/StockNewsAI.git
cd StockNewsAI/frontend

# 用 VS Code 打开（推荐）
code .

# 启动本地预览（任选一种）
# 方式1: VS Code 安装 Live Server 插件，右键 index.html → Open with Live Server
# 方式2: Python 简易服务器
python3 -m http.server 3000
# 然后打开 http://localhost:3000
```

> ✅ 页面会自动检测后端不可用，并使用 **Mock 示例数据** 展示完整界面。
> 左下角会显示 "Mock 模式" 黄色指示灯。

### 完整启动（含后端，需要 Docker）
```bash
git clone git@github.com:stzabl-png/StockNewsAI.git
cd StockNewsAI

# 复制配置模板
cp .env.example .env
# 编辑 .env，填入 API Keys（找项目负责人要）

# 一键启动所有服务
docker compose up -d --build

# 打开浏览器
open http://localhost:8000
```

## ✏️ 如何编辑前端

### 你只需要改 3 个文件：

| 文件 | 改什么 | 说明 |
|:---|:---|:---|
| `frontend/index.html` | 页面结构 | 添加/修改页面元素、布局 |
| `frontend/style.css` | 样式外观 | 颜色、字体、间距、动画 |
| `frontend/app.js` | 交互逻辑 | API 调用、数据渲染、按钮事件 |

### 修改流程（实时生效）
1. 用任何编辑器（VS Code 推荐）打开 `frontend/` 目录
2. 修改文件并保存
3. 刷新浏览器 `http://localhost:8000` → **立刻看到变化**（无需重启，无需编译）

> ✅ 前端是纯 HTML/CSS/JS，没有构建步骤，改了就能看到效果！

---

## 🎨 设计系统速查

### 颜色变量（在 style.css 顶部的 `:root` 区域）
```css
--bg-primary: #06060e;          /* 主背景 */
--bg-card: rgba(255,255,255,0.03); /* 卡片背景 */
--accent: #6366f1;              /* 主色（紫色） */
--bullish: #22c55e;             /* 利好（绿色） */
--bearish: #ef4444;             /* 利空（红色） */
--warning: #f59e0b;             /* 警告/高影响（橙色） */
--text-primary: #e8eaf0;        /* 主文字 */
--text-secondary: #8b8fa3;      /* 次要文字 */
```

### 常用 CSS 类
```css
.btn-primary    → 主按钮（紫色渐变）
.btn-ghost      → 次要按钮（透明边框）
.btn-danger     → 危险按钮（红色）
.badge-bullish  → 利好标签（绿色）
.badge-bearish  → 利空标签（红色）
.badge-high     → 高影响标签（橙色）
.card           → 卡片容器
.stat-card      → 统计卡片
```

### 页面结构
```
sidebar（侧边栏导航）
├── 概览 (page-dashboard)    — 统计卡片 + 高影响事件 + 最新新闻
├── 新闻流 (page-news)       — 新闻列表 + 筛选
├── AI 分析 (page-analysis)  — 分析结果 + 展开详情
├── 关注列表 (page-watchlist) — 公司管理 CRUD
└── 系统 (page-system)       — 健康状态 + 定时任务管理
```

---

## 🔌 可用的后端 API

前端通过 `app.js` 中的 `API` 对象调用后端，所有接口都是 `/api/` 开头：

| API | 方法 | 说明 |
|:---|:---|:---|
| `/api/health` | GET | 系统健康检查 |
| `/api/watchlist` | GET | 获取关注公司列表 |
| `/api/watchlist` | POST | 添加公司 `{ticker, name, priority}` |
| `/api/watchlist/{ticker}` | DELETE | 删除公司 |
| `/api/news?ticker=MRNA&limit=50` | GET | 获取新闻列表 |
| `/api/news/stats` | GET | 新闻统计 |
| `/api/analysis?sentiment=bullish` | GET | 获取分析结果 |
| `/api/analysis/stats` | GET | 分析统计 |
| `/api/fetch/finnhub` | POST | 触发新闻采集 |
| `/api/scheduler/jobs` | GET | 查看定时任务 |

完整 API 文档: `http://localhost:8000/docs` (Swagger UI)

---

## 💡 常见改动示例

### 改配色
编辑 `frontend/style.css` 顶部的 `:root` 变量即可全局更换。

### 加一个新页面
1. 在 `index.html` 的 sidebar 添加导航链接
2. 在 `<main>` 里添加 `<section id="page-xxx" class="page">`
3. 在 `app.js` 的 `PAGE_TITLES` 添加标题
4. 在 `loadPageData()` 的 switch 里添加加载函数

### 改新闻卡片的展示样式
找到 `app.js` 中的 `loadNews()` 函数，修改里面的 HTML 模板字符串。

---

## ❓ 常见问题

**Q: 改了文件但浏览器没变化？**
A: 强制刷新 `Ctrl+Shift+R` 清除缓存。

**Q: API 调不通？**
A: 确认 Docker 容器在运行：`docker compose ps`

**Q: 怎么看 API 返回了什么数据？**
A: 浏览器按 F12 → Network 标签，或直接访问 `http://localhost:8000/docs`
