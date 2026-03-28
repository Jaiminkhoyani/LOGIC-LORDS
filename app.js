// ============================================================
//   LiveStock IQ — app.js
//   Frontend connected to Django REST API backend
//   API Base: http://127.0.0.1:8000/api/v1/
// ============================================================

'use strict';

const API_BASE = 'http://127.0.0.1:8000/api/v1';

// ===================== GLOBAL STATE =====================
const APP = {
  currentPage: 'dashboard',
  currentChart: 'temperature',
  simulation: true,
  simulationInterval: null,
  thresholds: { highTemp: 39.5, lowTemp: 37.5, minActivity: 30, minFeeding: 40 },
  herdChart: null,
  weeklyChart: null,
  donutChart: null,
  modalChart: null,
  currentFilter: 'all',
  alertFilter: 'all',
  selectedCattleId: null,
  cattleCache: [],
  alertsCache: [],
};

// ===================== API HELPERS =====================
async function apiFetch(endpoint, options = {}) {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`API error [${endpoint}]:`, err.message);
    return null;
  }
}

async function apiPost(endpoint, body) {
  return apiFetch(endpoint, { method: 'POST', body: JSON.stringify(body) });
}

async function apiPut(endpoint, body) {
  return apiFetch(endpoint, { method: 'PUT', body: JSON.stringify(body) });
}

// ===================== CHART DATA (FALLBACK) =====================
const HOURS = ['00','02','04','06','08','10','12','14','16','18','20','22'];
const CHART_DATA_LOCAL = {
  temperature: { label: 'Avg Herd Temperature (°C)', data: [38.2,38.1,38.0,38.3,38.5,38.8,38.9,38.7,38.9,39.1,38.8,38.6], color: '#ef4444', fill: 'rgba(239,68,68,0.12)' },
  activity:    { label: 'Avg Herd Activity (%)',      data: [55,40,30,45,72,80,75,85,78,70,65,60],                         color: '#22c55e', fill: 'rgba(34,197,94,0.12)' },
  feeding:     { label: 'Avg Feeding Index (%)',       data: [70,30,20,80,85,75,60,72,80,68,65,72],                         color: '#3b82f6', fill: 'rgba(59,130,246,0.12)' },
};
// Will be overwritten by API data if available
let CHART_DATA = JSON.parse(JSON.stringify(CHART_DATA_LOCAL));

