# Public Site

This is the operator reference for the public website at
<https://hjmoncrieff.github.io/sentinel/>. It is deployed by `.github/workflows/pages.yml`
(GitHub Pages source: **GitHub Actions**).

## Pages

| Page | Purpose |
|---|---|
| `index.html` | The dashboard. Tabs are deep-linkable, e.g. `#events`, `#profiles`, `#about` |
| `404.html` | Custom not-found page. GitHub Pages serves it for any missing path |
| `privacy.html` | Privacy policy. Includes a control to reset analytics consent |
| `terms.html` | Terms of use, data limitations, and citation |
| `thank-you.html` | Destination after a weekly-brief signup succeeds (`noindex`) |
| `apps/analyst-console/` | React analyst console, built at deploy time. Invite-only Supabase sign-in; `noindex, nofollow` |

## Shared pieces

- **`assets/js/site.js`** is the single place for site configuration. It sets the site URL,
  the repo and issues links, the Formspree form endpoint, and analytics. It also runs the
  consent banner.
- **`assets/css/site.css`** styles the consent banner, the static pages (`.page`), and the
  footers.
- **Icons** are in `assets/icons/`: `favicon.svg`, `favicon-32.png`, `apple-touch-icon.png`,
  `icon-192.png`, and `icon-512.png`. The manifest is `site.webmanifest`.
- **The social card** is `assets/og/sentinel-og.png`, 1200×630. Its source is
  `assets/og/og-card.html`.
- **Regenerate icons and the card** with
  `bash scripts/site/render_brand_assets.sh <python-with-Pillow>`. It needs Chrome, and it
  palette-compresses the PNGs.
- **Crawler files:** `robots.txt` and `sitemap.xml`.

## Owner actions

1. **Enable analytics (optional).** Create a GoatCounter site, then set
   `analytics.code` in `assets/js/site.js`. The consent banner appears automatically after
   that, and nothing loads without an explicit *Allow*. The privacy page already describes
   this setup.
2. **Weekly brief delivery.** Signups post to the Formspree endpoint and reach the
   maintainers. Sending the brief to subscribers is not automated, so someone has to add
   each address to the distribution list.
3. **Contact.** The site offers the feedback form (Formspree) and GitHub issues. To publish a
   dedicated email address, add it to the privacy, terms, and About contact sections.
4. **Custom domain.** If the site moves off `/sentinel/`, update:
   - `<base href>` in `404.html`
   - every canonical and `og:url` URL
   - `sitemap.xml`, `robots.txt`, and `SENTINEL_SITE.url`

   `robots.txt` only takes effect at a domain root, so it starts working once the site
   has its own domain.

## Deployment

`.github/workflows/pages.yml` runs on every push to `main`. It also runs after each
successful Daily Pipeline or Supabase Sync run, because bot data commits use `[skip ci]`,
which suppresses push triggers. Each run:

1. Builds the console with `CONSOLE_BASE=/sentinel/ CONSOLE_DEPLOY=1 pnpm analyst-console:build`.
   Its bundles land in `dist/apps/analyst-console/`, and no workspace JSON is copied.
2. Copies the repo into `_site/`, excluding the console source, tests, and tooling.
3. Places the built console over `apps/analyst-console/`.
4. Deletes `data/review`, `data/gold`, `data/modeling`, and `data/staging` from `_site/` as a
   second safeguard. Those folders are already gitignored apart from templates.
5. Deploys with `actions/deploy-pages`.

The console gets review data only from Supabase, after sign-in, under row-level security.
Without a session it shows the sign-in screen and requests no private files.

## Data loading

The dashboard fetches `data/published/*.json` with `cache: 'no-cache'`. The browser
revalidates with the ETag, so an unchanged dataset (about 9 MB) comes back as a 304 instead
of being downloaded again. While data loads, the Events list shows a status message. If the
load fails, it shows a Retry button. If the last publication is more than 48 hours old, the
status bar says "Updates paused" instead of "Pipeline active".
