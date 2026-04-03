# SENTINEL System Workflow

## Purpose

This document describes the staged operating system that SENTINEL is becoming. It complements `docs/architecture.md` and `docs/pipeline-operations.md` by focusing on workflow boundaries and file contracts.

For exact runner commands by stage, use:

- `docs/stage-runners.md`

The project is designed as an AI-first system. Most routine work should be done
by automated ingestion, coding, QA, and analysis layers. Human users should
mainly intervene for correction, corroboration, duplicate resolution, manual
event consolidation when near-duplicates were missed upstream, and publication
control.

For public-facing event prose, the current workflow should remain:

- structured council interpretation first
- deterministic public prose rendering second
- optional API editorial rewrite later, only as a downstream polish layer

For future event classification improvement, the intended AI path should be:

- deterministic classification first
- AI copilot second
- human resolution on disagreements

The AI layer should enrich and adjudicate edge cases, not replace the
deterministic event-coding baseline.

The product should be understood in three layers:

- public publication layer
  public-safe outputs only
- analyst operations layer
  credentialed review and release control
- private modeling layer
  structural refresh, calibration, and forecasting work

## Workflow Discipline

When a major leap is made in the project, the private workflow should capture it
immediately in writing.

At minimum, record:

- what changed
- what architectural or product decision was taken
- why that decision was taken
- what file contracts or stage boundaries changed
- what run order or commands must now be used
- and, when new variables or fields were introduced, update `data/CODEBOOK.md`
  in the same change set

If a major leap changes the operating sequence, update:

- `docs/user-guide.md`
- `docs/stage-runners.md`
- `docs/private-roadmap.md`
- `docs/private-integration-diagram.md`
- `docs/private-construct-diagram.md`
- `docs/private-process-episode-event-note.md`
- `docs/private-signal-panel-note.md`
- and, when relevant, the private design notes in `docs/`

This is a private operating rule, not a public-facing product requirement.

## Stage Model

### 1. Ingest

Primary files:

- `scripts/run_pipeline.py`
- `scripts/ingest_rss.py`
- `scripts/ingest_newsapi.py`
- `scripts/rss_sources.py`
- `scripts/normalize_articles.py`
- `scripts/ingest_gdelt.py`
- `scripts/historical_ingest.py`

Outputs:

- live event store input data
- review-layer source audit

### 2. Structural Refresh

Primary files:

- `scripts/refresh_vdem.py`
- `scripts/fetch_worldbank.py`
- `scripts/clean_greenbook.py`
- `scripts/clean_eusanct.py`
- `scripts/clean_financial_crises.py`
- `scripts/build_country_year.py`

Outputs:

- `data/cleaned/vdem.json`
- `data/cleaned/vdem.csv`
- `data/cleaned/worldbank.json`
- `data/cleaned/worldbank.csv`
- `data/cleaned/greenbook.json`
- `data/cleaned/greenbook.csv`
- `data/cleaned/eusanct.json`
- `data/cleaned/eusanct.csv`
- `data/cleaned/financial_crises.json`
- `data/cleaned/financial_crises.csv`
- `data/cleaned/country_year.json`
- `data/cleaned/country_year.csv`

This stage is private/internal. It feeds country monitors, calibration, and
future predictive modeling rather than the public dashboard directly.

### 2A. Private Modeling Panel

Primary file:

- `scripts/analysis/build_country_month_panel.py`

Outputs:

- `data/modeling/country_month_panel.json`
- `data/modeling/country_month_panel.csv`
- `data/modeling/country_month_target_audit.json`
- `data/modeling/internal_signal_panel_<country>.json`

This stage remains private/internal. It turns annual structural inputs and
monthly reviewed-event signals into a country-month modeling panel for
calibration and forecasting work.

Current panel scope:

- structural baseline fields
- monthly event-pulse fields
- rolling-window features
- conservative proxy target fields for near-term irregular-transition modeling
- target score/label support fields for those same transition horizons
- benchmark-seed-ready external pressure, economic fragility, and policy-shock
  fields

Useful follow-up runner:

- `scripts/analysis/audit_country_month_targets.py`

Current bridge for external/economic inputs:

- tracked contract:
  - `config/modeling/panel_feature_contract.json`
- tracked benchmark seed:
  - `data/modeling/benchmark_country_month_signals.json`
- local manual seed path:
  - `data/modeling/manual_country_month_signals.local.json`