// ===================== LOCAL CATTLE DATA (FALLBACK) =====================
const CATTLE_LOCAL = [
  { id: 'C001', cattle_id:'C001', name:'Ganga',       breed:'HF Cross',    age_years:4, sex:'F', temperature:39.8, activity:22, feeding:35, status:'sick',    lactating:true,  weight_kg:420, last_calved:'2025-11-03', notes:'Respiratory distress — treatment ongoing' },
  { id: 'C002', cattle_id:'C002', name:'Yamuna',      breed:'Sahiwal',      age_years:6, sex:'F', temperature:38.4, activity:78, feeding:85, status:'healthy',  lactating:true,  weight_kg:385, last_calved:'2026-01-18', notes:'All vitals normal' },
  { id: 'C003', cattle_id:'C003', name:'Kaveri',      breed:'Gir',          age_years:3, sex:'F', temperature:38.9, activity:91, feeding:72, status:'estrus',   lactating:false, weight_kg:360, last_calved:'—',          notes:'Estrus detected — high activity' },
  { id: 'C004', cattle_id:'C004', name:'Godavari',    breed:'HF Cross',    age_years:5, sex:'F', temperature:40.1, activity:18, feeding:28, status:'fever',    lactating:true,  weight_kg:440, last_calved:'2025-09-22', notes:'High fever — vet called' },
  { id: 'C005', cattle_id:'C005', name:'Saraswati',   breed:'Murrah',       age_years:7, sex:'F', temperature:38.5, activity:65, feeding:80, status:'healthy',  lactating:true,  weight_kg:510, last_calved:'2025-12-30', notes:'Stable' },
  { id: 'C006', cattle_id:'C006', name:'Narmada',     breed:'Jersey Cross', age_years:4, sex:'F', temperature:38.2, activity:70, feeding:90, status:'healthy',  lactating:true,  weight_kg:390, last_calved:'2026-02-05', notes:'Excellent feeder' },
  { id: 'C007', cattle_id:'C007', name:'Mahanadi',    breed:'Sahiwal',      age_years:2, sex:'F', temperature:38.7, activity:88, feeding:68, status:'estrus',   lactating:false, weight_kg:320, last_calved:'—',          notes:'First estrus cycle' },
  { id: 'C008', cattle_id:'C008', name:'Tapi',        breed:'Gir',          age_years:8, sex:'F', temperature:38.3, activity:55, feeding:77, status:'healthy',  lactating:true,  weight_kg:475, last_calved:'2025-10-14', notes:'Monitor activity' },
  { id: 'C009', cattle_id:'C009', name:'Krishna',     breed:'HF Cross',    age_years:5, sex:'F', temperature:39.2, activity:42, feeding:60, status:'sick',     lactating:true,  weight_kg:415, last_calved:'2025-08-10', notes:'Mild infection suspected' },
  { id: 'C010', cattle_id:'C010', name:'Alaknanda',   breed:'Sahiwal',      age_years:3, sex:'F', temperature:38.6, activity:72, feeding:82, status:'healthy',  lactating:false, weight_kg:345, last_calved:'—',          notes:'Growing well' },
  { id: 'C011', cattle_id:'C011', name:'Bhagirathi',  breed:'Murrah',       age_years:6, sex:'F', temperature:38.1, activity:80, feeding:91, status:'healthy',  lactating:true,  weight_kg:505, last_calved:'2026-01-01', notes:'Top producer' },
  { id: 'C012', cattle_id:'C012', name:'Betwa',       breed:'Jersey Cross', age_years:4, sex:'F', temperature:38.4, activity:68, feeding:79, status:'healthy',  lactating:true,  weight_kg:400, last_calved:'2025-11-20', notes:'Normal' },
  { id: 'C013', cattle_id:'C013', name:'Chambal',     breed:'Gir',          age_years:9, sex:'F', temperature:38.0, activity:50, feeding:70, status:'healthy',  lactating:true,  weight_kg:490, last_calved:'2025-07-05', notes:'Senior — monitor regularly' },
  { id: 'C014', cattle_id:'C014', name:'Sone',        breed:'HF Cross',    age_years:2, sex:'F', temperature:38.5, activity:84, feeding:76, status:'healthy',  lactating:false, weight_kg:310, last_calved:'—',          notes:'Energetic heifer' },
  { id: 'C015', cattle_id:'C015', name:'Tapti',       breed:'Sahiwal',      age_years:5, sex:'F', temperature:38.3, activity:73, feeding:83, status:'healthy',  lactating:true,  weight_kg:395, last_calved:'2025-12-10', notes:'Good milk yield' },
  { id: 'C016', cattle_id:'C016', name:'Mandakini',   breed:'Gir',          age_years:3, sex:'F', temperature:39.0, activity:38, feeding:45, status:'sick',     lactating:false, weight_kg:330, last_calved:'—',          notes:'Low feeding — check lameness' },
  { id: 'C017', cattle_id:'C017', name:'Pinakini',    breed:'Jersey Cross', age_years:7, sex:'F', temperature:38.1, activity:62, feeding:78, status:'healthy',  lactating:true,  weight_kg:455, last_calved:'2025-09-01', notes:'Stable' },
  { id: 'C018', cattle_id:'C018', name:'Periyar',     breed:'Murrah',       age_years:4, sex:'F', temperature:38.7, activity:75, feeding:87, status:'healthy',  lactating:true,  weight_kg:480, last_calved:'2026-02-25', notes:'Good milker' },
  { id: 'C019', cattle_id:'C019', name:'Penna',       breed:'HF Cross',    age_years:6, sex:'F', temperature:38.5, activity:69, feeding:80, status:'healthy',  lactating:true,  weight_kg:430, last_calved:'2025-10-30', notes:'Normal' },
  { id: 'C020', cattle_id:'C020', name:'Tungabhadra', breed:'Sahiwal',      age_years:3, sex:'F', temperature:38.2, activity:82, feeding:74, status:'healthy',  lactating:false, weight_kg:350, last_calved:'—',          notes:'Active and growing' },
  { id: 'C021', cattle_id:'C021', name:'Sharavathi',  breed:'Gir',          age_years:5, sex:'F', temperature:38.6, activity:66, feeding:85, status:'healthy',  lactating:true,  weight_kg:410, last_calved:'2025-11-15', notes:'Steady producer' },
  { id: 'C022', cattle_id:'C022', name:'Kabini',      breed:'HF Cross',    age_years:2, sex:'F', temperature:38.3, activity:86, feeding:71, status:'healthy',  lactating:false, weight_kg:300, last_calved:'—',          notes:'Young heifer — healthy' },
  { id: 'C023', cattle_id:'C023', name:'Kapila',      breed:'Murrah',       age_years:8, sex:'F', temperature:38.0, activity:48, feeding:65, status:'healthy',  lactating:true,  weight_kg:500, last_calved:'2025-08-20', notes:'Senior — lower activity normal' },
];
let CATTLE = [...CATTLE_LOCAL];

let ALERTS = [
  { id:'A001', cattleId:'C004', cattle_id:'C004', type:'critical', alert_type:'critical', icon:'🔥', title:'High Fever Detected — Godavari', description:'Temperature 40.1°C exceeds critical threshold. Immediate vet required.', time:'2 min ago', timestamp:Date.now()-120000 },
  { id:'A002', cattleId:'C001', cattle_id:'C001', type:'critical', alert_type:'critical', icon:'🤒', title:'Illness Suspected — Ganga', description:'Temp 39.8°C + low activity (22%) + poor feeding (35%). Likely infection.', time:'15 min ago', timestamp:Date.now()-900000 },
  { id:'A003', cattleId:'C003', cattle_id:'C003', type:'info',     alert_type:'info',     icon:'💜', title:'Estrus Detected — Kaveri', description:'Activity spike 91% sustained. Breeding window: next 6–18 hours.', time:'38 min ago', timestamp:Date.now()-2280000 },
  { id:'A004', cattleId:'C007', cattle_id:'C007', type:'info',     alert_type:'info',     icon:'💜', title:'Estrus Detected — Mahanadi', description:'First estrus cycle. High activity confirmed for 3+ hours.', time:'1 hr ago', timestamp:Date.now()-3600000 },
  { id:'A005', cattleId:'C009', cattle_id:'C009', type:'warning',  alert_type:'warning',  icon:'⚠️', title:'Mild Illness — Krishna', description:'Elevated temp (39.2°C) + reduced activity. Monitor closely.', time:'2 hrs ago', timestamp:Date.now()-7200000 },
  { id:'A006', cattleId:'C016', cattle_id:'C016', type:'warning',  alert_type:'warning',  icon:'🌿', title:'Low Feeding Alert — Mandakini', description:'Feeding 45% — below threshold. Check for lameness or dental issues.', time:'3 hrs ago', timestamp:Date.now()-10800000 },
];

