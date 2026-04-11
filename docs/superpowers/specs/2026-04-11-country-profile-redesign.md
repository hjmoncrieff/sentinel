# Country Profile Redesign — Design Spec

**Date:** 2026-04-11  
**Status:** Approved  
**Scope:** `showCountryProfile()` in `index.html` — layout, radar chart, and supporting data additions

---

## Overview

Redesign the per-country profile view in the Country Profiles tab. The primary addition is a hexagonal risk radar chart using Chart.js. The layout is simplified: the Leaflet per-country map and measure cards are removed; the profile reads as a clean analytical brief from top to bottom.

---

## New Layout (top to bottom)

```
1  Header          ← country name, capital/regime, CMR pill, back button
2  Summary strip   ← analytical summary text + Overall Risk score box
3  Radar section   ← hexagonal radar + score table with rank badges
   Sources band    ← muted attribution strip
4  Context / Watch ← two-column: Context note | What to Watch items
5  Reference band  ← three-column: Key Stats | Key Positions | Next Election
6  Event Pulse     ← 12-month stacked bar chart, computed from events.json
7  Live Events     ← full-width event list (no sidebar)
8  Structural Trends ← dark annex strip: 4 cells side by side
```

### Removed elements
- Leaflet per-country map (`cp-map-leaf`, `initCpMap`) — removed entirely
- Measure cards row (`cp-measure-row`, `cp-hero`) — replaced by radar
- Trends sparklines block (`trendsBlock`, `renderTrends()`) — replaced by Structural Trends annex
- Middle band grid (`cp-mid-grid`) — replaced by Context/Watch two-column
- `referenceBand` right-sidebar layout — replaced by full-width events

---

## Section 3 — Radar Chart

### Chart type
Chart.js 4.4.1 `radar`. Already loaded in `index.html`.

### Six axes (all risk-oriented: higher = more risk)

| Axis | Label (array for wrapping) | Source | Computation |
|---|---|---|---|
| 1 | `['Regime', 'Vulnerability']` | `country_monitors.json` | `risk_constructs[regime_vulnerability].score` (0–100) |
| 2 | `['Militarization']` | `country_monitors.json` | `risk_constructs[militarization].score` (0–100) |
| 3 | `['Security', 'Fragmentation']` | `country_monitors.json` | `risk_constructs[security_fragmentation].score` (0–100) |
| 4 | `['Democracy', 'Deficit']` | V-Dem (`vdem.json`) | `(1 − polyarchy) × 100` |
| 5 | `['Physical', 'Vulnerability']` | V-Dem (`vdem.json`) | `(1 − physinteg) × 100` |
| 6 | `['State', 'Fragility']` | WGI (`worldbank.json`) | `(1 − (wgi_govt_effectiveness + 2) / 4) × 100`, clamped 0–100 |

**Direction:** bigger shape = higher risk. All axes share the same 0–100 scale.

### Chart config
- `responsive: false`, `maintainAspectRatio: false`, fixed `258×258px`
- `layout.padding: 10`
- Scale: `min: 0`, `max: 100`, ticks hidden, `stepSize: 25`
- Grid and angleLines: `#1e2230`
- Point labels: `color: #6a6560`, size 9, `DM Mono`
- Dataset: `borderColor: rgba(184,50,50,0.7)`, `backgroundColor: rgba(180,50,50,0.10)`
- Tooltip: dark theme, title joins array labels, shows `X.X / 100`

### Score table (right column of radar section)
Two groups, separated by a `grp-lbl` header:

**Risk Constructs** — regime vulnerability, militarization, security fragmentation  
Each row: `name · score/100 · trend label (rising/easing) · rank badge (#X of 25)`

**Structural Indicators** — democracy deficit, physical vulnerability, state fragility  
Each row: `name · score/100 · rank badge (#X of 25)`

### Rank badges
Computed in-browser by sorting all 25 countries' scores for each axis from `country_monitors.json` and `_vdemData`/`_wbData`. Color thresholds (risk-oriented, higher rank = more concerning):
- `#1–6` (top quartile): red — `r-hi`
- `#7–18` (middle): orange — `r-md`
- `#19–25` (bottom quartile): green — `r-lo`

### Sources band
Slim dark strip (`#111419`) below radar section:  
`Sources · Risk constructs · SENTINEL Monitor · Democracy · Physical Integrity · V-Dem 2024 · State Fragility · WGI 2023`

