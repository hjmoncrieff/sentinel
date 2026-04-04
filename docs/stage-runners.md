# SENTINEL Stage Runners

This document lists the executable stage runners in SENTINEL and the command
used to run each one.

It is the command reference. For the daily operational sequence, use
`docs/user-guide.md`.

## Documentation Sync

### Refresh Obsidian documentation mirror

```bash
python3 scripts/sync_obsidian_docs.py
```

This mirrors the project documentation set into:

- `/Users/hjmoncrieff/Library/CloudStorage/Dropbox/MyObsidiainVault/Sentinel Documentation`

## Ingest

Source-expansion planning note:

- `docs/private-source-expansion-note.md`

### Fast monitoring pipeline

Primary orchestrator:

```bash
python3 scripts/run_pipeline.py
```

Use this for the default non-GDELT monitoring run.

Legacy compatibility path:

```bash
python3 scripts/fetch_events.py
```

This wrapper is retired and should not be the normal command.

### Fast monitoring pipeline with GDELT

```bash
python3 scripts/run_pipeline.py --gdelt
```

Use this when you want the normal pipeline plus live GDELT enrichment.

### Historical/backfill mode through the main pipeline

```bash
python3 scripts/run_pipeline.py --since 2025-01-01
```

Or:

```bash
python3 scripts/run_pipeline.py --backfill --years 5
```

Use this only for bounded backfill through the current source layer. It is not
the same as a true 2000+ historical archive pipeline.

### RSS and archive ingestion module

Current status:

- `scripts/ingest_rss.py` is a module used by `scripts/run_pipeline.py`
- it does not yet expose a standalone CLI entry point

Execution path:

```bash
python3 scripts/run_pipeline.py
```

### NewsAPI ingestion module

Current status:

- `scripts/ingest_newsapi.py` is a module used by `scripts/run_pipeline.py`
- it does not yet expose a standalone CLI entry point

Execution path:

```bash
python3 scripts/run_pipeline.py
```

### Standalone GDELT

```bash
python3 scripts/ingest_gdelt.py
```

Conservative mode:

```bash
python3 scripts/ingest_gdelt.py --conservative
```

### Historical GDELT

```bash
python3 scripts/ingest_gdelt.py --historical --since 2025-01-01
```

This path now retries with backoff when GDELT returns `429 Too Many Requests`,
but it should still be treated as a slower, rate-limit-sensitive workflow.

Conservative historical mode:

```bash
python3 scripts/ingest_gdelt.py --historical --since 2025-01-01 --conservative
```

Resume a historical run from checkpoint:

```bash
python3 scripts/ingest_gdelt.py --historical --since 2025-01-01 --resume
```

Resume in conservative off-hours mode:

```bash
python3 scripts/ingest_gdelt.py --historical --since 2025-01-01 --resume --conservative --off-hours
```

Set a stricter rate-limit cutoff:

```bash
python3 scripts/ingest_gdelt.py --conservative --max-backoff-seconds 45
```

Clear the saved checkpoint:

```bash
python3 scripts/ingest_gdelt.py --clear-checkpoint
```

### Historical ingestion planner

```bash
python3 scripts/historical_ingest.py --since 2000-01-01
```

Inspect the plan as JSON:

```bash
python3 scripts/historical_ingest.py --since 2000-01-01 --json
```

## Structural Refresh

### Refresh cleaned V-Dem layer

```bash
python3 scripts/refresh_vdem.py
```

This Python runner refreshes `data/cleaned/vdem.json` and `data/cleaned/vdem.csv`
through the locally installed V-Dem data package.

### Refresh World Bank layer

```bash
python3 scripts/fetch_worldbank.py
```

### Refresh Greenbook assistance layer

```bash
python3 scripts/clean_greenbook.py
```

### Clean EUSANCT sanctions layer

```bash
python3 scripts/clean_eusanct.py
```

### Clean financial crises layer

```bash
python3 scripts/clean_financial_crises.py
```

### Rebuild country-year structural join

```bash
python3 scripts/build_country_year.py
```

### Build broader actor seed

```bash
python3 scripts/pipeline/build_broad_actor_registry_seed.py
```

Use this to refresh the reusable state, civil-society, economic, media,
protest, and international actor seed module before rebuilding the durable
actor registry.

## Future AI Copilot Stage

This stage is documented but not yet part of the production pipeline.

Planned runner:

```bash
python3 scripts/analysis/run_ai_classification_copilot.py
```

Intended purpose:

- second-pass AI review of ambiguous event classifications
- structured proposals for taxonomy refinement
- disagreement routing into human review

