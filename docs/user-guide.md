# SENTINEL User Guide

This is the step-by-step operating guide for trusted SENTINEL users. It is
written for day-to-day use, not for public project overview.

The operating assumption is AI-first. Humans should spend most of their time on
review, corroboration, correction, and publication judgment rather than routine
manual coding.

For a command-by-command reference for every executable stage runner, use:

- `docs/stage-runners.md`

## 1. Ground Rules

- treat analyst credentials, live review edits, and private reasoning as local
  operational data
- do not commit `*.local.json` review files
- use the public dashboard only for published outputs
- use the analyst console only through the local server when making real edits
- after any major architectural or product leap, record three things in the
  private docs before moving on:
  - what changed
  - what decision was taken and why
  - what commands or workflow order are now expected
- when a new variable, field, construct, or dataset column is introduced,
  update `data/CODEBOOK.md` in the same pass
- keep `docs/private-roadmap.md` current when a major leap changes short-term,
  medium-term, or long-term priorities
- keep the private diagrams current when architecture or construct logic
  changes:
  - `docs/private-integration-diagram.md`
  - `docs/private-integration-diagram.svg`
  - `docs/private-construct-diagram.md`
  - `docs/private-construct-diagram.svg`
- keep private model-logic notes current when internal reasoning layers change:
  - `docs/private-process-episode-event-note.md`
  - `docs/private-signal-panel-note.md`
- when a major leap changes the operating sequence, update this guide so the
  step-by-step private workflow stays current

## 2. One-Time Local Setup

Initialize the local analyst files:

```bash
python3 scripts/review/init_local_analyst_env.py
```

This creates:

- `data/review/users.local.json`
- `data/review/edits.local.json`
- `data/review/registry_edits.local.json`

Generate password hashes:

```bash
python3 scripts/review/hash_password.py
```

Paste the generated hashes into `data/review/users.local.json` and replace every
`replace_me` placeholder before starting the analyst server.

## 3. Start The Workspace

### Public dashboard

```bash
python3 -m http.server
```

Open:

- `http://127.0.0.1:8000/`

### Analyst console

```bash
python3 scripts/review/run_analyst_server.py
```

If the default port is busy, start it on another local port:

```bash
python3 scripts/review/run_analyst_server.py --port 8766
```

Open:

- `http://127.0.0.1:8765/apps/analyst-console/`
- or the port you selected

## 4. Daily Data Workflow

### Structural refresh when updating the country model

Run these when you want to refresh slow-moving structural inputs before
rebuilding country monitors:

```bash
python3 scripts/refresh_vdem.py
python3 scripts/fetch_worldbank.py
python3 scripts/clean_greenbook.py
python3 scripts/clean_eusanct.py
python3 scripts/clean_financial_crises.py
python3 scripts/build_country_year.py
```

These update:

- `data/cleaned/vdem.json`
- `data/cleaned/worldbank.json`
- `data/cleaned/greenbook.json`
- `data/cleaned/eusanct.json`
- `data/cleaned/financial_crises.json`
- `data/cleaned/country_year.json`

### Build the private country-month modeling panel

Run this when you want the first private modeling artifact that joins
structural and event-derived monthly data:

```bash
python3 scripts/analysis/build_episodes.py
python3 scripts/analysis/build_external_economic_signals.py
python3 scripts/analysis/build_country_month_panel.py
```

This writes:

- `data/modeling/episodes.json`
- `data/modeling/external_economic_country_month.json`
- `data/modeling/country_month_panel.json`
- `data/modeling/country_month_panel.csv`

This panel is private/internal. It should not be treated as a public dashboard
artifact.

To build the current private benchmark review for the external/economic layer:

```bash
python3 scripts/analysis/review_external_economic_signals.py
```

This writes:

- `data/review/external_economic_signal_review.json`

It currently includes:

- structural baseline fields
- monthly event-pulse fields
- rolling-window features
- first proxy target columns for `irregular_transition_next_1m` and
  `irregular_transition_next_3m`
- target score/label support fields for the same transition horizon
- benchmark-seed-ready contracts for external pressure, economic fragility, and
  policy-shock inputs

The tracked internal benchmark seed file is:

- `data/modeling/benchmark_country_month_signals.json`

If you want to seed private country-month external/economic inputs before
automated ingestion exists:

1. Copy:
   - `data/modeling/manual_country_month_signals.template.json`
   to:
   - `data/modeling/manual_country_month_signals.local.json`
2. Fill in local country-month rows.
3. Rebuild:

```bash
python3 scripts/analysis/build_country_month_panel.py
```

To inspect the proxy-target distribution after rebuilding:

```bash
python3 scripts/analysis/audit_country_month_targets.py
```

This writes:

- `data/modeling/country_month_target_audit.json`

Optional follow-up review:

```bash
python3 scripts/analysis/review_irregular_transition_targets.py
```

This produces:

- `data/review/irregular_transition_target_review.json`

To convert the remaining `plausible` and `review` cases into a working
adjudication queue:

```bash
python3 scripts/analysis/build_adjudication_queue.py
```

This adds:

- `data/review/adjudication_queue_irregular_transition.json`

To build the first selective adjudicated target layer from that review:

```bash
python3 scripts/analysis/build_adjudicated_transition_labels.py
python3 scripts/analysis/build_country_month_panel.py
python3 scripts/analysis/audit_country_month_targets.py
```

This adds:

- `data/modeling/adjudicated_irregular_transition_labels.json`

If you want to extend the adjudicated layer locally beyond the tracked
benchmark cases:

1. Copy:
   - `data/review/adjudicated_transition_decisions.template.json`
   to:
   - `data/review/adjudicated_transition_decisions.local.json`
2. Add reviewed rows.
3. Rebuild:

```bash
python3 scripts/analysis/build_adjudicated_transition_labels.py
python3 scripts/analysis/build_country_month_panel.py
python3 scripts/analysis/audit_country_month_targets.py
```

The current adjudicated layer is intentionally narrow. It overrides only the
`irregular_transition_next_1m` label for benchmark-reviewed cases, while the
rest of the panel remains on the episode-aware proxy rule.

Current checkpoint:

- the first internal adjudicated layer now contains `34` reviewed `1m` labels
- the adjudication queue is currently cleared
- the recommended next step is to pause expansion and later tighten this into a
  stricter gold-label subset

To build that stricter gold subset:

```bash
python3 scripts/analysis/build_gold_transition_labels.py
```

This adds:

- `data/modeling/gold_irregular_transition_labels.json`

To validate the stricter fit-path target layer against that gold subset:

```bash
python3 scripts/analysis/validate_gold_transition_targets.py
```

This adds:

- `data/review/gold_irregular_transition_validation.json`

Current first validation checkpoint:

- gold rows: `25`
- fit-path gold recall: `88.0%`
- fit-path precision against gold: `75.0%`

To build the reviewed fit-ready dataset directly:

```bash
python3 scripts/analysis/build_irregular_transition_fit_dataset.py
```

This adds:

- `data/modeling/irregular_transition_fit_dataset.json`

Current fit-dataset checkpoint:

- rows: `64`
- gold positives: `25`
- reviewed-watch negatives: `9`
- weak-review negatives: `2`
- local reviewed negatives: `28`

For first model fitting, use the panel’s gold-aligned target fields rather than
the broader adjudicated `v1` layer:

- `irregular_transition_gold_next_1m`
- `irregular_transition_gold_label_available`
- `irregular_transition_fit_score_next_1m`
- `irregular_transition_fit_label_next_1m`

To validate the current signal-score baseline on the reviewed fit-ready sample:

```bash
python3 scripts/analysis/validate_irregular_transition_baseline.py
```

This adds:

- `data/review/irregular_transition_baseline_validation.json`

Current baseline checkpoint:

- validation sample rows: `64`
- positives: `25`
- reviewed negatives: `39`
- local reviewed negatives: `28`
- operational `v1` label precision: `73.529%`
- fit-path recommended score threshold: `2`
- at fit threshold `2`:
  - precision: `74.194%`
  - recall: `92.0%`
  - specificity: `79.487%`
- at fit threshold `4`:
  - precision: `100%`
  - recall: `88.0%`
  - specificity: `100%`

To run the first actual fit comparison:

```bash
python3 scripts/analysis/validate_irregular_transition_models.py
```

This adds:

- `data/review/irregular_transition_model_validation.json`

Current first fit-comparison result:

- threshold baseline:
  - precision: `100%`
  - recall: `88.0%`
- leave-one-out logistic baseline:
  - precision: `46.875%`
  - recall: `60.0%`

Current conclusion:

- the stricter fit-path threshold baseline is still better than the first
  fitted model on the reviewed sample
- the broader watch-path remains useful for analyst-facing monitoring and
  rupture-watch coverage
- the expanded historical-memory feature set improved recall, but not enough to
  replace the fit-time threshold benchmark
