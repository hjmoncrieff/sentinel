#!/usr/bin/env python3
"""
GDELT ingestion utilities for SENTINEL.

This module is intentionally separate from the main `fetch_events.py` pipeline so
GDELT can be run as an explicit, slower enrichment path rather than part of the
default fast pipeline.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone

import requests

from normalize_articles import make_article_record

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_TIMESPAN = "4H"
GDELT_BATCH_PAUSE = 2.0

log = logging.getLogger("sentinel.gdelt")

_GDELT_CMR_QUERY = (
    '(military OR army OR coup OR "armed forces" OR purge OR "security forces" '
    'OR narco OR cartel OR guerrilla OR ejército OR "fuerzas armadas" OR naval '
    'OR protest OR "state of exception" OR "estado de excepción" OR ceasefire '
    'OR "peace process" OR "security reform" OR paramilitary OR FARC OR ELN) '
    "sourcecountry:(BR OR CO OR MX OR VE OR AR OR PE OR CL OR EC OR BO OR HN "
    "OR NI OR GT OR SV OR PY OR UY OR CU OR HT OR DO OR PA OR CR OR JM OR TT)"
)


def fetch_gdelt() -> list[dict]:
    country_codes = "BR OR CO OR MX OR VE OR AR OR PE OR CL OR EC OR BO OR HN OR NI OR GT OR SV OR PY OR UY OR CU OR HT OR DO OR PA OR CR"
    params = {
        "query": (
            "(military OR army OR coup OR protest OR guerrilla OR narco OR naval "
            'OR "armed forces" OR ejército OR fuerzas OR policía OR "security forces") '
            f"sourcecountry:({country_codes})"
        ),
        "mode": "artlist",
        "maxrecords": "100",
        "timespan": GDELT_TIMESPAN,
        "format": "json",
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
    for article in articles:
        title = (article.get("title") or "").strip()
        if not title:
            continue
        raw_date = (article.get("seendate") or "")[:8]
        try:
            date = datetime.strptime(raw_date, "%Y%m%d").strftime("%Y-%m-%d")
        except Exception:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        lat, lon = article.get("latitude"), article.get("longitude")
        coords = [float(lat), float(lon)] if lat and lon else None
        domain = (article.get("domain") or "GDELT").split(".")[0].title()
        out.append(make_article_record(
            title=title,
            description=title,
            url=article.get("url", ""),
            date=date,
            source=domain,
            source_type="gdelt",
            source_method="gdelt_api",
            coords=coords,
        ))
    return out


def fetch_gdelt_range(start_dt: datetime, end_dt: datetime) -> list[dict]:
    """Query GDELT Full-Text API for a specific date range."""
    params = {
        "query": _GDELT_CMR_QUERY,
        "mode": "artlist",
        "maxrecords": "250",
        "startdatetime": start_dt.strftime("%Y%m%d%H%M%S"),
        "enddatetime": end_dt.strftime("%Y%m%d%H%M%S"),
        "format": "json",
    }
    try:
        resp = requests.get(GDELT_URL, params=params, timeout=40)
        resp.raise_for_status()
        articles = resp.json().get("articles") or []
        log.info(f"GDELT [{start_dt.date()}→{end_dt.date()}]: {len(articles)} articles")
        return articles
    except Exception as e:
        log.error(f"GDELT range fetch failed [{start_dt.date()}→{end_dt.date()}]: {e}")
        return []


def fetch_gdelt_historical(since_dt: datetime, until_dt: datetime | None = None) -> list[dict]:
    """Fetch GDELT in monthly batches from since_dt to until_dt."""
    if until_dt is None:
        until_dt = datetime.now(timezone.utc)
    all_articles: list[dict] = []
    cursor = since_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    while cursor < until_dt:
        if cursor.month == 12:
            batch_end = cursor.replace(year=cursor.year + 1, month=1)
        else:
            batch_end = cursor.replace(month=cursor.month + 1)
        batch_end = min(batch_end, until_dt)
        articles = fetch_gdelt_range(cursor, batch_end)
        all_articles.extend(normalize_gdelt(articles))
        cursor = batch_end
        time.sleep(GDELT_BATCH_PAUSE)
    log.info(f"GDELT historical total: {len(all_articles)} articles across all batches")
    return all_articles


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Fetch GDELT articles for SENTINEL")
    parser.add_argument("--historical", action="store_true", help="Fetch monthly historical batches")
    parser.add_argument("--since", type=str, default=None, help="Start date YYYY-MM-DD for historical mode")
    args = parser.parse_args()

    if args.historical:
        if not args.since:
            raise ValueError("--historical requires --since YYYY-MM-DD")
        since_dt = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        rows = fetch_gdelt_historical(since_dt)
    else:
        rows = normalize_gdelt(fetch_gdelt())

    print(json.dumps({"count": len(rows), "articles": rows}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
