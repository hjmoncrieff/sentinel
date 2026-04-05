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

from ingest_gdelt import fetch_gdelt, fetch_gdelt_historical, normalize_gdelt
from ingest_newsapi import fetch_newsapi, normalize_newsapi
from ingest_rss import fetch_all_archives, fetch_rss
from normalize_articles import make_article_record
from rss_sources import RSS_FEEDS

# ── Load .env file if present (local development) ─────────────
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            _k, _v = _k.strip(), _v.strip()
            if _v:  # only write non-empty values so blank optionals don't clobber
                os.environ[_k] = _v

try:
    import anthropic
    import requests
except ImportError:
    print("Missing dependencies. Run: pip install requests anthropic", file=sys.stderr)
    sys.exit(1)

# ── Config ─────────────────────────────────────────────────────────────────────

DAYS_BACK      = 2          # RSS / ACLED lookback window
MAX_ACLED_ROWS = 100
CLASSIFY_BATCH = 8          # articles per Claude classification call
CLUSTER_BATCH  = 20         # max candidates per clustering call
MAX_EVENTS     = 2500       # increased to support 5-year history

DATA_FILE = Path(__file__).parent.parent / "data" / "events.json"
REVIEW_DIR = Path(__file__).parent.parent / "data" / "review"
STAGING_DIR = Path(__file__).parent.parent / "data" / "staging"

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

# ── Country code lookups ──────────────────────────────────────────────────────
# ISO 3166-1 alpha-3
COUNTRY_ISO3: dict[str, str] = {
    "Brazil": "BRA", "Colombia": "COL", "Mexico": "MEX", "Venezuela": "VEN",
    "Argentina": "ARG", "Peru": "PER", "Chile": "CHL", "Ecuador": "ECU",
    "Bolivia": "BOL", "Honduras": "HND", "Nicaragua": "NIC", "Guatemala": "GTM",
    "El Salvador": "SLV", "Paraguay": "PRY", "Uruguay": "URY", "Cuba": "CUB",
    "Haiti": "HTI", "Dominican Republic": "DOM", "Panama": "PAN",
    "Costa Rica": "CRI", "Jamaica": "JAM", "Trinidad and Tobago": "TTO",
    "Guyana": "GUY", "Suriname": "SUR", "Belize": "BLZ", "Regional": "REG",
}

# Correlates of War numeric codes
COUNTRY_COW_N: dict[str, int] = {
    "Brazil": 140, "Colombia": 100, "Mexico": 70, "Venezuela": 101,
    "Argentina": 160, "Peru": 135, "Chile": 155, "Ecuador": 130,
    "Bolivia": 145, "Honduras": 91, "Nicaragua": 93, "Guatemala": 90,
    "El Salvador": 92, "Paraguay": 150, "Uruguay": 165, "Cuba": 40,
    "Haiti": 41, "Dominican Republic": 42, "Panama": 95, "Costa Rica": 94,
    "Jamaica": 51, "Trinidad and Tobago": 52, "Guyana": 110, "Suriname": 115,
    "Belize": 80,
}

# Correlates of War character codes
COUNTRY_COW_C: dict[str, str] = {
    "Brazil": "BRA", "Colombia": "COL", "Mexico": "MEX", "Venezuela": "VEN",
    "Argentina": "ARG", "Peru": "PER", "Chile": "CHL", "Ecuador": "ECU",
    "Bolivia": "BOL", "Honduras": "HON", "Nicaragua": "NIC", "Guatemala": "GUA",
    "El Salvador": "SAL", "Paraguay": "PAR", "Uruguay": "URU", "Cuba": "CUB",
    "Haiti": "HAI", "Dominican Republic": "DOM", "Panama": "PAN",
    "Costa Rica": "COS", "Jamaica": "JAM", "Trinidad and Tobago": "TRI",
    "Guyana": "GUY", "Suriname": "SUR", "Belize": "BLZ",
}

