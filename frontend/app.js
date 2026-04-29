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
    fetchPolygon(h) { return this.request(`/api/fetch/polygon?hours_back=${h||2}`, { method: 'POST' }); },
    fetchRTPR() { return this.request('/api/fetch/rtpr', { method: 'POST' }); },
    fetchEDGAR() { return this.request('/api/fetch/edgar', { method: 'POST' }); },

    // Sectors
    getSectors() { return this.request('/api/sectors'); },
    getSectorCompanies(name) { return this.request(`/api/sector-companies/${encodeURIComponent(name)}`); },
    getCompanyNews(t) { return this.request(`/api/news?ticker=${t}&limit=20`); },
    getMarketOverview() { return this.request('/api/market/overview'); },
    getConceptCompanies(id) { return this.request(`/api/concepts/${id}/companies`); },
    getChart(ticker, days) { return this.request(`/api/market/chart/${ticker}?days=${days||30}`); },
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
        case 'scanner':   loadScannerPage(); break;
        case 'dashboard': loadDashboard(); break;
        case 'latest':    loadLatest(); break;
        case 'categories': loadCategories(); break;
        case 'analysis':  loadAnalysis(); break;
        case 'backtest':  loadBacktestPage(); break;
        case 'watchlist': loadWatchlist(); break;
        case 'system':    loadSystem(); break;
        case 'trend':     loadTrendScanner(); break;
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

let _marketData = null;
let _marketTab  = 'sectors';

async function loadCategories() {
    const el = document.getElementById('category-grid');
    if (!el) return;
    // If data already cached, just re-render current tab
    if (_marketData) { renderMarketTab(el, _marketData, _marketTab); return; }

    // Show loading with progress hint
    el.innerHTML = `
        <div style="text-align:center;padding:40px 20px">
            <div style="font-size:32px;margin-bottom:12px">📊</div>
            <div style="font-size:15px;font-weight:600;color:var(--text-primary);margin-bottom:6px">正在加载行情数据</div>
            <div style="font-size:12px;color:var(--text-muted);margin-bottom:20px">首次加载约 5-10 秒，之后缓存 1 小时</div>
            <div class="market-loading-bar"><div class="market-loading-fill"></div></div>
        </div>`;

    try {
        // Add 30s timeout to prevent infinite hang
        const controller = new AbortController();
        const tid = setTimeout(() => controller.abort(), 30000);
        _marketData = await API.getMarketOverview();
        clearTimeout(tid);
        renderMarketTab(el, _marketData, _marketTab);
    } catch(e) {
        const msg = e.name === 'AbortError' ? '请求超时，请刷新重试' : e.message;
        el.innerHTML = `
            <div style="text-align:center;padding:60px 20px">
                <div style="font-size:32px;margin-bottom:12px">⚠️</div>
                <div style="font-size:14px;font-weight:600;color:var(--bearish);margin-bottom:8px">加载失败</div>
                <div style="font-size:12px;color:var(--text-muted);margin-bottom:16px">${msg}</div>
                <button onclick="loadCategories()" style="padding:8px 20px;border-radius:8px;background:var(--accent);color:white;border:none;cursor:pointer;font-size:13px">🔄 重试</button>
            </div>`;
    }
}

function switchMarketTab(tab) {
    _marketTab = tab;
    // Update tab button states
    document.querySelectorAll('.mtab').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });
    const el = document.getElementById('category-grid');
    if (!el) return;
    if (_marketData) {
        renderMarketTab(el, _marketData, tab);
    }
}

function renderMarketTab(el, data, tab) {
    el.innerHTML = '';
    if (tab === 'sectors')  renderSectorsTab(el, data);
    if (tab === 'concepts') renderConceptsTab(el, data);
    if (tab === 'styles')   renderStylesTab(el, data);
}

// ------- Market Tab Renderers --------
let _moConceptsShowAll = false;

function renderSectorsTab(el, data) {
    const allSectors = data.sectors || [];

    // Only show sectors that have companies, put 综合类 last
    const active = allSectors.filter(s => s.company_count > 0 && s.name !== '综合类');
    const misc = allSectors.filter(s => s.name === '综合类' && s.company_count > 0);

    // Group by group field
    const groups = {};
    active.forEach(s => {
        const g = s.group || '其他';
        if (!groups[g]) groups[g] = [];
        groups[g].push(s);
    });

    // Sort bar
    let _sortedSectors = [...active];
    const sortBar = buildSortBar(key => {
        if (key === 'up')      _sortedSectors.sort((a,b) => (b.change_pct||0) - (a.change_pct||0));
        if (key === 'down')    _sortedSectors.sort((a,b) => (a.change_pct||0) - (b.change_pct||0));
        if (key === 'default') _sortedSectors = [...active];
        renderFlat(_sortedSectors);
    });
    el.appendChild(sortBar);

    // Container for sector groups
    const wrap = document.createElement('div');
    wrap.style.cssText = 'padding:0 14px 8px';
    el.appendChild(wrap);

    // Flat sort render (after sort button)
    let _isSorted = false;
    function renderFlat(sectors) {
        _isSorted = true;
        wrap.innerHTML = '';
        const grid = document.createElement('div');
        grid.style.cssText = 'display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px;padding:8px 0';
        sectors.forEach(s => appendSectorCard(grid, s));
        wrap.appendChild(grid);
    }

    function renderGrouped(groupMap) {
        _isSorted = false;
        wrap.innerHTML = '';
        const GROUP_ORDER = ['科技','新能源','医疗','金融','能源','材料','消费','工业','建筑地产','农业','文化','通信','综合'];
        const orderedGroups = [...new Set([...GROUP_ORDER.filter(g => groupMap[g]), ...Object.keys(groupMap)])];
        orderedGroups.forEach(grp => {
            const sectors = groupMap[grp];
            if (!sectors?.length) return;
            // Group header
            const header = document.createElement('div');
            header.style.cssText = 'font-size:12px;font-weight:700;color:var(--text-muted);letter-spacing:0.06em;text-transform:uppercase;margin:18px 0 8px;padding-bottom:6px;border-bottom:1px solid var(--border)';
            header.textContent = `${grp}  ·  ${sectors.length} 个板块`;
            wrap.appendChild(header);
            // Cards grid
            const grid = document.createElement('div');
            grid.style.cssText = 'display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px;margin-bottom:4px';
            sectors.forEach(s => appendSectorCard(grid, s));
            wrap.appendChild(grid);
        });
    }

    function appendSectorCard(grid, s) {
        const card = document.createElement('div');
        const isUp = (s.change_pct || 0) >= 0;
        const color = s.change_pct != null ? (isUp ? '#10b981' : '#ef4444') : 'var(--text-muted)';
        const chgStr = s.change_pct != null ? (isUp ? '+' : '') + s.change_pct + '%' : '--';
        const leaderChgStr = s.leader_change != null ? (s.leader_change > 0 ? '+' : '') + s.leader_change + '%' : '';
        const leaderColor = (s.leader_change || 0) >= 0 ? '#10b981' : '#ef4444';
        card.className = 'sector-card-compact';
        card.style.cssText = `background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:16px;cursor:pointer;transition:all 0.2s;border-left:4px solid ${color}`;
        card.innerHTML = `
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
                <span style="font-size:26px;flex-shrink:0">${s.icon}</span>
                <div style="min-width:0;flex:1">
                    <div style="font-size:14px;font-weight:700;color:var(--text-primary)">${s.name}</div>
                    <div style="font-size:11px;color:var(--text-muted);margin-top:1px">${s.company_count} 家公司</div>
                </div>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:flex-end">
                <div>
                    <div style="font-size:22px;font-weight:800;color:${color};line-height:1">${chgStr}</div>
                    <div style="font-size:10px;color:var(--text-muted);margin-top:3px">平均涨跌</div>
                </div>
                ${s.leader ? `<div style="text-align:right">
                    <div style="font-size:12px;font-weight:700;color:var(--accent)">${s.leader}</div>
                    <div style="font-size:11px;color:${leaderColor};font-weight:600">${leaderChgStr}</div>
                    <div style="font-size:10px;color:var(--text-muted)">领涨</div>
                </div>` : ''}
            </div>`;
        card.onmouseover = () => { card.style.transform = 'translateY(-2px)'; card.style.boxShadow = '0 8px 24px rgba(0,0,0,0.1)'; };
        card.onmouseout  = () => { card.style.transform = ''; card.style.boxShadow = ''; };
        card.onclick = () => handleSectorCardClick(s, card);
        grid.appendChild(card);
    }

    // Initial render: grouped
    renderGrouped(groups);

    // Add 综合类 as collapsible at the bottom
    if (misc.length) {
        const miscHeader = document.createElement('div');
        miscHeader.style.cssText = 'font-size:12px;color:var(--text-muted);margin:18px 0 8px;cursor:pointer;display:flex;align-items:center;gap:8px;user-select:none';
        miscHeader.innerHTML = `<span>🏢 综合类 (${misc[0].company_count} 家未分类)</span><span style="font-size:11px;opacity:0.7">▼ 点击展开</span>`;
        let miscExpanded = false;
        const miscGrid = document.createElement('div');
        miscGrid.style.cssText = 'display:none;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px;margin-bottom:12px';
        misc.forEach(s => appendSectorCard(miscGrid, s));
        miscHeader.onclick = () => {
            miscExpanded = !miscExpanded;
            miscGrid.style.display = miscExpanded ? 'grid' : 'none';
            miscHeader.querySelector('span:last-child').textContent = miscExpanded ? '▲ 收起' : '▼ 点击展开';
        };
        wrap.appendChild(miscHeader);
        wrap.appendChild(miscGrid);
    }

    // Date note
    const note = document.createElement('div');
    note.className = 'mo-refresh-note';
    note.textContent = '数据日期: ' + data.date + ' · 每小时更新 · ' + active.length + ' 个行业板块';
    el.appendChild(note);
}

