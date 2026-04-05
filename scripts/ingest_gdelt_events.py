#!/usr/bin/env python3
"""
GDELT Events Database bulk-CSV connector for SENTINEL.

Downloads GDELT 1.0 annual/daily event files, filters for Latin America
civil-military relevant events, and writes normalized article records to
data/staging/gdelt_events/ as JSONL files for later classification.

Coverage:
  2000-01-01 → 2015-02-18   (GDELT Full-Text Doc API starts 2015-02-19;
                              use ingest_gdelt.py for 2015 onwards)

Data product:
  GDELT Events Database — structured CAMEO-coded events with lat/lon,
  actor names, country codes, and (from 2013+) source URLs.
  No API key required. Direct HTTP file downloads; no rate limits.

URLs:
  Annual (2000–2012):  http://data.gdeltproject.org/events/{YYYY}.zip
  Daily  (2013+):      http://data.gdeltproject.org/events/{YYYYMMDD}.export.CSV.zip

Usage:
    # Full 2000–2015 backfill (runs step 1 of 2)
    python3 scripts/ingest_gdelt_events.py --since 2000-01-01 --until 2015-02-18

    # Resume an interrupted run
    python3 scripts/ingest_gdelt_events.py --since 2000-01-01 --until 2015-02-18 --resume

    # Dry-run — print plan without downloading
    python3 scripts/ingest_gdelt_events.py --since 2000-01-01 --dry-run

    # Step 2: classify staged records (run afterwards)
    python3 scripts/run_pipeline.py --from-staging data/staging/gdelt_events/
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import time
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

import requests

from normalize_articles import make_article_record

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sentinel.gdelt_events")

ROOT = Path(__file__).resolve().parent.parent
STAGING_DIR = ROOT / "data" / "staging" / "gdelt_events"
CHECKPOINT_PATH = ROOT / "data" / "staging" / "gdelt_events_checkpoint.json"

GDELT_ANNUAL_URL = "http://data.gdeltproject.org/events/{year}.zip"
GDELT_DAILY_URL  = "http://data.gdeltproject.org/events/{ymd}.export.CSV.zip"

# Last date covered by GDELT Doc API (use ingest_gdelt.py after this)
GDELT_DOC_API_START = date(2015, 2, 19)

# ── Column indices for GDELT 1.0 TSV (no header row) ──────────────────────────
C_DAY          = 1   # YYYYMMDD
C_ACTOR1_NAME  = 6
C_ACTOR1_CC    = 7   # FIPS country code
C_ACTOR1_TYPE1 = 12
C_ACTOR2_NAME  = 16
C_ACTOR2_CC    = 17
C_ACTOR2_TYPE1 = 22
C_EVENT_CODE   = 26
C_EVENT_ROOT   = 28
C_AVG_TONE     = 34
C_GEO_FULLNAME = 50
C_GEO_CC       = 51  # ActionGeo country code (FIPS)
C_GEO_LAT      = 53
C_GEO_LON      = 54
C_SOURCE_URL   = 57  # only present in later files

# ── FIPS → ISO-2 mapping for GDELT country codes ──────────────────────────────
FIPS_TO_ISO: dict[str, str] = {
    "AR": "AR",  # Argentina
    "BH": "BZ",  # Belize
    "BL": "BO",  # Bolivia
    "BR": "BR",  # Brazil
    "CI": "CL",  # Chile
    "CO": "CO",  # Colombia
    "CS": "CR",  # Costa Rica
    "CU": "CU",  # Cuba
    "DR": "DO",  # Dominican Republic
    "EC": "EC",  # Ecuador
    "ES": "SV",  # El Salvador
    "GT": "GT",  # Guatemala
    "GY": "GY",  # Guyana
    "HA": "HT",  # Haiti
    "HO": "HN",  # Honduras
    "JM": "JM",  # Jamaica
    "MX": "MX",  # Mexico
    "NS": "SR",  # Suriname
    "NU": "NI",  # Nicaragua
    "PA": "PY",  # Paraguay  (FIPS PA = Paraguay, not Panama!)
    "PE": "PE",  # Peru
    "PM": "PA",  # Panama    (FIPS PM = Panama)
    "TD": "TT",  # Trinidad and Tobago
    "UY": "UY",  # Uruguay
    "VE": "VE",  # Venezuela
}

ISO_TO_COUNTRY: dict[str, str] = {
    "AR": "Argentina",        "BZ": "Belize",            "BO": "Bolivia",
    "BR": "Brazil",           "CL": "Chile",             "CO": "Colombia",
    "CR": "Costa Rica",       "CU": "Cuba",              "DO": "Dominican Republic",
    "EC": "Ecuador",          "SV": "El Salvador",       "GT": "Guatemala",
    "GY": "Guyana",           "HT": "Haiti",             "HN": "Honduras",
    "JM": "Jamaica",          "MX": "Mexico",            "NI": "Nicaragua",
    "PA": "Panama",           "PY": "Paraguay",          "PE": "Peru",
    "SR": "Suriname",         "TT": "Trinidad and Tobago", "UY": "Uruguay",
    "VE": "Venezuela",
}

LAC_FIPS: frozenset[str] = frozenset(FIPS_TO_ISO)

# ── CMR relevance filters ──────────────────────────────────────────────────────
# Actor type codes that signal a CMR-relevant actor
CMR_ACTOR_TYPES: frozenset[str] = frozenset({"MIL", "REB", "SPY", "GOV"})

# CAMEO root codes that are always relevant regardless of actor
CMR_ROOT_CODES: frozenset[str] = frozenset({
    "14",  # PROTEST
    "15",  # EXHIBIT FORCE POSTURE / exercises
    "17",  # COERCE
    "18",  # ASSAULT
    "19",  # FIGHT
    "20",  # USE UNCONVENTIONAL MASS VIOLENCE
})

# ── CAMEO root → human-readable verb ──────────────────────────────────────────
CAMEO_DESC: dict[str, str] = {
    "01": "made statement",
    "02": "appealed for action",
    "03": "expressed intent to cooperate",
    "04": "consulted",
    "05": "engaged in diplomatic cooperation",
    "06": "provided material cooperation",
    "07": "provided aid",
    "08": "yielded position",
    "09": "investigated",
    "10": "demanded action",
    "11": "criticized",
    "12": "rejected",
    "13": "threatened",
    "14": "protested",
    "15": "exhibited military force",
    "16": "reduced relations",
    "17": "coerced",
    "18": "assaulted",
    "19": "engaged in armed conflict",
    "20": "used mass violence",
}


# ── Streaming download helpers ─────────────────────────────────────────────────

def _stream_zip_tsv(url: str, timeout: int = 120) -> Iterator[list[str]]:
    """Download a zip file and yield parsed TSV rows from the first CSV inside."""
    log.info(f"Downloading {url}")
    try:
        resp = requests.get(url, stream=True, timeout=timeout)
        resp.raise_for_status()
    except requests.HTTPError as e:
        log.error(f"HTTP error downloading {url}: {e}")
        return
    except requests.RequestException as e:
        log.error(f"Request failed for {url}: {e}")
        return

    buf = io.BytesIO(resp.content)
    try:
        zf = zipfile.ZipFile(buf)
    except zipfile.BadZipFile as e:
        log.error(f"Bad zip from {url}: {e}")
        return

    for name in zf.namelist():
        if name.endswith(".CSV") or name.endswith(".csv"):
            with zf.open(name) as f:
                text = io.TextIOWrapper(f, encoding="utf-8", errors="replace")
                reader = csv.reader(text, delimiter="\t")
                for row in reader:
                    yield row
            return


def _safe(cols: list[str], idx: int, default: str = "") -> str:
    try:
        return cols[idx].strip()
    except IndexError:
        return default


# ── Row filtering and conversion ───────────────────────────────────────────────

def _lac_fips(cols: list[str]) -> str | None:
    """Return the FIPS code if any country field is in the LAC set."""
    for idx in (C_GEO_CC, C_ACTOR1_CC, C_ACTOR2_CC):
        cc = _safe(cols, idx)
        if cc in LAC_FIPS:
            return cc
    return None


def _is_cmr_relevant(cols: list[str]) -> bool:
    root = _safe(cols, C_EVENT_ROOT)
    if root in CMR_ROOT_CODES:
        return True
    for idx in (C_ACTOR1_TYPE1, C_ACTOR2_TYPE1):
        if _safe(cols, idx) in CMR_ACTOR_TYPES:
            return True
    return False


def _row_to_record(cols: list[str]) -> dict | None:
    fips = _lac_fips(cols)
    if not fips:
        return None
    if not _is_cmr_relevant(cols):
        return None

    iso = FIPS_TO_ISO[fips]
    country = ISO_TO_COUNTRY.get(iso, "")
    if not country:
        return None

    # Date
    raw_day = _safe(cols, C_DAY)
    try:
        dt = datetime.strptime(raw_day, "%Y%m%d")
        event_date = dt.strftime("%Y-%m-%d")
    except ValueError:
        return None

    # Title
    actor1 = _safe(cols, C_ACTOR1_NAME) or "Actor"
    actor2 = _safe(cols, C_ACTOR2_NAME) or "party"
    root   = _safe(cols, C_EVENT_ROOT)
    verb   = CAMEO_DESC.get(root, "interacted with")
    location = _safe(cols, C_GEO_FULLNAME) or country
    title = f"{actor1} {verb} {actor2} in {location}"

    # Coordinates
    coords: list[float] | None = None
    lat_s = _safe(cols, C_GEO_LAT)
    lon_s = _safe(cols, C_GEO_LON)
    try:
        lat, lon = float(lat_s), float(lon_s)
        if lat != 0.0 or lon != 0.0:
            coords = [lat, lon]
    except (ValueError, TypeError):
        pass

    url = _safe(cols, C_SOURCE_URL) if len(cols) > C_SOURCE_URL else ""

    # Description carries extra metadata for the classifier prompt
    tone = _safe(cols, C_AVG_TONE)
    event_code = _safe(cols, C_EVENT_CODE)
    description = (
        f"GDELT event: {verb} | country={country} | "
        f"actor1_type={_safe(cols, C_ACTOR1_TYPE1)} | "
        f"actor2_type={_safe(cols, C_ACTOR2_TYPE1)} | "
        f"cameo={event_code} | tone={tone}"
    )

    return make_article_record(
        title=title,
        description=description,
        url=url,
        date=event_date,
        source="GDELT Events",
        source_type="gdelt_events_db",
        source_method="gdelt_bulk_csv",
        coords=coords,
    )


# ── Annual file fetching ───────────────────────────────────────────────────────

def process_annual_year(year: int, since: date, until: date) -> list[dict]:
    url = GDELT_ANNUAL_URL.format(year=year)
    records: list[dict] = []
    seen: set[str] = set()
    for cols in _stream_zip_tsv(url):
        raw_day = _safe(cols, C_DAY)
        try:
            row_date = datetime.strptime(raw_day, "%Y%m%d").date()
        except ValueError:
            continue
        if row_date < since or row_date > until:
            continue
        rec = _row_to_record(cols)
        if rec and rec["article_id"] not in seen:
            seen.add(rec["article_id"])
            records.append(rec)
    log.info(f"Year {year}: {len(records)} LAC/CMR records extracted")
    return records


def process_daily_file(file_date: date) -> list[dict]:
    ymd = file_date.strftime("%Y%m%d")
    url = GDELT_DAILY_URL.format(ymd=ymd)
    records: list[dict] = []
    seen: set[str] = set()
    for cols in _stream_zip_tsv(url):
        rec = _row_to_record(cols)
        if rec and rec["article_id"] not in seen:
            seen.add(rec["article_id"])
            records.append(rec)
    return records


# ── Checkpoint helpers ─────────────────────────────────────────────────────────

def load_checkpoint() -> dict | None:
    if not CHECKPOINT_PATH.exists():
        return None
    try:
        return json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_checkpoint(payload: dict) -> None:
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def clear_checkpoint() -> None:
    if CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()


# ── Staging output ─────────────────────────────────────────────────────────────

def write_staging(records: list[dict], label: str) -> Path:
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    out_path = STAGING_DIR / f"gdelt_events_{label}.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    log.info(f"Wrote {len(records)} records → {out_path}")
    return out_path


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download and filter GDELT Events Database bulk CSVs for SENTINEL"
    )
    parser.add_argument("--since", required=True,
                        help="Start date YYYY-MM-DD (earliest useful: 2000-01-01)")
    parser.add_argument("--until", default=GDELT_DOC_API_START.strftime("%Y-%m-%d"),
                        help=f"End date YYYY-MM-DD (default: {GDELT_DOC_API_START}, day before Doc API)")
    parser.add_argument("--resume", action="store_true",
                        help="Resume a previous run from checkpoint")
    parser.add_argument("--clear-checkpoint", action="store_true",
                        help="Delete checkpoint and exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the download plan without actually downloading")
    parser.add_argument("--pause", type=float, default=2.0,
                        help="Seconds to pause between annual files (default: 2)")
    args = parser.parse_args()

    if args.clear_checkpoint:
        clear_checkpoint()
        log.info("Checkpoint cleared.")
        return

    since = datetime.strptime(args.since, "%Y-%m-%d").date()
    until = datetime.strptime(args.until, "%Y-%m-%d").date()

    if until >= GDELT_DOC_API_START:
        log.warning(
            f"--until {until} overlaps with GDELT Full-Text Doc API coverage "
            f"(starts {GDELT_DOC_API_START}). Consider setting --until 2015-02-18."
        )

    # ── Determine work units ───────────────────────────────────────────────────
    # Annual mode: 2000–2012; daily mode: 2013+
    ANNUAL_CUTOVER = date(2013, 1, 1)
    annual_years = [y for y in range(since.year, min(until.year, 2012) + 1)
                    if since.year <= y <= 2012]
    daily_start  = max(since, ANNUAL_CUTOVER)
    daily_end    = min(until, GDELT_DOC_API_START - timedelta(days=1))
    daily_dates  = []
    if daily_start <= daily_end:
        cur = daily_start
        while cur <= daily_end:
            daily_dates.append(cur)
            cur += timedelta(days=1)

    log.info(f"Plan: {len(annual_years)} annual files ({annual_years[0] if annual_years else '—'}–"
             f"{annual_years[-1] if annual_years else '—'}) + {len(daily_dates)} daily files")

    if args.dry_run:
        for y in annual_years:
            print(f"  [annual] {GDELT_ANNUAL_URL.format(year=y)}")
        for d in daily_dates[:5]:
            print(f"  [daily]  {GDELT_DAILY_URL.format(ymd=d.strftime('%Y%m%d'))}")
        if len(daily_dates) > 5:
            print(f"  ... and {len(daily_dates) - 5} more daily files")
        return

    # ── Resume logic ──────────────────────────────────────────────────────────
    completed_years: set[int] = set()
    completed_days: set[str] = set()
    if args.resume:
        cp = load_checkpoint()
        if cp:
            completed_years = set(cp.get("completed_years", []))
            completed_days  = set(cp.get("completed_days", []))
            log.info(f"Resuming: {len(completed_years)} annual years and "
                     f"{len(completed_days)} daily files already done")

    # ── Annual files ──────────────────────────────────────────────────────────
    for year in annual_years:
        if year in completed_years:
            log.info(f"Skipping year {year} (already completed)")
            continue
        year_since = max(since, date(year, 1, 1))
        year_until = min(until, date(year, 12, 31))
        records = process_annual_year(year, year_since, year_until)
        write_staging(records, str(year))
        completed_years.add(year)
        write_checkpoint({
            "since": args.since,
            "until": args.until,
            "completed_years": sorted(completed_years),
            "completed_days": sorted(completed_days),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        time.sleep(args.pause)

    # ── Daily files (2013–2015-02-18) — grouped and written monthly ──────────
    month_records: dict[str, list[dict]] = {}
    for d in daily_dates:
        label = d.strftime("%Y%m")
        ymd   = d.strftime("%Y%m%d")
        if ymd in completed_days:
            continue
        recs = process_daily_file(d)
        month_records.setdefault(label, []).extend(recs)
        completed_days.add(ymd)

        # Flush a month's worth when we roll over
        next_d = d + timedelta(days=1)
        if not daily_dates or next_d > daily_dates[-1] or next_d.month != d.month:
            if month_records.get(label):
                write_staging(month_records.pop(label, []), label)
                write_checkpoint({
                    "since": args.since,
                    "until": args.until,
                    "completed_years": sorted(completed_years),
                    "completed_days": sorted(completed_days),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
        time.sleep(0.5)

    # Flush any remaining month buffer
    for label, recs in month_records.items():
        if recs:
            write_staging(recs, label)

    clear_checkpoint()
    total_files = len(list(STAGING_DIR.glob("*.jsonl")))
    log.info(f"Done. {total_files} staging JSONL files in {STAGING_DIR}")
    log.info("Next step: python3 scripts/run_pipeline.py --from-staging data/staging/gdelt_events/")


if __name__ == "__main__":
    main()