PLACE_COORDS: dict[str, list[float]] = {
    # Colombia
    "bogotá": [4.71, -74.07], "bogota": [4.71, -74.07], "medellín": [6.25, -75.56],
    "medellin": [6.25, -75.56], "cali": [3.44, -76.52], "cartagena": [10.39, -75.51],
    "barranquilla": [10.97, -74.80], "cúcuta": [7.89, -72.51], "cucuta": [7.89, -72.51],
    "bucaramanga": [7.13, -73.13], "catatumbo": [8.8, -73.0], "urabá": [8.0, -76.5],
    "uraba": [8.0, -76.5], "cauca": [2.7, -76.8], "nariño": [1.28, -77.28],
    "narino": [1.28, -77.28], "putumayo": [0.43, -76.64], "chocó": [5.7, -76.7],
    "choco": [5.7, -76.7], "norte de santander": [7.9, -72.5], "arauca": [7.09, -70.76],
    # Mexico
    "ciudad de méxico": [19.43, -99.13], "ciudad de mexico": [19.43, -99.13],
    "mexico city": [19.43, -99.13], "guadalajara": [20.66, -103.35],
    "monterrey": [25.67, -100.31], "culiacán": [24.80, -107.39],
    "culiacan": [24.80, -107.39], "tijuana": [32.51, -117.03],
    "juárez": [31.74, -106.49], "juarez": [31.74, -106.49],
    "sinaloa": [25.8, -108.4], "jalisco": [20.6, -103.3],
    "michoacán": [19.2, -101.9], "michoacan": [19.2, -101.9],
    "guerrero": [17.4, -99.5], "tamaulipas": [24.3, -98.8],
    "chiapas": [16.8, -92.6], "oaxaca": [17.07, -96.72],
    "veracruz": [19.2, -96.1],
    # Venezuela
    "caracas": [10.48, -66.88], "maracaibo": [10.63, -71.64],
    "valencia": [10.16, -67.99], "barquisimeto": [10.07, -69.32],
    "maracay": [10.25, -67.60], "fort tiuna": [10.47, -66.92],
    "guayana": [8.36, -62.64], "apure": [7.07, -68.54],
    "zulia": [10.6, -71.7], "táchira": [7.9, -72.3], "tachira": [7.9, -72.3],
    # Brazil
    "brasília": [-15.78, -47.93], "brasilia": [-15.78, -47.93],
    "são paulo": [-23.55, -46.63], "sao paulo": [-23.55, -46.63],
    "rio de janeiro": [-22.91, -43.17], "rio": [-22.91, -43.17],
    "manaus": [-3.10, -60.02], "belém": [-1.46, -48.50], "belem": [-1.46, -48.50],
    "salvador": [-12.97, -38.50], "recife": [-8.06, -34.88],
    "fortaleza": [-3.72, -38.54], "porto alegre": [-30.03, -51.23],
    "amazonas": [-3.1, -60.0], "pará": [-3.5, -52.0], "para": [-3.5, -52.0],
    # El Salvador
    "san salvador": [13.69, -89.19], "soyapango": [13.71, -89.15],
    "santa ana": [13.99, -89.56], "san miguel": [13.48, -88.18],
    "CECOT": [13.78, -89.02], "cecot": [13.78, -89.02],
    "chalatenango": [14.04, -88.93], "cabañas": [13.87, -88.75],
    # Argentina
    "buenos aires": [-34.61, -58.38], "córdoba": [-31.42, -64.18],
    "cordoba": [-31.42, -64.18], "rosario": [-32.95, -60.64],
    "mendoza": [-32.89, -68.85], "tucumán": [-26.82, -65.22],
    "tucuman": [-26.82, -65.22],
    # Peru
    "lima": [-12.05, -77.04], "cusco": [-13.53, -71.97],
    "arequipa": [-16.41, -71.54], "trujillo": [-8.11, -79.03],
    "ayacucho": [-13.16, -74.22], "la pampa": [-13.8, -70.5],
    "vraem": [-12.5, -73.8], "apurímac": [-14.0, -73.1], "apurimac": [-14.0, -73.1],
    # Ecuador
    "quito": [-0.22, -78.51], "guayaquil": [-2.19, -79.89],
    "cuenca": [-2.90, -79.00], "esmeraldas": [0.97, -79.65],
    "sucumbíos": [0.09, -76.89], "sucumbios": [0.09, -76.89],
    # Bolivia
    "la paz": [-16.50, -68.15], "cochabamba": [-17.39, -66.16],
    "santa cruz": [-17.79, -63.18], "el alto": [-16.50, -68.19],
    "chapare": [-16.8, -65.7],
    # Honduras
    "tegucigalpa": [14.07, -87.21], "san pedro sula": [15.47, -88.03],
    # Guatemala
    "guatemala city": [14.63, -90.51], "quetzaltenango": [14.84, -91.52],
    # Nicaragua
    "managua": [12.13, -86.31],
    # Haiti
    "port-au-prince": [18.54, -72.34], "port au prince": [18.54, -72.34],
    "cite soleil": [18.57, -72.33],
    # Cuba
    "havana": [23.14, -82.36], "la habana": [23.14, -82.36],
    # Panama
    "panama city": [8.99, -79.52], "colón": [9.36, -79.90], "colon": [9.36, -79.90],
    # Dominican Republic
    "santo domingo": [18.48, -69.96],
    # Paraguay
    "asunción": [-25.29, -57.64], "asuncion": [-25.29, -57.64],
    # Uruguay
    "montevideo": [-34.90, -56.17],
    # Costa Rica
    "san josé": [9.93, -84.08], "san jose": [9.93, -84.08],
    # Chile
    "santiago": [-33.46, -70.65], "valparaíso": [-33.05, -71.62],
    "valparaiso": [-33.05, -71.62], "antofagasta": [-23.65, -70.40],
}