---

## Section 4 — Context / What to Watch

Two equal columns, `1px` gap separator.

- **Context**: `prof.note` (existing field from `COUNTRY_PROFILES`)
- **What to Watch**: `summary.watchpoints[]` array from `getCountryPredictiveSummary()`, falling back to `COUNTRY_WATCH[name]`

---

## Section 5 — Reference Band

Three equal columns:

| Key Stats | Key Positions | Next Election |
|---|---|---|
| Spending, Personnel, Defence/GDP, US Aid | From `COUNTRY_POSITIONS[name]` | From `COUNTRY_ELECTIONS[name]` |

---

## Section 6 — Event Pulse

A stacked bar chart (Chart.js) showing the last 12 calendar months of event counts for this country. Computed at render time from `allEvents`.

- **X axis:** month labels (e.g. `Apr`, `May`, …)
- **Two stacks:**
  - Conflict / OC events: `rgba(168,64,0,0.5)`
  - All other events: `#2a2e3c` (muted)
- Height: `52px`
- Legend inline with month range label
- No Y axis displayed
- Updates automatically as `allEvents` grows from nightly pipeline

**Data computation:**
```js
// Group allEvents for country by month, last 12 months
// Stack: type === 'conflict' || type === 'oc' → hot bucket; else other
```

---

## Section 7 — Live Events

Full-width, no sidebar. Identical to current event rows in `showCountryProfile()`. Latest 12 events, sorted descending by date.

---

## Section 8 — Structural Indicator Trends

Dark annex strip (`background: #131720`). Four cells side by side, `1px` gap.

| Cell | Label | Value | Delta |
|---|---|---|---|
| 1 | Democracy Deficit | `score/100` | `±X.X vs YYYY` — red if positive (more risk), green if negative |
| 2 | Physical Vulnerability | `score/100` | same color logic |
| 3 | State Fragility | `score/100` | same color logic |
| 4 | GDP per Capita | `$X,XXX` (constant 2015 USD) | `±X.X% vs YYYY` — green if positive growth, red if contraction |

**Delta computation:**
- Democracy Deficit / Physical Vulnerability / State Fragility: compute current and prior-year values from V-Dem and WGI series, subtract
- GDP per capita: `(current − prior) / prior × 100`, formatted as `%`, from `worldbank.json` `gdp_per_capita_constant_2015_usd_series`

**Prior year:** most recent year with data minus 1.

---

## Data Dependencies

| Data | Already loaded? | Variable |
|---|---|---|
| Risk constructs (regime, mil, frag) | Yes | `countryMonitorsByCountry` |
| V-Dem series (polyarchy, physinteg) | Yes | `_vdemData` |
| World Bank series (wgi_govt_effectiveness, gdp_per_capita) | Yes | `_wbData` |
| Live events | Yes | `allEvents` |

All data is already fetched and available at profile render time. No new fetches required.

---

## Implementation Notes

- **Chart instance management:** destroy any existing radar/pulse Chart.js instances before re-rendering (e.g. when user navigates between countries). Use a module-level `let _cpRadarChart, _cpPulseChart` and call `.destroy()` before `new Chart(...)`.
- **Canvas IDs:** use `cp-radar-${safeId}` and `cp-pulse-${safeId}` to avoid conflicts with other charts on the page.
- **Special profiles** (Colombia, Venezuela, El Salvador, Mexico): the special focus block still renders below the standard layout (unchanged). The new layout replaces `baseProfile`, not the special content block.
- **Resize observer:** the Country Profiles tab may be hidden on load; Chart.js needs the canvas visible before rendering. Trigger render inside `showCountryProfile()` after `countryDiv.innerHTML = ...` is set, using `setTimeout(..., 0)` if needed.
- **`renderTrends()` and `makeSvgSparkline()`:** can be left in the codebase (used nowhere else to verify before removing), but the `trendsBlock` HTML is no longer injected.

---

## Files Changed

- `index.html` — the only file. All changes are within `showCountryProfile()` and supporting CSS.

---

# Part B — Special Monitor Sub-View

**Scope:** A dedicated deep-dive view for the four special-focus countries (Colombia, Venezuela, El Salvador, Mexico), reached by clicking an entry point inside the standard country profile.