function renderConceptsTab(el, data) {
    const concepts = data.concepts || [];
    let defaultConcepts = concepts.filter(c => c.is_default);
    let moreConcepts    = concepts.filter(c => !c.is_default);

    // Sort bar
    const sortBarEl = buildSortBar(key => {
        if (key === 'up')   defaultConcepts.sort((a,b) => (b.change_pct||0) - (a.change_pct||0));
        if (key === 'down') defaultConcepts.sort((a,b) => (a.change_pct||0) - (b.change_pct||0));
        if (key === 'default') {
            defaultConcepts = concepts.filter(c => c.is_default);
        }
        // Re-render rows
        const rowsWrap = document.getElementById('concept-rows-wrap');
        if (rowsWrap) {
            rowsWrap.innerHTML = '';
            defaultConcepts.forEach(c => rowsWrap.appendChild(moRow({
                icon: c.icon, name: c.name, name_en: c.name_en,
                change_pct: c.change_pct, leader: c.leader, leader_change: c.leader_change,
                id: 'concept_' + c.id,
            }, handleConceptClick)));
        }
    });
    _lastSortCallback = sortBarEl._onSort;
    el.appendChild(sortBarEl);
    // Section header
    const hdr = document.createElement('div');
    hdr.className = 'mo-section-header';
    hdr.innerHTML = '<span class="mo-section-title">概念主题</span><span class="mo-section-sub">领涨股</span>';
    el.appendChild(hdr);

    // Default concepts rows
    const rowsWrap = document.createElement('div');
    rowsWrap.id = 'concept-rows-wrap';
    defaultConcepts.forEach(c => {
        rowsWrap.appendChild(moRow({
            icon: c.icon, name: c.name, name_en: c.name_en,
            change_pct: c.change_pct, leader: c.leader, leader_change: c.leader_change,
            id: 'concept_' + c.id,
        }, handleConceptClick));
    });
    el.appendChild(rowsWrap);

    // More toggle
    const morePill = document.createElement('div');
    morePill.className = 'mo-show-more';
    morePill.textContent = `更多 ∨  (${moreConcepts.length} 个主题)`;
    morePill.onclick = () => {
        _moConceptsShowAll = !_moConceptsShowAll;
        morePill.textContent = _moConceptsShowAll ? '收起 ∧' : `更多 ∨  (${moreConcepts.length} 个主题)`;
        const extra = document.getElementById('mo-extra-concepts');
        if (extra) extra.style.display = _moConceptsShowAll ? 'block' : 'none';
    };
    el.appendChild(morePill);

    const extraWrap = document.createElement('div');
    extraWrap.id = 'mo-extra-concepts';
    extraWrap.style.display = 'none';
    moreConcepts.forEach(c => {
        extraWrap.appendChild(moRow({
            icon: c.icon, name: c.name, name_en: c.name_en,
            change_pct: c.change_pct, leader: c.leader, leader_change: c.leader_change,
            id: 'concept_' + c.id,
        }, handleConceptClick));
    });
    el.appendChild(extraWrap);

    const note = document.createElement('div');
    note.className = 'mo-refresh-note';
    note.textContent = '数据日期: ' + data.date;
    el.appendChild(note);
}

function renderStylesTab(el, data) {
    const hdr = document.createElement('div');
    hdr.className = 'mo-section-header';
    hdr.innerHTML = '<span class="mo-section-title">风格 ETF</span><span class="mo-section-sub">代表指数</span>';
    el.appendChild(hdr);

    (data.styles || []).forEach(s => {
        el.appendChild(moRow({
            icon: s.icon, name: s.name, name_en: s.name_en,
            change_pct: s.change_pct, leader: s.ticker,
            leader_change: s.change_pct, id: 'style_' + s.ticker,
            etf: s.ticker,
        }, handleStyleClick));
    });

    const note = document.createElement('div');
    note.className = 'mo-refresh-note';
    note.textContent = '数据日期: ' + data.date;
    el.appendChild(note);
}
// Drill-down: show companies for a sector/concept
async function handleSectorClick(r, rowEl) {
    toggleMoDrill(r.id, r.name, rowEl, async () => {
        return await API.getSectorCompanies(r.name);
    });
}

