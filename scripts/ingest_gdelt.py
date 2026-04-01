#!/usr/bin/env python3
"""
GDELT ingestion utilities for SENTINEL.

This module is intentionally separate from the main fast monitoring pipeline so
GDELT can be run as an explicit, slower enrichment path rather than part of the
default fast pipeline.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from normalize_articles import make_article_record

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_TIMESPAN = "4H"
GDELT_BATCH_PAUSE = 4.0
GDELT_TIMEOUT = 40
GDELT_MAX_RETRIES = 5
GDELT_BACKOFF_BASE = 8.0
GDELT_HISTORICAL_MAXRECORDS = 100
GDELT_LIVE_MAXRECORDS = 75
GDELT_CONSERVATIVE_BATCH_PAUSE = 10.0
GDELT_CONSERVATIVE_HISTORICAL_MAXRECORDS = 50
GDELT_CONSERVATIVE_LIVE_MAXRECORDS = 25
GDELT_CONSERVATIVE_TIMESPAN = "1H"
GDELT_MAX_BACKOFF_SECONDS = 90.0
GDELT_OFF_HOURS_START = 0
GDELT_OFF_HOURS_END = 6
ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT_PATH = ROOT / "data" / "staging" / "gdelt_checkpoint.json"

log = logging.getLogger("sentinel.gdelt")

_GDELT_CMR_QUERY = (
    '(military OR army OR coup OR "armed forces" OR purge OR "security forces" '
    'OR narco OR cartel OR guerrilla OR ejército OR "fuerzas armadas" OR naval '
    'OR protest OR "state of exception" OR "estado de excepción" OR ceasefire '
    'OR "peace process" OR "security reform" OR paramilitary OR FARC OR ELN) '
    "sourcecountry:(BR OR CO OR MX OR VE OR AR OR PE OR CL OR EC OR BO OR HN "
    "OR NI OR GT OR SV OR PY OR UY OR CU OR HT OR DO OR PA OR CR OR JM OR TT)"
)

_GDELT_CONSERVATIVE_QUERY = (
    '(military OR coup OR cartel OR guerrilla OR protest OR "armed forces" '
    'OR ELN OR FARC OR "security forces") '
    "sourcecountry:(BR OR CO OR MX OR VE OR AR OR PE OR CL OR EC OR BO OR HN "
    "OR NI OR GT OR SV OR PY OR UY OR CU OR HT OR DO OR PA OR CR)"
)


def _sleep_for_rate_limit(
    attempt: int,
    response: requests.Response | None = None,
    max_backoff_seconds: float = GDELT_MAX_BACKOFF_SECONDS,
) -> bool:
    retry_after = None
    if response is not None:
        retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            wait_seconds = max(float(retry_after), GDELT_BACKOFF_BASE)
        except ValueError:
            wait_seconds = GDELT_BACKOFF_BASE * (2 ** attempt)
    else:
        wait_seconds = GDELT_BACKOFF_BASE * (2 ** attempt)
    if wait_seconds > max_backoff_seconds:
        log.error(
            "GDELT rate-limit wait %.1fs exceeded configured cutoff of %.1fs; stopping request",
            wait_seconds,
            max_backoff_seconds,
        )
        return False
    log.warning(f"GDELT rate-limited; backing off for {wait_seconds:.1f}s before retry")
    time.sleep(wait_seconds)
    return True


def _gdelt_request(
    params: dict,
    timeout: int = GDELT_TIMEOUT,
    max_backoff_seconds: float = GDELT_MAX_BACKOFF_SECONDS,
) -> list[dict]:
    for attempt in range(GDELT_MAX_RETRIES):
        try:
            resp = requests.get(GDELT_URL, params=params, timeout=timeout)
            if resp.status_code == 429:
                if attempt == GDELT_MAX_RETRIES - 1:
                    log.error("GDELT request exhausted retries after repeated 429 responses")
                    return []
                if not _sleep_for_rate_limit(
                    attempt,
                    resp,
                    max_backoff_seconds=max_backoff_seconds,
                ):
                    return []
                continue
            resp.raise_for_status()
            return resp.json().get("articles") or []
        except requests.HTTPError as e:
            log.error(f"GDELT HTTP error: {e}")
            return []
        except requests.RequestException as e:
            if attempt == GDELT_MAX_RETRIES - 1:
                log.error(f"GDELT request failed after {GDELT_MAX_RETRIES} attempts: {e}")
                return []
            wait_seconds = min(30.0, 3.0 * (attempt + 1))
            log.warning(f"GDELT request error: {e}; retrying in {wait_seconds:.1f}s")
            time.sleep(wait_seconds)
    return []


def _build_live_query(conservative: bool = False) -> str:
    if conservative:
        return _GDELT_CONSERVATIVE_QUERY
    country_codes = "BR OR CO OR MX OR VE OR AR OR PE OR CL OR EC OR BO OR HN OR NI OR GT OR SV OR PY OR UY OR CU OR HT OR DO OR PA OR CR"
    return (
        "(military OR army OR coup OR protest OR guerrilla OR narco OR naval "
        'OR "armed forces" OR ejército OR fuerzas OR policía OR "security forces") '
        f"sourcecountry:({country_codes})"
    )


def fetch_gdelt(
    conservative: bool = False,
    max_backoff_seconds: float = GDELT_MAX_BACKOFF_SECONDS,
) -> list[dict]:
    params = {
        "query": _build_live_query(conservative=conservative),
        "mode": "artlist",
        "maxrecords": str(GDELT_CONSERVATIVE_LIVE_MAXRECORDS if conservative else GDELT_LIVE_MAXRECORDS),
        "timespan": GDELT_CONSERVATIVE_TIMESPAN if conservative else GDELT_TIMESPAN,
        "format": "json",
    }
    try:
        articles = _gdelt_request(
            params,
            timeout=GDELT_TIMEOUT,
            max_backoff_seconds=max_backoff_seconds,
        )
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


def fetch_gdelt_range(
    start_dt: datetime,
    end_dt: datetime,
    conservative: bool = False,
    max_backoff_seconds: float = GDELT_MAX_BACKOFF_SECONDS,
) -> list[dict]:
    """Query GDELT Full-Text API for a specific date range."""
    params = {
        "query": _GDELT_CONSERVATIVE_QUERY if conservative else _GDELT_CMR_QUERY,
        "mode": "artlist",
        "maxrecords": str(GDELT_CONSERVATIVE_HISTORICAL_MAXRECORDS if conservative else GDELT_HISTORICAL_MAXRECORDS),
        "startdatetime": start_dt.strftime("%Y%m%d%H%M%S"),
        "enddatetime": end_dt.strftime("%Y%m%d%H%M%S"),
        "format": "json",
    }
    try:
        articles = _gdelt_request(
            params,
            timeout=GDELT_TIMEOUT,
            max_backoff_seconds=max_backoff_seconds,
        )
        log.info(f"GDELT [{start_dt.date()}→{end_dt.date()}]: {len(articles)} articles")
        return articles
    except Exception as e:
        log.error(f"GDELT range fetch failed [{start_dt.date()}→{end_dt.date()}]: {e}")
        return []


def load_checkpoint() -> dict | None:
    if not CHECKPOINT_PATH.exists():
        return None
    try:
        return json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning(f"Could not read GDELT checkpoint: {e}")
        return None


def write_checkpoint(payload: dict) -> None:
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_checkpoint() -> None:
    if CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()


def _sleep_until_off_hours(window_start: int, window_end: int) -> None:
    now = datetime.now().astimezone()
    hour = now.hour
    if window_start < window_end:
        in_window = window_start <= hour < window_end
    else:
        in_window = hour >= window_start or hour < window_end
    if in_window:
        return

    next_start = now.replace(hour=window_start, minute=0, second=0, microsecond=0)
    if hour >= window_start:
        next_start = next_start + timedelta(days=1)
    wait_seconds = max((next_start - now).total_seconds(), 0)
    log.info(
        "Off-hours mode active; waiting %.2f hours until local window %02d:00-%02d:00",
        wait_seconds / 3600 if wait_seconds else 0.0,
        window_start,
        window_end,
    )
    time.sleep(wait_seconds)


def fetch_gdelt_historical(
    since_dt: datetime,
    until_dt: datetime | None = None,
    conservative: bool = False,
    resume: bool = False,
    off_hours: bool = False,
    off_hours_start: int = GDELT_OFF_HOURS_START,
    off_hours_end: int = GDELT_OFF_HOURS_END,
    max_backoff_seconds: float = GDELT_MAX_BACKOFF_SECONDS,
) -> list[dict]:
    """Fetch GDELT in monthly batches from since_dt to until_dt."""
    if until_dt is None:
        until_dt = datetime.now(timezone.utc)
    all_articles: list[dict] = []
    cursor = since_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    batch_pause = GDELT_CONSERVATIVE_BATCH_PAUSE if conservative else GDELT_BATCH_PAUSE

    if resume:
        checkpoint = load_checkpoint()
        if checkpoint and checkpoint.get("mode") == "historical":
            checkpoint_until = checkpoint.get("until")
            checkpoint_next = checkpoint.get("next_cursor")
            checkpoint_conservative = bool(checkpoint.get("conservative"))
            if checkpoint_until == until_dt.strftime("%Y-%m-%d") and checkpoint_next:
                cursor = datetime.strptime(checkpoint_next, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                conservative = checkpoint_conservative or conservative
                batch_pause = GDELT_CONSERVATIVE_BATCH_PAUSE if conservative else GDELT_BATCH_PAUSE
                off_hours = bool(checkpoint.get("off_hours")) or off_hours
                off_hours_start = int(checkpoint.get("off_hours_start", off_hours_start))
                off_hours_end = int(checkpoint.get("off_hours_end", off_hours_end))
                log.info(f"Resuming GDELT historical run from checkpoint at {cursor.date()}")

    while cursor < until_dt:
        if cursor.month == 12:
            batch_end = cursor.replace(year=cursor.year + 1, month=1)
        else:
            batch_end = cursor.replace(month=cursor.month + 1)
        batch_end = min(batch_end, until_dt)
        write_checkpoint({
            "mode": "historical",
            "since": since_dt.strftime("%Y-%m-%d"),
            "until": until_dt.strftime("%Y-%m-%d"),
            "next_cursor": cursor.strftime("%Y-%m-%d"),
            "conservative": conservative,
            "off_hours": off_hours,
            "off_hours_start": off_hours_start,
            "off_hours_end": off_hours_end,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        if off_hours:
            _sleep_until_off_hours(off_hours_start, off_hours_end)
        articles = fetch_gdelt_range(
            cursor,
            batch_end,
            conservative=conservative,
            max_backoff_seconds=max_backoff_seconds,
        )
        all_articles.extend(normalize_gdelt(articles))
        cursor = batch_end
        write_checkpoint({
            "mode": "historical",
            "since": since_dt.strftime("%Y-%m-%d"),
            "until": until_dt.strftime("%Y-%m-%d"),
            "next_cursor": cursor.strftime("%Y-%m-%d"),
            "conservative": conservative,
            "off_hours": off_hours,
            "off_hours_start": off_hours_start,
            "off_hours_end": off_hours_end,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        time.sleep(batch_pause)
    clear_checkpoint()
    log.info(f"GDELT historical total: {len(all_articles)} articles across all batches")
    return all_articles


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Fetch GDELT articles for SENTINEL")
    parser.add_argument("--historical", action="store_true", help="Fetch monthly historical batches")
    parser.add_argument("--since", type=str, default=None, help="Start date YYYY-MM-DD for historical mode")
    parser.add_argument("--until", type=str, default=None, help="End date YYYY-MM-DD for historical mode")
    parser.add_argument("--conservative", action="store_true", help="Use smaller requests, narrower query, and longer pauses")
    parser.add_argument("--resume", action="store_true", help="Resume a historical run from data/staging/gdelt_checkpoint.json if present")
    parser.add_argument("--clear-checkpoint", action="store_true", help="Delete the saved GDELT historical checkpoint and exit")
    parser.add_argument("--off-hours", action="store_true", help="For historical mode, only run monthly batches during the local off-hours window")
    parser.add_argument("--off-hours-start", type=int, default=GDELT_OFF_HOURS_START, help="Local start hour for off-hours mode (0-23)")
    parser.add_argument("--off-hours-end", type=int, default=GDELT_OFF_HOURS_END, help="Local end hour for off-hours mode (0-23)")
    parser.add_argument("--max-backoff-seconds", type=float, default=GDELT_MAX_BACKOFF_SECONDS, help="Stop retrying when a single rate-limit wait would exceed this threshold")
    args = parser.parse_args()

    if args.clear_checkpoint:
        clear_checkpoint()
        print(json.dumps({"status": "checkpoint_cleared", "path": str(CHECKPOINT_PATH)}, ensure_ascii=False, indent=2))
        return

    if args.historical:
        if not args.since:
            raise ValueError("--historical requires --since YYYY-MM-DD")
        since_dt = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        until_dt = datetime.strptime(args.until, "%Y-%m-%d").replace(tzinfo=timezone.utc) if args.until else None
        rows = fetch_gdelt_historical(
            since_dt,
            until_dt=until_dt,
            conservative=args.conservative,
            resume=args.resume,
            off_hours=args.off_hours,
            off_hours_start=args.off_hours_start,
            off_hours_end=args.off_hours_end,
            max_backoff_seconds=args.max_backoff_seconds,
        )
    else:
        rows = normalize_gdelt(
            fetch_gdelt(
                conservative=args.conservative,
                max_backoff_seconds=args.max_backoff_seconds,
            )
        )

    print(json.dumps({"count": len(rows), "articles": rows}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
