# apps/public-site/

The public site. Public. It is built as static files and is the root of the GitHub Pages deploy
(`/sentinel/`); `.github/workflows/pages.yml` builds it into an empty folder and then copies in the
repo's static pages, the published layer and the analyst console.

```bash
node apps/public-site/build.mjs                                  # → dist/public-site/, served from /, preview banner
node apps/public-site/build.mjs --out _site --base /sentinel/ --production   # what the deploy runs
node scripts/dev/smoke_public_site.mjs                           # build, then check every kind of page in Chrome
```

`--production` removes the preview banner and `noindex`, and adds the redirect for old dashboard `#tab` links. The output folder is emptied first; the build refuses a folder that is or contains the repository. Until 2026-10-16 the site was previewed under `/sentinel/next/`; `404.html` redirects those links.

**Not yet coded.** When the model API is unavailable, the nightly run publishes the headlines it collected to `data/published/pending_headlines.json` (`scripts/publish/pending_headlines.py`). The front page and feed then point to `headlines/`, which lists them as reports, not events. The next normal run removes the file.

**Light and dark.** Pages follow the system setting until a visitor uses the switch in the header; the choice is stored as `sentinel-theme` in localStorage and shared with the static pages (`src/client/theme.js`). If the data is more than 48 hours old, the header says "Updates paused since <date>".

The build needs Node 18+ and nothing else. It reads only `data/published/` (the
public-safe layer), plus the two folders below.

| Path | What it is |
|---|---|
| `build.mjs` | Entry point: loads the data, renders every page, copies styles and scripts, writes `data/feed.json` |
| `src/lib/model.mjs` | Build-time data model from `data/published/` and `reference/` |
| `src/lib/geo.mjs` | Decodes the map topology and projects it to SVG paths (build only) |
| `src/lib/html.mjs` | Rendering helpers shared by the build and the browser |
| `src/pages/` | Page templates: `front`, `feed`, `countries` (index and country monitor), `maps`, `layout` |
| `src/client/` | Browser modules: live feed, map interaction, table and timeline behaviour, hover cards (`peek.js`) and the topic-page strip filter (`topic.js`) |
| `src/styles/site.css` | The design tokens and all styles |
| `reference/countries.json` | Country reference: profile, officials, elections, watch notes, military roles, in-depth monitor content. `scripts/reference/refresh_country_reference.py` proposes updates (`proposed`); `scripts/reference/review_reference.py approve` publishes them and sets `reviewed`. Pages show "Under review" while a proposal is pending |
| `reference/changes.json` | Log of every proposal and review decision |
| `reference/americas-topo.json` | Map geometry (world-atlas 110m) |
| `content/weekly.json` | Optional editor-approved weekly note (see below) |
| `content/organized-crime.json`, `content/us-security.json` | Hand-written background for the two topic pages: figures, essays, timeline and access table. Every claim carries a numbered source; `as_of` is the date the facts were last checked |

## Pages

- `/` front page: weekly lede, region map, coverage figures, sections, in-depth monitors
- `/feed/` live feed: every published event, filtered in the browser; state lives in the URL (`?e=<id>&c=<country>&p=<days>`). The right pane shows the country pressure map (bubbles by country for the events in view, dots for located events) until a record is picked; clicking a country filters the list
- `/countries/` regional summary and situation board
- `/countries/<iso3>/` one monitor per country; four carry an in-depth section with a timeline
- `/events/<id>/` one page per record, with sources, coding, provenance and a citation. The id of a folded duplicate forwards to the record that replaced it
- `/organized-crime/` and `/us-security/` topic monitors, computed from published events, the risk-model readings and `data/cleaned/us_assistance.json`
- `/about/` methodology, labels and limitations; the codebook tables are generated from `config/taxonomy/codebook_v3.json`

What a country monitor adds beyond the reference data, all computed at build time:

- **Structural strip.** Each indicator shows the regional median (25 countries) beside the country's value.
- **Events behind a reading.** Each risk reading lists coded events from the past 90 days that count toward it (`event_construct_destinations` in the published layer). Readings with none say they rest on structural indicators.
- **Activity chart.** Events per month for 12 months, stacked by type. The note under it says that early months are under-counted, because collection was irregular before October 2026.
- **Where.** A map of events coded to a town or region in the past 12 months. Country-level events are not drawn; a place outside the country's outline is dropped.
- **US assistance.** Obligations for twelve fiscal years in three groups (see `scripts/structural/fetch_us_assistance.py`).
- **Recent events.** Records of the same story are folded into one row (`groupStories` in `src/lib/model.mjs`: within three days, sharing at least three and at least half of their headline words).
- **In-depth "needs revision".** `in_depth.text_as_of` in `reference/countries.json` is the date the hand-written text was last edited. When the head of state or government took office after it, or a change of leader is awaiting review, the section is flagged. Update `text_as_of` when the text is rewritten.

Maps, charts and the timeline are drawn at build time as SVG, so pages are complete
without scripts. Scripts add filtering and hover behaviour only.

## Weekly note

Without `content/weekly.json`, the front page lede and the regional summary are computed
from the coded events and labelled as automatic. To publish an editor-written note, add:

```json
{"week": "2026-10-05", "approved_by": "HM",
 "lede": {"head": [["Headline text", "<event id>"]], "dek": [["First sentence.", "<event id>"]]},
 "watch": [{"when": "Sun 4 Oct", "rel": "in 3 days", "iso": "BRA", "what": "General election", "note": "…", "ids": ["<event id>"]}],
 "brief": {"paras": [["Sentence with a citation", "<event id>"], [" and one without.", null]]}}
```

It is used only while `week` is within 10 days of the newest event and `approved_by` is set.

## Labels

Outlook is shown as a level; numeric model scores are not shown. Template-written text is
labelled "Automated rule-based"; model-written text is labelled "AI-assisted".
