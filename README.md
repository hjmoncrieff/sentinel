# SENTINEL — LatAm Civil-Military Monitor

A quasi-automated dashboard that monitors civil-military events in Latin America.  
Nightly GitHub Actions pipeline → RSS + ACLED → Claude classification → `data/events.json` → dashboard.

---

## Repository structure

```
sentinel/
├── .github/workflows/fetch_events.yml   ← nightly GitHub Action
├── scripts/fetch_events.py              ← Python pipeline
├── data/events.json                     ← auto-updated event store
└── index.html                           ← dashboard (reads events.json)
```

---

## Setup (one-time, ~15 minutes)

### Step 1 — Create a GitHub repository

1. Go to [github.com](https://github.com) and sign in
2. Click **+** → **New repository**
3. Name it `sentinel` (or anything you like)
4. Set visibility to **Public** (required for free GitHub Pages hosting) or Private
5. Do **not** initialize with a README — you'll push files yourself
6. Click **Create repository**

---

### Step 2 — Upload the files

You have two options:

**Option A — GitHub web interface (no Git needed):**
1. In your new repo, click **Add file → Upload files**
2. Upload in this order, recreating the folder structure:
   - `index.html` (root)
   - `data/events.json` (create `data/` folder first via "Create new file → data/events.json")
   - `.github/workflows/fetch_events.yml`
   - `scripts/fetch_events.py`

**Option B — Git command line:**
```bash
git clone https://github.com/YOUR_USERNAME/sentinel.git
cd sentinel
# copy all files into this folder preserving structure
git add .
git commit -m "Initial commit"
git push
```

---

### Step 3 — Add API keys as GitHub Secrets

1. In your repo, go to **Settings → Secrets and variables → Actions**
2. Click **New repository secret** for each of the following:

| Secret name        | Value                              |
|--------------------|------------------------------------|
| `ANTHROPIC_API_KEY`| Your Anthropic API key (`sk-ant-…`)|
| `ACLED_API_KEY`    | Your ACLED API key                 |
| `ACLED_EMAIL`      | Email registered with ACLED        |

> **ACLED access:** Register for free at [acleddata.com/register](https://acleddata.com/register/).  
> Select "Academic" access. Approval is usually same-day.

---

### Step 4 — Enable GitHub Pages

1. Go to **Settings → Pages**
2. Under **Source**, select **Deploy from a branch**
3. Branch: `main`, folder: `/ (root)`
4. Click **Save**
5. After ~1 minute, your dashboard will be live at:  
   `https://YOUR_USERNAME.github.io/sentinel/`

---

### Step 5 — Run the pipeline for the first time

1. Go to the **Actions** tab in your repo
2. Click **Fetch LatAm Military Events** in the left sidebar
3. Click **Run workflow → Run workflow**
4. Watch the logs — the run takes 2–4 minutes
5. When complete, `data/events.json` will have your first events
6. Refresh your GitHub Pages URL to see them on the map

After this, the pipeline runs automatically every night at 04:00 UTC.

---

### Step 6 — (Optional) View locally

```bash
# From the repo root — Python's built-in server handles the fetch() to data/events.json
python -m http.server 8000
# Open http://localhost:8000
```

> **Note:** Opening `index.html` directly as a file (`file://`) will fail because  
> browsers block `fetch()` on local files. Always use a local server.

---

## How the pipeline works

1. **RSS fetching** — Pulls last 2 days from InSight Crime, Reuters LatAm, NACLA, SOUTHCOM
2. **ACLED fetch** — Queries ACLED API for regions 6/7/15 (Central America, South America, Caribbean)
3. **Claude classification** — Batches of 8 items sent to `claude-sonnet-4-20250514` for relevance filtering and event typing (coup / purge / aid / protest / reform / conflict)
4. **AI analysis** — High-salience new events get a 2–3 sentence civil-military analysis
5. **Deduplication** — Events are keyed by SHA-1 hash of title + date; no duplicates accumulate
6. **Persistence** — `data/events.json` keeps the latest 500 events, sorted by date
7. **Commit** — The Action commits the updated JSON back to the repo; GitHub Pages serves it automatically

---

## Customization

| What to change | Where |
|----------------|-------|
| Add/remove RSS feeds | `scripts/fetch_events.py` → `RSS_FEEDS` list |
| Change schedule | `.github/workflows/fetch_events.yml` → `cron:` line |
| Adjust days-back window | `scripts/fetch_events.py` → `DAYS_BACK = 2` |
| Add event types | Both `fetch_events.py` prompt and `index.html` `TYPE_COLORS` dict |
| Change max stored events | `fetch_events.py` → `[:500]` slice in `save_events()` |

---

## Notes on CORS and local RSS

The Python pipeline runs server-side (GitHub Actions), so there are no CORS restrictions.  
The dashboard only reads `data/events.json` — no live API calls from the browser except  
optional on-demand Claude analysis in the detail panel (requires entering your API key in the UI).