- do not replace the baseline yet

The next broader political-risk target now also exists privately at the proxy
stage:

- `acute_political_risk_next_1m`
- `acute_political_risk_next_3m`
- current proxy version:
  - `proxy_acute_political_risk_v1`
- first checkpoint:
  - `1m` positives: `51`
  - `3m` positives: `125`
- first review path:
  - `scripts/analysis/review_acute_political_risk_targets.py`
  - `data/review/acute_political_risk_target_review.json`
- first adjudication-queue path:
  - `scripts/analysis/build_acute_political_risk_adjudication_queue.py`
  - `data/review/adjudication_queue_acute_political_risk.json`
- first adjudicated acute-risk layer:
  - `scripts/analysis/build_adjudicated_acute_political_risk_labels.py`
  - `data/modeling/adjudicated_acute_political_risk_labels.json`
- current checkpoint:
  - `acute political risk adjudicated layer v1`
  - `30` reviewed `1m` rows
  - adjudication queue empty
- next stricter artifact:
  - `scripts/analysis/build_gold_acute_political_risk_labels.py`
  - `data/modeling/gold_acute_political_risk_labels.json`
- first gold validation path:
  - `scripts/analysis/validate_gold_acute_political_risk_targets.py`
  - `data/review/gold_acute_political_risk_validation.json`
- current first checkpoint:
  - gold recall `100.0%`
  - proxy precision `45.833%`
- next benchmark diagnostics:
  - `scripts/analysis/build_acute_political_risk_benchmark_tiers.py`
  - `scripts/analysis/audit_acute_political_risk_tier_separation.py`
  - `scripts/analysis/review_acute_political_risk_protest_cases.py`
  - `scripts/analysis/build_acute_political_risk_benchmark_refinement_queue.py`
- current benchmark-tier checkpoint:
  - gold positives `22`
  - hard negatives `18`
  - easy negatives `22`
- fit-ready acute-risk sample:
  - `scripts/analysis/build_acute_political_risk_fit_dataset.py`
  - `data/modeling/acute_political_risk_fit_dataset.json`
- first acute-risk baseline validation:
  - `scripts/analysis/validate_acute_political_risk_baseline.py`
  - `data/review/acute_political_risk_baseline_validation.json`
  - current best threshold: `4`
  - current result: precision `100.0%`, recall `100.0%`, specificity `100.0%`
  - this result still holds after freezing the benchmark refinement layer `v1`
- first acute-risk model comparison:
  - `scripts/analysis/validate_acute_political_risk_models.py`
  - `data/review/acute_political_risk_model_validation.json`
  - current result:
    - threshold baseline still wins
    - logistic precision `84.615%`, recall `100.0%`, specificity `89.744%`
- protest-specific interpretation fields now also exist in the panel:
  - `protest_acute_signal_score`
  - `protest_background_load_score`
- current modeling stance:
  - keep those protest fields for interpretation/review
  - do not feed them directly into acute-risk scoring until protest-heavy
    benchmark cases are reviewed more tightly
- current benchmark-refinement stance:
  - review hard negatives before inventing more acute-risk features
  - start with:
    - protest-linked near misses
    - high-severity near misses
    - fragmentation-boundary hard negatives
  - reviewed refinement decisions can be stored in:
    - `data/review/acute_political_risk_benchmark_refinement_decisions.local.json`
  - current checkpoint:
    - all currently queued acute-risk refinement rows have been reviewed
    - the active refinement queue is now `0`
    - the acute-risk benchmark refinement layer can be treated as frozen `v1`

The reviewed-negative workflow now has two layers:

- `data/review/irregular_transition_negative_queue.json`
  - broad low-intensity/background negatives
- `data/review/irregular_transition_hard_negative_queue.json`
  - hard transition-like negatives for benchmark stress-testing

The benchmark layer now also has a consolidated tiered reference artifact:

- `data/modeling/irregular_transition_benchmark_tiers.json`

Current benchmark tier counts:

- gold positives: `25`
- hard negatives: `10`
- easy negatives: `18`

Current tiered validation read:

- under the current `proxy_irregular_transition_v6` rule:
  - `threshold 2` is the best reviewed-sample F1 cut
  - `threshold 4` remains a stricter high-specificity cut
- the fitted logistic struggles most on `hard_negative` cases
  - hard-negative specificity: `30.0%`
- the tier-separation audit suggests the strongest current contrasts are:
  - higher `transition_contestation_load_score` in `hard_negative`
  - more negative `transition_specificity_gap` in `hard_negative`
  - `transition_rupture_precursor_score` alone is not yet sufficient
