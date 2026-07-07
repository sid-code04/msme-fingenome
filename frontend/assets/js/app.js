/**
 * MSME FinGenome — Frontend Application v2
 * ==========================================
 * Multi-page SPA: Home portfolio grid + MSME profile view
 * D3.js radar chart, force network, Chart.js trajectories,
 * Phase 2 Living Loan Monitor lifecycle tracking
 */

// ─── Constants ─────────────────────────────────────────────────────────────

const API_BASE = '';

const STRAND_COLORS = {
    'Revenue DNA':    '#00f5d4',
    'Cash Flow DNA':  '#7b61ff',
    'Compliance DNA': '#fbbf24',
    'Workforce DNA':  '#f472b6',
    'Network DNA':    '#60a5fa',
    'Trajectory DNA': '#e879f9',
};
const STRAND_KEYS  = ['revenue_dna','cashflow_dna','compliance_dna','workforce_dna','network_dna','trajectory_dna'];
const STRAND_NAMES = ['Revenue DNA','Cash Flow DNA','Compliance DNA','Workforce DNA','Network DNA','Trajectory DNA'];

const GRADE_COLORS = {
    'A+':'#00f5d4','A':'#4ade80','B+':'#60a5fa','B':'#fbbf24','C':'#fb923c','D':'#f87171',
};

const CREDIT_STYLES = {
    'approve': { label:'✅ APPROVE', cls:'approve' },
    'review':  { label:'⚠️ REVIEW',  cls:'review' },
    'decline': { label:'❌ DECLINE', cls:'decline' },
};

// ─── App State ─────────────────────────────────────────────────────────────

let state = {
    msmeList: [],
    selectedId: null,
    currentGenome: null,
    currentNetwork: null,
    trajectoryChart: null,
    lifecycleCharts: {},
};

// ─── API ───────────────────────────────────────────────────────────────────

async function api(endpoint) {
    const res = await fetch(`${API_BASE}${endpoint}`);
    if (!res.ok) throw new Error(`API error ${res.status}: ${endpoint}`);
    return res.json();
}
const fetchHealth    = () => api('/api/health');
const fetchSummary   = () => api('/api/dashboard/summary');
const fetchMSMEs     = (q='') => api(`/api/msmes${q ? '?'+q : ''}`);
const fetchGenome    = id => api(`/api/msmes/${id}/genome`);
const fetchNetwork   = id => api(`/api/msmes/${id}/network`);
const fetchLifecycle = id => api(`/api/loan-lifecycle/${id}`);
const fetchIndustries= () => api('/api/industries');

function formatCurrency(n) {
    if (n >= 10000000) return `${(n/10000000).toFixed(1)}Cr`;
    if (n >= 100000)   return `${(n/100000).toFixed(1)}L`;
    if (n >= 1000)     return `${(n/1000).toFixed(0)}K`;
    return String(Math.round(n));
}
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function getGradeClass(g) {
    return {'A+':'grade-aplus','A':'grade-a','B+':'grade-bplus','B':'grade-b','C':'grade-c','D':'grade-d'}[g] || 'grade-b';
}
function getTrendIcon(t) {
    return {'improving':'📈','stable':'➡️','declining':'📉','volatile':'📊'}[t] || '➡️';
}

// ═══════════════════════════════════════════════════════════════════════════
// INITIALIZATION
// ═══════════════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', async () => {
    const statusEl = document.getElementById('loading-status');
    try {
        statusEl.textContent = 'Connecting to Genome Engine...';
        let tries = 0;
        while (tries < 30) {
            try { const h = await fetchHealth(); if (h.initialized) break; } catch(e) {}
            await sleep(1000); tries++;
            statusEl.textContent = `Initializing... (${tries}s)`;
        }

        statusEl.textContent = 'Loading MSME Ecosystem...';
        const [summary, msmes, industries] = await Promise.all([
            fetchSummary(), fetchMSMEs(), fetchIndustries()
        ]);
        state.msmeList = msmes;

        statusEl.textContent = 'Rendering Portfolio...';
        await sleep(300);

        renderNavKPIs(summary);
        populateIndustryFilter(industries);
        renderPortfolioGrid(msmes);
        renderHeroStats(summary);
        document.getElementById('portfolio-count').textContent = msmes.length;

        setupEventListeners();

        // Hide loading, show app
        document.getElementById('loading-screen').classList.add('fade-out');
        document.getElementById('app').classList.remove('hidden');

    } catch(err) {
        statusEl.textContent = `Error: ${err.message}. Is the backend running?`;
        console.error(err);
    }
});

// ═══════════════════════════════════════════════════════════════════════════
// PAGE ROUTER
// ═══════════════════════════════════════════════════════════════════════════

