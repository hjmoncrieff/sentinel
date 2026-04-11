# Country Profile Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign `showCountryProfile()` with a radar chart, stacked event pulse bar, structural trend annex, and a new `showSpecialMonitor()` deep-dive view for Colombia, Venezuela, El Salvador, and Mexico.

**Architecture:** All changes are confined to `index.html`. Part A replaces the country profile body with an 8-section layout (header → radar → context → reference band → event pulse → events → structural trends). Part B adds `SPECIAL_MONITOR_MILESTONES` data and a `showSpecialMonitor()` function that renders a dark-themed card with an SVG horizontal timeline, filter tabs, compact event list, and key data strip.

**Tech Stack:** Chart.js 4.4.1 (already loaded), SVG DOM API, existing data globals (`countryMonitorsByCountry`, `_vdemData`, `_wbData`, `allEvents`), DM Sans / DM Mono (already loaded).

**Dev server:** `python3 -m http.server 8000` from repo root — visit `http://localhost:8000`.

---

## Part A — Country Profile Redesign

---

### Task 1: CSS — New Profile Layout Classes

**Files:**
- Modify: `index.html` — CSS block (before `</style>`, around line 1408)

Add all new CSS needed for the redesigned profile. Find the `/* ── PROSE TEXT JUSTIFICATION ──` block near the end of the `<style>` section and insert the following block immediately before it.

- [ ] **Step 1: Add CSS**

Locate this comment in the `<style>` block:
```
/* ── PROSE TEXT JUSTIFICATION ──────────────────────────────── */
```

Insert the following CSS block immediately before that comment:

```css
/* ── COUNTRY PROFILE v2 ───────────────────────────────────── */
/* Header */
.cp2-hdr { padding: 14px 20px 12px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 10px; flex-wrap: wrap; background: linear-gradient(180deg, rgba(184,150,62,0.05), transparent); }
.cp2-back { font-family: var(--mono); font-size: 9px; letter-spacing: 1px; text-transform: uppercase; color: var(--text-muted); background: none; border: none; cursor: pointer; padding: 0; }
.cp2-back:hover { color: var(--slate); }
.cp2-name { font-family: var(--serif); font-size: 22px; font-weight: 500; color: var(--slate); line-height: 1; }
.cp2-sub { font-family: var(--mono); font-size: 9px; color: var(--text-muted); letter-spacing: 0.5px; margin-top: 2px; }
.cp2-cmr-pill { margin-left: auto; font-family: var(--mono); font-size: 8px; letter-spacing: 1.2px; text-transform: uppercase; padding: 3px 10px; border-radius: 2px; border: 1px solid; }
.cp2-cmr-pill.stable      { color: #2d6e52; border-color: rgba(45,110,82,0.35); background: rgba(45,110,82,0.07); }
.cp2-cmr-pill.strained    { color: #8a6e1f; border-color: rgba(184,150,62,0.35); background: rgba(184,150,62,0.07); }
.cp2-cmr-pill.crisis      { color: #8a3a2f; border-color: rgba(163,55,47,0.35); background: rgba(163,55,47,0.07); }
.cp2-cmr-pill.authoritarian{ color: #6a2f6a; border-color: rgba(106,47,106,0.35); background: rgba(106,47,106,0.07); }
.cp2-sm-btn { font-family: var(--mono); font-size: 8px; letter-spacing: 1px; text-transform: uppercase; color: var(--coup); background: rgba(184,50,50,0.08); border: 1px solid rgba(184,50,50,0.25); padding: 3px 9px; border-radius: 2px; cursor: pointer; }
.cp2-sm-btn:hover { background: rgba(184,50,50,0.14); }

/* Summary strip */
.cp2-summary { display: grid; grid-template-columns: 1fr auto; gap: 16px; align-items: start; padding: 16px 20px; border-bottom: 1px solid var(--border); }
.cp2-summary-text { font-size: 13px; line-height: 1.8; color: var(--text-dim); font-weight: 300; }
.cp2-risk-box { min-width: 130px; text-align: right; border: 1px solid var(--border); padding: 10px 14px; background: rgba(255,255,255,0.4); }
.cp2-risk-kicker { font-family: var(--mono); font-size: 8px; letter-spacing: 1.2px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 4px; }
.cp2-risk-value { font-family: var(--serif); font-size: 32px; line-height: 1; color: var(--slate); }
.cp2-risk-note { font-family: var(--mono); font-size: 9px; color: var(--text-muted); margin-top: 3px; line-height: 1.4; }

/* Radar section */
.cp2-radar-section { display: grid; grid-template-columns: 278px 1fr; gap: 0; border-bottom: 1px solid var(--border); }
.cp2-radar-canvas-wrap { padding: 16px 16px 14px; display: flex; align-items: center; justify-content: center; border-right: 1px solid var(--border); }
.cp2-score-table { padding: 14px 18px; display: flex; flex-direction: column; gap: 0; }
.cp2-grp-lbl { font-family: var(--mono); font-size: 8px; letter-spacing: 1.4px; text-transform: uppercase; color: var(--text-muted); padding: 10px 0 6px; border-bottom: 1px solid var(--border); margin-bottom: 2px; }
.cp2-grp-lbl:first-child { padding-top: 0; }
.cp2-score-row { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid rgba(216,208,196,0.5); font-size: 11.5px; }
.cp2-score-row:last-child { border-bottom: none; }
.cp2-score-name { flex: 1; color: var(--text-dim); font-weight: 300; min-width: 0; }
.cp2-score-val { font-family: var(--mono); font-size: 11px; color: var(--text); min-width: 44px; text-align: right; }
.cp2-score-trend { font-family: var(--mono); font-size: 8px; letter-spacing: 0.5px; text-transform: uppercase; min-width: 40px; text-align: right; }
.cp2-rank-badge { font-family: var(--mono); font-size: 7.5px; letter-spacing: 0.3px; padding: 1px 5px; border-radius: 2px; white-space: nowrap; }
.cp2-rank-badge.r-hi { background: rgba(163,55,47,0.12); color: var(--coup); border: 1px solid rgba(163,55,47,0.25); }
.cp2-rank-badge.r-md { background: rgba(196,110,18,0.10); color: var(--purge); border: 1px solid rgba(196,110,18,0.22); }
.cp2-rank-badge.r-lo { background: rgba(45,110,82,0.10); color: var(--reform); border: 1px solid rgba(45,110,82,0.22); }

/* Sources band */
.cp2-sources-band { background: #f5f1ea; border-bottom: 1px solid var(--border); padding: 6px 20px; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.cp2-sources-label { font-family: var(--mono); font-size: 7.5px; letter-spacing: 1.2px; text-transform: uppercase; color: var(--text-muted); }
.cp2-sources-item { font-family: var(--mono); font-size: 7.5px; color: var(--text-faint); }
.cp2-sources-sep { color: var(--border2); font-size: 9px; }

/* Context / Watch */
.cp2-context-band { display: grid; grid-template-columns: 1fr 1fr; gap: 0; border-bottom: 1px solid var(--border); }
.cp2-context-col { padding: 14px 18px; }
.cp2-context-col:first-child { border-right: 1px solid var(--border); }
.cp2-col-kicker { font-family: var(--mono); font-size: 8px; letter-spacing: 1.4px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 8px; }
.cp2-context-text { font-size: 12px; line-height: 1.75; color: var(--text-dim); font-weight: 300; }
.cp2-watch-item { font-size: 12px; line-height: 1.7; color: var(--text-dim); padding: 5px 0; border-bottom: 1px solid rgba(216,208,196,0.5); font-weight: 300; }
.cp2-watch-item:last-child { border-bottom: none; }

/* Reference band */
.cp2-ref-band { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0; border-bottom: 1px solid var(--border); }
.cp2-ref-col { padding: 14px 18px; }
.cp2-ref-col:not(:last-child) { border-right: 1px solid var(--border); }
.cp2-ref-col .cp2-col-kicker { margin-bottom: 10px; }
.cp2-ref-row { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; padding: 5px 0; border-bottom: 1px solid rgba(216,208,196,0.5); font-size: 11.5px; }
.cp2-ref-row:last-child { border-bottom: none; }
.cp2-ref-label { color: var(--text-dim); font-weight: 300; font-size: 11px; }
.cp2-ref-val { font-family: var(--mono); font-size: 10.5px; color: var(--text); text-align: right; }
.cp2-pos-title { font-family: var(--mono); font-size: 8px; letter-spacing: 0.5px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 1px; }
.cp2-pos-name { font-size: 11.5px; color: var(--text); line-height: 1.4; }
.cp2-pos-item { padding: 5px 0; border-bottom: 1px solid rgba(216,208,196,0.5); }
.cp2-pos-item:last-child { border-bottom: none; }
.cp2-elect-type { font-family: var(--mono); font-size: 8px; letter-spacing: 0.7px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 2px; }
.cp2-elect-date { font-family: var(--serif); font-size: 18px; color: var(--slate); line-height: 1.1; }
.cp2-elect-note { font-size: 11px; color: var(--text-dim); margin-top: 4px; line-height: 1.5; }

/* Event Pulse */
.cp2-pulse-section { padding: 12px 20px 10px; border-bottom: 1px solid var(--border); }
.cp2-pulse-hdr { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.cp2-pulse-label { font-family: var(--mono); font-size: 8px; letter-spacing: 1.2px; text-transform: uppercase; color: var(--text-muted); }
.cp2-pulse-legend { display: flex; align-items: center; gap: 12px; }
.cp2-pulse-legend-item { display: flex; align-items: center; gap: 5px; font-family: var(--mono); font-size: 7.5px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.4px; }
.cp2-pulse-swatch { width: 10px; height: 8px; border-radius: 1px; }
.cp2-pulse-canvas-wrap { position: relative; width: 100%; height: 52px; }

/* Live Events */
.cp2-events-section { padding: 0; border-bottom: 1px solid var(--border); }
.cp2-events-hdr { display: flex; align-items: center; justify-content: space-between; padding: 10px 20px 8px; border-bottom: 1px solid var(--border); }
.cp2-events-label { font-family: var(--mono); font-size: 8px; letter-spacing: 1.2px; text-transform: uppercase; color: var(--text-muted); }
.cp2-events-count { font-family: var(--mono); font-size: 9px; color: var(--text-faint); }

/* Structural Trends */
.cp2-trends-strip { background: #f0ebe2; border-top: 1px solid var(--border); display: flex; gap: 0; }
.cp2-trend-cell { flex: 1; padding: 12px 16px; border-right: 1px solid var(--border); }
.cp2-trend-cell:last-child { border-right: none; }
.cp2-trend-kicker { font-family: var(--mono); font-size: 7.5px; letter-spacing: 1px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 4px; }
.cp2-trend-value { font-family: var(--serif); font-size: 22px; color: var(--slate); line-height: 1; }
.cp2-trend-delta { font-family: var(--mono); font-size: 9px; margin-top: 3px; }
.cp2-trend-delta.up   { color: var(--coup); }
.cp2-trend-delta.down { color: var(--reform); }
.cp2-trend-delta.neutral { color: var(--text-muted); }
```

