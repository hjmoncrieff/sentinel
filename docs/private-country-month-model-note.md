# SENTINEL Private Country-Month Modeling Note

This note is internal-only for now. It translates the current forecasting sketch
into a concrete design path for SENTINEL's predictive modeling layer.

It should be read alongside:

- [private-risk-architecture-note.md](/Users/hjmoncrieff/Library/CloudStorage/Dropbox/SENTINEL/docs/private-risk-architecture-note.md)
- [baseline-pulse-design.md](/Users/hjmoncrieff/Library/CloudStorage/Dropbox/SENTINEL/docs/baseline-pulse-design.md)

## Why This Layer Should Exist

SENTINEL now has:

- event ingestion
- actor coding
- council interpretation
- country constructs
- benchmark-based validation for the layered risk scaffold

What it does not yet have is a dedicated predictive modeling layer for explicit
probability estimation.

The purpose of the country-month model is to provide that missing layer.

It should not replace the current monitoring architecture. It should sit on top
of it.

In practice:

- the monitoring stack explains the country condition
- the predictive stack estimates specific future outcomes

## Core Unit Of Analysis

Recommended unit:

- `country x month`

Recommended coverage:

- Latin America and the Caribbean
- historical coverage as far back as the structural and event layers allow
- ideal target window: `1990-present`

Important distinction:

- `operational product window`
  - `1990-present`
  - this should remain the live monitoring, review, and public/internal product
    window
- `training-history window`
  - currently reaches back to `1960` in the merged structural layer
  - may extend earlier than `1960` later when structural country-year data is
    available and analytically useful
  - this is appropriate for private model training, calibration, priors, and
    long-run legacy features

So the project should not treat those as the same thing. Earlier structural
history can strengthen the models without changing the live product window.

Why country-month:

- it is granular enough for event and sanctions logic
- it is stable enough for panel modeling
- it aligns well with rare-event forecasting
- it can absorb both structural annual data and high-frequency event counts

## Coverage Rule

SENTINEL should now distinguish two coverage windows explicitly:

- `product coverage window`
  - default: `1990-present`
  - applies to:
    - public dashboard outputs
    - analyst-console live monitoring
    - operational event/episode watch logic
- `training coverage window`
  - currently includes `1960-1989` in the merged structural layer
  - may extend earlier than `1960` later
  - applies to:
    - structural-only training extensions
    - long-run country-history features
    - calibration and historical benchmark work

Practical rule:

- do use pre-1990 structural country-year history where it improves training
  and historical context
- do not silently fold pre-1990 history into the live monthly product window
  as if it were part of the current operational monitoring surface

## Proposed Internal Data Product

SENTINEL should create a dedicated modeling artifact such as:

- `data/modeling/country_month_panel.parquet`

or initially:

- `data/modeling/country_month_panel.csv`
- `data/modeling/country_month_panel.json`

This panel should be private/internal and not part of the public dashboard
surface.

First implementation path now exists:

- `scripts/analysis/build_country_month_panel.py`

Current output:

- `data/modeling/country_month_panel.json`
- `data/modeling/country_month_panel.csv`

Current status:

- structural baseline fields are usable
- event-pulse and rolling-window fields are usable
- first episode-sequence fields are now usable
- first target columns are now present as conservative proxy labels
- external and economic fields now have a first live private/internal monthly
  signal layer, though benchmark/manual overrides still remain important
- the current monthly panel now spans `1960-01` through `2025-12`
- the live product window still remains conceptually anchored to
  `1990-present`
- the `1960-1989` portion should be treated as private training history, not a
  change to the live public-facing coverage claim
- the first fitted irregular-transition comparison now also uses the expanded
  structural feature family, including:
  - `time_since_last_coup`
  - `coup_count_5y`
  - `regime_shift_flag`
  - `polyarchy_delta_1y`
  - `trade_openness_delta_3y`
  - `oda_received_delta_3y`
- the added historical-memory and shift features improved the fitted model's
  recall, but the simple score-threshold baseline still remains the best
  benchmark on the reviewed sample

## Panel Structure

