#!/usr/bin/env python3
"""
SENTINEL — LatAm Civil-Military Monitor
Pipeline: RSS + GDELT + NewsAPI + ACLED → Claude classification + clustering → data/events.json

Features:
  - Four data sources: RSS feeds (curated), GDELT (real-time/geolocated),
    NewsAPI, and ACLED (structured conflict data)
  - Pre-filter with keyword list before spending Claude API tokens
  - Semantic deduplication: Claude clusters articles about the same incident
    and merges them into one record with a `sources` list
  - ID keyed on country+type+ISO week — stable across source title variations
  - Per-event AI analysis for high-salience new events
  - Smart merge: existing events get upgraded (salience, summary, sources, links)
  - Weekly HTML email digest (Mondays)

Required env vars:
  ANTHROPIC_API_KEY

Optional env vars:
  NEWSAPI_KEY
  ACLED_API_KEY / ACLED_EMAIL
  DIGEST_TO / DIGEST_FROM
  SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD
"""

import hashlib
import json
import logging
import os
import re
import smtplib
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

try:
    import anthropic
    import feedparser
    import requests
except ImportError:
    print("Missing dependencies. Run: pip install requests feedparser anthropic", file=sys.stderr)
    sys.exit(1)

# ── Config ─────────────────────────────────────────────────────────────────────

DAYS_BACK      = 2          # RSS / ACLED lookback window
GDELT_TIMESPAN = "4H"       # GDELT API timespan per run
MAX_ACLED_ROWS = 100
CLASSIFY_BATCH = 8          # articles per Claude classification call
CLUSTER_BATCH  = 20         # max candidates per clustering call
MAX_EVENTS     = 500

DATA_FILE = Path(__file__).parent.parent / "data" / "events.json"

GDELT_URL   = "https://api.gdeltproject.org/api/v2/doc/doc"
NEWSAPI_URL = "https://newsapi.org/v2/everything"

RSS_FEEDS = [
    {"name": "InSight Crime",  "url": "https://insightcrime.org/feed/"},
    {"name": "Reuters LatAm",  "url": "https://feeds.reuters.com/reuters/LATopNews"},
    {"name": "NACLA",          "url": "https://nacla.org/rss.xml"},
    {"name": "SOUTHCOM",       "url": "https://www.southcom.mil/RSS/?CH=1"},
]

LATAM_COUNTRIES = [
    "Brazil", "Colombia", "Mexico", "Venezuela", "Argentina", "Peru",
    "Chile", "Ecuador", "Bolivia", "Honduras", "Nicaragua", "Guatemala",
    "El Salvador", "Paraguay", "Uruguay", "Cuba", "Haiti",
    "Dominican Republic", "Panama", "Costa Rica", "Jamaica",
    "Trinidad and Tobago", "Guyana", "Suriname",
]

COUNTRY_CENTROIDS: dict[str, list[float]] = {
    "Brazil":               [-14.2, -51.9],
    "Colombia":             [  4.6, -74.1],
    "Mexico":               [ 23.6, -102.5],
    "Venezuela":            [  6.4, -66.6],
    "Argentina":            [-38.4, -63.6],
    "Peru":                 [ -9.2, -75.0],
    "Chile":                [-35.7, -71.5],
    "Ecuador":              [ -1.8, -78.2],
    "Bolivia":              [-16.3, -63.6],
    "Honduras":             [ 15.2, -86.2],
    "Nicaragua":            [ 12.9, -85.2],
    "Guatemala":            [ 15.8, -90.2],
    "El Salvador":          [ 13.8, -88.9],
    "Paraguay":             [-23.4, -58.4],
    "Uruguay":              [-32.5, -55.8],
    "Cuba":                 [ 21.5, -79.5],
    "Haiti":                [ 18.9, -72.3],
    "Dominican Republic":   [ 18.7, -70.2],
    "Panama":               [  8.5, -80.8],
    "Costa Rica":           [  9.7, -83.8],
    "Jamaica":              [ 18.1, -77.3],
    "Trinidad and Tobago":  [ 10.7, -61.2],
    "Guyana":               [  4.9, -59.0],
    "Suriname":             [  3.9, -56.0],
    "Regional":             [ -5.0, -60.0],
}

