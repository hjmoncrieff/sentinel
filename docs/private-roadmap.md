# SENTINEL Private Roadmap

This document is private/internal. It tracks the project across short-term,
medium-term, and long-term goals so major work stays connected to the broader
direction of the system.

Use this roadmap alongside:

- `docs/user-guide.md`
- `docs/system-workflow.md`
- `docs/next-steps.md`
- `docs/private-risk-architecture-note.md`
- `docs/private-country-month-model-note.md`
- `docs/private-process-episode-event-note.md`
- `docs/private-signal-panel-note.md`

## Purpose

This roadmap is meant to help answer four questions:

- what should be prioritized next
- what foundations are still missing
- what should remain private/internal for now
- how current work ladders up to the long-term product

## Short-Term Goals

These are the next major work items for the current phase.

Cross-cutting coverage rule:

- keep the operational/live project window anchored to `1990-present`
- allow the private training/calibration layer to use earlier structural
  country-year history when useful
- document that split clearly whenever model-training artifacts claim broader
  history than the public or analyst-facing product

### 1. Structural Model Expansion

- maintain the Python-first structural refresh flow:
  - `scripts/refresh_vdem.py`
  - `scripts/fetch_worldbank.py`
  - `scripts/build_country_year.py`
- strengthen `state_capacity_composite` and document its components clearly
- add scaffolding for:
  - external pressure
  - economic fragility
  - policy-shock signals
- deepen the new live private data series for those families beyond the current
  first derived layer
- keep a six-country benchmark review artifact current while tuning the
  external/economic formulas
- integrate newly acquired sanctions and crisis datasets into the private
  external/economic signal layer before later IMF additions
- use the improved external/economic layer to refine difficult cases like
  Haiti, where fragmentation should rise for state-weakness reasons while
  militarization remains comparatively low
- use the current manual-seed bridge first where needed:
  - `config/modeling/panel_feature_contract.json`
  - `data/modeling/manual_country_month_signals.local.json`
- begin planning how pre-1990 structural country-year history can be used as a
  private training extension without changing the live product window
- first concrete check now exists through:
  - `scripts/analysis/audit_training_history_coverage.py`
  - `data/review/training_history_coverage_audit.json`
- current finding:
  - the merged `country_year` layer now spans `1960-2025`
  - pre-1990 structural history is now available privately for all `25`
    countries
  - any extension earlier than `1960` will still require upstream ingestion
    expansion
- next diagnostic step now exists through:
  - `scripts/analysis/audit_upstream_training_sources.py`
  - `data/review/upstream_training_source_audit.json`

### 2. Country Monitor Calibration

- continue targeted calibration for:
  - `regime_vulnerability`
  - `militarization`
  - `security_fragmentation`
- keep the top-line overall-risk weighting aligned with the real dominant
  pathway of stress:
  - more weight to fragmentation where coercive disorder is the main danger
  - less weight to militarization where military political expansion is not the
    principal driver
- keep benchmark validation current
- add short validation notes when a country remains persistently misfit
- tighten the remaining difficult cases before expanding public exposure

### 2A. Process-Episode-Event Schema

- define the internal `process -> episode -> event` hierarchy clearly
- keep events as the atomic ingestion/publication layer
- use episodes as the first aggregation layer for meaningful sequences
- use processes as the country-risk reasoning layer
- current first implementation:
  - `scripts/analysis/build_episodes.py`
  - `data/modeling/episodes.json`
- immediate tuning priority:
  - benchmark episode behavior against cases like Haiti and Venezuela so major
    rupture sequences are not split into too many trivial low-severity episodes
- prepare the private panel to absorb:
  - episode counts
  - episode severity
  - active process states
  - process-transition flags

### 2B. Internal Signal Panel

- prototype a private/internal signal panel for benchmark countries
- replace placeholder-only external/economic panel fields with a real monthly
  signal artifact feeding the private country-month panel
- use it to detect:
  - episode formation
  - episode escalation
  - process acceleration
- begin with a small interpretable series set:
  - coercive instability
  - institutional erosion
  - security fragmentation
  - elite fracture
  - external pressure
  - economic stress / policy shock
- use the signal layer to feed:
  - `regime_vulnerability`
  - `militarization`
  - `security_fragmentation`
  - and a top-line internal overall risk layer
