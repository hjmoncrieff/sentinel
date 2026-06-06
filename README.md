# SENTINEL

SENTINEL is a research platform for tracking civil-military relations, political
stability, and regional security events across Latin America and the Caribbean.
It combines automated event ingestion with analyst review and publishes a
public-facing static dashboard.

## Surfaces

- `index.html`
  Public dashboard served as a static site.
- `apps/analyst-console/`
  Private analyst workspace for review, QA, deduplication, and publication
  control.
- `scripts/`
  Ingestion, normalization, QA, review, publishing, and analysis runners.
- `scripts/sync/`
  Local-to-Supabase and Supabase-to-published JSON sync automation.
- `supabase/`
  Supabase schema, RLS migration scaffolding, and local project config.
- `data/published/`
  Public-safe JSON outputs consumed by the dashboard.

## Repo Boundary

This repository is being prepared as a public codebase. The intended split is:

- GitHub stores public-safe code, schemas, templates, and published outputs.
- Supabase will own authenticated analyst operations and mutable workflow state.
- Local-only files remain outside the public repo when they contain private
  notes, credentials, internal planning, or generated scratch artifacts.

See `docs/repo-boundaries.md` for the current boundary rules.

## Running The Dashboard

```bash
pnpm install
python3 -m http.server
```

Then open `http://127.0.0.1:8000/`.

## Local Development Baseline

SENTINEL now assumes the local toolchain is managed with:

- `mise` for runtime pinning
- `uv` for Python package workflows
- `pnpm` for Node/package scripts
- `playwright` for dashboard smoke checks

The repo pins:

- Node `22`
- Python `3.13`

Useful local commands:

```bash
pnpm install
uv pip install -r requirements-ci.txt
make lint-python
make typecheck-python
pnpm run smoke:dashboard
make supabase-start
make supabase-status
make supabase-cycle
```

Environment setup starts from `.env.example`.

## Analyst Console UI Workflow

- `pnpm analyst-console:dev` - run the Vite analyst console
- `pnpm analyst-console:test` - run Vitest component tests
- `pnpm analyst-console:storybook` - inspect component states
- `pnpm analyst-console:test:e2e` - run Playwright smoke tests
- `pnpm analyst-console:test:visual` - validate screenshot baselines

## Data Layers

- `data/events.json`
  Current live event store from the ingestion pipeline.
- `data/canonical/`
  Internal canonical event and actor layers.
- `data/review/`
  Review templates and workflow artifacts.
- `data/published/events_public.json`
  Public-safe dataset used by the dashboard.

## Workflow

SENTINEL currently works as a staged pipeline:

1. ingest and normalize source material
2. classify, deduplicate, and code actors
3. generate QA and review queues
4. review and approve records in the analyst console
5. publish public-safe outputs for the dashboard

The public dashboard should only consume the published layer. Credentials,
private analyst notes, local edits, and internal planning materials should stay
outside the public deployment surface.

## Key Docs

- `docs/architecture.md`
- `docs/security-privacy.md`
- `docs/repo-boundaries.md`
- `docs/historical-ingestion.md`
- `docs/next-steps.md`
- `docs/supabase-setup.md`
- `data/CODEBOOK.md`