---

## Navigation Model

Three-level stack, all within the Country Profiles tab:

```
showRegionalOverview()          ← back to regional list
  └─ showCountryProfile(name)   ← standard profile (Part A)
       └─ showSpecialMonitor(name)  ← special monitor (Part B)
```

- Entry point: a `★ Special Monitor` button rendered in the country profile header, visible only when `COUNTRY_PROFILES[name].special === true`.
- Back button in the special monitor header returns to `showCountryProfile(name)`, not to the regional overview.
- The special monitor replaces `#cp-country` content in-place (same scroll container). No new tab or panel.

---

## Layout (top to bottom)

```
1  Header          ← back button | country name + subtitle | ★ Special Monitor pill + CMR pill
2  Brief           ← analytical context text (left) | meta blocks: Focus period, Key dynamic (right)
3  Timeline        ← filter tabs + scrollable SVG timeline + compact event list below
4  Key Data strip  ← 4 fixed data cells, country-specific
```

---

## Section 1 — Header

- **Back:** `← [Country] Profile` — calls `showCountryProfile(name)` on click.
- **Country name** (large, serif) + subtitle line (topic focus, e.g. `Peace Process · Armed Conflict · CMR`).
- **Right side:** `★ Special Monitor` pill (red/muted) + CMR status pill (color-coded by status class).

---

## Section 2 — Brief

Two-column layout inside a single row:

- **Left:** Analytical context paragraph (~3–4 sentences). Source: `SPECIAL_MONITOR_MILESTONES[name].brief`. Plain prose, `font-size: 11.5px`, muted color.
- **Right:** Two stacked meta blocks (`Focus period` and `Key dynamic`), each with a mono kicker label and a short value. Source: `SPECIAL_MONITOR_MILESTONES[name].meta`.

---

## Section 3 — CMR Timeline

### Filter tabs

Eight filter buttons above the SVG figure:

| Button label | `data-c` value | Color when active |
|---|---|---|
| All | `all` | neutral (`#9a9590`) |
| Peace | `peace` | `#2d8659` |
| Military | `military` | `#a84000` |
| Political | `political` | `#1a6e82` |
| Armed Groups | `oc` | `#6a4a6e` |
| Reform | `reform` | `#1a538f` |
| International | `intl` | `#2e6b8a` |
| ● Live | `live` | `#c49a20` |

Active filter hides non-matching dots (opacity `0.07`, `pointer-events: none`) and non-matching event rows (`display: none`).

### SVG timeline geometry

```js
const PAD_L    = 32, PAD_R = 32;
const YEAR_W   = 90;           // px per year
const START    = 2016, END = 2027;
const YEARS    = END - START;  // 11
const SVG_W    = PAD_L + YEARS * YEAR_W + PAD_R;  // 1054px
const AXIS_Y   = 110;          // axis y-position from top of SVG
const DOT_R    = 5;
const STEM_BASE = 18;          // minimum stem height in px
const STEP     = 16;           // extra px per collision level
```

All events sit **above** the axis. Stem height = `STEM_BASE + level * STEP`.

### Collision-level algorithm

```js
function assignLevels(events) {
  const sorted = [...events].sort((a,b) => a.date.localeCompare(b.date));
  const placed = [];
  sorted.forEach(ev => {
    const x = dateToX(ev.date);
    let level = 0;
    while (placed.some(p => p.level === level && Math.abs(p.x - x) < 38)) level++;
    placed.push({ ...ev, x, level });
  });
  return placed;
}
```

Minimum horizontal gap before a new level is required: **38px**.

### Visual elements

- **Year bands:** alternating faint rect fills `rgba(255,255,255,0.008)` for even years.
- **Axis:** `stroke: #252830`, `stroke-width: 1.5`.
- **Year ticks + labels:** DM Mono, 9.5px, color `#3e3c38`, centered at year start.
- **"NOW" dashed line:** `stroke: rgba(196,80,32,0.22)`, `stroke-dasharray: 3,3`, text label `NOW` in same color.
- **Stems:** `stroke-width: 1`, `stroke-opacity: 0.2` default; highlighted stem → `0.65`.
- **Dots:** `r=5`, `fill: #161a22` (dark background), `stroke: CAT_COLOR`, `stroke-width: 2`. Click fills dot with `CAT_COLOR`.
- **Pulse ring:** `r=10`, hidden by default (`stroke-opacity: 0`), shown on hover/active at `0.3`/`0.35`.
- **Hit area:** transparent `r=13` circle for easier click targeting.

