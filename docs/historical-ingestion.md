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

## Components

- `scripts/historical_ingest.py` is the planner and runner.
- `config/historical_sources.json` is the source manifest: groups, connector types,
  endpoints, and coverage floors.

Without `--run`, the script only prints a plan, as it always has. With `--run`, it
executes the ingest:

1. Every runnable source is split into **units** of one (source, calendar month).
   Months before a source's `coverage_start` are dropped. For example, GDELT starts
   on 2015-02-19.
2. Each unit writes `data/staging/historical/<since>_<until>/<source_id>__<YYYY-MM>.jsonl`
   using the shared `normalize_articles` schema. Duplicates within a unit are removed.
3. `_checkpoint.json` records each unit as it finishes. An interrupted, crashed, or
   rate-limited run resumes from where it stopped. A unit whose connector raises stays
   pending and is recorded under `failed`.
4. `_qa.json` is the archive-quality report. It flags:
   - `coverage_gap`: months that returned zero articles
   - `cross_batch_duplicates`: the same URL appearing in more than one month
   - `source_imbalance`: one source contributing over 60% of articles
   - `connector_error`
5. The staged directory feeds straight into classification:
   `python3 scripts/run_pipeline.py --from-staging <run_dir>`.

The runner currently supports three connectors:

| `connector_type` | Implementation | Sources |
|---|---|---|
| `gdelt` | `ingest_gdelt.fetch_gdelt_range` | GDELT API |
| `wordpress_archive` | `ingest_rss.fetch_wordpress_archive` (needs `endpoint`; a list of endpoints is allowed) | InSight Crime, Americas Quarterly (`webexclusive` post type), NACLA |
| `google_news_window` | `ingest_rss.google_news_backfill_feeds` + `fetch_google_news_window` | Every curated Google News feed in `rss_sources.py` |

**Google News windows.** Plain RSS only returns recent items, so this connector re-issues
each curated Google News feed with `after:`/`before:` operators, one week at a time.
Google silently ignores the date operators when a query carries a long `OR` list, so the
backfill drops the live feeds' topic terms. Small outlets get a bare `site:` query.
High-volume wires (Reuters, AP, AFP, EFE) get one `site:` + country query per country,
because a bare wire query returns global news capped at about 100 items. Relevance is left
to the pipeline pre-filter. Coverage thins out for older periods, so treat this as a
gap-filler for recent months.

Sources that can't run are listed in the report under `skipped_sources`, each with a
reason:
- ACLED is structured events, not articles.
- El Faro has no confirmed endpoint yet.
- The El País and Folha custom archives have no connector yet.
- NewsAPI only has 30 days of history.

## Examples

```bash
# Plan only
python3 scripts/historical_ingest.py --since 2000-01-01 --until 2025-12-31
python3 scripts/historical_ingest.py --since 2000-01-01 --json

# Preview the units without fetching anything
python3 scripts/historical_ingest.py --since 2015-01-01 --until 2015-12-31 --run --dry-run

# Execute in bounded, resumable slices
python3 scripts/historical_ingest.py --since 2015-01-01 --until 2015-12-31 --run --max-units 24
python3 scripts/historical_ingest.py --since 2015-01-01 --until 2015-12-31 --run   # resumes

# One source, gentler GDELT profile, retry months that came back empty
python3 scripts/historical_ingest.py --since 2015-01-01 --until 2015-12-31 --run \
    --source gdelt_api --conservative --pause 10 --retry-empty

# Classify the staged articles
python3 scripts/run_pipeline.py --from-staging data/staging/historical/2015-01-01_2015-12-31
```

**Caveat on empty months:** the existing connectors log request errors and return an
empty list instead of raising. So a `coverage_gap` month may be a failed request rather
than a real gap. Rerun with `--retry-empty` before treating it as real.

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

Done as of 2026-09-29: resumable batch execution, article-level staging output, and
archive QA for gaps, duplicates, and imbalance.

Still open:
- custom connectors for El País and Folha, which need article-date pagination
- confirming El Faro's archive endpoint and depth
- per-source rate-limit rules. Today there is one global `--pause`, plus GDELT's own
  retry and backoff
- making connectors raise on request failure, so empty months are unambiguous
- duplicate-title clustering across sources, beyond the current exact-URL matching