Each row should represent one country-month.

Suggested fields:

### Index Fields

- `country`
- `iso3`
- `year`
- `month`
- `panel_date`

### Structural Baseline Features

These should update slowly and be forward-filled or quarter-filled as needed.

Examples:

- `polyarchy`
- `regime_type`
- `mil_constrain`
- `mil_exec`
- `coup_total_events`
- `executive_direct_election`
- `democracy_breakdown`
- `democracy_transition`
- `trade_openness_pct_gdp`
- `oda_received_pct_gni`
- `m3_conscription`
- `m3_mil_veto`
- `m3_mil_impunity`
- `m3_mil_crime_police`
- `m3_mil_eco`
- `wgi_rule_of_law`
- `wgi_govt_effectiveness`
- `wgi_control_corruption`
- `wgi_political_stability`
- `state_capacity_composite`
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
- `militarization_structural`
- `criminality_baseline`

### Event-Derived Pulse Features

Monthly aggregated event features should come from SENTINEL's reviewed/canonical
event layer.

Examples:

- total event count
- high-salience event count
- conflict count
- organized-crime count
- protest count
- purge count
- coup-related count
- DEED erosion count
- DEED symptom count
- DEED precursor count
- DEED resistance count
- vertical-axis erosion count
- horizontal-axis erosion count
- human-validated event count
- duplicate-adjusted event count

### Rolling-Window Features

The panel should not only store current-month counts. It should also include
rolling windows.

Examples:

- 1-month counts
- 3-month totals
- 6-month totals
- 12-month slope or change
- shock dummy for abrupt jumps
- monthly mix summaries for:
  - salience
  - confidence
  - DEED
  - review state

### Episode Features

The panel should now begin to absorb bounded sequence logic, not only event
counts.

Current implementation path:

- `scripts/analysis/build_episodes.py`
- `data/modeling/episodes.json`

Current episode fields in the panel include:

- `episode_count`
- `episode_start_count`
- `active_episode_count`
- `high_severity_episode_count`
- `medium_severity_episode_count`
- `escalating_episode_count`
- `fragmenting_episode_count`
- `institutionalizing_episode_count`
- `dominant_episode_type`
- `dominant_episode_severity`
- construct-linked episode counts

This is the first bridge from raw events toward later process-aware modeling.

### External Pressure Features

These should become explicit panel features.

First-priority candidates:

- `sanctions_active`
- `sanctions_added_this_month`
- `sanctions_removed_this_month`
- `imf_program_active`
- `imf_program_start`
- `imf_program_breakdown`
- `us_security_assistance_level`
- `us_security_assistance_change`

Current implementation status:

- contract fields exist in the panel
- a tracked contract now defines them in:
  - `config/modeling/panel_feature_contract.json`
- a first derived monthly artifact now feeds them through:
  - `data/modeling/external_economic_country_month.json`
- a tracked benchmark seed now exists through:
  - `data/modeling/benchmark_country_month_signals.json`
- a local manual-seed path now exists through:
  - `data/modeling/manual_country_month_signals.local.json`
- panel presence flags now make seeded coverage visible:
  - `external_pressure_signal_present`
- deeper ingestion remains future work

### Economic Features

These should be treated as baseline plus shock logic.

Examples:

- inflation
- GDP growth
- debt/GDP
- reserves adequacy
- exchange-rate stress
- resource rents
- commodity dependence
- capital-control announcement flag
- nationalization / expropriation signal

Current implementation status:

- contract fields exist in the panel
- a tracked contract now defines them in:
  - `config/modeling/panel_feature_contract.json`
- a first derived monthly artifact now feeds them through:
  - `data/modeling/external_economic_country_month.json`
- a tracked benchmark seed now exists through:
  - `data/modeling/benchmark_country_month_signals.json`
- a local manual-seed path now exists through:
  - `data/modeling/manual_country_month_signals.local.json`
- panel presence flags now make seeded coverage visible:
  - `economic_fragility_signal_present`
  - `policy_shock_signal_present`
- deeper live ingestion remains future work

## Recommended Targets

The predictive layer should be target-specific.

