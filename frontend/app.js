// =====================================================
//  Mock Mode Detection & API Client
// =====================================================
let isMockMode = false;

const API = {
    base: '',

    async request(path, options = {}) {
        try {
            const res = await fetch(`${this.base}${path}`, {
                headers: { 'Content-Type': 'application/json', ...options.headers },
                ...options,
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || `HTTP ${res.status}`);
            }
            return res.json();
        } catch (e) {
            console.error(`API Error [${path}]:`, e);
            throw e;
        }
    },

    // Health
    getHealth() {
        if (isMockMode) return Promise.resolve(MOCK_DATA.health);
        return this.request('/api/health');
    },

    // News
    getNews(params = {}) {
        if (isMockMode) {
            let data = MOCK_DATA.news;
            if (params.ticker) data = data.filter(n => n.ticker === params.ticker);
            return Promise.resolve(data);
        }
        const q = new URLSearchParams();
        if (params.ticker) q.set('ticker', params.ticker);
        if (params.source) q.set('source', params.source);
        q.set('limit', params.limit || 50);
        return this.request(`/api/news?${q}`);
    },
    getNewsStats() {
        if (isMockMode) return Promise.resolve(MOCK_DATA.newsStats);
        return this.request('/api/news/stats');
    },

    // Analysis
    getAnalysis(params = {}) {
        if (isMockMode) {
            let data = MOCK_DATA.analysis;
            if (params.ticker) data = data.filter(a => a.ticker === params.ticker);
            if (params.sentiment) data = data.filter(a => a.sentiment === params.sentiment);
            if (params.impact_level) data = data.filter(a => a.impact_level === params.impact_level);
            return Promise.resolve(data);
        }
        const q = new URLSearchParams();
        if (params.ticker) q.set('ticker', params.ticker);
        if (params.sentiment) q.set('sentiment', params.sentiment);
        if (params.impact_level) q.set('impact_level', params.impact_level);
        q.set('limit', params.limit || 50);
        return this.request(`/api/analysis?${q}`);
    },
    getAnalysisStats() {
        if (isMockMode) return Promise.resolve(MOCK_DATA.analysisStats);
        return this.request('/api/analysis/stats');
    },
    analyzeNews(newsId) { return this.request(`/api/analysis/${newsId}`, { method: 'POST' }); },
    analyzeBatch(sync = true) { return this.request(`/api/analysis/batch?sync=${sync}`, { method: 'POST' }); },

    // Watchlist
    getWatchlist() {
        if (isMockMode) return Promise.resolve(MOCK_DATA.watchlist);
        return this.request('/api/watchlist?active_only=false');
    },
    addCompany(data) { return this.request('/api/watchlist', { method: 'POST', body: JSON.stringify(data) }); },
    deleteCompany(ticker) { return this.request(`/api/watchlist/${ticker}`, { method: 'DELETE' }); },

    // Scheduler
    getJobs() {
        if (isMockMode) return Promise.resolve(MOCK_DATA.schedulerJobs);
        return this.request('/api/scheduler/jobs');
    },
    triggerJob(jobId) { return this.request(`/api/scheduler/jobs/${jobId}/trigger`, { method: 'POST' }); },
    pauseJob(jobId) { return this.request(`/api/scheduler/jobs/${jobId}/pause`, { method: 'POST' }); },
    resumeJob(jobId) { return this.request(`/api/scheduler/jobs/${jobId}/resume`, { method: 'POST' }); },

    // Fetch
    fetchFinnhub() { return this.request('/api/fetch/finnhub', { method: 'POST' }); },
};


// =====================================================
//  Router
// =====================================================
const PAGE_TITLES = {
    dashboard: '概览',
    news: '新闻流',
    analysis: 'AI 分析',
    watchlist: '关注列表',
    system: '系统状态',
};

let currentPage = 'dashboard';

function navigateTo(page) {
    currentPage = page;

    // Update nav
    document.querySelectorAll('.nav-item').forEach(el => {
        el.classList.toggle('active', el.dataset.page === page);
    });

    // Show page
    document.querySelectorAll('.page').forEach(el => {
        el.classList.toggle('active', el.id === `page-${page}`);
    });

    // Load page data
    loadPageData(page);
}

