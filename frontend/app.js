/* ============================================
   QQQ 预警看板 - 前端逻辑
   ============================================ */

// 数据 JSON 路径 (相对于 frontend/index.html)
const DATA_URL = '../data/dashboard.json';

// 全局状态
let dashboardData = null;
let qqqChartInstance = null;
let vixChartInstance = null;

// ============================================
// 工具函数
// ============================================

function formatNumber(n, decimals = 2) {
  if (n === null || n === undefined) return '--';
  return Number(n).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function colorClassFromScore(score, maxScore = 4) {
  if (score >= maxScore * 0.5) return 'bull';
  if (score >= 0) return 'neutral';
  if (score >= -maxScore * 0.5) return 'warn';
  return 'bear';
}

function colorClassFromChange(pct) {
  if (pct > 0) return 'bull';
  if (pct < 0) return 'bear';
  return 'neutral';
}

function formatChange(pct) {
  if (pct === null || pct === undefined) return '0.00%';
  const sign = pct > 0 ? '+' : '';
  return `${sign}${formatNumber(pct, 2)}%`;
}

function regimeColorClass(color) {
  if (color === 'success') return 'bull';
  if (color === 'danger') return 'bear';
  if (color === 'warning') return 'warn';
  return 'info';
}

// ============================================
// 数据加载
// ============================================

async function loadData() {
  const live = document.getElementById('liveDot');
  live.style.background = 'var(--warn)';
  live.style.boxShadow = '0 0 0 4px rgba(251,191,36,0)';

  try {
    const res = await fetch(DATA_URL + '?t=' + Date.now());
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    dashboardData = await res.json();
    try {
      renderAll();
    } catch (renderErr) {
      console.error('Render error:', renderErr);
      // 渲染部分失败但数据加载成功 - 不阻塞用户
    }
    live.style.background = 'var(--bull)';
    showError(null);
  } catch (err) {
    showError(`数据加载失败: ${err.message}. 请确认后端已生成 data/dashboard.json`);
    live.style.background = 'var(--bear)';
    console.error(err);
  }
}

function showError(msg) {
  const box = document.getElementById('errorBox');
  if (msg) {
    box.style.display = 'block';
    box.textContent = '⚠️  ' + msg;
  } else {
    box.style.display = 'none';
  }
}

// ============================================
// 渲染主入口
// ============================================

function renderAll() {
  if (!dashboardData) return;
  renderTimestamp();
  renderMockBadge();
  renderHeroPanel();
  renderLayers();
  renderMetrics();
  renderCharts();
  renderRatios();
  renderFred();
}

function renderTimestamp() {
  const ts = new Date(dashboardData.timestamp);
  const opts = { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false };
  document.getElementById('updateTime').textContent =
    `${ts.toLocaleDateString('zh-CN')} ${ts.toLocaleTimeString('zh-CN', opts)}`;
}

function renderMockBadge() {
  const badge = document.getElementById('mockBadge');
  badge.style.display = dashboardData.is_mock ? 'inline-block' : 'none';
}

// ============================================
// 综合评分主面板
// ============================================

function renderHeroPanel() {
  const s = dashboardData.scoring;
  const colorClass = regimeColorClass(s.color);

  const scoreEl = document.getElementById('overallScore');
  scoreEl.textContent = (s.total_score > 0 ? '+' : '') + s.total_score;
  scoreEl.className = 'hero-score ' + colorClass;

  document.getElementById('regimeLabel').textContent = s.regime;
  document.getElementById('positionText').textContent = s.position_suggestion;

  // 滑块位置: -12 ~ +12 映射到 0% ~ 100%
  const marker = document.getElementById('scoreMarker');
  const pct = Math.max(0, Math.min(100, ((s.total_score + 12) / 24) * 100));
  marker.style.left = pct + '%';
  marker.className = 'score-marker ' + colorClass;
}

// ============================================
// 4 层信号
// ============================================

function renderLayers() {
  const grid = document.getElementById('layersGrid');
  const layers = dashboardData.scoring.layers;
  grid.innerHTML = '';

  const ORDER = ['layer1_price', 'layer2_volatility', 'layer3_structure', 'layer4_macro'];
  const ICONS = ['◆', '▲', '●', '■'];

  ORDER.forEach((key, idx) => {
    const layer = layers[key];
    if (!layer) return;

    const colorClass = colorClassFromScore(layer.score, layer.max);
    const progressPct = Math.max(0, Math.min(100, ((layer.score + layer.max) / (layer.max * 2)) * 100));

    const card = document.createElement('div');
    card.className = 'layer-card fade-in';

    const sign = layer.score > 0 ? '+' : '';
    const detailsHtml = layer.details.map(d =>
      `<div class="layer-detail-item">${d}</div>`
    ).join('');

    card.innerHTML = `
      <div class="layer-header">
        <div>
          <div class="layer-name">LAYER ${idx + 1} · ${ICONS[idx]}</div>
          <div class="layer-title">${layer.name}</div>
        </div>
        <div class="layer-score ${colorClass}">${sign}${layer.score}</div>
      </div>
      <div class="layer-progress">
        <div class="layer-progress-fill ${colorClass}" style="width: ${progressPct}%;"></div>
      </div>
      <div class="layer-details">${detailsHtml}</div>
    `;
    grid.appendChild(card);
  });
}

// ============================================
// 核心指标
// ============================================

function renderMetrics() {
  const grid = document.getElementById('metricsGrid');
  const data = dashboardData.data;
  grid.innerHTML = '';

  // 显示哪些 + 显示顺序
  const DISPLAY = [
    { key: 'QQQ', label: 'QQQ', desc: 'Nasdaq 100' },
    { key: 'SPY', label: 'SPY', desc: 'S&P 500' },
    { key: 'VIX', label: 'VIX', desc: '股市波动率' },
    { key: 'MOVE', label: 'MOVE', desc: '债市波动率' },
    { key: 'VVIX', label: 'VVIX', desc: '波动率的波动率' },
    { key: 'HYG', label: 'HYG', desc: '高收益债' },
    { key: 'TLT', label: 'TLT', desc: '20年+国债' },
    { key: 'JNK', label: 'JNK', desc: '高收益债' },
    { key: 'IEF', label: 'IEF', desc: '7-10年国债' },
    { key: 'LQD', label: 'LQD', desc: '投资级信用债' },
    { key: 'DXY', label: 'DXY', desc: '美元指数' },
    { key: 'GLD', label: 'GLD', desc: '黄金' },
  ];

  DISPLAY.forEach(item => {
    const d = data[item.key];
    if (!d) return;

    const changeClass = colorClassFromChange(d.change_pct);
    const cardClass = d.above_sma200 ? 'bull' : 'bear';

    const card = document.createElement('div');
    card.className = `metric-card ${cardClass}`;
    card.innerHTML = `
      <div class="metric-symbol">${item.label} · ${item.desc}</div>
      <div class="metric-price">${formatNumber(d.price, 2)}</div>
      <div class="metric-change">
        <span class="metric-change-pct ${changeClass}">${formatChange(d.change_pct)}</span>
        <span class="metric-sma">${d.above_sma200 ? '↑' : '↓'} 200SMA</span>
      </div>
    `;
    grid.appendChild(card);
  });
}

// ============================================
// 关键比率
// ============================================

function renderRatios() {
  const grid = document.getElementById('ratiosGrid');
  const r = dashboardData.ratios;
  grid.innerHTML = '';

  const RATIOS = [
    {
      key: 'VIX_VIX3M',
      name: 'VIX / VIX3M',
      desc: r.VIX_in_backwardation
        ? '⚠️ Backwardation 倒挂 - 市场恐慌'
        : '✓ Contango 正常 - 市场平静',
    },
    { key: 'HYG_IEF',  name: 'HYG / IEF',   desc: '风险偏好 (替代 JNK/TLT, 信号更纯)' },
    { key: 'JNK_TLT',  name: 'JNK / TLT',   desc: '经典风险偏好指标' },
    { key: 'QQQ_QQEW', name: 'QQQ / QQEW',  desc: '比率升高 = 大盘股独涨 (头重)' },
    { key: 'MAGS_RSP', name: 'MAGS / RSP',  desc: 'MAG7 vs 等权 S&P (集中度)' },
  ];

  RATIOS.forEach(item => {
    const v = r[item.key];
    if (v === undefined || v === null) return;

    const card = document.createElement('div');
    card.className = 'ratio-card';
    card.innerHTML = `
      <div class="ratio-name">${item.name}</div>
      <div class="ratio-value">${formatNumber(v, 3)}</div>
      <div class="ratio-desc">${item.desc}</div>
    `;
    grid.appendChild(card);
  });
}

// ============================================
// FRED 宏观
// ============================================

function renderFred() {
  const fred = dashboardData.fred || {};
  const keys = Object.keys(fred);
  const section = document.getElementById('fredSection');
  const grid = document.getElementById('fredGrid');

  if (keys.length === 0) {
    section.style.display = 'none';
    return;
  }

  section.style.display = 'flex';
  grid.innerHTML = '';

  keys.forEach(k => {
    const item = fred[k];
    const card = document.createElement('div');
    card.className = 'fred-card';
    card.innerHTML = `
      <div class="fred-name">${item.name} · ${k}</div>
      <div class="fred-value">${formatNumber(item.value, 2)}</div>
      <div class="fred-date">${item.date}</div>
    `;
    grid.appendChild(card);
  });
}

// ============================================
// 图表
// ============================================

const CHART_BASE_OPTS = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: {
      display: true,
      position: 'top',
      align: 'end',
      labels: {
        color: 'rgba(245, 245, 244, 0.6)',
        font: { family: 'JetBrains Mono', size: 11 },
        boxWidth: 12,
        boxHeight: 2,
        padding: 12,
      }
    },
    tooltip: {
      backgroundColor: 'rgba(20, 20, 20, 0.95)',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      borderWidth: 1,
      titleColor: '#f5f5f4',
      bodyColor: '#d1cfc5',
      titleFont: { family: 'JetBrains Mono', size: 11 },
      bodyFont: { family: 'JetBrains Mono', size: 12 },
      padding: 10,
      displayColors: true,
      boxPadding: 4,
      callbacks: {
        label: (ctx) => `${ctx.dataset.label}: ${formatNumber(ctx.parsed.y, 2)}`
      }
    }
  },
  scales: {
    x: {
      grid: { color: 'rgba(255, 255, 255, 0.04)', drawBorder: false },
      ticks: {
        color: 'rgba(245, 245, 244, 0.4)',
        font: { family: 'JetBrains Mono', size: 10 },
        maxTicksLimit: 6,
        maxRotation: 0,
      },
      border: { display: false },
    },
    y: {
      grid: { color: 'rgba(255, 255, 255, 0.04)', drawBorder: false },
      ticks: {
        color: 'rgba(245, 245, 244, 0.4)',
        font: { family: 'JetBrains Mono', size: 10 },
        callback: (v) => formatNumber(v, 0),
      },
      border: { display: false },
      position: 'right',
    }
  }
};