That means defining outcomes clearly rather than trying to predict a vague
"country risk" score.

### First-Priority Targets

- `irregular_transition_next_1m`
- `irregular_transition_next_3m`

These are the cleanest initial targets for a rare-events framework.

Current implementation status:

- both targets now exist in the panel as `proxy_label` fields
- current rule version:
  - `proxy_irregular_transition_v3`
- current positive rule:
  - a future month is positive when it reaches a proxy transition score of at
    least `3`
  - strongest positive paths include:
    - `event_type = coup`
    - a destabilizing, high-salience purge
    - a destabilizing shock month combining escalation and erosion signals
    - a high-severity episode linked to `regime_vulnerability`
    - an escalating episode start linked to `regime_vulnerability`
- current tightening:
  - weak episode paths are now more conservative, so not every escalating
    regime-linked episode turns positive
  - the high-severity rupture path is preserved, which is especially important
    for benchmark cases like Haiti
- supporting target fields now include:
  - `irregular_transition_signal_score_next_1m`
  - `irregular_transition_signal_score_next_3m`
  - `irregular_transition_signal_label_next_1m`
  - `irregular_transition_signal_label_next_3m`
  - `irregular_transition_fit_score_next_1m`
  - `irregular_transition_fit_score_next_3m`
  - `irregular_transition_fit_label_next_1m`
  - `irregular_transition_fit_label_next_3m`

This is intentionally conservative and should be treated as target-ready
infrastructure, not final adjudicated ground truth.

### Second-Priority Target

- `acute_political_risk_next_1m`
- `acute_political_risk_next_3m`

This is the first broader political-risk deterioration target beyond the
narrower irregular-transition path.

Current implementation status:

- both targets now exist in the panel as `proxy_label` fields
- current rule version:
  - `proxy_acute_political_risk_v1`
- the proxy combines:
  - high-severity episodes linked to `regime_vulnerability`
  - high-severity episodes linked to `security_fragmentation`
  - fragmenting sequences
  - event-shock deterioration
  - external-pressure spikes
  - economic-fragility spikes
  - structural shift flags

Current first proxy checkpoint:

- `1m` positives: `51`
- `3m` positives: `125`
- `1m` watch rows: `156`
- `3m` watch rows: `323`

Illustrative current behavior:

- Haiti `2021-06-01`
  - `acute_political_risk_next_1m = 1`
  - score `6`
- El Salvador `2023-11-01`
  - `acute_political_risk_next_1m = 1`
  - score `6`
- Venezuela `2023-06-01`
  - `acute_political_risk_next_1m = 1`
  - score `5`

Current review path:

- `scripts/analysis/review_acute_political_risk_targets.py`
- output:
  - `data/review/acute_political_risk_target_review.json`

Current first review checkpoint:

- Bolivia: `4` cases
- Brazil: `2`
- Chile: `2`
- Colombia: `18`
- El Salvador: `3`
- Guatemala: `2`
- Haiti: `6`
- Honduras: `4`
- Mexico: `2`
- Peru: `1`
- Venezuela: `7`

Current review read:

- many acute-risk positives look stronger than the narrower irregular-transition
  cases because this target is meant to absorb broader deterioration
- Colombia is currently the heaviest review burden
- Haiti, El Salvador, and Venezuela look especially central for benchmark work

Current adjudication-queue path:

- `scripts/analysis/build_acute_political_risk_adjudication_queue.py`
- output:
  - `data/review/adjudication_queue_acute_political_risk.json`
- optional local decisions file:
  - `data/review/adjudicated_acute_political_risk_decisions.local.json`
- tracked template:
  - `data/review/adjudicated_acute_political_risk_decisions.template.json`

Current adjudicated acute-risk layer:

- `scripts/analysis/build_adjudicated_acute_political_risk_labels.py`
- output:
  - `data/modeling/adjudicated_acute_political_risk_labels.json`
- this should now be treated as:
  - `acute political risk adjudicated layer v1`
- current acute-risk adjudicated layer count:
  - `30`
