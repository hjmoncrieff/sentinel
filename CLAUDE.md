# SENTINEL — Project Context for Claude

> Civil-Military Relations Dashboard for Latin America
> Last updated: 2026-03-28

---

## What SENTINEL Is

A static-site intelligence dashboard tracking civil-military relations (CMR) across 25 Latin American and Caribbean countries. It ingests news, classifies events with Claude Haiku, and presents them on interactive maps and country profiles. Hosted on GitHub Pages; fully automated via GitHub Actions nightly cron.

**Research focus:** civilian control of the military, coup-proofing, institutional autonomy, SSR, democratic backsliding, transnational security threats, US security cooperation.

---

## Repository Layout

```
SENTINEL/
├── index.html                  ← Single-page dashboard (all tabs, all JS, all CSS)
├── CLAUDE.md                   ← This file
├── CODEBOOK.md → data/CODEBOOK.md
├── .env                        ← Local secrets (gitignored); GitHub Actions uses repo secrets
├── .gitignore
├── scripts/
│   ├── fetch_events.py         ← Main pipeline: RSS → filter → Claude classify → cluster → events.json
│   ├── fetch_worldbank.py      ← World Bank WDI + WGI, 1990–2025, 25 countries
│   ├── clean_vdem.py           ← V-Dem Core v16 → cleaned JSON/CSV
│   ├── clean_acled_index.py    ← ACLED Conflict Index 2025 → JSON
│   └── clean_greenbook.py      ← US Greenbook foreign aid → JSON/CSV
├── data/
│   ├── events.json             ← Live event store (pipeline output, source of truth)
│   ├── CODEBOOK.md             ← Dataset documentation
│   ├── raw/                    ← Source files (vdem.csv, ACLED_Conflict_Index_2025.xlsx, us_foreignaid_greenbook.xlsx, wb_*.json)
│   └── cleaned/                ← Processed outputs (worldbank.json/.csv, vdem.json/.csv, acled_index.json, greenbook.json/.csv)
└── .github/
    └── workflows/
        └── nightly.yml         ← GitHub Actions: runs fetch_events.py at 04:00 UTC daily
```

---

## Dashboard Architecture

- **Static site** — no server, no backend, no database. All data in `data/events.json` and inline JS.
- **Hosted**: GitHub Pages from `main` branch root.
- **Pipeline**: GitHub Actions `0 4 * * *` → `python3 scripts/fetch_events.py` → commits `data/events.json` with `[skip ci]` to prevent loops.
- **Local dev**: `python3 -m http.server 8000` or `npx http-server .`

---

## index.html Structure

### Tab bar (8 tabs, in order)
1. **Overview** — D3 choropleth SVG map + featured monitors + email subscription widget
2. **Events** — Leaflet map + sidebar event list + filters (type, country, confidence)
3. **US Cooperation** — US security aid charts
4. **Country Profiles** — sidebar country list + regional overview + individual per-country views with Leaflet maps
5. **Procurement & Arms** — arms deals and supplier trends
6. **Transnational Security** — OC/cartel events tab
7. **Timeline** — chronological event feed with filters
8. **About** — framework, methodology, data sources, citation

> **Note:** "Exercises & Multilateral" was removed as a standalone tab (2026-03-28). Exercises are now tracked as the `exercise` event type/tag, which appears in the Events and Timeline filters like any other event type. If a major exercise warrants attention, classify it as type `exercise` and it will surface across all relevant views.

### Event Type Color Scheme
| Type | CSS var | Hex |
|------|---------|-----|
| coup | `--coup` | `#b83232` |
| purge | `--purge` | `#c46e12` |
| conflict | `--conflict` | `#a84000` |
| reform | `--reform` | `#1a6e52` |
| aid | `--aid` | `#1a538f` |
| exercise | `--exercise` | `#2e6b8a` |
| oc | `--oc` | `#6a4a6e` |
| protest | `--protest` | `#6e389a` |
| peace | `--peace` | `#2d8659` |
| other | `--other` | `#6a6560` |