function loadPageData(page) {
    switch (page) {
        case 'dashboard': loadDashboard(); break;
        case 'latest': loadLatest(); break;
        case 'categories': loadCategories(); break;
        case 'analysis': loadAnalysis(); break;
        case 'watchlist': loadWatchlist(); break;
        case 'system': loadSystem(); break;
    }
}

function refreshCurrentPage() {
    loadPageData(currentPage);
    showToast('已刷新', 'info');
}


// =====================================================
//  Dashboard
// =====================================================
async function loadDashboard() {
    const container = document.getElementById('home-feed-list');
    if (!container) return;
    try {
        const analyses = await API.getAnalysis({ limit: 50 });
        
        if (analyses.length === 0) {
            container.innerHTML = emptyState('📋', '暂无最新新闻，请点击右上角 Fetch 刷新数据');
            return;
        }

        container.innerHTML = analyses.map((a, i) => `
            <div class="analysis-item">
                <div class="analysis-header" onclick="toggleDetail('home-${i}')">
                    <div class="analysis-summary-row">
                        <div class="news-sentiment ${a.sentiment}" style="width:32px;height:32px;font-size:16px;border-radius:8px;">
                            ${sentimentIcon(a.sentiment)}
                        </div>
                        <span class="news-ticker" style="font-weight: 700;">${a.ticker}</span>
                        <span class="analysis-title">${escHtml(a.news_title)}</span>
                    </div>
                    <div class="analysis-badges">
                        <span class="badge badge-${a.sentiment}">${sentimentLabel(a.sentiment)}</span>
                        <span style="color:#ef4444; font-weight:600; font-size: 11px; margin-left: 8px;">${timeAgo(a.created_at)}</span>
                    </div>
                </div>
                <div class="analysis-detail" id="detail-home-${i}">
                    <div style="margin-bottom: 12px;">
                        <strong>中文摘要:</strong>
                        <p style="color: var(--text-secondary); margin-top: 4px;">${escHtml(a.summary_cn || '暂无摘要')}</p>
                    </div>
                    ${a.detailed_analysis ? renderDetailedAnalysis(a.detailed_analysis) : '<p style="color:var(--text-muted);font-size:12px;">无深度AI分析</p>'}
                </div>
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = `<div class="empty-state"><p>加载失败: ${e.message}</p></div>`;
        showToast(`首页加载失败: ${e.message}`, 'error');
    }
}

async function loadLatest() {
    const listEl = document.getElementById('latest-news-list');
    if (!listEl) return;
    try {
        const news = await API.getNews({ limit: 50 });
        if (news.length === 0) {
            listEl.innerHTML = emptyState('📰', '暂无最新新闻');
            return;
        }
        listEl.innerHTML = news.map(n => `
            <div class="news-item">
                <div class="news-content">
                    <div class="news-meta" style="margin-bottom: 6px;">
                        <span class="news-ticker" style="font-size:14px; font-weight:700;">${n.ticker}</span>
                        ${categoryHtml(n.category)}
                        <span style="color:#ef4444; font-weight:600; margin-left: auto;">${timeAgo(n.published_at)}</span>
                    </div>
                    <div class="news-title" style="font-size:16px; margin-bottom: 8px;">${escHtml(n.title)}</div>
                    <div class="news-meta">
                        <span>📰 ${n.source}</span>
                    </div>
                </div>
            </div>
        `).join('');
    } catch(e) {
        listEl.innerHTML = emptyState('❌', '加载最新消息失败: ' + e.message);
    }
}

async function loadCategories() {
    const gridEl = document.getElementById('category-grid');
    if (!gridEl) return;
    
    // Placeholder categories UI
    const cats = [
        { id: 'biotech', icon: '🧬', label: '生物医疗', count: 34, color: '#dcfce7' },
        { id: 'clinical', icon: '💉', label: '临床数据', count: 12, color: '#fee2e2' },
        { id: 'fda', icon: '🏛️', label: 'FDA 动态', count: 8, color: '#dbeafe' },
        { id: 'tech', icon: '💻', label: '科技前沿', count: 56, color: '#f3e8ff' },
        { id: 'pharma', icon: '💊', label: '制药公司', count: 42, color: '#fef08a' }
    ];

    gridEl.innerHTML = cats.map(c => `
        <div class="category-card" onclick="document.getElementById('global-search-input').value='${c.label}'; handleGlobalSearch(new Event('submit'));" style="border-left: 4px solid ${c.color}">
            <div class="category-icon">${c.icon}</div>
            <div class="category-info">
                <h3>${c.label}</h3>
                <span class="category-count">${c.count} 条相关</span>
            </div>
        </div>
    `).join('');
}




// =====================================================
//  Analysis
// =====================================================
async function loadAnalysis() {
    const ticker = document.getElementById('analysis-filter-ticker').value;
    const sentiment = document.getElementById('analysis-filter-sentiment').value;
    const impact_level = document.getElementById('analysis-filter-impact').value;
    const container = document.getElementById('analysis-list');

    try {
        const analyses = await API.getAnalysis({ ticker, sentiment, impact_level, limit: 100 });
        await populateTickerFilters();

        if (analyses.length === 0) {
            container.innerHTML = emptyState('🔍', '暂无分析结果，先在"概览"页点击"立即采集"');
            return;
        }

        container.innerHTML = analyses.map((a, i) => `
            <div class="analysis-item">
                <div class="analysis-header" onclick="toggleDetail(${i})">
                    <div class="analysis-summary-row">
                        <div class="news-sentiment ${a.sentiment}" style="width:32px;height:32px;font-size:16px;border-radius:8px;">
                            ${sentimentIcon(a.sentiment)}
                        </div>
                        <span class="news-ticker">${a.ticker}</span>
                        <span class="analysis-title">${escHtml(a.news_title)}</span>
                    </div>
                    <div class="analysis-badges">
                        <span class="badge badge-${a.sentiment}">${sentimentLabel(a.sentiment)}</span>
                        ${a.impact_level === 'high' ? '<span class="badge badge-high">⚡ HIGH</span>' : ''}
                        <span class="badge badge-level">L${a.level}</span>
                    </div>
                </div>
                <div class="analysis-detail" id="detail-${i}">
                    <div style="margin-bottom: 12px;">
                        <strong>中文摘要:</strong>
                        <p style="color: var(--text-secondary); margin-top: 4px;">${escHtml(a.summary_cn || '无')}</p>
                    </div>
                    <div style="margin-bottom: 10px;">
                        <span style="font-size: 12px; color: var(--text-muted);">置信度</span>
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: ${(a.confidence * 100)}%"></div>
                        </div>
                        <span style="font-size: 11px; color: var(--text-muted);">${(a.confidence * 100).toFixed(0)}%</span>
                    </div>
                    ${a.detailed_analysis ? renderDetailedAnalysis(a.detailed_analysis) : ''}
                    ${a.related_tickers?.length ? `
                        <div style="margin-top: 12px;">
                            <span style="font-size: 11px; color: var(--text-muted); text-transform: uppercase;">关联股票</span>
                            <div class="related-tickers">
                                ${a.related_tickers.map(t => `<span class="ticker-tag">${t}</span>`).join('')}
                            </div>
                        </div>
                    ` : ''}
                    ${a.key_dates?.length ? `
                        <div style="margin-top: 10px;">
                            <span style="font-size: 11px; color: var(--text-muted); text-transform: uppercase;">关注日期</span>
                            <ul style="margin-top: 4px; padding-left: 16px; color: var(--text-secondary); font-size: 12px;">
                                ${a.key_dates.map(d => `<li>${escHtml(d)}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                </div>
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = `<div class="empty-state"><p>加载失败: ${e.message}</p></div>`;
    }
}

function toggleDetail(index) {
    const el = document.getElementById(`detail-${index}`);
    if (el) el.classList.toggle('open');
}

function renderDetailedAnalysis(da) {
    if (!da) return '';
    return `
        <div class="detail-grid">
            ${da.expected_change ? `<div class="detail-block"><h4>📈 预期变化</h4><p style="color:var(--bullish); font-weight:600;">${escHtml(da.expected_change)}</p></div>` : ''}
            ${da.potential_volatility ? `<div class="detail-block"><h4>📉 潜在波动</h4><p>${escHtml(da.potential_volatility)}</p></div>` : ''}
            ${da.direct_impact ? `<div class="detail-block" style="grid-column: 1 / -1; margin-top:8px;"><h4>📊 核心影响</h4><p>${escHtml(da.direct_impact)}</p></div>` : ''}
        </div>
        ${da.target_range ? `
            <div class="detail-block-focus" style="margin-top: 12px;">
                <h4>🎯 交易区间</h4>
                <p>${escHtml(da.target_range)}</p>
            </div>
        ` : ''}
        ${da.risk_factors?.length ? `
            <div style="margin-top: 12px;">
                <span style="font-size: 11px; color: var(--text-muted); text-transform: uppercase;">⚠️ 风险因素</span>
                <ul style="margin-top: 4px; padding-left: 16px; color: var(--bearish); font-size: 12px;">
                    ${da.risk_factors.map(r => `<li>${escHtml(r)}</li>`).join('')}
                </ul>
            </div>
        ` : ''}
    `;
}


// =====================================================
//  Watchlist
// =====================================================
async function loadWatchlist() {
    const container = document.getElementById('watchlist-grid');

    try {
        const companies = await API.getWatchlist();

        if (companies.length === 0) {
            container.innerHTML = emptyState('📋', '关注列表为空，添加你关注的公司');
            return;
        }

        container.innerHTML = companies.map(c => `
            <div class="company-card">
                <div class="company-ticker">${c.ticker}</div>
                <div class="company-name">${escHtml(c.name)}</div>
                <div class="company-meta">
                    <span class="badge ${c.priority === 'high' ? 'badge-warning' : 'badge-neutral'}">${c.priority}</span>
                    <span class="badge badge-level">${c.sector}</span>
                    ${c.track_fda ? '<span class="badge badge-bullish">FDA</span>' : ''}
                    ${c.track_trials ? '<span class="badge badge-bullish">临床</span>' : ''}
                    ${!c.is_active ? '<span class="badge badge-bearish">已停用</span>' : ''}
                </div>
                <div class="company-actions">
                    <button class="btn btn-danger btn-sm" onclick="deleteCompany('${c.ticker}')">删除</button>
                </div>
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = `<div class="empty-state"><p>加载失败: ${e.message}</p></div>`;
    }
}

async function addCompany(event) {
    event.preventDefault();
    const ticker = document.getElementById('input-ticker').value.trim();
    const name = document.getElementById('input-name').value.trim();
    const priority = document.getElementById('input-priority').value;

    if (!ticker || !name) return;

    try {
        await API.addCompany({ ticker, name, priority });
        showToast(`✅ 已添加 ${ticker.toUpperCase()}`, 'success');
        document.getElementById('add-company-form').reset();
        loadWatchlist();
        populateTickerFilters(true);
    } catch (e) {
        showToast(`添加失败: ${e.message}`, 'error');
    }
}

async function deleteCompany(ticker) {
    if (!confirm(`确定删除 ${ticker}？`)) return;
    try {
        await API.deleteCompany(ticker);
        showToast(`已删除 ${ticker}`, 'info');
        loadWatchlist();
        populateTickerFilters(true);
    } catch (e) {
        showToast(`删除失败: ${e.message}`, 'error');
    }
}


// =====================================================
//  System
// =====================================================
async function loadSystem() {
    try {
        const [health, jobs] = await Promise.all([
            API.getHealth(),
            API.getJobs(),
        ]);

        // Health
        const healthEl = document.getElementById('health-info');
        healthEl.innerHTML = `
            <div class="health-row">
                <span>整体状态</span>
                <span><span class="status-dot ${health.status === 'ok' ? 'ok' : 'error'}"></span>${health.status}</span>
            </div>
            <div class="health-row">
                <span>数据库 (PostgreSQL)</span>
                <span><span class="status-dot ${health.db === 'connected' ? 'ok' : 'error'}"></span>${health.db}</span>
            </div>
            <div class="health-row">
                <span>缓存 (Redis)</span>
                <span><span class="status-dot ${health.redis === 'connected' ? 'ok' : 'error'}"></span>${health.redis}</span>
            </div>
            <div class="health-row">
                <span>调度器</span>
                <span><span class="status-dot ${health.scheduler === 'running' ? 'ok' : 'error'}"></span>${health.scheduler}</span>
            </div>
            <div class="health-row">
                <span>版本</span>
                <span>${health.version}</span>
            </div>
        `;

        // Scheduler jobs
        const schedulerEl = document.getElementById('scheduler-info');
        schedulerEl.innerHTML = jobs.jobs.map(job => `
            <div class="job-card">
                <div class="job-info">
                    <div class="job-name">${job.name}</div>
                    <div class="job-next">
                        ${job.paused ? '⏸️ 已暂停' : `下次运行: ${formatTime(job.next_run)}`}
                    </div>
                </div>
                <div style="display: flex; gap: 4px;">
                    <button class="btn btn-primary btn-sm" onclick="triggerSchedulerJob('${job.id}')">▶ 执行</button>
                    ${job.paused
                        ? `<button class="btn btn-ghost btn-sm" onclick="resumeSchedulerJob('${job.id}')">▶ 恢复</button>`
                        : `<button class="btn btn-ghost btn-sm" onclick="pauseSchedulerJob('${job.id}')">⏸ 暂停</button>`
                    }
                </div>
            </div>
        `).join('');
    } catch (e) {
        showToast(`加载失败: ${e.message}`, 'error');
    }
}

async function triggerSchedulerJob(jobId) {
    try {
        showToast(`⏳ 正在执行 ${jobId}...`, 'info');
        await API.triggerJob(jobId);
        showToast(`✅ ${jobId} 执行完成`, 'success');
        loadSystem();
    } catch (e) {
        showToast(`执行失败: ${e.message}`, 'error');
    }
}

async function pauseSchedulerJob(jobId) {
    try {
        await API.pauseJob(jobId);
        showToast(`⏸ ${jobId} 已暂停`, 'info');
        loadSystem();
    } catch (e) {
        showToast(`操作失败: ${e.message}`, 'error');
    }
}

async function resumeSchedulerJob(jobId) {
    try {
        await API.resumeJob(jobId);
        showToast(`▶ ${jobId} 已恢复`, 'success');
        loadSystem();
    } catch (e) {
        showToast(`操作失败: ${e.message}`, 'error');
    }
}


// =====================================================
//  Global Actions
// =====================================================
async function triggerFetch() {
    const btn = document.getElementById('btn-fetch');
    btn.disabled = true;
    btn.textContent = '⏳ 采集中...';

    try {
        const result = await API.fetchFinnhub();
        showToast(
            `✅ 采集完成: ${result.new_articles} 条新新闻 (共 ${result.total_fetched} 条)`,
            result.new_articles > 0 ? 'success' : 'info'
        );
        // Refresh current page
        setTimeout(() => loadPageData(currentPage), 2000);
    } catch (e) {
        showToast(`❌ 采集失败: ${e.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '⚡ 立即采集';
    }
}


// =====================================================
//  Ticker Filter Population
// =====================================================
let cachedTickers = null;

async function populateTickerFilters(force = false) {
    if (cachedTickers && !force) return;

    try {
        const companies = await API.getWatchlist();
        cachedTickers = companies.map(c => c.ticker);

        ['news-filter-ticker', 'analysis-filter-ticker'].forEach(id => {
            const select = document.getElementById(id);
            if (!select) return;
            const currentVal = select.value;
            // Keep first option, replace rest
            select.innerHTML = '<option value="">全部公司</option>' +
                cachedTickers.map(t => `<option value="${t}" ${t === currentVal ? 'selected' : ''}>${t}</option>`).join('');
        });
    } catch (e) {
        console.warn('Failed to load tickers:', e);
    }
}


// =====================================================
//  Utilities
// =====================================================
function sentimentIcon(s) {
    switch (s) {
        case 'bullish': return '📈';
        case 'bearish': return '📉';
        case 'neutral': return '➖';
        default: return '📄';
    }
}

function sentimentLabel(s) {
    switch (s) {
        case 'bullish': return '利好';
        case 'bearish': return '利空';
        case 'neutral': return '中性';
        default: return s;
    }
}

function categoryHtml(cat) {
    if (!cat) return '';
    switch(cat) {
        case 'clinical_trial': return '<span class="badge badge-cat-clinical">🔬 临床数据</span>';
        case 'fda_approval': return '<span class="badge badge-cat-fda">🏛️ FDA审批</span>';
        case 'regulatory': return '<span class="badge badge-cat-regulatory">⚖️ 监管政策</span>';
        case 'earnings': return '<span class="badge badge-cat-general">💰 财报</span>';
        case 'breaking': return '<span class="badge badge-cat-breaking">⚡ 突发大新闻</span>';
        default: return `<span class="badge badge-cat-general">📰 ${cat.toUpperCase()}</span>`;
    }
}

function escHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function timeAgo(dateStr) {
    if (!dateStr) return '';
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return '刚刚';
    if (mins < 60) return `${mins} 分钟前`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours} 小时前`;
    const days = Math.floor(hours / 24);
    return `${days} 天前`;
}

function formatTime(isoStr) {
    if (!isoStr) return '—';
    const d = new Date(isoStr);
    return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function emptyState(icon, text) {
    return `<div class="empty-state"><div class="empty-icon">${icon}</div><p>${text}</p></div>`;
}

function showToast(msg, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = msg;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}


// =====================================================
//  Init
// =====================================================
document.addEventListener('DOMContentLoaded', async () => {
    // Nav click handlers
    document.querySelectorAll('.nav-item').forEach(el => {
        el.addEventListener('click', (e) => {
            e.preventDefault();
            navigateTo(el.dataset.page);
        });
    });

    try {
        const res = await fetch('/api/health', { signal: AbortSignal.timeout(2000) });
        if (!res.ok) throw new Error('Backend responded with error');
        isMockMode = false;
    } catch {
        isMockMode = true;
        console.log('🔶 Backend unreachable, using mock data');
        // Update live indicator
        const liveDot = document.querySelector('.live-dot');
        if (liveDot) liveDot.style.background = '#f59e0b';
        const liveText = document.querySelector('.live-indicator span:last-child');
        if (liveText) liveText.textContent = 'Mock 模式';
    }

    // Load initial page
    navigateTo('dashboard');

    if (isMockMode) {
        showToast('📋 Mock 模式 — 使用示例数据预览', 'info');
    }

    // Auto-refresh every 5 minutes (only in live mode)
    setInterval(() => {
        if (!isMockMode) {
            refreshCurrentPage();
        }
    }, 5 * 60 * 1000);
});

// Global Search logic
window.handleGlobalSearch = function(e) {
    e.preventDefault();
    const input = document.getElementById('global-search-input');
    const ticker = input.value.trim().toUpperCase();
    if (!ticker) return;

    // Navigate to Trending (news)
    navigateTo('news');
    
    // Set the filter and load
    setTimeout(() => {
        const filterSelect = document.getElementById('news-filter-ticker');
        if (filterSelect) {
            // Include option if missing
            if (![...filterSelect.options].some(opt => opt.value === ticker)) {
                filterSelect.insertAdjacentHTML('beforeend', `<option value="${ticker}">${ticker}</option>`);
            }
            filterSelect.value = ticker;
            loadNews();
            // Optional: reset input
            input.value = '';
        }
    }, 100);
};

// Sidebar Toggle logic
window.toggleSidebar = function() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.classList.toggle('collapsed');
    }
};
