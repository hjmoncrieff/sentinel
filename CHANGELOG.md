# SENTINEL Changelog

This file records major project changes.

Each major change entry should include:
- date
- affected areas
- summary of what changed
- validation completed
- remaining risks or follow-up

## 2026-06-05

## 2026-06-06

### Editorial System Redesign Spec

Affected areas:
- `docs/superpowers/specs/2026-06-06-sentinel-editorial-system-redesign-design.md`

What changed:
- Wrote the approved public-site editorial redesign spec capturing the selected `C2 — Editorial Oxide` palette, the `B — Editorial System` sitewide direction, and the rule that `Events` stays the most operational tab.
- Documented shared visual-system rules for palette roles, typography, surface treatment, active states, and tab-by-tab application across `Overview`, `Countries`, `OC`, `US-LATAM`, `Events`, and `About`.
- Recorded the rollout order, design risks, and validation criteria so later implementation work can stay aligned with the approved publication identity.

Validation completed:
- Reviewed the written spec for placeholders, contradictions, ambiguity, and scope.

Remaining risks / follow-up:
- The written spec still needs user review and approval before implementation planning begins.
- The approved design direction has not yet been translated into a detailed implementation plan.

### Editorial System Implementation Plan

Affected areas:
- `docs/superpowers/plans/2026-06-06-sentinel-editorial-system-redesign.md`

What changed:
- Added the execution plan for the approved public-site editorial redesign, including the public-dashboard Playwright harness, shared palette rollout, dossier-surface application across `Countries`, `OC`, and `US-LATAM`, the operational `Events` treatment, and the `About` methods-note rewrite.
- Locked the redesign work to the current public-dashboard architecture so implementation stays grounded in `index.html`, `assets/css/dashboard.css`, `assets/js/dashboard.js`, and the existing smoke workflow rather than inventing a new component system first.

Validation completed:
- Reviewed the plan against the approved design spec for coverage, naming consistency, and placeholder-free task detail.

Remaining risks / follow-up:
- The plan still needs to be executed task by task in the working tree.
- The earlier spec entry above reflects the state before approval; the approved plan supersedes its “pending planning” note.

### Public Country Trend Visibility Follow-up

Affected areas:
- `index.html`
- `assets/css/dashboard.css`

What changed:
- Changed the public country-profile structural and predictive trend cards so their year-range sparkline panels are visible by default instead of being hidden behind hover-only behavior.
- Added a cache-busting asset version to both the public dashboard CSS and JS includes so the in-app browser and localhost sessions pick up the updated trend rendering immediately after refresh.

Validation completed:
- `node --check assets/js/dashboard.js`
- `curl -s http://localhost:8000/index.html | rg "20260606-trends-visible"`

Remaining risks / follow-up:
- The already-open browser tab still needs a manual refresh to load the new asset URLs.
- A fuller browser-level interaction smoke is still worth re-running once in-app browser control is available again.

### Country Profile Redesign And Event Brief Overhaul

Affected areas:
- `index.html`
- `assets/js/dashboard.js`
- `assets/css/dashboard.css`

What changed:
- Reorganized the public country profile around a stronger monitor brief, with the opening section now combining the predictive summary, watchpoints, and compact KPI cards instead of repeating the same story across separate summary and risk strips.
- Added a dedicated `Economy & State Capacity` panel so GDP per capita, inflation, population, defence burden, aid, and rule-of-law context sit alongside the political-risk story rather than being buried in generic reference rows.
- Replaced the older context/reference band layout with cleaner briefing panels for institutional context, leadership and election timing, and the dossier data window.
- Upgraded the live-event presentation from a metadata-heavy event card into a field-note format with tighter list summaries, event tags, a clearer `What happened / Why it matters` split, and monitor-relevance cues.
- Bumped the public dashboard asset version again so browsers pick up the redesigned country-profile CSS and JS on refresh.

Validation completed:
- `node --check assets/js/dashboard.js`
- `curl -s http://localhost:8000/index.html | rg "20260606-country-overhaul"`
- `curl -s http://localhost:8000/assets/js/dashboard.js | rg "Field Reporting & Event Briefs|Economy & State Capacity|National Monitor Brief"`

Remaining risks / follow-up:
- The open browser tab still needs a refresh to load the overhauled country-profile assets.
- A visual smoke pass in the in-app browser is still worth doing after refresh to tune spacing, copy density, and mobile behavior from the rendered page.

### Sitewide Editorial Coherence Pass

Affected areas:
- `index.html`
- `assets/css/dashboard.css`

What changed:
- Reworked the public dashboard shell around a stronger editorial masthead, including a desk-style SENTINEL lockup and more publication-like navigation treatment.
- Added a sitewide paper-and-dossier visual system with shared background texture, softened gradients, stronger section frames, and more consistent shadows and corner treatment across overview, hero sections, event surfaces, country dossiers, and long-form pages.
- Expanded the homepage from a narrow centered rail into a wider editorial stage so overview sections feel like designed features rather than stacked landing-page blocks.
- Tightened coherence across `Overview`, `Events`, `Countries`, `OC`, `US–LatAm`, and `About` by aligning hero cards, section surfaces, and the persistent log bar to the same visual language.
- Bumped the public asset version again so browsers refresh into the new editorial shell immediately.

Validation completed:
- `node --check assets/js/dashboard.js`
- `curl -s http://localhost:8000/index.html | rg "20260606-editorial-coherence|Political Risk Desk"`

Remaining risks / follow-up:
- The open browser tab still needs a refresh to load the editorial coherence pass.
- A manual visual review in the in-app browser is still useful to tune any tab-specific spacing that now looks slightly tighter or looser under the shared shell styles.

### Country Brief Interaction Tightening

Affected areas:
- `index.html`
- `assets/js/dashboard.js`
- `assets/css/dashboard.css`

What changed:
- Removed the added top-left `Political Risk Desk` masthead subheading so the SENTINEL wordmark returns to a cleaner single-line lockup.
- Flattened the country navigator cards by removing the stronger gradient treatment and toning down the hover motion so the left rail feels closer to the original dossier navigation.
- Reworked country event briefs from a split list/detail workspace into a single-column accordion list where clicking one item expands it downward in place.
- Updated the accordion behavior so opening one event closes the others automatically.
- Restacked the expanded event-note content into a vertical reading flow rather than side-by-side panes.
- Bumped the asset version again so browsers pick up the interaction and styling changes on refresh.

Validation completed:
- `node --check assets/js/dashboard.js`
- `curl -s http://localhost:8000/index.html | rg "20260606-country-accordion"`

Remaining risks / follow-up:
- The open browser tab still needs a refresh to load the accordion version.
- A quick live click-through in the in-app browser is still worth doing after refresh to confirm the accordion spacing feels right with longer event analyses.

### Homepage Layout Revert

Affected areas:
- `index.html`
- `assets/css/dashboard.css`

What changed:
- Reverted the overview homepage back to its earlier centered, narrower layout and original section/card treatment.
- Removed the homepage-specific overrides from the broader editorial pass while leaving the newer country-profile and event-accordion work intact.
- Bumped the public asset version again so browsers pick up the homepage rollback on refresh.