- current acute-risk adjudicated countries:
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
- current remaining acute-risk adjudication queue:
  - empty

Recommended stance:

- do not keep expanding this layer casually
- later derive a stricter acute-risk gold subset from this reviewed base

Current acute-risk gold subset:

- `scripts/analysis/build_gold_acute_political_risk_labels.py`
- output:
  - `data/modeling/gold_acute_political_risk_labels.json`
- current gold acute-risk row count:
  - `22`
- current gold acute-risk countries:
  - `Bolivia`
  - `Chile`
  - `Colombia`
  - `El Salvador`
  - `Haiti`
  - `Honduras`
  - `Peru`
  - `Venezuela`

Current acute-risk gold-validation path:

- `scripts/analysis/validate_gold_acute_political_risk_targets.py`
- output:
  - `data/review/gold_acute_political_risk_validation.json`

Current acute-risk gold-validation checkpoint:

- gold rows: `22`
- true positives against gold: `22`
- false negatives against gold: `0`
- false positives against gold: `26`
- gold recall: `100.0%`
- proxy precision against gold: `45.833%`

Current acute-risk benchmark tiers:

- `scripts/analysis/build_acute_political_risk_benchmark_tiers.py`
- output:
  - `data/modeling/acute_political_risk_benchmark_tiers.json`
- current tier counts:
  - gold positives: `22`
  - hard negatives: `18`
  - easy negatives: `22`

Current acute-risk tier-separation audit:

- `scripts/analysis/audit_acute_political_risk_tier_separation.py`
- output:
  - `data/review/acute_political_risk_tier_separation.json`
- current takeaway:
  - hard negatives are more contestation-heavy than acute-risk gold positives
  - `transition_contestation_load_score`
    - gold mean: `1.516`
    - hard-negative mean: `4.829`
  - `transition_rupture_precursor_score`
    - gold mean: `0.823`
    - hard-negative mean: `2.871`
  - latest acute-risk refinement:
    - preserved `100.0%` gold recall
    - reduced false positives from `29` to `26`

Current protest-specific interpretation layer:

- the panel now includes:
  - `protest_acute_signal_score`
  - `protest_background_load_score`
- these are derived from:
  - protest counts
  - protest-security-escalation episodes
  - conflict overlap
  - high-severity / shock reinforcement
- current use:
  - they feed transition-specificity interpretation
  - they do not currently feed the acute-risk score directly
- reason:
  - the first direct scoring pass increased acute-risk overfire and was
    intentionally backed out
- current review path:
  - `scripts/analysis/review_acute_political_risk_protest_cases.py`
  - output:
    - `data/review/acute_political_risk_protest_review.json`
- narrow interpretation note:
  - `docs/private-acute-protest-interpretation-note.md`
- current working read:
  - protest-heavy acute positives are rare in the current benchmark
  - protest-heavy hard negatives are much more common
  - the clearest positive protest pattern so far is:
    - protest-security escalation
    - plus high severity
    - plus low background overload
    - plus non-negative specificity gap
  - a first candidate field now also exists:
    - `protest_escalation_specificity_score`
  - current benchmark read:
    - `gold_positive` mean `0.142` with `2` nonzero rows
    - `hard_negative` mean `0.291` with `5` nonzero rows
  - implication:
    - keep it as a benchmark-only candidate feature for now
    - do not let it drive acute-risk scoring yet

Current acute-risk benchmark-refinement path:

- `scripts/analysis/build_acute_political_risk_benchmark_refinement_queue.py`
- output:
  - `data/review/acute_political_risk_benchmark_refinement_queue.json`
- current first checkpoint:
  - current active refinement queue: `0`
  - `hard_negative`: `0`
  - `easy_negative`: `0`
- current stance:
  - acute-risk benchmark refinement layer is now frozen as `v1`
  - use the current benchmark as the active reviewed reference set unless new
    evidence justifies reopening specific rows
- reviewed local refinement decisions now exist in:
  - `data/review/acute_political_risk_benchmark_refinement_decisions.local.json`