Future aggregation direction:

- internal logic should move toward:
  - `process -> episode -> event`
- events remain the atomic operational layer
- episodes become the first sequence/aggregation layer
- processes become the higher-order country-risk layer
- schema scaffold:
  - `config/modeling/process_episode_event_schema.json`
- first episode builder:
  - `scripts/analysis/build_episodes.py`
- first episode artifact:
  - `data/modeling/episodes.json`
- those episode features now also feed the private proxy irregular-transition
  target logic in the `country x month` panel, so near-term labels can respond
  to rupture sequences instead of only raw event counts
- private review of those proxy positives now runs through:
  - `scripts/analysis/review_irregular_transition_targets.py`
  - `data/review/irregular_transition_target_review.json`
- remaining `plausible` and `review` cases can now be converted into a
  working adjudication queue:
  - `scripts/analysis/build_adjudication_queue.py`
  - `data/review/adjudication_queue_irregular_transition.json`
- a first selective adjudicated target layer now also exists:
  - `scripts/analysis/build_adjudicated_transition_labels.py`
  - `data/modeling/adjudicated_irregular_transition_labels.json`
- that adjudicated layer currently overrides only the `1m` irregular-transition
  label for narrow benchmark-reviewed cases; everything else stays on the
  episode-aware proxy rule
- current checkpoint:
  - `34` adjudicated `1m` rows across
    `Bolivia`, `Brazil`, `Chile`, `Colombia`, `El Salvador`, `Haiti`,
    `Honduras`, `Mexico`, and `Venezuela`
  - the current adjudication queue is cleared
  - this should now be treated as the first internal adjudicated layer rather
    than expanded casually
- local country-by-country expansion can now flow through:
  - `data/review/adjudicated_transition_decisions.template.json`
  - `data/review/adjudicated_transition_decisions.local.json`
- a stricter gold subset can now also be derived from the reviewed base:
  - `scripts/analysis/build_gold_transition_labels.py`
  - `data/modeling/gold_irregular_transition_labels.json`
- current gold-subset rule:
  - always include `strong`
  - include `reviewed` only when proxy score and note language imply a clearer
    high-severity rupture-type case
  - exclude `reviewed_watch`
- first validation pass against that gold subset now runs through:
  - `scripts/analysis/validate_gold_transition_targets.py`
  - `data/review/gold_irregular_transition_validation.json`
- current first validation checkpoint:
  - fit-path gold recall: `88.0%`
  - fit-path precision against gold: `75.0%`
- implication for fitting:
  - the broader adjudicated `v1` layer should remain operational/internal
  - the gold subset should be treated as the first fit-ready target layer
  - the panel now carries:
    - `irregular_transition_gold_next_1m`
    - `irregular_transition_gold_label_available`
    - `irregular_transition_fit_score_next_1m`
    - `irregular_transition_fit_label_next_1m`
- baseline score validation now also runs through:
  - `scripts/analysis/validate_irregular_transition_baseline.py`
  - `data/review/irregular_transition_baseline_validation.json`