Validation completed:
- `node --check assets/js/dashboard.js`
- `curl -s http://localhost:8000/index.html | rg "20260606-home-revert"`

Remaining risks / follow-up:
- The open browser tab still needs a refresh to load the reverted homepage assets.

### Shared Country Dossier Contract And Publication Layer

Affected areas:
- `config/schemas/country_dossier_public.schema.json`
- `scripts/analysis/build_country_dossiers.py`
- `scripts/analysis/validate_country_dossiers.py`
- `scripts/analysis/build_country_monitors.py`
- `scripts/publish/publish_dashboard_data.py`
- `scripts/sync/common.py`
- `scripts/sync/push_console_snapshots_to_supabase.py`
- `scripts/sync/export_published_from_supabase.py`
- `tests/test_build_country_dossiers.py`
- `data/published/country_dossiers.json`

What changed:
- Added a canonical public `country_dossiers.json` artifact that emits exactly one public-safe dossier row for each of the 25 monitored countries.
- Added a strict dossier schema, recursive validator, and regression tests covering canonical country identity, public/private field separation, nested payload shape, and null-safe public summary handling.
- Hardened dossier generation against pseudo-country leakage by limiting country monitor row generation to the structural canonical country set.
- Wired dossier generation and validation into the publication layer so published country dossiers are rebuilt and checked alongside other dashboard artifacts.
- Added a dedicated `country_dossiers` snapshot family to the Supabase push/export scripts so the analyst console can adopt the same shared base object after login.
- Added annualized public predictive trajectories for `regime_vulnerability`, `militarization`, and `security_fragmentation`, derived from the monthly modeling panel and dossier-backed into both the public profile view and analyst console country brief.

Validation completed:
- `pytest tests/test_build_country_dossiers.py -q`
- `python3 scripts/analysis/build_country_dossiers.py`
- `python3 scripts/analysis/validate_country_dossiers.py`

Remaining risks / follow-up:
- The public dashboard still needs to switch its country-profile rendering over to the dossier artifact rather than reading older structural sources directly.
- The analyst console snapshot now carries the shared dossier base layer, but the React console still needs a follow-on UI/data wiring pass to consume it.

### Analyst Console Workflow Cleanup Pass

Affected areas:
- `apps/analyst-console/src/app/App.tsx`
- `apps/analyst-console/src/components/shell/filter-manager.tsx`
- `apps/analyst-console/src/components/shell/notification-center.tsx`
- `apps/analyst-console/src/features/actions/release-panel.tsx`
- `apps/analyst-console/src/features/queue/queue-panel.tsx`
- `apps/analyst-console/src/lib/domain/queue.ts`
- `apps/analyst-console/src/lib/domain/types.ts`
- `apps/analyst-console/src/lib/state/console-reducer.ts`
- `apps/analyst-console/src/lib/domain/queue.test.ts`
- `apps/analyst-console/src/lib/state/console-reducer.test.ts`
- `apps/analyst-console/src/app/App.test.tsx`

What changed:
- Added targeted analyst worklists on top of the simpler `All` and `Review now` queue toggle so the console can pivot cleanly into publish-ready, corroboration, registry, and duplicate lanes without bloating the left queue chrome.
- Added a compact queue-health strip in the left column that surfaces ready, corroboration, and registry counts as fast entry points into the highest-value work buckets.
- Reworked the filter navigator into a denser single-sheet control surface so queue scope, worklist, priority, sort, country, and event-type filters can be combined without adding more top-level navigation.
- Added a publish checklist to the release workspace and disabled the ready-for-release action until human review, QA, registry/duplicate, and source-package requirements are satisfied.
- Extended notifications into assignment-style team handoffs with explicit assignment type and due-window metadata that is visible both in the composer and the inbox.

Validation completed:
- `pnpm run analyst-console:typecheck`
- `pnpm run analyst-console:test`
- `pnpm run analyst-console:build`

Remaining risks / follow-up:
- The publish-ready lane is intentionally conservative and may still need tuning once real analyst behavior shows which unresolved cases should remain releasable with note-only exceptions.
- The current notification metadata is client-driven and stored in the existing generic payload shape; if assignment routing becomes a core workflow, the Supabase layer should eventually harden those fields into a more explicit schema.

### Review Queue Priority Rebalance

Affected areas:
- `scripts/review/build_review_queue.py`
- `data/review/review_queue.json`
- `data/review/review_queue_with_edits.json`
- `apps/analyst-console/src/lib/domain/queue.ts`
- `apps/analyst-console/src/lib/api/load-console-workspace.ts`
- `apps/analyst-console/src/lib/domain/types.ts`
- `apps/analyst-console/src/lib/domain/queue.test.ts`
- `apps/analyst-console/src/lib/api/load-console-workspace.test.ts`

What changed:
- Tightened the analyst review-priority rule so `high` is no longer a broad upper bucket driven only by a composite score threshold.
- Updated the queue builder so `high` now requires either an extreme priority score or a genuine blocking condition such as publication risk, strong council disagreement, or multiple QA / registry issues.
- Raised the `medium` cutoff so more routine review items fall back to `low`, which restores separation between urgent queue items and normal supervision load.
- Normalized queue priorities when the analyst console loads snapshots, so stale Supabase or local artifacts with inflated `high` labels are rebalanced in the UI even before the next snapshot sync.
- Updated priority-first sorting so items with the same priority bucket are ordered by `priority_score` before recency.

Validation completed:
- `python3 scripts/review/build_review_queue.py`
- `python3 scripts/review/apply_analyst_edits.py`
- `pnpm run analyst-console:test`
- `pnpm run analyst-console:typecheck`
- `pnpm run analyst-console:build`

Remaining risks / follow-up:
- Supabase snapshot rows already pushed before this change will still exist until the next snapshot sync, though the console now rebalances their priority labels on read.
- The event-level `review_priority` stored in canonical event artifacts is still salience-driven and may merit a separate redesign if other downstream workflows start relying on it more heavily.

### Analyst Console Invite-Only Access Workflow

Affected areas:
- `apps/analyst-console/src/app/App.tsx`
- `apps/analyst-console/src/components/shell/auth-banner.tsx`
- `apps/analyst-console/src/components/shell/access-manager.tsx`
- `apps/analyst-console/src/lib/api/console-invites.ts`
- `apps/analyst-console/src/lib/domain/access.ts`
- `apps/analyst-console/src/lib/domain/types.ts`
- `apps/analyst-console/src/app/App.test.tsx`
- `supabase/functions/review-action/index.ts`
- `supabase/migrations/20260606023519_console_admin_invites.sql`

What changed:
- Added an admin-only access manager to the analyst console so invited-user provisioning now has a real signed-in workflow instead of only explanatory copy on the auth screen.
- Added a Supabase-backed `console_user_invites` audit table plus admin-only RLS policies for invite history and access review.
- Extended the `review-action` Edge Function with an `invite_console_user` action that sends Supabase Auth invitation emails and upserts the invited user profile with the requested console role.
- Updated the signed-out auth surface so it explicitly directs users to contact a Sentinel admin for an invitation rather than implying public registration is available.