- keep this layer internal until validation is stronger

### 3. Public/Internal Product Separation

- keep the public dashboard limited to:
  - `data/published/*`
  - public-safe interpretation and monitor summaries
- keep the analyst console focused on:
  - review
  - correction
  - corroboration
  - publication control
- keep calibration, modeling panels, predictive experiments, and validation
  artifacts private/internal

### 4. Public Event Quality

- improve public event prose so interpretation is:
  - country-specific
  - less repetitive
  - more causal and mechanistic
- continue standardizing titles for clustered events
- keep internal review language out of the public event view

### 5. Internal Documentation Discipline

- after every major leap, record:
  - what changed
  - what decision was taken
  - why it was taken
  - what commands or run order changed
- keep the workflow docs synchronized with actual operating practice

## Medium-Term Goals

These are the next phase goals once the current monitor layer is steadier.

### 1. External And Economic Layers

- build structured inputs for:
  - sanctions imposition and removal
  - IMF program starts, suspensions, and renegotiations
  - major US security-assistance shifts
  - nationalization signals
  - capital controls
  - abrupt policy or regulatory shocks
- decide which of these are:
  - slow-moving baseline factors
  - high-frequency triggers

### 2. Country-Month Modeling Panel

- create a private `country x month` panel as a dedicated modeling product
- include:
  - structural factors
  - pulse/event factors
  - external signals
  - economic controls
  - target labels
- keep this panel out of the public dashboard and public docs for now
- current first implementation:
  - `scripts/analysis/build_country_month_panel.py`
  - refine it iteratively rather than treating the first schema as final
- future aggregation goal:
  - integrate process/episode features rather than relying only on raw event
    counts
- immediate next refinement:
  - freeze the current internal adjudicated layer as `v1`
  - later derive a stricter gold-label subset from it instead of continuing
    unbounded local expansion
  - current gold-subset builder:
    - `scripts/analysis/build_gold_transition_labels.py`
  - current gold subset:
    - `data/modeling/gold_irregular_transition_labels.json`

### 3. Predictive Model Layer

- broader system scope:
  - SENTINEL is modeling political / sovereign risk more broadly
  - `irregular_transition` is only the first predictive target we have
    operationalized and validated
- next target now exists at the private proxy stage:
- `acute_political_risk_next_1m`
- `acute_political_risk_next_3m`
- current proxy version:
  - `proxy_acute_political_risk_v1`
- current checkpoint:
  - `1m` positives: `51`
  - `3m` positives: `125`
- current adjudicated checkpoint:
  - `acute political risk adjudicated layer v1`
  - protest-heavy acute-risk interpretation note added so protest-linked
    near-miss months can be reviewed separately from direct score changes
  - acute-risk benchmark refinement queue added so the next modeling work can
    focus on case curation rather than new feature invention
  - first local refinement decisions now clear the top Mexico and Venezuela
    protest-near-miss rows from the active queue
  - Honduras and El Salvador acute-risk boundary cases have also now been
    reviewed and cleared from the active refinement queue
  - Peru protest-near-miss case has also now been reviewed and cleared from
    the active refinement queue
  - the El Salvador, Haiti, and Honduras fragmentation-boundary cases have now
    also been reviewed and cleared from the active queue
  - the remaining confirm-hard-negative batch and easy-negative sanity row have
    now also been reviewed, leaving the acute-risk benchmark refinement queue at `0`
  - acute-risk benchmark refinement can now be treated as frozen `v1`
  - `30` reviewed `1m` rows
- current gold-subset builder:
  - `scripts/analysis/build_gold_acute_political_risk_labels.py`
- current gold subset:
  - `data/modeling/gold_acute_political_risk_labels.json`
  - `22` reviewed `1m` rows
- current tiered benchmark layer:
  - `data/modeling/acute_political_risk_benchmark_tiers.json`
  - gold positives: `22`
  - hard negatives: `18`
  - easy negatives: `22`
- latest proxy checkpoint:
  - gold recall: `100.0%`
  - proxy precision against gold: `45.833%`
- current fit-ready checkpoint:
  - `data/modeling/acute_political_risk_fit_dataset.json`
  - sample rows: `61`
  - best baseline threshold: `4`
  - current first model-comparison result:
    - threshold baseline still wins