function renderCharts() {
  renderQqqChart();
  renderVixChart();
}

function renderQqqChart() {
  const ctx = document.getElementById('qqqChart');
  const hist = dashboardData.history?.QQQ || [];
  if (hist.length === 0) return;
  if (typeof Chart === 'undefined') {
    console.warn('Chart.js not loaded, skipping chart render');
    return;
  }

  if (qqqChartInstance) qqqChartInstance.destroy();

  const latest = hist[hist.length - 1];
  document.getElementById('qqqLatest').textContent = '$' + formatNumber(latest.close, 2);

  qqqChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: hist.map(h => h.date),
      datasets: [
        {
          label: 'QQQ Close',
          data: hist.map(h => h.close),
          borderColor: '#4ade80',
          backgroundColor: 'rgba(74, 222, 128, 0.06)',
          fill: true,
          borderWidth: 1.5,
          pointRadius: 0,
          pointHoverRadius: 4,
          tension: 0.1,
        },
        {
          label: '50 SMA',
          data: hist.map(h => h.sma50),
          borderColor: '#60a5fa',
          backgroundColor: 'transparent',
          borderWidth: 1,
          borderDash: [4, 4],
          pointRadius: 0,
          tension: 0.1,
        },
        {
          label: '200 SMA',
          data: hist.map(h => h.sma200),
          borderColor: '#f59e0b',
          backgroundColor: 'transparent',
          borderWidth: 1,
          pointRadius: 0,
          tension: 0.1,
        },
      ],
    },
    options: CHART_BASE_OPTS,
  });
}