- resolved so far:
  - Mexico `2020-07-01`
  - Venezuela `2024-08-01`
  - Venezuela `2025-09-01`
  - Honduras `2022-02-01`
  - El Salvador `2020-09-01`
  - Peru `2024-05-01`
  - El Salvador `2022-03-01`
  - Haiti `2021-04-01`
  - Honduras `2022-03-01`
  - Colombia `2024-06-01`
  - Brazil `2023-01-01`
  - Brazil `2024-06-01`
  - Guatemala `2020-12-01`
  - Guatemala `2021-01-01`
  - Colombia `2024-04-01`
  - Haiti `2021-03-01`
  - Mexico `2020-10-01`
  - Brazil `2025-01-01`

Current acute-risk fit dataset:

- `scripts/analysis/build_acute_political_risk_fit_dataset.py`
- output:
  - `data/modeling/acute_political_risk_fit_dataset.json`
- current fit-sample checkpoint:
  - rows: `61`
  - gold positives: `22`
  - hard negatives: `17`
  - easy negatives: `22`
  - this fit-ready sample now reflects the frozen acute-risk benchmark
    refinement layer `v1`

Current acute-risk baseline validation:

- `scripts/analysis/validate_acute_political_risk_baseline.py`
- output:
  - `data/review/acute_political_risk_baseline_validation.json`
- current best threshold:
  - `4`
- current result:
  - precision `100.0%`
  - recall `100.0%`
  - specificity `100.0%`
  - this result still holds after freezing the benchmark refinement layer `v1`

Current acute-risk model comparison:

- `scripts/analysis/validate_acute_political_risk_models.py`
- output:
  - `data/review/acute_political_risk_model_validation.json`
- current comparison:
  - threshold baseline:
    - precision `100.0%`
    - recall `100.0%`
    - specificity `100.0%`
  - leave-one-out logistic:
    - precision `84.615%`
    - recall `100.0%`
    - specificity `89.744%`
  - hard-negative specificity under logistic:
    - `76.471%`
  - current implication after freezing benchmark refinement `v1`:
    - the threshold baseline remains the operative benchmark
    - the first fitted model still does not beat it

Private design/spec references:

- `docs/private-acute-political-risk-note.md`
- `config/modeling/acute_political_risk_spec.json`

Current audit path:

- `scripts/analysis/audit_country_month_targets.py`
- output:
  - `data/modeling/country_month_target_audit.json`

Current review path:

- `scripts/analysis/review_irregular_transition_targets.py`
- output:
  - `data/review/irregular_transition_target_review.json`

Current adjudication-queue path:

- `scripts/analysis/build_adjudication_queue.py`
- output:
  - `data/review/adjudication_queue_irregular_transition.json`

This second step is now useful because the episode-aware proxy rule can produce
plausible rupture-watch labels that still need country-by-country inspection
before they are treated as good training labels.

Current adjudicated bridge:

- `scripts/analysis/build_adjudicated_transition_labels.py`
- output:
  - `data/modeling/adjudicated_irregular_transition_labels.json`

This first adjudicated layer is intentionally narrow. It currently promotes a
small set of reviewed benchmark positives and overrides only the
`irregular_transition_next_1m` label in the panel where those reviewed rows
exist. Everything else stays on the episode-aware proxy rule.

Current checkpoint status:

- the first internal adjudicated layer now contains `34` reviewed `1m`
  irregular-transition labels
- current adjudicated countries:
  - `Bolivia`
  - `Brazil`
  - `Chile`
  - `Colombia`
  - `El Salvador`
  - `Haiti`
  - `Honduras`
  - `Mexico`
  - `Venezuela`
- the current adjudication queue has been cleared

Recommended next stance:

- pause expansion here
- treat this as `internal adjudicated layer v1`
- later tighten this into a stricter gold-label subset rather than continuing
  to expand the local adjudication file indefinitely

Current gold-subset path:

- `scripts/analysis/build_gold_transition_labels.py`
- output:
  - `data/modeling/gold_irregular_transition_labels.json`

Current gold-subset status:

- `25` gold `1m` irregular-transition labels
- gold countries:
  - `Bolivia`
  - `Brazil`
  - `Chile`
  - `Colombia`
  - `El Salvador`
  - `Haiti`
  - `Mexico`
  - `Venezuela`

Gold rule:

- always include benchmark `strong` cases
- include local `reviewed` cases only when:
  - `proxy_score_1m >= 4`
  - and the note reflects:
    - `high-severity`
    - `rupture`
    - `assassination`
    - or `coup-coded`
- exclude `reviewed_watch`

Current gold-validation path:

- `scripts/analysis/validate_gold_transition_targets.py`
- output:
  - `data/review/gold_irregular_transition_validation.json`

Current first validation checkpoint:

- gold rows: `25`
- true positives against gold: `22`
- false negatives against gold: `3`
- false positives against gold: `6`
- fit-path gold recall: `88.0%`
- fit-path precision against gold: `75.0%`
- the stricter fit-path now trades recall for cleaner precision relative to the
  earlier broader watch-path checkpoint

Fit-target implication:

- the broader `adjudicated v1` layer remains useful for internal monitoring and
  reviewed watch logic
- the stricter `gold` subset should be treated as the training/validation
  target for first model fitting
- the benchmark reference layer now also has a consolidated tiered artifact:
  - `gold_positive`
  - `hard_negative`
  - `easy_negative`
- the current tiered validation result is especially useful because it shows:
  - the threshold baseline cleanly separates all three tiers
  - the fitted logistic still performs poorly on `hard_negative` months
    even when it does somewhat better on `easy_negative` months
- the panel now carries a dedicated gold-aligned field:
  - `irregular_transition_gold_next_1m`
  - with availability flag:
    - `irregular_transition_gold_label_available`

Current baseline-validation path:

- `scripts/analysis/validate_irregular_transition_baseline.py`
- output:
  - `data/review/irregular_transition_baseline_validation.json`

Current baseline checkpoint on the reviewed fit-ready sample:

- sample rows: `64`
- gold positives: `25`
- reviewed negatives: `39`
- local reviewed negatives: `28`
- operational `v1` label:
  - precision: `73.529%`
  - recall: `100%`
- score-threshold sweep:
  - the broader watch-path remains in:
    - `irregular_transition_signal_score_next_1m`
    - `irregular_transition_signal_label_next_1m`
  - the stricter fit-path now lives in:
    - `irregular_transition_fit_score_next_1m`
    - `irregular_transition_fit_label_next_1m`
  - for the stricter fit-path, `threshold 2` is the current best F1
    threshold on the reviewed sample
  - at fit threshold `2`:
    - precision: `74.194%`
    - recall: `92.0%`
    - specificity: `79.487%`
  - fit threshold `4` remains useful as a stricter high-specificity cut:
    - precision: `100%`
    - recall: `88.0%`
    - specificity: `100%`

Current first fit comparison:

- `scripts/analysis/validate_irregular_transition_models.py`
- output:
  - `data/review/irregular_transition_model_validation.json`

Compared on the same reviewed fit-ready sample:

- threshold baseline:
  - precision: `100%`
  - recall: `88.0%`
- operational `v1` label:
  - precision: `73.529%`
  - recall: `100%`
- leave-one-out logistic model:
  - precision: `46.875%`
  - recall: `60.0%`

Current implication:

- the first fitted model does not beat the threshold baseline
- the threshold baseline should remain the pre-training benchmark until a
  better feature set or larger reviewed sample exists
- tier-separation evidence now suggests the best feature direction is:
  - higher contestation-load penalties for near-miss cases
  - better rupture-specific signals that do more than count high-severity
    episodes
- the `v6` rupture-sequence escape hatch did improve benchmark-positive watch
  cases like Haiti `2021-06-01` and Mexico `2020-06-01`, but it also made the
  stricter `threshold 4` benchmark less recall-complete than before
- the latest fit-only refinements recovered most of that loss, lifting
  stricter `threshold 4` gold recall to `88.0%` while keeping hard-negative
  specificity at `100%`
- the remaining missed gold cases are now concentrated in El Salvador, which
  makes the next refinement problem much narrower and more interpretable
