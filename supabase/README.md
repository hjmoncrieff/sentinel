# Supabase Integration

This directory scaffolds the first Supabase-backed SENTINEL analyst backend.

## Purpose

Supabase is used for:

- analyst authentication
- analyst roles and profile records
- private console snapshot storage
- append-only review workflow logs
- future Edge Functions and publication controls

The public dashboard remains static and continues to read generated JSON from
`data/published/`.

## Setup

1. Create a Supabase project.
2. Run the SQL migration in `migrations/`.
3. Deploy the authenticated review-write function:

```bash
supabase functions deploy review-action
```

4. Copy your project URL and anon key into:
   - `apps/analyst-console/supabase-config.js`
5. Export your service role credentials locally before running sync scripts:

```bash
export SUPABASE_URL="https://YOUR_PROJECT.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="YOUR_SERVICE_ROLE_KEY"
```

## Sync Flow

- `scripts/sync/push_console_snapshots_to_supabase.py`
  Pushes local canonical, review, published, and registry snapshots into
  `public.console_snapshots`.
- `scripts/sync/pull_registry_edits_from_supabase.py`
  Pulls analyst-submitted registry edits from Supabase into the local ignored
  registry edit file.
- `scripts/sync/export_published_from_supabase.py`
  Pulls the published dashboard layer back into `data/published/`.
- `scripts/sync/run_supabase_cycle.py`
  Runs the standard sync cycle:
  1. pull registry edits
  2. apply them locally
  3. rebuild actor-coded and published layers
  4. push refreshed snapshots
  5. export published artifacts

For the full step-by-step setup and automation model, use:

- `docs/supabase-setup.md`

## Notes

- Only the anon key belongs in frontend code. Never place the service role key
  in the browser.
- The browser analyst console now sends write actions through the `review-action`
  Edge Function. Reads still come from snapshots and review tables directly.
- Self-registration is intentionally conservative. New browser-created accounts
  default to the `analyst` role. Promote privileged users manually in Supabase.
- In Supabase mode, registry edits are stored immediately in Supabase but are
  materialized into `config/actors/actor_registry.json` only when the sync cycle
  is run from a trusted local environment.
- Local `supabase status` may report `imgproxy` and `pooler` as stopped. That is
  currently acceptable for SENTINEL because the repo does not use Storage image
  transformations or a pooled local database connection in its active workflow.