// ===================== UTILITY =====================
function getRand(min, max, d = 1) { return parseFloat((Math.random()*(max-min)+min).toFixed(d)); }
function statusColor(s) { return {healthy:'#22c55e',sick:'#ef4444',fever:'#f59e0b',estrus:'#a855f7'}[s]||'#94a3b8'; }
function statusLabel(s) { return {healthy:'✅ Healthy',sick:'🤒 Sick',fever:'🔥 Fever',estrus:'💜 Estrus'}[s]||s; }
function getVitalColor(type, v) {
  if (type==='temp')     return v>=39.5?'#ef4444':v>=39.0?'#f59e0b':v<=37.8?'#3b82f6':'#22c55e';
  if (type==='activity') return v<30?'#ef4444':v<50?'#f59e0b':'#22c55e';
  if (type==='feeding')  return v<40?'#ef4444':v<55?'#f59e0b':'#22c55e';
  return '#22c55e';
}
function tempNorm(t) { return Math.min(100,Math.max(0,((t-37)/3)*100)); }
function showToast(msg, dur=3000) {
  const t=document.getElementById('toast');
  t.textContent=msg; t.classList.remove('hidden');
  setTimeout(()=>t.classList.add('hidden'),dur);
}
function updateClock() {
  const n=new Date();
  document.getElementById('clock').textContent=n.getHours().toString().padStart(2,'0')+':'+n.getMinutes().toString().padStart(2,'0');
}
function relativeTime(ts) {
  const diff=Date.now()-ts, m=Math.floor(diff/60000);
  if(m<1)return 'Just now'; if(m<60)return `${m} min ago`;
  const h=Math.floor(m/60); if(h<24)return `${h} hr ago`;
  return `${Math.floor(h/24)} day ago`;
}

// ===================== NAVIGATION =====================
function goToPage(page) {
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById('page-'+page).classList.add('active');
  document.getElementById('nav-'+page).classList.add('active');
  APP.currentPage=page;
  if(page==='analytics') initAnalyticsCharts();
  if(page==='cattle')    renderFullCattleList();
  if(page==='alerts')    renderFullAlerts();
}
function openAlerts()   { goToPage('alerts'); }
function openSettings() { goToPage('settings'); }

// ===================== SPLASH =====================
window.addEventListener('load', () => {
  updateClock();
  setInterval(updateClock, 30000);
  setTimeout(async () => {
    const splash = document.getElementById('splash-screen');
    splash.classList.add('fade-out');
    setTimeout(async () => {
      splash.style.display = 'none';
      document.getElementById('app').classList.remove('hidden');
      await loadDashboardFromAPI();
      startSimulation();
    }, 600);
  }, 2600);
});

// ===================== LOAD FROM API =====================
async function loadDashboardFromAPI() {
  // Try loading cattle from API
  const cattleRes = await apiFetch('/cattle/?page_size=100');
  if (cattleRes && cattleRes.results) {
    CATTLE = cattleRes.results.map(normalizeApiCattle);
    APP.cattleCache = CATTLE;
  }

  // Try loading alerts from API
  const alertRes = await apiFetch('/alerts/?is_resolved=false&page_size=50');
  if (alertRes && alertRes.results) {
    ALERTS = alertRes.results.map(normalizeApiAlert);
    APP.alertsCache = ALERTS;
  }

  // Try loading dashboard summary
  const dash = await apiFetch('/farm/dashboard/');
  if (dash) {
    document.getElementById('healthy-count').textContent = dash.healthy || 0;
    document.getElementById('alert-count').textContent   = (dash.sick||0) + (dash.fever||0);
    document.getElementById('estrus-count').textContent  = dash.estrus || 0;
    document.getElementById('alert-badge').textContent   = dash.critical_alerts || 0;
  }

  // Load analytics chart data
  const analytics = await apiFetch('/farm/analytics/');
  if (analytics && analytics.hourly) {
    const h = analytics.hourly;
    CHART_DATA.temperature.data = h.temperature;
    CHART_DATA.activity.data    = h.activity;
    CHART_DATA.feeding.data     = h.feeding;
    if (h.labels) CHART_DATA.temperature.labels = h.labels;
  }

  initDashboard();
}

function normalizeApiCattle(c) {
  return {
    id:         c.id,
    cattle_id:  c.cattle_id,
    name:       c.name,
    breed:      c.breed,
    sex:        c.sex,
    age_years:  c.age_years,
    weight_kg:  c.weight_kg,
    lactating:  c.lactating,
    last_calved: c.last_calved || '—',
    temperature: c.temperature,
    activity:   c.activity,
    feeding:    c.feeding,
    status:     c.status,
    notes:      c.notes || '',
    device:     c.device,
  };
}

function normalizeApiAlert(a) {
  return {
    id:          a.id,
    cattleId:    a.cattle_cid || a.cattle,
    cattle_id:   a.cattle_cid || a.cattle,
    type:        a.alert_type,
    alert_type:  a.alert_type,
    icon:        a.icon || '⚠️',
    title:       a.title,
    description: a.description,
    time:        relativeTime(new Date(a.created_at).getTime()),
    timestamp:   new Date(a.created_at).getTime(),
    is_resolved: a.is_resolved,
  };
}

