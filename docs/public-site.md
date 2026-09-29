# Public Site

This is the operator reference for the public website at
<https://hjmoncrieff.github.io/sentinel/>, which is served by GitHub Pages from the repo root.

## Pages

| Page | Purpose |
|---|---|
| `index.html` | The dashboard. Tabs are deep-linkable, e.g. `#events`, `#profiles`, `#about` |
| `404.html` | Custom not-found page. GitHub Pages serves it for any missing path |
| `privacy.html` | Privacy policy. Includes a control to reset analytics consent |
| `terms.html` | Terms of use, data limitations, and citation |
| `thank-you.html` | Destination after a weekly-brief signup succeeds (`noindex`) |
| `apps/analyst-console/` | Private console (`noindex, nofollow`) |

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

## Data loading

The dashboard fetches `data/published/*.json` with `cache: 'no-cache'`. The browser
revalidates with the ETag, so an unchanged dataset (about 9 MB) comes back as a 304 instead
of being downloaded again. While data loads, the Events list shows a status message. If the
load fails, it shows a Retry button. If the last publication is more than 48 hours old, the
status bar says "Updates paused" instead of "Pipeline active".