- [ ] **Step 2: Verify — open in browser**

Navigate to `http://localhost:8000`, open the Country Profiles tab, click any country. The profile should still render (unchanged — new CSS classes are unused yet). No console errors from CSS.

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "style: add cp2 CSS classes for redesigned country profile"
```

---

### Task 2: Helper Functions — Data Lookups and Rank Badges

**Files:**
- Modify: `index.html` — JS section, near the existing `getCountryRiskConstruct` helpers (around line 2972)

These functions compute the six radar axis scores and rank badges.

- [ ] **Step 1: Add helper functions**

Find the function `getCountryPredictiveSummary` (around line 2978) and insert the following block immediately after its closing brace:

```js
// ── CP v2 DATA HELPERS ─────────────────────────────────────────

function cpGetVdem(name) {
  if (!_vdemData) return null;
  return _vdemData.countries.find(c => c.country === name) || null;
}

function cpGetWb(name) {
  if (!_wbData) return null;
  return _wbData.countries.find(c => c.country === name) || null;
}

// Returns { regimeVuln, militarization, secFrag, democDeficit, physVuln, stateFrag }
// All 0-100, higher = more risk
function cpRadarScores(name) {
  const rv  = getCountryRiskConstruct(name, 'regime_vulnerability')?.score ?? 0;
  const mil = getCountryRiskConstruct(name, 'militarization')?.score ?? 0;
  const sf  = getCountryRiskConstruct(name, 'security_fragmentation')?.score ?? 0;

  const vd = cpGetVdem(name);
  const dem = vd ? Math.round((1 - (vd.polyarchy ?? 0.5)) * 100) : 0;
  const phys = vd ? Math.round((1 - (vd.physinteg ?? 0.5)) * 100) : 0;

  const wb = cpGetWb(name);
  const wgi = wb?.wgi_govt_effectiveness ?? 0;
  const frag = Math.min(100, Math.max(0, Math.round((1 - (wgi + 2) / 4) * 100)));

  return { regimeVuln: rv, militarization: mil, secFrag: sf, democDeficit: dem, physVuln: phys, stateFrag: frag };
}

// Returns rank (1 = highest risk) for each of the 6 axes across all 25 monitored countries
// Result shape: { regimeVuln: { [name]: rank }, militarization: {...}, ... }
function cpComputeRanks() {
  const COUNTRIES = Object.keys(COUNTRY_PROFILES);
  const axes = ['regimeVuln', 'militarization', 'secFrag', 'democDeficit', 'physVuln', 'stateFrag'];
  const allScores = {};
  COUNTRIES.forEach(c => { allScores[c] = cpRadarScores(c); });

  const ranks = {};
  axes.forEach(axis => {
    const sorted = [...COUNTRIES].sort((a, b) => (allScores[b][axis] ?? 0) - (allScores[a][axis] ?? 0));
    ranks[axis] = {};
    sorted.forEach((c, i) => { ranks[axis][c] = i + 1; });
  });
  return ranks;
}

function cpRankClass(rank) {
  if (rank <= 6)  return 'r-hi';
  if (rank <= 18) return 'r-md';
  return 'r-lo';
}

// Returns { score, delta, priorYear } for a V-Dem indicator (polyarchy or physinteg)
// delta is in risk-oriented direction: positive = more risk
function cpVdemDelta(name, field) {
  const vd = cpGetVdem(name);
  if (!vd) return { score: 0, delta: null, priorYear: null };
  const series = vd.series?.[field];
  if (!series?.length) return { score: Math.round((1 - (vd[field] ?? 0.5)) * 100), delta: null, priorYear: null };
  const sorted = [...series].sort((a, b) => b.year - a.year);
  const cur = sorted[0]; const prev = sorted[1];
  const curScore  = Math.round((1 - (cur.value  ?? 0.5)) * 100);
  const prevScore = prev ? Math.round((1 - (prev.value ?? 0.5)) * 100) : null;
  const delta = prevScore !== null ? +(curScore - prevScore).toFixed(1) : null;
  return { score: curScore, delta, priorYear: prev?.year ?? null };
}

// Returns { score, delta, priorYear } for WGI state fragility
function cpWgiDelta(name) {
  const wb = cpGetWb(name);
  if (!wb) return { score: 0, delta: null, priorYear: null };
  const series = wb.wgi_govt_effectiveness_series;
  if (!series?.length) {
    const wgi = wb.wgi_govt_effectiveness ?? 0;
    return { score: Math.min(100, Math.max(0, Math.round((1 - (wgi + 2) / 4) * 100))), delta: null, priorYear: null };
  }
  const sorted = [...series].filter(d => d.value != null).sort((a, b) => b.year - a.year);
  const cur = sorted[0]; const prev = sorted[1];
  const toFrag = v => Math.min(100, Math.max(0, Math.round((1 - (v + 2) / 4) * 100)));
  const curScore = toFrag(cur.value);
  const prevScore = prev ? toFrag(prev.value) : null;
  const delta = prevScore !== null ? +(curScore - prevScore).toFixed(1) : null;
  return { score: curScore, delta, priorYear: prev?.year ?? null };
}

// Returns { value, delta, priorYear } for GDP per capita (constant 2015 USD)
function cpGdpDelta(name) {
  const wb = cpGetWb(name);
  if (!wb) return { value: null, delta: null, priorYear: null };
  const series = (wb.gdp_per_capita_constant_2015_usd_series || []).filter(d => d.value != null);
  if (!series.length) return { value: null, delta: null, priorYear: null };
  const sorted = [...series].sort((a, b) => b.year - a.year);
  const cur = sorted[0]; const prev = sorted[1];
  const delta = prev ? +((cur.value - prev.value) / prev.value * 100).toFixed(1) : null;
  return { value: Math.round(cur.value), delta, priorYear: prev?.year ?? null };
}
```

- [ ] **Step 2: Verify — open browser console**

Open `http://localhost:8000`, go to Country Profiles tab, open the browser console (F12) and run:

```js
cpRadarScores('Colombia')
// Expected: object with 6 numeric properties, all 0-100
// e.g. { regimeVuln: 56, militarization: 38, secFrag: 78, democDeficit: ~30, physVuln: ~39, stateFrag: ~53 }

const r = cpComputeRanks(); r.regimeVuln['Colombia']
// Expected: a number 1-25

cpGdpDelta('Colombia')
// Expected: { value: 6864, delta: 0.5, priorYear: 2023 } (approximate)
```

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat: add cp2 data helper functions (radar scores, rank computation, deltas)"
```

---

### Task 3: Build Radar Section HTML

**Files:**
- Modify: `index.html` — JS section, after the helpers from Task 2

This function returns the HTML string for the radar canvas + score table. The chart is initialized separately via `setTimeout`.

- [ ] **Step 1: Add `cpBuildRadarSection(name, safeId)`**

Insert immediately after the Task 2 helper functions:

```js
function cpBuildRadarSection(name, safeId) {
  const scores = cpRadarScores(name);
  const ranks  = cpComputeRanks();
  const rv  = getCountryRiskConstruct(name, 'regime_vulnerability');
  const mil = getCountryRiskConstruct(name, 'militarization');
  const sf  = getCountryRiskConstruct(name, 'security_fragmentation');

  function rankBadge(axis, country) {
    const r = ranks[axis]?.[country] ?? 25;
    return `<span class="cp2-rank-badge ${cpRankClass(r)}">#${r} of 25</span>`;
  }
  function trendSpan(label) {
    const color = label === 'rising' ? 'var(--purge)' : label === 'easing' ? 'var(--reform)' : 'var(--text-muted)';
    return label ? `<span class="cp2-score-trend" style="color:${color};">${label}</span>` : '';
  }

  const constructRows = [
    { label: 'Regime Vulnerability', axis: 'regimeVuln', score: scores.regimeVuln, trend: rv?.trend_label },
    { label: 'Militarization',       axis: 'militarization', score: scores.militarization, trend: mil?.trend_label },
    { label: 'Security Fragmentation', axis: 'secFrag', score: scores.secFrag, trend: sf?.trend_label },
  ].map(r => `
    <div class="cp2-score-row">
      <span class="cp2-score-name">${r.label}</span>
      <span class="cp2-score-val">${Math.round(r.score)}/100</span>
      ${trendSpan(r.trend)}
      ${rankBadge(r.axis, name)}
    </div>`).join('');

  const indicatorRows = [
    { label: 'Democracy Deficit',     axis: 'democDeficit', score: scores.democDeficit },
    { label: 'Physical Vulnerability', axis: 'physVuln',    score: scores.physVuln },
    { label: 'State Fragility',        axis: 'stateFrag',   score: scores.stateFrag },
  ].map(r => `
    <div class="cp2-score-row">
      <span class="cp2-score-name">${r.label}</span>
      <span class="cp2-score-val">${Math.round(r.score)}/100</span>
      ${rankBadge(r.axis, name)}
    </div>`).join('');

  return `
    <div class="cp2-radar-section">
      <div class="cp2-radar-canvas-wrap">
        <canvas id="cp-radar-${safeId}" width="258" height="258"></canvas>
      </div>
      <div class="cp2-score-table">
        <div class="cp2-grp-lbl">Risk Constructs</div>
        ${constructRows}
        <div class="cp2-grp-lbl">Structural Indicators</div>
        ${indicatorRows}
      </div>
    </div>
    <div class="cp2-sources-band">
      <span class="cp2-sources-label">Sources</span>
      <span class="cp2-sources-sep">·</span>
      <span class="cp2-sources-item">Risk constructs — SENTINEL Monitor</span>
      <span class="cp2-sources-sep">·</span>
      <span class="cp2-sources-item">Democracy · Physical Integrity — V-Dem 2024</span>
      <span class="cp2-sources-sep">·</span>
      <span class="cp2-sources-item">State Fragility — WGI 2023</span>
    </div>`;
}
```

- [ ] **Step 2: Commit**

```bash
git add index.html
git commit -m "feat: add cpBuildRadarSection() HTML builder"
```

---

### Task 4: Initialize Radar Chart.js Instance

**Files:**
- Modify: `index.html` — JS section, after `cpBuildRadarSection`

Add the Chart.js initialization function and the module-level instance variables.

- [ ] **Step 1: Add instance variables near top of script**

Find the line `let _cpRadarChart, _cpPulseChart;` — if it doesn't exist, find the line `let _currentCpName` (around line 5273) and add before it:

```js
let _cpRadarChart = null, _cpPulseChart = null;
```

- [ ] **Step 2: Add `cpInitRadar(name, safeId)` function**

Insert after `cpBuildRadarSection`:

```js
function cpInitRadar(name, safeId) {
  if (_cpRadarChart) { try { _cpRadarChart.destroy(); } catch(e){} _cpRadarChart = null; }
  const canvas = document.getElementById(`cp-radar-${safeId}`);
  if (!canvas) return;
  const scores = cpRadarScores(name);
  const data = [
    scores.regimeVuln,
    scores.militarization,
    scores.secFrag,
    scores.democDeficit,
    scores.physVuln,
    scores.stateFrag,
  ];
  _cpRadarChart = new Chart(canvas, {
    type: 'radar',
    data: {
      labels: [
        ['Regime', 'Vulnerability'],
        ['Militarization'],
        ['Security', 'Fragmentation'],
        ['Democracy', 'Deficit'],
        ['Physical', 'Vulnerability'],
        ['State', 'Fragility'],
      ],
      datasets: [{
        data,
        borderColor: 'rgba(184,50,50,0.7)',
        backgroundColor: 'rgba(180,50,50,0.10)',
        borderWidth: 1.5,
        pointRadius: 3,
        pointBackgroundColor: 'rgba(184,50,50,0.7)',
      }],
    },
    options: {
      responsive: false,
      maintainAspectRatio: false,
      layout: { padding: 10 },
      scales: {
        r: {
          min: 0, max: 100,
          ticks: { display: false, stepSize: 25 },
          grid: { color: '#e8e0d4' },
          angleLines: { color: '#e8e0d4' },
          pointLabels: {
            color: '#7a746c',
            font: { size: 9, family: "'DM Mono', monospace" },
          },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: items => {
              const lbl = items[0].label;
              return Array.isArray(lbl) ? lbl.join(' ') : lbl;
            },
            label: item => `${item.raw.toFixed(1)} / 100`,
          },
        },
      },
    },
  });
}
```

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat: add cpInitRadar() Chart.js radar initializer"
```