### Country Profile System
- `COUNTRY_PROFILES{}` — capital, regime, HoG, CMR status/class, GDP%, branches, note; Colombia/Venezuela/El Salvador/Mexico have `special:true, specialId:"cp-[id]"` to clone their rich HTML profile blocks
- `COUNTRY_STATS{}` — spending, personnel, US aid
- `COUNTRY_POSITIONS{}` — array of `{t: title, n: name}` for each country
- `COUNTRY_ELECTIONS{}` — type, date, note
- `COUNTRY_WATCH{}` — 1-sentence analytical watch item
- `COUNTRY_MAP_CONFIG{}` — Leaflet center + zoom per country
- `showCountryProfile(name)` — renders per-country view, clones special profiles, initializes Leaflet map (`initCpMap`)
- `showRegionalOverview()` — back to regional view

### Featured Monitors (Special Profiles)
Full deep-dive HTML blocks exist in `#cp-[country]-block` for:
- **Colombia** — peace process, armed groups, DDR data
- **Venezuela** — FANB structure, sanctions, 2025 political crisis
- **El Salvador** — Régimen de Excepción data, CECOT, US-Bukele alignment
- **Mexico** — SEDENA militarization, Sinaloa war, FTO designations

---

## fetch_events.py Pipeline

### Key parameters
```python
DAYS_BACK = 3          # lookback window (normal mode)
BATCH_SIZE = 8         # articles per Claude classify call
MODEL = "claude-haiku-4-5-20251001"
MAX_EVENTS = 500       # cap on events.json store
```

### CLI modes
```bash
python3 scripts/fetch_events.py             # normal (3-day lookback)
python3 scripts/fetch_events.py --backfill  # since 2026-01-01
```

### Data sources (active)
| Source | Type | Notes |
|--------|------|-------|
| InSight Crime | RSS | Primary for OC/cartel |
| The Guardian LatAm | RSS | English wire |
| BBC Mundo | RSS | Spanish-language |
| El País América | RSS | Spanish-language |
| El Tiempo Colombia | RSS | Colombia-specific |
| Folha de S.Paulo | RSS | Brazil |
| Crisis Group | RSS | Conflict analysis |
| AP Latin America | RSS | Wire |
| Americas Quarterly | RSS | Occasionally 0 items |
| Wilson Center LatAm | RSS | Occasionally 0 items |
| GDELT | API | Rate-limited; fine on nightly cron |
| NewsAPI | API | 3 queries (military, conflict, political); 30-day history limit on dev plan |

### Event schema
```json
{
  "id": "sha1[:12]",
  "title": "string",
  "date": "YYYY-MM-DD",
  "country": "string",
  "type": "coup|purge|conflict|reform|aid|exercise|oc|protest|peace|other",
  "salience": "high|medium|low",
  "conf": "green|yellow|red",
  "coords": [lat, lon],
  "location": "City/Region string",
  "source": "Source name",
  "url": "string",
  "summary": "string",
  "analysis": "string (high-salience only — Claude CMR analysis)"
}
```

### Geolocation
- `PLACE_COORDS` dict (~80 LatAm city/region → [lat, lon])
- `geolocate(text, country)` — longest-match-first search, falls back to `COUNTRY_CENTROIDS`
- `"location"` field in classify prompt — Claude provides city/region in output

### Deduplication
- `stable_id(country, type, iso_week)` — SHA1[:12] based on country + type + ISO week
- Events already in store are skipped; `--backfill` respects this too

### Clustering
- Groups same-incident articles per country using Claude
- Bracket-depth JSON parser fixes "Extra data" issue from Claude appending text after array

---

## Secret / Environment Management