- define first predictive targets such as:
  - `irregular_transition_next_1m`
  - `irregular_transition_next_3m`
- compare model families:
  - rare-events logit
  - random forest
  - gradient boosting
- use rolling out-of-sample validation rather than static fit checks
- keep a target-audit step in the workflow before first model training

### 4. Gold Data And Continuous Learning

- create a `gold` layer for:
  - human-corrected events
  - validated actor codings
  - duplicate decisions
  - publication decisions
  - country-level validation notes
- use these first for:
  - retrieval
  - rule refinement
  - evaluation
- delay task-specific training until quality thresholds are clear
- immediate next irregular-transition modeling task:
  - expand the reviewed negative sample
  - use the structured negative-review queue first
  - especially beyond:
    - `Colombia`
    - `El Salvador`
    - `Honduras`
    - `Mexico`
    - `Venezuela`
  - and add lower-intensity reviewed negatives so the fit sample is not mostly
    severe-vs-severe
  - current checkpoint after the first negative pass:
    - `28` local reviewed negatives added
    - reviewed-negative country coverage increased to all `25` countries
    - `8` hard benchmark negatives added to the reviewed sample
    - tiered benchmark set now exists with:
      - `25` gold positives
      - `10` hard negatives
      - `18` easy negatives
    - the threshold baseline still clearly outperforms the first fitted model
    - the expanded historical-memory feature pass improved fitted-model recall,
      but not enough to displace the threshold rule
    - the stricter fit-path threshold now reaches:
      - `88.0%` gold recall
      - `100%` precision
      - `100%` hard-negative specificity
    - remaining residual misses are now concentrated in El Salvador and are
      documented in:
      - `docs/private-el-salvador-fit-interpretation-note.md`

### 5. Analyst-Model Feedback Loop

- let internal review improve not only events but also country monitors
- create a process for:
  - analyst notes on country outlooks
  - monitor-shift validation
  - structured disagreement with model outputs

## Long-Term Goals

These are the strategic product goals beyond the current build phase.

### 1. Layered Sovereign-Risk System

- evolve SENTINEL from an event monitor into a layered sovereign-risk platform
- connect:
  - structural baseline
  - event-driven pulse
  - predictive probability outputs
  - country-level analytical interpretation

### 2. Clear Multi-Surface Product

- public dashboard:
  - public-safe monitoring and interpretation
- analyst console:
  - internal review and release operations
- private modeling workspace:
  - calibration
  - forecasting
  - validation
  - panel-building

### 3. Stronger Modeling And Validation Infrastructure

- maintain versioned model specs
- compare model vintages over time
- track why weights or constructs changed
- maintain a real model-review workflow instead of ad hoc calibration

### 4. Multi-User Operational Maturity

- move toward more durable local persistence when needed
- support stronger role-based workflows
- improve auditability for:
  - analyst edits
  - registry changes
  - publication decisions
  - model-validation decisions

### 5. Private-To-Public Translation Discipline

- not every internal construct should appear publicly
- keep a deliberate translation layer between:
  - internal model complexity
  - public presentation simplicity
- public surfaces should show:
  - interpretable summaries
  - transparent trust signals
  - carefully curated risk language
  but not raw internal scaffolding

## Working Principles

- build private/internal modeling capability before promising public precision
- prefer interpretable constructs over opaque scores when the model is still
  maturing
- keep data-layer boundaries strict
- treat documentation as part of the architecture, not a side task
- update this roadmap when a major leap changes priorities

## Current Priority Order

1. structural expansion and cleaner country-model inputs
2. external pressure and economic fragility scaffolding
3. tighten the current internal adjudicated irregular-transition layer into a
   stricter gold-label subset before expanding it further
4. predictive target validation workflow
5. stronger analyst-to-model feedback and gold-data integration

## Public Event Quality Follow-On List

- strengthen country-specific public prose in the Events tab
- reduce repeated sentence openings and generic interpretation language
- sharpen causal/mechanistic explanation in `Why It Matters`
- clean up source presentation for clustered multi-source events
- the first construct-oriented benchmark-refinement pass is now underway for
  `security_fragmentation_jump_next_3m`
- immediate goal:
  - treat the current construct-oriented benchmark work as:
    - `security fragmentation jump adjudicated layer v1`
  - avoid casually expanding it further before deriving a stricter gold subset