# Places that belong to a specific country — prevents cross-country false matches.
# Key: lowercase place name as it appears in PLACE_COORDS
# Value: the country that place belongs to (must match LATAM_COUNTRIES strings)
PLACE_COUNTRY: dict[str, str] = {
    # "salvador" is a city in Brazil (Bahia), NOT "El Salvador" the country
    "salvador":         "Brazil",
    # Other ambiguous names
    "cartagena":        "Colombia",   # also exists in Spain
    "valencia":         "Venezuela",  # also exists in Spain
    "san jose":         "Costa Rica",
    "san josé":         "Costa Rica",
    "guayana":          "Venezuela",
    "fort tiuna":       "Venezuela",
    "santa ana":        "El Salvador",
    "san miguel":       "El Salvador",
    "cecot":            "El Salvador",
    "trujillo":         "Peru",       # also a city in Venezuela/Honduras
    "santa cruz":       "Bolivia",
    "colón":            "Panama",
    "colon":            "Panama",
}


def geolocate(text: str, country: str) -> list[float]:
    """Try to find specific coords from text, fall back to country centroid.

    Country-aware: if a place name is registered in PLACE_COUNTRY and that
    country does NOT match the event's country, skip it so we don't assign
    e.g. the Brazilian city of Salvador to an El Salvador event.
    """
    text_lower = text.lower()
    # Longest match first to avoid sub-string shadowing (e.g. "lima" in "lima beans")
    for place, coords in sorted(PLACE_COORDS.items(), key=lambda x: -len(x[0])):
        if place.lower() in text_lower:
            place_ctry = PLACE_COUNTRY.get(place.lower())
            # Skip if this place is explicitly assigned to a DIFFERENT country
            if place_ctry is not None and place_ctry != country:
                continue
            return coords
    return COUNTRY_CENTROIDS.get(country, [0.0, 0.0])


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
    # Expanded keywords
    "ceasefire", "peace talks", "negotiations", "disarmament", "reintegration",
    "state of emergency", "martial law", "curfew", "detention", "extradition",
    "trafficking", "smuggling", "seizure", "arrest", "assassination", "kidnapping",
    "hostage", "bombing", "airstrike", "massacre", "displacement", "refugee",
    "sanction", "indictment", "conviction", "corruption", "bribery", "impunity",
    "ELN", "FARC", "Sendero", "Hezbollah", "MS-13", "Mara",
    "maduro", "petro", "bukele", "lula", "milei", "boric",
    "southcom", "USAID", "pentagon", "DEA", "CIA",
    "tren de aragua", "jalisco", "sinaloa", "gulf cartel",
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


