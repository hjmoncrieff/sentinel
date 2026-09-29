# Next + Supabase + OpenAI + Playwright Starter

This template is the default bootstrap path for new app and web projects on
this machine.

What it gives you:

- **Next.js** for the web app shell and API routes
- **Supabase** for Postgres, auth, storage, and realtime
- **OpenAI SDK** for model calls
- **Playwright** for browser smoke tests and end-to-end checks
- **Zod** for input and env validation
- **TanStack Query** for client-side data fetching
- **React Hook Form** for form state
- **mise** runtime pinning
- **pnpm** package management

## Bootstrap

From the repo root:

```bash
bash scripts/dev/bootstrap_next_supabase_openai_app.sh my-app
```

That script creates a new Next.js app and installs the core dependencies used
for AI-enabled product work.

## After Bootstrap

Inside the new app directory:

```bash
pnpm exec playwright install chromium
cp .env.example .env.local
```

Then fill in:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`
- `SUPABASE_SERVICE_ROLE_KEY` when needed server-side
- `OPENAI_API_KEY`

## Default stack

- App framework: `next`
- Auth / DB / Storage: `@supabase/supabase-js`, `@supabase/ssr`
- AI: `openai`
- Validation: `zod`
- Data fetching: `@tanstack/react-query`
- Forms: `react-hook-form`
- QA: `playwright`