Validation completed:
- `pnpm run analyst-console:typecheck`
- `pnpm run analyst-console:test`
- `pnpm run analyst-console:build`

Remaining risks / follow-up:
- The invite flow assumes the legacy `SUPABASE_SERVICE_ROLE_KEY` is available to the Edge Function runtime; migrating this path to `SUPABASE_SECRET_KEYS` is the next security-hardening step.
- This change provisions invited roles and keeps an audit trail, but it does not yet add a separate admin UI for revoking or reassigning existing users after they have already joined.

### Analyst Console Operability, Role Gating, and Artifact Serving

Affected areas:
- `apps/analyst-console/src/app/App.tsx`
- `apps/analyst-console/src/components/shell/`
- `apps/analyst-console/src/features/actions/`
- `apps/analyst-console/src/features/detail/`
- `apps/analyst-console/src/lib/api/`
- `apps/analyst-console/src/lib/domain/`
- `apps/analyst-console/src/lib/state/`
- `vite.config.ts`
- `vitest.config.ts`
- `supabase/functions/review-action/index.ts`
- `supabase/migrations/20260605_000002_expand_registry_and_publish_permissions.sql`

What changed:
- Made the React analyst console operable end to end by wiring the left rail, top workspace state, review actions, release controls, audit history, and registry submission workflow to real app state and Supabase-backed mutations.
- Added role-aware access rules so `ra` users can edit and annotate but cannot publish, while `analyst` and `admin` users can publish and can view restricted AI analysis and country brief surfaces.
- Added dedicated center-panel tabs for event brief, AI analysis, country brief, and source/data inspection so analysts can review the decision surface, model output, and underlying context side by side.
- Added a notification center in the top bar with an inbox, unread count, and event-linked message composer so users can route changes to RAs, analysts, or admins directly from the review workspace.
- Added a manual-event submission workflow so signed-in users can add missed events directly into the analyst review queue when the scraper fails to capture them.
- Added authenticated session handling for console users and local preview fallbacks for the core analyst artifacts when Supabase is unavailable.
- Expanded the Vite artifact-serving layer so local preview and built preview both expose the required review artifacts: review queue, council analyses, country monitors, and actor registry snapshots.
- Updated Vitest boundaries so Playwright specs are no longer collected by the unit test runner.
- Added Supabase-backed `console_notifications` storage plus server-side send/read actions for team notifications.
- Moved the analyst console behind a real sign-in gate so signed-out users no longer see the queue or review surfaces, and removed self-service registration from the public console UI.
- Added Supabase-backed `manual_event_submissions` storage plus queue-side create actions so human-submitted events persist and load back into the queue on authenticated sessions.

Validation completed:
- `pnpm run analyst-console:typecheck`
- `pnpm exec vitest run apps/analyst-console/src/app/App.test.tsx apps/analyst-console/src/lib/state/console-reducer.test.ts apps/analyst-console/src/lib/api/load-console-data.test.ts`
- `pnpm run analyst-console:build`

Remaining risks / follow-up:
- Browser verification should still be rerun after restarting the local analyst-console server so the updated artifact-serving layer is active in the live preview.
- The current role model still accepts a legacy `coordinator` value as analyst-equivalent for compatibility with older profile rows; this can be removed once all profile data is normalized to the three intended roles.

### Analyst Console Shell Cutover and QA Workflow

Affected areas:
- `apps/analyst-console/index.html`
- `apps/analyst-console/src/`
- `.storybook/`
- `playwright.config.ts`
- `tests/analyst-console/`
- `package.json`
- `pnpm-lock.yaml`
- `README.md`

What changed:
- Replaced the temporary analyst-console fallback route with the React shell as the canonical private workspace entry.
- Added the multi-panel review shell, queue workflow, progressive brief surface, and stacked action, release, and audit panels.
- Added Storybook coverage for core analyst-console components, including accessibility addons and local component-state review scripts.
- Added Playwright smoke and visual regression coverage for the analyst-console route and generated the first screenshot baseline.
- Updated the README with the analyst-console UI workflow so local development now points at the Vite shell, Storybook, and Playwright checks directly.

Validation completed:
- `CI=true pnpm analyst-console:test apps/analyst-console/src/app/App.test.tsx`
- `CI=true pnpm analyst-console:typecheck`
- `CI=true pnpm analyst-console:build`
- `CI=true pnpm analyst-console:storybook:build`
- `CI=true pnpm exec playwright test tests/analyst-console/smoke.spec.ts`
- `CI=true pnpm exec playwright test tests/analyst-console/visual.spec.ts --update-snapshots`
- `CI=true pnpm analyst-console:test:visual`

Remaining risks / follow-up:
- The legacy single-file analyst console remains preserved at `apps/analyst-console/legacy/index.legacy.html` as a migration reference, but it is no longer the default entry route.
- Future work should connect the new action controls to live review mutations and add broader browser coverage for additional analyst states.

### Analyst Console Vite/React Scaffold

Affected areas:
- `package.json`
- `pnpm-lock.yaml`
- `vite.config.ts`
- `vitest.config.ts`
- `tsconfig.json`
- `apps/analyst-console/index.html`
- `apps/analyst-console/legacy/index.legacy.html`
- `apps/analyst-console/src/`

What changed:
- Kept `apps/analyst-console/index.html` as the stable static entry and redirected it to the preserved legacy console so the existing analyst workflow does not break during the migration.
- Added `apps/analyst-console/app-shell.html` as the Vite entry for the new React application shell preview.
- Added root Vite, Vitest, and TypeScript configuration for the analyst console app.
- Added the first application bootstrap files: React entrypoint, minimal shell component, test setup, and style/token files.
- Added an `analyst-console:typecheck` script plus React/Node type packages so the TypeScript scaffold validates cleanly.
- Preserved the previous single-file analyst console in `apps/analyst-console/legacy/index.legacy.html` as the migration reference during the redesign.

Validation completed:
- Added the bootstrap test first and confirmed the initial red state with `pnpm vitest run apps/analyst-console/src/app/App.test.tsx` failing because `vitest` was not yet available.
- `CI=true pnpm analyst-console:test apps/analyst-console/src/app/App.test.tsx`
- `CI=true pnpm analyst-console:build`
- `CI=true pnpm analyst-console:typecheck`

Remaining risks / follow-up:
- The React shell is intentionally not the live default route yet; later migration tasks still need to port real workflow panels before cutover.

### Authenticated Review Action Function

Affected areas:
- `supabase/config.toml`
- `supabase/functions/review-action/index.ts`
- `supabase/functions/_shared/cors.ts`
- `apps/analyst-console/index.html`
- `supabase/README.md`
- `docs/supabase-setup.md`

What changed:
- Added a real `review-action` Supabase Edge Function for authenticated analyst write actions.
- Moved analyst-console write operations for event edits, QA resolutions, duplicate resolutions, and registry edits out of direct browser table inserts and behind the Edge Function.
- Kept browser reads on the existing snapshot/table path while making all review writes flow through a single server-side entrypoint that still respects row-level security with the signed-in user context.
- Added shared CORS handling so the browser-based analyst console can call the function cleanly from local and hosted origins.
- Updated the Supabase setup docs to reflect the new browser-to-function write path.