---

### Task 5: Event Pulse HTML Builder and Chart Init

**Files:**
- Modify: `index.html` — JS section, after `cpInitRadar`

- [ ] **Step 1: Add `cpBuildPulseSection(name, safeId)` and `cpInitPulse(name, safeId)`**

```js
function cpBuildPulseSection(name, safeId) {
  const now = new Date();
  const months = [];
  for (let i = 11; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    months.push({ year: d.getFullYear(), month: d.getMonth(), label: d.toLocaleString('en', { month: 'short' }) });
  }
  const rangeLabel = `${months[0].label} ${months[0].year} – ${months[11].label} ${months[11].year}`;
  return `
    <div class="cp2-pulse-section">
      <div class="cp2-pulse-hdr">
        <span class="cp2-pulse-label">Event Pulse — ${rangeLabel}</span>
        <div class="cp2-pulse-legend">
          <div class="cp2-pulse-legend-item"><div class="cp2-pulse-swatch" style="background:rgba(168,64,0,0.5)"></div>Conflict / OC</div>
          <div class="cp2-pulse-legend-item"><div class="cp2-pulse-swatch" style="background:#ccc5b9"></div>Other</div>
        </div>
      </div>
      <div class="cp2-pulse-canvas-wrap">
        <canvas id="cp-pulse-${safeId}" style="width:100%;height:52px;"></canvas>
      </div>
    </div>`;
}

function cpInitPulse(name, safeId) {
  if (_cpPulseChart) { try { _cpPulseChart.destroy(); } catch(e){} _cpPulseChart = null; }
  const canvas = document.getElementById(`cp-pulse-${safeId}`);
  if (!canvas) return;

  const now = new Date();
  const months = [];
  for (let i = 11; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    months.push({ year: d.getFullYear(), month: d.getMonth(), label: d.toLocaleString('en', { month: 'short' }) });
  }

  const hot   = months.map(() => 0);
  const other = months.map(() => 0);

  (allEvents || []).filter(e => e.country === name).forEach(ev => {
    const d = new Date(ev.date);
    const idx = months.findIndex(m => m.year === d.getFullYear() && m.month === d.getMonth());
    if (idx === -1) return;
    if (ev.type === 'conflict' || ev.type === 'oc') hot[idx]++;
    else other[idx]++;
  });

  const labels = months.map(m => m.label);
  _cpPulseChart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Conflict/OC', data: hot,   backgroundColor: 'rgba(168,64,0,0.5)', stack: 's' },
        { label: 'Other',       data: other, backgroundColor: '#ccc5b9',             stack: 's' },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } },
      scales: {
        x: { stacked: true, grid: { display: false }, ticks: { font: { size: 8, family: "'DM Mono', monospace" }, color: '#b5ab9d' } },
        y: { stacked: true, display: false },
      },
    },
  });
}
```

- [ ] **Step 2: Commit**

```bash
git add index.html
git commit -m "feat: add cpBuildPulseSection() and cpInitPulse() event pulse bar chart"
```

---

### Task 6: Structural Trends Section

**Files:**
- Modify: `index.html` — JS section, after `cpInitPulse`

- [ ] **Step 1: Add `cpBuildStructuralTrends(name)`**

```js
function cpBuildStructuralTrends(name) {
  const dem  = cpVdemDelta(name, 'polyarchy');
  const phys = cpVdemDelta(name, 'physinteg');
  const frag = cpWgiDelta(name);
  const gdp  = cpGdpDelta(name);

  function deltaSpan(delta, priorYear, invertGood) {
    if (delta === null) return `<div class="cp2-trend-delta neutral">— no prior data</div>`;
    const isRisk = invertGood ? delta > 0 : delta < 0;  // for GDP: positive=good
    const cls = isRisk ? 'up' : delta === 0 ? 'neutral' : 'down';
    const sign = delta > 0 ? '+' : '';
    return `<div class="cp2-trend-delta ${cls}">${sign}${delta} vs ${priorYear}</div>`;
  }

  const demDelta  = dem.delta !== null  ? deltaSpan(dem.delta,  dem.priorYear,  false) : `<div class="cp2-trend-delta neutral">—</div>`;
  const physDelta = phys.delta !== null ? deltaSpan(phys.delta, phys.priorYear, false) : `<div class="cp2-trend-delta neutral">—</div>`;
  const fragDelta = frag.delta !== null ? deltaSpan(frag.delta, frag.priorYear, false) : `<div class="cp2-trend-delta neutral">—</div>`;

  let gdpVal = '—', gdpDeltaHtml = `<div class="cp2-trend-delta neutral">—</div>`;
  if (gdp.value !== null) {
    gdpVal = '$' + gdp.value.toLocaleString();
    if (gdp.delta !== null) {
      const sign = gdp.delta > 0 ? '+' : '';
      const cls = gdp.delta > 0 ? 'down' : gdp.delta < 0 ? 'up' : 'neutral'; // GDP: positive=good(down=green)
      gdpDeltaHtml = `<div class="cp2-trend-delta ${cls}">${sign}${gdp.delta}% vs ${gdp.priorYear}</div>`;
    }
  }

  return `
    <div class="cp2-trends-strip">
      <div class="cp2-trend-cell">
        <div class="cp2-trend-kicker">Democracy Deficit</div>
        <div class="cp2-trend-value">${dem.score}/100</div>
        ${demDelta}
      </div>
      <div class="cp2-trend-cell">
        <div class="cp2-trend-kicker">Physical Vulnerability</div>
        <div class="cp2-trend-value">${phys.score}/100</div>
        ${physDelta}
      </div>
      <div class="cp2-trend-cell">
        <div class="cp2-trend-kicker">State Fragility</div>
        <div class="cp2-trend-value">${frag.score}/100</div>
        ${fragDelta}
      </div>
      <div class="cp2-trend-cell">
        <div class="cp2-trend-kicker">GDP per Capita</div>
        <div class="cp2-trend-value">${gdpVal}</div>
        ${gdpDeltaHtml}
      </div>
    </div>`;
}
```

- [ ] **Step 2: Commit**

```bash
git add index.html
git commit -m "feat: add cpBuildStructuralTrends() four-cell annex strip"
```

---

### Task 7: Rewrite `showCountryProfile()`

**Files:**
- Modify: `index.html` — `showCountryProfile(name)` function (around line 5050)

Replace the entire function body with the new 8-section layout. The existing function currently builds `topBrief`, `middleBand`, `referenceBand`, and conditionally clones special profile blocks.

- [ ] **Step 1: Replace `showCountryProfile`**

Find the entire function from `function showCountryProfile(name){` to its closing `}` (ends around line 5278). Replace it with:

```js
function showCountryProfile(name) {
  document.querySelectorAll('.cp-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.country === name);
  });
  const regional   = document.getElementById('cp-regional');
  const countryDiv = document.getElementById('cp-country');
  const prof = COUNTRY_PROFILES[name];
  if (!prof) return;

  const safeId   = name.replace(/ /g, '_');
  const summary  = getCountryPredictiveSummary(name);
  const stats    = COUNTRY_STATS[name]   || { spending: '—', personnel: '—', usAid: '—' };
  const positions = COUNTRY_POSITIONS[name] || [];
  const election = COUNTRY_ELECTIONS[name] || null;
  const watch    = COUNTRY_WATCH[name]   || '';
  const overallRiskScore = Number(summary?.overall_risk_score) || 0;
  const overallRiskTone  = getOverallRiskTone(overallRiskScore);

  // ── 1. Header ────────────────────────────────────────────────
  const cmrPillClass = (prof.cmrClass || 'stable').toLowerCase();
  const smBtn = prof.special
    ? `<button class="cp2-sm-btn" onclick="showSpecialMonitor('${name.replace(/'/g, "\\'")}')">★ Special Monitor</button>`
    : '';
  const hdrHtml = `
    <div class="cp2-hdr">
      <button class="cp2-back" onclick="showRegionalOverview()">← All Countries</button>
      <div style="margin-left:6px;">
        <div class="cp2-name">${name}</div>
        <div class="cp2-sub">${prof.capital} · ${prof.regime}</div>
      </div>
      <div style="margin-left:auto;display:flex;align-items:center;gap:8px;">
        ${smBtn}
        <span class="cp2-cmr-pill ${cmrPillClass}">${prof.cmrStatus} CMR</span>
      </div>
    </div>`;

  // ── 2. Summary strip ─────────────────────────────────────────
  const summaryText = summary?.summary_text || prof.note || '—';
  const riskNote    = `${summary?.overall_risk_level || getOverallRiskBand(overallRiskScore)} · ${summary?.leading_trend || 'steady'}`;
  const summaryHtml = `
    <div class="cp2-summary">
      <div class="cp2-summary-text">${summaryText}</div>
      <div class="cp2-risk-box ${overallRiskTone}">
        <div class="cp2-risk-kicker">Overall Risk</div>
        <div class="cp2-risk-value" style="color:${getMonitorScoreColor(overallRiskScore)};">${formatMonitorValue(overallRiskScore) || '—'}</div>
        <div class="cp2-risk-note">${riskNote}</div>
      </div>
    </div>`;

  // ── 3. Radar + Sources band ──────────────────────────────────
  const radarHtml = cpBuildRadarSection(name, safeId);

  // ── 4. Context / Watch ───────────────────────────────────────
  const watchpoints = (summary?.watchpoints || []).length
    ? summary.watchpoints
    : (watch ? [watch] : ['No watchpoints available yet.']);
  const watchItemsHtml = watchpoints.map(w => `<div class="cp2-watch-item">${w}</div>`).join('');
  const contextHtml = `
    <div class="cp2-context-band">
      <div class="cp2-context-col">
        <div class="cp2-col-kicker">Context</div>
        <div class="cp2-context-text">${prof.note || '—'}</div>
      </div>
      <div class="cp2-context-col">
        <div class="cp2-col-kicker">What to Watch</div>
        ${watchItemsHtml}
      </div>
    </div>`;

  // ── 5. Reference Band ────────────────────────────────────────
  const statsColHtml = `
    <div class="cp2-ref-row"><span class="cp2-ref-label">Spending</span><span class="cp2-ref-val">${stats.spending}</span></div>
    <div class="cp2-ref-row"><span class="cp2-ref-label">Personnel</span><span class="cp2-ref-val">${stats.personnel}</span></div>
    <div class="cp2-ref-row"><span class="cp2-ref-label">Defence / GDP</span><span class="cp2-ref-val">${prof.gdpPct || '—'}</span></div>
    <div class="cp2-ref-row"><span class="cp2-ref-label">US Aid FY25</span><span class="cp2-ref-val">${stats.usAid}</span></div>`;
  const posColHtml = positions.map(p => `
    <div class="cp2-pos-item">
      <div class="cp2-pos-title">${p.t}</div>
      <div class="cp2-pos-name">${p.n}</div>
    </div>`).join('') || '<div class="cp2-ref-label">No data.</div>';
  const electColHtml = election
    ? `<div class="cp2-elect-type">${election.type}</div>
       <div class="cp2-elect-date">${election.date}</div>
       <div class="cp2-elect-note">${election.note}</div>`
    : '<div class="cp2-elect-note">No election data.</div>';
  const refHtml = `
    <div class="cp2-ref-band">
      <div class="cp2-ref-col"><div class="cp2-col-kicker">Key Stats</div>${statsColHtml}</div>
      <div class="cp2-ref-col"><div class="cp2-col-kicker">Key Positions</div>${posColHtml}</div>
      <div class="cp2-ref-col"><div class="cp2-col-kicker">Next Election</div>${electColHtml}</div>
    </div>`;

  // ── 6. Event Pulse ───────────────────────────────────────────
  const pulseHtml = cpBuildPulseSection(name, safeId);

  // ── 7. Live Events ───────────────────────────────────────────
  const cEvs = (allEvents || []).filter(e => e.country === name).sort((a, b) => b.date.localeCompare(a.date)).slice(0, 12);
  const evRows = cEvs.length
    ? cEvs.map(ev => `
        <div class="ev-item" style="cursor:pointer;" onclick="switchTab('events');setTimeout(()=>selectEvent(allEvents.find(e=>String(e.id)==='${ev.id}')),100)">
          <div class="ev-row1">
            <div class="ev-dot" style="background:${TC_HEX[ev.type] || '#6a6560'}"></div>
            <span class="ev-type" style="color:${TC_HEX[ev.type] || '#6a6560'}">${TYPE_LABEL[ev.type] || ev.type}</span>
            <span class="ev-country">${ev.date}</span>
          </div>
          <div class="ev-title">${ev.title}</div>
          <div class="ev-meta"><span>${ev.source || ''}</span></div>
        </div>`).join('')
    : '<div style="padding:16px 20px;font-size:12px;color:var(--text-muted);">No events in data store for this country yet.</div>';
  const eventsHtml = `
    <div class="cp2-events-section">
      <div class="cp2-events-hdr">
        <span class="cp2-events-label">Live Events — ${name}</span>
        <span class="cp2-events-count">${cEvs.length} events</span>
      </div>
      ${evRows}
    </div>`;

  // ── 8. Structural Trends ─────────────────────────────────────
  const trendsHtml = cpBuildStructuralTrends(name);

  // ── Assemble and render ──────────────────────────────────────
  countryDiv.innerHTML = hdrHtml + summaryHtml + radarHtml + contextHtml + refHtml + pulseHtml + eventsHtml + trendsHtml;

  _currentCpName = name;
  regional.style.display = 'none';
  countryDiv.style.display = 'block';
  countryDiv.scrollTop = 0;

  // Chart.js requires canvas to be visible — defer one tick
  setTimeout(() => {
    cpInitRadar(name, safeId);
    cpInitPulse(name, safeId);
  }, 0);
}
```

- [ ] **Step 2: Verify — open browser, navigate country profiles**

Open `http://localhost:8000`, click Country Profiles tab, click any standard country (e.g. Chile). Verify:
- Header shows country name, capital · regime, CMR pill right-aligned
- Summary strip shows analytical text and risk score box
- Radar section shows hexagonal chart (6 axes) + score table with rank badges
- Sources band appears below radar
- Context / Watch two columns appear
- Key Stats / Positions / Election three-column band appears
- Event Pulse 12-month stacked bar renders (or is empty if no events)
- Live Events list shows up to 12 event rows
- Structural Trends shows 4 cells at the bottom

Check console for errors.

- [ ] **Step 3: Verify special country — Colombia**