// ===================== DASHBOARD =====================
function initDashboard() {
  renderSummary();
  renderActiveAlerts();
  renderCattleGrid();
  initHerdChart();
}

function renderSummary() {
  const counts = { healthy:0, alert:0, estrus:0 };
  CATTLE.forEach(c => {
    if(c.status==='healthy') counts.healthy++;
    if(c.status==='sick'||c.status==='fever') counts.alert++;
    if(c.status==='estrus') counts.estrus++;
  });
  document.getElementById('healthy-count').textContent = counts.healthy;
  document.getElementById('alert-count').textContent   = counts.alert;
  document.getElementById('estrus-count').textContent  = counts.estrus;
  document.getElementById('alert-badge').textContent   = ALERTS.filter(a=>(a.type||a.alert_type)==='critical').length;
}

function renderActiveAlerts() {
  const container = document.getElementById('active-alerts-list');
  const critical  = ALERTS.filter(a=>(a.type||a.alert_type)==='critical').slice(0,3);
  container.innerHTML = critical.length
    ? critical.map(alertCardHTML).join('')
    : `<p style="color:var(--text-muted);text-align:center;padding:14px">No critical alerts 🎉</p>`;
}

function alertCardHTML(a) {
  const type = a.type||a.alert_type;
  const cid  = a.cattleId||a.cattle_id;
  return `
    <div class="alert-card ${type}" onclick="openCattleModal('${cid}')">
      <div class="alert-icon">${a.icon||'⚠️'}</div>
      <div class="alert-body">
        <div class="alert-title">${a.title}</div>
        <div class="alert-desc">${a.description}</div>
        <div class="alert-time">${a.time}</div>
      </div>
      <span class="alert-badge-type ${type}">${type}</span>
    </div>`;
}

function renderCattleGrid() {
  const container = document.getElementById('cattle-grid');
  container.innerHTML = CATTLE.slice(0,6).map(cattleMiniCardHTML).join('');
}

function cattleMiniCardHTML(c) {
  const tc=getVitalColor('temp',c.temperature), ac=getVitalColor('activity',c.activity), fc=getVitalColor('feeding',c.feeding);
  const cid = c.cattle_id || c.id;
  return `
    <div class="cattle-mini-card status-${c.status}" onclick="openCattleModal('${cid}')">
      <div class="cattle-mini-top"><span class="cattle-id">${cid}</span><span class="cattle-status-dot dot-${c.status}"></span></div>
      <p class="cattle-name">🐄 ${c.name}</p>
      <div class="cattle-vitals">
        <div class="vital-row"><span class="vital-label">🌡️</span><div class="vital-bar-wrap"><div class="vital-bar" style="width:${tempNorm(c.temperature)}%;background:${tc}"></div></div><span class="vital-value" style="color:${tc}">${c.temperature}°</span></div>
        <div class="vital-row"><span class="vital-label">🏃</span><div class="vital-bar-wrap"><div class="vital-bar" style="width:${c.activity}%;background:${ac}"></div></div><span class="vital-value" style="color:${ac}">${c.activity}%</span></div>
        <div class="vital-row"><span class="vital-label">🌿</span><div class="vital-bar-wrap"><div class="vital-bar" style="width:${c.feeding}%;background:${fc}"></div></div><span class="vital-value" style="color:${fc}">${c.feeding}%</span></div>
      </div>
    </div>`;
}

// ===================== HERD CHART =====================
function initHerdChart() {
  const el = document.getElementById('herd-chart');
  if (!el) return;
  const ctx = el.getContext('2d');
  const d   = CHART_DATA[APP.currentChart];
  APP.herdChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: HOURS,
      datasets: [{ label:d.label, data:d.data, borderColor:d.color, backgroundColor:d.fill, fill:true, tension:0.4, pointRadius:3, pointBackgroundColor:d.color, borderWidth:2 }]
    },
    options: {
      responsive:true, maintainAspectRatio:false,
      plugins: { legend:{ display:false } },
      scales: {
        x: { ticks:{ color:'#475569', font:{ size:10 } }, grid:{ color:'rgba(255,255,255,0.04)' } },
        y: { ticks:{ color:'#475569', font:{ size:10 } }, grid:{ color:'rgba(255,255,255,0.04)' } },
      },
    }
  });
}

function switchChart(type, btn) {
  APP.currentChart=type;
  document.querySelectorAll('.chart-tab').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  const d=CHART_DATA[type];
  APP.herdChart.data.datasets[0].data=d.data;
  APP.herdChart.data.datasets[0].label=d.label;
  APP.herdChart.data.datasets[0].borderColor=d.color;
  APP.herdChart.data.datasets[0].backgroundColor=d.fill;
  APP.herdChart.data.datasets[0].pointBackgroundColor=d.color;
  APP.herdChart.update('active');
}

// ===================== CATTLE LIST =====================
function renderFullCattleList(filter=APP.currentFilter, search='') {
  const container=document.getElementById('full-cattle-list');
  let list=CATTLE;
  if(filter!=='all') list=list.filter(c=>c.status===filter);
  if(search) list=list.filter(c=>c.name.toLowerCase().includes(search.toLowerCase())||((c.cattle_id||c.id)||'').toLowerCase().includes(search.toLowerCase()));
  container.innerHTML=list.length ? list.map(cattleListItemHTML).join('') :
    `<p style="color:var(--text-muted);text-align:center;padding:30px">No cattle found.</p>`;
}