Validation completed:
- Extracted inline analyst-console JavaScript and passed `node --check`
- `deno check supabase/functions/review-action/index.ts`
- `supabase functions serve review-action --env-file .env`
- Authenticated local `GET /functions/v1/review-action` returned supported actions
- Authenticated local `POST /functions/v1/review-action` inserted a smoke-test `event_edit` row under RLS
- Deployed `review-action` to hosted Supabase project `bnlfbxuawhujwvzdufwp`

Remaining risks / follow-up:
- A browser smoke test against the hosted analyst console should still be run with a real analyst account to confirm the configured project URL, auth session, and deployed function all line up in the UI.

### Local Supabase Config Cleanup

Affected areas:
- `supabase/config.toml`
- local Supabase CLI / OrbStack development workflow

What changed:
- Removed a stale `functions.review-action` entry from local Supabase config.
- Aligned the local Supabase project definition with the files that actually exist in the repository so `supabase start` no longer tries to read a missing edge-function entrypoint during boot.
- Upgraded the local Supabase CLI used for local stack management from `2.102.0` to `2.104.0`.

Validation completed:
- `supabase stop`
- `supabase start`
- `supabase status`
- `supabase status -o env`

Remaining risks / follow-up:
- Local status still reports `supabase_imgproxy_sentinel` and `supabase_pooler_sentinel` as stopped. Core API, database, auth, storage, Studio, and Mailpit services are running, so this is not currently blocking SENTINEL's workflow.
- The local project is one CLI release behind latest (`2.105.0` available). Update again later if a specific fix is needed.

## 2026-06-02

### Public Event Taxonomy and Signal Navigation Overhaul

Affected areas:
- `scripts/publish/publish_dashboard_data.py`
- `index.html`
- `data/published/events_public.json`

What changed:
- Added a public-facing editorial category layer for published events so dashboard navigation no longer exposes the raw backend family set as-is.
- Introduced stable public categories: `Power & Command`, `Security Governance`, `Protest & Repression`, `Armed Conflict`, `Crime & Illicit Economies`, `External Security`, `Force Build-Up`, and `Peace & Negotiation`.
- Materialized lexicon-aligned signal families into the published event layer so retrieval logic, analytical signals, and public event coding now speak to each other.
- Reworked the Events drawer so the old `Type` control is now presented honestly as `Domain`, and added first-class `Category` and `Signal` filters beside the existing country/search controls.
- Updated event search and right-rail coding to surface the new `Domain`, `Category`, and `Signal` model instead of relying on the previous flat family labels.
- Removed the need for a public-facing `Other` category by remapping ambiguous backend families into clearer editorial groupings at publication time.

Validation completed:
- `python3 -m py_compile scripts/publish/publish_dashboard_data.py`
- `python3 scripts/publish/publish_dashboard_data.py`
- Extracted inline dashboard JavaScript and passed `node --check`
- Spot-checked published rows to confirm new fields populate, including `public_category_key`, `public_category_label`, `event_signal_families`, and `event_signal_labels`

Remaining risks / follow-up:
- The new category and signal mappings should be visually QA'd in the live Events tab to tune drawer layout and filter discoverability.
- Some borderline events may need category/signal mapping adjustments after a few days of analyst use, especially at the boundary between `Armed Conflict` and `Crime & Illicit Economies` and between `Security Governance` and `Protest & Repression`.

### Central Query Lexicon Scaffold

Affected areas:
- `config/queries/event_query_lexicon.json`

What changed:
- Added a centralized multilingual retrieval lexicon for SENTINEL event discovery and filtering.
- Structured the lexicon around query families that map directly to SENTINEL event types instead of keeping retrieval logic as a flat, scattered keyword bag.
- Added country scopes, multilingual country aliases, regional terms, thematic term sets, actor aliases, false-positive filters, and priority-country overrides.
- Added query-assembly hints for future use across three distinct jobs: pipeline pre-filtering, NewsAPI bundle construction, and source-specific Google News discovery profiles.
- Added a dedicated organized-crime monitor layer covering criminal violence, illicit economies, prison power, extortion systems, illegal extraction, and criminal-governance vocabulary so these signals are not buried inside a generic security bucket.
- Documented a staged integration order so the lexicon can be adopted incrementally without forcing a single large refactor.

Validation completed:
- `python3 -m json.tool config/queries/event_query_lexicon.json`

Remaining risks / follow-up:
- The lexicon is design-ready but not yet wired into `scripts/pipeline_core.py`, `scripts/ingest_newsapi.py`, or `scripts/rss_sources.py`.
- Some country and actor expansions are intentionally concentrated on priority cases; future adoption should add new overrides only when source-audit evidence justifies the added complexity.

### Source Ingestion and Pipeline Overhaul

Affected areas:
- `scripts/rss_sources.py`
- `scripts/extract_article_text.py`
- `scripts/normalize_articles.py`
- `scripts/ingest_rss.py`
- `scripts/ingest_newsapi.py`
- `scripts/ingest_gdelt.py`
- `scripts/ingest_gdelt_events.py`
- `scripts/pipeline_core.py`

What changed:
- Replaced the flat RSS source list with a metadata-rich source registry using `tier`, `role`, `policy`, `languages`, `fetch_limit`, and `quality_weight`.
- Added higher-value investigative and regional sources, including `CONNECTAS`, `La Silla Vacía`, `Vorágine`, `Armando.info`, `TalCual`, and `IDL-Reporteros`.
- Added a lawful full-text extraction layer for sources explicitly marked `public_fulltext`.
- Updated RSS and WordPress archive ingestion to respect per-source fetch depth and carry source metadata into normalized article records.
- Expanded normalized article records to include source trust metadata, extraction status, and optional article body text.
- Upgraded NewsAPI ingestion to use multilingual query sets and preserve language/source-quality metadata.
- Tagged GDELT and bulk GDELT event ingestion as lower-trust discovery sources instead of treating them like flat peers.
- Replaced the old keyword-only pre-filter with a weighted relevance score that uses title, description, body text, country mentions, source role, source tier, and source quality.
- Expanded source auditing so it now reports source tier/role/policy, average filter score, and how much full text was successfully captured.
- Added source-diversity and trusted-source logic to event confidence after clustering.

Validation completed:
- `python3 -m py_compile scripts/rss_sources.py scripts/extract_article_text.py scripts/normalize_articles.py scripts/ingest_rss.py scripts/ingest_newsapi.py scripts/ingest_gdelt.py scripts/ingest_gdelt_events.py scripts/pipeline_core.py`
- Basic import smoke test confirmed registry loads with `44` feeds and `3` archive-backed sources.

Remaining risks / follow-up:
- Newly upgraded direct feed URLs should be smoke-tested live before relying on them in production.
- Full-text extraction is intentionally lawful and conservative; it will not retrieve restricted or paywalled bodies.
- Historical backfills may still need tuning if some archive sources are too slow or too noisy at scale.

### Official Source Endpoint Repair

Affected areas:
- `scripts/pipeline_core.py`
- `scripts/rss_sources.py`