- a narrow interpretation pass is now recorded in:
  - `docs/private-el-salvador-fit-interpretation-note.md`
- current interpretive stance:
  - keep the remaining El Salvador cases as reviewed/watch-relevant positives
  - do not automatically force them into the stricter fit rule without
    additional rupture-specific evidence

Current fit-sample audit:

- `scripts/analysis/audit_irregular_transition_fit_sample.py`
- output:
  - `data/review/irregular_transition_fit_sample_audit.json`

Current sample weakness:

- reviewed negatives are broader than before, but the reviewed fit sample is
  still small
- the sample still leans too heavily toward severe-vs-severe distinctions
- some difficult reviewed negatives now intentionally remain in-sample as hard
  benchmark cases
- some episode and conflict features still invert intuition because the
  negative layer remains thin relative to the positive set
- the harder negative pass made the fitted model weaker again, which is useful
  evidence that the threshold baseline remains the honest benchmark
- tier-specific validation now confirms where the fitted model fails:
  - `hard_negative` specificity is currently only `30.0%`
- the new tier-separation audit shows:
  - `transition_contestation_load_score` is materially higher in
    `hard_negative`
  - `transition_specificity_gap` is materially more negative in
    `hard_negative`
  - `transition_rupture_precursor_score` alone does not yet cleanly separate
    the tiers

Immediate modeling recommendation:

- deepen reviewed negatives within the countries already in the sample
- add more hard benchmark negatives alongside lower-intensity negatives
- only then retry fitted-model comparisons

Local expansion path:

- template:
  - `data/review/adjudicated_transition_decisions.template.json`
- local file:
  - `data/review/adjudicated_transition_decisions.local.json`

This lets the project expand the adjudicated layer gradually without baking new
country decisions directly into the benchmark-review script.

This should be used before any first model fit so class balance and country/time
distribution are inspected explicitly.

### Second-Priority Targets

- `backsliding_acceleration_next_6m`
- `militarization_escalation_next_3m`
- `security_fragmentation_jump_next_3m`

The first construct-oriented benchmark pass is now underway for
`security_fragmentation_jump_next_3m`.

Current checkpoint:

- proxy version:
  - `proxy_security_fragmentation_jump_v2`
- first review artifact:
  - `data/review/security_fragmentation_jump_target_review.json`
- reviewed positives across the initial benchmark-country set: `234`
- first adjudication queue:
  - `data/review/adjudication_queue_security_fragmentation_jump.json`
  - first queue size: `111`
- first adjudicated construct batch:
  - `data/modeling/adjudicated_security_fragmentation_jump_labels.json`
  - adjudicated rows after full queue clearance: `119`
  - adjudicated countries now covered:
    - `Brazil`
    - `Colombia`
    - `Ecuador`
    - `El Salvador`
    - `Guatemala`
    - `Haiti`
    - `Honduras`
    - `Mexico`
    - `Peru`
    - `Venezuela`
  - queue now `0`
  - this can now be treated as:
    - `security fragmentation jump adjudicated layer v1`
  - stricter gold subset:
    - `data/modeling/gold_security_fragmentation_jump_labels.json`
    - gold rows: `36`
  - first gold validation:
    - `data/review/gold_security_fragmentation_jump_validation.json`
    - recall: `100.0%`
    - precision against gold: `10.976%`
  - current interpretation:
    - the construct proxy is catching clean gold cases
    - the next refinement problem is specificity, not recall
  - tiered benchmark:
    - `data/modeling/security_fragmentation_jump_benchmark_tiers.json`
    - gold positives: `36`
    - hard negatives: `14`
    - easy negatives: `20`
  - tier separation:
    - `data/review/security_fragmentation_jump_tier_separation.json`
  - current separation read:
    - strongest positive separator:
      - `security_fragmentation_jump_signal_score_next_3m`
    - strongest hard-negative separators:
      - `transition_rupture_precursor_score`
      - `transition_contestation_load_score`
  - latest refinement read:
    - the `v2` contestation-discount pass did not materially change the gold
      or tiered benchmark metrics
    - the next refinement step likely needs a stronger structural redesign

