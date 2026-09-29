# SENTINEL Shared Country Dossier Contract — Design Spec
**Date:** 2026-06-06  
**Status:** Draft for written review  
**Scope:** Shared country dossier contract, public/private boundary, published artifact design, and phased rollout for the public dashboard and analyst console

---

## Overview

SENTINEL now has three distinct but related layers:

- a public dashboard
- a credentialed analyst console
- a private modeling stack

These layers already overlap in practice through `country_monitors`, structural data, and Supabase snapshots, but they do not yet share one explicit country-level contract. The result is growing risk of schema drift, duplicated logic, and different country-level stories across the public and private surfaces.

This spec defines a **shared country dossier contract** that becomes the single country-level source of truth for both surfaces. The public dashboard should consume a public-safe dossier artifact. The analyst console should consume the same public dossier as its base layer, then enrich it with private monthly signals and predictive/modeling fields after analyst login.

The guiding decision for this spec is:

- **Conservative public / rich private**

Public surfaces should show calibrated constructs, structural trend context, and publication-safe summary text. Private surfaces should show monthly signals, predictive targets, drivers, validation state, and analyst-only diagnostics.

---

## Goals

1. Create one canonical country-level contract shared across the public dashboard and analyst console.
2. Keep the public/private separation strict while preserving cross-surface coherence.
3. Make country profile data easier to extend with structural series, monitor history, and predictive layers.
4. Normalize country identity so published artifacts contain exactly one canonical row per monitored country.
5. Support a phased rollout that improves public country profiles first without blocking later console intelligence features.

---

## Non-Goals

- Replacing the current event pipeline or canonical event schema
- Publishing internal monthly model outputs directly to the public dashboard
- Rebuilding the analyst console around a new backend architecture
- Turning Supabase into the immediate system of record for all country data
- Finalizing model training, fit, or forecasting methodology beyond current proxy and validation workflows

---

## Product Direction

### Chosen sequencing

Implementation should prioritize:

1. **Public country profiles first**
2. **Shared plumbing second**
3. **Console intelligence third**

This means the first cycle should improve what public users can understand from country profiles while doing the contract and normalization work needed to keep the analyst console aligned.

### Chosen contract model

`Published dossier artifact`

The preferred architecture is a single shared dossier model with two concrete outputs:

- a public-safe published dossier artifact
- a richer private dossier or enrichment layer for logged-in analyst use

This is preferred over maintaining separate surface-specific country payloads because it reduces schema drift and matches the public/private split already described in `docs/architecture.md`.

---

## Core Decision

### Shared country dossier first

The public dashboard and analyst console should be linked through a shared country dossier contract rather than through duplicated UI-specific data shapes.

The dossier must be:

- country-keyed
- canonical
- publish-aware
- extensible for both structural and predictive layers

The contract should explicitly distinguish:

- public-safe identity and context
- public-safe structural history
- public-safe construct summaries
- private monthly signals
- private predictive/modeling outputs
- private governance and validation metadata

---

## Information Architecture

The country dossier should sit between the existing cleaned/modeling layers and the two presentation surfaces.

### Upstream layers

1. **Structural annual layer**
   - `data/cleaned/country_year.json`
   - joined V-Dem, World Bank, M3, and annual SENTINEL rollups

2. **Public monitor layer**
   - current layered monitor and construct builder
   - public narrative, watchpoints, calibrated construct scores

3. **Private modeling layer**
   - `data/modeling/country_month_panel.json`
   - internal signal panels
   - proxy targets
   - validation artifacts

### Downstream surfaces

1. **Public dashboard**
   - reads only published dossiers and published events

2. **Analyst console**
   - reads the same published dossier as its base layer
   - enriches with private data after login via local JSON or Supabase snapshots

---

## Shared Contract

The shared contract should use one canonical row per monitored country.

### Required top-level fields

- `country`
- `iso2`
- `iso3`
- `subregion`
- `generated_at`
- `public_freshness`
- `public_summary`
- `public_structural_cards`
- `public_construct_series`
- `public_context`

### Private extension fields

- `private_monthly_signals`
- `private_model_outputs`
- `private_drivers`
- `private_governance`

The public artifact should exclude all private extension fields.

---

## Canonical Country Identity

The dossier contract depends on strict country normalization.

### Canonical rule

There should be exactly one dossier row for each monitored country and no pseudo-country or multi-country rows.

### Current issue

`scripts/analysis/build_country_monitors.py` currently creates country rows from the union of:

- structural country keys
- raw event `country` strings