- a second broader political-risk target now also exists at proxy stage:
  - `acute_political_risk_next_1m`
  - `acute_political_risk_next_3m`
  - current proxy version:
    - `proxy_acute_political_risk_v1`
  - current checkpoint:
    - `1m` positives: `51`
    - `3m` positives: `125`
  - first review artifact now also exists:
    - `scripts/analysis/review_acute_political_risk_targets.py`
    - `data/review/acute_political_risk_target_review.json`
  - acute-risk adjudication queue now also exists:
    - `scripts/analysis/build_acute_political_risk_adjudication_queue.py`
    - `data/review/adjudication_queue_acute_political_risk.json`
  - a first adjudicated acute-risk artifact now also exists:
    - `scripts/analysis/build_adjudicated_acute_political_risk_labels.py`
    - `data/modeling/adjudicated_acute_political_risk_labels.json`
  - current adjudication checkpoint:
    - queue empty
    - first reviewed layer frozen as:
      - `acute political risk adjudicated layer v1`
  - a stricter acute-risk gold subset can now also be derived from:
    - `scripts/analysis/build_gold_acute_political_risk_labels.py`
    - `data/modeling/gold_acute_political_risk_labels.json`
  - first validation against that acute-risk gold subset now also runs through:
    - `scripts/analysis/validate_gold_acute_political_risk_targets.py`
    - `data/review/gold_acute_political_risk_validation.json`
  - the acute-risk benchmark layer can now also be tiered through:
    - `scripts/analysis/build_acute_political_risk_benchmark_tiers.py`
    - `data/modeling/acute_political_risk_benchmark_tiers.json`
  - acute-risk tier separation can now also be audited through:
    - `scripts/analysis/audit_acute_political_risk_tier_separation.py`
    - `data/review/acute_political_risk_tier_separation.json`
  - protest-heavy acute-risk benchmark cases can now also be reviewed through:
    - `scripts/analysis/review_acute_political_risk_protest_cases.py`
    - `data/review/acute_political_risk_protest_review.json`
  - the acute-risk benchmark can now also be refined through:
    - `scripts/analysis/build_acute_political_risk_benchmark_refinement_queue.py`
    - `data/review/acute_political_risk_benchmark_refinement_queue.json`
    - with optional local decisions in:
      - `data/review/acute_political_risk_benchmark_refinement_decisions.local.json`
  - the acute-risk fit-ready sample can now also be built through:
    - `scripts/analysis/build_acute_political_risk_fit_dataset.py`
    - `data/modeling/acute_political_risk_fit_dataset.json`
  - the first acute-risk baseline validation now also runs through:
    - `scripts/analysis/validate_acute_political_risk_baseline.py`
    - `data/review/acute_political_risk_baseline_validation.json`
  - the first acute-risk model comparison now also runs through:
    - `scripts/analysis/validate_acute_political_risk_models.py`
    - `data/review/acute_political_risk_model_validation.json`
  - current tiered acute-risk benchmark:
    - gold positives: `22`
    - hard negatives: `18`
    - easy negatives: `22`
  - current feature-separation read:
    - hard negatives are more contestation-heavy than gold positives
  - protest-specific panel fields now also exist:
    - `protest_acute_signal_score`
    - `protest_background_load_score`
  - current stance on those protest fields:
    - keep them as interpretive inputs for now
    - the first direct scoring use increased false positives and was backed out
  - current next-stage emphasis:
    - refine the benchmark before adding more acute-risk features
    - start with the highest-priority hard negatives in the refinement queue
  - latest refinement checkpoint:
    - all active acute-risk benchmark refinement rows have now been reviewed
    - the active refinement queue is now `0`
    - the acute-risk benchmark refinement layer can be treated as frozen `v1`
  - latest acute-risk refinement preserved recall while trimming overfire modestly
  - current acute-risk gold validation checkpoint:
    - recall: `100.0%`
    - precision: `45.833%`
    - current problem is specificity rather than missed gold cases
  - current acute-risk baseline checkpoint on the reviewed fit-ready sample:
  - a first construct-oriented benchmark-refinement pass now also exists for:
    - `security_fragmentation_jump_next_3m`
    - current proxy version:
      - `proxy_security_fragmentation_jump_v2`
    - first review artifact:
      - `scripts/analysis/review_security_fragmentation_jump_targets.py`
      - `data/review/security_fragmentation_jump_target_review.json`
    - current review checkpoint:
      - reviewed positives across the first benchmark-country set: `234`
    - adjudication queue:
      - `scripts/analysis/build_security_fragmentation_jump_adjudication_queue.py`
      - `data/review/adjudication_queue_security_fragmentation_jump.json`
      - first queue size: `111`
      - remaining queue after the first reviewed batch: `108`
    - local adjudication path:
      - `data/review/adjudicated_security_fragmentation_jump_decisions.local.json`
    - adjudicated-label builder:
      - `scripts/analysis/build_adjudicated_security_fragmentation_jump_labels.py`
    - adjudicated-label artifact:
      - `data/modeling/adjudicated_security_fragmentation_jump_labels.json`
    - first adjudication checkpoint:
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
      - queue is now `0`
      - this layer can now be treated as:
        - `security fragmentation jump adjudicated layer v1`
    - a stricter gold subset can now also be derived from:
      - `scripts/analysis/build_gold_security_fragmentation_jump_labels.py`
      - `data/modeling/gold_security_fragmentation_jump_labels.json`
    - first validation against that gold subset now also runs through:
      - `scripts/analysis/validate_gold_security_fragmentation_jump_targets.py`
      - `data/review/gold_security_fragmentation_jump_validation.json`
    - current gold checkpoint:
      - gold rows: `36`
      - recall: `100.0%`
      - precision against gold: `10.976%`
    - current read:
      - the proxy is catching clean gold cases
      - the main problem is specificity rather than misses
    - the benchmark layer can now also be tiered through:
      - `scripts/analysis/build_security_fragmentation_jump_benchmark_tiers.py`
      - `data/modeling/security_fragmentation_jump_benchmark_tiers.json`
    - tier separation can now also be audited through:
      - `scripts/analysis/audit_security_fragmentation_jump_tier_separation.py`
      - `data/review/security_fragmentation_jump_tier_separation.json`
    - current tiered benchmark:
      - gold positives: `36`
      - hard negatives: `14`
      - easy negatives: `20`
    - current feature-separation read:
      - the main positive separator is:
        - `security_fragmentation_jump_signal_score_next_3m`
      - the main hard-negative separators are:
        - `transition_rupture_precursor_score`
        - `transition_contestation_load_score`
    - current interpretation:
      - hard negatives are more contestation-heavy than clean gold fragmentation jumps
      - the next refinement problem remains specificity rather than recall
    - latest refinement read:
      - the `v2` contestation-discount pass did not materially change the
        benchmark metrics
      - remaining overfire likely needs a stronger structural redesign rather
        than a small penalty tweak
    - sample rows: `61`
    - threshold `4` currently gives:
      - precision: `100.0%`
      - recall: `100.0%`
      - specificity: `100.0%`
    - this still holds after the benchmark refinement layer was frozen as `v1`
  - current acute-risk model-comparison result:
    - threshold baseline still wins
    - leave-one-out logistic:
      - precision: `84.615%`
      - recall: `100.0%`
      - specificity: `89.744%`
    - logistic fails hardest on `hard_negative`
  - current first review burden is heaviest in:
    - `Colombia`
    - `Venezuela`
    - `Haiti`
    - `El Salvador`