def make_sentinel_id(country: str, date: str, internal_id: str) -> str:
    """Human-readable citable ID: ISO3_YYYY_MM_SHA6  (e.g. COL_2026_03_a3f7c9)."""
    iso3 = COUNTRY_ISO3.get(country, "REG")
    year  = date[:4]  if len(date) >= 4  else "0000"
    month = date[5:7] if len(date) >= 7  else "00"
    return f"{iso3}_{year}_{month}_{internal_id[:6]}"


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
            prev_article_ids = prev.get("source_article_ids") or []
            new_article_ids = ev.get("source_article_ids") or []
            existing[eid]["source_article_ids"] = list(dict.fromkeys(
                article_id for article_id in prev_article_ids + new_article_ids if article_id
            ))
            prev_reports = prev.get("linked_reports") or []
            new_reports = ev.get("linked_reports") or []
            report_map: dict[str, dict] = {}
            ordered_keys: list[str] = []
            for report in prev_reports + new_reports:
                key = report.get("article_id") or report.get("url") or report.get("source_name") or str(len(report_map))
                if key not in report_map:
                    ordered_keys.append(key)
                    report_map[key] = report
            existing[eid]["linked_reports"] = [report_map[key] for key in ordered_keys]

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


# ── DSCA ───────────────────────────────────────────────────────────────────────

def fetch_dsca() -> list[dict]:
    """Scrape DSCA Major Arms Sales press releases for LatAm countries."""
    url = "https://www.dsca.mil/press-media/major-arms-sales"
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        items = []
        # DSCA lists articles in .views-row divs or similar
        for link in soup.select("a[href*='/major-arms-sales']"):
            title = link.get_text(strip=True)
            href = link.get("href", "")
            if not title or len(title) < 20:
                continue
            full_url = f"https://www.dsca.mil{href}" if href.startswith("/") else href
            # Check if any LatAm country mentioned
            if any(c.lower() in title.lower() for c in LATAM_COUNTRIES):
                items.append(make_article_record(
                    title=title,
                    description=title,
                    url=full_url,
                    date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    source="DSCA",
                    source_type="official",
                    source_method="scrape",
                    coords=None,
                ))
        log.info(f"DSCA: {len(items)} LatAm arms sale items")
        return items
    except Exception as e:
        log.error(f"DSCA scrape failed: {e}")
        return []


# ── DEA ────────────────────────────────────────────────────────────────────────