### Tooltip (foreignObject)

Each dot has a `<foreignObject>` tooltip pinned above the dot, hidden by default (`display: none`). Contains: date (mono, 7.5px, muted) + category label (colored, uppercase) + event title. Flips left if dot is within 200px of right edge. Shown on hover (if not active) or on click (always).

### Compact event list (below SVG)

Rendered below the scroll hint, inside the same section. Sorted newest-first. Each row:

```
[2px cat-color bar] | [date, 58px] | [category label, 90px] | [title, flex-1]
```

Click on a row calls `selectEvent(id)`, which highlights the corresponding dot and expands an inline description row below the event row. Clicking again deselects.

Live events carry a `live` pip badge (amber, small caps).

### SVG container

- `overflow-x: auto; overflow-y: visible` — horizontal scroll only.
- Thin scrollbar (`scrollbar-width: thin`).
- Scroll hint text below figure: `scroll to explore full timeline`.

---

## Section 4 — Key Data Strip

Dark background (`#131720`). Four equal cells in a flex row with `1px` gaps.

Each cell:
- **Name** (mono, 8.5px, very muted)
- **Value** (mono, 15px, bold, mid-gray)
- **Sub** (mono, 8.5px, very muted) — e.g. context / year reference

Source: `SPECIAL_MONITOR_MILESTONES[name].keyData` — array of `{ name, value, sub }`.

---

## Data Structure — `SPECIAL_MONITOR_MILESTONES`

New JS object defined in `index.html`, one entry per special country:

```js
const SPECIAL_MONITOR_MILESTONES = {
  Colombia: {
    brief: "...",           // analytical context paragraph
    meta: [
      { kicker: "Focus period", value: "2016 – present\nPost-agreement arc" },
      { kicker: "Key dynamic",  value: "Peace process vs. military autonomy" },
    ],
    timelineStart: 2016,
    events: [
      { id: "e1", date: "YYYY-MM-DD", cat: "peace|military|political|oc|reform|intl|live", title: "...", desc: "..." },
      // ...
    ],
    keyData: [
      { name: "FARC ex-combatants", value: "13,202", sub: "enrolled in DDR · 2016" },
      // ...
    ],
  },
  Venezuela: { ... },
  "El Salvador": { ... },
  Mexico: { ... },
};
```

`live` events are those sourced from `allEvents` for this country — they are merged with the curated `events` array at render time, deduped by `id`.

---

## CMR Category Color Map

```js
const SM_CAT_COLOR = {
  peace:    '#2d8659',
  military: '#a84000',
  political:'#1a6e82',
  oc:       '#6a4a6e',
  reform:   '#1a538f',
  intl:     '#2e6b8a',
  live:     '#c49a20',
};
```

---

## Implementation Notes

- **Function:** `showSpecialMonitor(name)` — replaces `#cp-country` innerHTML. Called from a button inside `showCountryProfile()`.
- **Chart.js:** not used in the special monitor. The SVG timeline is pure SVG + DOM, no Chart.js dependency.
- **Live event merging:** at render time, filter `allEvents` for `country === name` and `date >= SPECIAL_MONITOR_MILESTONES[name].timelineStart + '-01-01'`. Assign `cat: 'live'`. Merge with curated events array, dedup by `id`, sort by date.
- **Canvas ID conflicts:** none — no canvases in the special monitor.
- **Existing special profile HTML blocks** (`#cp-colombia-block`, etc.): these blocks are cloned by the current `showCountryProfile()` logic. Under the new design, `showSpecialMonitor()` replaces this mechanism for the four special countries — the static HTML blocks can be retired once the dynamic special monitor is implemented.
- **`showSpecialMonitor()` subtitle line:** pulled from `SPECIAL_MONITOR_MILESTONES[name].subtitle` (e.g. `"Peace Process · Armed Conflict · CMR"`).

---

## Files Changed (Part B)

- `index.html` — add `SPECIAL_MONITOR_MILESTONES` object, `showSpecialMonitor(name)` function, CSS for special monitor card, and entry-point button in `showCountryProfile()`.