What changed:
- Replaced the blocked DSCA HTML scrape with DSCA's working official Major Arms Sales RSS endpoint.
- Reworked the DEA fetcher to use a Google News discovery feed targeted at `dea.gov` because DEA's official site blocks programmatic access with `403` responses.
- Replaced the broken direct `Animal Político` feed URL with a Google News discovery fallback so the Mexico investigative slot no longer hard-fails on `404`.

Validation completed:
- Verified the DSCA RSS endpoint responds successfully and returns live XML items.
- Verified the prior DEA programmatic endpoints still return `403`, which justified the discovery fallback.

Remaining risks / follow-up:
- DEA remains a discovery-layer workaround rather than a direct official feed because the official site is WAF-blocked.
- `Animal Político` is currently metadata-only via Google News rather than full-text capable until a stable first-party feed or archive endpoint is identified.

### Events Detail / Country Brief Split

Affected areas:
- `index.html`

What changed:
- Removed country-monitor readouts from the Events right rail so the detail panel is event-first instead of mixing country and event context.
- Reorganized the event panel into a clearer sequence: event title, event ID, event description, AI analysis, AI classification, then sources and transparency.
- Moved the country-monitor role more cleanly into the map-side country brief and widened the country brief overlay for a more balanced layout.

Validation completed:
- Manual template and CSS pass completed to remove old monitor-strip/watchpoint dependencies from the event detail structure.

Remaining risks / follow-up:
- The new event/country split should be visually checked in-browser across both file and local server views, especially for long AI analysis blocks and small-screen layouts.

### Missed-Window Pipeline Recovery

Affected areas:
- `data/events.json`
- `data/review/source_audit.json`
- `data/staging/raw_articles.json`
- `data/staging/filtered_articles.json`
- `data/staging/event_article_links.json`

What changed:
- Checked the last committed event-store update and used `2026-04-05` as the historical recovery start point.
- Ran a targeted historical pipeline pass with `python3 scripts/run_pipeline.py --since 2026-04-05` to cover the period that had not been fetched.
- Recovered additional events from RSS, archive, Google News discovery, and repaired official-source paths without relying on a full five-year re-run.

Validation completed:
- Historical recovery run completed successfully.
- Event store increased from `1040` to `1105` total events.
- Source audit and staging artifacts were refreshed during the recovery run.

Remaining risks / follow-up:
- NewsAPI could not contribute to this historical window on the current plan and returned `426 Upgrade Required` for backfill-style queries.
- Public-facing derived layers should be refreshed after the recovery run so monitor outputs stay aligned with the updated live event store.

### Canonical / Review / Publication Refresh

Affected areas:
- `data/canonical/events.json`
- `data/canonical/events.jsonl`
- `data/canonical/articles.json`
- `data/canonical/event_article_links.json`
- `data/canonical/events_actor_coded.json`
- `data/canonical/events_actor_coded.jsonl`
- `data/canonical/actor_mentions.json`
- `data/review/qa_report.json`
- `data/review/duplicate_candidates.json`
- `data/review/council_analyses.json`
- `data/review/review_queue.json`
- `data/review/events_with_edits.json`
- `data/review/country_monitor_validation.json`
- `data/published/events_public.json`
- `data/published/country_monitors.json`

What changed:
- Rebuilt the canonical event layer from the refreshed live event store so the downstream review and publication pipeline reflects the recovered `1105`-event base.
- Re-ran actor coding, QA checks, duplicate detection, analyst-edit application, council analysis generation, and the AI supervision review queue.
- Rebuilt country monitors and re-published the public dashboard data from the refreshed review/canonical layers.
- Moved the public dashboard event layer from the stale `1013` published events to `1097` published events, with `8` events withheld by publication policy.

Validation completed:
- `python3 scripts/pipeline/build_canonical_events.py`
- `python3 scripts/pipeline/code_actors.py`
- `python3 scripts/qa/run_qa.py`
- `python3 scripts/qa/run_registry_qa.py`
- `python3 scripts/pipeline/detect_duplicates.py`
- `python3 scripts/review/apply_analyst_edits.py`
- `python3 scripts/analysis/run_council.py`
- `python3 scripts/review/build_review_queue.py`
- `python3 scripts/analysis/build_country_monitors.py`
- `python3 scripts/analysis/validate_country_monitors.py`
- `python3 scripts/publish/publish_dashboard_data.py`
- Final output counts verified:
  - live events: `1105`
  - canonical actor-coded events: `1105`
  - review queue items: `1062`
  - published dashboard events: `1097`
  - withheld dashboard events: `8`

Remaining risks / follow-up:
- `data/published/country_monitors.json` now contains `50` rows, so the monitor-generation logic should be checked to confirm that this is the intended shape and not a duplicated country layer.
- `data/review/country_monitor_validation.json` flagged `12` countries needing review, so monitor quality should be spot-checked before treating the new monitor layer as finalized.

### Pipeline Cost Logging and Events Navigation Overhaul

Affected areas:
- `scripts/normalize_articles.py`
- `scripts/pipeline_core.py`
- `index.html`

What changed:
- Added canonical URL normalization so tracking-parameter variants and duplicate discovery links collapse before classification.
- Added a raw-ingestion dedupe pass in the pipeline to reduce redundant article classification across RSS, discovery, and verification sources.
- Added Anthropic usage tracking across classification, clustering, and high-salience analysis generation.
- Added a private per-run cost ledger at `data/review/pipeline_run_costs.md` so every future fetch/classification run records token usage, estimated model cost, article counts, and top fetched sources.
- Split the Events tab navigator into distinct search and filter behaviors instead of treating them like one mixed drawer.
- Changed the filter drawer to overlay the Events workspace rather than expanding and reflowing the whole layout.
- Kept the quick-action rail visible while drawers are open so the left-most strip behaves like a real control dock.
- Strengthened the country-brief control under the map with clearer highlighting and a wider overlay card.

Validation completed:
- `python3 -m py_compile scripts/pipeline_core.py scripts/normalize_articles.py scripts/ingest_rss.py scripts/ingest_newsapi.py`
- Extracted inline dashboard JavaScript and passed `node --check`

Remaining risks / follow-up:
- The new cost ledger uses configured estimate rates for `claude-haiku-4-5`; if Anthropic pricing changes, the environment-rate overrides should be updated.
- The Events tab interaction pass should be visually checked over `http://127.0.0.1:8000/` to tune overlay spacing and dock density on smaller screens.

### Countries, OC, and US-LATAM Editorial Integration Refresh

Affected areas:
- `index.html`

What changed:
- Reframed the `Countries`, `OC`, and `US-LATAM` tabs as one connected editorial family instead of three separate destinations.
- Added a shared cross-section bridge to each of the three tabs so users can move between country monitors, organized-crime pressure, and US external-security posture with clearer conceptual continuity.
- Reworked the `Countries` landing surface around anchor cases, regional routes, and a stronger field-brief structure rather than a simple regional summary block.
- Added special focus cards and route cards in the `Countries` tab so the section behaves more like a navigable monitor architecture and less like a static directory.
- Reworked the `OC` section with a clearer frontline-cases block that connects criminal ecosystems back to country-level consequences.
- Tightened the `US-LATAM` section by adding the shared bridge and consolidating duplicated channel/installations material into a cleaner operational-architecture treatment.
- Updated the subregion interaction logic so the new route cards and the existing sidebar subregion controls stay visually in sync.