def fetch_dea() -> list[dict]:
    """Scrape DEA press releases mentioning LatAm countries."""
    url = "https://www.dea.gov/press-releases"
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        items = []
        for article in soup.select("article, .views-row, .press-release-teaser")[:30]:
            link = article.find("a")
            if not link:
                continue
            title = link.get_text(strip=True)
            href = link.get("href", "")
            if not title or len(title) < 15:
                continue
            full_url = f"https://www.dea.gov{href}" if href.startswith("/") else href
            if any(c.lower() in title.lower() for c in LATAM_COUNTRIES):
                items.append(make_article_record(
                    title=title,
                    description=title,
                    url=full_url,
                    date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    source="DEA",
                    source_type="official",
                    source_method="scrape",
                    coords=None,
                ))
        log.info(f"DEA: {len(items)} LatAm items")
        return items
    except Exception as e:
        log.error(f"DEA scrape failed: {e}")
        return []


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
    iid = stable_id(country, event_type, date)
    return {
        "id":          iid,
        "sentinel_id": make_sentinel_id(country, date, iid),
        "type":        event_type,
        "subtype":     None,
        "deed_type":   None,
        "axis":        None,
        "actor":       "military",
        "target":      None,
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


def _summarize_articles_by_source(articles: list[dict]) -> dict[str, dict]:
    summary: dict[str, dict] = {}
    for article in articles:
        source = article.get("source", "Unknown")
        row = summary.setdefault(source, {
            "source": source,
            "source_type": article.get("source_type"),
            "source_method": article.get("source_method"),
            "count": 0,
            "urls": set(),
        })
        row["count"] += 1
        if article.get("url"):
            row["urls"].add(article["url"])
    for row in summary.values():
        row["unique_urls"] = len(row.pop("urls"))
    return dict(sorted(summary.items(), key=lambda item: (-item[1]["count"], item[0])))


def _summarize_events_by_source(events: list[dict]) -> dict[str, dict]:
    summary: dict[str, dict] = {}
    for event in events:
        sources = event.get("sources") or [event.get("source", "Unknown")]
        for source in sources:
            row = summary.setdefault(source, {
                "source": source,
                "event_count": 0,
                "high_salience": 0,
                "event_types": defaultdict(int),
            })
            row["event_count"] += 1
            if event.get("salience") == "high":
                row["high_salience"] += 1
            row["event_types"][event.get("type", "other")] += 1
    out: dict[str, dict] = {}
    for source, row in summary.items():
        out[source] = {
            "source": source,
            "event_count": row["event_count"],
            "high_salience": row["high_salience"],
            "event_types": dict(sorted(row["event_types"].items())),
        }
    return dict(sorted(out.items(), key=lambda item: (-item[1]["event_count"], item[0])))


def write_source_audit(raw_articles: list[dict], filtered_articles: list[dict], events: list[dict]) -> None:
    raw_summary = _summarize_articles_by_source(raw_articles)
    filtered_summary = _summarize_articles_by_source(filtered_articles)
    event_summary = _summarize_events_by_source(events)

    sources = sorted(set(raw_summary) | set(filtered_summary) | set(event_summary))
    rows = []
    for source in sources:
        raw = raw_summary.get(source, {})
        filtered = filtered_summary.get(source, {})
        ev = event_summary.get(source, {})
        raw_count = raw.get("count", 0)
        filtered_count = filtered.get("count", 0)
        event_count = ev.get("event_count", 0)
        rows.append({
            "source": source,
            "source_type": raw.get("source_type") or filtered.get("source_type"),
            "source_method": raw.get("source_method") or filtered.get("source_method"),
            "raw_articles": raw_count,
            "filtered_articles": filtered_count,
            "filtered_rate": round(filtered_count / raw_count, 3) if raw_count else 0.0,
            "events_generated": event_count,
            "event_yield": round(event_count / filtered_count, 3) if filtered_count else 0.0,
            "high_salience_events": ev.get("high_salience", 0),
            "event_types": ev.get("event_types", {}),
        })

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "raw_article_count": len(raw_articles),
        "filtered_article_count": len(filtered_articles),
        "event_count": len(events),
        "sources": rows,
    }
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REVIEW_DIR / "source_audit.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info(f"Source audit written to {out_path}")


def _staging_payload(label: str, articles: list[dict]) -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stage": label,
        "count": len(articles),
        "articles": articles,
    }