function showPage(pageId) {
    document.querySelectorAll('.page').forEach(p => {
        p.classList.remove('active');
        p.classList.add('hidden');
    });
    const pg = document.getElementById(`page-${pageId}`);
    if (!pg) return;
    pg.classList.remove('hidden');
    // Small delay for animation reset
    requestAnimationFrame(() => pg.classList.add('active'));
    window.currentPage = pageId;
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function goHome() {
    state.selectedId = null;
    showPage('home');
    document.getElementById('nav-profile').classList.add('hidden');
    document.getElementById('nav-home').classList.add('active');
}

// ═══════════════════════════════════════════════════════════════════════════
// EVENT LISTENERS
// ═══════════════════════════════════════════════════════════════════════════

function setupEventListeners() {
    // Home button
    document.getElementById('home-btn').addEventListener('click', goHome);

    // Search
    let searchTimer;
    document.getElementById('search-input').addEventListener('input', () => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(filterPortfolio, 200);
    });

    // Filters
    document.getElementById('filter-industry').addEventListener('change', filterPortfolio);
    document.getElementById('filter-grade').addEventListener('change', filterPortfolio);

    // View toggle
    document.getElementById('view-grid').addEventListener('click', () => {
        document.getElementById('portfolio-grid').classList.remove('list-view');
        document.getElementById('view-grid').classList.add('active');
        document.getElementById('view-list').classList.remove('active');
    });
    document.getElementById('view-list').addEventListener('click', () => {
        document.getElementById('portfolio-grid').classList.add('list-view');
        document.getElementById('view-list').classList.add('active');
        document.getElementById('view-grid').classList.remove('active');
    });

    // Modal
    document.getElementById('btn-open-modal').addEventListener('click', () =>
        document.getElementById('onboard-modal').classList.remove('hidden'));
    document.getElementById('close-modal').addEventListener('click', () =>
        document.getElementById('onboard-modal').classList.add('hidden'));
    document.getElementById('close-modal-backdrop').addEventListener('click', () =>
        document.getElementById('onboard-modal').classList.add('hidden'));
    document.getElementById('btn-onboard').addEventListener('click', handleOnboard);

    // Simulation sliders
    let simTimer;
    const simHandler = () => {
        document.getElementById('rev-val').textContent  = document.getElementById('sim-revenue').value;
        document.getElementById('cash-val').textContent = document.getElementById('sim-cashflow').value;
        clearTimeout(simTimer);
        simTimer = setTimeout(runSimulation, 400);
    };
    document.getElementById('sim-revenue').addEventListener('input', simHandler);
    document.getElementById('sim-cashflow').addEventListener('input', simHandler);
    document.getElementById('btn-reset-sim').addEventListener('click', () => {
        document.getElementById('sim-revenue').value  = 0;
        document.getElementById('sim-cashflow').value = 0;
        document.getElementById('rev-val').textContent  = '0';
        document.getElementById('cash-val').textContent = '0';
        runSimulation();
    });
}

// ═══════════════════════════════════════════════════════════════════════════
// NAV KPIs
// ═══════════════════════════════════════════════════════════════════════════

function renderNavKPIs(summary) {
    document.getElementById('nav-kpis').innerHTML = `
        <div class="nav-kpi">
            <div class="nav-kpi-value">${summary.total_msmes}</div>
            <div class="nav-kpi-label">MSMEs</div>
        </div>
        <div class="nav-kpi">
            <div class="nav-kpi-value">${summary.avg_health_score.toFixed(0)}</div>
            <div class="nav-kpi-label">Avg Score</div>
        </div>
        <div class="nav-kpi">
            <div class="nav-kpi-value" style="color:var(--success)">${summary.credit_worthy_count}</div>
            <div class="nav-kpi-label">Credit Worthy</div>
        </div>
        <div class="nav-kpi">
            <div class="nav-kpi-value" style="color:var(--danger)">${summary.at_risk_count}</div>
            <div class="nav-kpi-label">At Risk</div>
        </div>
    `;
}

// ═══════════════════════════════════════════════════════════════════════════
// HERO STATS
// ═══════════════════════════════════════════════════════════════════════════

function renderHeroStats(summary) {
    document.getElementById('hero-stats').innerHTML = `
        <div class="hero-stat">
            <div class="hero-stat-value">${summary.total_msmes}</div>
            <div class="hero-stat-label">MSMEs Analyzed</div>
        </div>
        <div class="hero-stat">
            <div class="hero-stat-value">${summary.avg_health_score.toFixed(1)}</div>
            <div class="hero-stat-label">Avg Genome Score</div>
        </div>
        <div class="hero-stat">
            <div class="hero-stat-value">${summary.credit_worthy_count}</div>
            <div class="hero-stat-label">Credit-Worthy</div>
        </div>
        <div class="hero-stat">
            <div class="hero-stat-value">₹${formatCurrency(summary.total_credit_capacity || 0)}</div>
            <div class="hero-stat-label">Total Credit Capacity</div>
        </div>
    `;
}

// ═══════════════════════════════════════════════════════════════════════════
// PORTFOLIO GRID
// ═══════════════════════════════════════════════════════════════════════════

function populateIndustryFilter(industries) {
    const sel = document.getElementById('filter-industry');
    industries.forEach(ind => {
        const o = document.createElement('option');
        o.value = ind; o.textContent = ind;
        sel.appendChild(o);
    });
}

