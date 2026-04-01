#!/usr/bin/env python3
"""
Backfill article-link metadata into the live event store.

This upgrades older events in `data/events.json` so they carry:

- `source_article_ids`
- `linked_reports`

The backfill is inferred from existing event-level `source` / `sources` and
`url` / `links` fields. It is intended as a bridge while the ingestion layer
becomes more article-native upstream.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent.parent
EVENTS_IN = ROOT / "data" / "events.json"


def unique_nonempty(items: list[str | None]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        values.append(value)
    return values


def infer_domain(url: str | None) -> str | None:
    if not url:
        return None
    try:
        domain = (urlparse(url).netloc or "").lower()
    except Exception:
        return None
    if domain.startswith("www."):
        domain = domain[4:]
    return domain or None


def article_id_for_url(url: str | None, source_name: str | None) -> str:
    key = f"{url or ''}|{source_name or ''}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def build_linked_reports(event: dict) -> list[dict]:
    event_id = event.get("id", "")
    headline = event.get("title", "")
    source_primary = event.get("source") or ""
    source_all = unique_nonempty(event.get("sources") or [source_primary])
    url_primary = event.get("url") or ""
    url_all = unique_nonempty(event.get("links") or [url_primary])
    source_type = event.get("source_type")
    source_method = event.get("source_method") or "backfilled_from_event_store"
    linked_at = event.get("ingested_at") or datetime.now(UTC).isoformat()

    rows: list[dict] = []
    if not url_all and source_primary:
        url_all = [url_primary]

    for idx, url in enumerate(url_all):
        source_name = source_all[idx] if idx < len(source_all) else (source_primary if idx == 0 else None)
        source_name = source_name or infer_domain(url) or source_primary or "Unknown"
        role = "primary" if idx == 0 or url == url_primary else "supporting"
        rows.append(
            {
                "article_id": article_id_for_url(url, source_name),
                "article_rank": idx + 1,
                "report_role": role,
                "source_name": source_name,
                "url": url,
                "link_domain": infer_domain(url),
                "headline": headline if role == "primary" else None,
                "source_type": source_type,
                "source_method": source_method,
                "linked_at": linked_at,
                "event_id": event_id,
            }
        )

    if not rows and source_primary:
        rows.append(
            {
                "article_id": article_id_for_url(url_primary, source_primary),
                "article_rank": 1,
                "report_role": "primary",
                "source_name": source_primary,
                "url": url_primary,
                "link_domain": infer_domain(url_primary),
                "headline": headline,
                "source_type": source_type,
                "source_method": source_method,
                "linked_at": linked_at,
                "event_id": event_id,
            }
        )

    return rows


def main() -> None:
    payload = json.loads(EVENTS_IN.read_text(encoding="utf-8"))
    events = payload.get("events", payload if isinstance(payload, list) else [])

    upgraded = 0
    for event in events:
        if event.get("source_article_ids") and event.get("linked_reports"):
            continue
        linked_reports = build_linked_reports(event)
        if not linked_reports:
            continue
        event["linked_reports"] = linked_reports
        event["source_article_ids"] = [
            report.get("article_id")
            for report in linked_reports
            if report.get("article_id")
        ]
        upgraded += 1

    if isinstance(payload, dict):
        payload["updated"] = datetime.now(UTC).isoformat()
        payload["count"] = len(events)
        payload["events"] = events
        out = payload
    else:
        out = events

    EVENTS_IN.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Backfilled events: {upgraded}")
    print(f"Total events: {len(events)}")
    print(f"Wrote upgraded event store to {EVENTS_IN}")


if __name__ == "__main__":
    main()