Validation completed:
- Extracted inline dashboard JavaScript and passed `node --check`

Remaining risks / follow-up:
- The redesign should be visually checked in the live browser, especially the new bridge cards and route-card rhythm at tablet widths.
- The `Countries` regional landing surface may benefit from a second pass if the new anchor-case block should become even more prominent relative to the directory sidebar.

### Lexicon-Wired Retrieval and Events Briefing Upgrade

Affected areas:
- `scripts/query_lexicon.py`
- `scripts/pipeline_core.py`
- `scripts/ingest_newsapi.py`
- `scripts/ingest_rss.py`
- `scripts/rss_sources.py`
- `index.html`

What changed:
- Added a new shared query-lexicon utility module so retrieval logic can be assembled from `config/queries/event_query_lexicon.json` instead of staying split across hard-coded keyword lists.
- Replaced the old flat pre-filter keyword bag with lexicon-driven family matching, multilingual normalized term handling, negative-noise penalties, and retrieval-family tagging on articles.
- Upgraded NewsAPI discovery to build multilingual query bundles from lexicon families rather than relying on three static hand-written strings.
- Updated a large share of Google News-backed source wrappers to use lexicon-derived family terms, especially for organized crime, conflict, repression, and external-security alignment.
- Improved RSS backfill behavior by letting feeds fetch deeper windows when the cutoff is older, with source-specific backfill limits for the highest-value feeds.
- Tightened event granularity by shifting the event ID basis from country+type+week to country+type+day+location, reducing over-collapsing of distinct same-week incidents.
- Enriched the Events right rail with a more substantive `Reporting Synthesis` section, including an expandable event brief derived from linked reporting rather than only the short event summary.
- Reworked the Events search and filter controls so they behave more like distinct tools: darker analyst-console-style triggers, overlay drawer/backdrop behavior, and a more visually prominent country-brief control under the map.
- Reduced country/event duplication in the map overlay by moving country scores into the strip and using the overlay for summary, trend, leading pressure, watchpoints, and the visible event field count.

Validation completed:
- `python3 -m py_compile scripts/query_lexicon.py scripts/pipeline_core.py scripts/ingest_newsapi.py scripts/ingest_rss.py scripts/rss_sources.py scripts/publish/publish_dashboard_data.py`
- Extracted inline dashboard JavaScript and passed `node --check`

Remaining risks / follow-up:
- The lexicon is now wired into pre-filtering and query assembly, but the feed set should still be live-tested to confirm the new Google News query terms produce the intended recall profile.
- The finer-grained event ID scheme will improve event density going forward, but older stored events still reflect the earlier weekly ID logic and may merit a future normalization pass if full historical consistency becomes important.
- The new Events drawer and search overlay should still be checked over `http://127.0.0.1:8000/` to tune spacing and interaction feel in a live browser.

Run results after implementation:
- Ran `python3 scripts/run_pipeline.py` against the live source set to validate the new retrieval logic end to end.
- Live run output:
  - raw articles: `206`
  - filtered articles: `186`
  - candidate events after clustering: `28`
  - new events added: `27`
  - live event store after run: `1132`
  - estimated model cost recorded in `data/review/pipeline_run_costs.md`: `$0.1525`
- Refreshed downstream canonical/review/publication layers after the run:
  - canonical actor-coded events: `1132`
  - review queue items: `1089`
  - published dashboard events: `1124`
  - withheld dashboard events: `8`

### Dashboard Asset Split

Affected areas:
- `index.html`
- `assets/css/dashboard.css`
- `assets/js/dashboard.js`

What changed:
- Split the dashboard's large inline stylesheet out of `index.html` into `assets/css/dashboard.css`.
- Split the dashboard's large inline application script out of `index.html` into `assets/js/dashboard.js`.
- Rewired `index.html` to load the extracted stylesheet and script as static assets while preserving the existing load order and execution position.
- Kept the site architecture static, so the dashboard still works as a single-page app without introducing a build step.

Validation completed:
- Confirmed `index.html` now references `assets/css/dashboard.css` and `assets/js/dashboard.js`.
- Passed `node --check assets/js/dashboard.js`.

Remaining risks / follow-up:
- The split should be visually checked over `http://127.0.0.1:8000/` to confirm there are no asset-path or load-order regressions in the live browser.

### Editorial Section Navigation Cleanup

Affected areas:
- `index.html`
- `assets/css/dashboard.css`

What changed:
- Removed the in-page "connected surface" card rows that behaved like a second tab bar inside the `Countries`, `OC`, and `US-LATAM` sections.
- Replaced them with a quieter editorial orientation strip that explains how each section relates to the others without duplicating page navigation.
- Kept the upper navigation as the only actual control for switching between those top-level sections.

Validation completed:
- Confirmed the new `section-lens-strip` markup replaced the prior `monitor-bridge` rows in all three editorial sections.

Remaining risks / follow-up:
- The updated strip should be checked in the live browser for spacing and visual hierarchy, especially at narrower desktop widths.

### Countries Sidebar Drawer Refresh

Affected areas:
- `index.html`
- `assets/css/dashboard.css`
- `assets/js/dashboard.js`

What changed:
- Reworked the `Countries` left sidebar so the `Visible Countries` and `Subregion` controls no longer stay permanently open at the top of the rail.
- Added a compact sticky `Country navigator` trigger that expands into a dedicated filter drawer, closer to the interaction model used in the `Events` tab.
- Kept the country list itself always visible below the drawer, so the rail remains a live country feed rather than a filter panel first.
- Updated the drawer summary to reflect the active subregion and the current visible-country count.
- Made subregion selection close the drawer after applying the filter, so the rail returns quickly to the country list.

Validation completed:
- Passed `node --check assets/js/dashboard.js`.

Remaining risks / follow-up:
- The new drawer should be checked in the live browser for spacing, sticky behavior, and whether the dark panel feels too heavy or too light relative to the rest of the `Countries` tab.

### Country Profile Editorial Refresh

Affected areas:
- `assets/js/dashboard.js`
- `assets/css/dashboard.css`

What changed:
- Reworked the standard country-profile dossier so the structural indicator strip no longer sits at the bottom of the page.
- Moved the core indicator block closer to the top of the profile, immediately after the country brief, so users see the main country signals earlier.
- Rebuilt the `Live Events` section into an in-profile event field with a selectable event list on the left and a dedicated event briefing panel on the right.
- Removed the old behavior that redirected users into the `Events` tab when they clicked a live event from a country profile.
- The event briefing panel now shows the selected event's title, type, date, location, signal quality, salience, reporting synthesis, SENTINEL assessment, source label, and source link in place.

Validation completed:
- Passed `node --check assets/js/dashboard.js`.

