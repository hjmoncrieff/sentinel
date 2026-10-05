# apps/public-site/

The redesigned public site. Public. It is built as static files and currently deployed
as a preview at `/sentinel/next/`, next to the existing dashboard (`index.html` at the
repo root), which stays in place until the redesign is approved section by section.

```bash
node apps/public-site/build.mjs                       # → dist/public-site/, served from /
node apps/public-site/build.mjs --base /sentinel/next/ --legacy /sentinel/ --out _site/next
cd dist/public-site && python3 -m http.server 8731    # preview locally
```

The build needs Node 18+ and nothing else. It reads only `data/published/` (the
public-safe layer), plus the two folders below.

| Path | What it is |
|---|---|
| `build.mjs` | Entry point: loads the data, renders every page, copies styles and scripts, writes `data/feed.json` |
| `src/lib/model.mjs` | Build-time data model from `data/published/` and `reference/` |
| `src/lib/geo.mjs` | Decodes the map topology and projects it to SVG paths (build only) |
| `src/lib/html.mjs` | Rendering helpers shared by the build and the browser |
| `src/pages/` | Page templates: `front`, `feed`, `countries` (index and country monitor), `maps`, `layout` |
| `src/client/` | Browser modules: live feed, map interaction, table and timeline behaviour |
| `src/styles/site.css` | The design tokens and all styles |
| `reference/countries.json` | Hand-maintained country reference: profile, key positions, elections, watch notes, military roles, in-depth monitor content. Set `reviewed` to a date when an entry is checked; pages show "Not yet reviewed" until then |
| `reference/americas-topo.json` | Map geometry (world-atlas 110m) |
| `content/weekly.json` | Optional editor-approved weekly note (see below) |

## Pages

- `/` front page: weekly lede, region map, coverage figures, sections, in-depth monitors
- `/feed/` live feed: every published event, filtered in the browser; state lives in the URL (`?e=<id>&c=<country>&p=<days>`)
- `/countries/` regional summary and situation board
- `/countries/<iso3>/` one monitor per country; four carry an in-depth section with a timeline

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