def _event_article_links(events: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for event in events:
        for report in event.get("linked_reports", []):
            rows.append({
                "event_id": event.get("id"),
                "sentinel_id": event.get("sentinel_id"),
                "article_id": report.get("article_id"),
                "article_rank": report.get("article_rank"),
                "report_role": report.get("report_role"),
                "source_name": report.get("source_name"),
                "url": report.get("url"),
                "link_domain": report.get("link_domain"),
                "source_type": report.get("source_type"),
                "source_method": report.get("source_method"),
                "headline": report.get("headline"),
                "linked_at": report.get("linked_at"),
            })
    return rows


def write_staging_articles(raw_articles: list[dict], filtered_articles: list[dict], events: list[dict]) -> None:
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = STAGING_DIR / "raw_articles.json"
    filtered_path = STAGING_DIR / "filtered_articles.json"
    links_path = STAGING_DIR / "event_article_links.json"

    raw_path.write_text(
        json.dumps(_staging_payload("raw_ingestion", raw_articles), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    filtered_path.write_text(
        json.dumps(_staging_payload("keyword_filtered", filtered_articles), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    link_rows = _event_article_links(events)
    links_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "stage": "event_cluster_links",
                "count": len(link_rows),
                "links": link_rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    log.info(f"Staging articles written to {raw_path} and {filtered_path}")
    log.info(f"Staging event/article links written to {links_path}")


# ── Claude classification ──────────────────────────────────────────────────────

CLASSIFY_PROMPT = """\
You are an expert on Latin American civil-military relations. Classify each news item.

For each item [N], respond with ONE JSON line — no preamble, no markdown:
{{"idx":N,"relevant":true/false,"type":"coup|purge|coup_proofing|aid|coop|protest|reform|conflict|exercise|oc|peace|other","subtype":null,"country":"CountryName or null","salience":"high|med|low","conf":"high|med|low","deed_type":"precursor|symptom|resistance|destabilizing|null","axis":"horizontal|vertical|both|null","actor":"executive|military|judiciary|legislature|civil_society|external|oc_group|null","target":"executive|military|judiciary|legislature|civil_society|external|oc_group|population|null","brief":"One sentence summary.","location":"City or region"}}

TYPES:
- coup: coup attempt, military takeover, autogolpe; subtype: attempt|successful|autogolpe|plot
- purge: OFFICER dismissals/forced retirements for political/loyalty reasons (NOT civilian mass detentions)
- coup_proofing: deliberate strategy — parallel forces, political commissars, loyalty promotions as pattern
- aid: US/foreign military assistance, arms sales, IMET, FMF grants
- coop: US military presence, joint ops, FTO/DEA operations, Green Berets, SOUTHCOM activities
- protest: civil-military street tensions, soldier protests, anti-military demonstrations
- reform: SSR, defense reform, institutional change; subtype: SSR|structural|legal|budget
- conflict: armed conflict, guerrilla ops, criminal violence involving security forces
- exercise: joint military exercises, multinational drills, port visits (non-US-led = exercise; US-led = coop)
- oc: organized crime involving or targeting security forces (cartels, gangs, trafficking networks)
- peace: peace talks, ceasefires, DDR, demobilization, negotiated settlements
- other: civil-military relevance, no other type fits

conf: high=verified/multi-source credible outlet, med=single credible source, low=unverified/social media only
salience: high=acute CMR significance OR major political stability impact; med=notable country-level development; low=background/routine
deed_type (DEED democratic erosion framework):
  precursor=warning sign, no institutional change yet; symptom=erosion institutionalized;
  resistance=pushback against military overreach or authoritarianism; destabilizing=threatens regime stability from below; null=not applicable
axis: horizontal=between institutions (executive/military/courts/legislature); vertical=government vs citizens; both; null
actor: who initiated/drove the event; target: who was affected/acted upon
relevant=true ONLY if clear civil-military or defense-institutional relevance for a Latin American country.
country: recognized Latin American country name or null. location: most specific place (city/department/region).
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
        if start == -1:
            raise ValueError("No array in clustering response")
        # Walk brackets to find exact end of the outermost array
        depth, end = 0, start
        for i, ch in enumerate(raw[start:], start):
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        clusters = json.loads(raw[start:end])
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
        ev.setdefault("source_article_ids", [r.get("article_id") for r in ev.get("linked_reports", []) if r.get("article_id")])
        ev.setdefault("linked_reports", [])
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
    seen_article_ids: set[str] = set()
    linked_reports: list[dict] = []
    for ev in events:
        for report in ev.get("linked_reports", []):
            article_id = report.get("article_id")
            if article_id and article_id in seen_article_ids:
                continue
            if article_id:
                seen_article_ids.add(article_id)
            linked_reports.append(report)
    merged["linked_reports"] = linked_reports
    merged["source_article_ids"] = [report.get("article_id") for report in linked_reports if report.get("article_id")]
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
            location = r.get("location", "")
            date     = article["date"]
            ev_type  = r.get("type", "other")
            link     = article.get("url", "")
            # Use article coords if already geolocated (e.g. GDELT), otherwise
            # attempt city/region lookup from Claude's location field + title + snippet
            if article.get("coords"):
                coords = article["coords"]
            else:
                location_text = f"{location} {article['title']} {article.get('description', '')}".strip()
                coords = geolocate(location_text, country)
            _conf_map = {"high": "green", "med": "yellow", "low": "red"}
            _sal_map  = {"high": "high", "med": "medium", "low": "low"}
            iid = stable_id(country, ev_type, date)
            candidates.append({
                "id":          iid,
                "sentinel_id": make_sentinel_id(country, date, iid),
                "type":        ev_type,
                "subtype":     r.get("subtype") or None,
                "deed_type":   r.get("deed_type") or None,
                "axis":        r.get("axis") or None,
                "actor":       r.get("actor") or None,
                "target":      r.get("target") or None,
                "title":       article["title"],
                "summary":     r.get("brief", "") or article.get("description", ""),
                "country":     country,
                "location":    location,
                "date":        date,
                "source":      article["source"],
                "sources":     [article["source"]],
                "conf":        _conf_map.get(r.get("conf", "med"), "yellow"),
                "salience":    _sal_map.get(r.get("salience", "med"), "medium"),
                "coords":      coords,
                "url":         link,
                "links":       [link] if link and link != "#" else [],
                "source_article_ids": [article.get("article_id")] if article.get("article_id") else [],
                "linked_reports": [
                    {
                        "article_id": article.get("article_id"),
                        "article_rank": 1,
                        "report_role": "primary",
                        "source_name": article.get("source"),
                        "url": link,
                        "link_domain": article.get("source_domain"),
                        "headline": article.get("title"),
                        "source_type": article.get("source_type"),
                        "source_method": article.get("source_method"),
                        "linked_at": article.get("normalized_at") or now,
                    }
                ],
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
Write 2-3 sentences on why this event matters for political risk and security politics in {country}.
Be specific, concrete, and country-focused. Avoid jargon and generic theory language.
Explain the mechanism: what happened, why it matters, and what it could change next.

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
    import argparse
    parser = argparse.ArgumentParser(description="SENTINEL event pipeline")
    parser.add_argument("--backfill",    action="store_true",
                        help="Historical mode — fetch all sources back to --since date")
    parser.add_argument("--since",       type=str, default=None,
                        help="Start date for historical fetch (YYYY-MM-DD). Implies --backfill.")
    parser.add_argument("--years",       type=int, default=5,
                        help="Years back when using --backfill without --since (default: 5)")
    parser.add_argument("--gdelt",       action="store_true",
                        help="Opt in to GDELT. Disabled by default for both normal and historical runs.")
    parser.add_argument("--from-staging", type=str, default=None, metavar="DIR",
                        help="Load pre-fetched article records from JSONL files in DIR "
                             "(e.g. data/staging/gdelt_events/) and classify them. "
                             "Skips all live fetching when specified.")
    args = parser.parse_args()

    backfill = args.backfill or (args.since is not None)

    if args.since:
        try:
            cutoff = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise ValueError(f"--since must be YYYY-MM-DD, got: {args.since!r}")
    elif backfill:
        cutoff = datetime.now(timezone.utc) - timedelta(days=365 * args.years)
    else:
        cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)

    log.info("=== SENTINEL pipeline starting ===")
    if backfill:
        log.info(f"Historical mode: fetching from {cutoff.date()} ({args.years}-year window)")

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set.")

    client   = anthropic.Anthropic(api_key=anthropic_key)
    existing = load_existing()
    existing_ids = set(existing.keys())
    log.info(f"Existing events in store: {len(existing)}")

    # ── 1. Fetch all sources ───────────────────────────────────────────────────
    all_articles: list[dict] = []

    if args.from_staging:
        # Staging mode: read pre-fetched JSONL files; skip all live fetching.
        staging_dir = Path(args.from_staging)
        if not staging_dir.is_dir():
            raise ValueError(f"--from-staging path does not exist or is not a directory: {staging_dir}")
        jsonl_files = sorted(staging_dir.glob("*.jsonl"))
        log.info(f"Loading staging articles from {len(jsonl_files)} JSONL file(s) in {staging_dir}")
        for jf in jsonl_files:
            loaded = 0
            for line in jf.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    all_articles.append(json.loads(line))
                    loaded += 1
                except json.JSONDecodeError as e:
                    log.warning(f"Bad JSON line in {jf.name}: {e}")
            log.info(f"  {jf.name}: {loaded} records")
        log.info(f"Total staging articles loaded: {len(all_articles)}")
    elif backfill:
        # Historical mode: archive scrapers, with optional GDELT.
        if args.gdelt:
            log.info("Fetching GDELT in monthly batches...")
            all_articles.extend(fetch_gdelt_historical(cutoff))

        log.info("Fetching WordPress archive sources...")
        all_articles.extend(fetch_all_archives(cutoff))

        # RSS still useful for article text/URLs (recent portion)
        for feed in RSS_FEEDS:
            all_articles.extend(fetch_rss(feed, cutoff))
            time.sleep(0.3)
    else:
        # Normal nightly mode: RSS, with optional current GDELT window
        for feed in RSS_FEEDS:
            all_articles.extend(fetch_rss(feed, cutoff))
            time.sleep(0.3)
        if args.gdelt:
            all_articles.extend(normalize_gdelt(fetch_gdelt()))

    # NewsAPI (works in normal/backfill modes; skip in --from-staging mode)
    if not args.from_staging:
        newsapi_key = os.environ.get("NEWSAPI_KEY", "")
        if newsapi_key:
            newsapi_since = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ") if backfill else None
            all_articles.extend(normalize_newsapi(fetch_newsapi(newsapi_key, since=newsapi_since)))
        else:
            log.info("No NEWSAPI_KEY — skipping NewsAPI")

    if not args.from_staging:
        # DSCA arms sales
        all_articles.extend(fetch_dsca())
        # DEA press releases
        all_articles.extend(fetch_dea())

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

    # ── 6. Source audit ──────────────────────────────────────────────────────
    write_source_audit(all_articles, relevant, new_events)
    write_staging_articles(all_articles, relevant, new_events)

    # ── 7. Save ───────────────────────────────────────────────────────────────
    added = save_events(existing, new_events)
    current_total = len(json.loads(DATA_FILE.read_text(encoding="utf-8")).get("events", []))
    log.info(f"Done. {added} new events added. Total stored: {current_total}")

    # ── 8. Weekly digest ──────────────────────────────────────────────────────
    all_saved = list(existing.values())
    send_digest(all_saved)

    log.info("=== SENTINEL pipeline complete ===")


if __name__ == "__main__":
    main()