| Variable | Use | Required |
|----------|-----|---------|
| `ANTHROPIC_API_KEY` | Claude Haiku classification | Yes |
| `NEWSAPI_KEY` | NewsAPI supplementary feed | Optional |
| `ACLED_API_KEY` / `ACLED_EMAIL` | ACLED real-time events | Optional (not yet active) |
| `DIGEST_TO/FROM`, `SMTP_*` | Weekly Monday email digest | Optional |

- **Local**: `.env` file auto-loaded by `fetch_events.py` pure-Python parser (no `python-dotenv`). Parser uses `os.environ[k] = v` with `if _v:` guard.
- **CI**: GitHub Actions repo secrets → injected as environment variables.
- `.env` is gitignored.

---

## Data Layers

### World Bank (`fetch_worldbank.py`)
- Coverage: 25 SENTINEL countries, 1990–2025
- Indicators: `population_total`, `gdp_constant_2015_usd`, `gdp_per_capita_constant_2015_usd`, `wgi_rule_of_law`, `wgi_govt_effectiveness`, `wgi_control_of_corruption`, `wgi_political_stability`, `military_expenditure_pct_gdp`, `military_expenditure_current_usd`, `military_personnel_total`
- Outputs: `data/cleaned/worldbank.json` (full series), `data/cleaned/worldbank.csv` (latest only)
- WGI sparse pre-2002 (biennial collection pre-2012)

### V-Dem (`clean_vdem.py`)
- Source: V-Dem Country-Year Core v16, `data/raw/vdem.csv`
- Coverage: 24 of 25 countries (Belize absent from V-Dem), 1990–2023
- Indicators: `polyarchy`, `regime_type`, `physinteg`, `mil_constrain`, `mil_exec`, `coup_event`, `coup_attempts`, `polity2`, `cs_repress`, `political_violence`
- Outputs: `data/cleaned/vdem.json`, `data/cleaned/vdem.csv`