### Why Target Design Matters

SENTINEL should avoid training a model on:

- generic instability
- unspecific "risk"
- loosely defined political deterioration

Instead, it should define:

- what exactly counts as the event
- over what horizon
- with what source or adjudication rules

For now, SENTINEL is using an interpretable event-rule proxy rather than a full
historical adjudication layer.

## Recommended Model Families

The system should compare several model types rather than committing too early
to one.

### 1. Rare-Events Logit

Use for:

- coup risk
- irregular transition risk
- interpretable baseline

Why:

- transparent coefficients
- useful benchmark
- easy to explain

### 2. Random Forest

Use for:

- nonlinear interaction detection
- robustness checks
- feature importance comparison

Why:

- simple strong baseline
- less tuning burden than some alternatives

### 3. Gradient Boosting

Use for:

- strongest likely predictive performance
- sequential error correction

Why:

- often performs well on structured panel data
- handles nonlinearities and interactions well

## Rare-Event Handling

This part of the diagram is exactly right and should be explicit in SENTINEL.

Likely tools:

- class weighting
- stratified sampling
- threshold tuning
- precision-recall optimization

SMOTE-style methods may be useful in experiments, but they should not become the
default without careful testing because synthetic minority generation can distort
rare political events.

Recommended baseline:

- start with weighting + threshold tuning
- compare to stratified resampling
- evaluate with precision-recall, not accuracy

## Validation Design

Validation should be first-class, not an afterthought.

Recommended:

- rolling out-of-sample windows
- train on past, validate on future
- compare against a base-rate null
- track both ranking performance and calibration

Metrics to emphasize:

- precision-recall
- AUROC
- calibration error
- recall at analyst-relevant thresholds

Accuracy should not be the headline metric for rare events.

## Relationship To The Existing Dashboard

The predictive layer should feed the dashboard, not be the dashboard itself.

That means:

- the public dashboard can consume monthly probabilities later
- country pages can show predictive outlooks
- the analyst console can inspect model explanations and validation notes

But the modeling pipeline should remain separate from the frontend.

## Suggested Outputs

Private/internal outputs:

- monthly probability by country
- model version
- training window
- validation metrics
- feature importance
- notes on top drivers

Public-safe outputs later:

- country probability tier
- concise interpretation
- what moved the probability recently

## Variable Importance And Explainability

This should be a required output, not a nice-to-have.

For each model version, SENTINEL should store:

- top global predictors
- country-specific top features for current month
- whether the signal was mostly:
  - political
  - security
  - external
  - economic

This is especially important if the system will be used alongside analyst
review.

## How This Connects To Current SENTINEL Work

Already available:

- structural country-year layer
- ACLED-style baseline features
- SENTINEL event pulse
- DEED erosion event signals
- country constructs

Still needed:

- dedicated country-month panel builder
- target-label builder
- model training/evaluation runner
- validation artifacts
- feature-importance outputs

## Recommended Build Order

1. Create a private note and spec for the panel schema.
2. Build `country_month_panel`.
3. Define first target:
   - `irregular_transition_next_3m`
4. Train baseline rare-events logit.
5. Add random forest and gradient boosting comparisons.
6. Write rolling validation reports.
7. Decide what parts of the predictive layer become visible in the dashboard.

## Draft Pipeline Shape

Suggested future runners:

- `scripts/modeling/build_country_month_panel.py`
- `scripts/modeling/build_transition_targets.py`
- `scripts/modeling/train_irregular_transition_models.py`
- `scripts/modeling/validate_irregular_transition_models.py`

Possible outputs:

- `data/modeling/country_month_panel.parquet`
- `data/modeling/transition_targets.parquet`
- `data/review/model_validation/irregular_transition_report.json`
- `data/published/model_outputs/transition_risk.json`

## Strategic Recommendation

Do not jump directly from the current dashboard into a forecasting product.

Instead:

- keep the current monitoring and interpretation layer
- build the panel and target layer underneath
- validate models privately
- only then decide what forecast outputs deserve a public or analyst-facing role