Click Colombia in the sidebar. Verify:
- `★ Special Monitor` button appears in the header (right side, before CMR pill)
- Layout is identical to other countries (not the old cloned HTML block)
- No console errors

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: rewrite showCountryProfile() with 8-section cp2 layout and radar chart"
```

---

## Part B — Special Monitor Sub-View

---

### Task 8: `SPECIAL_MONITOR_MILESTONES` Data Object

**Files:**
- Modify: `index.html` — JS section, near other large data objects (e.g. near `COUNTRY_PROFILES`)

This object provides the curated historical timeline events, analytical brief, and key data for each of the four special-focus countries.

- [ ] **Step 1: Add `SPECIAL_MONITOR_MILESTONES`**

Find the line `const COUNTRY_WATCH = {` (or any nearby large data object) and insert the following block immediately before it:

```js
const SPECIAL_MONITOR_MILESTONES = {
  Colombia: {
    subtitle: 'Peace Process · Armed Conflict · CMR',
    brief: "Colombia's civil-military relations are defined by a decades-long counter-insurgency legacy and the unfinished 2016 FARC peace process. The armed forces retain significant operational autonomy acquired during 50+ years of internal conflict, which structurally constrains Petro's Total Peace agenda. Three simultaneous negotiation tracks — FARC-EMC, ELN, and paramilitary successor groups — create competing military command authorities and fragmented territorial control.",
    meta: [
      { kicker: 'Focus period', value: '2016 – present\nPost-agreement arc' },
      { kicker: 'Key dynamic',  value: 'Peace process vs. military autonomy' },
    ],
    timelineStart: 2016,
    events: [
      { id:'col-e1',  date:'2016-11-24', cat:'peace',    title:'Final FARC agreement signed',                        desc:'Revised agreement establishes JEP, requiring military officers to testify on false positives. Armed forces accept framework but resist accountability mechanisms.' },
      { id:'col-e2',  date:'2016-12-01', cat:'reform',   title:'DDR begins for 13,000 FARC combatants',             desc:'Military role shifts to territorial stabilisation. Doctrine gap exposed — counter-insurgency institutions ill-equipped for post-conflict consolidation.' },
      { id:'col-e3',  date:'2018-04-10', cat:'military', title:'Army accused of resuming false positives',           desc:'HRW documents 5 new extrajudicial killings presented as combat kills. Defence Minister orders investigation.' },
      { id:'col-e4',  date:'2019-08-29', cat:'oc',       title:'FARC-EMC declared; Márquez resurfaces',             desc:'Key FARC commanders return to armed conflict, citing non-compliance with 2016 agreement. Creates new armed actor outside the peace framework.' },
      { id:'col-e5',  date:'2019-11-15', cat:'military', title:'Army airstrike kills 8 minors in Caquetá',          desc:'Bombing of a FARC-EMC camp. Defence Minister resigns. Military operating autonomously in borderline legal territory.' },
      { id:'col-e6',  date:'2020-03-22', cat:'intl',     title:'SOUTHCOM joint ops expand under COVID',             desc:'US-Colombia counter-narcotics operations expand. Military given expanded police powers in 7 departments.' },
      { id:'col-e7',  date:'2021-05-01', cat:'political',title:'National Strike — military deployed against protests',desc:'Mass protests met with live fire. Military tasked with civilian policing, triggering ICC preliminary examination.' },
      { id:'col-e8',  date:'2022-08-07', cat:'political',title:'Petro inaugurated; Velásquez named Defence Minister',desc:'First civilian critic of military in the post. Three generals and army commander retire within 30 days.' },
      { id:'col-e9',  date:'2022-10-13', cat:'military', title:'11 generals removed — deepest purge since 1957',    desc:'Rotation accelerates promotion of officers with professional rather than counter-insurgency profiles.' },
      { id:'col-e10', date:'2023-02-20', cat:'peace',    title:'ELN peace talks open in Havana',                    desc:'Fifth round of talks. Military High Command publicly expresses reservations about ceasefire scope.' },
      { id:'col-e11', date:'2023-10-05', cat:'intl',     title:'US suspends $90M FMF over human rights',            desc:'Leahy Law restrictions on three army brigades. SOUTHCOM ops continue separately, creating parallel US-military channels.' },
      { id:'col-e12', date:'2024-02-08', cat:'peace',    title:'FARC-EMC ceasefire collapses',                      desc:'Estado Mayor Central cites non-compliance. Southwest Command resumes full offensive posture after 14-month pause.' },
      { id:'col-e13', date:'2025-01-15', cat:'peace',    title:'ELN ceasefire collapses',                           desc:'Sixth round of Havana talks breaks down. Northern Command reauthorized for offensive operations.' },
      { id:'col-e14', date:'2025-03-04', cat:'oc',       title:'FARC-EMC fractures into two factions',              desc:'EMC/Mordisco split creates ambiguity over negotiating partners. Army begins dual posture: ops vs Mordisco, talks with EMC.' },
    ],
    keyData: [
      { name: 'FARC ex-combatants', value: '13,202', sub: 'enrolled in DDR · 2016' },
      { name: 'Reincorporated',     value: '~3,900',  sub: 'civilian returnees · 2024' },
      { name: 'FARC-EMC strength',  value: '~4,800',  sub: 'active combatants · 2025' },
      { name: 'Ex-combatant killings', value: '390+', sub: 'since agreement · 2025' },
    ],
  },
  Venezuela: {
    subtitle: 'FANB Structure · Authoritarian CMR · Succession',
    brief: "Venezuela represents the region's most advanced case of civil-military fusion. The Bolivarian Armed Forces (FANB) are structurally integrated into the economy, intelligence architecture, and political legitimation of the regime. The January 2026 Operation Absolute Resolve — the arrest of President Maduro by opposition forces and his transfer to US custody — creates an acute succession crisis with no precedent in SENTINEL's monitoring period.",
    meta: [
      { kicker: 'Focus period', value: '2013 – present\nMaduro era & beyond' },
      { kicker: 'Key dynamic',  value: 'Military as regime pillar · succession crisis' },
    ],
    timelineStart: 2016,
    events: [
      { id:'ven-e1', date:'2017-04-19', cat:'military',  title:'Military loyalty oath to Maduro — officer corps public pledge', desc:'Following mass protests. Padrino López leads ceremony. Marks militarization of regime survival strategy.' },
      { id:'ven-e2', date:'2018-05-20', cat:'political', title:'Maduro re-elected — international non-recognition',            desc:'FANB provides electoral security. US, EU, Lima Group reject results.' },
      { id:'ven-e3', date:'2019-01-23', cat:'political', title:'Guaidó declares interim presidency — coup attempt fails',      desc:'Military refuses to back Guaidó despite US recognition. Padrino remains loyal. Marks limits of opposition strategy.' },
      { id:'ven-e4', date:'2020-03-01', cat:'oc',        title:'FANB-colectivo-Tren de Aragua integration documented',        desc:'US Treasury sanctions FANB generals with direct cartel ties. Military economic enterprises (CAMIMPEG) expand.' },
      { id:'ven-e5', date:'2023-07-28', cat:'political', title:'Maduro claims re-election amid mass fraud allegations',        desc:'Results disputed internationally. Armed forces maintain loyalty. Opposition candidate Edmundo González wins by independent tally.' },
      { id:'ven-e6', date:'2025-01-10', cat:'political', title:'Maduro transferred to US custody — Operation Absolute Resolve',desc:'Opposition coalition seizes Caracas, arrests Maduro. Rodríguez sworn in as President. FANB High Command remains in place.' },
      { id:'ven-e7', date:'2025-03-17', cat:'political', title:'Maduro federal detention hearing in New York',                desc:'First appearance before US judge. Charges include narco-terrorism. FANB generals monitor Rodríguez closely.' },
    ],
    keyData: [
      { name: 'FANB active personnel', value: '~160K',  sub: 'army, navy, air, NG · 2024' },
      { name: 'FANB generals',          value: '2,000+', sub: 'coup-proofing legacy' },
      { name: 'Colectivos',             value: '~15K',   sub: 'armed pro-regime militias' },
      { name: 'GDP contraction (2014–23)', value: '−80%', sub: 'constant USD' },
    ],
  },
  'El Salvador': {
    subtitle: 'Régimen de Excepción · Civil-Military Fusion · CECOT',
    brief: "El Salvador represents a textbook case of democratic backsliding through civil-military fusion. Unlike classical coups, Bukele's consolidation proceeds via managed elections — enabled by judicial packing that reversed constitutional term limits — while using the military as a visible loyalty instrument and domestic enforcement mechanism. The February 2020 Legislative Assembly occupation was the defining inflection point.",
    meta: [
      { kicker: 'Focus period', value: '2020 – present\nBukele consolidation' },
      { kicker: 'Key dynamic',  value: 'Civil-military fusion via Régimen' },
    ],
    timelineStart: 2016,
    events: [
      { id:'sv-e1', date:'2019-06-01', cat:'political', title:'Bukele inaugurated — begins military-adjacent posture',    desc:'Cabinet includes former military figures. Security policy emphasizes visibility of armed forces.' },
      { id:'sv-e2', date:'2020-02-09', cat:'military',  title:'Bukele enters Assembly with armed soldiers — loyalty oath', desc:'Officers publicly pledge loyalty to president. Constitutional crisis: military refuses to enforce legislative limits on executive.' },
      { id:'sv-e3', date:'2021-05-01', cat:'political', title:'Bukele-controlled Assembly removes Supreme Court magistrates',desc:'Judicial packing removes institutional check. Plan announced to double army from 20K to 40K by 2026.' },
      { id:'sv-e4', date:'2022-03-27', cat:'military',  title:'Régimen de Excepción declared — mass arrest campaign',      desc:'Following 80-homicide weekend. Military and police begin mass arrests. Suspension of due process rights.' },
      { id:'sv-e5', date:'2023-02-01', cat:'military',  title:'CECOT mega-prison opens — military operates security',       desc:'Designed for 40,000 detainees. Military handles transport and perimeter. Military discipline applied to civilians.' },
      { id:'sv-e6', date:'2024-02-04', cat:'political', title:'Bukele re-elected with 85% — second term begins June 2024',  desc:'Despite constitutional ban on consecutive terms, reversed by packed court. No major military dissent recorded.' },
      { id:'sv-e7', date:'2025-03-16', cat:'intl',      title:'252 Venezuelan deportees arrive at CECOT under Trump deal',  desc:'US pays $6M/year. Deportees later report systematic torture per HRW report (Nov 2025).' },
      { id:'sv-e8', date:'2025-05-12', cat:'military',  title:'Military deployed to disperse peaceful protests',           desc:'First post-civil war use of armed forces against civil society. Heinrich Böll Stiftung documents cases.' },
      { id:'sv-e9', date:'2025-07-31', cat:'political', title:'Constitutional reform: indefinite re-election, 6-year terms', desc:'Assembly approves 57–3: abolishes runoffs, moves elections to 2027. Constitutional order restructured.' },
      { id:'sv-e10',date:'2026-03-27', cat:'political', title:'GIPES presents to CIDH: 504 in-custody deaths under régimen', desc:'Findings of crimes against humanity submitted to Inter-American Commission. 48th régimen extension.' },
    ],
    keyData: [
      { name: 'Régimen detentions',  value: '85K+',  sub: 'total since Mar 2022' },
      { name: 'In-custody deaths',   value: '504',   sub: 'per GIPES · Mar 2026' },
      { name: 'CECOT capacity',      value: '40,000',sub: 'mega-prison · opened 2023' },
      { name: 'Homicide rate (2023)','value': '2.4/100K', sub: 'vs 103/100K in 2015' },
    ],
  },
  Mexico: {
    subtitle: 'SEDENA Militarization · Cartel Wars · FTO Designations',
    brief: "Mexico presents the region's most complex civil-military case: deep structural militarization under a formally democratic civilian government that has not experienced a coup. The officer corps has not asserted political preferences but has been the consistent beneficiary of institutional expansion. The Sheinbaum administration has deepened the AMLO-era model: in July 2025, SEDENA was formally granted national security intelligence authority, and the National Guard was transferred to SEDENA command.",
    meta: [
      { kicker: 'Focus period', value: '2006 – present\nMilitarization arc' },
      { kicker: 'Key dynamic',  value: 'Structural militarization under civilian rule' },
    ],
    timelineStart: 2016,
    events: [
      { id:'mx-e1', date:'2019-01-01', cat:'reform',   title:'AMLO creates National Guard — civilian name, military personnel', desc:'Constitutionally civilian in name only. Built from military cadre. Marks start of institutional re-militarization under new labels.' },
      { id:'mx-e2', date:'2022-09-05', cat:'reform',   title:'National Guard formally transferred to SEDENA',                  desc:'Military takes AIFA airport, Tren Maya, ports, customs. Mexico has no nationwide civilian police force.' },
      { id:'mx-e3', date:'2024-06-01', cat:'political','title':'Sheinbaum takes office — deepens AMLO militarization model',   desc:'New SEDENA / SEMAR chiefs appointed Sep 2024. Maintains and expands military institutional roles.' },
      { id:'mx-e4', date:'2024-09-12', cat:'oc',       title:'Sinaloa civil war begins — El Mayo transferred to US',          desc:'Chapitos faction hands Zambada to US. Cartel splits: La Mayiza vs Chapitos. 2,197 homicides in Sinaloa state.' },
      { id:'mx-e5', date:'2025-02-06', cat:'intl',     title:'Trump designates 6 Mexican cartels as FTOs',                    desc:'Sovereignty crisis. Sheinbaum deploys 10K NG to border to preempt tariffs. DEA access restricted.' },
      { id:'mx-e6', date:'2025-07-01', cat:'reform',   title:'SEDENA granted national security intelligence authority',        desc:'Legislative reform. Military now authorized to generate and act on national security intelligence without civilian co-lead.' },
      { id:'mx-e7', date:'2026-02-22', cat:'military', title:'El Mencho (CJNG) killed in joint SEDENA/SEMAR operation',       desc:'US JITC-CC intelligence and planning support. 25 National Guard members killed. Largest cartel takedown in years.' },
    ],
    keyData: [
      { name: 'Active military',       value: '~277K', sub: 'SEDENA + SEMAR · 2025' },
      { name: 'National Guard (SEDENA)','value':'~120K', sub: 'formerly civilian mandate' },
      { name: 'Homicides (2025)',       value: '23,374',sub: '−30% vs 2024 · 17.5/100K' },
      { name: 'Cartel HVTs to US',      value: '93',    sub: 'transferred in 12 months' },
    ],
  },
};
```

- [ ] **Step 2: Verify — console check**

Open browser console and run:
```js
SPECIAL_MONITOR_MILESTONES['Colombia'].events.length
// Expected: 14

SPECIAL_MONITOR_MILESTONES['Mexico'].keyData[0].name
// Expected: "Active military"
```

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat: add SPECIAL_MONITOR_MILESTONES data for 4 special-focus countries"
```

---

### Task 9: CSS for Special Monitor Card

**Files:**
- Modify: `index.html` — CSS block

- [ ] **Step 1: Add special monitor CSS**

Find the `/* ── CP v2 ───` block you added in Task 1 and append the following at the end of it (before the closing `*/` or before the next comment block):

```css
/* ── SPECIAL MONITOR ─────────────────────────────────────────── */
.sm-card { display: flex; flex-direction: column; background: #0d1016; color: #d4cfc8; font-family: var(--sans); border: 1px solid #252830; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.18); margin: 0; }
.sm-sec  { background: #161a22; }

.sm-hdr { padding: 13px 20px 11px; display: flex; align-items: center; gap: 8px; background: #161a22; border-bottom: 1px solid #1e2230; }
.sm-back { font-family: var(--mono); font-size: 9px; letter-spacing: 0.8px; text-transform: uppercase; color: #3a3830; background: none; border: none; cursor: pointer; padding: 0; }
.sm-back:hover { color: #6a6560; }
.sm-name { font-size: 16px; font-weight: 700; color: #ede8e0; letter-spacing: -0.3px; }
.sm-sub  { font-size: 9px; color: #4a4840; font-family: var(--mono); }
.sm-badge { font-size: 8px; letter-spacing: 1px; text-transform: uppercase; font-family: var(--mono); color: #b83232; background: rgba(184,50,50,0.1); border: 1px solid rgba(184,50,50,0.22); padding: 2px 7px; border-radius: 3px; }
.sm-cmr-pill { font-size: 9px; letter-spacing: 1px; text-transform: uppercase; font-family: var(--mono); padding: 3px 9px; border-radius: 4px; border: 1px solid; }
.sm-cmr-pill.stable       { color: #2d8659; border-color: rgba(45,134,89,0.35);  background: rgba(45,134,89,0.07); }
.sm-cmr-pill.strained     { color: #c46e12; border-color: rgba(196,110,18,0.25); background: rgba(196,110,18,0.07); }
.sm-cmr-pill.crisis       { color: #b83232; border-color: rgba(184,50,50,0.25);  background: rgba(184,50,50,0.07); }
.sm-cmr-pill.authoritarian{ color: #8a4a8a; border-color: rgba(138,74,138,0.25); background: rgba(138,74,138,0.07); }

.sm-brief { padding: 14px 20px; display: flex; gap: 14px; background: #161a22; border-bottom: 1px solid #1e2230; }
.sm-brief-text { flex: 1; font-size: 11.5px; color: #6a6560; line-height: 1.75; text-align: justify; hyphens: auto; }
.sm-brief-meta { flex: 0 0 128px; display: flex; flex-direction: column; gap: 7px; }
.sm-meta-block { background: #1c1f28; border: 1px solid #1e2230; border-radius: 5px; padding: 8px 10px; }
.sm-meta-kicker { font-size: 7.5px; font-family: var(--mono); letter-spacing: 1px; text-transform: uppercase; color: #2e2c28; margin-bottom: 2px; }
.sm-meta-val { font-size: 10.5px; color: #7a7570; line-height: 1.45; white-space: pre-line; }

.sm-tl-sec { padding: 16px 20px 0; background: #161a22; border-bottom: 1px solid #1e2230; }
.sm-tl-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; flex-wrap: wrap; gap: 8px; }
.sm-tl-label { font-size: 8.5px; letter-spacing: 1.2px; text-transform: uppercase; font-family: var(--mono); color: #2e2c28; }
.sm-filters { display: flex; gap: 4px; flex-wrap: wrap; }
.sm-f-btn { font-size: 8px; font-family: var(--mono); letter-spacing: 0.5px; text-transform: uppercase; padding: 2px 7px; border-radius: 3px; cursor: pointer; border: 1px solid #1e2230; background: #131720; color: #3a3830; transition: all 0.12s; }
.sm-f-btn:hover { color: #6a6560; border-color: #2a2e3c; }
.sm-f-btn.active { background: #1e2230; border-color: #2a2e3c; color: #9a9590; }
.sm-f-btn[data-c="peace"].active    { color: #2d8659; border-color: rgba(45,134,89,0.35);   background: rgba(45,134,89,0.07); }
.sm-f-btn[data-c="military"].active { color: #a84000; border-color: rgba(168,64,0,0.35);    background: rgba(168,64,0,0.07); }
.sm-f-btn[data-c="political"].active{ color: #1a6e82; border-color: rgba(26,110,130,0.35);  background: rgba(26,110,130,0.07); }
.sm-f-btn[data-c="oc"].active       { color: #6a4a6e; border-color: rgba(106,74,110,0.35);  background: rgba(106,74,110,0.07); }
.sm-f-btn[data-c="reform"].active   { color: #1a538f; border-color: rgba(26,83,143,0.35);   background: rgba(26,83,143,0.07); }
.sm-f-btn[data-c="intl"].active     { color: #2e6b8a; border-color: rgba(46,107,138,0.35);  background: rgba(46,107,138,0.07); }
.sm-f-btn[data-c="live"].active     { color: #c49a20; border-color: rgba(196,154,32,0.35);  background: rgba(196,154,32,0.07); }

.sm-tl-figure { overflow-x: auto; overflow-y: visible; padding-bottom: 2px; scrollbar-width: thin; scrollbar-color: #1e2230 transparent; }
.sm-tl-figure::-webkit-scrollbar { height: 3px; }
.sm-tl-figure::-webkit-scrollbar-thumb { background: #252830; border-radius: 2px; }
.sm-scroll-hint { padding: 6px 0 14px; font-size: 8px; font-family: var(--mono); color: #252830; display: flex; align-items: center; gap: 5px; }
.sm-scroll-hint::before { content:''; display:inline-block; width:16px; height:1px; background:#252830; }

.sm-ev-list { border-top: 1px solid #1e2230; }
.sm-ev-list-hdr { padding: 10px 20px 8px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #191c25; }
.sm-ev-list-label { font-size: 8.5px; letter-spacing: 1.1px; text-transform: uppercase; font-family: var(--mono); color: #2e2c28; }
.sm-ev-count { font-size: 9px; font-family: var(--mono); color: #2e2c28; }
.sm-ev-row { display: flex; align-items: flex-start; gap: 0; padding: 6px 20px; border-bottom: 1px solid #191c25; cursor: pointer; transition: background 0.1s; }
.sm-ev-row:last-child { border-bottom: none; }
.sm-ev-row:hover { background: #1a1d26; }
.sm-ev-row.highlighted { background: #1b2030; }
.sm-ev-row.filtered-out { display: none; }
.sm-ev-cat-bar { width: 2px; flex-shrink: 0; border-radius: 1px; margin-right: 10px; align-self: stretch; min-height: 18px; }
.sm-ev-date { flex: 0 0 58px; font-size: 9px; font-family: var(--mono); color: #3a3830; padding-top: 2px; white-space: nowrap; }
.sm-ev-cat-lbl { flex: 0 0 90px; font-size: 8px; font-family: var(--mono); text-transform: uppercase; letter-spacing: 0.5px; padding-top: 2px; }
.sm-ev-title { flex: 1; font-size: 11.5px; color: #7a7570; line-height: 1.45; }
.sm-ev-row.highlighted .sm-ev-title { color: #b8b3ac; }
.sm-ev-desc { display: none; font-size: 11px; color: #4a4840; line-height: 1.65; padding: 5px 20px 8px calc(20px + 2px + 10px + 58px + 90px); border-bottom: 1px solid #191c25; background: #141720; }
.sm-ev-row.expanded + .sm-ev-desc { display: block; }
.sm-live-pip { font-size: 7px; font-family: var(--mono); letter-spacing: 0.8px; text-transform: uppercase; color: #c49a20; background: rgba(196,154,32,0.1); border: 1px solid rgba(196,154,32,0.2); padding: 1px 4px; border-radius: 2px; margin-left: 5px; vertical-align: middle; }

.sm-data-strip { padding: 14px 20px 16px; background: #131720; }
.sm-ds-label { font-size: 8.5px; letter-spacing: 1.1px; text-transform: uppercase; font-family: var(--mono); color: #2a2820; margin-bottom: 10px; }
.sm-ds-grid { display: flex; gap: 1px; background: #1a1d26; border-radius: 5px; overflow: hidden; }
.sm-ds-cell { flex: 1; background: #161a22; padding: 10px 12px; }
.sm-ds-name { font-size: 8.5px; font-family: var(--mono); color: #3a3830; margin-bottom: 4px; }
.sm-ds-val  { font-size: 15px; font-weight: 700; font-family: var(--mono); color: #7a7570; }
.sm-ds-sub  { font-size: 8.5px; color: #2e2c28; font-family: var(--mono); margin-top: 2px; }
```

- [ ] **Step 2: Commit**

```bash
git add index.html
git commit -m "style: add special monitor CSS classes (.sm-*)"
```

---

### Task 10: `showSpecialMonitor()` Function

**Files:**
- Modify: `index.html` — JS section, after `showCountryProfile`

- [ ] **Step 1: Add `showSpecialMonitor(name)`**

Insert immediately after the closing `}` of `showCountryProfile`:

```js
const SM_CAT_COLOR = {
  peace:'#2d8659', military:'#a84000', political:'#1a6e82',
  oc:'#6a4a6e', reform:'#1a538f', intl:'#2e6b8a', live:'#c49a20',
};
const SM_CAT_LABEL = {
  peace:'Peace', military:'Military', political:'Political',
  oc:'Armed Groups', reform:'Reform', intl:'International', live:'Live',
};

function showSpecialMonitor(name) {
  const countryDiv = document.getElementById('cp-country');
  const prof = COUNTRY_PROFILES[name];
  const data = SPECIAL_MONITOR_MILESTONES[name];
  if (!prof || !data) { showCountryProfile(name); return; }

  const cmrClass = (prof.cmrClass || 'stable').toLowerCase();

  // Merge curated events with live pipeline events (cat='live')
  const startDate = `${data.timelineStart || 2016}-01-01`;
  const liveEvs = (allEvents || [])
    .filter(e => e.country === name && e.date >= startDate)
    .map(e => ({ id: String(e.id), date: e.date, cat: 'live', title: e.title, desc: e.summary || '' }));
  const curatedIds = new Set(data.events.map(e => e.id));
  const merged = [
    ...data.events,
    ...liveEvs.filter(e => !curatedIds.has(e.id)),
  ].sort((a, b) => a.date.localeCompare(b.date));

  // ── Header ──────────────────────────────────────────────────
  const hdrHtml = `
    <div class="sm-hdr">
      <button class="sm-back" onclick="showCountryProfile('${name.replace(/'/g, "\\'")}')">← ${name} Profile</button>
      <div style="margin-left:10px;">
        <div class="sm-name">${name}</div>
        <div class="sm-sub">${data.subtitle || ''}</div>
      </div>
      <div style="margin-left:auto;display:flex;align-items:center;gap:6px;">
        <span class="sm-badge">★ Special Monitor</span>
        <span class="sm-cmr-pill ${cmrClass}">${prof.cmrStatus} CMR</span>
      </div>
    </div>`;

  // ── Brief ────────────────────────────────────────────────────
  const metaHtml = (data.meta || []).map(m => `
    <div class="sm-meta-block">
      <div class="sm-meta-kicker">${m.kicker}</div>
      <div class="sm-meta-val">${m.value}</div>
    </div>`).join('');
  const briefHtml = `
    <div class="sm-brief">
      <div class="sm-brief-text">${data.brief || ''}</div>
      <div class="sm-brief-meta">${metaHtml}</div>
    </div>`;

  // ── Timeline section (shell — SVG built after innerHTML set) ─
  const smId = name.replace(/ /g, '_');
  const filterBtns = [
    ['All', 'all'], ['Peace', 'peace'], ['Military', 'military'],
    ['Political', 'political'], ['Armed Groups', 'oc'], ['Reform', 'reform'],
    ['International', 'intl'], ['● Live', 'live'],
  ].map(([label, cat]) =>
    `<button class="sm-f-btn${cat === 'all' ? ' active' : ''}" data-c="${cat}" onclick="smSetFilter('${smId}','${cat}')">${label}</button>`
  ).join('');

  const evListRows = [...merged].reverse().map(ev => {
    const color = SM_CAT_COLOR[ev.cat] || '#6a6560';
    const livePip = ev.cat === 'live' ? '<span class="sm-live-pip">live</span>' : '';
    return `
      <div class="sm-ev-row" data-id="${ev.id}" data-cat="${ev.cat}" onclick="smSelectEvent('${smId}','${ev.id}')">
        <div class="sm-ev-cat-bar" style="background:${color}"></div>
        <div class="sm-ev-date">${ev.date.slice(0,7)}</div>
        <div class="sm-ev-cat-lbl" style="color:${color}">${SM_CAT_LABEL[ev.cat] || ev.cat}${livePip}</div>
        <div class="sm-ev-title">${ev.title}</div>
      </div>
      <div class="sm-ev-desc" data-id="${ev.id}">${ev.desc || ''}</div>`;
  }).join('');

  const tlHtml = `
    <div class="sm-tl-sec">
      <div class="sm-tl-top">
        <div class="sm-tl-label">CMR Timeline — ${data.timelineStart} to present</div>
        <div class="sm-filters">${filterBtns}</div>
      </div>
      <div class="sm-tl-figure">
        <svg id="sm-svg-${smId}" xmlns="http://www.w3.org/2000/svg" style="display:block;overflow:visible;"></svg>
      </div>
      <div class="sm-scroll-hint">scroll to explore full timeline</div>
      <div class="sm-ev-list">
        <div class="sm-ev-list-hdr">
          <span class="sm-ev-list-label">Events</span>
          <span class="sm-ev-count" id="sm-ev-count-${smId}">${merged.length} total</span>
        </div>
        <div id="sm-ev-body-${smId}">${evListRows}</div>
      </div>
    </div>`;

  // ── Key Data strip ───────────────────────────────────────────
  const dsHtml = `
    <div class="sm-data-strip">
      <div class="sm-ds-label">Key Data — ${name}</div>
      <div class="sm-ds-grid">
        ${(data.keyData || []).map(d => `
          <div class="sm-ds-cell">
            <div class="sm-ds-name">${d.name}</div>
            <div class="sm-ds-val">${d.value}</div>
            <div class="sm-ds-sub">${d.sub}</div>
          </div>`).join('')}
      </div>
    </div>`;

  countryDiv.innerHTML = `<div class="sm-card">${hdrHtml}${briefHtml}${tlHtml}${dsHtml}</div>`;
  countryDiv.style.display = 'block';
  countryDiv.scrollTop = 0;
  document.getElementById('cp-regional').style.display = 'none';

  // Build SVG after DOM is set
  setTimeout(() => smBuildSvg(smId, merged), 0);
}

// ── SVG builder ──────────────────────────────────────────────────
function smBuildSvg(smId, events) {
  const svg = document.getElementById(`sm-svg-${smId}`);
  if (!svg) return;

  const PAD_L = 32, PAD_R = 32, YEAR_W = 90;
  const START = 2016, END = 2027, YEARS = END - START;
  const SVG_W = PAD_L + YEARS * YEAR_W + PAD_R;
  const AXIS_Y = 110, DOT_R = 5, STEM_BASE = 18, STEP = 16;
  const NOW = new Date().toISOString().slice(0, 10);

  function dateToX(d) {
    const dt = new Date(d);
    const t  = dt.getFullYear() + dt.getMonth() / 12 + dt.getDate() / 365;
    return PAD_L + ((t - START) / YEARS) * (YEARS * YEAR_W);
  }

  function ns(tag, attrs = {}) {
    const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
    return el;
  }

  // Collision levels
  const sorted = [...events].sort((a, b) => a.date.localeCompare(b.date));
  const placed = [];
  sorted.forEach(ev => {
    const x = dateToX(ev.date);
    let level = 0;
    while (placed.some(p => p.level === level && Math.abs(p.x - x) < 38)) level++;
    placed.push({ ...ev, x, level });
  });

  const svgH = AXIS_Y + 38;
  svg.setAttribute('width', SVG_W);
  svg.setAttribute('height', svgH);
  svg.setAttribute('viewBox', `0 0 ${SVG_W} ${svgH}`);
  svg.style.height = svgH + 'px';
  svg.innerHTML = '';

  // Year bands
  for (let yr = START; yr < END; yr++) {
    const x = dateToX(`${yr}-01-01`);
    if ((yr - START) % 2 === 0) {
      svg.appendChild(ns('rect', { x, y: 0, width: YEAR_W, height: svgH, fill: 'rgba(255,255,255,0.008)' }));
    }
  }

  // Axis
  svg.appendChild(ns('line', { x1: PAD_L, y1: AXIS_Y, x2: SVG_W - PAD_R, y2: AXIS_Y, stroke: '#252830', 'stroke-width': '1.5' }));

  // Year ticks + labels
  for (let yr = START; yr <= END - 1; yr++) {
    const x = dateToX(`${yr}-01-01`);
    svg.appendChild(ns('line', { x1: x, y1: AXIS_Y - 4, x2: x, y2: AXIS_Y + 4, stroke: '#2a2e3c', 'stroke-width': '1' }));
    const lbl = ns('text', { x, y: AXIS_Y + 18, 'text-anchor': 'middle', fill: '#3e3c38', 'font-family': 'DM Mono,monospace', 'font-size': '9.5', 'letter-spacing': '0.3' });
    lbl.textContent = yr;
    svg.appendChild(lbl);
  }

  // NOW line
  const nowX = dateToX(NOW);
  svg.appendChild(ns('line', { x1: nowX, y1: 2, x2: nowX, y2: AXIS_Y - 2, stroke: 'rgba(196,80,32,0.22)', 'stroke-width': '1', 'stroke-dasharray': '3,3' }));
  const nowT = ns('text', { x: nowX + 4, y: 11, fill: 'rgba(196,80,32,0.3)', 'font-family': 'DM Mono,monospace', 'font-size': '7.5', 'letter-spacing': '0.5' });
  nowT.textContent = 'NOW';
  svg.appendChild(nowT);

  // Events
  placed.forEach(ev => {
    const color = SM_CAT_COLOR[ev.cat] || '#6a6560';
    const stemH = STEM_BASE + ev.level * STEP;
    const dotY  = AXIS_Y - stemH;

    svg.appendChild(ns('line', {
      x1: ev.x, y1: AXIS_Y, x2: ev.x, y2: dotY + DOT_R,
      stroke: color, 'stroke-width': '1', 'stroke-opacity': '0.2',
      class: `sm-stem sm-stem-${smId}-${ev.id}`,
    }));

    const g = ns('g', { transform: `translate(${ev.x},${dotY})`, cursor: 'pointer', class: `sm-dot-g sm-dot-${smId}-${ev.id}`, 'data-id': ev.id, 'data-cat': ev.cat });
    g.appendChild(ns('circle', { r: '10', fill: 'none', stroke: color, 'stroke-width': '1', 'stroke-opacity': '0', class: 'sm-dot-ring' }));
    g.appendChild(ns('circle', { r: String(DOT_R), fill: '#161a22', stroke: color, 'stroke-width': '2', class: 'sm-dot-circle' }));
    g.appendChild(ns('circle', { r: '13', fill: 'transparent' }));

    // Tooltip
    const tipH = 58, tipW = 172;
    const tipX = ev.x > SVG_W - 200 ? -(tipW + 6) : 9;
    const tipY = -(stemH + tipH + 4);
    const fo = ns('foreignObject', { x: tipX, y: tipY, width: tipW, height: tipH, class: `sm-tip-fo sm-tip-${smId}-${ev.id}`, style: 'display:none;pointer-events:none;' });
    const div = document.createElement('div');
    div.style.cssText = `background:#1e2230;border:1px solid #2a2e40;border-radius:5px;padding:7px 9px;font-size:10px;color:#9a9590;line-height:1.4;font-family:'DM Sans',sans-serif;`;
    div.innerHTML = `<div style="font-size:7.5px;font-family:'DM Mono',monospace;color:#4a4840;margin-bottom:2px;">${ev.date}</div><div style="font-size:7.5px;font-family:'DM Mono',monospace;color:${color};margin-bottom:3px;text-transform:uppercase;letter-spacing:.5px;">${SM_CAT_LABEL[ev.cat] || ev.cat}</div>${ev.title}`;
    fo.appendChild(div);
    g.appendChild(fo);

    g.addEventListener('mouseenter', () => {
      if (!g._smActive) fo.style.display = '';
      g.querySelector('.sm-dot-ring').setAttribute('stroke-opacity', '0.3');
      document.querySelector(`.sm-stem-${smId}-${ev.id}`)?.setAttribute('stroke-opacity', '0.55');
    });
    g.addEventListener('mouseleave', () => {
      if (!g._smActive) fo.style.display = 'none';
      if (!g._smActive) g.querySelector('.sm-dot-ring').setAttribute('stroke-opacity', '0');
      if (!g._smActive) document.querySelector(`.sm-stem-${smId}-${ev.id}`)?.setAttribute('stroke-opacity', '0.2');
    });
    g.addEventListener('click', () => smSelectEvent(smId, ev.id));
    svg.appendChild(g);
  });
}

