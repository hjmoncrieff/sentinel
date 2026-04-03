# SENTINEL Private Signal Panel Note

This note is private/internal. It defines a pilot internal signal panel for
episode and process detection. It is not intended for the public dashboard.

It should be read alongside:

- [private-process-episode-event-note.md](/Users/hjmoncrieff/Library/CloudStorage/Dropbox/SENTINEL/docs/private-process-episode-event-note.md)
- [private-risk-architecture-note.md](/Users/hjmoncrieff/Library/CloudStorage/Dropbox/SENTINEL/docs/private-risk-architecture-note.md)
- [private-country-month-model-note.md](/Users/hjmoncrieff/Library/CloudStorage/Dropbox/SENTINEL/docs/private-country-month-model-note.md)

## Why Build An Internal Signal Panel

SENTINEL now has:

- event-level coding
- country constructs
- a private country-month modeling panel
- a proposed `process -> episode -> event` logic

What is still missing is a compact internal surface that helps analysts and
future models identify:

- episode formation
- episode escalation
- process persistence
- multi-signal convergence that deserves special monitoring

The panel should not be treated as a public-facing risk product. It should be
an internal aid for:

- analyst monitoring
- benchmark-case review
- episode/process hypothesis generation
- future predictive feature engineering

## Core Design Rule

The panel should not be driven by media attention alone.

Recommended logic:

- primary signals should come from SENTINEL-coded events and internal constructs
- secondary overlay signals may come from media attention, tone, or
  corroboration

In other words:

- `SENTINEL event logic first`
- `attention/tone as supplemental context`

## Pilot Signal Series

The first internal panel should be intentionally small and interpretable.

Recommended pilot series:

### 1. Coercive Instability Signal

Purpose:

- captures destabilizing coercive activity that may signal acute rupture risk or
  the start of a live escalation episode

Primary ingredients:

- `event_type_coup_count`
- `event_type_purge_count`
- `event_type_conflict_count`
- `high_salience_event_count`
- `deed_type_destabilizing_count`

### 2. Institutional Erosion Signal

Purpose:

- tracks DEED-style erosion pressure that may indicate a broader governance or
  regime-vulnerability process

Primary ingredients:

- `deed_type_symptom_count`
- `deed_type_precursor_count`
- `deed_type_destabilizing_count`
- `axis_vertical_count`
- `axis_horizontal_count`

### 3. Security Fragmentation Signal

Purpose:

- tracks disorder, fragmentation, and contested coercive control

Primary ingredients:

- `event_type_oc_count`
- `event_type_conflict_count`
- `event_shock_flag`
- weak state-capacity context

### 4. Elite Fracture / Security Realignment Signal

Purpose:

- captures elite-security stress and internal reconfiguration that may feed
  regime vulnerability or militarization

Primary ingredients:

- `event_type_purge_count`
- high-salience command/leadership events
- episode-level actor continuity once available

### 5. External Pressure Signal

Purpose:

- captures when external actors and constraints materially intensify pressure on
  a country

Primary ingredients:

- `external_pressure_sanctions_active`
- `external_pressure_sanctions_delta`
- `external_pressure_imf_program_active`
- `external_pressure_imf_program_break`
- `external_pressure_us_security_shift`

### 6. Economic Stress / Policy Shock Signal

Purpose:

- tracks macro strain and abrupt economic-policy shifts that can amplify regime
  stress or process acceleration

Primary ingredients:

- `economic_fragility_inflation_stress`
- `economic_fragility_fx_stress`
- `economic_fragility_debt_stress`
- `economic_policy_capital_controls_flag`
- `economic_policy_nationalization_signal`

## How The Signal Layer Should Feed The Main Measures

The signal panel should not sit off to the side as a standalone monitoring toy.
It should become an internal layer that feeds the main country-risk measures.

Recommended logic:

- signal series feed construct pressure
- construct pressure feeds top-line internal risk

So the intended flow is:

`event logic -> signal series -> main constructs -> overall internal risk`

### Main Construct Destinations

#### Regime Vulnerability

Most relevant signal inputs:

- coercive instability
- institutional erosion
- elite fracture
- external pressure
- economic stress / policy shock

Why:

- regime vulnerability is the construct most exposed to convergence across
  coercive, institutional, external, and macro stress

#### Militarization

Most relevant signal inputs:

- coercive instability
- elite fracture
- external pressure

Why:

- militarization is most likely to move when coercive stress, security
  realignment, and external-security posture interact with the structural base

#### Security Fragmentation

Most relevant signal inputs:

- security fragmentation
- economic stress / policy shock

Why:

- fragmentation should still be anchored in coercive disorder, but economic
  stress can amplify local breakdown and spillover

### Overall Internal Risk

The top-line internal risk measure should not be a simple sum of the raw signal
series.

Recommended logic:

- first aggregate signals into the three main constructs
- then aggregate the three constructs into a top-line internal risk layer

That keeps the system interpretable and aligned with the existing architecture.

## Suggested Internal Aggregation Rule

Signal layer:

- each signal series gets its own time path and internal label

Construct layer:

- `regime_vulnerability_signal_pressure`
- `militarization_signal_pressure`
- `security_fragmentation_signal_pressure`

Top-line layer:

- `overall_risk_internal`

This creates a cleaner bridge between:

- raw event logic
- episode/process detection
- country-risk monitoring
- future forecasting

## Suggested Display Logic

The pilot internal panel should show:

- 4 to 6 series only
- clear line separation
- event markers for major events
- episode-start markers
- episode-escalation markers
- process-transition markers later

Recommended first layout:

- one country at a time
- 90-day to 180-day window by default
- event markers and notes overlaid on the series

## Suggested Output Labels

Useful internal readouts:

- `background`
- `watch`
- `forming episode`
- `active episode`
- `process acceleration`

## Benchmark-Case Use

Recommended early benchmark countries:

- Venezuela
- El Salvador
- Ecuador
- Haiti
- Mexico

Recommended first anchor:

- Venezuela, especially the sequence beginning on January 3, as a test of
  whether the panel can distinguish:
  - a major break
  - a sustained episode
  - a longer process of regime-security tightening

## Current Decision

Current architectural decision:

- SENTINEL should prototype a private/internal signal panel
- the first version should use 4 to 6 interpretable signal series
- it should support episode and process detection, not replace the event layer
- it should feed the three main constructs and a top-line internal risk measure
- it should remain internal and not appear in the public dashboard