Remaining risks / follow-up:
- The refreshed country dossier should be checked live over `http://127.0.0.1:8000/` for balance between the summary, indicator strip, radar section, and the new event briefing panel.
- A second visual pass may still help tighten spacing inside the country dossier if the top section now feels too dense on smaller desktops.

### Countries Hero Editorial Redesign

Affected areas:
- `index.html`
- `assets/css/dashboard.css`

What changed:
- Reworked the `Countries` landing hero so it no longer shares the same neutral centered-banner feel as the other editorial sections.
- Shifted the hero into a left-aligned field-brief composition with a stronger reading hierarchy, a ribbon of quick orientation tags, and a side panel that explains how to navigate the section.
- Added a more atmospheric visual treatment to the hero so it reads more like a dossier cover than a generic dashboard header.
- Kept the upper navigation as the only tab-level navigation while making the `Countries` opener itself feel more specific to the way the section is used.

Validation completed:
- Checked the updated hero markup and profile-specific CSS wiring in `index.html` and `assets/css/dashboard.css`.

Remaining risks / follow-up:
- The new hero should be visually checked live over `http://127.0.0.1:8000/` to tune balance between the main headline block and the right-hand reading-order panel.

### Editorial Bridge Row Removal

Affected areas:
- `index.html`
- `assets/css/dashboard.css`

What changed:
- Removed the row of in-page editorial bridge cards from `Countries`, `OC`, and `US-LATAM`.
- Simplified those sections so the upper navigation remains the only top-level page switcher.
- Deleted the now-unused `section-lens-*` styling after removing the markup.

Validation completed:
- Confirmed no `section-lens-*` references remain in `index.html` or `assets/css/dashboard.css`.
- Passed `node --check assets/js/dashboard.js`.

Remaining risks / follow-up:
- The simplified sections should be checked live to decide whether the space now feels clean enough or whether one of the following content blocks should move upward slightly.

### Cross-Section Editorial Overhaul (No Pipeline Pass)

Affected areas:
- `index.html`
- `assets/css/dashboard.css`
- `assets/js/dashboard.js`

What changed:
- Reworked the `OC` and `US-LATAM` landing sections around a shared `field-hero` shell so they now read more like dossier openers than generic centered banners.
- Added left-aligned editorial briefing columns, right-hand reading-order panels, tag strips, and section-specific atmospheric treatments for both tabs.
- Tightened cross-tab coherence by aligning the hero language, button emphasis, and section rhythm across `Countries`, `OC`, and `US-LATAM`.
- Added section-specific styling to the `Countries` anchor-case block and the `OC` frontline block so those modules stop reading like generic shared cards.
- Promoted more country-monitor intelligence to the top of the standard country dossier with a new `cp2-monitor-strip` showing overall risk, leading pressure, trend, and current live-field count before the deeper briefing sections.
- Strengthened the country-profile special-monitor button so it behaves more like a primary object and less like a passive tag.
- Renamed regional readout modules in `Countries` from `Construct Snapshot` / `Countries To Watch` to `Regional Monitor Surface` / `Priority Country Readouts` to better match the editorial framing.

Validation completed:
- Passed `node --check assets/js/dashboard.js`.
- Attempted to use the Browser plugin for live localhost inspection, but the in-app browser session was blocked by local URL policy (`ERR_BLOCKED_BY_CLIENT`), so final evaluation relied on direct code review plus the existing browser comments rather than plugin-driven page automation.

Remaining risks / follow-up:
- `OC` and `US-LATAM` should still get a true rendered-browser QA pass once the local browser policy issue is cleared, especially for hero balance and vertical spacing on mid-width desktops.
- The new country dossier monitor strip should be visually checked alongside the radar and live-event field to confirm it does not feel too dense on smaller screens.

### Countries Special Monitor Interaction Alignment

Affected areas:
- `index.html`
- `assets/css/dashboard.css`
- `assets/js/dashboard.js`

What changed:
- Replaced the static `Anchor Cases` block in the `Countries` landing section with a real expandable `Special Monitors` module.
- Matched the interaction pattern of the `US-LATAM` special-focus block: clickable headline, collapsible body, and explicit open/collapse affordance.
- Switched the four featured country cards to open the full special-monitor dossier directly instead of routing through the standard country brief.
- Tuned the special-monitor card styling inside the expanded body so it visually reads as part of the same monitor object rather than a leftover grid of passive cards.

Validation completed:
- Passed `node --check assets/js/dashboard.js`.

Remaining risks / follow-up:
- The new block should be checked live to confirm the expanded state feels proportional inside the `Countries` landing flow and that the special-monitor jump is clearer than the old country-brief path.

### Frontend Coherence and Country Dossier Refactor

Affected areas:
- `index.html`
- `assets/css/dashboard.css`
- `assets/js/dashboard.js`

What changed:
- Refactored top-level tab activation so the dashboard now uses one shared tab-switch path instead of duplicating activation logic in multiple handlers.
- Simplified the collapsed `Events` dock by reducing the number of surfaced quick controls, tightening the collapsed geometry, and consolidating the status chip into one clearer live-state object.
- Reworked the country list buttons into denser monitor cards with clearer risk hierarchy, leading-signal labeling, and live-event counts for faster scanning.
- Reorganized the standard country dossier into larger editorial sections: a shared top deck, a consolidated intelligence grid, and a separate live-field shell instead of a long sequence of visually separate bands.
- Strengthened cross-page control language by bringing the country back button and more of the sidebar/dossier controls closer to the darker, elevated button treatment used elsewhere in the product.
- Pushed the `Countries` lower-page blocks toward the same authored visual language as the hero with stronger panel surfaces, spacing, and layout rhythm.

Validation completed:
- Passed `node --check assets/js/dashboard.js`.
- Confirmed removed quick-control IDs no longer appear in the active frontend code.

Remaining risks / follow-up:
- A true rendered-browser QA pass is still needed to judge whether the reworked country dossier sections feel balanced on desktop and not too compressed on smaller screens.
- The new `Events` dock is intentionally simpler; if it now feels too sparse, the next refinement should be improving the quality of the surfaced controls rather than adding all of the old buttons back.

### Events Drawer Behavior Refinement

Affected areas:
- `assets/css/dashboard.css`

What changed:
- Reduced the visual weight of the `Events` filter drawer so it behaves less like a full-screen modal and more like an attached workspace tool.
- Shrunk both the filter drawer and the search popover, tightened their spacing, and reduced headline/body scale so they no longer dominate the page when opened.
- Removed the dimming/backdrop behavior for the search state so search behaves like a light popover rather than freezing the whole workspace.
- Softened the filter-mode backdrop and blur so the live map and detail rail remain visually present while filtering.

Validation completed:
- CSS-only change; no JS syntax changes required.

Remaining risks / follow-up:
- The live browser should be checked again to judge whether the filter drawer now feels sufficiently attached to the dock or whether it still needs a lighter surface treatment.

### Analyst Console Risk Console Redesign

Affected areas:
- `apps/analyst-console/index.html`