- the `v6` rupture-sequence adjustment restored benchmark-positive
  rupture-watch months like Haiti `2021-06-01` and Mexico `2020-06-01`, but
  it also reduced recall at the stricter `threshold 4` cut

The latest pass added five more hard benchmark negatives in:

- Colombia
- Mexico
- Peru
- Ecuador

To audit what the reviewed fit sample still lacks:

```bash
python3 scripts/analysis/audit_irregular_transition_fit_sample.py
```

This adds:

- `data/review/irregular_transition_fit_sample_audit.json`

Current takeaway:

- the fit sample still needs more reviewed negatives
- especially outside:
  - `Colombia`
  - `El Salvador`
  - `Honduras`
  - `Mexico`
  - `Venezuela`

To build a structured queue of lower-intensity and background negative
candidates:

```bash
python3 scripts/analysis/build_irregular_transition_negative_queue.py
```

This adds:

- `data/review/irregular_transition_negative_queue.json`

Current first queue checkpoint:

- queue rows: `75`
- reviewed-negative countries already represented: `25`
- rows prioritized to expand country coverage: `0`
- rows deepening existing negative countries: `75`

To extend the fit-ready sample locally with reviewed negatives:

1. Copy:
   - `data/review/reviewed_negative_decisions.template.json`
   to:
   - `data/review/reviewed_negative_decisions.local.json`
2. Add reviewed negative rows.
3. Re-run:

```bash
python3 scripts/analysis/validate_irregular_transition_baseline.py
python3 scripts/analysis/validate_irregular_transition_models.py
python3 scripts/analysis/audit_irregular_transition_fit_sample.py
```

The validation runners now absorb those local reviewed negatives
automatically.

To build the first internal one-country signal panel pilot:

```bash
python3 scripts/analysis/build_internal_signal_panel.py --country Venezuela
```

This currently writes:

- `data/modeling/internal_signal_panel_venezuela.json`

To inspect it as a private internal chart page, open:

- `apps/internal-tools/signal-panel.html?country=Venezuela`

### Fast ingest run

Run the default non-GDELT pipeline:

```bash
python3 scripts/run_pipeline.py
```

This updates:

- `data/events.json`
- `data/review/source_audit.json`

### Optional GDELT run

Use GDELT only when needed:

```bash
python3 scripts/run_pipeline.py --gdelt
```

Or run the separate GDELT path directly:

```bash
python3 scripts/ingest_gdelt.py
```

If GDELT rate-limits a run, the standalone client now retries with backoff
instead of failing immediately on the first `429` response.

For a gentler fallback, use:

```bash
python3 scripts/ingest_gdelt.py --conservative
```

For historical runs that may need to resume after throttling or interruption:

```bash
python3 scripts/ingest_gdelt.py --historical --since 2025-01-01 --resume --conservative
```

For the gentlest historical path, restrict execution to local off-hours:

```bash
python3 scripts/ingest_gdelt.py --historical --since 2025-01-01 --resume --conservative --off-hours
```

If you want the client to give up sooner when rate-limited, lower the cutoff:

```bash
python3 scripts/ingest_gdelt.py --conservative --max-backoff-seconds 45
```

### Deep historical planning

For historical archive planning rather than the fast monitoring pipeline:

```bash
python3 scripts/historical_ingest.py --since 2000-01-01 --json
```

## 5. Build Internal Review Artifacts

Run the review diagnostics and internal data layers:

```bash
python3 scripts/qa/run_qa.py
python3 scripts/qa/run_registry_qa.py
python3 scripts/pipeline/detect_duplicates.py
python3 scripts/pipeline/build_canonical_events.py
python3 scripts/pipeline/code_actors.py
python3 scripts/review/build_review_queue.py
python3 scripts/pipeline/update_actor_registry.py
```

This refreshes:

- `data/review/qa_report.json`
- `data/review/registry_qa_report.json`
- `data/review/duplicate_candidates.json`
- `data/review/review_queue.json`
- `data/canonical/events.json`
- `data/canonical/events_actor_coded.json`
- `data/canonical/actor_mentions.json`
- `config/actors/nsva_registry_seed.json`
- `config/actors/broad_actor_registry_seed.json`
- `config/actors/actor_registry.json`

If you need the exact runner list for each stage, see:

- `docs/stage-runners.md`

If you want classification as its own explicit stage over filtered article
records, you can also run:

```bash
python3 scripts/pipeline/classify_events.py
```

## 6. Generate Council Analysis

Run the internal council layer:

```bash
python3 scripts/analysis/run_council.py
```

This writes:

- `data/review/council_analyses.json`

Council analysis runs across every event, but every council output is explicitly
tagged as AI-generated analysis. It should be treated as an analytical layer,
not as human validation.

The council now also records:

- compact upstream AI-worker output summaries
- recommended analyst actions for review follow-up
- selective lens activation and analyst weights by event type and actor profile
- article-context snippets drawn from linked source records rather than headline-only framing
- mechanism-specific writing tied to `event_subcategory`, so public analysis is more event-specific and less repetitive

The council is informed by:

- `config/agents/analyst_knowledge.json`
- `config/agents/council_guidance.json`
- `config/agents/council_roles.json`
- `config/agents/ai_workers.json`

The Council tab now surfaces the project knowledge trace behind each lens, so
analysts can inspect which concepts, priorities, and AI workers shaped the
assessment.

Current council structure:

- `Military Analyst`
- `Political Analyst`
- `Security Analyst`
- `International Analyst` when the event has a strong external-pressure or foreign-alignment mechanism
- `Economist Analyst` when the event has a strong macro, fiscal, or illicit-economy mechanism
- `Synthesis Analyst`

Not every event activates the same bundle of analysts. Some events now route
mainly through one core lens, while others activate multiple core and specialist
lenses with unequal weights.

The event taxonomy is now construct-aware as well. Event records can now carry:

- `event_category`
  - broad analytical family such as `political`, `military`, `security`, or
    `international`
- `event_subcategory`
  - narrower mechanism bucket
- `event_construct_destinations`
  - which higher-order constructs the event most directly feeds
- `event_analyst_lenses`
  - which analyst lenses should usually activate first

## 6b. Build Country Monitors

Run the layered country-monitor and predictive-risk builder:

```bash
python3 scripts/analysis/build_country_monitors.py
```

This writes:

- `data/published/country_monitors.json`

Treat this as an experimental analytical layer. It is intended to improve
country-level monitoring over time, not to replace event-level interpretation.

## 6c. Validate Country Monitors

Run the benchmark validation pass:

```bash
python3 scripts/analysis/validate_country_monitors.py
```

This writes:

- `data/review/country_monitor_validation.json`

Use this report to see which benchmark countries still sit outside the intended
target ranges for overall risk, regime vulnerability, militarization, and
security fragmentation.

## 7. Review Events In The Analyst Console

Log in using your local analyst account.

Role expectations:

- `RA`
  summary cleanup, notes, actor cleanup, low-risk QA fixes
- `Analyst`
  event coding, actor coding, review-state updates, duplicate resolution
- `Coordinator`
  final approval, publication-facing validation, higher-consequence review

Use the console to:

- search and filter the review queue
- fix QA issues manually in the structured editor
- mark QA flags resolved
- review duplicate candidates and either merge them with confirmation or mark them as genuinely different events
  This workflow now includes a short reason picker so false-positive duplicate flags can be categorized consistently.
- use the manual merge controls in the `Duplicates` tab when two events should be consolidated even if they were not pre-flagged together
  This path also lets analysts set a canonical keeper title and summary while preserving the audit trail.
- undo duplicate decisions when a prior merge or distinct-event judgment needs to be reversed
- undo QA resolutions when a flag should return to the active review queue
- edit coding fields through dropdowns and collapsible sections
- add new actors directly in the review editor
- remove or restore existing actors without deleting audit history
- mark actor confidence and registry follow-up status during review
- move actors through the registry workflow:
  - `needs_registry_entry`
  - `registry_seeded`
  - `registry_confirmed`
- mark uncertain actors explicitly when identity, classification, or role is not secure
- capture actor aliases and relationship tags such as `state-linked`,
  `collusive`, or `security_partner` when justified by the reporting
- use the `Registry` tab to:
  - promote unmatched actors into the durable registry
  - link event actors to existing registry entries
  - update registry aliases, subtype, relationship tags, and status in a controlled way
- add private analyst reasoning when needed
- mark events as human reviewed or human validated
- eliminate entries safely by marking them `rejected`
- restore rejected entries back into active workflow when needed
- undo publication-facing decisions without removing the audit trail

The goal is not to recode everything by hand. The console is mainly for
exception handling, supervision, and release control.

Use the `Actor Registry` quick view or queries like `registry:true` and
`actor_uncertain:true` to focus on actor follow-up work.