## Private Modeling Layer

### Build country-month modeling panel

```bash
python3 scripts/analysis/build_country_month_panel.py
```

Use this to create the private/internal `country x month` modeling panel that
joins structural annual data with monthly event-derived pulse features.

### Build internal episode layer

```bash
python3 scripts/analysis/build_episodes.py
```

Use this to build the first private/internal episode artifact from reviewed
events so the modeling layer can start using bounded sequences instead of only
raw event totals.

### Build external/economic month signals

```bash
python3 scripts/analysis/build_external_economic_signals.py
```

Use this to build the private/internal monthly external-pressure and
economic-signal layer that the country-month panel now consumes.

Optional private/local seed path for external and economic month signals:

- copy `data/modeling/manual_country_month_signals.template.json`
  to `data/modeling/manual_country_month_signals.local.json`
- populate country-month values locally
- rebuild the panel with the same runner above

### Audit country-month proxy targets

```bash
python3 scripts/analysis/audit_country_month_targets.py
```

Use this to inspect class balance, coverage windows, and country/year
distribution for the current proxy target fields.

### Review irregular-transition proxy positives

```bash
python3 scripts/analysis/review_irregular_transition_targets.py
```

Use this to review the current proxy irregular-transition positives country by
country and separate strong, plausible, and weak cases before moving toward
adjudicated targets.

### Review acute political-risk proxy positives

```bash
python3 scripts/analysis/review_acute_political_risk_targets.py
```

Use this to review the broader acute political-risk proxy positives country by
country and separate strong, plausible, review, and weak cases before moving
toward adjudicated targets.

### Build adjudicated irregular-transition labels

```bash
python3 scripts/analysis/build_adjudicated_transition_labels.py
```

Use this to promote a narrow set of reviewed benchmark positives into a tracked
private adjudicated label layer that can override the `1m` proxy target where
we have already made an internal benchmark decision.

### Build gold irregular-transition subset

```bash
python3 scripts/analysis/build_gold_transition_labels.py
```

Use this to derive a stricter gold subset from the broader adjudicated layer
for higher-confidence validation and future model-fitting work.

### Validate against gold irregular-transition subset

```bash
python3 scripts/analysis/validate_gold_transition_targets.py
```

Use this to measure how the stricter fit-path target layer performs against the
gold subset before any first model fit.

### Build irregular-transition fit dataset

```bash
python3 scripts/analysis/build_irregular_transition_fit_dataset.py
```

Use this to materialize the reviewed fit-ready sample as a dedicated modeling
artifact built from gold positives plus reviewed negatives, using the stricter
fit-path fields in the panel.

### Validate baseline irregular-transition score

```bash
python3 scripts/analysis/validate_irregular_transition_baseline.py
```

Use this to validate the current signal-score baseline against the reviewed
fit-ready sample built from gold positives and reviewed-watch / weak negatives.
This runner now uses the stricter fit-path fields in the panel rather than the
broader internal rupture-watch fields.

### Compare first irregular-transition fit models

```bash
python3 scripts/analysis/validate_irregular_transition_models.py
```

Use this to compare the current threshold baseline against a first leave-one-out
logistic-regression model on the reviewed fit-ready sample. The current feature
set now includes both event/episode features and the expanded historical-memory
structural layer from the `1960-2025` country-year panel. This runner also uses
the stricter fit-path signal fields rather than the broader watch-path fields.

### Build irregular-transition negative review queue

```bash
python3 scripts/analysis/build_irregular_transition_negative_queue.py
```

Use this to generate lower-intensity and background candidate negatives that
can broaden the fit-ready sample beyond severe-vs-severe reviewed cases.

### Build irregular-transition hard-negative benchmark queue

```bash
python3 scripts/analysis/build_irregular_transition_hard_negative_queue.py
```

Use this to isolate the small set of difficult reviewed-negative candidates
that still look transition-like because of episode or historical-memory
signals.

### Build tiered irregular-transition benchmark set

```bash
python3 scripts/analysis/build_irregular_transition_benchmark_tiers.py
```

Use this to consolidate the benchmark reference layer into:

- `gold_positive`
- `hard_negative`
- `easy_negative`

### Audit irregular-transition tier separation

```bash
python3 scripts/analysis/audit_irregular_transition_tier_separation.py
```

Use this to compare `gold_positive` vs `hard_negative` benchmark tiers and
identify which features best separate true rupture cases from
contestation-heavy near misses.

### Build irregular-transition adjudication queue