function cattleListItemHTML(c) {
  const cid=c.cattle_id||c.id;
  return `
    <div class="cattle-list-item status-${c.status}" onclick="openCattleModal('${cid}')">
      <span class="cli-avatar">🐄</span>
      <div class="cli-info">
        <p class="cli-name">${c.name} <span style="font-size:11px;color:var(--text-muted)">(${cid})</span></p>
        <p class="cli-id">${c.breed} • ${c.age_years} yrs • ${c.weight_kg} kg</p>
        <div class="cli-metrics">
          <span class="cli-badge" style="color:${getVitalColor('temp',c.temperature)}">🌡️ ${c.temperature}°C</span>
          <span class="cli-badge" style="color:${getVitalColor('activity',c.activity)}">🏃 ${c.activity}%</span>
          <span class="cli-badge" style="color:${getVitalColor('feeding',c.feeding)}">🌿 ${c.feeding}%</span>
        </div>
      </div>
      <div class="cli-status"><span class="status-pill ${c.status}">${statusLabel(c.status)}</span></div>
    </div>`;
}

function filterByStatus(status, btn) {
  APP.currentFilter=status;
  document.querySelectorAll('.filter-chips .chip').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  renderFullCattleList(status, document.getElementById('search-input')?.value||'');
}
function filterCattle() {
  renderFullCattleList(APP.currentFilter, document.getElementById('search-input').value);
}

// ===================== FULL ALERTS =====================
function renderFullAlerts(filter=APP.alertFilter) {
  const container=document.getElementById('full-alerts-list');
  let list=ALERTS;
  if(filter!=='all') list=list.filter(a=>(a.type||a.alert_type)===filter);
  container.innerHTML=list.length ? list.map(alertCardHTML).join('') :
    `<p style="color:var(--text-muted);text-align:center;padding:30px">No alerts.</p>`;
}
function filterAlerts(type, btn) {
  APP.alertFilter=type;
  document.querySelectorAll('.alert-filters .chip').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  renderFullAlerts(type);
}

// ===================== CATTLE MODAL =====================
async function openCattleModal(cid) {
  APP.selectedCattleId=cid;
  let c = CATTLE.find(x=>(x.cattle_id||x.id)===cid);
  if(!c) return;

  // Try fetching detailed cattle from API (includes vet records + alerts)
  const apiData = await apiFetch(`/cattle/${c.id || cid}/`);
  if(apiData) c = { ...c, ...normalizeApiCattle(apiData), vet_records: apiData.vet_records, alerts: apiData.alerts };

  // Try fetching sensor history from MongoDB (via API)
  let historyData = null;
  const histRes = await apiFetch(`/cattle/${c.id || cid}/history/?hours=12`);
  if(histRes && histRes.readings && histRes.readings.length > 0) historyData = histRes.readings;

  const modal   = document.getElementById('cattle-modal');
  const content = document.getElementById('modal-content');

  content.innerHTML = buildModalHTML(c);
  modal.classList.remove('hidden');

  // Render chart
  setTimeout(() => {
    const mctx=document.getElementById('modal-chart-canvas');
    if(!mctx) return;
    if(APP.modalChart) { APP.modalChart.destroy(); APP.modalChart=null; }
    const temps = historyData
      ? historyData.map(r=>r.temperature)
      : Array.from({length:12}, ()=>getRand(c.temperature-0.5, c.temperature+0.5));
    const labels = historyData
      ? historyData.map(r => new Date(r.timestamp).getHours()+':00')
      : HOURS;
    APP.modalChart = new Chart(mctx.getContext('2d'), {
      type:'line',
      data:{ labels, datasets:[{ data:temps, borderColor:getVitalColor('temp',c.temperature), backgroundColor:'rgba(239,68,68,0.1)', fill:true, tension:0.4, pointRadius:2, borderWidth:2 }] },
      options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}},
        scales:{ x:{ticks:{color:'#475569',font:{size:9}},grid:{color:'rgba(255,255,255,0.04)'}}, y:{min:37,max:41,ticks:{color:'#475569',font:{size:9}},grid:{color:'rgba(255,255,255,0.04)'}} } }
    });
  }, 50);
}