This currently allows rows such as:

- `Brazil|Colombia|Mexico|Panama`
- `Colombia or regional`
- `Colombia|Venezuela`

These are invalid for dossier generation and must not appear in published country artifacts.

### Required behavior

- country dossier generation must use only canonical country names from the monitored country taxonomy
- multi-country or regional event strings should be normalized earlier or excluded from dossier row generation
- dashboard and console should resolve country detail views using the same canonical key

### Validation requirement

Published dossier output must contain exactly `25` monitored country rows.

---

## Public Fields

The public dossier should contain only information appropriate for GitHub Pages publication and public display.

### `public_freshness`

Purpose:
- show the temporal character of the country reading

Suggested fields:

- `structural_as_of_year`
- `events_as_of_date`
- `monitor_generated_at`
- `series_coverage_note`

### `public_summary`

Purpose:
- provide the compact risk posture for both country profiles and map/tooltips

Suggested fields:

- `overall_risk_score`
- `overall_risk_level`
- `leading_construct`
- `leading_label`
- `leading_trend`
- `summary_text`
- `watchpoints`

### `public_structural_cards`

Purpose:
- support a compact profile layout where a current value expands into historical context

Each card should include:

- `code`
- `label`
- `current_value`
- `display_value`
- `unit`
- `as_of_year`
- `trend_series`

Each `trend_series` should be annual or otherwise slow-moving and should preserve original observation cadence rather than implying false monthly movement.

### `public_construct_series`

Purpose:
- expose publication-safe higher-order series or refresh-based measures

Suggested constructs:

- `regime_vulnerability`
- `militarization`
- `security_fragmentation`

If a construct is not yet meaningfully historical, the series can initially be a limited refresh history or omitted until enough observations exist.

### `public_context`

Purpose:
- preserve the qualitative country profile context already present in the dashboard

Suggested fields:

- `capital`
- `regime`
- `cmr_status`
- `cmr_class`
- `note`
- `key_positions`
- `next_election`
- `country_watch`
- `special_profile_id`

---

## Private Fields

Private fields should be available only in analyst-facing contexts.

### `private_monthly_signals`

Purpose:
- support console intelligence and model-aware review

Suggested fields:

- monthly signal series from `country_month_panel`
- event-shock markers
- signal labels
- rolling windows
- internal country signal panel slices

### `private_model_outputs`

Purpose:
- carry internal predictive targets and scoring layers

Suggested fields:

- `irregular_transition`
- `acute_political_risk`
- `security_fragmentation_jump`
- score values
- label values
- horizon metadata
- model or rule version
- validation state

### `private_drivers`

Purpose:
- explain movement in the internal model layer

Suggested fields:

- top structural drivers
- top pulse drivers
- top contributing recent events
- driver weights or weighted contributions

### `private_governance`

Purpose:
- preserve internal integrity and analyst trust

Suggested fields:

- calibration status
- coverage caveats
- benchmark status
- proxy/adjudicated/gold status
- analyst-only notes
- source confidence and missingness warnings

---

## Public Structural Cards

The first implementation cycle should curate a small number of structural cards rather than exposing every available annual indicator.

### Recommended first public set

- `polyarchy`
- `mil_constrain`
- `mil_exec`
- `wgi_rule_of_law`
- `mil_exp_pct_gdp`
- one macro stress indicator such as `inflation_consumer_prices_pct` or `debt_service_pct_exports`

### Rationale

This first set balances:

- civil-military relations
- governance quality
- coercive institutional autonomy
- military resource posture
- macro stress context

These are interpretable for public users and already align with the existing country profile logic.

### Interaction behavior

Each card should show:

- current displayed value
- year of latest observation
- unit label

On hover or tap, the card should reveal or render a trend line over time.

The design must work on both desktop and mobile, with hover behavior degraded gracefully to click/tap behavior on touch devices.

---

## Public Predictive Layer

The public predictive layer should remain cautious and editorially legible.

### What public should show

- calibrated construct scores
- overall risk summary
- leading construct
- direction of trend
- short publication-safe narrative
- up to two watchpoints

### What public should not show

- raw monthly target scores
- proxy target labels
- internal observation-window logic
- adjudication queues
- fit diagnostics
- model coefficients
- analyst notes

### Public tone rule

Public risk language should describe posture and direction, not overclaim forecast certainty.

Examples of acceptable public framing:

- “guarded posture”
- “elevated regime vulnerability”
- “rising militarization pressure”

Examples to avoid in public:

- exact short-horizon internal target probabilities
- strong coup-style prediction framing
- unresolved internal validation terminology

---

## Private Predictive Layer

The analyst console should expose the private monthly and predictive layers more directly once the shared base contract is in place.

### Console should show

- monthly signal lines
- event markers
- recent movement by construct
- target watch scores
- validation badges
- model or rule version
- internal driver decomposition

### Console should preserve the public base

The analyst console should still begin from the same country posture seen publicly:

- overall risk
- leading construct
- leading trend
- public summary text

Then it should expand into:

- why the score moved
- which events contributed most
- which internal signals are rising
- whether the target is proxy-only, adjudicated, or gold-backed

---

## Data Flow

The desired flow is:

1. build structural annual country layer
2. build public monitor and construct layer
3. build private monthly and predictive layers
4. assemble full dossier object
5. publish public-safe dossier artifact
6. expose private enrichments through console data loading and snapshots

### Required artifact split

- `data/published/country_dossiers.json`
  - public-safe only

- private dossier or enrichment artifacts
  - remain in `data/modeling/`, `data/review/`, or Supabase snapshots

The public dashboard should ultimately read published dossier artifacts rather than directly loading cleaned structural files from `data/cleaned/`.

---

## Surface Responsibilities

### Public dashboard

Responsibilities:

- display country-level posture
- show structural context over time
- connect event reading to country context
- stay publication-safe and light enough for a static site

Must read:

- published events
- published country dossiers

Should not read:

- private monthly signals
- internal validation artifacts
- private review state

### Analyst console

Responsibilities:

- preserve the same country story seen publicly
- add private diagnostics after login
- support analyst interpretation and review context

Must read:

- public dossier base layer
- private enrichments from local JSON or Supabase snapshots

---

## Supabase And Snapshot Implications

The shared dossier contract should also shape snapshot boundaries.

### Required direction

- continue pushing `country_monitors` while the dossier is introduced
- add a dedicated dossier snapshot family when implementation begins
- make the console load the dossier base object and then enrich it after login

### Reason

This prevents the console from assembling country state through separate ad hoc fetches and keeps the public/private relationship explicit.

---

## Implementation Phasing

### Phase 1 — Public country profiles

Primary goal:
- improve public country profiles first

Includes:

- define shared dossier schema
- create published dossier artifact
- normalize country keys to canonical `25`
- move public profile structural series into the published layer
- add structural cards with current value plus trend interaction
- preserve current country context and summary content

### Phase 2 — Shared plumbing

Primary goal:
- ensure both surfaces are linked through the same contract

Includes:

- align publisher, dashboard, console loader, and Supabase snapshots
- stop reading raw cleaned structural layers directly from public UI
- validate public/private field separation

### Phase 3 — Console intelligence

Primary goal:
- add deeper private country intelligence views

Includes:

- private monthly signal panels
- target diagnostics
- validation badges
- model-aware driver views

---

## Validation And Testing

The shared dossier rollout should include explicit validation checks.

### Contract checks

- published dossier contains exactly `25` rows
- each row has one canonical country key
- no pseudo-country or regional rows appear
- required public fields exist for every country

### Boundary checks

- no private fields appear in `data/published/`
- dashboard cannot access internal monthly fields
- console can resolve the same country key as the dashboard

### Data integrity checks

- structural card `as_of_year` values are correct
- series cadence remains annual where annual is the true cadence
- no monthly interpolation is implied for annual democracy or governance measures

### UX checks

- structural cards work on desktop and mobile
- public summary remains understandable without internal terminology
- console expansion preserves public-facing baseline before deeper internal detail

---

## Risks

### Country normalization risk

If country identity is not normalized first, the dossier layer will inherit the same pseudo-country leakage currently visible in `country_monitors`.

### Drift risk

If the dashboard and console adopt separate dossier shapes, the shared-contract goal will fail and maintenance cost will rise quickly.

### Overpublication risk

If internal monthly or proxy-target fields leak into the public dossier, the public/private boundary will erode and the published product may overstate predictive certainty.

### Historical-series risk

If annual structural measures are rendered like dense high-frequency series, users may infer false precision or false recency.

---

## Recommended Outcome

SENTINEL should adopt a shared country dossier architecture in which:

- the public dashboard reads a public-safe country dossier artifact
- the analyst console reads the same dossier as its base layer
- private monthly and predictive layers are attached only after analyst login

This approach gives SENTINEL one country story, two surface-specific presentations, and a clean place to grow public structural context and private predictive intelligence without mixing them.