### ACLED Conflict Index (`clean_acled_index.py`)
- Source: `data/raw/ACLED_Conflict_Index_2025.xlsx`, Results sheet
- Top LatAm: Mexico (#4), Ecuador (#6), Brazil (#7), Haiti (#8), Colombia (#14)
- Output: `data/cleaned/acled_index.json`

### US Greenbook (`clean_greenbook.py`)
- Source: `data/raw/us_foreignaid_greenbook.xlsx`, 72,638 rows, 1946–present
- Constant USD obligations by country/year/category (Economic vs Military)
- Top LatAm recipients (all-time): Colombia $26.96B, Brazil $20.69B, Peru $13.28B, El Salvador $12.70B
- Outputs: `data/cleaned/greenbook.json`, `data/cleaned/greenbook.csv`

---

## 25 Monitored Countries

| Country | ISO2 | Subregion |
|---------|------|-----------|
| Brazil | BR | Brazil |
| Colombia | CO | Andean |
| Mexico | MX | Mexico |
| Venezuela | VE | Andean |
| Chile | CL | Southern Cone |
| Argentina | AR | Southern Cone |
| Peru | PE | Andean |
| Ecuador | EC | Andean |
| Bolivia | BO | Andean |
| Cuba | CU | Caribbean |
| Honduras | HN | Central America |
| Guatemala | GT | Central America |
| El Salvador | SV | Central America |
| Nicaragua | NI | Central America |
| Paraguay | PY | Southern Cone |
| Uruguay | UY | Southern Cone |
| Haiti | HT | Caribbean |
| Dominican Republic | DO | Caribbean |
| Panama | PA | Central America |
| Costa Rica | CR | Central America |
| Jamaica | JM | Caribbean |
| Trinidad and Tobago | TT | Caribbean |
| Guyana | GY | Caribbean |
| Suriname | SR | Caribbean |
| Belize | BZ | Central America |

---

## Positions & Stats — Maintenance Notes

**Cadence**: Positions should be reviewed after any election, cabinet reshuffle, or commander rotation. Countries with elections in 2025–26 that need verification:

| Country | Event | Status |
|---------|-------|--------|
| Chile | Presidential election Nov 2025 + runoff Dec; inauguration Mar 11, 2026 | `[verify]` in dashboard |
| Bolivia | Presidential + legislative Aug 2025 | `[verify]` in dashboard |
| Honduras | Presidential + legislative Nov 2025 | `[verify]` in dashboard |
| Argentina | Legislative midterms Oct 2025 | Milei remains president |
| Ecuador | Presidential Feb 2025 | Noboa re-elected ✓ |
| Uruguay | Orsi since Mar 1, 2025 | Confirmed in dashboard |

**To update positions**: edit `COUNTRY_POSITIONS`, `COUNTRY_ELECTIONS`, and `COUNTRY_WATCH` objects in `index.html`. For special profiles (Colombia, Venezuela, El Salvador, Mexico), also update the HTML blocks `#cp-[country]-block`.

---

## GitHub Actions

```yaml
# .github/workflows/nightly.yml
name: nightly-pipeline
on:
  schedule:
    - cron: '0 4 * * *'   # 04:00 UTC daily
  workflow_dispatch:        # manual trigger
jobs:
  run:
    steps:
      - uses: actions/checkout@v4
      - run: pip install anthropic requests beautifulsoup4 feedparser
      - run: python3 scripts/fetch_events.py
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          NEWSAPI_KEY: ${{ secrets.NEWSAPI_KEY }}
      - run: |
          git config user.name "sentinel-bot"
          git config user.email "actions@github.com"
          git add data/events.json
          git diff --cached --quiet || git commit -m "chore: nightly event update [skip ci]"
          git push
```

---

## CMR Theoretical Framework

SENTINEL tracks six core civil-military relations concepts:

1. **Civilian Control** — subordination of military to elected civilian authority
2. **Coup-Proofing** — mechanisms (counterbalancing units, loyalty promotions, economic integration) used by leaders to prevent coups
3. **Institutional Autonomy** — degree to which officer corps retains policy/budgetary independence from civilian oversight
4. **SSR (Security Sector Reform)** — external/internal efforts to restructure security forces for democratic accountability
5. **Democratic Backsliding** — erosion of civilian control norms via executive encroachment (Bukele model) or military prerogatives
6. **Transnational Security** — cartel/OC interactions with state security forces, proxy relationships (e.g., Tren de Aragua / FANB)

**CMR Status classifications** used in dashboard:
- `Stable` — robust civilian control, no acute tensions
- `Strained` — friction between civilian/military but within institutional bounds
- `Crisis` — active breach of civilian control norms (Ecuador internal conflict framework, El Salvador régimen)
- `Authoritarian` — civil-military fusion; military as pillar of authoritarian regime (Venezuela, Cuba, Nicaragua)

---

## Tech Stack

| Library | Version | Use |
|---------|---------|-----|
| Leaflet | 1.9.4 | Events map + per-country profile maps |
| D3.js | v7 | Overview choropleth SVG map |
| TopoJSON Client | v3 | World topology for D3 map |
| Chart.js | 4.4.1 | All analytics charts (ResizeObserver for hidden panels) |
| Anthropic Python SDK | latest | Claude Haiku in pipeline |
| Fonts: DM Sans, DM Mono, Playfair Display | Google Fonts | Typography |

---

## Known Limitations / Future Work

- **DSCA/DEA scrapers** return 403 — replace with RSS or official data portals
- **ACLED real-time** — keys not yet configured; `ACLED_API_KEY` and `ACLED_EMAIL` in `.env` when ready
- **NewsAPI dev plan** — 30-day history limit; `--backfill` beyond 30 days will hit 426 error
- **V-Dem latest year** — v16 ends at 2023; update when v17 releases
- **Individual country charts** — V-Dem/WB series data cleaned but not yet visualized in per-country profile view
- **SIPRI TIV** — arms transfer data is manually entered; automate via SIPRI API when available
- **Email digest** — SMTP settings in `.env` but not yet wired to GitHub Actions secrets