// ── Interaction handlers ─────────────────────────────────────────
function smSelectEvent(smId, id) {
  // Deselect if same
  const g = document.querySelector(`.sm-dot-${smId}-${id}`);
  if (g && g._smActive) {
    g._smActive = false;
    g.querySelector('.sm-dot-ring').setAttribute('stroke-opacity', '0');
    g.querySelector('.sm-dot-circle').setAttribute('fill', '#161a22');
    document.querySelector(`.sm-tip-${smId}-${id}`)?.setAttribute('style', 'display:none;pointer-events:none;');
    document.querySelector(`.sm-stem-${smId}-${id}`)?.setAttribute('stroke-opacity', '0.2');
    document.querySelectorAll(`#sm-ev-body-${smId} .sm-ev-row[data-id="${id}"]`).forEach(r => { r.classList.remove('highlighted', 'expanded'); });
    document.querySelectorAll(`#sm-ev-body-${smId} .sm-ev-desc[data-id="${id}"]`).forEach(d => d.style.display = 'none');
    return;
  }

  // Clear previous active
  document.querySelectorAll(`.sm-dot-g`).forEach(dg => {
    dg._smActive = false;
    dg.querySelector('.sm-dot-ring')?.setAttribute('stroke-opacity', '0');
    dg.querySelector('.sm-dot-circle')?.setAttribute('fill', '#161a22');
  });
  document.querySelectorAll(`[class*="sm-tip-${smId}-"]`).forEach(t => t.setAttribute('style', 'display:none;pointer-events:none;'));
  document.querySelectorAll(`[class*="sm-stem-${smId}-"]`).forEach(s => s.setAttribute('stroke-opacity', '0.12'));
  document.querySelectorAll(`#sm-ev-body-${smId} .sm-ev-row`).forEach(r => r.classList.remove('highlighted', 'expanded'));
  document.querySelectorAll(`#sm-ev-body-${smId} .sm-ev-desc`).forEach(d => d.style.display = 'none');

  // Activate selected
  if (g) {
    g._smActive = true;
    const color = SM_CAT_COLOR[g.dataset.cat] || '#6a6560';
    g.querySelector('.sm-dot-ring').setAttribute('stroke-opacity', '0.35');
    g.querySelector('.sm-dot-circle').setAttribute('fill', color);
    document.querySelector(`.sm-tip-${smId}-${id}`)?.setAttribute('style', 'display:;pointer-events:none;');
    document.querySelector(`.sm-stem-${smId}-${id}`)?.setAttribute('stroke-opacity', '0.65');
  }
  document.querySelectorAll(`#sm-ev-body-${smId} .sm-ev-row[data-id="${id}"]`).forEach(r => r.classList.add('highlighted', 'expanded'));
  document.querySelectorAll(`#sm-ev-body-${smId} .sm-ev-desc[data-id="${id}"]`).forEach(d => { d.style.display = 'block'; });
  document.querySelector(`#sm-ev-body-${smId} .sm-ev-row[data-id="${id}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function smSetFilter(smId, cat) {
  document.querySelectorAll(`.sm-filters .sm-f-btn`).forEach(b => b.classList.toggle('active', b.dataset.c === cat));
  document.querySelectorAll(`.sm-dot-g`).forEach(g => {
    const show = cat === 'all' || g.dataset.cat === cat;
    g.setAttribute('opacity', show ? '1' : '0.07');
    g.style.pointerEvents = show ? '' : 'none';
  });
  document.querySelectorAll(`[class*="sm-stem-"]`).forEach(s => {
    const cls = [...s.classList].find(c => c.startsWith('sm-stem-'));
    const evId = cls?.split('-').slice(3).join('-');
    const ev   = document.querySelector(`.sm-dot-g[data-id="${evId}"]`);
    s.setAttribute('stroke-opacity', (cat === 'all' || ev?.dataset.cat === cat) ? '0.2' : '0.04');
  });
  const body = document.getElementById(`sm-ev-body-${smId}`);
  if (body) {
    body.querySelectorAll('.sm-ev-row').forEach(r => r.classList.toggle('filtered-out', cat !== 'all' && r.dataset.cat !== cat));
  }
  const visCount = cat === 'all'
    ? document.querySelectorAll(`.sm-dot-g`).length
    : document.querySelectorAll(`.sm-dot-g[data-cat="${cat}"]`).length;
  const countEl = document.getElementById(`sm-ev-count-${smId}`);
  if (countEl) countEl.textContent = `${visCount} shown`;
}
```

- [ ] **Step 2: Verify**

Open `http://localhost:8000`, click Country Profiles, click Colombia. Verify:
- `★ Special Monitor` button is visible in header
- Click the button → view changes to dark card (not the country profile)
- Header shows `← Colombia Profile` back button, `★ Special Monitor` badge, `Strained CMR` pill
- Brief text and two meta blocks appear
- SVG timeline renders with colored dots and axis
- Clicking a dot highlights it and expands description in the list
- Filter tabs filter timeline dots and list rows
- Key data strip shows 4 Colombia cells
- Back button returns to the standard Colombia profile

Repeat for Venezuela, El Salvador, Mexico.

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat: add showSpecialMonitor(), smBuildSvg(), smSelectEvent(), smSetFilter()"
```

---

### Task 11: Final Cleanup and Smoke Test

**Files:**
- Modify: `index.html` — minor cleanup only

- [ ] **Step 1: Smoke test all tabs**

Open `http://localhost:8000`. Exercise each tab:
1. **Overview** — loads, choropleth renders, monitor cards visible
2. **Events** — map loads, sidebar event list populates, filters work
3. **Countries** — regional overview renders, click 5+ countries, verify radar + pulse on each
4. **Colombia special monitor** — timeline, filters, key data all work; back returns to Colombia profile
5. **Venezuela, El Salvador, Mexico** — same as Colombia
6. **US-LatAm** — aid charts render
7. **Organized Crime** — tab loads
8. **Timeline** — event feed loads
9. **About** — renders without errors

Check browser console — no JS errors.

- [ ] **Step 2: Verify chart cleanup on re-navigation**

In the Country Profiles tab: click Chile → click Colombia → click Chile again. Verify no "Canvas already in use" Chart.js warning in the console. The `_cpRadarChart` and `_cpPulseChart` module-level variables and `.destroy()` calls handle this.

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "chore: final smoke test and cleanup for country profile redesign"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| Header: name, capital/regime, CMR pill, back button | Task 7 |
| Summary strip: analytical text + risk score box | Task 7 |
| Radar chart: 6 axes, Chart.js, 258×258px | Tasks 3, 4 |
| Rank badges: computed in-browser, r-hi/r-md/r-lo | Task 2 |
| Sources band below radar | Task 3 |
| Context / Watch two-column | Task 7 |
| Reference Band: Stats / Positions / Election | Task 7 |
| Event Pulse stacked bar (12 months) | Tasks 5, 7 |
| Live Events full-width list | Task 7 |
| Structural Trends 4-cell strip | Tasks 6, 7 |
| GDP delta (green if +, red if −) | Task 6 |
| Chart instance cleanup on re-navigation | Task 4, 5 |
| Special Monitor entry button | Task 7 |
| SM navigation: back returns to country profile | Task 10 |
| SM Brief section | Task 10 |
| SM SVG horizontal timeline | Task 10 |
| SM collision-level algorithm | Task 10 |
| SM filter tabs (8 categories) | Task 10 |
| SM compact event list | Task 10 |
| SM live event merging + dedup | Task 10 |
| SM Key Data strip | Task 10 |
| SPECIAL_MONITOR_MILESTONES data (4 countries) | Task 8 |
| CSS for all new sections | Tasks 1, 9 |

All requirements covered.