function buildModalHTML(c) {
  const cid = c.cattle_id || c.id;
  const vetHTML = (c.vet_records && c.vet_records.length > 0)
    ? c.vet_records.map(v => `<div class="history-item"><div class="h-dot" style="background:#3b82f6"></div><div><p class="h-text">${v.record_type}: ${v.diagnosis}</p><p class="h-time">${v.vet_name || 'Vet'} — ₹${v.cost}</p></div></div>`).join('')
    : `<p style="font-size:12px;color:var(--text-muted)">No vet records on file.</p>`;

  return `
    <div class="modal-cow-header">
      <div class="modal-cow-emoji">🐄</div>
      <div class="modal-cow-info">
        <h3>${c.name}</h3>
        <p>${cid} • ${c.breed} • ${c.age_years} yrs</p>
        <span class="status-pill ${c.status}" style="margin-top:6px;display:inline-block">${statusLabel(c.status)}</span>
      </div>
    </div>
    <div class="modal-vitals-grid">
      <div class="modal-vital"><div class="mv-icon">🌡️</div><div class="mv-value" style="color:${getVitalColor('temp',c.temperature)}">${c.temperature}°C</div><div class="mv-label">Temperature</div></div>
      <div class="modal-vital"><div class="mv-icon">🏃</div><div class="mv-value" style="color:${getVitalColor('activity',c.activity)}">${c.activity}%</div><div class="mv-label">Activity</div></div>
      <div class="modal-vital"><div class="mv-icon">🌿</div><div class="mv-value" style="color:${getVitalColor('feeding',c.feeding)}">${c.feeding}%</div><div class="mv-label">Feeding</div></div>
      <div class="modal-vital"><div class="mv-icon">⚖️</div><div class="mv-value">${c.weight_kg}</div><div class="mv-label">Weight (kg)</div></div>
      <div class="modal-vital"><div class="mv-icon">${c.lactating?'🥛':'—'}</div><div class="mv-value" style="font-size:13px">${c.lactating?'Yes':'No'}</div><div class="mv-label">Lactating</div></div>
      <div class="modal-vital"><div class="mv-icon">🗓️</div><div class="mv-value" style="font-size:11px">${c.last_calved||'—'}</div><div class="mv-label">Last Calved</div></div>
    </div>
    <p class="modal-chart-title">📈 Temperature (MongoDB — 12h)</p>
    <canvas id="modal-chart-canvas" class="modal-chart"></canvas>
    <div class="modal-history" style="margin-top:16px"><h4>📋 Notes</h4>
      <div style="background:var(--bg-card);border-radius:10px;padding:12px;font-size:12px;color:var(--text-secondary)">${c.notes||'No notes.'}</div>
    </div>
    <div class="modal-history"><h4>🩺 Vet Records</h4>${vetHTML}</div>
    <div class="modal-actions">
      <button class="modal-action-btn primary" onclick="callVet('${cid}')">📞 Call Vet</button>
      <button class="modal-action-btn secondary" onclick="markTreated('${cid}')">✅ Mark Treated</button>
    </div>`;
}

async function markTreated(cid) {
  const c = CATTLE.find(x=>(x.cattle_id||x.id)===cid);

  // Call API treat endpoint
  const res = await apiPost(`/cattle/${c.id || cid}/treat/`, {});

  // Update local state
  if(c) {
    c.status=res?.status||'healthy';
    c.temperature=parseFloat((38.0+Math.random()*0.9).toFixed(1));
    c.activity=Math.round(60+Math.random()*25);
    c.feeding=Math.round(65+Math.random()*25);
    c.notes='Treatment administered. Monitoring recovery.';
  }
  ALERTS=ALERTS.filter(a=>(a.cattleId||a.cattle_id)!==cid);
  closeCattleModal();
  renderSummary(); renderActiveAlerts(); renderCattleGrid();
  showToast(`✅ ${c?.name||cid} marked as treated.`);
}

function callVet(cid) {
  const c=CATTLE.find(x=>(x.cattle_id||x.id)===cid);
  closeCattleModal();
  showToast(`📞 Calling veterinarian for ${c?.name||cid}...`);
}

function closeModal(event) { if(event.target===document.getElementById('cattle-modal')) closeCattleModal(); }
function closeCattleModal() {
  document.getElementById('cattle-modal').classList.add('hidden');
  if(APP.modalChart) { APP.modalChart.destroy(); APP.modalChart=null; }
}

// ===================== ANALYTICS CHARTS =====================
async function initAnalyticsCharts() {
  const analytics = await apiFetch('/farm/analytics/');

  if(!APP.weeklyChart) {
    const wctx=document.getElementById('weekly-chart').getContext('2d');
    const wdata = analytics?.weekly || { labels:['Mon','Tue','Wed','Thu','Fri','Sat','Sun'], healthy:[20,19,18,21,20,19,18], sick:[3,4,5,2,3,4,5], estrus:[1,1,2,1,0,2,2] };
    APP.weeklyChart=new Chart(wctx,{
      type:'bar',
      data:{ labels:wdata.labels, datasets:[
        { label:'Healthy', data:wdata.healthy, backgroundColor:'rgba(34,197,94,0.7)',  borderRadius:6 },
        { label:'Sick/Fever', data:wdata.sick, backgroundColor:'rgba(239,68,68,0.7)', borderRadius:6 },
        { label:'Estrus',  data:wdata.estrus,  backgroundColor:'rgba(168,85,247,0.7)', borderRadius:6 },
      ]},
      options:{ responsive:true, maintainAspectRatio:false,
        plugins:{ legend:{ labels:{ color:'#94a3b8', font:{ size:10 } } } },
        scales:{ x:{ ticks:{color:'#475569',font:{size:10}},grid:{color:'rgba(255,255,255,0.04)'} }, y:{ticks:{color:'#475569',font:{size:10}},grid:{color:'rgba(255,255,255,0.04)'}} } }
    });
  }

  if(!APP.donutChart) {
    const dctx=document.getElementById('donut-chart').getContext('2d');
    const dist = analytics?.alert_dist || { Fever:5, 'Low Activity':4, 'Poor Feeding':3, Estrus:2 };
    APP.donutChart=new Chart(dctx,{
      type:'doughnut',
      data:{ labels:Object.keys(dist), datasets:[{ data:Object.values(dist),
        backgroundColor:['rgba(239,68,68,0.85)','rgba(245,158,11,0.85)','rgba(59,130,246,0.85)','rgba(168,85,247,0.85)'],
        borderColor:['#ef4444','#f59e0b','#3b82f6','#a855f7'], borderWidth:2 }]},
      options:{ responsive:true, maintainAspectRatio:false, cutout:'60%',
        plugins:{ legend:{ position:'right', labels:{ color:'#94a3b8', font:{size:11}, boxWidth:14 } } } }
    });
  }

  // Update analytics summary cards
  const dash = await apiFetch('/farm/dashboard/');
  if(dash) {
    const el=id=>document.getElementById(id);
    if(el('avg-temp'))     el('avg-temp').textContent    = dash.avg_temperature+'°C';
    if(el('avg-activity')) el('avg-activity').textContent = dash.avg_activity+'%';
    if(el('avg-feed'))     el('avg-feed').textContent     = dash.avg_feeding+'%';
    if(el('health-score')) el('health-score').textContent = dash.health_score+'/100';
  }
}

