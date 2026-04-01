# SENTINEL Data Codebook

**Project:** SENTINEL — Latin American Civil-Military Events Monitor
**Codebook last updated:** 2026-03-27
**Maintainer:** SENTINEL Research Team

This codebook documents every dataset used by SENTINEL: its source, coverage, indicators, file locations, and update cadence. All paths are relative to the repository root.

---

## Table of Contents

1. [Events Pipeline (SENTINEL-generated)](#1-events-pipeline)
2. [World Bank — Development Indicators & Governance](#2-world-bank)
3. [V-Dem — Varieties of Democracy](#3-v-dem)
4. [ACLED — Armed Conflict Location & Event Data](#4-acled)
5. [SIPRI — Military Expenditure](#5-sipri) *(planned)*
6. [UNODC — Drug & Crime Data](#6-unodc) *(planned)*

---

## 1. Events Pipeline

**Description:** The core SENTINEL event log. Ingested nightly by the GitHub Actions pipeline from open-source news feeds, GDELT, NewsAPI, and ACLED. Each record represents a classified civil-military relations event with AI-generated analysis.

| Field | | |
|---|---|---|
| **Source** | GDELT v2, NewsAPI, InSight Crime RSS, Reuters LatAm RSS, NACLA RSS, SOUTHCOM RSS, ACLED API | |
| **Coverage** | 25 Latin American countries | 2024–present |
| **Update cadence** | Nightly (GitHub Actions cron: `0 4 * * *`) | |
| **Raw files** | None — pipeline writes directly to cleaned output | |
| **Cleaned file** | `data/events.json` | |
| **Fetch script** | `scripts/fetch_events.py` | |

### Schema

| Field | Type | Description |
|---|---|---|
| `id` | string (hex12) | Stable SHA1-based ID: `sha1(country + type + ISO_week)[:12]` |
| `type` | string | Event type: `coup`, `purge`, `aid`, `protest`, `reform`, `conflict`, `exercise`, `procurement`, `peace`, `oc`, `other` |
| `title` | string | Article headline or synthesized title |
| `country` | string | SENTINEL canonical country name (see §Coverage below) |
| `date` | string (YYYY-MM-DD) | Event date |
| `source` | string | Primary source outlet |
| `sources` | array[string] | All outlets covering this event (after clustering) |
| `conf` | string | Source confidence: `green` / `yellow` / `red` |
| `salience` | string | Event significance: `high` / `medium` / `low` |
| `coords` | [lat, lon] | Geographic coordinates for map placement |
| `summary` | string | 1–2 sentence summary |
| `ai_analysis` | string | AI-generated CMR analysis (high-salience events only) |
| `url` | string | Primary source URL |
| `links` | array[string] | All source URLs |
| `ingested_at` | string (ISO 8601) | Pipeline ingestion timestamp |

### Actor Hierarchy Note

SENTINEL is moving toward a hierarchical actor model in the canonical event layer. The intended logic is:

- `actor_type` = broad category such as `organized_crime`, `armed_group`, `military`, `executive`
- `actor_subtype` = subcategory such as `cartel`, `gang`, `dissident_faction`, `state_security_force`, `state_institution`
- `actor_canonical_name` = specific named actor such as `Tren de Aragua`, `ELN`, `CJNG`

This hierarchy is currently implemented in the actor-coded canonical layer under `data/canonical/` and will eventually be documented as a full standalone actor codebook.

### Event Type Codes

| Code | Label | Description |
|---|---|---|
| `coup` | Coup / Coup Plot | Attempted or rumoured seizure of power; assassination of political/military figures |
| `purge` | Purge / Reshuffle | Forced dismissals, retirements, or command restructuring of military/police officers |
| `aid` | Military Aid | Foreign military assistance, FMF transfers, IMET, equipment deliveries |
| `protest` | Civil-Military Protest | Civil unrest involving security forces; military-linked social movements |
| `reform` | Security Sector Reform | Legislative or doctrinal changes to armed forces, defence white papers, oversight reforms |
| `conflict` | Armed Conflict | Combat operations involving state security forces and non-state armed actors |
| `exercise` | Military Exercise | Bilateral or multilateral training exercises, joint operations |
| `procurement` | Procurement / Arms | Weapons acquisitions, defence contracts, arms transfers |
| `peace` | Peace Process | Negotiations, ceasefires, DDR milestones |
| `oc` | Transnational Crime | Military operations against organised crime, narco-trafficking, illicit mining |
| `other` | Other | Institutionally significant events not captured above |

---

## 2. World Bank

**Description:** World Development Indicators (WDI) and Worldwide Governance Indicators (WGI) for all 25 SENTINEL countries. Fetched directly from the World Bank REST API — no authentication required.

| Field | | |
|---|---|---|
| **Source** | World Bank Open Data API v2 (`api.worldbank.org/v2/`) | |
| **Source URL** | https://data.worldbank.org | |
| **API docs** | https://datahelpdesk.worldbank.org/knowledgebase/articles/889392 | |
| **Coverage** | 25 Latin American countries | Most recent available year (typically 2023) |
| **Update cadence** | Run manually or add to GitHub Actions. Re-run annually. | |
| **Raw files** | `data/raw/wb_<indicator_name>.json` (9 files, last 5 years per indicator) | |
| **Cleaned file** | `data/cleaned/worldbank.json` · `data/cleaned/worldbank.csv` | |
| **Fetch script** | `scripts/fetch_worldbank.py` | |
| **Last fetched** | 2026-03-27 | |

### Indicators

| Column name | World Bank code | Label | Unit | Series |
|---|---|---|---|---|
| `population_total` | `SP.POP.TOTL` | Population, total | Persons | WDI |
| `gdp_constant_2015_usd` | `NY.GDP.MKTP.KD` | GDP (constant 2015 USD) | USD | WDI |
| `gdp_per_capita_constant_2015_usd` | `NY.GDP.PCAP.KD` | GDP per capita (constant 2015 USD) | USD | WDI |
| `wgi_rule_of_law` | `RL.EST` | Rule of Law: Estimate | −2.5 to +2.5 | WGI |
| `wgi_govt_effectiveness` | `GE.EST` | Government Effectiveness: Estimate | −2.5 to +2.5 | WGI |
| `wgi_control_of_corruption` | `CC.EST` | Control of Corruption: Estimate | −2.5 to +2.5 | WGI |
| `wgi_political_stability` | `PV.EST` | Political Stability & Absence of Violence: Estimate | −2.5 to +2.5 | WGI |
| `military_expenditure_pct_gdp` | `MS.MIL.XPND.GD.ZS` | Military expenditure (% of GDP) | % | WDI |
| `military_expenditure_current_usd` | `MS.MIL.XPND.CD` | Military expenditure (current USD) | USD | WDI |
| `military_personnel_total` | `MS.MIL.TOTL.P1` | Armed forces personnel, total | Persons | WDI |

**Note on WGI scores:** Higher is better. +2.5 = strongest governance; −2.5 = weakest. The WGI composite scores are produced by the World Bank using an Unobserved Components Model aggregating ~30 underlying data sources. Scores are comparable across years but not perfectly comparable across indicators (each has its own distribution).

**Note on `wgi_govt_effectiveness`:** Used in SENTINEL as the primary proxy for **state capacity**. Captures perceptions of the quality of public services, policy implementation, and credibility of government commitment.

### Raw File Format

Each `data/raw/wb_<indicator>.json` contains the raw World Bank API response: an array of country-year records with fields `indicator`, `country`, `date`, `value`, `countryiso3code`, `unit`, `obs_status`, `decimal`.

### Cleaned File Format

`data/cleaned/worldbank.json`:
```json
{
  "updated": "2026-03-27T15:40:22Z",
  "indicators": ["population_total", "gdp_constant_2015_usd", ...],
  "countries": [
    {
      "country": "Argentina",
      "iso2": "AR",
      "population_total": 45696159,
      "population_total_year": "2023",
      "wgi_rule_of_law": -0.41,
      "wgi_rule_of_law_year": "2023",
      ...
    }
  ]
}
```

Each indicator column has a companion `<indicator>_year` column recording which year the value comes from (most recent non-null observation, up to 5 years back).

---

## 3. V-Dem

**Description:** Varieties of Democracy country-year dataset. Provides fine-grained indices of democratic quality, civil liberties, and — critically for SENTINEL — military constraints on executive authority (`v2elmilcap`).

| Field | | |
|---|---|---|
| **Source** | V-Dem Institute, University of Gothenburg | |
| **Source URL** | https://www.v-dem.net/data/the-v-dem-dataset/ | |
| **Version** | Country-Year Core v16 | |
| **Coverage** | 25 Latin American countries | 1900–2023 (SENTINEL uses 2000–2023) |
| **Update cadence** | Annual release (typically Q1). Re-run cleaner on each new version. | |
| **Download** | Manual — requires email + CAPTCHA at source URL above. Select "Country-Year: V-Dem Core". | |
| **Raw file** | `data/raw/V-Dem-CY-Core-v16.csv` *(place here after download)* | |
| **Cleaned file** | `data/cleaned/vdem.json` | |
| **Clean script** | `scripts/clean_vdem.py data/raw/V-Dem-CY-Core-v16.csv` | |
| **Last fetched** | Not yet downloaded | |

### Indicators Extracted

| Column name | V-Dem variable | Label | Range |
|---|---|---|---|
| `vdem_libdem` | `v2x_libdem` | Liberal democracy index | 0–1 |
| `vdem_polyarchy` | `v2x_polyarchy` | Electoral democracy index | 0–1 |
| `vdem_civlib` | `v2x_civlib` | Civil liberties index | 0–1 |
| `vdem_rol` | `v2xcl_rol` | Rule of law (civil liberties dimension) | 0–1 |
| `vdem_corruption` | `v2x_corr` | Political corruption index | 0–1 (higher = more corrupt) |
| `vdem_mil_constrain` | `v2elmilcap` | Military constraints on executive | ordinal, higher = more constrained |
| `vdem_cspart` | `v2x_cspart` | Civil society participation | 0–1 |
| `vdem_execorrup` | `v2x_execorr` | Executive corruption | 0–1 (higher = more corrupt) |
| `vdem_physinteg` | `v2x_clphy` | Physical integrity index | 0–1 |

**Note on `v2elmilcap`:** This is SENTINEL's primary V-Dem variable for civil-military relations. It measures whether the military can remove the head of government and the extent to which the military exercises autonomy from civilian oversight. Scale is ordinal (0 = no constraints on military, 4 = full civilian control). See V-Dem codebook §3.8.

### Cleaned File Format

`data/cleaned/vdem.json`:
```json
{
  "updated": "...",
  "source": "V-Dem Country-Year Core v16",
  "columns": { "vdem_libdem": "Liberal democracy index", ... },
  "countries": [
    {
      "country": "Colombia",
      "year": 2023,
      "vdem_libdem": 0.42,
      "vdem_polyarchy": 0.51,
      "vdem_mil_constrain": 3.2,
      "libdem_trend": [{"year": 2014, "value": 0.51}, ...]
    }
  ]
}
```

The `libdem_trend` array contains the last 10 years of liberal democracy scores for dashboard sparklines.

---

## 4. ACLED

**Description:** Armed Conflict Location & Event Data Project. Provides georeferenced conflict events. Used directly in the SENTINEL events pipeline as a structured data source alongside news feeds.

| Field | | |
|---|---|---|
| **Source** | ACLED (`acleddata.com`) | |
| **Source URL** | https://acleddata.com/data-export-tool/ | |
| **API docs** | https://apidocs.acleddata.com | |
| **Coverage** | Regions 6 (Central America), 7 (South America), 15 (Caribbean) | |
| **Update cadence** | Nightly via pipeline (`scripts/fetch_events.py`) | |
| **Authentication** | Requires `ACLED_API_KEY` + `ACLED_EMAIL` (free registration) | |
| **Raw files** | Not saved separately — merged into `data/events.json` | |
| **Cleaned file** | `data/events.json` | |

### Fields Used

| ACLED field | SENTINEL field | Notes |
|---|---|---|
| `event_type` | `type` | Remapped to SENTINEL type taxonomy |
| `country` | `country` | Normalised to SENTINEL canonical names |
| `event_date` | `date` | |
| `latitude` / `longitude` | `coords` | |
| `notes` | `summary` | Truncated |
| `source` | `source` | |

---

## 5. SIPRI Military Expenditure *(planned)*

**Description:** Stockholm International Peace Research Institute annual military expenditure database. More authoritative than World Bank for defence spending; includes constant USD, current USD, and % GDP.

| Field | | |
|---|---|---|
| **Source** | SIPRI (`sipri.org/databases/milex`) | |
| **Source URL** | https://www.sipri.org/databases/milex | |
| **Coverage** | All SENTINEL countries | 1949–present |
| **Download** | Manual Excel download from source URL above | |
| **Raw file** | `data/raw/SIPRI-Milex-data-<year>.xlsx` *(place here after download)* | |
| **Cleaned file** | `data/cleaned/sipri.json` *(not yet built)* | |
| **Clean script** | `scripts/clean_sipri.py` *(not yet built)* | |
| **Status** | Planned | |

---

## 6. UNODC Drug & Crime Data *(planned)*

**Description:** United Nations Office on Drugs and Crime. Primary source for coca cultivation estimates (Colombia, Peru, Bolivia), seizure data, and homicide rates.

| Field | | |
|---|---|---|
| **Source** | UNODC (`dataunodc.un.org`) | |
| **Source URL** | https://dataunodc.un.org | |
| **Coverage** | Selected SENTINEL countries | Annual |
| **Download** | Manual CSV/Excel from UNODC data portal | |
| **Raw file** | `data/raw/unodc_<topic>_<year>.csv` | |
| **Cleaned file** | `data/cleaned/unodc.json` *(not yet built)* | |
| **Clean script** | `scripts/clean_unodc.py` *(not yet built)* | |
| **Status** | Planned | |

---

## Country Coverage

All datasets use the following canonical country names. Any raw dataset with variant spellings must be normalised to this list before ingestion.

| SENTINEL name | ISO2 | ISO3 | ISO numeric |
|---|---|---|---|
| Argentina | AR | ARG | 32 |
| Belize | BZ | BLZ | 84 |
| Bolivia | BO | BOL | 68 |
| Brazil | BR | BRA | 76 |
| Chile | CL | CHL | 152 |
| Colombia | CO | COL | 170 |
| Costa Rica | CR | CRI | 188 |
| Cuba | CU | CUB | 192 |
| Dominican Republic | DO | DOM | 214 |
| Ecuador | EC | ECU | 218 |
| El Salvador | SV | SLV | 222 |
| Guatemala | GT | GTM | 320 |
| Guyana | GY | GUY | 328 |
| Haiti | HT | HTI | 332 |
| Honduras | HN | HND | 340 |
| Jamaica | JM | JAM | 388 |
| Mexico | MX | MEX | 484 |
| Nicaragua | NI | NIC | 558 |
| Panama | PA | PAN | 591 |
| Paraguay | PY | PRY | 600 |
| Peru | PE | PER | 604 |
| Suriname | SR | SUR | 740 |
| Trinidad and Tobago | TT | TTO | 780 |
| Uruguay | UY | URY | 858 |
| Venezuela | VE | VEN | 862 |

---

## File Index

| File | Description | Last updated | Auto-updated? |
|---|---|---|---|
| `data/events.json` | SENTINEL events pipeline output | Nightly | ✅ GitHub Actions |
| `data/raw/wb_population_total.json` | World Bank population raw | 2026-03-27 | Manual (`fetch_worldbank.py`) |
| `data/raw/wb_gdp_constant_2015_usd.json` | World Bank GDP constant raw | 2026-03-27 | Manual |
| `data/raw/wb_gdp_per_capita_constant_2015_usd.json` | World Bank GDP/capita raw | 2026-03-27 | Manual |
| `data/raw/wb_wgi_rule_of_law.json` | World Bank Rule of Law raw | 2026-03-27 | Manual |
| `data/raw/wb_wgi_govt_effectiveness.json` | World Bank Govt Effectiveness raw | 2026-03-27 | Manual |
| `data/raw/wb_wgi_control_of_corruption.json` | World Bank Corruption Control raw | 2026-03-27 | Manual |
| `data/raw/wb_wgi_political_stability.json` | World Bank Political Stability raw | 2026-03-27 | Manual |
| `data/raw/wb_military_expenditure_pct_gdp.json` | World Bank mil. exp. % GDP raw | 2026-03-27 | Manual |
| `data/raw/wb_military_expenditure_current_usd.json` | World Bank mil. exp. USD raw | 2026-03-27 | Manual |
| `data/raw/V-Dem-CY-Core-v16.csv` | V-Dem raw *(not yet downloaded)* | — | Manual download |
| `data/cleaned/worldbank.json` | World Bank — all indicators merged | 2026-03-27 | Manual |
| `data/cleaned/worldbank.csv` | World Bank — same, CSV format | 2026-03-27 | Manual |
| `data/raw/wb_military_personnel_total.json` | World Bank mil. personnel raw | 2026-03-27 | Manual |
| `data/cleaned/vdem.json` | V-Dem — selected indicators *(not yet built)* | — | Run `clean_vdem.py` |
| `data/CODEBOOK.md` | This file | 2026-03-27 | Manual |