function renderPortfolioGrid(msmes) {
    const grid = document.getElementById('portfolio-grid');
    document.getElementById('portfolio-count').textContent = msmes.length;

    if (!msmes.length) {
        grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:80px 0;color:var(--text-muted)">
            <div style="font-size:3rem;margin-bottom:16px">🔍</div>
            <p>No MSMEs match your filters</p>
        </div>`;
        return;
    }

    grid.innerHTML = msmes.map(m => {
        const gc = getGradeClass(m.risk_grade);
        const gradeColor = GRADE_COLORS[m.risk_grade] || '#fbbf24';
        const score = Math.round(m.overall_score);
        const circumference = 163;
        const dashOffset = circumference - (circumference * score / 100);
        const trendIcon = getTrendIcon(m.trend);

        // Determine credit rec from score
        const rec = score >= 70 ? 'approve' : score >= 50 ? 'review' : 'decline';
        const recStyle = CREDIT_STYLES[rec];

        return `
        <div class="msme-card" data-id="${m.business_id}" onclick="selectMSME('${m.business_id}')">
            <div class="msme-card-header">
                <div class="msme-card-info">
                    <div class="msme-card-name">${m.name}</div>
                    <div class="msme-card-meta">
                        <span>📍 ${m.city}</span>
                        <span class="dot"></span>
                        <span>${m.category}</span>
                    </div>
                    <div style="margin-top:10px">
                        <span class="industry-pill">${m.industry}</span>
                    </div>
                </div>
                <div class="msme-score-ring" style="--score:${score}">
                    <svg viewBox="0 0 56 56" width="64" height="64">
                        <circle class="ring-bg" cx="28" cy="28" r="26"/>
                        <circle class="ring-fill" cx="28" cy="28" r="26"
                            stroke="${gradeColor}"
                            stroke-dasharray="${circumference}"
                            stroke-dashoffset="${dashOffset}"/>
                    </svg>
                    <div class="msme-score-text">
                        <span class="msme-score-num" style="color:${gradeColor}">${score}</span>
                    </div>
                </div>
            </div>
            <div class="msme-card-grade-strip">
                <span class="grade-badge ${gc}">${m.risk_grade}</span>
                <span class="trend-badge">${trendIcon} ${m.trend}</span>
                <span class="credit-rec-chip ${recStyle.cls}">${recStyle.label}</span>
            </div>
        </div>`;
    }).join('');
}

async function filterPortfolio() {
    const search   = document.getElementById('search-input').value;
    const industry = document.getElementById('filter-industry').value;
    const grade    = document.getElementById('filter-grade').value;
    const params   = new URLSearchParams();
    if (search)   params.set('search', search);
    if (industry) params.set('industry', industry);
    if (grade)    params.set('risk_grade', grade);
    try {
        const msmes = await fetchMSMEs(params.toString());
        state.msmeList = msmes;
        renderPortfolioGrid(msmes);
    } catch(e) { console.error(e); }
}

// ═══════════════════════════════════════════════════════════════════════════
// SELECT MSME → GO TO PROFILE PAGE
// ═══════════════════════════════════════════════════════════════════════════

async function selectMSME(businessId) {
    state.selectedId = businessId;
    window.currentBusinessId = businessId;

    // Update nav breadcrumb
    const msme = state.msmeList.find(m => m.business_id === businessId);
    if (msme) {
        document.getElementById('nav-profile-name').textContent = msme.name;
        document.getElementById('nav-profile').classList.remove('hidden');
    }
    document.getElementById('nav-home').classList.remove('active');

    // Reset to Phase 1
    switchPhase('origination');

    // Show profile page immediately with loading state
    showPage('profile');
    document.getElementById('profile-hero').innerHTML = `
        <div class="profile-hero-inner">
            <div style="color:var(--text-muted);font-size:0.9rem">Loading genome data...</div>
        </div>`;

    try {
        const [genome, network] = await Promise.all([
            fetchGenome(businessId), fetchNetwork(businessId)
        ]);
        state.currentGenome = genome;
        state.currentNetwork = network;

        renderProfileHero(genome);
        renderGenomeRadar(genome);
        renderHealthCard(genome);
        renderStrandDetails(genome);
        renderNetworkGraph(network);
        renderTrajectoryChart(genome);
        renderInsights(genome);

    } catch(err) {
        console.error('Error loading MSME:', err);
        document.getElementById('profile-hero').innerHTML = `
            <div class="profile-hero-inner" style="color:var(--danger)">
                Error loading data: ${err.message}
            </div>`;
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// PHASE SWITCHER
// ═══════════════════════════════════════════════════════════════════════════

function switchPhase(phase) {
    const origEl  = document.getElementById('phase-origination');
    const liveEl  = document.getElementById('phase-lifecycle');
    const tabOrig = document.getElementById('tab-origination');
    const tabLive = document.getElementById('tab-lifecycle');

    if (phase === 'origination') {
        origEl.classList.remove('hidden');
        liveEl.classList.add('hidden');
        tabOrig.classList.add('active');
        tabLive.classList.remove('active');
    } else {
        origEl.classList.add('hidden');
        liveEl.classList.remove('hidden');
        tabOrig.classList.remove('active');
        tabLive.classList.add('active');
        if (state.selectedId) fetchAndRenderLifecycle(state.selectedId);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// PROFILE HERO
// ═══════════════════════════════════════════════════════════════════════════

function renderProfileHero(genome) {
    const gradeColor = GRADE_COLORS[genome.risk_grade] || '#fbbf24';
    const score = Math.round(genome.overall_score);
    const circumference = 283; // 2π * 45
    const dashOffset = circumference - (circumference * score / 100);
    const rec = CREDIT_STYLES[genome.credit_recommendation] || CREDIT_STYLES['review'];

    document.getElementById('profile-hero').innerHTML = `
        <div class="profile-hero-inner">
            <div class="profile-score-ring">
                <svg viewBox="0 0 100 100">
                    <circle class="ring-bg" cx="50" cy="50" r="45" stroke="rgba(255,255,255,0.07)" fill="none" stroke-width="8"/>
                    <circle cx="50" cy="50" r="45" fill="none" stroke="${gradeColor}" stroke-width="8"
                        stroke-dasharray="${circumference}" stroke-dashoffset="${dashOffset}"
                        stroke-linecap="round" style="transition: stroke-dashoffset 1s ease;"/>
                </svg>
                <div class="profile-score-text">
                    <div class="profile-score-num" style="color:${gradeColor}">${score}</div>
                    <div class="profile-score-lbl">Genome</div>
                </div>
            </div>
            <div class="profile-info">
                <h2 class="profile-name">${genome.business_name}</h2>
                <div class="profile-meta">
                    <span>${genome.industry || '—'}</span>
                    <span class="sep">|</span>
                    <span>${genome.city || '—'}</span>
                    <span class="sep">|</span>
                    <span>${genome.category || '—'} Enterprise</span>
                    <span class="sep">|</span>
                    <span class="grade-badge ${getGradeClass(genome.risk_grade)} grade-${genome.risk_grade.toLowerCase().replace('+','plus')}">${genome.risk_grade}</span>
                </div>
                <div class="profile-kpis">
                    <div class="profile-kpi">
                        <div class="profile-kpi-label">Annual Revenue</div>
                        <div class="profile-kpi-value">₹${formatCurrency(genome.inferred_annual_revenue || 0)}</div>
                        <div class="profile-kpi-sub">Inferred from transactions</div>
                    </div>
                    <div class="profile-kpi">
                        <div class="profile-kpi-label">Employees</div>
                        <div class="profile-kpi-value">${genome.employee_count || '—'}</div>
                        <div class="profile-kpi-sub">Estimated workforce</div>
                    </div>
                    <div class="profile-kpi">
                        <div class="profile-kpi-label">Truth Confidence</div>
                        <div class="profile-kpi-value">${genome.truth_confidence || 'HIGH'}</div>
                        <div class="profile-kpi-sub">Data reliability score</div>
                    </div>
                    <div class="profile-kpi">
                        <div class="profile-kpi-label">Trend</div>
                        <div class="profile-kpi-value">${getTrendIcon(genome.trajectory_dna?.trend || 'stable')} ${genome.trajectory_dna?.trend || 'stable'}</div>
                        <div class="profile-kpi-sub">6-month trajectory</div>
                    </div>
                </div>
            </div>
            <div class="profile-decision">
                <div class="decision-label">Credit Decision</div>
                <div class="decision-value ${rec.cls}">${rec.label}</div>
                <div class="decision-limit">₹${formatCurrency(genome.suggested_credit_limit || 0)}</div>
                <div class="decision-limit-label">Suggested Credit Limit</div>
            </div>
        </div>
    `;
}

// ═══════════════════════════════════════════════════════════════════════════
// GENOME RADAR CHART (D3)
// ═══════════════════════════════════════════════════════════════════════════

function renderGenomeRadar(genome) {
    const container = document.getElementById('genome-chart-container');
    const svg = d3.select('#genome-radar');
    svg.selectAll('*').remove();

    const W = container.clientWidth  || 400;
    const H = container.clientHeight || 320;
    const cx = W / 2, cy = H / 2;
    const R  = Math.min(W, H) / 2 - 50;

    svg.attr('viewBox', `0 0 ${W} ${H}`);

    const strands = STRAND_KEYS.map((k, i) => ({
        name:  STRAND_NAMES[i],
        score: genome[k]?.score ?? 0,
        color: Object.values(STRAND_COLORS)[i],
    }));
    const N = strands.length;
    const angle = (i) => (2 * Math.PI * i / N) - Math.PI / 2;

    const g = svg.append('g').attr('transform', `translate(${cx},${cy})`);

    // Background rings
    [20,40,60,80,100].forEach(v => {
        const pts = strands.map((_, i) => {
            const a = angle(i), r = R * v / 100;
            return `${r * Math.cos(a)},${r * Math.sin(a)}`;
        }).join(' ');
        g.append('polygon').attr('points', pts)
            .attr('fill', 'none').attr('stroke', 'rgba(255,255,255,0.05)').attr('stroke-width', 1);
        g.append('text').attr('x', 0).attr('y', -R * v / 100 - 4)
            .attr('text-anchor','middle').attr('fill','rgba(255,255,255,0.2)')
            .style('font-size','10px').text(v);
    });

    // Axis lines
    strands.forEach((_, i) => {
        const a = angle(i);
        g.append('line')
            .attr('x1',0).attr('y1',0)
            .attr('x2', R * Math.cos(a)).attr('y2', R * Math.sin(a))
            .attr('stroke','rgba(255,255,255,0.07)').attr('stroke-width',1);
    });

    // Gradient fill
    const defs = svg.append('defs');
    const grad = defs.append('radialGradient').attr('id','radar-fill');
    grad.append('stop').attr('offset','0%').attr('stop-color','#00f5d4').attr('stop-opacity','0.25');
    grad.append('stop').attr('offset','100%').attr('stop-color','#7b61ff').attr('stop-opacity','0.08');

    const polyPts = strands.map((s, i) => {
        const a = angle(i), r = R * s.score / 100;
        return `${r * Math.cos(a)},${r * Math.sin(a)}`;
    }).join(' ');

    g.append('polygon').attr('points', polyPts)
        .attr('fill','url(#radar-fill)')
        .attr('stroke','rgba(0,245,212,0.5)').attr('stroke-width',2);

    // Data points
    strands.forEach((s, i) => {
        const a = angle(i), r = R * s.score / 100;
        const px = r * Math.cos(a), py = r * Math.sin(a);
        g.append('circle').attr('cx',px).attr('cy',py).attr('r',5)
            .attr('fill',s.color).attr('stroke','rgba(0,0,0,0.5)').attr('stroke-width',2);
    });

    // Labels
    strands.forEach((s, i) => {
        const a = angle(i), lR = R + 32;
        const lx = lR * Math.cos(a), ly = lR * Math.sin(a);
        const anchor = Math.abs(lx) < 10 ? 'middle' : lx > 0 ? 'start' : 'end';
        g.append('text')
            .attr('x', lx).attr('y', ly + 4)
            .attr('text-anchor', anchor)
            .attr('fill', s.color)
            .style('font-size','11px').style('font-weight','600')
            .text(`${s.name.replace(' DNA','')} ${s.score}`);
    });
}

// ═══════════════════════════════════════════════════════════════════════════
// HEALTH CARD
// ═══════════════════════════════════════════════════════════════════════════

function renderHealthCard(genome) {
    const gradeColor = GRADE_COLORS[genome.risk_grade] || '#fbbf24';
    const score = Math.round(genome.overall_score);
    const rec = CREDIT_STYLES[genome.credit_recommendation] || CREDIT_STYLES['review'];

    document.getElementById('health-card').innerHTML = `
        <div class="card-header">
            <h3>Credit Health Summary</h3>
        </div>
        <div class="health-overview">
            <div class="health-score-row">
                <div class="health-score-circle" style="border-color:${gradeColor}">
                    <div class="health-score-number" style="color:${gradeColor}">${score}</div>
                    <div class="health-score-label">Score</div>
                </div>
                <div>
                    <div class="health-grade-label" style="color:${gradeColor}">Grade ${genome.risk_grade}</div>
                    <div class="health-text">${genome.credit_recommendation_reason || 'Analysis complete.'}</div>
                </div>
            </div>
            <div class="health-pills">
                <span class="health-pill" style="background:rgba(74,222,128,0.1);color:#4ade80">
                    ${rec.label}
                </span>
                <span class="health-pill" style="background:rgba(255,255,255,0.05);color:var(--text-muted)">
                    Confidence: ${genome.truth_confidence || 'HIGH'}
                </span>
            </div>
            <div style="padding:16px;background:rgba(0,0,0,0.2);border-radius:10px;">
                <div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.5px;color:var(--text-muted);margin-bottom:10px">Key Insights</div>
                ${(genome.strengths || []).slice(0,2).map(i => `
                    <div style="font-size:0.78rem;color:var(--text-secondary);padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.04);line-height:1.5">
                        <span style="color:#4ade80">✓</span> ${i}
                    </div>`).join('')}
                ${(genome.risks || []).slice(0,1).map(i => `
                    <div style="font-size:0.78rem;color:var(--text-secondary);padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.04);line-height:1.5">
                        <span style="color:#f87171">⚠</span> ${i}
                    </div>`).join('')}
            </div>
        </div>
    `;
}

// ═══════════════════════════════════════════════════════════════════════════
// STRAND DETAILS
// ═══════════════════════════════════════════════════════════════════════════

function renderStrandDetails(genome) {
    document.getElementById('strand-list').innerHTML = STRAND_KEYS.map((k, i) => {
        const strand = genome[k] || {};
        const name   = STRAND_NAMES[i];
        const color  = Object.values(STRAND_COLORS)[i];
        const score  = strand.score ?? 0;
        return `
        <div class="strand-item">
            <div class="strand-item-header">
                <span class="strand-name">${name}</span>
                <span class="strand-score" style="color:${color}">${score}/100</span>
            </div>
            <div class="strand-bar">
                <div class="strand-bar-fill" style="width:${score}%;background:${color}"></div>
            </div>
            ${strand.insight ? `<div class="strand-insight">${strand.insight}</div>` : ''}
        </div>`;
    }).join('');
}

// ═══════════════════════════════════════════════════════════════════════════
// NETWORK GRAPH (D3 Force)
// ═══════════════════════════════════════════════════════════════════════════

function renderNetworkGraph(network) {
    const container = document.getElementById('network-container');
    const svg = d3.select('#network-svg');
    svg.selectAll('*').remove();

    const W = container.clientWidth  || 500;
    const H = container.clientHeight || 280;
    svg.attr('viewBox', `0 0 ${W} ${H}`);

    const nodes = network.nodes || [];
    const links = network.links || [];

    const colorMap = {
        'focal': '#00f5d4', 'buyer': '#60a5fa',
        'supplier': '#e879f9', 'competitor': '#f87171', 'peer': '#fbbf24',
    };

    const sim = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(70))
        .force('charge', d3.forceManyBody().strength(-120))
        .force('center', d3.forceCenter(W/2, H/2))
        .force('collision', d3.forceCollide(22));

    const link = svg.append('g')
        .selectAll('line').data(links).join('line')
        .attr('stroke','rgba(255,255,255,0.08)').attr('stroke-width',1.5);

    const node = svg.append('g')
        .selectAll('g').data(nodes).join('g')
        .attr('cursor','pointer')
        .call(d3.drag()
            .on('start', (e,d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; })
            .on('drag',  (e,d) => { d.fx=e.x; d.fy=e.y; })
            .on('end',   (e,d) => { if (!e.active) sim.alphaTarget(0); d.fx=null; d.fy=null; }));

    node.append('circle')
        .attr('r', d => d.type === 'focal' ? 14 : 8)
        .attr('fill', d => colorMap[d.type] || '#60a5fa')
        .attr('fill-opacity', d => d.type === 'focal' ? 0.9 : 0.5)
        .attr('stroke', d => colorMap[d.type] || '#60a5fa')
        .attr('stroke-width', d => d.type === 'focal' ? 2 : 1);

    node.filter(d => d.type === 'focal').append('text')
        .attr('dy','0.35em').attr('text-anchor','middle')
        .style('font-size','10px').style('font-weight','700').style('fill','#06060f')
        .text(d => (d.label||'').slice(0,2));

    sim.on('tick', () => {
        link
            .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
        node.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    // Metrics
    const metrics = network.metrics || {};
    document.getElementById('network-metrics').innerHTML = `
        <div class="net-metric">
            <div class="net-metric-value">${metrics.degree_centrality?.toFixed(2) || '—'}</div>
            <div class="net-metric-label">Centrality</div>
        </div>
        <div class="net-metric">
            <div class="net-metric-value">${metrics.total_connections || nodes.length}</div>
            <div class="net-metric-label">Connections</div>
        </div>
        <div class="net-metric">
            <div class="net-metric-value">${metrics.contagion_risk || 'LOW'}</div>
            <div class="net-metric-label">Contagion Risk</div>
        </div>
    `;
}

// ═══════════════════════════════════════════════════════════════════════════
// TRAJECTORY CHART (Chart.js)
// ═══════════════════════════════════════════════════════════════════════════

function renderTrajectoryChart(genome) {
    if (state.trajectoryChart) { state.trajectoryChart.destroy(); }
    const ctx = document.getElementById('trajectory-chart').getContext('2d');
    const traj = genome.trajectory_dna || {};
    const hist = traj.historical_scores || [];
    const proj = traj.projected_scores || [];

    const histLabels = hist.map((_, i) => `M-${hist.length - i}`);
    const projLabels = proj.map((_, i) => `M+${i+1}`);
    const labels = [...histLabels, 'Now', ...projLabels];
    const currentScore = genome.overall_score;
    const histData = [...hist, currentScore, ...Array(proj.length).fill(null)];
    const projData = [...Array(hist.length).fill(null), currentScore, ...proj];

    state.trajectoryChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'Historical',
                    data: histData,
                    borderColor: '#00f5d4', borderWidth: 2,
                    pointRadius: 3, pointBackgroundColor: '#00f5d4',
                    tension: 0.4, fill: false,
                },
                {
                    label: 'Projected',
                    data: projData,
                    borderColor: '#7b61ff', borderWidth: 2,
                    borderDash: [5, 4],
                    pointRadius: 3, pointBackgroundColor: '#7b61ff',
                    tension: 0.4, fill: false,
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: 'rgba(255,255,255,0.4)', font: { size: 10 } } }
            },
            scales: {
                y: { min: 0, max: 100, grid: { color: 'rgba(255,255,255,0.04)' },
                     ticks: { color: 'rgba(255,255,255,0.3)', font: { size: 10 } } },
                x: { grid: { display: false },
                     ticks: { color: 'rgba(255,255,255,0.3)', font: { size: 10 } } },
            }
        }
    });
}

// ═══════════════════════════════════════════════════════════════════════════
// INSIGHTS
// ═══════════════════════════════════════════════════════════════════════════

function renderInsights(genome) {
    const insights = [];
    if (genome.strengths) genome.strengths.forEach(s => insights.push({ type: 'positive', title: 'Strength', description: s }));
    if (genome.risks) genome.risks.forEach(r => insights.push({ type: 'negative', title: 'Risk Factor', description: r }));
    if (genome.recommendations) genome.recommendations.forEach(r => insights.push({ type: 'neutral', title: 'Recommendation', description: r }));

    if (!insights.length) {
        document.getElementById('insights-content').innerHTML =
            `<div style="color:var(--text-muted);font-size:0.85rem">No insights available.</div>`;
        return;
    }
    document.getElementById('insights-content').innerHTML = insights.map(ins => `
        <div class="insight-item ${ins.type}">
            <div class="insight-title">${ins.title}</div>
            <div class="insight-body">${ins.description}</div>
        </div>
    `).join('');
}

// ═══════════════════════════════════════════════════════════════════════════
// STRESS TEST SIMULATOR
// ═══════════════════════════════════════════════════════════════════════════

async function runSimulation() {
    if (!state.selectedId) return;
    const revShock  = parseFloat(document.getElementById('sim-revenue').value);
    const cashShock = parseFloat(document.getElementById('sim-cashflow').value);

    if (revShock === 0 && cashShock === 0) {
        if (state.currentGenome) {
            renderGenomeRadar(state.currentGenome);
            renderTrajectoryChart(state.currentGenome);
            renderHealthCard(state.currentGenome);
            renderProfileHero(state.currentGenome);
        }
        return;
    }
    try {
        const simGenome = await (async () => {
            const res = await fetch(`/api/msmes/${state.selectedId}/simulate`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ revenue_shock: revShock, cashflow_shock: cashShock }),
            });
            return res.json();
        })();
        renderGenomeRadar(simGenome);
        renderTrajectoryChart(simGenome);
        renderHealthCard(simGenome);
        renderProfileHero(simGenome);
    } catch(e) { console.error('Simulation failed:', e); }
}

// ═══════════════════════════════════════════════════════════════════════════
// PHASE 2: LIVING LOAN MONITOR
// ═══════════════════════════════════════════════════════════════════════════

async function fetchAndRenderLifecycle(businessId) {
    const grid = document.getElementById('lifecycle-grid');
    grid.style.opacity = '0.5';
    try {
        const data = await fetchLifecycle(businessId);
        renderLoanStatusCard(data);
        renderHeartbeatChart(data);
        renderSweepChart(data);
        renderAlertTimeline(data);
        renderNPACounter(data);
        renderPassportCard(data);
        grid.style.opacity = '1';
    } catch(e) {
        console.error('Lifecycle fetch failed:', e);
        grid.style.opacity = '1';
    }
}

function renderLoanStatusCard(data) {
    const z = data.current_zone;
    const zIcon = z === 'GREEN' ? '🟢' : z === 'YELLOW' ? '🟡' : '🟠';
    document.getElementById('loan-status-card').innerHTML = `
        <div class="loan-status-zone ${z}">
            <div class="zone-label">Health Zone</div>
            <div class="zone-icon">${zIcon}</div>
            <div class="zone-name ${z}">${z}</div>
        </div>
        <div class="loan-status-metrics">
            <div class="lsm-item">
                <div class="lsm-label">Loan Amount</div>
                <div class="lsm-value">₹${formatCurrency(data.loan_amount)}</div>
                <div class="lsm-sub">Disbursed ${data.disbursement_date}</div>
            </div>
            <div class="lsm-item">
                <div class="lsm-label">Total Repaid</div>
                <div class="lsm-value">₹${formatCurrency(data.total_swept_to_date)}</div>
                <div class="lsm-sub">${data.loan_repaid_percent}% of principal</div>
            </div>
            <div class="lsm-item">
                <div class="lsm-label">Sweep Rate</div>
                <div class="lsm-value">${data.sweep_rate}%</div>
                <div class="lsm-sub">of all incoming txns</div>
            </div>
            <div class="lsm-item">
                <div class="lsm-label">Full Repayment</div>
                <div class="lsm-value">${data.projected_months_to_full_repayment}mo</div>
                <div class="lsm-sub">at current velocity</div>
            </div>
        </div>
    `;
}

function renderHeartbeatChart(data) {
    if (state.lifecycleCharts.heartbeat) state.lifecycleCharts.heartbeat.destroy();
    const ctx = document.getElementById('heartbeat-chart').getContext('2d');
    const labels = data.heartbeat.map(h => h.month);
    const scores = data.heartbeat.map(h => h.score);
    const pointColors = scores.map(s =>
        s > 75 ? '#4ade80' : s > 55 ? '#fbbf24' : s > 40 ? '#fb923c' : '#f87171');

    state.lifecycleCharts.heartbeat = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Genome Score',
                data: scores,
                borderColor: '#00f5d4', borderWidth: 2.5,
                pointBackgroundColor: pointColors, pointBorderColor: pointColors,
                pointRadius: 5, pointHoverRadius: 8,
                fill: true,
                backgroundColor: (ctx) => {
                    const {ctx: c, chartArea} = ctx.chart;
                    if (!chartArea) return 'transparent';
                    const g = c.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
                    g.addColorStop(0, 'rgba(0,245,212,0.2)');
                    g.addColorStop(1, 'rgba(0,245,212,0)');
                    return g;
                },
                tension: 0.4,
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: c => {
                    const s = c.raw;
                    const z = s > 75 ? '🟢 GREEN' : s > 55 ? '🟡 YELLOW' : s > 40 ? '🟠 ORANGE' : '🔴 RED';
                    return ` Score: ${s} — ${z}`;
                }}}
            },
            scales: {
                y: { min: 20, max: 100, grid: { color: 'rgba(255,255,255,0.04)' },
                     ticks: { color: 'rgba(255,255,255,0.3)', font: { size: 10 } } },
                x: { grid: { display: false },
                     ticks: { color: 'rgba(255,255,255,0.3)', font: { size: 10 } } },
            }
        }
    });
}

function renderSweepChart(data) {
    if (state.lifecycleCharts.sweep) state.lifecycleCharts.sweep.destroy();
    const ctx = document.getElementById('sweep-chart').getContext('2d');
    state.lifecycleCharts.sweep = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.sweep_data.map(s => s.month),
            datasets: [
                {
                    label: 'Monthly Revenue',
                    data: data.sweep_data.map(s => s.revenue),
                    backgroundColor: 'rgba(96,165,250,0.2)', borderColor: 'rgba(96,165,250,0.5)',
                    borderWidth: 1, borderRadius: 4,
                },
                {
                    label: 'Auto-Swept (3.5%)',
                    data: data.sweep_data.map(s => s.swept),
                    backgroundColor: 'rgba(0,245,212,0.45)', borderColor: '#00f5d4',
                    borderWidth: 1, borderRadius: 4,
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { labels: { color: 'rgba(255,255,255,0.4)', font: { size: 10 } } },
                tooltip: { callbacks: { label: c => ` ${c.dataset.label}: ₹${formatCurrency(c.raw)}` } } },
            scales: {
                y: { grid: { color: 'rgba(255,255,255,0.04)' },
                     ticks: { color: 'rgba(255,255,255,0.3)', font: { size: 10 }, callback: v => `₹${formatCurrency(v)}` } },
                x: { grid: { display: false }, ticks: { color: 'rgba(255,255,255,0.3)', font: { size: 10 } } },
            }
        }
    });

    document.getElementById('sweep-accounts').innerHTML = data.linked_accounts.map(a => `
        <div class="sweep-account-row">
            <div>
                <div class="sa-bank">${a.bank}</div>
                <div class="sa-type">${a.type}</div>
            </div>
            <div class="sa-share">${a.sweep_share}%</div>
            <div class="sa-status">${a.status}</div>
        </div>
    `).join('');
}

function renderAlertTimeline(data) {
    document.getElementById('alert-timeline').innerHTML = data.alerts.map(a => `
        <div class="alert-item ${a.type}">
            <div>
                <div class="alert-badge ${a.type}">${a.type}</div>
                <div class="alert-month">${a.month}</div>
            </div>
            <div class="alert-body">
                <div class="alert-trigger"><strong>⚡ Trigger:</strong> ${a.trigger}</div>
                <div class="alert-action"><strong>🤖 Auto-Action:</strong> ${a.action}</div>
                ${a.resolved ? `<div class="alert-resolved">✓ Resolved in ${a.days_to_resolve} days — NPA Prevented</div>` : ''}
            </div>
        </div>
    `).join('');
}

function renderNPACounter(data) {
    const n = data.npa_prevention;
    document.getElementById('npa-counter-card').innerHTML = `
        <div class="card-header">
            <h3>🛡️ NPA Prevention Engine</h3>
            <span class="card-badge" style="background:rgba(74,222,128,0.12);color:#4ade80">Active</span>
        </div>
        <div class="npa-counter-title">Capital Protected — This Account</div>
        <div class="npa-headline">₹${formatCurrency(n.total_value_protected)}</div>
        <div class="npa-sub">Estimated loss prevented vs traditional lending approach</div>
        <div class="npa-stats">
            <div class="npa-stat-row"><span class="npa-stat-label">🟡 Yellow Alerts</span><span class="npa-stat-value">${n.yellow_alerts_sent}</span></div>
            <div class="npa-stat-row"><span class="npa-stat-label">🟠 Orange Alerts</span><span class="npa-stat-value">${n.orange_alerts_sent}</span></div>
            <div class="npa-stat-row"><span class="npa-stat-label">🔴 Red Alerts</span><span class="npa-stat-value">${n.red_alerts_sent}</span></div>
            <div class="npa-stat-row"><span class="npa-stat-label">Payment Holidays</span><span class="npa-stat-value">${n.payment_holidays_granted}</span></div>
            <div class="npa-stat-row"><span class="npa-stat-label">Capital Saved</span><span class="npa-stat-value" style="color:#4ade80">₹${formatCurrency(n.estimated_capital_saved)}</span></div>
            <div class="npa-stat-row"><span class="npa-stat-label">Interest Preserved</span><span class="npa-stat-value" style="color:#4ade80">₹${formatCurrency(n.interest_revenue_preserved)}</span></div>
        </div>
        <div class="npa-detection-advantage">
            ⚡ Detected distress <strong>${n.detection_advantage_days} days earlier</strong> than traditional banking<br>
            <small style="opacity:0.7">Traditional: ${n.traditional_bank_discovery_month} — FinGenome: ${n.living_loan_detection_month}</small>
        </div>
    `;
}

function renderPassportCard(data) {
    const p = data.passport;
    const emoji = p.rate_tier === 'Gold' ? '🥇' : p.rate_tier === 'Silver' ? '🥈' : '📋';
    document.getElementById('passport-card').innerHTML = `
        <div class="card-header"><h3>🪪 Behavioral Credit Passport</h3></div>
        <div class="passport-tier ${p.rate_tier}">${emoji} ${p.rate_tier} Tier</div>
        <div class="passport-rate-display">
            <span class="passport-rate-old">${p.original_rate}%</span>
            <span class="passport-rate-new">${p.current_rate}%</span>
            <span class="passport-rate-saving">-${p.rate_saved}% earned</span>
        </div>
        <div style="font-size:0.72rem;color:var(--text-muted);margin-bottom:4px">Current Interest Rate (Dynamic)</div>
        <div style="font-size:0.8rem;color:#4ade80;margin-bottom:8px">
            Saving ₹${formatCurrency(p.annual_interest_saving)}/year vs entry rate
        </div>
        <div class="passport-stats">
            <div class="passport-stat">
                <div class="passport-stat-label">Months on Platform</div>
                <div class="passport-stat-value">${p.months_on_platform}</div>
            </div>
            <div class="passport-stat">
                <div class="passport-stat-label">Avg Genome Score</div>
                <div class="passport-stat-value">${p.avg_genome_score}</div>
            </div>
            <div class="passport-stat">
                <div class="passport-stat-label">Alerts Responded</div>
                <div class="passport-stat-value">${p.alerts_responded_to}</div>
            </div>
            <div class="passport-stat">
                <div class="passport-stat-label">Next Review</div>
                <div class="passport-stat-value">${p.next_review}</div>
            </div>
        </div>
        <div style="margin-top:16px;padding:10px 14px;background:rgba(123,97,255,0.08);border-radius:10px;border:1px solid rgba(123,97,255,0.15);font-size:0.72rem;color:var(--accent-light);text-align:center;line-height:1.5">
            This passport is non-transferable. Switching banks resets all earned behavioral credit history.
        </div>
    `;
}

// ═══════════════════════════════════════════════════════════════════════════
// ONBOARD MOCK
// ═══════════════════════════════════════════════════════════════════════════

async function handleOnboard() {
    const btn    = document.getElementById('btn-onboard');
    const status = document.getElementById('onboard-status');
    const gstin  = document.getElementById('mock-gstin').value;
    const name   = document.getElementById('mock-name').value;
    if (!gstin || !name) { status.textContent = 'Please fill all fields.'; return; }

    btn.disabled = true;
    btn.querySelector('span').textContent = 'Connecting to ULI...';
    status.textContent = 'Establishing secure connection...';

    try {
        await sleep(1500);
        status.textContent = 'Fetching AA bank statements & GST returns...';
        await sleep(1500);
        status.textContent = 'Computing Genome Score...';

        const res = await fetch('/api/msmes/onboard', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ gstin, name }),
        });
        const data = await res.json();
        const msmes = await fetchMSMEs();
        state.msmeList = msmes;
        renderPortfolioGrid(msmes);
        document.getElementById('onboard-modal').classList.add('hidden');
        selectMSME(data.business_id);
    } catch(err) {
        status.textContent = `Error: ${err.message}`;
    } finally {
        btn.disabled = false;
        btn.querySelector('span').textContent = 'Establish ULI Connection & Fetch Data';
    }
}