// ===================== SETTINGS =====================
const thresholdValues = { highTemp:39.5, lowTemp:37.5, minActivity:30, minFeeding:40 };

async function adjustThreshold(key, delta) {
  thresholdValues[key]=parseFloat((thresholdValues[key]+delta).toFixed(1));
  APP.thresholds[key]=thresholdValues[key];
  const suffix=(key==='highTemp'||key==='lowTemp')?'°C':'%';
  document.getElementById(key+'-val').textContent=thresholdValues[key]+suffix;

  // Persist to API
  const payloadKey = { highTemp:'high_temp', lowTemp:'low_temp', minActivity:'min_activity', minFeeding:'min_feeding' }[key];
  await apiPut('/thresholds/', { [payloadKey]: thresholdValues[key] });
  showToast(`⚙️ Threshold saved: ${thresholdValues[key]}${suffix}`);
}

function toggleSimulation() {
  const checked=document.getElementById('toggle-sim').checked;
  if(checked) startSimulation(); else stopSimulation();
}

// ===================== SENSOR SIMULATION (pushes to API) =====================
function startSimulation() {
  APP.simulation=true;
  const rate=parseInt(document.getElementById('refresh-rate')?.value||'10')*1000;
  APP.simulationInterval=setInterval(simulateSensorUpdate, rate);
}
function stopSimulation() {
  APP.simulation=false;
  if(APP.simulationInterval) clearInterval(APP.simulationInterval);
}

async function simulateSensorUpdate() {
  // Push simulated sensor readings to backend (which stores in MongoDB + updates SQLite)
  const pushPromises = CATTLE.map(async c => {
    const newTemp = parseFloat((c.temperature+getRand(-0.2,0.2)).toFixed(1));
    const newAct  = Math.min(100, Math.max(5, c.activity+Math.round(getRand(-8,8))));
    const newFeed = Math.min(100, Math.max(5, c.feeding+Math.round(getRand(-5,5))));
    const clampedTemp = Math.min(41,Math.max(37,newTemp));

    const payload = {
      cattle_id:   c.cattle_id||c.id,
      temperature: clampedTemp,
      activity:    newAct,
      feeding:     newFeed,
      battery_pct: c.device?.battery_pct||95,
      signal:      c.device?.signal_strength||85,
    };

    // Push to API (non-blocking)
    const res = await apiPost('/sensors/push/', payload);
    if(res) {
      c.temperature=clampedTemp; c.activity=newAct; c.feeding=newFeed;
      if(res.new_status) c.status=res.new_status;
    } else {
      // Offline: update locally only
      c.temperature=clampedTemp; c.activity=newAct; c.feeding=newFeed;
    }
  });

  await Promise.allSettled(pushPromises);

  // Refresh alerts from API
  const alertRes=await apiFetch('/alerts/?is_resolved=false&page_size=20');
  if(alertRes && alertRes.results) ALERTS=alertRes.results.map(normalizeApiAlert);

  // Update UI
  renderSummary();
  if(APP.currentPage==='dashboard') {
    renderActiveAlerts(); renderCattleGrid();
    if(APP.herdChart) {
      CHART_DATA[APP.currentChart].data=CHART_DATA[APP.currentChart].data.map(v=>parseFloat((v+getRand(-0.3,0.3)).toFixed(1)));
      APP.herdChart.update('active');
    }
  }
  if(APP.currentPage==='cattle') renderFullCattleList();
  if(APP.currentPage==='alerts') renderFullAlerts();
}

// ===================== THEME TOGGLE =====================
function toggleTheme() {
  const html = document.documentElement;
  const currentTheme = html.getAttribute('data-theme') || 'dark';
  const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

  html.setAttribute('data-theme', newTheme);
  localStorage.setItem('theme', newTheme);

  // Update button emoji
  const themeBtn = document.getElementById('theme-toggle');
  themeBtn.textContent = newTheme === 'dark' ? '🌙' : '☀️';
}

