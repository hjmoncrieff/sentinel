# scripts/

Run every script from the repo root with Python 3.11+, for example
`python3 scripts/run_pipeline.py`. Each script finds the repo root from its own location,
so the current working directory doesn't matter.

## Top level: fast ingestion pipeline

These modules import each other by bare name, so they stay together at this level.

| Script | Role |
|---|---|
| `run_pipeline.py` | ★ Entry point for the daily monitoring run (`--gdelt`, `--since`, `--from-staging`) |
| `pipeline_core.py` | Collect → pre-filter → classify → cluster → `data/events.json` |
| `ingest_rss.py`, `ingest_newsapi.py`, `ingest_gdelt.py` | Source connectors |
| `rss_sources.py` | Curated feed list |
| `normalize_articles.py` | Shared article-record schema |
| `prompt_library.py` | Loads the versioned prompts and model IDs in `prompts/` |
| `historical_ingest.py` | Deep-backfill planner and resumable runner (`--run`) |
| `ingest_gdelt_events.py` | Standalone GDELT event-table staging |
| `generate_clean_events.py` | Research export: `data/cleaned/events_clean.json` / `events.csv` |
| `sync_obsidian_docs.py` | Local tool: mirrors the docs into an Obsidian vault |

## Stage folders

| Folder | Stage |
|---|---|
| `pipeline/` | Canonical events, actor coding, duplicate detection, actor registry |
| `qa/` | Event and registry QA reports |
| `review/` | Review queue, analyst and registry edits, local analyst server, gold layer |
| `analysis/` | Country monitors, council, risk-model datasets, benchmarks, validation |
| `publish/` | Public-safe outputs → `data/published/` |
| `sync/` | Local ↔ Supabase sync |
| `structural/` | Slow-moving structural data (World Bank, V-Dem, ACLED index, Greenbook, EUSANCT, financial crises) → `data/cleaned/`, then `build_country_year.py` merges them |
| `site/` | Public-site asset tooling (`render_brand_assets.sh`) |

The downstream rebuild order after `data/events.json` changes is listed in `AGENTS.md`
and in `.github/workflows/fetch_events.yml`.