ACLED_TYPE_MAP = {
    "Riots":                     "protest",
    "Protests":                  "protest",
    "Violence against civilians": "conflict",
    "Battles":                   "conflict",
    "Explosions/Remote violence": "conflict",
    "Strategic developments":    "other",
}

TYPE_COLORS = {
    "coup":        "#b83232",
    "purge":       "#c46e12",
    "aid":         "#1a538f",
    "protest":     "#6e389a",
    "reform":      "#1a6e52",
    "conflict":    "#a84000",
    "exercise":    "#2e6b8a",
    "procurement": "#7a5c1f",
    "oc":          "#6a4a6e",
    "peace":       "#2d8659",
    "other":       "#6a6560",
}

# Pre-filter: discard articles with none of these before the Claude call
RELEVANCE_KEYWORDS = [
    "military", "army", "coup", "protest", "soldier", "general",
    "forces", "defense", "defence", "minister", "ejército", "fuerzas",
    "militares", "golpe", "policía", "police", "security", "naval",
    "navy", "air force", "guerrilla", "insurgent", "paramilitary",
    "armed group", "cartel", "narco", "operation", "battalion",
    "brigade", "regiment", "deployment", "exercise", "procurement",
    "weapon", "arms", "missile", "drone", "intelligence",
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sentinel")


# ── Helpers ────────────────────────────────────────────────────────────────────

def stable_id(country: str, event_type: str, date: str) -> str:
    """ID keyed on country+type+ISO week — stable across source title variations."""
    try:
        d = datetime.strptime(date, "%Y-%m-%d")
        week = d.strftime("%Y-W%V")
    except Exception:
        week = date[:7]
    key = f"{country.lower()}|{event_type}|{week}"
    return hashlib.sha1(key.encode()).hexdigest()[:12]


# ── Load / save ────────────────────────────────────────────────────────────────

def load_existing() -> dict:
    """Returns a dict keyed by event ID."""
    if not DATA_FILE.exists():
        return {}
    try:
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        events = raw.get("events", raw) if isinstance(raw, dict) else raw
        return {ev["id"]: ev for ev in events if "id" in ev}
    except Exception as e:
        log.warning(f"Could not load existing events: {e}")
        return {}


def save_events(existing: dict, new_events: list[dict]) -> int:
    """Merge new_events into existing, upgrading records when the same ID is seen."""
    added = 0
    sal_rank = {"high": 0, "medium": 1, "low": 2}

    for ev in new_events:
        eid = ev["id"]
        if eid not in existing:
            existing[eid] = ev
            added += 1
        else:
            prev = existing[eid]
            # Merge sources
            prev_sources = prev.get("sources") or ([prev["source"]] if prev.get("source") else [])
            new_sources  = ev.get("sources")  or ([ev["source"]]   if ev.get("source")  else [])
            existing[eid]["sources"] = list(dict.fromkeys(prev_sources + new_sources))
            existing[eid]["source"]  = " · ".join(existing[eid]["sources"])
            # Upgrade salience
            if sal_rank.get(ev.get("salience", "low"), 2) < sal_rank.get(prev.get("salience", "low"), 2):
                existing[eid]["salience"] = ev["salience"]
            # Keep longest summary
            if len(ev.get("summary", "")) > len(prev.get("summary", "")):
                existing[eid]["summary"] = ev["summary"]
            # Merge links
            prev_links = prev.get("links") or ([prev["url"]] if prev.get("url") else [])
            new_links  = ev.get("links")   or ([ev["url"]]   if ev.get("url")   else [])
            existing[eid]["links"] = list(dict.fromkeys(
                l for l in prev_links + new_links if l and l != "#"
            ))
            existing[eid]["url"] = existing[eid]["links"][0] if existing[eid]["links"] else ""

    all_events = sorted(existing.values(), key=lambda e: e.get("date", ""), reverse=True)[:MAX_EVENTS]

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(
        json.dumps({
            "updated": datetime.now(timezone.utc).isoformat(),
            "count":   len(all_events),
            "events":  all_events,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.info(f"Saved {len(all_events)} events to {DATA_FILE}")
    return added


# ── RSS ────────────────────────────────────────────────────────────────────────

def fetch_rss(feed: dict, cutoff: datetime) -> list[dict]:
    log.info(f"RSS: {feed['name']}")
    try:
        parsed = feedparser.parse(feed["url"])
        items = []
        for entry in parsed.entries[:20]:
            pub = entry.get("published_parsed") or entry.get("updated_parsed")
            if pub:
                pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                if pub_dt < cutoff:
                    continue
            else:
                pub_dt = datetime.now(timezone.utc)
            title = (entry.get("title") or "").strip()
            if not title:
                continue
            items.append({
                "title":       title,
                "description": (entry.get("summary") or "")[:500].strip(),
                "url":         entry.get("link", ""),
                "date":        pub_dt.strftime("%Y-%m-%d"),
                "source":      feed["name"],
                "coords":      None,
            })
        log.info(f"  → {len(items)} items")
        return items
    except Exception as e:
        log.error(f"  RSS error {feed['name']}: {e}")
        return []


# ── GDELT ──────────────────────────────────────────────────────────────────────

def fetch_gdelt() -> list[dict]:
    country_codes = "BR OR CO OR MX OR VE OR AR OR PE OR CL OR EC OR BO OR HN OR NI OR GT OR SV OR PY OR UY OR CU OR HT OR DO OR PA OR CR"
    params = {
        "query": (
            "(military OR army OR coup OR protest OR guerrilla OR narco OR naval "
            'OR "armed forces" OR ejército OR fuerzas OR policía OR "security forces") '
            f"sourcecountry:({country_codes})"
        ),
        "mode":       "artlist",
        "maxrecords": "100",
        "timespan":   GDELT_TIMESPAN,
        "format":     "json",
    }
    try:
        resp = requests.get(GDELT_URL, params=params, timeout=30)
        resp.raise_for_status()
        articles = resp.json().get("articles") or []
        log.info(f"GDELT: {len(articles)} raw articles")
        return articles
    except Exception as e:
        log.error(f"GDELT fetch failed: {e}")
        return []


def normalize_gdelt(articles: list[dict]) -> list[dict]:
    out = []
    for a in articles:
        title = (a.get("title") or "").strip()
        if not title:
            continue
        raw_date = (a.get("seendate") or "")[:8]
        try:
            date = datetime.strptime(raw_date, "%Y%m%d").strftime("%Y-%m-%d")
        except Exception:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        lat, lon = a.get("latitude"), a.get("longitude")
        coords = [float(lat), float(lon)] if lat and lon else None
        domain = (a.get("domain") or "GDELT").split(".")[0].title()
        out.append({
            "title":       title,
            "description": title,
            "url":         a.get("url", ""),
            "date":        date,
            "source":      domain,
            "coords":      coords,
        })
    return out


# ── NewsAPI ────────────────────────────────────────────────────────────────────

def fetch_newsapi(api_key: str) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%SZ")
    country_terms = " OR ".join(LATAM_COUNTRIES[:14])
    params = {
        "q": (
            f"(military OR army OR coup OR protest OR \"security forces\" OR guerrilla) "
            f"AND ({country_terms})"
        ),
        "language": "en",
        "sortBy":   "publishedAt",
        "pageSize": "50",
        "from":     since,
        "apiKey":   api_key,
    }
    try:
        resp = requests.get(NEWSAPI_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "ok":
            log.error(f"NewsAPI: {data.get('message', data.get('status'))}")
            return []
        articles = data.get("articles") or []
        log.info(f"NewsAPI: {len(articles)} raw articles")
        return articles
    except Exception as e:
        log.error(f"NewsAPI fetch failed: {e}")
        return []


def normalize_newsapi(articles: list[dict]) -> list[dict]:
    out = []
    for a in articles:
        title = (a.get("title") or "").strip()
        if not title or title == "[Removed]":
            continue
        published = a.get("publishedAt") or ""
        date = published[:10] if published else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        source_name = (a.get("source") or {}).get("name") or "NewsAPI"
        out.append({
            "title":       title,
            "description": (a.get("description") or title)[:500].strip(),
            "url":         a.get("url", ""),
            "date":        date,
            "source":      source_name,
            "coords":      None,
        })
    return out


# ── ACLED ──────────────────────────────────────────────────────────────────────

def fetch_acled(api_key: str, email: str, days_back: int) -> list[dict]:
    log.info("ACLED fetch...")
    date_from = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
    date_to   = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        r = requests.get("https://api.acleddata.com/acled/read", params={
            "key": api_key, "email": email,
            "region":           "6|7|15",
            "event_date":       date_from,
            "event_date_where": "BETWEEN",
            "event_date_end":   date_to,
            "limit":            MAX_ACLED_ROWS,
            "fields":           "event_date|event_type|sub_event_type|country|location|latitude|longitude|actor1|actor2|notes|source",
        }, timeout=30)
        r.raise_for_status()
        rows = r.json().get("data", [])
        log.info(f"  → {len(rows)} ACLED rows")
        return rows
    except Exception as e:
        log.error(f"ACLED error: {e}")
        return []


def acled_to_event(row: dict) -> dict:
    country    = row.get("country", "Unknown")
    lat, lon   = row.get("latitude"), row.get("longitude")
    coords     = [float(lat), float(lon)] if lat and lon else COUNTRY_CENTROIDS.get(country)
    event_type = ACLED_TYPE_MAP.get(row.get("event_type", ""), "conflict")
    actor1     = row.get("actor1", "")
    actor2     = row.get("actor2", "")
    title      = f"{row.get('event_type', 'Event')}: {actor1}" + (f" vs {actor2}" if actor2 else "")
    date       = row.get("event_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    src        = f"ACLED / {row.get('source', '')}".strip(" /")
    return {
        "id":          stable_id(country, event_type, date),
        "type":        event_type,
        "title":       title,
        "summary":     row.get("notes", ""),
        "country":     country,
        "date":        date,
        "source":      src,
        "sources":     [src],
        "conf":        "green",
        "salience":    "medium",
        "coords":      coords,
        "url":         "",
        "links":       [],
        "ai_analysis": None,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Pre-filter ─────────────────────────────────────────────────────────────────

def pre_filter(articles: list[dict]) -> list[dict]:
    kept = []
    for a in articles:
        text = f"{a['title']} {a.get('description', '')}".lower()
        if any(kw in text for kw in RELEVANCE_KEYWORDS):
            kept.append(a)
    log.info(f"Pre-filter: {len(articles)} → {len(kept)} articles retained")
    return kept


# ── Claude classification ──────────────────────────────────────────────────────

CLASSIFY_PROMPT = """\
You are an expert on Latin American civil-military relations. Classify each news item.

For each item [N], respond with ONE JSON line:
{{"idx":N,"relevant":true/false,"type":"coup|purge|aid|protest|reform|conflict|exercise|procurement|oc|peace|other","country":"CountryName or null","salience":"high|medium|low","conf":"green|yellow|red","brief":"One sentence summary."}}

TYPES:
- coup: coup attempt, autogolpe, military takeover, putsch
- purge: officer dismissals, reshuffles, forced retirements, loyalty purges
- aid: foreign military assistance, arms sales, IMET, FMF, security cooperation
- protest: military-adjacent unrest, soldier protests, civil-military street tensions
- reform: SSR, defense reform, civil-military institutional change, oversight legislation
- conflict: armed conflict, guerrilla operations, criminal violence involving security forces
- exercise: joint military exercises, multinational drills, port visits
- procurement: arms purchases, equipment acquisitions, defense contracts
- oc: organized crime involving or targeting security forces
- peace: peace talks, ceasefires, DDR, demobilization
- other: military/security topic with civil-military relevance but no other type fits

conf: green=verified/credible outlet, yellow=single or soft-credibility source, red=unverified/social media only
relevant=true ONLY if there is clear civil-military or defense-institutional relevance.
country must be a recognized Latin American country name, or null if unclear.
Respond ONLY with JSON lines — no preamble, no markdown.

ITEMS:
{items}"""


CLUSTER_PROMPT = """\
You are an expert on Latin American civil-military relations.

Below are {n} classified news items from the past few days.
Some may report the SAME real-world event from different outlets.

Identify groups of items that describe the SAME event.
Two items are the same event if: same country, same event type, same approximate date (within 3 days), and same core incident.

Respond with a JSON array of clusters — each cluster is a list of idx values.
Items that are NOT duplicates appear as singleton clusters [idx].
Example: [[0,3],[1],[2,4,7],[5],[6]]

Respond ONLY with the JSON array, no other text.

ITEMS:
{items}"""


def _classify_batch(client: anthropic.Anthropic, items: list[dict]) -> list[dict]:
    texts = "\n\n".join(
        f"[{i}] TITLE: {it['title']}\nSNIPPET: {it.get('description', '')[:300]}\nSOURCE: {it['source']}"
        for i, it in enumerate(items)
    )
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1200,
            temperature=0,
            messages=[{"role": "user", "content": CLASSIFY_PROMPT.format(items=texts)}],
        )
        lines = msg.content[0].text.strip().split("\n")
        return [json.loads(l) for l in lines if l.strip().startswith("{")]
    except Exception as e:
        log.error(f"Classification batch error: {e}")
        return []


def _cluster_events(client: anthropic.Anthropic, candidates: list[dict]) -> list[list[int]]:
    """Ask Claude to group candidates that describe the same real-world incident."""
    if len(candidates) <= 1:
        return [[i] for i in range(len(candidates))]
    texts = "\n\n".join(
        f"[{i}] TYPE:{ev['type']} COUNTRY:{ev['country']} DATE:{ev['date']}\nTITLE:{ev['title']}\nSUMMARY:{ev.get('summary','')[:200]}"
        for i, ev in enumerate(candidates)
    )
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            temperature=0,
            messages=[{"role": "user", "content": CLUSTER_PROMPT.format(n=len(candidates), items=texts)}],
        )
        raw = msg.content[0].text.strip()
        start = raw.find("[")
        clusters = json.loads(raw[start:])
        log.info(f"  Clustering: {len(candidates)} items → {len(clusters)} clusters")
        return clusters
    except Exception as e:
        log.error(f"Clustering error: {e}")
        return [[i] for i in range(len(candidates))]


def _merge_cluster(events: list[dict]) -> dict:
    """Merge events covering the same incident into one canonical record."""
    if len(events) == 1:
        ev = events[0]
        ev.setdefault("sources", [ev.get("source", "")])
        ev.setdefault("links", [l for l in [ev.get("url")] if l and l != "#"])
        return ev
    sal_rank = {"high": 0, "medium": 1, "low": 2}
    best     = min(events, key=lambda e: sal_rank.get(e.get("salience", "low"), 2))
    sources  = list(dict.fromkeys(
        s for ev in events for s in (ev.get("sources") or [ev.get("source", "")]) if s
    ))
    links    = list(dict.fromkeys(
        l for ev in events for l in (ev.get("links") or ([ev.get("url")] if ev.get("url") else []))
        if l and l != "#"
    ))
    summary  = max((ev.get("summary", "") for ev in events), key=len)
    title    = max((ev.get("title", "")   for ev in events), key=len)
    merged   = {**best}
    merged["title"]   = title
    merged["summary"] = summary
    merged["sources"] = sources
    merged["source"]  = " · ".join(sources)
    merged["links"]   = links
    merged["url"]     = links[0] if links else ""
    return merged


def classify_articles(client: anthropic.Anthropic, articles: list[dict], existing_ids: set[str]) -> list[dict]:
    """Classify, deduplicate, and cluster a list of raw articles into event records."""
    # Dedup against existing store (by stable_id approximation using title+date)
    seen_titles: set[str] = set()
    fresh = []
    for a in articles:
        key = hashlib.sha1(f"{a['title']}{a['date']}".encode()).hexdigest()[:12]
        if key not in existing_ids and key not in seen_titles:
            seen_titles.add(key)
            fresh.append(a)
    log.info(f"Dedup: {len(articles)} → {len(fresh)} fresh articles")

    if not fresh:
        return []

    # Classify in batches
    candidates: list[dict] = []
    now = datetime.now(timezone.utc).isoformat()
    for i in range(0, len(fresh), CLASSIFY_BATCH):
        batch = fresh[i:i + CLASSIFY_BATCH]
        log.info(f"Classifying batch {i // CLASSIFY_BATCH + 1}/{-(-len(fresh) // CLASSIFY_BATCH)}")
        results = _classify_batch(client, batch)
        for r in results:
            idx = r.get("idx", -1)
            if not isinstance(idx, int) or not (0 <= idx < len(batch)):
                continue
            if not r.get("relevant", False):
                continue
            article  = batch[idx]
            country  = r.get("country") or "Regional"
            coords   = article.get("coords") or COUNTRY_CENTROIDS.get(country)
            date     = article["date"]
            ev_type  = r.get("type", "other")
            link     = article.get("url", "")
            candidates.append({
                "id":          stable_id(country, ev_type, date),
                "type":        ev_type,
                "title":       article["title"],
                "summary":     r.get("brief", "") or article.get("description", ""),
                "country":     country,
                "date":        date,
                "source":      article["source"],
                "sources":     [article["source"]],
                "conf":        r.get("conf", "yellow"),
                "salience":    r.get("salience", "medium"),
                "coords":      coords,
                "url":         link,
                "links":       [link] if link and link != "#" else [],
                "ai_analysis": None,
                "ingested_at": now,
            })
        time.sleep(0.5)

    log.info(f"Relevant after classification: {len(candidates)}")
    if not candidates:
        return []

    # Semantic clustering per country
    by_country: dict[str, list] = defaultdict(list)
    for ev in candidates:
        by_country[ev["country"]].append(ev)

    merged_events: list[dict] = []
    for country, evs in by_country.items():
        if len(evs) <= 1:
            merged_events.extend(evs)
            continue
        for i in range(0, len(evs), CLUSTER_BATCH):
            chunk = evs[i:i + CLUSTER_BATCH]
            clusters = _cluster_events(client, chunk)
            for cluster_idxs in clusters:
                group = [chunk[j] for j in cluster_idxs if j < len(chunk)]
                if group:
                    merged_events.append(_merge_cluster(group))
            time.sleep(0.3)

    log.info(f"After clustering: {len(candidates)} → {len(merged_events)} events")
    return merged_events


# ── AI analysis ────────────────────────────────────────────────────────────────

ANALYSIS_PROMPT = """\
In 2-3 sentences, analyze the civil-military significance of this event for {country}.
Be specific and analytical; draw on CMR theory (civilian control, institutional autonomy, \
coup-proofing, security sector reform) where appropriate.

Event: {title}
Summary: {summary}
Type: {type}"""


def generate_analysis(client: anthropic.Anthropic, ev: dict) -> str | None:
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=250,
            temperature=0,
            messages=[{"role": "user", "content": ANALYSIS_PROMPT.format(
                country=ev.get("country", "the region"),
                title=ev.get("title", ""),
                summary=ev.get("summary", ""),
                type=ev.get("type", "other"),
            )}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        log.error(f"Analysis error: {e}")
        return None


# ── Weekly email digest ────────────────────────────────────────────────────────

def _build_digest_html(events: list[dict], days: int = 7) -> str:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    recent = [ev for ev in events if ev.get("date", "") >= cutoff.strftime("%Y-%m-%d")]
    sal_rank = {"high": 0, "medium": 1, "low": 2}
    recent.sort(key=lambda e: (sal_rank.get(e.get("salience", "low"), 2), e.get("date", "")))

    rows = ""
    for ev in recent:
        color    = TYPE_COLORS.get(ev.get("type", "other"), "#6a6560")
        sources  = ev.get("sources") or [ev.get("source", "")]
        src_str  = " · ".join(sources)
        ai_html  = (
            f'<p style="font-style:italic;color:#5a5450;margin:6px 0 0;font-size:12px;">'
            f'{ev["ai_analysis"]}</p>'
        ) if ev.get("ai_analysis") else ""
        links    = ev.get("links") or ([ev["url"]] if ev.get("url") else [])
        link_html = " ".join(
            f'<a href="{l}" style="color:#1a5fa8;font-size:11px;margin-right:8px;">Read →</a>'
            for l in links[:3]
        )
        rows += f"""
        <tr><td style="padding:16px 0;border-bottom:1px solid #e8e4dd;vertical-align:top;">
          <div style="margin-bottom:6px;">
            <span style="background:{color};color:white;font-family:monospace;font-size:9px;padding:2px 7px;border-radius:2px;text-transform:uppercase;letter-spacing:1px;">{ev.get("type","other")}</span>
            <span style="font-family:monospace;font-size:10px;color:#9a9490;margin-left:8px;">{ev.get("country","—")}</span>
            <span style="font-family:monospace;font-size:10px;color:#b8b4b0;margin-left:8px;">{ev.get("date","")}</span>
          </div>
          <p style="margin:0 0 5px;font-size:14px;font-weight:500;color:#1c1a17;line-height:1.4;">{ev.get("title","")}</p>
          <p style="margin:0 0 5px;font-size:12px;color:#5a5450;line-height:1.65;">{ev.get("summary","")}</p>
          {ai_html}
          <p style="margin:8px 0 0;font-family:monospace;font-size:9px;color:#b0aca8;">Sources: {src_str}</p>
          {link_html}
        </td></tr>"""

    date_range  = f"{cutoff.strftime('%b %d')} – {datetime.now(timezone.utc).strftime('%b %d, %Y')}"
    high_count  = sum(1 for e in recent if e.get("salience") == "high")
    n_countries = len(set(e.get("country") for e in recent))

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f5f2ed;font-family:Georgia,serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f2ed;padding:32px 0;">
<tr><td align="center">
<table width="620" cellpadding="0" cellspacing="0" style="background:#fffff8;border:1px solid #e0dbd2;">
  <tr><td style="padding:28px 32px;border-bottom:1px solid #e0dbd2;">
    <h1 style="margin:0;font-size:22px;color:#1c1a17;font-weight:600;">Sentinel<span style="color:#b83232;">.</span></h1>
    <p style="margin:4px 0 0;font-family:monospace;font-size:9px;color:#9a9490;letter-spacing:2px;text-transform:uppercase;">Weekly Civil-Military Digest · Latin America</p>
    <p style="margin:5px 0 0;font-family:monospace;font-size:11px;color:#b0aca8;">{date_range}</p>
  </td></tr>
  <tr><td style="padding:14px 32px;background:#f0ece4;border-bottom:1px solid #e0dbd2;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td align="center"><b style="font-family:monospace;font-size:20px;color:#1c1a17;">{len(recent)}</b><br><span style="font-family:monospace;font-size:9px;color:#9a9490;text-transform:uppercase;letter-spacing:1px;">Events</span></td>
      <td align="center"><b style="font-family:monospace;font-size:20px;color:#b83232;">{high_count}</b><br><span style="font-family:monospace;font-size:9px;color:#9a9490;text-transform:uppercase;letter-spacing:1px;">High Salience</span></td>
      <td align="center"><b style="font-family:monospace;font-size:20px;color:#1c1a17;">{n_countries}</b><br><span style="font-family:monospace;font-size:9px;color:#9a9490;text-transform:uppercase;letter-spacing:1px;">Countries</span></td>
    </tr></table>
  </td></tr>
  <tr><td style="padding:0 32px;">
    <table width="100%" cellpadding="0" cellspacing="0">
    {rows or '<tr><td style="padding:24px 0;color:#9a9490;font-family:monospace;font-size:12px;">No events this week.</td></tr>'}
    </table>
  </td></tr>
  <tr><td style="padding:18px 32px;border-top:1px solid #e0dbd2;background:#f0ece4;">
    <p style="margin:0;font-family:monospace;font-size:9px;color:#b0aca8;line-height:1.8;">
      Sentinel · LatAm Civil-Military Monitor<br>
      Generated automatically · Powered by Claude + GDELT + RSS + ACLED
    </p>
  </td></tr>
</table></td></tr></table></body></html>"""


def send_digest(events: list[dict]) -> None:
    if datetime.now(timezone.utc).weekday() != 0:  # Monday only
        log.info("Not Monday — skipping digest.")
        return

    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASSWORD", "")
    from_addr = os.environ.get("DIGEST_FROM", smtp_user)
    to_addr   = os.environ.get("DIGEST_TO", "")

    if not all([smtp_user, smtp_pass, to_addr]):
        log.info("Email digest skipped — SMTP env vars not set.")
        return

    html = _build_digest_html(events)
    msg  = MIMEMultipart("alternative")
    msg["Subject"] = f"Sentinel Weekly Digest — {datetime.now(timezone.utc).strftime('%b %d, %Y')}"
    msg["From"]    = from_addr
    msg["To"]      = to_addr
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as srv:
            srv.starttls()
            srv.login(smtp_user, smtp_pass)
            srv.sendmail(from_addr, to_addr, msg.as_string())
        log.info(f"Digest sent to {to_addr}")
    except Exception as e:
        log.error(f"Digest send failed: {e}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    log.info("=== SENTINEL pipeline starting ===")

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set.")

    client   = anthropic.Anthropic(api_key=anthropic_key)
    cutoff   = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
    existing = load_existing()
    existing_ids = set(existing.keys())
    log.info(f"Existing events in store: {len(existing)}")

    # ── 1. Fetch all sources ───────────────────────────────────────────────────
    all_articles: list[dict] = []

    # RSS (curated civil-military sources)
    for feed in RSS_FEEDS:
        all_articles.extend(fetch_rss(feed, cutoff))
        time.sleep(0.3)

    # GDELT (real-time, geolocated)
    all_articles.extend(normalize_gdelt(fetch_gdelt()))

    # NewsAPI
    newsapi_key = os.environ.get("NEWSAPI_KEY", "")
    if newsapi_key:
        all_articles.extend(normalize_newsapi(fetch_newsapi(newsapi_key)))
    else:
        log.info("No NEWSAPI_KEY — skipping NewsAPI")

    log.info(f"Total raw articles: {len(all_articles)}")

    # ── 2. Pre-filter ─────────────────────────────────────────────────────────
    relevant = pre_filter(all_articles)

    # ── 3. Classify + cluster ─────────────────────────────────────────────────
    new_events = classify_articles(client, relevant, existing_ids)

    # ── 4. ACLED (already structured — skip classification) ───────────────────
    acled_key   = os.environ.get("ACLED_API_KEY", "")
    acled_email = os.environ.get("ACLED_EMAIL", "")
    if acled_key and acled_email:
        rows = fetch_acled(acled_key, acled_email, DAYS_BACK)
        for row in rows:
            new_events.append(acled_to_event(row))
    else:
        log.info("ACLED not configured — skipping.")

    # ── 5. AI analysis for high-salience truly-new events ─────────────────────
    truly_new   = [ev for ev in new_events if ev["id"] not in existing_ids]
    high_new    = [ev for ev in truly_new if ev.get("salience") == "high"]
    log.info(f"Generating AI analysis for {len(high_new)} high-salience new events...")
    for ev in high_new:
        ev["ai_analysis"] = generate_analysis(client, ev)
        time.sleep(0.5)

    # ── 6. Save ───────────────────────────────────────────────────────────────
    added = save_events(existing, new_events)
    log.info(f"Done. {added} new events added. Total: {len(existing) + added}")

    # ── 7. Weekly digest ──────────────────────────────────────────────────────
    all_saved = list(existing.values())
    send_digest(all_saved)

    log.info("=== SENTINEL pipeline complete ===")


if __name__ == "__main__":
    main()