// Initialize theme on page load
function initTheme() {
  const savedTheme = localStorage.getItem('theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
  const themeBtn = document.getElementById('theme-toggle');
  if(themeBtn) {
    themeBtn.textContent = savedTheme === 'dark' ? '🌙' : '☀️';
  }
}

// ===================== COMMUNITY FEATURES =====================
// Mock community data (replace with API calls)
const MOCK_FARMERS = [
  { id: 1, name: 'Rajesh Kumar', location: 'Haryana', expertise: 'Dairy farming, vaccination', experience_years: 15, followers_count: 124, is_verified: true },
  { id: 2, name: 'Priya Singh', location: 'Punjab', expertise: 'Cattle breeding, nutrition', experience_years: 8, followers_count: 87, is_verified: false },
  { id: 3, name: 'Amit Patel', location: 'Gujarat', expertise: 'Organic farming, health management', experience_years: 12, followers_count: 156, is_verified: true },
];

const MOCK_POSTS = [
  {
    id: 1,
    farm_name: 'Green Valley Farm',
    category: 'experience',
    title: 'How I increased milk production by 25%',
    content: 'Started using the new feeding schedule and minerals supplement. Results were amazing!',
    likes_count: 45,
    comments_count: 12,
    views_count: 234,
    created_at: '2 hours ago'
  },
  {
    id: 2,
    farm_name: 'Happy Cattle Ranch',
    category: 'question',
    title: 'Best treatment for mastitis?',
    content: 'One of my cattle has been showing signs of mastitis. What preventive measures and treatments do you recommend?',
    likes_count: 23,
    comments_count: 8,
    views_count: 156,
    created_at: '4 hours ago'
  },
  {
    id: 3,
    farm_name: 'Sunny Hills Farm',
    category: 'success',
    title: 'Successfully used AI for early disease detection',
    content: 'Our herd health has improved significantly after implementing AI-based temperature monitoring.',
    likes_count: 67,
    comments_count: 18,
    views_count: 412,
    created_at: '1 day ago'
  },
];

function switchCommunityTab(tab, element) {
  // Hide all tabs
  document.getElementById('community-feed-tab').classList.add('hidden');
  document.getElementById('community-farmers-tab').classList.add('hidden');
  document.getElementById('community-connections-tab').classList.add('hidden');

  // Show selected tab
  document.getElementById('community-' + tab + '-tab').classList.remove('hidden');

  // Update button styles
  document.querySelectorAll('.filter-tab').forEach(btn => btn.classList.remove('active'));
  element.classList.add('active');

  // Load tab content
  if(tab === 'feed') loadCommunityFeed();
  else if(tab === 'farmers') loadFarmers();
  else if(tab === 'connections') loadConnections();
}

function loadCommunityFeed() {
  const container = document.getElementById('community-feed-tab');
  container.innerHTML = MOCK_POSTS.map(post => `
    <div class="community-post">
      <div class="post-header">
        <div class="post-author-avatar">${post.farm_name[0]}</div>
        <div class="post-author-info">
          <div class="post-author-name">${post.farm_name}</div>
          <div class="post-timestamp">${post.created_at}</div>
        </div>
        <span class="post-category-badge">${post.category.charAt(0).toUpperCase() + post.category.slice(1)}</span>
      </div>
      <h3 class="post-title">${post.title}</h3>
      <p class="post-content">${post.content}</p>
      <div class="post-stats">
        <div class="post-stat">❤️ ${post.likes_count} likes</div>
        <div class="post-stat">💬 ${post.comments_count} comments</div>
        <div class="post-stat">👁️ ${post.views_count} views</div>
      </div>
      <div class="post-actions">
        <button class="post-btn" onclick="likePost(${post.id})">❤️ Like</button>
        <button class="post-btn" onclick="commentPost(${post.id})">💬 Comment</button>
        <button class="post-btn">⤴️ Share</button>
      </div>
    </div>
  `).join('');
}

function loadFarmers() {
  const container = document.getElementById('farmers-list');
  if(!container) return;

  container.innerHTML = MOCK_FARMERS.map(farmer => `
    <div class="farmer-card" onclick="viewFarmerProfile(${farmer.id})">
      <div class="farmer-avatar">${farmer.name[0]}</div>
      <div class="farmer-info">
        <div class="farmer-name">${farmer.name}${farmer.is_verified ? '<span class="verified-badge">✓</span>' : ''}</div>
        <div class="farmer-bio">${farmer.expertise}</div>
        <div class="farmer-stats">📍 ${farmer.location} • ${farmer.experience_years} yrs exp. • ${farmer.followers_count} followers</div>
      </div>
    </div>
  `).join('');
}

function searchFarmers() {
  const query = document.getElementById('farmer-search').value.toLowerCase();
  const container = document.getElementById('farmers-list');
  if(!container) return;

  const filtered = MOCK_FARMERS.filter(f =>
    f.name.toLowerCase().includes(query) ||
    f.location.toLowerCase().includes(query) ||
    f.expertise.toLowerCase().includes(query)
  );

  container.innerHTML = filtered.map(farmer => `
    <div class="farmer-card" onclick="viewFarmerProfile(${farmer.id})">
      <div class="farmer-avatar">${farmer.name[0]}</div>
      <div class="farmer-info">
        <div class="farmer-name">${farmer.name}${farmer.is_verified ? '<span class="verified-badge">✓</span>' : ''}</div>
        <div class="farmer-bio">${farmer.expertise}</div>
        <div class="farmer-stats">📍 ${farmer.location} • ${farmer.experience_years} yrs exp. • ${farmer.followers_count} followers</div>
      </div>
    </div>
  `).join('');
}

function loadConnections() {
  const container = document.getElementById('community-connections-tab');
  container.innerHTML = `
    <div style="text-align: center; padding: 40px 20px; color: var(--text-muted);">
      <p style="font-size: 32px; margin-bottom: 10px;">🤝</p>
      <h3 style="color: var(--text-secondary); margin-bottom: 5px;">Connect with Farmers</h3>
      <p style="font-size: 13px;">Send connection requests to other farmers from the Farmers tab to start collaborating!</p>
    </div>
  `;
}

function viewFarmerProfile(farmerId) {
  const farmer = MOCK_FARMERS.find(f => f.id === farmerId);
  if(!farmer) return;

  showToast(`Viewing profile of ${farmer.name}`);
  // In a real app, you would navigate to a detailed profile page
}

function likePost(postId) {
  showToast('Post liked! ❤️');
}

function commentPost(postId) {
  const comment = prompt('What would you like to say?');
  if(comment) showToast('Comment posted! 💬');
}

// Initialize theme when page loads
window.addEventListener('DOMContentLoaded', initTheme);
