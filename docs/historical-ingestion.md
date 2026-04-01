# Historical Ingestion

## Purpose

SENTINEL's fast pipeline is optimized for ongoing monitoring, not for complete
historical archive recovery. Deep backfill, especially for coverage starting in
2000, should run through a separate historical-ingestion path.

## Why A Separate Path Is Needed

The current enhanced pipeline is strong for recent monitoring, but it is not a
credible stand-alone solution for 2000+ news collection because:

- RSS feeds are mostly recent, not long-run historical archives
- NewsAPI is not a deep-archive source
- only some publishers expose usable archive endpoints
- GDELT is valuable but does not replace outlet-specific archive coverage
- structured datasets like ACLED cover event structure, not full news archives

## Operating Principle

Treat historical ingestion as a different problem from nightly monitoring.

- fast pipeline:
  recent reporting, ongoing updates, public dashboard refreshes
- historical pipeline:
  slow, resumable, source-specific archive recovery with heavier QA

## Current Scaffold

The repo now includes:

- [historical_ingest.py](/Users/hjmoncrieff/Library/CloudStorage/Dropbox/SENTINEL/scripts/historical_ingest.py)
- [historical_sources.json](/Users/hjmoncrieff/Library/CloudStorage/Dropbox/SENTINEL/config/historical_sources.json)

The script is currently a planning/orchestration scaffold. It does not yet
perform full historical ingest, but it does establish:

- a dedicated entry point
- a source-group manifest
- a planning contract for deep backfill

## Example

```bash
python3 scripts/historical_ingest.py --since 2000-01-01 --until 2025-12-31
```

Or inspect the full plan as JSON:

```bash
python3 scripts/historical_ingest.py --since 2000-01-01 --json
```

## Recommended Source Order

1. structured historical layers
   GDELT, ACLED, and similar sources
2. WordPress archives
   outlets with accessible paginated archives or REST APIs
3. custom publisher archives
   source-specific connectors for major outlets
4. search APIs
   only as a limited supplement, not the main backfill strategy

## Next Build Steps

- add source-specific historical connectors
- add resumable batch execution
- write article-level historical staging output
- add archive QA for coverage gaps and duplicate title clusters
- define source-specific access and rate-limit rules