```bash
python3 scripts/analysis/build_adjudication_queue.py
```

Use this to turn the target-review artifact into a cleaner working queue of
`plausible` and `review` cases that still need country-by-country adjudication.

### Build acute political-risk adjudication queue

```bash
python3 scripts/analysis/build_acute_political_risk_adjudication_queue.py
```

Use this to turn the acute-political-risk review artifact into a cleaner
working queue of `plausible` and `review` cases that still need
country-by-country adjudication.

### Build adjudicated acute political-risk labels

```bash
python3 scripts/analysis/build_adjudicated_acute_political_risk_labels.py
```

Use this to promote a narrow set of reviewed benchmark acute-risk positives
into a tracked private adjudicated label layer while leaving the broader proxy
target in place.

### Review security-fragmentation-jump positives

```bash
python3 scripts/analysis/review_security_fragmentation_jump_targets.py
```

Use this to review the first construct-oriented security-fragmentation-jump
proxy positives country by country before adjudication.

### Build security-fragmentation-jump adjudication queue

```bash
python3 scripts/analysis/build_security_fragmentation_jump_adjudication_queue.py
```

Use this to turn the security-fragmentation-jump review artifact into a
country-by-country working adjudication queue of `plausible` and `review`
cases.

### Build adjudicated security-fragmentation-jump labels

```bash
python3 scripts/analysis/build_adjudicated_security_fragmentation_jump_labels.py
```

Use this to promote a narrow reviewed batch of construct-oriented
security-fragmentation-jump cases into a tracked private adjudicated label
layer.

### Build gold security-fragmentation-jump subset

```bash
python3 scripts/analysis/build_gold_security_fragmentation_jump_labels.py
```

Use this to derive a stricter gold subset from the adjudicated
security-fragmentation-jump layer for higher-confidence validation and future
fitting.

### Validate against gold security-fragmentation-jump subset

```bash
python3 scripts/analysis/validate_gold_security_fragmentation_jump_targets.py
```

Use this to compare the current security-fragmentation-jump proxy against the
stricter gold subset before any future fitted-model work.

### Build security-fragmentation-jump benchmark tiers

```bash
python3 scripts/analysis/build_security_fragmentation_jump_benchmark_tiers.py
```

Use this to consolidate the reviewed fragmentation-jump benchmark material into
`gold_positive`, `hard_negative`, and `easy_negative` tiers.

### Audit security-fragmentation-jump tier separation

```bash
python3 scripts/analysis/audit_security_fragmentation_jump_tier_separation.py
```

Use this to compare gold fragmentation-jump cases against hard negatives and
identify which features best separate clean construct jumps from broad
fragmentation-heavy overfire.

### Build gold acute political-risk subset

```bash
python3 scripts/analysis/build_gold_acute_political_risk_labels.py
```

Use this to derive a stricter acute-risk gold subset from the broader reviewed
acute political-risk layer for higher-confidence validation and future fitting.

### Validate against gold acute political-risk subset

```bash
python3 scripts/analysis/validate_gold_acute_political_risk_targets.py
```

Use this to measure how the broader acute political-risk target layer performs
against the acute-risk gold subset before any first acute-risk model fit.

### Build tiered acute political-risk benchmark set

```bash
python3 scripts/analysis/build_acute_political_risk_benchmark_tiers.py
```

Use this to consolidate the acute-risk benchmark reference layer into:

- `gold_positive`
- `hard_negative`
- `easy_negative`

### Audit acute political-risk tier separation

```bash
python3 scripts/analysis/audit_acute_political_risk_tier_separation.py
```

Use this to compare `gold_positive` vs `hard_negative` acute-risk tiers and
identify which features best separate true acute deterioration from broad
stress overfire.

### Review protest-heavy acute political-risk benchmark cases

```bash
python3 scripts/analysis/review_acute_political_risk_protest_cases.py
```

Use this to inspect how protest-heavy months behave inside the acute-risk
benchmark tiers. This runner is especially useful now that the panel carries
`protest_acute_signal_score` and `protest_background_load_score`, but those
fields are still interpretive rather than directly score-driving.

### Build acute political-risk benchmark refinement queue

```bash
python3 scripts/analysis/build_acute_political_risk_benchmark_refinement_queue.py
```

Use this to shift the acute-risk workflow from feature invention to benchmark
refinement. It prioritizes the benchmark rows that most deserve closer review,
especially protest-linked near misses, high-severity near misses, and
fragmentation-boundary hard negatives.

Local decision support:

- template:
  - `data/review/acute_political_risk_benchmark_refinement_decisions.template.json`