- current baseline result on the reviewed fit-ready sample:
  - fit-path recommended threshold: `2`
  - threshold `2` yields:
    - precision: `74.194%`
    - recall: `92.0%`
    - specificity: `79.487%`
  - threshold `4` remains the stricter high-specificity cut:
    - precision: `100%`
    - recall: `88.0%`
    - specificity: `100%`
- first fit comparison now also runs through:
  - `scripts/analysis/validate_irregular_transition_models.py`
  - `data/review/irregular_transition_model_validation.json`
- current first fit-comparison result:
  - threshold baseline:
    - precision: `100%`
    - recall: `88.0%`
  - leave-one-out logistic baseline:
    - precision: `46.875%`
    - recall: `60.0%`
  - tiered benchmark read:
    - under the current `proxy_irregular_transition_v6` rule:
      - `threshold 2` is the best reviewed-sample F1 cut
      - `threshold 4` remains a strict high-specificity cut
    - logistic baseline struggles most on `hard_negative`
      - hard-negative specificity: `30.0%`
    - tier-separation audit now suggests the clearest current contrasts are:
      - higher `transition_contestation_load_score` in `hard_negative`
      - more negative `transition_specificity_gap` in `hard_negative`
      - the new `transition_rupture_precursor_score` alone is not enough
        yet
  - current conclusion:
    - keep the stricter fit-path threshold baseline as the operative
      pre-training benchmark
    - keep the broader watch-path for analyst-facing rupture-watch coverage
    - the latest fit-path refinements lifted stricter-threshold gold recall
      from `60.0%` to `88.0%` without weakening hard-negative specificity
    - the remaining missed gold cases are now documented in:
      - `docs/private-el-salvador-fit-interpretation-note.md`
    - current interpretation:
      - leave the El Salvador residual cases as watch-relevant reviewed
        positives unless stronger rupture-specific evidence is added
    - the next useful feature work should focus on rupture-vs-contestation
      separation, not general model complexity
    - the expanded `1960-2025` structural feature set improved fitted-model
      recall relative to the earlier pass, but it still does not beat the
      threshold rule on the reviewed sample
    - the `v6` rupture-sequence adjustment restored some benchmark-positive
      rupture-watch months, but it also reduced recall at the stricter
      `threshold 4` cut
- fit-sample audit now runs through:
  - `scripts/analysis/audit_irregular_transition_fit_sample.py`
  - `data/review/irregular_transition_fit_sample_audit.json`