// Card-style sector click (for the sectors tab grid)
let _activeSectorCard = null;
async function handleSectorCardClick(s, cardEl) {
    // Remove any existing drill panel
    const existing = document.getElementById('sector-drill-container');
    if (existing) existing.remove();

    // Toggle off if same card clicked
    if (_activeSectorCard === s.name) {
        _activeSectorCard = null;
        document.querySelectorAll('.sector-card-active').forEach(c => c.classList.remove('sector-card-active'));
        return;
    }
    _activeSectorCard = s.name;
    document.querySelectorAll('.sector-card-active').forEach(c => c.classList.remove('sector-card-active'));
    cardEl.classList.add('sector-card-active');

    // Find the grid that contains this card, insert drill panel after the grid
    const grid = cardEl.parentElement;
    const drillEl = document.createElement('div');
    drillEl.id = 'sector-drill-container';
    drillEl.style.cssText = `
        grid-column: 1 / -1;
        background: var(--bg-card);
        border: 1px solid var(--accent);
        border-radius: 12px;
        padding: 16px 20px;
        margin-top: 4px;
        margin-bottom: 8px;
        animation: slideDown 0.2s ease;
    `;

    // Insert drill panel after the grid (not inside it)
    grid.insertAdjacentElement('afterend', drillEl);
    drillEl.innerHTML = `<div style="padding:8px;color:var(--text-muted);display:flex;align-items:center;gap:8px">
        <div class="loading-placeholder" style="padding:0;background:none"></div>加载 ${s.name} 公司...
    </div>`;
    drillEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    try {
        const companies = await API.getSectorCompanies(s.name);

        if (!companies.length) {
            drillEl.innerHTML = `<div style="padding:8px;color:var(--text-muted)">暂无公司数据</div>`;
            return;
        }

        drillEl.innerHTML = `
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
                <div style="font-size:15px;font-weight:700;color:var(--text-primary)">${s.icon} ${s.name} · ${companies.length} 家公司</div>
                <button onclick="
                    document.getElementById('sector-drill-container')?.remove();
                    document.querySelectorAll('.sector-card-active').forEach(c=>c.classList.remove('sector-card-active'));
                    _activeSectorCard=null;
                " style="font-size:13px;color:var(--text-muted);background:none;border:none;cursor:pointer;padding:4px 8px;border-radius:6px;hover:background:var(--bg-hover)">✕ 关闭</button>
            </div>
            <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:8px">
                ${companies.map(c => `
                    <div class="mo-company-chip" data-ticker="${c.ticker}" data-name="${(c.name||'').replace(/"/g,'&quot;')}" onclick="openCompanyNews(this.dataset.ticker, this.dataset.name)">
                        <span class="chip-ticker">${c.ticker}</span>
                        <span style="font-size:10px;color:var(--text-muted);text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:110px">${escHtml((c.name||'').split(' ').slice(0,3).join(' '))}</span>
                        ${c.news_24h > 0 ? `<span style="font-size:10px;color:var(--bullish)">📰${c.news_24h}</span>` : ''}
                    </div>`).join('')}
            </div>`;
    } catch(e) {
        drillEl.innerHTML = `<div style="color:var(--bearish);padding:8px">加载失败: ${e.message}</div>`;
    }
}

async function handleConceptClick(r, rowEl) {
    const conceptId = parseInt(r.id.replace('concept_', ''));
    toggleMoDrill(r.id, r.name, rowEl, async () => {
        return await API.getConceptCompanies(conceptId);
    });
}

// ── moRow: 构建一行数据行（概念/风格 Tab 通用） ──
function moRow(r, clickHandler) {
    const row = document.createElement('div');
    row.className = 'mo-row';
    row.id = 'row_' + r.id;

    const hasPct   = r.change_pct != null;
    const isUp     = hasPct && r.change_pct >= 0;
    const updown   = !hasPct ? 'flat' : (isUp ? 'up' : 'down');
    const chgStr   = !hasPct ? '--' : (isUp ? '+' : '') + r.change_pct + '%';

    const hasLdr   = r.leader != null;
    const isLdrUp  = hasLdr && r.leader_change >= 0;
    const lUpdown  = !hasLdr ? 'flat' : (isLdrUp ? 'up' : 'down');
    const lChgStr  = !hasLdr ? '' : (isLdrUp ? '+' : '') + r.leader_change + '%';

    row.innerHTML = `
        <span class="mo-name"><span class="mo-icon">${r.icon || ''}</span>${escHtml(r.name)}</span>
        <span class="mo-change ${updown}">${chgStr}</span>
        <div class="mo-divider"></div>
        <span class="mo-leader">${r.leader || '--'}</span>
        <span class="mo-leader-change ${lUpdown}">${lChgStr}</span>`;

    if (clickHandler) {
        row.style.cursor = 'pointer';
        row.addEventListener('click', () => clickHandler(r, row));
    }
    return row;
}

let _drillOpen = null;
async function toggleMoDrill(id, sectionTitle, rowEl, fetcher) {
    // Remove existing drill if same
    const existing = document.getElementById('drill_' + id);
    if (existing) {
        existing.remove();
        _drillOpen = null;
        return;
    }
    // Remove any other open drill
    if (_drillOpen) {
        const old = document.getElementById('drill_' + _drillOpen);
        if (old) old.remove();
    }

    _drillOpen = id;
    const panel = document.createElement('div');
    panel.className = 'mo-drill-panel open';
    panel.id = 'drill_' + id;
    panel.innerHTML = '<div class="loading-placeholder" style="padding:10px">加载中...</div>';
    rowEl.after(panel);

    try {
        const companies = await fetcher();
        if (!companies || companies.length === 0) {
            panel.innerHTML = '<div style="padding:10px;color:var(--text-muted);font-size:12px">暂无数据</div>';
            return;
        }
        panel.innerHTML = `<div class="mo-drill-title">${sectionTitle} · 相关公司</div>
            <div class="mo-company-grid">${companies.map(c => `
                <div class="mo-company-chip" data-ticker="${c.ticker}" data-name="${(c.name||'').replace(/"/g,'&quot;')}" onclick="openCompanyNews(this.dataset.ticker,this.dataset.name)">
                    <span class="chip-ticker">${c.ticker}</span>
                    <span style="font-size:10px;color:var(--text-muted);text-align:center;max-width:90px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escHtml(c.name)}</span>
                    ${c.news_24h > 0 ? `<span style="font-size:10px;color:var(--bullish)">📰${c.news_24h}</span>` : ''}
                </div>`).join('')}
            </div>`;
    } catch(e) {
        panel.innerHTML = `<div style="padding:10px;color:var(--bearish);font-size:12px">加载失败: ${e.message}</div>`;
    }
}


function formatMarketCap(cap) {
    if (!cap) return '';
    if (cap >= 1e12) return `$${(cap/1e12).toFixed(1)}T`;
    if (cap >= 1e9)  return `$${(cap/1e9).toFixed(0)}B`;
    if (cap >= 1e6)  return `$${(cap/1e6).toFixed(0)}M`;
    return '';
}




// =====================================================
//  Analysis
// =====================================================
// =====================================================================
//  AI 分析进度条轮询
// =====================================================================

let _progressTimer = null;

function _updateProgressWidget(p) {
    const widget = document.getElementById('analysis-progress-widget');
    if (!widget) return;

    const isRunning = p.status === 'running';
    const isDone    = p.status === 'done' || p.total === 0;
    const isQuota   = p.status === 'quota_exceeded';

    if (!isRunning && !isQuota) {
        widget.style.display = 'none';
        return;
    }

    widget.style.display = 'block';

    const total     = parseInt(p.total) || 1;
    const completed = parseInt(p.completed) || 0;
    const pct       = Math.min(100, Math.round((completed / total) * 100));

    document.getElementById('apw-bar').style.width    = pct + '%';
    document.getElementById('apw-counts').textContent = `${completed} / ${total}  (${pct}%)`;
    document.getElementById('apw-current').textContent = isQuota
        ? '⚠️ OpenAI 额度耗尽，请充值后重试'
        : (p.current ? `▶ ${p.current}` : '');
    document.getElementById('apw-hi').textContent  = p.high_impact > 0 ? `⚡ ${p.high_impact} 高影响` : '';
    document.getElementById('apw-err').textContent = p.errors > 0     ? `❌ ${p.errors} 错误`      : '';

    if (isQuota) {
        document.getElementById('apw-bar').style.background = 'linear-gradient(90deg,#ef4444,#f97316)';
    }
}

async function pollAnalysisProgress() {
    try {
        const p = await fetch('/api/analysis/progress').then(r => r.json());
        _updateProgressWidget(p);

        if (p.status === 'running') {
            // 每 3 秒刷新一次进度
            _progressTimer = setTimeout(async () => {
                await pollAnalysisProgress();
                // 每完成 20 条刷新一次列表
                const completed = parseInt(p.completed) || 0;
                if (completed > 0 && completed % 20 === 0) loadAnalysis();
            }, 3000);
        } else {
            // 完成 → 刷新列表 + 隐藏进度条
            if (p.status === 'done') {
                setTimeout(() => {
                    document.getElementById('analysis-progress-widget').style.display = 'none';
                    loadAnalysis();
                }, 2000);
            }
            _progressTimer = null;
        }
    } catch (e) {
        // 网络错误静默处理
    }
}