function renderVixChart() {
  const ctx = document.getElementById('vixChart');
  const hist = dashboardData.history?.VIX || [];
  if (hist.length === 0) return;
  if (typeof Chart === 'undefined') return;

  if (vixChartInstance) vixChartInstance.destroy();

  const latest = hist[hist.length - 1];
  document.getElementById('vixLatest').textContent = formatNumber(latest.close, 2);

  vixChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: hist.map(h => h.date),
      datasets: [
        {
          label: 'VIX',
          data: hist.map(h => h.close),
          borderColor: '#fbbf24',
          backgroundColor: 'rgba(251, 191, 36, 0.06)',
          fill: true,
          borderWidth: 1.5,
          pointRadius: 0,
          pointHoverRadius: 4,
          tension: 0.1,
        },
      ],
    },
    options: {
      ...CHART_BASE_OPTS,
      plugins: {
        ...CHART_BASE_OPTS.plugins,
        annotation: undefined,  // 占位
      },
      scales: {
        ...CHART_BASE_OPTS.scales,
        y: {
          ...CHART_BASE_OPTS.scales.y,
          suggestedMin: 10,
          suggestedMax: 40,
        }
      }
    },
  });
}

// ============================================
// 启动
// ============================================

document.addEventListener('DOMContentLoaded', () => {
  loadData();
  // 自动每 5 分钟刷新一次
  setInterval(loadData, 5 * 60 * 1000);
});
