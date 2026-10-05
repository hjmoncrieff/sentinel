# Supabase Setup

This guide covers the first-time SENTINEL Supabase setup and the ongoing
automation model.

## 1. Create And Link The Project

From the repo root:

```bash
supabase login
supabase link
supabase db push
```

Use the project reference from the Supabase dashboard when `supabase link`
prompts for it.

## 2. Configure The Analyst Console

Edit:

- `apps/analyst-console/supabase-config.js`

Set:

```js
export const SUPABASE_CONFIG = {
  url: "https://YOUR_PROJECT.supabase.co",
  anonKey: "YOUR_ANON_KEY",
};
```

Use only the public `anon` key in the browser config.

The analyst console now reads snapshots and review tables directly, but sends
write actions through the authenticated `review-action` Edge Function. Deploy it
before testing browser edits:

```bash
supabase functions deploy review-action
```

## 3. Configure Local Sync Credentials

Set one of the following locally:

```bash
export SUPABASE_URL="https://YOUR_PROJECT.supabase.co"
export SUPABASE_SECRET_KEY="YOUR_SB_SECRET_KEY"
```

or:

```bash
export SUPABASE_URL="https://YOUR_PROJECT.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="YOUR_LEGACY_SERVICE_ROLE_KEY"
```

The sync scripts also auto-read `.env` and `.env.local` if those files contain
the same variables.

## 4. Seed Supabase With Current Snapshots

```bash
python3 scripts/sync/push_console_snapshots_to_supabase.py
```

This uploads the review queue, QA outputs, duplicates, council analyses,
canonical events, published events, country monitors, and actor registry into
`public.console_snapshots`.

## 5. Create Your First Analyst User

1. Start the local site:

```bash
python3 -m http.server 8000
```

2. Open:
   - `http://127.0.0.1:8000/apps/analyst-console/`
3. Register with an email address and password.
4. Promote yourself in Supabase:

```sql
update public.profiles
set role = 'admin'
where email = 'your-email@example.com';
```

Then log out and back in.

## 6. Verify The Review Function Locally

With the local Supabase stack running:

```bash
supabase functions serve review-action --env-file .env
```

Because `review-action` runs with `verify_jwt = true`, an unauthenticated curl
will correctly return a missing-authorization error. Use the analyst console
after signing in, or call the function with a real access token, for end-to-end
verification. Authenticated POST requests still respect row-level security.

## 7. Daily Local Command

For a full local cycle, run:

```bash
make supabase-cycle
```

This performs:

1. pull registry edits from Supabase
2. apply them to the local durable registry
3. rebuild dependent layers
4. push refreshed snapshots back to Supabase
5. export the published dashboard artifacts

## 8. GitHub Automation

The repo includes a GitHub Actions workflow that can run the Supabase cycle
after the nightly pipeline or on manual trigger.

Add these GitHub repository secrets:

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`

If you use a legacy elevated key instead, add:

- `SUPABASE_SERVICE_ROLE_KEY`

Once those secrets exist, the workflow in:

- `.github/workflows/supabase_sync.yml`

can:

1. pull registry edits from Supabase
2. apply them to the durable actor registry
3. rebuild the derived local layers
4. push refreshed snapshots back to Supabase
5. export published dashboard JSON
6. commit the refreshed public-safe outputs to GitHub

## 9. Recommended Operating Model

- local pipeline and research work stay local-first
- Supabase stores analyst workflow state and registry edit requests
- Supabase Edge Functions own authenticated analyst write actions
- GitHub Actions runs the sync/export cycle automatically for public release
- GitHub Pages serves only the public dashboard layer

## Restoring A Removed Project

Supabase pauses free-tier projects after a period of inactivity, and a project
left paused long enough can no longer be restored. Either way its
`https://<ref>.supabase.co` address stops resolving. When that happens:

- analyst login in the console fails;
- the nightly "Supabase Sync" workflow skips itself with a warning and opens the
  issue "Supabase project is unreachable";
- the public site and the nightly data pipeline keep working.

To recover:

1. Open the Supabase dashboard. If the project is listed as paused, choose
   **Restore**. The address and keys stay the same, and nothing else is needed.
2. If it cannot be restored, create a new project, then from the repo root:

   ```bash
   supabase login
   supabase link          # pick the new project
   supabase db push       # applies supabase/migrations/
   supabase functions deploy review-action
   ```

3. Put the new URL and public `anon` key in `apps/analyst-console/supabase-config.js`.
4. Update `SUPABASE_URL` and `SUPABASE_SECRET_KEY` in the local `.env` and in the
   GitHub repository secrets.
5. Recreate the analyst accounts in the dashboard (Authentication → Users).
   Analyst edits, review decisions and audit logs that lived only in the old
   project are not recoverable from this repository.
6. Run `make supabase-cycle` locally, then dispatch the "Supabase Sync" workflow
   and close the tracking issue.