async function loadAnalysis() {
    const ticker = document.getElementById('analysis-filter-ticker').value;
    const sentiment = document.getElementById('analysis-filter-sentiment').value;
    const impact_level = document.getElementById('analysis-filter-impact').value;
    const container = document.getElementById('analysis-list');

    // 自动启动进度轮询（如果没有在跑）
    if (!_progressTimer) pollAnalysisProgress();

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
    btn.textContent = '⏳ Polygon采集中...';
    try {
        const result = await API.fetchPolygon(2);
        showToast(
            `✅ Polygon完成: ${result.new_articles} 条新新闻 (处理 ${result.total_fetched} 条)`,
            result.new_articles > 0 ? 'success' : 'info'
        );
        setTimeout(() => loadPageData(currentPage), 2000);
    } catch (e) {
        showToast(`❌ Polygon失败: ${e.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '⚡ Fetch';
    }
}

async function triggerFetchPolygon24h() {
    const btn = document.getElementById('btn-fetch-polygon24');
    if (btn) { btn.disabled = true; btn.textContent = '⏳ 24h抓取中...'; }
    try {
        const result = await API.fetchPolygon(24);
        showToast(
            `✅ 24h: ${result.new_articles} 条新新闻 (${result.companies_processed} 家公司)`,
            result.new_articles > 0 ? 'success' : 'info'
        );
        setTimeout(() => loadPageData(currentPage), 2000);
    } catch(e) {
        showToast(`❌ 失败: ${e.message}`, 'error');
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = '🔄 24h补抓'; }
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

// ============================================================
//  Sparkline Chart Builder (pure SVG, no dependencies)
// ============================================================
function buildSparkline(chartData) {
    const bars = chartData.bars;
    if (!bars || bars.length < 2) return '';

    const W = 340, H = 80, PAD = 4;
    const closes = bars.map(b => b.close);
    const minP = Math.min(...closes);
    const maxP = Math.max(...closes);
    const range = maxP - minP || 1;

    // Build SVG polyline points
    const pts = closes.map((c, i) => {
        const x = PAD + (i / (closes.length - 1)) * (W - PAD * 2);
        const y = H - PAD - ((c - minP) / range) * (H - PAD * 2);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');

    // Build gradient fill polygon
    const fillPts = `${PAD},${H} ` + pts + ` ${W - PAD},${H}`;

    const isUp = chartData.period_change >= 0;
    const color = isUp ? '#10b981' : '#ef4444';
    const bgColor = isUp ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)';
    const changeSign = isUp ? '+' : '';
    const latest = chartData.latest_close;
    const pctStr = `${changeSign}${chartData.period_change}%`;
    const latestDate = chartData.latest_date;
    const firstDate = bars[0].date;

    // Volume bars (normalized to bottom 15px)
    const vols = bars.map(b => b.volume || 0);
    const maxVol = Math.max(...vols) || 1;
    const volBars = vols.map((v, i) => {
        const x = PAD + (i / (vols.length - 1)) * (W - PAD * 2) - 2;
        const vh = (v / maxVol) * 14;
        const vy = H - vh;
        const bc = bars[i].change_pct >= 0 ? '#10b98140' : '#ef444440';
        return `<rect x="${x.toFixed(1)}" y="${vy.toFixed(1)}" width="4" height="${vh.toFixed(1)}" fill="${bc}"/>`;
    }).join('');

    return `
    <div style="padding:14px 0 10px;border-bottom:1px solid var(--border)">
        <div style="display:flex;align-items:baseline;gap:10px;margin-bottom:8px">
            <span style="font-size:22px;font-weight:800;color:var(--text-primary)">$${latest?.toFixed(2)}</span>
            <span style="font-size:13px;font-weight:600;color:${color};padding:2px 8px;background:${bgColor};border-radius:20px">
                ${pctStr} <span style="font-size:10px;font-weight:400;color:var(--text-muted)">30D</span>
            </span>
            <span style="font-size:11px;color:var(--text-muted);margin-left:auto">${firstDate} → ${latestDate}</span>
        </div>
        <svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" style="overflow:visible;display:block;max-width:100%">
            <defs>
                <linearGradient id="grad-${chartData.ticker.replace(/\./g,'_')}" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="${color}" stop-opacity="0.25"/>
                    <stop offset="100%" stop-color="${color}" stop-opacity="0"/>
                </linearGradient>
            </defs>
            ${volBars}
            <polygon points="${fillPts}" fill="url(#grad-${chartData.ticker.replace(/\./g,'_')})" stroke="none"/>
            <polyline points="${pts}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
            <circle cx="${pts.split(' ').pop().split(',')[0]}" cy="${pts.split(' ').pop().split(',')[1]}" r="3" fill="${color}"/>
        </svg>
        <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--text-muted);margin-top:2px">
            <span>H: $${Math.max(...bars.map(b=>b.high||0)).toFixed(2)}</span>
            <span>L: $${Math.min(...bars.map(b=>b.low||Infinity)).toFixed(2)}</span>
            <span>Vol: ${formatVolume(bars[bars.length-1].volume)}</span>
        </div>
    </div>`;
}

function formatVolume(v) {
    if (!v) return '-';
    if (v >= 1e9) return (v/1e9).toFixed(1) + 'B';
    if (v >= 1e6) return (v/1e6).toFixed(1) + 'M';
    if (v >= 1e3) return (v/1e3).toFixed(0) + 'K';
    return v;
}

// ---- Style ETF click handler ----
// Style ETF descriptions
const STYLE_INFO = {
    "QQQ":  { desc: "追踪 NASDAQ 100 指数，科技成长龙头", tickers: ["AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","AVGO","COST","NFLX"] },
    "XLK":  { desc: "追踪 S&P 500 信息技术板块 ETF",    tickers: ["AAPL","MSFT","NVDA","AVGO","ORCL","AMD","CSCO","ADBE","TXN","INTU"] },
    "VTV":  { desc: "追踪大盘价值型股票",                 tickers: ["BRK.B","JPM","UNH","XOM","JNJ","PG","V","HD","CVX","MRK"] },
    "VYM":  { desc: "追踪高股息率蓝筹股",                 tickers: ["JPM","JNJ","PG","XOM","CVX","PFE","T","VZ","KO","MO"] },
    "IWM":  { desc: "追踪 Russell 2000 小盘股指数",      tickers: ["SAIA","STLD","CLF","RGTI","IONQ","HOOD","OPEN"] },
    "SPY":  { desc: "追踪 S&P 500 标普500全市场指数",    tickers: ["AAPL","MSFT","NVDA","AMZN","META","GOOGL","BRK.B","TSLA","UNH","JPM"] },
    "ICLN": { desc: "追踪全球清洁能源公司",               tickers: ["ENPH","FSLR","CEG","VST","NEE","ETN","ALB"] },
    "XBI":  { desc: "追踪生物科技中小盘公司",             tickers: ["MRNA","CRSP","BEAM","NTLA","EXAS","REGN","VRTX","BIIB"] },
};

async function handleStyleClick(r, rowEl) {
    const etfTicker = r.etf || r.leader || r.name_en;
    const info = STYLE_INFO[etfTicker] || { desc: etfTicker + " ETF", tickers: [] };

    toggleMoDrill(r.id, r.name, rowEl, async () => {
        if (!info.tickers.length) return [];
        // Return company objects for these tickers
        const sectors = await API.getSectors();
        // Build fake company list from known tickers
        return info.tickers.map(t => ({
            ticker: t, name: t, gics_sub_sector: '', news_24h: 0
        }));
    });
}

// ============================================================
//  K线图系统 (Lightweight Charts v4)
// ============================================================
let _chart       = null;
let _candleSeries = null;
let _volSeries    = null;
let _maSeries     = {};
let _chartTicker  = '';
let _chartDays    = 90;
let _chartRawData = [];
let _indicators   = { vol: true, ma5: false, ma10: false, ma20: true, ma50: true, ma60: false };

const MA_COLORS = { ma5:'#f59e0b', ma10:'#3b82f6', ma20:'#10b981', ma50:'#ef4444', ma60:'#a855f7' };

function openChartModal(ticker, companyName) {
    _chartTicker = ticker.toUpperCase();
    document.getElementById('chart-ticker').textContent  = _chartTicker;
    document.getElementById('chart-company').textContent = companyName || '';
    document.getElementById('chart-price-info').textContent = '加载中...';
    document.getElementById('chart-modal').style.display = 'flex';
    document.body.style.overflow = 'hidden';
    _initChart();
    chartSetPeriod(_chartDays, true);
}

function closeChartModal() {
    document.getElementById('chart-modal').style.display = 'none';
    document.body.style.overflow = '';
    if (_chart) { _chart.remove(); _chart = null; _candleSeries = null; _volSeries = null; _maSeries = {}; }
}

function handleChartModalBgClick(e) {
    if (e.target === document.getElementById('chart-modal')) closeChartModal();
}

function _getTheme() {
    const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
    return {
        bg:      isDark ? '#0f1117' : '#ffffff',
        text:    isDark ? '#e2e8f0' : '#1a202c',
        grid:    isDark ? '#1e2030' : '#e2e8f0',
        border:  isDark ? '#2d3748' : '#cbd5e0',
        upColor:   '#10b981',
        downColor: '#ef4444',
    };
}

function _initChart() {
    const container = document.getElementById('chart-container');
    if (!container) return;
    if (_chart) { _chart.remove(); _chart = null; _maSeries = {}; }

    const t = _getTheme();
    _chart = LightweightCharts.createChart(container, {
        width:  container.clientWidth,
        height: container.clientHeight || 420,
        layout: { background: { color: t.bg }, textColor: t.text },
        grid:   { vertLines: { color: t.grid }, horzLines: { color: t.grid } },
        crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
        rightPriceScale: { borderColor: t.border, scaleMarginTop: 0.1, scaleMarginBottom: 0.25 },
        timeScale: { borderColor: t.border, timeVisible: true, secondsVisible: false },
        handleScale: { mouseWheel: true, pinch: true, axisPressedMouseMove: true },
    });

    // Candlestick series
    _candleSeries = _chart.addCandlestickSeries({
        upColor:          t.upColor,   downColor:      t.downColor,
        borderUpColor:    t.upColor,   borderDownColor:t.downColor,
        wickUpColor:      t.upColor,   wickDownColor:  t.downColor,
    });

    // Volume sub-pane
    _volSeries = _chart.addHistogramSeries({
        color: 'rgba(99,102,241,0.4)', priceFormat: { type: 'volume' },
        priceScaleId: 'vol',
    });
    _chart.priceScale('vol').applyOptions({
        scaleMarginTop: 0.8, scaleMarginBottom: 0,
        drawTicks: false, borderVisible: false,
    });

    // Sync visibility
    _volSeries.applyOptions({ visible: _indicators.vol });

    // MA series
    for (const [key, color] of Object.entries(MA_COLORS)) {
        _maSeries[key] = _chart.addLineSeries({
            color, lineWidth: 1, priceLineVisible: false,
            lastValueVisible: false, crosshairMarkerVisible: false,
            visible: _indicators[key],
        });
    }

    // Crosshair price display
    _chart.subscribeCrosshairMove(param => _updatePriceInfo(param));

    // Double-click reset
    container.addEventListener('dblclick', () => _chart.timeScale().fitContent());

    // Resize observer
    const ro = new ResizeObserver(() => {
        if (_chart) _chart.applyOptions({ width: container.clientWidth, height: container.clientHeight });
    });
    ro.observe(container);
}

function _updatePriceInfo(param) {
    if (!_candleSeries) return;
    const el = document.getElementById('chart-price-info');
    if (!param || !param.time || param.seriesData.size === 0) {
        if (_chartRawData.length) {
            const last = _chartRawData[_chartRawData.length - 1];
            const chg = last.close - last.open;
            const pct = (chg / last.open * 100).toFixed(2);
            const sign = chg >= 0 ? '+' : '';
            el.innerHTML = `<span style="font-size:20px;font-weight:800">$${last.close.toFixed(2)}</span>
                <span style="font-size:13px;color:${chg>=0?'#10b981':'#ef4444'};margin-left:6px">${sign}${chg.toFixed(2)} (${sign}${pct}%)</span>
                <span style="font-size:11px;color:var(--text-muted);margin-left:8px">${last.date}</span>`;
        }
        return;
    }
    const d = param.seriesData.get(_candleSeries);
    if (!d) return;
    const chg = d.close - d.open;
    const pct = (chg / d.open * 100).toFixed(2);
    const sign = chg >= 0 ? '+' : '';
    el.innerHTML = `<span style="font-size:16px;font-weight:800">O:${d.open.toFixed(2)} H:${d.high.toFixed(2)} L:${d.low.toFixed(2)} C:${d.close.toFixed(2)}</span>
        <span style="font-size:13px;color:${chg>=0?'#10b981':'#ef4444'};margin-left:8px">${sign}${chg.toFixed(2)} (${sign}${pct}%)</span>`;
}

async function chartSetPeriod(days, init) {
    _chartDays = days;
    document.querySelectorAll('.cpill').forEach(b => b.classList.toggle('active', +b.dataset.days === days));
    if (!_chart) _initChart();

    const priceEl = document.getElementById('chart-price-info');
    if (priceEl) priceEl.textContent = '加载中...';

    try {
        const data = await API.getChart(_chartTicker, days);
        _chartRawData = data.bars || [];

        if (!_chartRawData.length) {
            // Show empty state in chart container
            const container = document.getElementById('chart-container');
            if (container) {
                container.innerHTML = `
                    <div style="height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;color:var(--text-muted)">
                        <div style="font-size:40px">📊</div>
                        <div style="font-size:14px;font-weight:600">${_chartTicker} 暂无价格图表数据</div>
                        <div style="font-size:12px;opacity:0.7">${data.message || '该股票在 Polygon 数据源中无记录'}</div>
                        <div style="font-size:11px;opacity:0.5">可能原因：ADR代码不同 / 场外交易 / 未上市</div>
                    </div>`;
            }
            if (priceEl) priceEl.textContent = '无数据';
            return;
        }

        // Restore chart container if it was replaced by empty state
        const container = document.getElementById('chart-container');
        if (container && !container.querySelector('canvas')) {
            container.innerHTML = '';
            _initChart();
        }

        _applyChartData(_chartRawData);

        // Update title to show actual ticker used (in case alias was applied)
        if (data.ticker && data.ticker !== _chartTicker) {
            const tickerEl = document.getElementById('chart-ticker');
            if (tickerEl) tickerEl.textContent = `${data.ticker} (${_chartTicker})`;
        }
    } catch(e) {
        console.error('Chart fetch error:', e);
        const container = document.getElementById('chart-container');
        if (container) {
            container.innerHTML = `<div style="height:100%;display:flex;align-items:center;justify-content:center;color:var(--bearish);font-size:13px">图表加载失败: ${e.message}</div>`;
        }
    }
}

function _applyChartData(bars) {
    if (!bars.length || !_candleSeries) return;

    const candles = bars.map(b => ({
        time: b.date, open: b.open, high: b.high, low: b.low, close: b.close
    }));
    const volumes = bars.map(b => ({
        time: b.date, value: b.volume || 0,
        color: b.close >= b.open ? 'rgba(16,185,129,0.4)' : 'rgba(239,68,68,0.4)'
    }));

    _candleSeries.setData(candles);
    _volSeries.setData(volumes);

    // Calculate and set MA series
    for (const [key] of Object.entries(MA_COLORS)) {
        const period = parseInt(key.replace('ma', ''));
        const maData = _calcMA(bars, period);
        _maSeries[key].setData(maData);
    }

    _chart.timeScale().fitContent();
    _updatePriceInfo(null);
}

function _calcMA(bars, period) {
    const result = [];
    for (let i = period - 1; i < bars.length; i++) {
        const slice = bars.slice(i - period + 1, i + 1);
        const avg = slice.reduce((s, b) => s + b.close, 0) / period;
        result.push({ time: bars[i].date, value: +avg.toFixed(2) });
    }
    return result;
}

function chartToggle(key) {
    _indicators[key] = !_indicators[key];
    const btn = document.querySelector(`.cindic[data-key="${key}"]`);
    if (btn) btn.classList.toggle('active', _indicators[key]);
    if (key === 'vol' && _volSeries)    _volSeries.applyOptions({ visible: _indicators[key] });
    if (key !== 'vol' && _maSeries[key]) _maSeries[key].applyOptions({ visible: _indicators[key] });
}

// ============================================================
//  排序功能 Sort
// ============================================================
let _sortKey = 'default';   // 'default' | 'up' | 'down'

function buildSortBar(onSort) {
    const bar = document.createElement('div');
    bar.className = 'mo-sort-bar';
    bar.innerHTML = `
        <span>排序:</span>
        <button class="sort-btn active" data-s="default" onclick="applySort('default')">默认</button>
        <button class="sort-btn" data-s="up"      onclick="applySort('up')">涨幅 ↑</button>
        <button class="sort-btn" data-s="down"    onclick="applySort('down')">跌幅 ↓</button>`;
    bar._onSort = onSort;
    return bar;
}
let _lastSortCallback = null;

function applySort(key) {
    _sortKey = key;
    document.querySelectorAll('.sort-btn').forEach(b => b.classList.toggle('active', b.dataset.s === key));
    if (_lastSortCallback) _lastSortCallback(key);
}

// ============================================================
//  修复: openCompanyNews → openCompanyChart (打开K线图)
// ============================================================
function openCompanyNews(ticker, companyName) {
    // If LightweightCharts is loaded, show chart; fallback to news page
    if (typeof LightweightCharts !== 'undefined') {
        openChartModal(ticker, companyName || ticker);
    } else {
        showPage('news');
        setTimeout(() => {
            const inp = document.getElementById('global-search-input');
            if (inp) inp.value = ticker;
            loadNews(ticker);
        }, 100);
    }
}

// =====================================================================
//  盘前 Scanner — P5
// =====================================================================

let _scannerData = [];    // 当前加载的信号数据（全量，用于前端筛选）
let _scannerFilter = '';  // 当前激活的信号类型筛选

async function loadScannerPage() {
    document.getElementById('scanner-date-label').textContent =
        '正在加载 ' + new Date().toLocaleString('zh-CN', { timeZone: 'America/New_York', hour12: false }) + ' ET';
    await refreshScanner();
}

async function refreshScanner() {
    const list = document.getElementById('scanner-list');
    if (!list) return;
    list.innerHTML = '<div class="loading-placeholder">拉取最新信号...</div>';

    const minScore = document.getElementById('scanner-min-score')?.value ?? 0;

    try {
        const res = await fetch(`/api/signals/today?min_final_score=${minScore}&min_event_score=0&limit=100`);
        const data = await res.json();
        _scannerData = data.signals || [];
        _updateScannerBadges(_scannerData);
        _renderScannerList(_scannerData, _scannerFilter);

        const now = new Date().toLocaleString('zh-CN', { timeZone: 'America/New_York', hour12: false });
        document.getElementById('scanner-date-label').textContent =
            `今日信号（美东时间 ${now}）｜共 ${_scannerData.length} 条`;

    } catch (e) {
        list.innerHTML = `<div class="loading-placeholder" style="color:var(--bearish)">加载失败: ${e.message}</div>`;
    }
}

function filterScanner(btn, signal) {
    document.querySelectorAll('.sfil').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    _scannerFilter = signal;
    _renderScannerList(_scannerData, signal);
}

function _updateScannerBadges(signals) {
    const counts = { BUY_ON_VWAP_HOLD: 0, WAIT_FOR_PULLBACK: 0, WATCH_ONLY: 0, WATCH_SYMPATHY: 0, AVOID: 0 };
    signals.forEach(s => { if (counts[s.signal] !== undefined) counts[s.signal]++; });

    document.getElementById('sbadge-total').textContent = `${signals.length} 条信号`;
    document.getElementById('sbadge-buy').textContent   = `✅ BUY ${counts.BUY_ON_VWAP_HOLD}`;
    document.getElementById('sbadge-wait').textContent  = `⏳ WAIT ${counts.WAIT_FOR_PULLBACK}`;
    document.getElementById('sbadge-watch').textContent = `👁 WATCH ${counts.WATCH_ONLY + counts.WATCH_SYMPATHY}`;
    document.getElementById('sbadge-avoid').textContent = `❌ AVOID ${counts.AVOID}`;
}

function _renderScannerList(signals, filter) {
    const list = document.getElementById('scanner-list');
    const filtered = filter ? signals.filter(s => s.signal === filter) : signals;

    if (!filtered.length) {
        list.innerHTML = '<div class="loading-placeholder">暂无符合条件的信号（尝试降低综合分门槛）</div>';
        return;
    }

    list.innerHTML = filtered.map((s, idx) => _buildSignalCard(s, idx)).join('');
}

function _fmt(val, suffix = '', decimals = 1, na = '—') {
    if (val == null || val === undefined) return na;
    return `${parseFloat(val).toFixed(decimals)}${suffix}`;
}

function _signalLabelClass(signal) {
    return `slabel-${signal || 'AVOID'}`;
}

function _buildSignalCard(s, idx) {
    const signal = s.signal || 'AVOID';
    const scores = { event: s.event_score, market: s.market_score, risk: s.risk_score, final: s.final_score };
    const mkt = s.market || {};

    // 行情数据行
    const mktParts = [];
    if (mkt.premarket_gap_pct != null) {
        const cls = mkt.premarket_gap_pct > 0 ? 'pos' : 'neg';
        mktParts.push(`<span class="mkt-item"><span class="mkt-label">盘前涨幅</span><span class="mkt-val ${cls}">${mkt.premarket_gap_pct > 0 ? '+' : ''}${_fmt(mkt.premarket_gap_pct, '%')}</span></span>`);
    }
    if (mkt.rel_volume != null) {
        mktParts.push(`<span class="mkt-item"><span class="mkt-label">相对成交量</span><span class="mkt-val">${_fmt(mkt.rel_volume, 'x')}</span></span>`);
    }
    if (mkt.spy_change_pct != null) {
        const cls = mkt.spy_change_pct > 0 ? 'pos' : 'neg';
        mktParts.push(`<span class="mkt-item"><span class="mkt-label">SPY</span><span class="mkt-val ${cls}">${mkt.spy_change_pct > 0 ? '+' : ''}${_fmt(mkt.spy_change_pct, '%')}</span></span>`);
    }
    if (mkt.qqq_change_pct != null) {
        const cls = mkt.qqq_change_pct > 0 ? 'pos' : 'neg';
        mktParts.push(`<span class="mkt-item"><span class="mkt-label">QQQ</span><span class="mkt-val ${cls}">${mkt.qqq_change_pct > 0 ? '+' : ''}${_fmt(mkt.qqq_change_pct, '%')}</span></span>`);
    }
    if (mkt.current_price != null) {
        mktParts.push(`<span class="mkt-item"><span class="mkt-label">价格</span><span class="mkt-val">$${_fmt(mkt.current_price, '', 2)}</span></span>`);
    }
    if (mkt.vwap != null) {
        mktParts.push(`<span class="mkt-item"><span class="mkt-label">VWAP</span><span class="mkt-val">$${_fmt(mkt.vwap, '', 2)}</span></span>`);
    }

    // 联动股标签
    const sympathy = (s.sympathy_tickers || []).slice(0, 5).map(t =>
        `<span class="sympathy-tag" onclick="openChartModal('${t}')">${t}</span>`
    ).join('');
    const etfs = (s.sector_etfs || []).map(t =>
        `<span class="sympathy-tag etf-tag">${t}</span>`
    ).join('');

    const publishedAt = s.published_at ? new Date(s.published_at).toLocaleString('zh-CN', { timeZone: 'America/New_York' }) : '';

    return `
<div class="signal-card sig-${signal}" id="sc-${idx}">
    <div class="signal-card-header">
        <div class="signal-ticker-block">
            <span class="signal-ticker" onclick="openChartModal('${s.ticker}')">${s.ticker}</span>
            <span class="signal-company" title="${s.company_name}">${s.company_name}</span>
        </div>
        <div class="signal-main">
            <div class="signal-top-row">
                <span class="signal-label ${_signalLabelClass(signal)}">${s.signal_label || signal}</span>
                ${s.conviction_level ? `<span class="badge badge-level">${s.conviction_level}</span>` : ''}
                ${s.sentiment === 'bullish' ? '<span class="badge badge-bullish">🟢 利好</span>' : s.sentiment === 'bearish' ? '<span class="badge badge-bearish">🔴 利空</span>' : ''}
                <span style="font-size:10px;color:var(--text-muted);margin-left:auto">${publishedAt}</span>
            </div>
            <div class="signal-headline">${s.news_title}</div>
            ${s.summary_cn ? `<div class="signal-summary">${s.summary_cn}</div>` : ''}
        </div>
    </div>

    <!-- 四维评分 -->
    <div class="signal-scores">
        <span style="font-size:10px;color:var(--text-muted);font-weight:600">评分</span>
        <div class="score-pill sp-event"><span class="s-label">事件</span><span class="s-value">${scores.event ?? '—'}</span></div>
        <div class="score-pill sp-market"><span class="s-label">行情</span><span class="s-value">${scores.market ?? '—'}</span></div>
        <div class="score-pill sp-risk"><span class="s-label">风险</span><span class="s-value">${scores.risk ?? '—'}</span></div>
        <div class="score-pill sp-final"><span class="s-label">综合</span><span class="s-value">${scores.final ?? '—'}</span></div>
        ${s.price_move_estimate ? `<span style="font-size:11px;color:var(--text-muted);margin-left:8px">预期波幅: <strong>${s.price_move_estimate}</strong></span>` : ''}
    </div>

    <!-- 行情数据 -->
    ${mktParts.length ? `<div class="signal-market-row">${mktParts.join('')}</div>` : ''}

    <!-- 展开按钮 -->
    <button class="signal-expand-btn" onclick="_toggleSignalRules(${idx})">
        <span>📋 交易规则 / 联动股</span>
        <span id="sc-arrow-${idx}">▼</span>
    </button>

    <!-- 交易规则展开区 -->
    <div class="signal-rules" id="sc-rules-${idx}">
        ${s.entry_rule ? `<div class="rule-row"><span class="rule-icon">🎯</span><span class="rule-text"><strong>入场：</strong>${s.entry_rule}</span></div>` : ''}
        ${s.stop_loss_rule ? `<div class="rule-row"><span class="rule-icon">🛡️</span><span class="rule-text"><strong>止损：</strong>${s.stop_loss_rule}</span></div>` : ''}
        ${s.reason_cn ? `<div class="rule-row"><span class="rule-icon">💡</span><span class="rule-text">${s.reason_cn}</span></div>` : ''}
        ${s.action_suggestion ? `<div class="rule-row"><span class="rule-icon">📌</span><span class="rule-text">${s.action_suggestion}</span></div>` : ''}
        ${(sympathy || etfs) ? `
        <div class="sympathy-row">
            <span class="sympathy-label">联动标的：</span>
            ${sympathy}
            ${etfs}
        </div>` : ''}
    </div>
</div>`;
}

function _toggleSignalRules(idx) {
    const rules = document.getElementById(`sc-rules-${idx}`);
    const arrow = document.getElementById(`sc-arrow-${idx}`);
    if (!rules) return;
    rules.classList.toggle('open');
    arrow.textContent = rules.classList.contains('open') ? '▲' : '▼';
}

// =====================================================================
//  回测统计页面 — P4
// =====================================================================

async function loadBacktestPage() {
    const container = document.getElementById('backtest-content');
    if (!container) return;
    container.innerHTML = '<div class="loading-placeholder">加载回测数据...</div>';

    try {
        const res = await fetch('/api/signals/backtest/stats');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        if (!data.total) {
            container.innerHTML = `
            <div class="backtest-empty">
                <div class="empty-icon">📊</div>
                <p>暂无完整回测数据。<br>系统会在每个交易日收盘后（美东21:00）自动回填价格数据。<br>至少需要5个交易日才能生成第一批完整统计。</p>
            </div>`;
            return;
        }

        container.innerHTML = `
        <!-- 整体胜率统计 -->
        <div class="backtest-stats-grid">
            <div class="bt-stat">
                <span class="bt-val neutral">${data.total}</span>
                <span class="bt-label">总事件数</span>
            </div>
            <div class="bt-stat">
                <span class="bt-val ${data.win_rate_day1 >= 50 ? 'pos' : 'neg'}">${data.win_rate_day1}%</span>
                <span class="bt-label">第1日胜率</span>
            </div>
            <div class="bt-stat">
                <span class="bt-val ${data.win_rate_day5 >= 50 ? 'pos' : 'neg'}">${data.win_rate_day5}%</span>
                <span class="bt-label">第5日胜率</span>
            </div>
            <div class="bt-stat">
                <span class="bt-val ${(data.avg_return_day1 || 0) >= 0 ? 'pos' : 'neg'}">${data.avg_return_day1 != null ? data.avg_return_day1 + '%' : '—'}</span>
                <span class="bt-label">平均第1日收益</span>
            </div>
        </div>
        <div class="backtest-stats-grid">
            <div class="bt-stat">
                <span class="bt-val neg">${data.gap_fade_rate}%</span>
                <span class="bt-label">高开低走率</span>
            </div>
            <div class="bt-stat">
                <span class="bt-val pos">${data.continuation_rate}%</span>
                <span class="bt-label">开盘续涨率</span>
            </div>
            <div class="bt-stat">
                <span class="bt-val ${(data.avg_return_day5 || 0) >= 0 ? 'pos' : 'neg'}">${data.avg_return_day5 != null ? data.avg_return_day5 + '%' : '—'}</span>
                <span class="bt-label">平均5日收益</span>
            </div>
            <div class="bt-stat">
                <span class="bt-val neutral">${((data.total - (data.total * data.win_rate_day1 / 100)) | 0)}</span>
                <span class="bt-label">亏损事件数</span>
            </div>
        </div>

        <!-- 按事件类型统计 -->
        <div class="backtest-table-section">
            <h3>📋 按事件类型统计</h3>
            <table class="bt-table">
                <thead><tr><th>事件类型</th><th>事件数</th><th>第1日胜率</th><th>平均第1日收益</th></tr></thead>
                <tbody>
                ${(data.by_category || []).map(row => `
                <tr>
                    <td class="cat-name">${row.category}</td>
                    <td>${row.count}</td>
                    <td class="win-rate-cell ${row.win_rate_d1 >= 55 ? 'high' : row.win_rate_d1 < 45 ? 'low' : ''}">${row.win_rate_d1}%</td>
                    <td class="${row.avg_return_d1 >= 0 ? 'bt-val pos' : 'bt-val neg'}" style="font-size:12px">${row.avg_return_d1 > 0 ? '+' : ''}${row.avg_return_d1}%</td>
                </tr>`).join('')}
                </tbody>
            </table>
        </div>

        <!-- 按信号类型统计 -->
        <div class="backtest-table-section">
            <h3>🎯 按信号类型统计</h3>
            <table class="bt-table">
                <thead><tr><th>信号类型</th><th>事件数</th><th>第1日胜率</th><th>平均第1日收益</th></tr></thead>
                <tbody>
                ${(data.by_signal || []).map(row => `
                <tr>
                    <td class="cat-name">${row.signal}</td>
                    <td>${row.count}</td>
                    <td class="win-rate-cell ${row.win_rate_d1 >= 55 ? 'high' : row.win_rate_d1 < 45 ? 'low' : ''}">${row.win_rate_d1}%</td>
                    <td class="${row.avg_return_d1 >= 0 ? 'bt-val pos' : 'bt-val neg'}" style="font-size:12px">${row.avg_return_d1 > 0 ? '+' : ''}${row.avg_return_d1}%</td>
                </tr>`).join('')}
                </tbody>
            </table>
        </div>`;

    } catch (e) {
        container.innerHTML = `<div class="loading-placeholder" style="color:var(--bearish)">加载失败: ${e.message}</div>`;
    }
}

// =====================================================
//  趋势 Scanner
// =====================================================
let _trendData = [];
let _trendStageFilter = '';

async function loadTrendScanner() {
    const list = document.getElementById('trend-list');
    const minScore = document.getElementById('trend-min-score')?.value || 50;
    if (!list) return;
    list.innerHTML = '<div class="loading-placeholder">加载趋势数据...</div>';

    try {
        const data = await API.request(`/api/trend/scanner?min_score=${minScore}&limit=60`);
        _trendData = data.results || [];

        // 大盘上下文
        const ctxEl = document.getElementById('trend-market-ctx');
        if (ctxEl) {
            const q = data.qqq_3m_return;
            const sign = q >= 0 ? '+' : '';
            const color = q >= 0 ? '#10b981' : '#ef4444';
            ctxEl.innerHTML = q !== null ? `
                <span style="background:var(--card-bg);border:1px solid var(--border);border-radius:8px;padding:6px 14px;font-size:12px;">
                    📊 <b>QQQ 3月</b>: <span style="color:${color}">${sign}${q}%</span>
                </span>
                <span style="background:var(--card-bg);border:1px solid var(--border);border-radius:8px;padding:6px 14px;font-size:12px;color:var(--text-muted)">
                    共找到 <b style="color:var(--text-primary)">${data.count}</b> 条趋势股
                </span>` : '';
        }

        renderTrendList();
    } catch (e) {
        list.innerHTML = `<div class="loading-placeholder" style="color:var(--bearish)">加载失败: ${e.message}<br><small>请先点击「更新数据」拉取历史价格</small></div>`;
    }
}

function renderTrendList() {
    const list = document.getElementById('trend-list');
    if (!list) return;

    let items = _trendData;
    if (_trendStageFilter) {
        items = items.filter(r => r.trend_stage === _trendStageFilter);
    }

    if (items.length === 0) {
        list.innerHTML = emptyState('📈', '暂无符合条件的趋势股，尝试降低趋势分门槛');
        return;
    }

    list.innerHTML = items.map(r => renderTrendCard(r)).join('');
}

function renderTrendCard(r) {
    const stageLabel = {
        'strong_uptrend':   '🚀 强趋势',
        'moderate_uptrend': '📈 中趋势',
        'weak_uptrend':     '〰️ 弱趋势',
        'sideways':         '➡️ 横盘',
        'downtrend':        '📉 下降趋势',
    }[r.trend_stage] || r.trend_stage;

    const scoreColor = r.trend_score >= 75 ? '#10b981'
                     : r.trend_score >= 60 ? '#f59e0b'
                     : r.trend_score >= 45 ? '#6366f1' : '#6b7280';

    const maStatus = {
        'price_above_20_50_200': '均线全排列 ✔',
        'price_above_50_200':    'MA50>200 ✔',
        'price_above_200_only':  '仅MA200上方',
        'below_ma200':           '跌破MA200 ⚠️',
    }[r.moving_average_status] || r.moving_average_status;

    const volIcon = r.volume_confirmation === 'positive' ? '✅ 量价健康'
                  : r.volume_confirmation === 'negative' ? '⚠️ 量价异常' : '➖ 中性';

    const hhIcon = (r.higher_high && r.higher_low) ? '↑HH+HL ✔'
                 : r.higher_high ? '↑HH' : r.higher_low ? '↑HL' : '—';

    const entryMap = {
        'buy_on_vwap_hold_or_ma20_hold': '开盘VWAP确认/回踩MA20',
        'wait_for_pullback_to_ma20':     '等回踩MA20',
        'wait_for_vwap_hold':            '等VWAP确认',
        'wait_for_confirmation':         '等待确认',
        'avoid_no_trend':                '暂不操作',
    }[r.best_entry] || r.best_entry;

    const fmt = (v) => v !== null && v !== undefined ? `${v >= 0 ? '+' : ''}${v}%` : '--';
    const retColor = (v) => v !== null && v >= 0 ? '#10b981' : '#ef4444';
    const distColor = r.dist_52w_high_pct !== null && r.dist_52w_high_pct >= -10 ? '#10b981' : '#f59e0b';

    return `
    <div class="scanner-card" onclick="openChartModal('${r.ticker}','')">
        <div class="sc-left">
            <div class="sc-ticker">${r.ticker}</div>
            <div class="sc-signal" style="background:${scoreColor}20; color:${scoreColor}; border:1px solid ${scoreColor}40; border-radius:6px; padding:2px 8px; font-size:11px; font-weight:600; white-space:nowrap;">${stageLabel}</div>
        </div>
        <div class="sc-center">
            <div class="sc-title">${maStatus} &nbsp; ${hhIcon} &nbsp; ${volIcon}</div>
            <div class="sc-meta" style="display:flex; gap:14px; flex-wrap:wrap; margin-top:4px;">
                <span style="font-size:11px; color:var(--text-muted)">1m: <b style="color:${retColor(r.ret_1m)}">${fmt(r.ret_1m)}</b></span>
                <span style="font-size:11px; color:var(--text-muted)">3m: <b style="color:${retColor(r.ret_3m)}">${fmt(r.ret_3m)}</b></span>
                <span style="font-size:11px; color:var(--text-muted)">距52w高: <b style="color:${distColor}">${fmt(r.dist_52w_high_pct)}</b></span>
                <span style="font-size:11px; color:var(--text-muted)">买点: <b style="color:var(--text-primary)">${entryMap}</b></span>
            </div>
        </div>
        <div class="sc-right" style="text-align:center; min-width:52px;">
            <div style="font-size:26px; font-weight:700; color:${scoreColor}; line-height:1;">${r.trend_score}</div>
            <div style="font-size:10px; color:var(--text-muted); margin-top:2px;">趋势分</div>
        </div>
    </div>`;
}

function filterTrend(btn, stage) {
    document.querySelectorAll('#page-trend .sfil').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    _trendStageFilter = stage;
    renderTrendList();
}

function refreshTrend() { loadTrendScanner(); }

async function fetchTrendHistory() {
    showToast('历史数据拉取已启动，约需 10 分钟，请稍后刷新', 'info');
    try {
        await API.request('/api/trend/fetch-history', { method: 'POST' });
        showToast('后台拉取中，10分钟后点击刷新查看数据', 'success');
    } catch(e) {
        showToast('启动失败: ' + e.message, 'error');
    }
}
