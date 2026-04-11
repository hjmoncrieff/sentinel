# SENTINEL Data Codebook

**Project:** SENTINEL — Latin American Civil-Military Events Monitor
**Codebook last updated:** 2026-04-02
**Maintainer:** SENTINEL Research Team

This codebook documents every dataset used by SENTINEL: its source, coverage, indicators, file locations, and update cadence. All paths are relative to the repository root.

Documentation rule: whenever a new variable, field, construct, or dataset
column is added to the project, this codebook should be updated in the same
change set.

---

## Table of Contents

1. [Events Pipeline (SENTINEL-generated)](#1-events-pipeline)
2. [World Bank — Development Indicators & Governance](#2-world-bank)
3. [V-Dem — Varieties of Democracy](#3-v-dem)
4. [ACLED — Armed Conflict Location & Event Data](#4-acled)
5. [SIPRI — Military Expenditure](#5-sipri) *(planned)*
6. [UNODC — Drug & Crime Data](#6-unodc) *(planned)*
7. [Private Modeling Layer (SENTINEL-generated)](#7-private-modeling-layer)

---

## 1. Events Pipeline

**Description:** The core SENTINEL event log. Ingested nightly by the GitHub Actions pipeline from open-source news feeds, GDELT, NewsAPI, and ACLED. Each record represents a classified political-risk and security event, with optional AI-generated analytical interpretation layered on top.

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

SENTINEL now uses a hierarchical actor model in the canonical event layer:

- `actor_category` = broad class such as `state_actor` or `non_state_actor`
- `actor_group` = branch such as `military`, `executive`, `civil_society`, `economic_group`, or `armed_non_state_actor`
- `actor_type` = specific actor class such as `state_security_force`, `state_institution`, `armed_group`, or `organized_crime`
- `actor_subtype` = finer subtype such as `cartel`, `gang`, `dissident_faction`, `state_security_force`, `state_institution`
- `actor_canonical_name` = specific named actor such as `Tren de Aragua`, `ELN`, `CJNG`

Example:

- `actor_category = non_state_actor`
- `actor_group = armed_non_state_actor`
- `actor_type = organized_crime`
- `actor_subtype = transnational_network`
- `actor_canonical_name = Tren de Aragua`

Registry files now follow a modular pattern:

- `config/actors/nsva_registry_seed.json`
  named organized-crime and armed non-state actors
- `config/actors/broad_actor_registry_seed.json`
  reusable state, civil-society, economic, media, protest, and international actors
- `config/actors/actor_registry.json`
  merged durable registry used by the actor-coding pipeline

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
| **Coverage** | 25 Latin American countries | Full cleaned series now spans 1960–2025 where indicators exist |
| **Update cadence** | Run manually or add to GitHub Actions. Re-run annually. | |
| **Raw files** | `data/raw/wb_<indicator_name>.json` (one file per indicator, full 1960–2025 series) | |
| **Cleaned file** | `data/cleaned/worldbank.json` · `data/cleaned/worldbank.csv` | |
| **Fetch script** | `scripts/fetch_worldbank.py` | |
| **Last fetched** | 2026-04-02 | |

### Indicators

| Column name | World Bank code | Label | Unit | Series |
|---|---|---|---|---|
| `population_total` | `SP.POP.TOTL` | Population, total | Persons | WDI |
| `gdp_constant_2015_usd` | `NY.GDP.MKTP.KD` | GDP (constant 2015 USD) | USD | WDI |
| `gdp_per_capita_constant_2015_usd` | `NY.GDP.PCAP.KD` | GDP per capita (constant 2015 USD) | USD | WDI |
| `inflation_consumer_prices_pct` | `FP.CPI.TOTL.ZG` | Inflation, consumer prices (annual %) | % | WDI |
| `real_interest_rate` | `FR.INR.RINR` | Real interest rate | % | WDI |
| `trade_openness_pct_gdp` | `NE.TRD.GNFS.ZS` | Trade (% of GDP) | % GDP | WDI |
| `oda_received_pct_gni` | `DT.ODA.ODAT.GN.ZS` | Net ODA received (% of GNI) | % GNI | WDI |
| `official_exchange_rate` | `PA.NUS.FCRF` | Official exchange rate (LCU per US$, period average) | Rate | WDI |
| `fdi_net_inflows_pct_gdp` | `BX.KLT.DINV.WD.GD.ZS` | Foreign direct investment, net inflows (% of GDP) | % | WDI |
| `debt_service_pct_exports` | `DT.TDS.DECT.EX.ZS` | Total debt service (% of exports of goods, services and primary income) | % | WDI |
| `current_account_pct_gdp` | `BN.CAB.XOKA.GD.ZS` | Current account balance (% of GDP) | % | WDI |
| `reserves_months_imports` | `FI.RES.TOTL.MO` | Total reserves in months of imports | Months | WDI |
| `resource_rents_pct_gdp` | `NY.GDP.TOTL.RT.ZS` | Total natural resource rents (% of GDP) | % | WDI |
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
| `event_category` | string/null | Broad construct-aware analytical family for the event, such as `political`, `military`, `security`, or `international` |
| `event_subcategory` | string/null | Narrower mechanism-oriented taxonomy bucket derived from the event type |
| `event_construct_destinations` | array | Higher-order constructs the event most directly feeds |
| `event_analyst_lenses` | array | Primary analyst lenses the event should activate first under the construct-aware council design |

For `event_type = other`, the canonical builder now applies a small context-
based taxonomy overlay so `event_subcategory` can still capture recurring
mechanisms such as:

- `diplomatic_pressure_and_external_alignment`
- `judicial_and_accountability_shock`
- `electoral_contestation_and_realignment`
- `institutional_drift_and_leadership_project`
- `macro_stress_and_policy_shock`
- `external_pressure_and_alignment_watch`

This enrichment logic now also extends across the main event families. Current
examples include:

- `oc`
  - `trafficking_logistics_and_route_shift`
  - `criminal_violence_and_social_control`
  - `criminal_interdiction_and_state_response`
  - `criminal_policy_and_legal_reclassification`
- `peace`
  - `peace_process_electoral_stress`
  - `transitional_justice_and_accountability`
  - `peace_process_breakdown_and_spoilers`
  - `negotiation_and_settlement_dynamics`
- `coop`
  - `operational_security_cooperation`
  - `foreign_training_and_advisory_presence`
  - `regional_security_alignment_and_strategy`
- `coup`, `purge`, `aid`, `protest`, `reform`, `exercise`, and `conflict`
  - now also carry more mechanism-specific subcategories in the canonical,
    council, and published layers
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

## 7. Private Modeling Layer

**Description:** Private/internal modeling artifacts used for calibration,
forecasting design, and panel-based validation. These outputs are not public
dashboard products.

| Field | | |
|---|---|---|
| **Source** | SENTINEL structural refresh + reviewed event layer | |
| **Coverage** | Country-month panel for LATAM/CAR countries with structural coverage | Current panel rows: 2000–present where monthly structural rows exist |
| **Update cadence** | Manual rebuild during modeling work | |
| **Cleaned files** | `data/modeling/country_month_panel.json` · `data/modeling/country_month_panel.csv` | |
| **Build script** | `scripts/analysis/build_country_month_panel.py` | |
| **Status** | Active, private/internal | |

### Country-Month Panel

The country-month panel joins annual structural data from
`data/cleaned/country_year.json` with monthly event-derived pulse features from
`data/review/events_with_edits.json`.

Coverage distinction:

- `operational/product window`
  - the live monitoring and product window remains `1990-present`
- `current panel row coverage`
  - now spans `1960-01` through `2025-12`
- `training-history window`
  - now actively includes `1960-1989`
  - may extend earlier than `1960` later when structural country-year history
    is available and used privately for training, calibration, or long-run
    legacy features

This distinction should remain explicit. Broader training history does not
automatically mean broader live product coverage.

Current training-history audit:

- `data/review/training_history_coverage_audit.json`
  - private audit of whether the merged structural layer already contains any
    pre-1990 rows usable for a deeper training-history window
- current finding:
  - `country_year.json` now spans `1960-2025`
  - current pre-1990 merged rows: `750`
  - pre-1990 merged coverage now exists for all `25` countries

Current upstream-source audit:

- `data/review/upstream_training_source_audit.json`
  - private audit of whether the current lower bound comes from source limits
    or from the existing ingest/build scripts

Recent structural additions now carried into `country_year` and the private
country-month panel include:

- `coup_total_events`
- `executive_direct_election`
- `democracy_breakdown`
- `democracy_transition`
- `trade_openness_pct_gdp`
- `oda_received_pct_gni`
- `time_since_last_coup`
- `time_since_last_coup_attempt`
- `coup_count_5y`
- `coup_count_10y`
- `polyarchy_delta_1y`
- `trade_openness_delta_3y`
- `oda_received_delta_3y`
- `regime_shift_flag`
- `repression_shift_flag`
- `macro_stress_shift_flag`

### Core Index Fields

| Field | Type | Description |
|---|---|---|
| `country` | string | SENTINEL canonical country name |
| `iso3` | string | ISO3 country code |
| `year` | integer | Panel year |
| `month` | integer | Panel month |
| `panel_date` | string | First day of the panel month (`YYYY-MM-01`) |
| `panel_month_id` | string | Compact month key (`YYYY-MM`) |

### Structural Inputs Included

Representative structural fields currently carried into the panel include:

- V-Dem democracy and governance indicators such as:
  - `polyarchy`
  - `liberal_democracy`
  - `regime_type`
  - `mil_constrain`
  - `mil_exec`
  - `judicial_constraints`
  - `legislative_constraints`
  - `state_authority`
- World Bank governance and macro fields such as:
  - `wgi_rule_of_law`
  - `wgi_govt_effectiveness`
  - `wgi_control_corruption`
  - `wgi_political_stability`
  - `gdp_const_2015_usd`
  - `gdp_per_capita_const_usd`
  - `inflation_consumer_prices_pct`
  - `real_interest_rate`
  - `official_exchange_rate`
  - `fdi_net_inflows_pct_gdp`
  - `debt_service_pct_exports`
  - `current_account_pct_gdp`
  - `reserves_months_imports`
  - `resource_rents_pct_gdp`
  - `population`
- M3 and related civil-military structure fields such as:
  - `m3_conscription`
  - `m3_conscription_gender`
  - `m3_conscription_dur_max`
  - `m3_conscription_dur_min`
  - `m3_alt_civil_service`
  - `m3_mil_origin`
  - `m3_mil_leader`
  - `m3_mil_mod`
  - `m3_mil_veto`
  - `m3_mil_repress`
  - `m3_mil_repress_count`
  - `m3_mil_impunity`
  - `m3_mil_crime_police`
  - `m3_mil_law_enforcement`
  - `m3_mil_peace_order`
  - `m3_mil_police_overlap`
  - `m3_mil_eco`
  - `m3_mil_eco_own`
  - `m3_mil_eco_share`
  - `m3_mil_eco_dom`
  - `m3_milex_gdp`
  - `m3_milex_healthexp`
  - `m3_pers_to_pop`
  - `m3_pers_to_phy`
  - `m3_reserve_pop`
  - `m3_hwi`
  - `m3_source_year`
  - `m3_observed_year`
- annual SENTINEL event rollups now carried in `country_year` such as:
  - `sentinel_event_count_y`
  - `sentinel_high_salience_event_count_y`
  - `sentinel_coup_family_count_y`
  - `sentinel_purge_family_count_y`
  - `sentinel_domestic_military_role_count_y`
  - `sentinel_military_policing_role_count_y`
  - `sentinel_exception_rule_militarization_count_y`
- composite structural field:
  - `state_capacity_composite`

### Private Annual Latent Outputs

The first private annual latent outputs now live in:

- `data/modeling/latent_design_matrix.json`
- `data/modeling/latent_design_matrix.csv`
- `data/review/latent_design_matrix_coverage.json`
- `data/modeling/static_latent_scores_v0.json`
- `data/modeling/static_latent_scores_v0.csv`
- `data/review/static_latent_scores_v0_diagnostics.json`

The `static_latent_scores_v0` layer currently includes:

- `civilian_control_latent_v0_score`
- `civilian_control_latent_v0_z`
- `civilian_control_latent_v0_raw`
- `militarization_latent_v0_score`
- `militarization_latent_v0_z`
- `militarization_latent_v0_raw`

These are private/internal first-pass measurement outputs.

They should be treated as:

- annual construct checks
- provisional static latent scores
- not the final public-facing index layer

### Monthly Event-Derived Features Included

Representative monthly pulse fields currently include:

- `event_count`
- `high_salience_event_count`
- `medium_salience_event_count`
- `low_salience_event_count`
- `high_confidence_event_count`
- `human_reviewed_event_count`
- `human_validated_event_count`
- `distinct_event_count`
- `merged_event_count`
- `event_type_<type>_count` for major event classes
- `deed_type_<type>_count`
- `axis_vertical_count`
- `axis_horizontal_count`
- dominant monthly labels:
  - `dominant_event_type`
  - `dominant_deed_type`
  - `dominant_axis`
- monthly mix labels:
  - `salience_mix_label`
  - `confidence_mix_label`
  - `deed_mix_label`
  - `review_state_mix_label`

### Internal Aggregation Placeholders

The canonical/review event layer now also reserves internal linkage placeholders
for a future `process -> episode -> event` hierarchy:

- `episode_id`
- `process_id`
- `episode_role`
- `process_relevance`

These are private/internal scaffolding fields and do not yet carry live
grouping logic.

### Rolling Features

The panel also includes first-pass rolling features such as:

- `*_3m`
- `*_6m`
- `*_12m`
- `event_shock_flag`

It also includes summary shares such as:

- `high_salience_share`
- `high_confidence_share`
- `deed_signal_share`
- `human_review_share`

### Target Fields

The panel now includes first-pass proxy target columns for predictive modeling:

| Field | Type | Description |
|---|---|---|
| `irregular_transition_next_1m` | integer (0/1) | Proxy label for whether the next country-month contains a conservative irregular-transition signal, now including episode-aware rupture logic |
| `irregular_transition_next_3m` | integer (0/1) | Proxy label for whether any of the next three country-months contains a conservative irregular-transition signal, now including episode-aware rupture logic |
| `irregular_transition_signal_score_next_1m` | integer | Proxy transition score for the next month under the current rule, including event and episode sequence signals |
| `irregular_transition_signal_score_next_3m` | integer | Maximum proxy transition score across the next three months under the current rule, including event and episode sequence signals |
| `irregular_transition_signal_label_next_1m` | string | Categorical label for the next-month signal: `background`, `watch`, or `elevated` |
| `irregular_transition_signal_label_next_3m` | string | Categorical label for the next-three-month signal: `background`, `watch`, or `elevated` |
| `irregular_transition_target_rule` | string | Current proxy-target rule version |
| `irregular_transition_fit_score_next_1m` | integer | Stricter fit-time rupture score for the next month, excluding the broader internal rupture-watch escape hatch |
| `irregular_transition_fit_score_next_3m` | integer | Maximum stricter fit-time rupture score across the next three months |
| `irregular_transition_fit_label_next_1m` | string | Categorical fit-time next-month label: `background`, `watch`, or `elevated` |
| `irregular_transition_fit_label_next_3m` | string | Categorical fit-time next-three-month label: `background`, `watch`, or `elevated` |
| `irregular_transition_fit_target_rule` | string | Current stricter fit-time proxy-rule version |
| `irregular_transition_label_source` | string | Whether the `1m` label came from the proxy rule or from the selective adjudicated benchmark layer |
| `irregular_transition_adjudicated_note` | string/null | Internal benchmark note attached when the `1m` label is overridden by the adjudicated layer |
| `irregular_transition_gold_next_1m` | integer (0/1) / null | Stricter gold-aligned `1m` fit target derived from the gold irregular-transition subset |
| `irregular_transition_gold_label_available` | integer (0/1) | Whether a stricter gold label is available for this country-month |
| `irregular_transition_observation_window_complete_1m` | integer (0/1) | Whether the next-month observation window exists in the panel |
| `irregular_transition_observation_window_complete_3m` | integer (0/1) | Whether the next-three-month observation window exists in the panel |
| `acute_political_risk_next_1m` | integer (0/1) | Broader acute political-risk proxy for the next month, capturing high-severity deterioration beyond irregular transition |
| `acute_political_risk_next_3m` | integer (0/1) | Broader acute political-risk proxy across the next three months |
| `acute_political_risk_signal_score_next_1m` | integer | Acute political-risk score for the next month under the broader deterioration rule |
| `acute_political_risk_signal_score_next_3m` | integer | Maximum acute political-risk score across the next three months |
| `acute_political_risk_signal_label_next_1m` | string | Categorical acute-risk label for the next month: `background`, `watch`, or `elevated` |
| `acute_political_risk_signal_label_next_3m` | string | Categorical acute-risk label across the next three months: `background`, `watch`, or `elevated` |
| `acute_political_risk_target_rule` | string | Current broader acute political-risk proxy-rule version |
| `acute_political_risk_observation_window_complete_1m` | integer (0/1) | Whether the next-month observation window exists for the acute political-risk target |
| `acute_political_risk_observation_window_complete_3m` | integer (0/1) | Whether the next-three-month observation window exists for the acute political-risk target |
| `security_fragmentation_jump_next_1m` | integer (0/1) | Proxy for whether the next month contains a meaningful jump in security-fragmentation pressure |
| `security_fragmentation_jump_next_3m` | integer (0/1) | Proxy for whether the next three months contain a meaningful jump in security-fragmentation pressure |
| `security_fragmentation_jump_signal_score_next_1m` | integer | Security-fragmentation-jump signal score for the next month |
| `security_fragmentation_jump_signal_score_next_3m` | integer | Maximum security-fragmentation-jump signal score across the next three months |
| `security_fragmentation_jump_signal_label_next_1m` | string | Categorical label for the next-month security-fragmentation-jump score: `background`, `watch`, or `elevated` |
| `security_fragmentation_jump_signal_label_next_3m` | string | Categorical label for the next-three-month security-fragmentation-jump score: `background`, `watch`, or `elevated` |
| `security_fragmentation_jump_target_rule` | string | Current proxy-rule version for the construct-oriented security-fragmentation-jump target |
| `security_fragmentation_jump_observation_window_complete_1m` | integer (0/1) | Whether the next-month observation window exists for the security-fragmentation-jump target |
| `security_fragmentation_jump_observation_window_complete_3m` | integer (0/1) | Whether the next-three-month observation window exists for the security-fragmentation-jump target |

Current watch-rule version:

- `proxy_irregular_transition_v6`

Current fit-rule version:

- `proxy_irregular_transition_fit_v1`

Current logic split:

- watch layer:
  - broader internal rupture-watch logic for monitoring and analyst review
- fit layer:
  - stricter rupture logic for model validation against the gold subset
    signals
- broader acute political-risk layer:
- `proxy_acute_political_risk_v1`
- `proxy_security_fragmentation_jump_v2`
  - first checkpoint:
    - `1m` positives: `51`
    - `3m` positives: `125`

These are private/internal labels, not final gold-standard outcome labels. The
panel now supports a narrow selective adjudicated override for benchmark
reviewed `1m` cases while leaving the broader target layer on the proxy rule.

Current adjudication workflow:

- `data/review/irregular_transition_target_review.json`
  - country-by-country review of current proxy positives
- `data/review/adjudication_queue_irregular_transition.json`
  - working queue of `plausible` and `review` cases still awaiting
    country-by-country adjudication
- `data/modeling/adjudicated_irregular_transition_labels.json`
  - selective reviewed labels that override the `1m` proxy target in the panel
- optional local decisions file:
  - `data/review/adjudicated_transition_decisions.local.json`

Current acute political-risk review workflow:

- `data/review/acute_political_risk_target_review.json`
  - country-by-country review of broader acute political-risk proxy positives
- `data/review/adjudication_queue_acute_political_risk.json`
  - working queue of `plausible` and `review` acute-risk cases still awaiting
    country-by-country adjudication
- optional local decisions file:
  - `data/review/adjudicated_acute_political_risk_decisions.local.json`
- tracked template:
  - `data/review/adjudicated_acute_political_risk_decisions.template.json`
- `data/modeling/adjudicated_acute_political_risk_labels.json`
  - selective reviewed labels for the broader acute political-risk target

Current acute political-risk adjudication checkpoint:

- `acute political risk adjudicated layer v1`
- `30` reviewed `1m` rows
- adjudicated countries:
  - `Bolivia`
  - `Brazil`
  - `Chile`
  - `Colombia`
  - `El Salvador`
  - `Guatemala`
  - `Haiti`
  - `Honduras`
  - `Peru`
  - `Venezuela`
- current acute-risk adjudication queue:
  - empty

Current acute political-risk gold-subset artifact:

- `data/modeling/gold_acute_political_risk_labels.json`

Current acute political-risk gold-subset status:

- `22` gold `1m` labels
- gold countries:
  - `Bolivia`
  - `Chile`
  - `Colombia`
  - `El Salvador`
  - `Haiti`
  - `Honduras`
  - `Peru`
  - `Venezuela`

Current acute political-risk gold-validation artifact:

- `data/review/gold_acute_political_risk_validation.json`

Current acute political-risk first validation checkpoint:

- gold rows: `22`
- true positives against gold: `22`
- false negatives against gold: `0`
- false positives against gold: `26`
- gold recall: `100.0%`
- proxy precision against gold: `45.833%`

Current acute political-risk benchmark-tier artifact:

- `data/modeling/acute_political_risk_benchmark_tiers.json`

Current acute political-risk tier-separation artifact:

- `data/review/acute_political_risk_tier_separation.json`

Current acute political-risk benchmark-tier status:

- gold positives: `22`
- hard negatives: `18`
- easy negatives: `22`

Current acute political-risk tier-separation takeaway:

- `transition_contestation_load_score`
  - gold mean: `1.516`
  - hard-negative mean: `4.829`
- `transition_rupture_precursor_score`
  - gold mean: `0.823`
  - hard-negative mean: `2.871`
- current implication:
- the acute-risk layer still needs better protection against broad contestation overfire
- the panel now also carries protest-split interpretive fields:
  - `protest_acute_signal_score`
  - `protest_background_load_score`
  - `protest_escalation_specificity_score`
- these fields separate:
  - protest as acute deterioration signal
  - protest as broad contestation background
- they currently support interpretation and review rather than direct acute-risk
  scoring, because the first direct scoring pass increased false positives
- the newer `protest_escalation_specificity_score` is also currently benchmark-only;
  its first audit suggests it is sparse and interpretable but still not cleanly
  separative enough to drive scoring
  - latest refinement preserved full gold recall while trimming overfire modestly

Current acute political-risk fit-dataset artifact:

- `data/modeling/acute_political_risk_fit_dataset.json`

Current acute political-risk baseline-validation artifact:

- `data/review/acute_political_risk_baseline_validation.json`

Current acute political-risk model-validation artifact:

- `data/review/acute_political_risk_model_validation.json`

Current acute political-risk fit-ready checkpoint:

- rows: `61`
- gold positives: `22`
- hard negatives: `17`
- easy negatives: `22`
- current best threshold:
  - `4`
- current baseline result:
  - precision: `100.0%`
  - recall: `100.0%`
  - specificity: `100.0%`

Current acute political-risk first model-comparison result:

- threshold baseline:
  - precision: `100.0%`
  - recall: `100.0%`
  - specificity: `100.0%`
- leave-one-out logistic:
  - precision: `84.615%`
  - recall: `100.0%`
  - specificity: `89.744%`
- hard-negative specificity under logistic:
  - `76.471%`

Current acute political-risk gold rule:

- always include `strong`
- include `reviewed` only when:
  - `proxy_score_1m >= 4`
  - and the adjudication note reflects a clearer:
    - `high-severity`
    - `shock`
    - `fragmenting conflict-linked`
    - `coup-coded`
    - or `clear broader acute deterioration`

Current checkpoint:

- `34` adjudicated `1m` rows
- adjudicated countries:
  - `Bolivia`
  - `Brazil`
  - `Chile`
  - `Colombia`
  - `El Salvador`
  - `Haiti`
  - `Honduras`
  - `Mexico`
  - `Venezuela`
- current adjudication queue status:
  - empty

This should now be treated as the first internal adjudicated layer rather than
expanded casually. The next refinement should be to derive a stricter
gold-label subset from this reviewed base.

Current gold-subset artifact:

- `data/modeling/gold_irregular_transition_labels.json`

Current gold-subset status:

- `25` gold `1m` labels
- gold countries:
  - `Bolivia`
  - `Brazil`
  - `Chile`
  - `Colombia`
  - `El Salvador`
  - `Haiti`
  - `Mexico`
  - `Venezuela`

Current gold rule:

- always include `strong`
- include `reviewed` only when:
  - `proxy_score_1m >= 4`
  - and the adjudication note reflects a clearer:
    - `high-severity`
    - `rupture`
    - `assassination`
    - or `coup-coded` case
- exclude `reviewed_watch`

Current gold-validation artifact:

- `data/review/gold_irregular_transition_validation.json`

Current first validation checkpoint:

- gold rows: `25`
- true positives against gold: `22`
- false negatives against gold: `3`
- false positives against gold: `6`
- fit-path gold recall: `88.0%`
- fit-path precision against gold: `75.0%`

Current fit-dataset artifact:

- `data/modeling/irregular_transition_fit_dataset.json`

Current fit-dataset checkpoint:

- rows: `64`
- gold positives: `25`
- reviewed-watch negatives: `9`
- weak-review negatives: `2`
- local reviewed negatives: `28`

Current baseline-validation artifact:

- `data/review/irregular_transition_baseline_validation.json`

Current baseline checkpoint on the reviewed fit-ready sample:

- sample rows: `64`
- positives: `25`
- reviewed negatives: `39`
- local reviewed negatives: `28`
- operational `v1` label precision: `73.529%`
- broader watch path remains in:
  - `irregular_transition_signal_score_next_1m`
  - `irregular_transition_signal_label_next_1m`
- stricter fit path now lives in:
  - `irregular_transition_fit_score_next_1m`
  - `irregular_transition_fit_label_next_1m`
- recommended fit threshold on `irregular_transition_fit_score_next_1m`:
  - `2`

Current fit-comparison artifact:

- `data/review/irregular_transition_model_validation.json`

Current first fit-comparison result:

- threshold baseline:
  - precision: `100%`
  - recall: `88.0%`
- leave-one-out logistic model:
  - precision: `46.875%`
  - recall: `60.0%`

Current conclusion:

- the first fitted model does not yet beat the threshold baseline
- the stricter fit-path threshold remains the operative pre-training benchmark
- the broader watch-path should remain available for analyst-facing monitoring
- the latest fit-only refinements improved stricter-threshold gold recall to
  `88.0%` while preserving `100%` hard-negative specificity
- the remaining missed gold cases are now concentrated in El Salvador
- the expanded historical-memory feature pass improved recall, but not enough
  to replace the threshold rule

Current fit-sample audit artifact:

- `data/review/irregular_transition_fit_sample_audit.json`

Current fit-sample audit takeaway:

- reviewed negatives are broader than before, but the sample is still small
- some difficult cases now intentionally stay in the negative layer as hard
  benchmark months
- the threshold baseline remains the right benchmark until the reviewed sample
  deepens further

Current reviewed-negative expansion artifacts:

- `data/review/irregular_transition_negative_queue.json`
  - private queue of lower-intensity and background negative candidates for
    irregular-transition fit-sample review
- `data/review/irregular_transition_hard_negative_queue.json`
  - private queue of hard benchmark negatives that still look transition-like
    because of episode or historical-memory signals
- optional local reviewed-negative file:
  - `data/review/reviewed_negative_decisions.local.json`
- tracked template:
  - `data/review/reviewed_negative_decisions.template.json`

Current reviewed-negative queue checkpoint:

- queue rows: `75`
- countries with reviewed negatives already represented: `25`
- rows prioritized to expand country coverage: `0`
- rows deepening existing negative countries: `75`
- hard-negative benchmark queue rows: `0`
  - the latest `8` hard negatives were already promoted into the local reviewed
    negative layer

Current validation-sample extension rule:

- baseline and model-validation runners now automatically include local
  reviewed negatives when:
  - `target_name = irregular_transition_next_1m`
  - `label = 0`

Current expanded fit-sample checkpoint:

- validation sample rows: `64`
- gold positives: `25`
- total reviewed negatives: `39`
- local reviewed negatives currently included: `28`
- the threshold baseline remains the operative benchmark

New tiered benchmark artifact:

- `data/modeling/irregular_transition_benchmark_tiers.json`

Purpose:

- consolidate the benchmark reference layer into:
  - `gold_positive`
  - `hard_negative`
  - `easy_negative`

Current tier counts:

- gold positives: `25`
- hard negatives: `10`
- easy negatives: `18`

Current tiered validation takeaway:

- under the current `proxy_irregular_transition_v6` rule:
  - `threshold 2` is the best reviewed-sample F1 cut
  - `threshold 4` remains a stricter high-specificity cut
- the fitted logistic still fails hardest on `hard_negative` cases
  - hard-negative specificity: `30.0%`
- the tier-separation audit suggests the strongest current contrasts are:
  - higher `transition_contestation_load_score` in `hard_negative`
  - more negative `transition_specificity_gap` in `hard_negative`
  - `transition_rupture_precursor_score` alone is not yet sufficient
- the `v6` rupture-sequence adjustment restored benchmark-positive rupture-watch
  cases like Haiti `2021-06-01` and Mexico `2020-06-01`, but it also reduced
  recall at the stricter `threshold 4` cut

New tier-separation audit artifact:

- `data/review/irregular_transition_tier_separation.json`

New acute protest-review artifact:

- `data/review/acute_political_risk_protest_review.json`

Supporting interpretation note:

- `docs/private-acute-protest-interpretation-note.md`

Acute benchmark-refinement artifact:

- `data/review/acute_political_risk_benchmark_refinement_queue.json`

Local refinement decisions:

- `data/review/acute_political_risk_benchmark_refinement_decisions.local.json`

Current acute-risk refinement checkpoint:

- active refinement queue:
  - `0`
- the acute-risk benchmark refinement layer is now frozen as `v1`

Post-freeze acute-risk validation checkpoint:

- fit dataset rows:
  - `61`
- best baseline threshold:
  - `4`
- baseline result:
  - precision `100.0%`
  - recall `100.0%`
  - specificity `100.0%`
- first fitted logistic still underperforms that threshold benchmark

Purpose:

- compare `gold_positive` vs `hard_negative`
- identify which features truly separate rupture cases from contestation-heavy
  near misses

### External And Economic Feature Families

The panel now carries live private/internal external and economic signal families:

- external pressure
- economic fragility
- economic policy shocks

Current panel readiness:

- external and economic fields are `derived_then_seed_override`
- the panel now also includes presence flags:
  - `external_pressure_signal_present`
  - `economic_fragility_signal_present`
  - `policy_shock_signal_present`

These fields are now supplied by:

- `data/modeling/external_economic_country_month.json`

and can still be overridden through tracked benchmark seeds or optional local
manual month rows.

Tracked contract:

- `config/modeling/panel_feature_contract.json`

Tracked benchmark seed path:

- `data/modeling/benchmark_country_month_signals.json`

Local private override path:

- `data/modeling/manual_country_month_signals.local.json`

Tracked template:

- `data/modeling/manual_country_month_signals.template.json`

These are intended as modeling inputs, not public-facing metrics.

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
| `data/raw/wb_population_total.json` | World Bank population raw | 2026-04-02 | Manual (`fetch_worldbank.py`) |
| `data/raw/wb_gdp_constant_2015_usd.json` | World Bank GDP constant raw | 2026-04-02 | Manual |
| `data/raw/wb_gdp_per_capita_constant_2015_usd.json` | World Bank GDP/capita raw | 2026-04-02 | Manual |
| `data/raw/wb_inflation_consumer_prices_pct.json` | World Bank inflation raw | 2026-04-02 | Manual |
| `data/raw/wb_real_interest_rate.json` | World Bank real interest raw | 2026-04-02 | Manual |
| `data/raw/wb_official_exchange_rate.json` | World Bank official exchange-rate raw | 2026-04-02 | Manual |
| `data/raw/wb_fdi_net_inflows_pct_gdp.json` | World Bank FDI inflows raw | 2026-04-02 | Manual |
| `data/raw/wb_debt_service_pct_exports.json` | World Bank debt-service raw | 2026-04-02 | Manual |
| `data/raw/wb_current_account_pct_gdp.json` | World Bank current-account raw | 2026-04-02 | Manual |
| `data/raw/wb_reserves_months_imports.json` | World Bank reserves/imports raw | 2026-04-02 | Manual |
| `data/raw/wb_resource_rents_pct_gdp.json` | World Bank resource-rents raw | 2026-04-02 | Manual |
| `data/raw/wb_trade_openness_pct_gdp.json` | World Bank trade openness raw | 2026-04-02 | Manual |
| `data/raw/wb_oda_received_pct_gni.json` | World Bank ODA received raw | 2026-04-02 | Manual |
| `data/raw/wb_wgi_rule_of_law.json` | World Bank Rule of Law raw | 2026-03-27 | Manual |
| `data/raw/wb_wgi_govt_effectiveness.json` | World Bank Govt Effectiveness raw | 2026-03-27 | Manual |
| `data/raw/wb_wgi_control_of_corruption.json` | World Bank Corruption Control raw | 2026-03-27 | Manual |
| `data/raw/wb_wgi_political_stability.json` | World Bank Political Stability raw | 2026-03-27 | Manual |
| `data/raw/wb_military_expenditure_pct_gdp.json` | World Bank mil. exp. % GDP raw | 2026-03-27 | Manual |
| `data/raw/wb_military_expenditure_current_usd.json` | World Bank mil. exp. USD raw | 2026-03-27 | Manual |
| `data/raw/V-Dem-CY-Core-v16.csv` | V-Dem raw *(not yet downloaded)* | — | Manual download |
| `data/cleaned/worldbank.json` | World Bank — all indicators merged | 2026-03-27 | Manual |
| `data/cleaned/worldbank.csv` | World Bank — same, CSV format | 2026-03-27 | Manual |
| `data/raw/us_foreignaid_greenbook.xlsx` | USAID Greenbook raw assistance workbook | 2026-04-02 | Manual source |
| `data/raw/EUSANCT_CLEAN.dta` | Raw EUSANCT sanctions panel | 2026-04-02 | Manual source |
| `data/raw/EUSANCT_Dataset_Case-level.xls` | Raw EUSANCT case-level workbook | 2026-04-02 | Manual source |
| `data/raw/FinancialCrises_A new comprehensive database of financial crises Identification, frequency, and duration.xlsx` | Raw financial crises workbook | 2026-04-02 | Manual source |
| `data/cleaned/greenbook.json` | Cleaned USAID Greenbook assistance series by country-year | 2026-04-02 | `clean_greenbook.py` |
| `data/cleaned/greenbook.csv` | Cleaned USAID Greenbook assistance series, CSV mirror | 2026-04-02 | `clean_greenbook.py` |
| `data/cleaned/eusanct.json` | Cleaned sanctions country-year panel derived from EUSANCT | 2026-04-02 | `clean_eusanct.py` |
| `data/cleaned/eusanct.csv` | Cleaned sanctions country-year panel, CSV mirror | 2026-04-02 | `clean_eusanct.py` |
| `data/cleaned/financial_crises.json` | Cleaned financial crises country-year panel | 2026-04-02 | `clean_financial_crises.py` |
| `data/cleaned/financial_crises.csv` | Cleaned financial crises country-year panel, CSV mirror | 2026-04-02 | `clean_financial_crises.py` |
| `data/raw/wb_military_personnel_total.json` | World Bank mil. personnel raw | 2026-04-02 | Manual |
| `data/cleaned/vdem.json` | V-Dem — selected indicators | 2026-04-02 | `refresh_vdem.py` |
| `data/cleaned/country_year.json` | Structural country-year merged layer | 2026-04-02 | `build_country_year.py` |
| `data/modeling/country_month_panel.json` | Private country-month modeling panel | 2026-04-02 | `build_country_month_panel.py` |
| `data/modeling/country_month_panel.csv` | Private country-month modeling panel, CSV mirror | 2026-04-02 | `build_country_month_panel.py` |
| `data/modeling/episodes.json` | Private/internal episode artifact built from reviewed events | 2026-04-02 | `build_episodes.py` |
| `data/modeling/adjudicated_irregular_transition_labels.json` | Private benchmark-reviewed adjudicated layer for selective `1m` irregular-transition labels | 2026-04-02 | `build_adjudicated_transition_labels.py` |
| `data/modeling/gold_irregular_transition_labels.json` | Private stricter gold subset derived from the adjudicated irregular-transition layer | 2026-04-02 | `build_gold_transition_labels.py` |
| `data/modeling/gold_acute_political_risk_labels.json` | Private stricter gold subset derived from the adjudicated acute political-risk layer | 2026-04-02 | `build_gold_acute_political_risk_labels.py` |
| `data/modeling/acute_political_risk_benchmark_tiers.json` | Private consolidated benchmark tier set for acute political-risk modeling, grouping gold positives, hard negatives, and easy negatives | 2026-04-02 | `build_acute_political_risk_benchmark_tiers.py` |
| `data/modeling/acute_political_risk_fit_dataset.json` | Private reviewed fit-ready sample for acute political-risk modeling built from gold positives and benchmark negatives | 2026-04-02 | `build_acute_political_risk_fit_dataset.py` |
| `data/modeling/external_economic_country_month.json` | Private monthly external-pressure and economic-signal layer feeding the country-month panel | 2026-04-02 | `build_external_economic_signals.py` |
| `data/review/external_economic_signal_review.json` | Private six-country benchmark review for the external/economic monthly signal layer | 2026-04-02 | `review_external_economic_signals.py` |
| `data/published/country_monitors.json` | Published country monitor layer with monitor families, risk constructs, and predictive summaries | 2026-04-02 | `build_country_monitors.py` |
| `config/modeling/process_episode_event_schema.json` | Private schema scaffold for future process/episode/event aggregation logic | 2026-04-02 | Internal schema scaffold |
| `config/modeling/internal_signal_panel_spec.json` | Private spec for an internal country signal panel used for episode/process detection | 2026-04-02 | Internal panel scaffold |
| `data/modeling/benchmark_country_month_signals.json` | Tracked internal benchmark month-level external/economic signal seeds | 2026-04-02 | Internal benchmark seed |
| `data/modeling/internal_signal_panel_venezuela.json` | Private Venezuela pilot signal-panel artifact | 2026-04-02 | `build_internal_signal_panel.py` |
| `apps/internal-tools/signal-panel.html` | Private standalone viewer for one-country internal signal-panel artifacts | 2026-04-02 | Internal HTML viewer |
| `data/modeling/country_month_target_audit.json` | Private audit of proxy target balance and distribution | 2026-04-02 | `audit_country_month_targets.py` |
| `data/review/irregular_transition_target_review.json` | Private country-by-country review of proxy irregular-transition positives | 2026-04-02 | `review_irregular_transition_targets.py` |
| `data/review/adjudication_queue_irregular_transition.json` | Private working queue of reviewed irregular-transition cases awaiting adjudication | 2026-04-02 | `build_adjudication_queue.py` |
| `data/review/acute_political_risk_target_review.json` | Private country-by-country review of proxy acute political-risk positives | 2026-04-02 | `review_acute_political_risk_targets.py` |
| `data/review/adjudication_queue_acute_political_risk.json` | Private working queue of reviewed acute political-risk cases awaiting adjudication | 2026-04-02 | `build_acute_political_risk_adjudication_queue.py` |
| `data/modeling/adjudicated_acute_political_risk_labels.json` | Private benchmark-reviewed adjudicated layer for selective `1m` acute political-risk labels | 2026-04-02 | `build_adjudicated_acute_political_risk_labels.py` |
| `data/review/security_fragmentation_jump_target_review.json` | Private country-by-country review of proxy security-fragmentation-jump positives for the first construct-oriented target pass | 2026-04-03 | `review_security_fragmentation_jump_targets.py` |
| `data/review/adjudication_queue_security_fragmentation_jump.json` | Private working queue of reviewed security-fragmentation-jump cases awaiting adjudication | 2026-04-03 | `build_security_fragmentation_jump_adjudication_queue.py` |
| `data/modeling/adjudicated_security_fragmentation_jump_labels.json` | Private first adjudicated construct-oriented label layer for selective `3m` security-fragmentation-jump cases | 2026-04-03 | `build_adjudicated_security_fragmentation_jump_labels.py` |
| `data/review/adjudicated_security_fragmentation_jump_decisions.template.json` | Private template for local adjudication decisions that extend the security-fragmentation-jump label layer | 2026-04-03 | Manual template |
| `data/modeling/gold_security_fragmentation_jump_labels.json` | Private stricter gold subset derived from the adjudicated security-fragmentation-jump layer | 2026-04-03 | `build_gold_security_fragmentation_jump_labels.py` |
| `data/review/gold_security_fragmentation_jump_validation.json` | Private first validation pass comparing the security-fragmentation-jump proxy against the stricter gold subset | 2026-04-03 | `validate_gold_security_fragmentation_jump_targets.py` |
| `data/modeling/security_fragmentation_jump_benchmark_tiers.json` | Private consolidated benchmark tier set for construct-oriented security-fragmentation-jump modeling, grouping gold positives, hard negatives, and easy negatives | 2026-04-03 | `build_security_fragmentation_jump_benchmark_tiers.py` |
| `data/review/security_fragmentation_jump_tier_separation.json` | Private audit comparing security-fragmentation-jump gold positives against hard negatives to identify the strongest separation features | 2026-04-03 | `audit_security_fragmentation_jump_tier_separation.py` |
| `data/review/gold_irregular_transition_validation.json` | Private first validation pass comparing the current target layer against the gold irregular-transition subset | 2026-04-02 | `validate_gold_transition_targets.py` |
| `data/review/gold_acute_political_risk_validation.json` | Private first validation pass comparing the broader acute political-risk target layer against the acute-risk gold subset | 2026-04-02 | `validate_gold_acute_political_risk_targets.py` |
| `data/review/acute_political_risk_tier_separation.json` | Private audit comparing acute political-risk gold positives against hard negatives to identify the strongest separation features | 2026-04-02 | `audit_acute_political_risk_tier_separation.py` |
| `data/review/acute_political_risk_baseline_validation.json` | Private baseline validation report for the current acute political-risk signal score against the reviewed acute-risk fit-ready sample | 2026-04-02 | `validate_acute_political_risk_baseline.py` |
| `data/review/acute_political_risk_model_validation.json` | Private first fit-comparison report contrasting the acute-risk threshold baseline against a leave-one-out logistic model | 2026-04-02 | `validate_acute_political_risk_models.py` |
| `data/review/irregular_transition_baseline_validation.json` | Private baseline validation report for the current irregular-transition signal score against the reviewed fit-ready sample | 2026-04-02 | `validate_irregular_transition_baseline.py` |
| `data/review/irregular_transition_model_validation.json` | Private first fit-comparison report contrasting the threshold baseline, operational label, and leave-one-out logistic model | 2026-04-02 | `validate_irregular_transition_models.py` |
| `data/review/irregular_transition_fit_sample_audit.json` | Private audit of reviewed fit-sample composition and crude feature separation for irregular-transition modeling | 2026-04-02 | `audit_irregular_transition_fit_sample.py` |
| `data/review/training_history_coverage_audit.json` | Private audit of whether the merged structural layer already contains usable pre-1990 history for training extensions | 2026-04-02 | `audit_training_history_coverage.py` |
| `data/review/upstream_training_source_audit.json` | Private audit of whether the current 1990 floor is caused by source coverage or by current ingest/build limits | 2026-04-02 | `audit_upstream_training_sources.py` |
| `data/review/adjudicated_transition_decisions.template.json` | Private template for local adjudication decisions that extend the irregular-transition label layer | 2026-04-02 | Manual template |
| `data/review/adjudicated_acute_political_risk_decisions.template.json` | Private template for local adjudication decisions that extend the acute political-risk label layer | 2026-04-02 | Manual template |
| `data/review/irregular_transition_negative_queue.json` | Private queue of candidate reviewed negatives for broadening the irregular-transition fit sample | 2026-04-02 | `build_irregular_transition_negative_queue.py` |
| `data/review/irregular_transition_hard_negative_queue.json` | Private hard-negative benchmark queue for transition-like reviewed negatives that should challenge the fit sample | 2026-04-02 | `build_irregular_transition_hard_negative_queue.py` |
| `data/modeling/irregular_transition_benchmark_tiers.json` | Private consolidated benchmark tier set for irregular-transition modeling, grouping gold positives, hard negatives, and easy negatives | 2026-04-02 | `build_irregular_transition_benchmark_tiers.py` |
| `data/review/reviewed_negative_decisions.template.json` | Private template for local reviewed negatives that extend the irregular-transition fit-ready sample | 2026-04-02 | Manual template |
| `data/modeling/manual_country_month_signals.template.json` | Private template for month-level external/economic seeds | 2026-04-02 | Manual template |
| `data/CODEBOOK.md` | This file | 2026-04-02 | Manual |