Inside the `Actor Registry` view, analysts can also use bulk actions across
selected events to:

- seed registry follow-up actors as `registry_seeded`
- confirm reviewed actors as `registry_confirmed`
- clear actor uncertainty when that review has been completed

When registry QA flags duplicate entries or alias collisions, the same view can
also:

- merge one registry entry into another while preserving aliases and evidence
- drop a conflicting alias from a single registry entry without forcing a merge

After actor follow-up review, promote the latest reviewed actor records into the
durable registry with:

```bash
python3 scripts/pipeline/build_broad_actor_registry_seed.py
python3 scripts/pipeline/update_actor_registry.py
```

The first command refreshes the broader seed module for state, civil-society,
economic, media, protest, and international actors. The second merges all seed
modules plus reviewed actor promotions into the durable registry.

Actor records now follow a broader hierarchy so the registry can support state,
social, economic, and armed non-state actors consistently:

- `actor_category`
  broad class such as `state_actor` or `non_state_actor`
- `actor_group`
  branch such as `executive`, `military`, `civil_society`, `economic_group`, or `armed_non_state_actor`
- `actor_type`
  specific class such as `state_institution`, `state_security_force`, `armed_group`, or `organized_crime`
- `actor_subtype`
  finer subtype such as `cartel`, `gang`, `insurgent`, or `dissident_faction`

So organized crime is no longer treated as the main actor category. It sits under:

- `actor_category = non_state_actor`
- `actor_group = armed_non_state_actor`
- `actor_type = organized_crime`

## 8. Save And Apply Analyst Edits

When using the authenticated analyst server, saves go directly into:

- `data/review/edits.local.json`

The server then reruns:

- `scripts/review/apply_analyst_edits.py`

This materializes edited local outputs such as:

- `data/review/events_with_edits.json`
- `data/review/review_queue_with_edits.json`

## 9. Publish Public-Safe Data

After review changes are in place, rebuild the public dataset:

```bash
python3 scripts/publish/publish_dashboard_data.py
```

This writes:

- `data/published/events_public.json`

The published file is safe for the public dashboard and includes:

- event fields needed for display
- public-safe provenance summary
- linked report metadata for clustered events
- `review_status`
- `review_priority`
- `human_validated`
- whether an event has been reviewed by a human

Private analyst reasoning and local credentials stay out of this layer.

If the live event store predates the article-linkage upgrade, run:

```bash
python3 scripts/pipeline/backfill_event_articles.py
```

Then rebuild the downstream layers.

Current publication policy:

- low-confidence events are withheld until a human reviews or corroborates them
- merged duplicates are withheld from the public layer
- records marked `flagged`, `needs_revision`, or `rejected` are withheld

## 10. Recommended Daily Operating Sequence

1. run `scripts/run_pipeline.py`
2. inspect `data/review/source_audit.json`
3. run QA, duplicates, canonical build, actor coding, review queue, and council scripts
4. open the analyst console
5. resolve high-attention items, QA flags, and duplicate candidates
6. use the publication queue for low-confidence corroboration and release checks
7. mark reviewed or validated events as appropriate
8. run `scripts/publish/publish_dashboard_data.py`
9. refresh the public dashboard

## 11. Troubleshooting

If the analyst server will not start:

- confirm `data/review/users.local.json` exists
- confirm all placeholder password hashes were replaced
- try another port with `--port`

If edits are not appearing:

- confirm you are logged in through the local analyst server
- check `data/review/edits.local.json`
- rerun `python3 scripts/review/apply_analyst_edits.py`

If public review badges are missing:

- confirm review changes were saved
- rerun `python3 scripts/publish/publish_dashboard_data.py`
- refresh the dashboard after the published dataset updates
- `security_fragmentation_jump_next_3m`
  - `proxy_security_fragmentation_jump_v2`
  - review artifact:
    - `data/review/security_fragmentation_jump_target_review.json`
  - adjudication queue:
    - `data/review/adjudication_queue_security_fragmentation_jump.json`
  - adjudicated layer:
    - `data/modeling/adjudicated_security_fragmentation_jump_labels.json`
  - gold subset:
    - `data/modeling/gold_security_fragmentation_jump_labels.json`
  - gold validation:
    - `data/review/gold_security_fragmentation_jump_validation.json`
  - tiered benchmark:
    - `data/modeling/security_fragmentation_jump_benchmark_tiers.json`
  - tier-separation audit:
    - `data/review/security_fragmentation_jump_tier_separation.json`
