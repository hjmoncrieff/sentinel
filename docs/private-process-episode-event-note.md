# SENTINEL Private Process-Episode-Event Note

This note is private/internal. It defines a proposed aggregation hierarchy for
SENTINEL's internal logic so event supervision, country monitoring, and future
forecasting can be organized around the same analytical structure.

It should be read alongside:

- [private-risk-architecture-note.md](/Users/hjmoncrieff/Library/CloudStorage/Dropbox/SENTINEL/docs/private-risk-architecture-note.md)
- [private-country-month-model-note.md](/Users/hjmoncrieff/Library/CloudStorage/Dropbox/SENTINEL/docs/private-country-month-model-note.md)
- [baseline-pulse-design.md](/Users/hjmoncrieff/Library/CloudStorage/Dropbox/SENTINEL/docs/baseline-pulse-design.md)

## Why This Hierarchy Matters

SENTINEL currently reasons most directly at the `event` level and then jumps to
country-level constructs.

That creates three recurring problems:

- isolated minor events can look too important when viewed alone
- major multi-event sequences are harder to represent cleanly
- country-level risk models have to infer process logic from raw event counts

An internal hierarchy of:

- `process`
- `episode`
- `event`

would reduce that gap.

## Core Logic

### Event

Definition:

- a single coded occurrence in the SENTINEL event store

Examples:

- one purge
- one protest clash
- one sanctions announcement
- one military aid package

Role in the system:

- ingestion unit
- coding and review unit
- publication unit
- atomic evidence unit

### Episode

Definition:

- a bounded cluster of related events that belong to the same immediate
  situation, escalation sequence, or policy/security episode

Examples:

- a week of command dismissals and elite-security friction
- a concentrated anti-gang crackdown wave
- a sanctions-and-policy-response sequence
- an election unrest sequence involving repeated security-force events

Role in the system:

- first aggregation layer above raw events
- helps distinguish one-off noise from meaningful sequences
- useful for internal analyst review and future monthly panel features

### Process

Definition:

- a broader country-level dynamic that persists across episodes and expresses a
  larger pattern of political, security, or institutional change

Examples:

- authoritarian consolidation
- military expansion into governance
- organized-crime fragmentation of coercive order
- economic fragility sharpening regime stress

Role in the system:

- country-risk reasoning layer
- bridge between event operations and country constructs
- likely future input to forecasting and scenario logic

## Recommended Analytical Relationship

Suggested hierarchy:

- events belong to episodes
- episodes belong to processes
- processes feed country constructs and forecasting layers

In shorthand:

`event -> episode -> process -> construct -> country risk interpretation`

## Current Implementation Status

The first internal episode stage now exists as a conservative builder:

- runner:
  - `scripts/analysis/build_episodes.py`
- artifact:
  - `data/modeling/episodes.json`

This first version does not attempt full process detection. It does:

- cluster reviewed events into bounded country-level episodes
- assign:
  - `episode_type`
  - `episode_severity`
  - `episode_direction`
  - `construct_links`
  - `process_type` placeholder
- expose linked event roles such as:
  - `trigger`
  - `reinforcing`
  - `turning_point`
  - `background`

Current tuning choices:

- clustering is now done conservatively at the process-family level rather than
  only by narrow event type, so rupture sequences are less likely to fragment
  into many trivial one-event episodes
- severity is now more sensitive to:
  - repeated high-salience events
  - repeated destabilizing events
  - short sequence length

This is especially important for benchmark cases like Haiti and Venezuela,
where the model should recognize meaningful rupture sequences instead of only
counting isolated incidents.

The private country-month panel now also absorbs first episode features such as:

- `episode_count`
- `episode_start_count`
- `active_episode_count`
- `high_severity_episode_count`
- `escalating_episode_count`
- construct-linked episode counts

This should be treated as the first sequence layer, not the finished logic.

## Major Vs Minor Logic

This hierarchy should improve how SENTINEL decides whether an event is minor,
important, or major.

### Minor Event

A likely minor event:

- has low intrinsic severity
- does not create or alter an episode
- has weak or no process relevance

### Important Event

An important event:

- may be moderate in intrinsic severity
- but strengthens or redirects an ongoing episode
- or clearly contributes to a live process

### Major Event

A likely major event:

- is intrinsically severe
- or materially shifts an episode
- or materially changes a process trajectory

Practical implication:

event salience should eventually be informed by:

- intrinsic event severity
- episode significance
- process significance

## Proposed Event Schema Role

Events should remain the current atomic layer, but gain a few internal linkage
fields.

Candidate internal fields:

- `event_id`
- `event_type`
- `event_subtype`
- `salience_intrinsic`
- `episode_id`
- `process_id`
- `episode_role`
  - `trigger`
  - `reinforcing`
  - `turning_point`
  - `background`
- `process_relevance`
  - `low`
  - `medium`
  - `high`

These do not need to become public-facing fields.

## Proposed Episode Schema

Episodes should be bounded, interpretable, and analytically legible.

Candidate fields:

- `episode_id`
- `country`
- `episode_type`
- `episode_title`
- `episode_status`
  - `forming`
  - `active`
  - `stabilizing`
  - `closed`
- `episode_start`
- `episode_end_estimate`
- `linked_event_ids`
- `event_count`
- `high_salience_event_count`
- `dominant_actor_set`
- `dominant_mechanism`
- `episode_direction`
  - `escalating`
  - `stabilizing`
  - `fragmenting`
  - `institutionalizing`
- `episode_severity`
  - `low`
  - `medium`
  - `high`
- `process_id`
- `construct_links`
  - `regime_vulnerability`
  - `militarization`
  - `security_fragmentation`
  - optional future:
    - `external_pressure`
    - `economic_fragility`

## Proposed Process Schema

Processes should be slower-moving and country-level.

Candidate fields:

- `process_id`
- `country`
- `process_type`
- `process_label`
- `process_status`
  - `latent`
  - `active`
  - `consolidating`
  - `receding`
- `start_estimate`
- `latest_episode_id`
- `linked_episode_ids`
- `trajectory`
  - `rising`
  - `stable`
  - `volatile`
  - `easing`
- `country_risk_relevance`
  - `low`
  - `medium`
  - `high`
- `construct_links`
- `watchpoints`
- `summary_text`

## Candidate Type Families

### Process Types

First useful process families could include:

- `authoritarian_consolidation`
- `military_governance_expansion`
- `security_fragmentation`
- `elite_security_fracture`
- `institutional_erosion`
- `external_pressure_cycle`
- `economic_stress_cycle`

### Episode Types

First useful episode families could include:

- `purge_wave`
- `election_security_episode`
- `anti_crime_crackdown`
- `protest_security_escalation`
- `sanctions_response_episode`
- `imf_negotiation_episode`
- `exception_regime_episode`
- `cross_border_security_episode`

## How This Should Feed The Model

The hierarchy should improve internal modeling logic in three ways.

### 1. Cleaner Country-Month Features

The private country-month panel should eventually be able to aggregate not only:

- raw event counts

but also:

- active episode count
- high-severity episode count
- active process flags
- process-transition indicators

This is more consistent with country-level risk modeling than relying only on
raw event counts.

### 2. Better Target Logic

A future irregular-transition target should likely look at:

- coup-type events
- destabilizing episodes
- process-level regime rupture indicators

rather than raw events alone.

### 3. Better Public/Internal Translation

The public dashboard may still show events.

But the internal system could reason more coherently because:

- public event view remains simple
- analyst console can review episode/process relevance
- private modeling layer can aggregate at higher analytical units

## Public vs Internal Boundary

Recommended boundary:

- public dashboard:
  - remains event-first
  - may later mention an episode in prose
- analyst console:
  - should eventually expose episode and process context
- private modeling layer:
  - uses episode and process fields heavily

The process and episode structures should stay internal until the logic is
stable and validated.

## Recommended Build Order

1. define schemas and type families
2. add internal linkage placeholders to events
3. prototype episode grouping logic
4. prototype process-state logic
5. add episode/process features to the private country-month panel
6. decide which pieces, if any, should surface in the analyst terminal

## Current Decision

Current architectural decision:

- SENTINEL should move toward a `process -> episode -> event` internal logic
  for country-risk modeling and analyst interpretation
- events remain the atomic ingestion and publication layer
- episodes become the first aggregation layer
- processes become the higher-order country-risk layer

This is a design commitment, not yet a fully implemented pipeline stage.