- local file:
  - `data/review/acute_political_risk_benchmark_refinement_decisions.local.json`

### Build acute political-risk fit dataset

```bash
python3 scripts/analysis/build_acute_political_risk_fit_dataset.py
```

Use this to materialize the reviewed fit-ready acute-risk sample from the
acute benchmark tiers.

### Validate acute political-risk baseline score

```bash
python3 scripts/analysis/validate_acute_political_risk_baseline.py
```

Use this to validate the current acute-risk signal-score baseline against the
reviewed acute-risk fit-ready sample.

### Compare first acute political-risk fit models

```bash
python3 scripts/analysis/validate_acute_political_risk_models.py
```

Use this to compare the current acute-risk threshold baseline against a first
leave-one-out logistic-regression model on the reviewed acute-risk fit-ready
sample.

### Review external/economic benchmark countries

```bash
python3 scripts/analysis/review_external_economic_signals.py
```

Use this to generate a private benchmark review for the current
external/economic monthly signal layer across the six anchor countries.

### Build internal signal panel pilot

```bash
python3 scripts/analysis/build_internal_signal_panel.py --country Venezuela
```

Use this to build a private/internal signal-panel artifact for one benchmark
country using the current country-month panel and internal signal spec.

Private standalone viewer:

- `apps/internal-tools/signal-panel.html?country=Venezuela`

## QA And Review Diagnostics

### Event QA

```bash
python3 scripts/qa/run_qa.py
```

### Registry QA

```bash
python3 scripts/qa/run_registry_qa.py
```

### Duplicate detection

```bash
python3 scripts/pipeline/detect_duplicates.py
```

### Review queue build

```bash
python3 scripts/review/build_review_queue.py
```

## Canonical And Actor Layers

### Canonical event build

```bash
python3 scripts/pipeline/build_canonical_events.py
```

### Event classification stage

```bash
python3 scripts/pipeline/classify_events.py
```

Run this when you want classification as an explicit standalone stage over
`data/staging/filtered_articles.json`.

### Actor coding

```bash
python3 scripts/pipeline/code_actors.py
```

### Backfill event/article links into live events

```bash
python3 scripts/pipeline/backfill_event_articles.py
```

### Promote reviewed actors into the durable registry

```bash
python3 scripts/pipeline/update_actor_registry.py
```

## Analyst Edit Materialization

### Apply event-level analyst edits

```bash
python3 scripts/review/apply_analyst_edits.py
```

### Apply registry-level edits

```bash
python3 scripts/review/apply_registry_edits.py
```

## Analysis

### Council analysis

```bash
python3 scripts/analysis/run_council.py
```

### Country monitor build

```bash
python3 scripts/analysis/build_country_monitors.py
```

This generates the layered country-monitor and predictive-risk output at:

- `data/published/country_monitors.json`

### Country monitor validation

```bash
python3 scripts/analysis/validate_country_monitors.py
```

This checks the current country-monitor outputs against benchmark target ranges
and writes:

- `data/review/country_monitor_validation.json`

## Publish

### Build the public-safe published dataset

```bash
python3 scripts/publish/publish_dashboard_data.py
```

## Local Workspace

### Initialize the local analyst environment

```bash
python3 scripts/review/init_local_analyst_env.py
```

### Generate a password hash

```bash
python3 scripts/review/hash_password.py
```

### Start the analyst server

```bash
python3 scripts/review/run_analyst_server.py
```

Choose a port explicitly if needed:

```bash
python3 scripts/review/run_analyst_server.py --port 8772
```

### Start a simple local server for the public dashboard

```bash
python3 -m http.server
```

## Recommended Full Internal Sequence

```bash
python3 scripts/run_pipeline.py
python3 scripts/qa/run_qa.py
python3 scripts/qa/run_registry_qa.py
python3 scripts/pipeline/detect_duplicates.py
python3 scripts/analysis/build_country_monitors.py
python3 scripts/analysis/validate_country_monitors.py
python3 scripts/pipeline/build_canonical_events.py
python3 scripts/pipeline/code_actors.py
python3 scripts/review/build_review_queue.py
python3 scripts/analysis/run_council.py
python3 scripts/publish/publish_dashboard_data.py
```

Run these only when needed:

```bash
python3 scripts/pipeline/update_actor_registry.py
python3 scripts/review/apply_analyst_edits.py
python3 scripts/review/apply_registry_edits.py
python3 scripts/ingest_gdelt.py --historical --since 2025-01-01
python3 scripts/historical_ingest.py --since 2000-01-01 --json
```