- a reviewed-negative expansion queue now also exists:
  - `scripts/analysis/build_irregular_transition_negative_queue.py`
  - `data/review/irregular_transition_negative_queue.json`
- a hard-negative benchmark queue now also exists:
  - `scripts/analysis/build_irregular_transition_hard_negative_queue.py`
  - `data/review/irregular_transition_hard_negative_queue.json`
- a tiered benchmark reference set now also exists:
  - `scripts/analysis/build_irregular_transition_benchmark_tiers.py`
  - `data/modeling/irregular_transition_benchmark_tiers.json`
- local reviewed-negative expansion can flow through:
  - `data/review/reviewed_negative_decisions.template.json`
  - `data/review/reviewed_negative_decisions.local.json`
- baseline and model-validation runners now automatically absorb those local
  reviewed negatives when present
- current reviewed-negative checkpoint:
  - `28` local reviewed negatives have already been added
  - the fit-ready sample now has `64` rows
  - `8` hard benchmark negatives have now been promoted into the reviewed sample:
    - `Colombia 2020-08-01`
    - `Colombia 2021-04-01`
    - `Mexico 2020-08-01`
    - `Colombia 2022-10-01`
    - `Mexico 2024-09-01`
    - `Peru 2022-11-01`
    - `Ecuador 2023-08-01`
    - `Ecuador 2023-09-01`
  - reviewed-negative country coverage increased to all `25` countries
  - tiered benchmark set now stands at:
    - `25` gold positives
    - `10` hard negatives
    - `18` easy negatives
- current next-step implication:
  - expand reviewed negatives across more countries
  - add lower-intensity reviewed negatives
  - then revisit fitted-model comparisons

Future internal monitoring layer:

- a private/internal signal panel should sit between raw events and higher-order
  episode/process reasoning
- signal-panel spec:
  - `config/modeling/internal_signal_panel_spec.json`
- first builder:
  - `scripts/analysis/build_internal_signal_panel.py`

Private external/economic signal layer:

- builder:
  - `scripts/analysis/build_external_economic_signals.py`
- artifact:
  - `data/modeling/external_economic_country_month.json`
- role:
  - supplies monthly external-pressure and economic-signal fields to the
    private `country x month` panel before benchmark/manual seed overrides
  - now combines event-derived pulse logic with macro baselines carried from
    `data/cleaned/country_year.json`
  - now also draws on structured US assistance, sanctions, and crisis datasets
    when those cleaned artifacts are present
  - latest country-month signals now also feed directly into the layered
    country constructs in `scripts/analysis/build_country_monitors.py`, so the
    published monitor architecture can absorb external and macro stress without
    collapsing everything into one top-line score
  - the country-construct layer now also uses a derived `security_governance_gap`
    logic to distinguish weak, fragmented security environments from cases of
    straightforward militarization
- benchmark review:
  - `scripts/analysis/review_external_economic_signals.py`
  - `data/review/external_economic_signal_review.json`
- first private viewer:
  - `apps/internal-tools/signal-panel.html`

Private episode layer:

- builder:
  - `scripts/analysis/build_episodes.py`
- artifact:
  - `data/modeling/episodes.json`
- role:
  - clusters reviewed events into bounded episodes so the private modeling
    layer can begin to use sequence logic rather than only raw event totals
  - now feeds first episode features into:
    - `data/modeling/country_month_panel.json`

### 3. Review Diagnostics

Primary files:

- `scripts/qa/run_qa.py`
- `scripts/qa/run_registry_qa.py`
- `scripts/pipeline/detect_duplicates.py`
- `scripts/review/build_review_queue.py`
- `scripts/review/apply_analyst_edits.py`

Outputs:

- `data/review/qa_report.json`
- `data/review/registry_qa_report.json`
- `data/review/duplicate_candidates.json`
- `data/review/review_queue.json`
- `data/review/edits.local.json`
- `data/review/events_with_edits.json`
- `data/review/review_queue_with_edits.json`

### 4. Canonicalize

Primary files:

- `scripts/pipeline/classify_events.py`
- `scripts/pipeline/build_canonical_events.py`
- `scripts/pipeline/code_actors.py`
- `scripts/pipeline/update_actor_registry.py`

Outputs:

- `data/canonical/events.json`
- `data/canonical/events.jsonl`
- `data/canonical/events_actor_coded.json`
- `data/canonical/events_actor_coded.jsonl`
- `data/canonical/actor_mentions.json`
- `config/actors/nsva_registry_seed.json`
- `config/actors/broad_actor_registry_seed.json`
- `config/actors/actor_registry.json`

Actor coding now follows a four-level hierarchy:

- `actor_category`
  broad class such as `state_actor` or `non_state_actor`
- `actor_group`
  branch such as `military`, `executive`, `civil_society`, `economic_group`, or `armed_non_state_actor`
- `actor_type`
  specific class such as `state_security_force`, `state_institution`, `armed_group`, or `organized_crime`
- `actor_subtype`
  finer subtype such as `cartel`, `insurgent`, or `dissident_faction`

This keeps organized crime in the right place:

- `actor_category = non_state_actor`
- `actor_group = armed_non_state_actor`
- `actor_type = organized_crime`

The durable registry is now seeded from modular inputs:

- `config/actors/nsva_registry_seed.json`
  named organized-crime and armed non-state actors
- `config/actors/broad_actor_registry_seed.json`
  reusable state, civil-society, economic, media, protest, and international actors
- `config/actors/actor_registry.json`
  merged durable registry plus analyst-reviewed promotions

### 5. Publish

Primary file:

- `scripts/publish/publish_dashboard_data.py`

Output:

- `data/published/events_public.json`

The published payload is public-safe and now carries review-state metadata for
the dashboard:

- `review_status`
- `review_priority`
- `human_validated`
- `provenance_summary.reviewed_by_human`

Private analyst fields such as `analyst_reasoning`, detailed review notes, and
local credential data remain outside the published layer.

Publication policy is now explicit:

- low-confidence events require human corroboration before publication
- merged duplicates are withheld
- records in blocked review states such as `flagged`, `needs_revision`, and
  `rejected` are withheld

### 6. Council Analysis

Primary file:

- `scripts/analysis/run_council.py`

Output:

- `data/review/council_analyses.json`

Council analysis now runs across every event, not only reviewed events, but the
resulting records are explicitly labeled as `AI-generated analysis`.

The council no longer assumes that every event needs equal treatment from the
same fixed bundle of analysts. Lens activation is now conditional on event
type, actor mix, and likely mechanism, and the resulting output stores analyst
weights plus activation reasons.

The current substantive lenses are:

- `Military`
- `Political`
- `Security`

These public-facing analyst labels map directly to the core construct logic:

- `Military`
  - military / civil-military dimension
- `Political`
  - `regime_vulnerability`
- `Security`
  - `security_fragmentation`

The council now also supports two conditional specialist lenses:

- `International`
  - external pressure, foreign alignment, sanctions, and multilateral leverage
- `Economist`
  - economic fragility, policy shock, and macro-political spillovers

The event taxonomy is now also construct-aware rather than purely operational.
Canonical and published event records carry:

- `docs/event-taxonomy-reference.md`
  - generated reference for the current `type -> category -> subcategory`
    structure
- `event_category`
  - broad analytical family such as `political`, `military`, `security`, or
    `international`
- `event_subcategory`
  - narrower mechanism bucket
- `event_construct_destinations`
  - which higher-order constructs the event most directly informs
- `event_analyst_lenses`
  - which analyst lenses should normally interpret the event first

The canonical builder also now applies a lightweight taxonomy-enrichment pass
for `other` events so they do not remain a single residual bucket when the
headline and article context clearly point to mechanisms such as:

- diplomatic pressure and external alignment
- judicial and accountability shocks
- electoral contestation and realignment
- institutional drift and leadership projects
- macro stress and policy shock

The same mechanism-first approach now also extends across the remaining event
families, so higher-volume categories no longer depend only on the top-level
type label. Examples now include:

- `oc`
  - trafficking logistics and route shifts
  - criminal violence and social control
  - criminal interdiction and state response
- `peace`
  - peace-process electoral stress
  - transitional justice and accountability
  - peace-process breakdown and spoilers
- `coop`
  - operational security cooperation
  - foreign training and advisory presence
  - regional security alignment and strategy
- `coup`, `purge`, `aid`, `protest`, `reform`, `exercise`, and `conflict`
  - now also carry more mechanism-specific subcategories instead of only the
    earlier generic construct bucket

Whenever `config/taxonomy/event_types.json` changes, regenerate the markdown
reference so the public taxonomy structure stays current:

```bash
python3 scripts/analysis/update_event_taxonomy_reference.py
```

The council layer is informed by structured analyst knowledge assets:

- `config/agents/analyst_knowledge.json`
- `config/agents/council_guidance.json`
- `config/agents/council_roles.json`
- `config/agents/ai_workers.json`

The council also now uses article-context snippets from the canonical article
catalog so public-facing and analyst-facing interpretation is based on more
than the event title alone.

The council prose is now also tied more explicitly to `event_subcategory`, so
the public analytical writing can explain mechanisms more concretely instead of
repeating the same top-level event-type language across very different cases.

Public analysis now also uses a second layer:

- the structured council output remains the internal reasoning layer
- a simpler public prose renderer rewrites that structure into shorter,
  more natural language for publication

That public prose stage is currently deterministic and rule-based. A future API
rewrite stage can be added later for additional editorial polish, but it should
remain downstream of the structured council output rather than replacing it.

The worker registry makes the AI-first architecture more explicit. It separates
routine automation into named roles such as:

- event classifier
- actor coder
- duplicate analyst
- QA scorer
- publication policy agent
- council analysts

## Emerging Country Monitor Layer

SENTINEL now has an experimental layered country-monitor system built on
`baseline + pulse` logic.

Design references:

- `docs/baseline-pulse-design.md`
- `config/baseline_pulse_model.json`

Current logic:

- `baseline`
  slower-moving structural context such as militarization, public-security role,
  conflict exposure, and external alignment
- `pulse`
  recent movement derived from event salience, confidence, recency, and human
  validation state

Country and regional surfaces can now expose:

- baseline score
- pulse score
- composite monitor
- higher-order risk constructs
- trend label
- predictive summary

This should remain interpretable and support the event model, not replace it.

First implementation path:

- `scripts/analysis/build_country_monitors.py`

Current output:

- `data/published/country_monitors.json`
- `data/review/country_monitor_validation.json`

Private modeling references:

- `docs/private-integration-diagram.md`
- `docs/private-construct-diagram.md`
- `docs/private-country-month-model-note.md`

This builder is still experimental. It uses available structural data plus
recent event activity, then aggregates those monitor families into country-level
constructs like regime vulnerability, militarization, and security
fragmentation. Missing structural coverage is reported explicitly rather than
hidden behind false precision. The current scaffold also applies an
anchor-country calibration pass so construct scores sit closer to regional
expert judgment. The militarization construct now also draws on explicit
country mission-role profiles so governance and domestic-security tasks carried
out by the armed forces shape the score directly. A separate validation runner
now compares those outputs against benchmark country ranges so calibration work
can be tracked explicitly instead of judged informally. The builder also
backfills the latest non-null structural values by field when the newest
country-year row is only a partial shell, which is especially important for
governance and democracy indicators that lag the calendar year.

This layer should stay conceptually distinct from the public product:

- selected summaries may appear in the public dashboard
- the validation and calibration artifacts remain internal
- future forecasting and country-month panels belong to the private modeling layer

## Data-Layer Contract

### `data/staging/`

Machine-generated intermediates. Not analyst reviewed.

Current staging artifacts include:

- `data/staging/raw_articles.json`
- `data/staging/filtered_articles.json`
- `data/staging/event_article_links.json`

### `data/review/`

Operational artifacts for analyst workflow and QA prioritization.

This layer now also holds human edit persistence and clearance-aware review state.
It is also where analysts can reverse high-consequence actions without deleting
the audit trail, such as undoing duplicate decisions, undoing QA resolutions, or
restoring rejected and publication-facing decisions.

### `data/canonical/`

Schema-aligned event and actor layers used for internal analysis and review.
These records now include a structured provenance timeline under
`provenance.timeline`.

The canonical builder also emits first-pass source/report linkage assets:

- `data/canonical/articles.json`
- `data/canonical/event_article_links.json`

It now also preserves `deed_type` as a first-class event field rather than only
as upstream metadata, so institutional-erosion signals can survive into the
actor-coded and review layers.

These are derived from merged source and URL arrays in the live event store and
serve as the current bridge between clustered events and the underlying reports
that produced them.

### `data/published/`

Public-safe outputs intended for the dashboard and other read-only surfaces.

This layer should not contain:

- local credentials
- analyst edits
- raw QA or duplicate workflow internals
- private council traces
- private modeling panels or calibration notes

### `data/cleaned/`

Slow-moving structural refresh artifacts used for country monitoring and future
modeling.

Examples:

- `data/cleaned/vdem.json`
- `data/cleaned/worldbank.json`
- `data/cleaned/greenbook.json`
- `data/cleaned/country_year.json`

Coverage rule:

- operational monitoring remains anchored to the project window of
  `1990-present`
- private training and calibration may still use earlier structural
  country-year history when it exists and is judged comparable enough
- that deeper history should be treated as `training-history coverage`, not as
  a silent extension of the live monitoring window

### `data/modeling/`

Reserved for future private modeling artifacts such as:

- country-month panels
- target-label tables
- model-validation outputs
- model comparison and feature-importance reports

Coverage distinction inside the modeling layer:

- `product coverage window`
  - the operational/live window used for monitoring and dashboard-facing
    interpretation
- `training-history window`
  - a deeper private-only structural history window that can extend earlier
    when useful for model fitting, priors, and long-run legacy features
- current audit runner for whether that deeper history is actually present in
  the merged layer:
  - `scripts/analysis/audit_training_history_coverage.py`
  - `data/review/training_history_coverage_audit.json`
- upstream audit runner for whether the current lower bound is a source limit
  or a runner/build limit:
  - `scripts/analysis/audit_upstream_training_sources.py`
  - `data/review/upstream_training_source_audit.json`

## Review Queue Logic

The review queue combines:

- event salience
- QA flags
- duplicate uncertainty
- upstream AI-worker supervision signals
- council-recommended analyst actions

This is an intervention queue, not the main production path. It is meant to
surface the subset of cases where human attention is most useful.

## Analyst Clearance Model

The analyst console now assumes three review tiers:

- `RA`
- `Analyst`
- `Coordinator`

These tiers are defined in `data/review/edits.local.json` during local operations, with `data/review/edits.template.json` providing the committed safe template. The current static console enforces them in the browser by disabling out-of-scope fields. The repo-side apply step enforces the same model when edits are materialized into review-layer outputs.

The intended role split is:

- `RA`: summary cleanup, review notes, actor coding cleanup
- `Analyst`: core event coding plus actor coding plus intermediate review states
- `Coordinator`: final approval and downstream-ready review states

These roles supervise AI output rather than replacing it with manual coding by
default.

Actor follow-up is part of this supervision loop. Analysts can create actors,
mark them uncertain, add aliases and relationship tags, and move them through a
lightweight registry workflow:

- `needs_registry_entry`
- `registry_seeded`
- `registry_confirmed`

The analyst console now also supports bulk actor follow-up actions in the
`Actor Registry` queue so reviewers can seed or confirm registry status and
clear actor uncertainty across multiple selected events without opening every
record one by one. Registry QA issues can then be resolved from the same
workspace by merging duplicate registry entries or dropping a conflicting alias
from one entry without forcing a full merge.

The workflow bridge from review to durable knowledge is
`scripts/pipeline/update_actor_registry.py`, which promotes reviewed actor
records into `config/actors/actor_registry.json`.

## Edit Persistence Workflow

Because the analyst console is still static, edit persistence happens in two steps:

1. Analysts make edits in the browser and save local drafts.
2. Analysts export the combined payload back into `data/review/edits.local.json`.
3. The repo applies those edits with `scripts/review/apply_analyst_edits.py`.

This keeps the workflow file-based for now while preserving a clean transition
path toward a future authenticated backend. The larger design goal remains
AI-first production with targeted human intervention.

## Local Authenticated Analyst Server

SENTINEL now includes a small local authenticated server:

- `scripts/review/run_analyst_server.py`

This server:

- serves the repo as a local web root
- handles analyst login and session state
- enforces role-based edit permissions
- writes analyst edits directly into `data/review/edits.local.json`
- reruns `scripts/review/apply_analyst_edits.py` after successful saves

Credential data lives in:

- `data/review/users.local.json`

This remains a local operations tool, not a production deployment path.

## Near-Term Target

The next version of SENTINEL should behave like this:

1. run ingest
2. generate QA, duplicates, and review queue
3. assemble canonical events
4. enrich actors
5. generate AI council analysis
6. expose review artifacts in the analyst console
7. publish a public-safe dataset

This is the shift from a script collection to a system.
