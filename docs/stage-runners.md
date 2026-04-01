# SENTINEL Stage Runners

This document lists the executable stage runners in SENTINEL and the command
used to run each one.

It is the command reference. For the daily operational sequence, use
`docs/user-guide.md`.

## Ingest

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

### Historical GDELT

```bash
python3 scripts/ingest_gdelt.py --historical --since 2025-01-01
```

### Historical ingestion planner

```bash
python3 scripts/historical_ingest.py --since 2000-01-01
```

Inspect the plan as JSON:

```bash
python3 scripts/historical_ingest.py --since 2000-01-01 --json
```

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