What changed:
- Reframed the analyst console from a light three-panel review page into a darker risk-console shell with a persistent top operations bar, a dedicated left workflow rail, and clearer separation between the live tape, pinned inspector, and release/audit surfaces.
- Moved the primary workflow views (`Core Tape`, `High Salience`, `Release Hold`, `Release Ready`, `Consolidation`, `Exceptions`, `Actor Intel`, `Registry`, `Most Recent`) into a left-side workspace rail so task switching behaves like a true operations console rather than a toolbar afterthought.
- Consolidated top-level analyst controls into a single operations bar for search, priority, grouping, presets, and export/reload/clear actions while preserving the existing review logic and control IDs.
- Added explicit authenticated backend state to the console header and retuned visible language around the selected-event surface so the middle column reads as a pinned inspector and the right column reads as release control.
- Shifted the authenticated analyst console into a darker visual system with higher tape/inspector contrast and more operational affordances while leaving the login/access wall intact.

Validation completed:
- Extracted the inline module script from `apps/analyst-console/index.html` and passed `node --check`.
- Confirmed the new structural IDs used by the console state logic (`workspace-backend`, `workspace-command-toggle-btn`, `queue-count`) appear exactly once in the page.

Remaining risks / follow-up:
- A live browser QA pass is still needed to tune the exact spacing and vertical rhythm of the new left rail and top operations bar on desktop and smaller laptop widths.
- The console now has a stronger shell, but the next logical refinement is improving the lower-priority subpanels and any embedded maps/charts so they inherit the same ops-center language.

### Analyst Console Simplification Pass

Affected areas:
- `apps/analyst-console/index.html`

What changed:
- Simplified the authenticated analyst console so it reads as one queue, one selected-event briefing surface, and one action lane rather than a stack of competing control systems.
- Reduced the left rail to a smaller workflow organizer with the most important review modes surfaced directly and lower-priority modes moved into an `Additional workflows` reveal.
- Split the operations bar into a clearer two-tier command surface: search/filter controls on top and state/action controls below, reducing the sense that every command was competing on one line.
- Narrowed the queue and action columns and gave more width to the selected-event briefing so the main reading surface feels primary instead of squeezed between side controls.
- Reworked the default inspector view so it prioritizes `Event Snapshot`, a smaller set of `Risk Signals`, and collapsible `Country Context` / `Evidence And Links` instead of rendering every secondary monitoring layer at once.
- Renamed key labels (`Review Tape`, `Selected Event`, `Actions`) to reduce the “console about the console” tone and make the authenticated workspace more direct.

Validation completed:
- Extracted the inline module script from `apps/analyst-console/index.html` and passed `node --check`.

Remaining risks / follow-up:
- A live authenticated browser pass is still needed to judge whether the queue column is now too narrow for long headlines and whether the action lane can be reduced even further.
- If the console still feels too busy after this pass, the next step should be collapsing the release/audit tabs into a single progressive workflow rather than adding new controls.

### Public Dashboard Artifact Boundary Hardening

Date:
- 2026-06-05

Affected areas:
- `index.html`
- `assets/js/dashboard.js`
- `scripts/publish/publish_dashboard_data.py`

What changed:
- Removed the public dashboard's runtime dependency on `data/events.json` and `data/review/council_analyses.json`; the browser now hydrates event views directly from `data/published/events_public.json` plus the existing published monitor artifact.
- Normalized published events into the client-side event shape the dashboard already expects, so event cards, detail panels, provenance chips, and country/profile surfaces continue to work without touching private review-layer files.
- Extended the published event artifact with a small publish-safe analysis subset (`public_classification` and `public_ai_generated`) so the event detail surface retains analytical framing after the Supabase split without exposing the full private council record.
- Updated the public log-bar placeholder copy and versioned the dashboard script include so the published site no longer advertises private review-queue state and picks up the new public-only loader path cleanly.

Validation completed:
- Re-ran the public publish step locally to confirm `data/published/events_public.json` still builds with the new fields.
- Checked the dashboard loader for direct references to `data/events.json` and `data/review/` files after the patch.

Remaining risks / follow-up:
- Existing deployed snapshots in Supabase need to be refreshed so the exported `events_public.json` includes the new publish-safe analysis fields everywhere the dashboard is served.
- A browser pass remains worthwhile to confirm the public event detail surface still renders the expected chips and transparency labels against the regenerated artifact.

### Developer Baseline And Smoke-Test Setup

Date:
- 2026-06-05

Affected areas:
- `.mise.toml`
- `.env.example`
- `pyproject.toml`
- `package.json`
- `Makefile`
- `README.md`
- `scripts/dev/playwright_smoke_dashboard.mjs`

What changed:
- Added repo-local runtime pinning with `mise` so the project standardizes on Node 22 and Python 3.13 instead of whatever happens to be installed globally.
- Added `.env.example` so local secrets and service credentials have an explicit bootstrap surface rather than being inferred from docs and scripts alone.
- Added a minimal `pyproject.toml` for Python tooling so Ruff and BasedPyright have a shared config surface without changing the existing runtime/install path.
- Upgraded the Node package surface from a placeholder `npm test` to a usable local workflow with `serve`, `playwright:install`, and `smoke:dashboard` scripts.
- Added a lightweight Playwright smoke test that serves the static dashboard locally, opens the Events view, and verifies that the published event layer loads without browser console errors.
- Added matching `Makefile` and README updates so the new local workflow is discoverable and consistent.

Validation completed:
- Verified the machine-level toolchain and OrbStack/Docker runtime after setup.
- Added a deterministic smoke-test entrypoint for future browser checks.

Remaining risks / follow-up:
- The repo still carries an `npm`-generated lockfile from the initial Playwright bootstrap; if you want strict `pnpm` standardization, the next cleanup step is to convert fully to `pnpm-lock.yaml`.
- The Python tool config is intentionally minimal; the next step would be repo-wide Ruff/BasedPyright enforcement only after auditing current script compatibility.

### Secret Hygiene, Local Supabase Commands, And Starter Bootstrap

Date:
- 2026-06-05

Affected areas:
- `~/.zshrc`
- `~/.config/dev-secrets.zsh`
- `package.json`
- `Makefile`
- `README.md`
- `scripts/dev/bootstrap_next_supabase_openai_app.sh`
- `templates/next-supabase-openai-playwright/README.md`

What changed:
- Moved the inline Anthropic API key out of `~/.zshrc` into a local-only sourced shell file so the interactive shell config no longer carries secrets directly in the main init file.
- Added explicit local Supabase commands for start, stop, status, env export, local DB reset, and local DB push so the container-backed backend workflow is part of the repo’s normal command surface.
- Added Python quality commands for Ruff linting, Ruff formatting, and BasedPyright type checking.
- Added a reusable bootstrap script and starter README for future Next.js + Supabase + OpenAI + Playwright app work so new projects can start from a consistent baseline instead of being assembled manually each time.

Validation completed:
- Verified Docker-compatible OrbStack runtime with a real test container.
- Verified the dashboard Playwright smoke test still passes after the repo command-surface changes.

Remaining risks / follow-up:
- The secret cleanup moved the key into a local shell file, but the next stronger step would be migrating all provider keys into a dedicated password manager or a secrets manager-backed bootstrap flow.
- The new bootstrap script installs the preferred default stack but does not generate app-specific auth/database code; that remains an application-level implementation step.
