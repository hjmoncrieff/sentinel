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

The council is informed by:

- `config/agents/analyst_knowledge.json`
- `config/agents/council_guidance.json`
- `config/agents/council_roles.json`
- `config/agents/ai_workers.json`

The Council tab now surfaces the project knowledge trace behind each lens, so
analysts can inspect which concepts, priorities, and AI workers shaped the
assessment.

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
python3 scripts/pipeline/update_actor_registry.py
```

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
