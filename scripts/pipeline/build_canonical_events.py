#!/usr/bin/env python3
"""
SENTINEL canonical event assembler.

Builds a schema-aligned canonical event dataset from the current live event store.

Outputs:
  data/canonical/events.json
  data/canonical/events.jsonl
  data/canonical/articles.json
  data/canonical/event_article_links.json
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent.parent
EVENTS_IN = ROOT / "data" / "events.json"
OUT_DIR = ROOT / "data" / "canonical"
JSON_OUT = OUT_DIR / "events.json"
JSONL_OUT = OUT_DIR / "events.jsonl"
ARTICLES_OUT = OUT_DIR / "articles.json"
ARTICLE_LINKS_OUT = OUT_DIR / "event_article_links.json"


CONFIDENCE_MAP = {
    "green": "high",
    "yellow": "medium",
    "red": "low",
    "high": "high",
    "medium": "medium",
    "low": "low",
}


ACTOR_TYPE_MAP = {
    "military": "military",
    "executive": "executive",
    "judiciary": "judiciary",
    "legislature": "legislature",
    "civil_society": "civil_society",
    "external": "foreign_government",
    "oc_group": "organized_crime",
    "population": "protesters",
}


def load_events() -> tuple[dict, list[dict]]:
    raw = json.loads(EVENTS_IN.read_text(encoding="utf-8"))
    events = raw.get("events", []) if isinstance(raw, dict) else raw
    return raw, events


def parse_date_parts(date_str: str) -> tuple[int | None, int | None, int | None]:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.year, dt.month, dt.day
    except Exception:
        return None, None, None


def to_actor_object(name: str | None, role: str, country: str) -> dict | None:
    if not name:
        return None
    actor_type = ACTOR_TYPE_MAP.get(name, "other")
    return {
        "actor_name": name,
        "actor_type": actor_type,
        "actor_subtype": None,
        "actor_country": country or None,
        "actor_role_in_event": role,
    }


def timeline_entry(stage: str, at: str | None, label: str, details: dict | None = None, status: str = "completed") -> dict:
    return {
        "stage": stage,
        "label": label,
        "status": status,
        "at": at,
        "details": details or {},
    }


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


def infer_source_name(url: str | None, fallback: str | None = None) -> str | None:
    if fallback:
        return fallback
    return infer_domain(url)


def article_id_for_url(url: str | None, source_name: str | None) -> str:
    key = f"{url or ''}|{source_name or ''}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def build_article_records(
    *,
    event_id: str,
    headline: str,
    source_primary: str,
    source_all: list[str],
    url_primary: str,
    url_all: list[str],
    source_type: str | None,
    linked_at: str,
) -> list[dict]:
    urls = unique_nonempty(url_all or [url_primary])
    sources = unique_nonempty(source_all or [source_primary])
    rows: list[dict] = []

    if not urls and source_primary:
        urls = [url_primary]

    for idx, url in enumerate(urls):
        source_name = infer_source_name(
            url,
            sources[idx] if idx < len(sources) else (source_primary if idx == 0 else None),
        ) or source_primary
        role = "primary" if idx == 0 or url == url_primary else "supporting"
        rows.append(
            {
                "article_id": article_id_for_url(url, source_name),
                "event_id": event_id,
                "article_rank": idx + 1,
                "report_role": role,
                "source_name": source_name,
                "url": url,
                "link_domain": infer_domain(url),
                "headline": headline if role == "primary" else None,
                "source_type": source_type,
                "linked_at": linked_at,
            }
        )

    if not rows and source_primary:
        rows.append(
            {
                "article_id": article_id_for_url(url_primary, source_primary),
                "event_id": event_id,
                "article_rank": 1,
                "report_role": "primary",
                "source_name": source_primary,
                "url": url_primary,
                "link_domain": infer_domain(url_primary),
                "headline": headline,
                "source_type": source_type,
                "linked_at": linked_at,
            }
        )

    return rows


def existing_linked_reports(event: dict) -> list[dict]:
    reports = event.get("linked_reports") or []
    out: list[dict] = []
    seen: set[str] = set()
    for idx, report in enumerate(reports, start=1):
        key = report.get("article_id") or report.get("url") or f"report-{idx}"
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "article_id": report.get("article_id") or article_id_for_url(report.get("url"), report.get("source_name") or report.get("source")),
                "event_id": event.get("id", ""),
                "article_rank": report.get("article_rank") or idx,
                "report_role": report.get("report_role") or ("primary" if idx == 1 else "supporting"),
                "source_name": report.get("source_name") or report.get("source"),
                "url": report.get("url"),
                "link_domain": report.get("link_domain") or infer_domain(report.get("url")),
                "headline": report.get("headline") or (event.get("title") if idx == 1 else None),
                "source_type": report.get("source_type") or event.get("source_type"),
                "linked_at": report.get("linked_at"),
            }
        )
    return out


def canonicalize_event(event: dict, source_updated_at: str | None) -> dict:
    event_date = event.get("date", "")
    year, month, day = parse_date_parts(event_date)
    coords = event.get("coords") or [None, None]
    if len(coords) != 2:
        coords = [None, None]

    source_all = event.get("sources") or ([event.get("source")] if event.get("source") else [])
    url_all = event.get("links") or ([event.get("url")] if event.get("url") else [])
    source_primary = source_all[0] if source_all else (event.get("source") or "")
    event_id = event.get("id", "")
    url_primary = url_all[0] if url_all else (event.get("url") or f"sentinel:event:{event_id}")

    actor_primary_name = event.get("actor") or None
    actor_secondary_name = event.get("target") or None
    country = event.get("country", "")

    actors = []
    primary_actor = to_actor_object(actor_primary_name, "initiator", country)
    secondary_actor = to_actor_object(actor_secondary_name, "target", country)
    if primary_actor:
        actors.append(primary_actor)
    if secondary_actor:
        actors.append(secondary_actor)

    salience = event.get("salience", "low")
    review_priority = "high" if salience == "high" else "medium" if salience == "medium" else "low"
    ingested_at = event.get("ingested_at") or source_updated_at or datetime.now(UTC).isoformat()
    merge_strategy = "clustered_source_merge" if len(source_all) > 1 else "single_source"
    linked_reports = existing_linked_reports(event) or build_article_records(
        event_id=event_id,
        headline=event.get("title", ""),
        source_primary=source_primary,
        source_all=source_all,
        url_primary=url_primary,
        url_all=url_all,
        source_type=event.get("source_type"),
        linked_at=ingested_at,
    )
    timeline = [
        timeline_entry(
            "ingestion",
            ingested_at,
            "Source ingestion",
            {
                "source_type": event.get("source_type"),
                "source_primary": source_primary,
                "source_count": len(source_all),
                "linked_report_count": len(linked_reports),
                "has_external_url": bool(event.get("url") or event.get("links")),
            },
        ),
        timeline_entry(
            "normalization",
            source_updated_at or ingested_at,
            "Source record normalized",
            {
                "normalized_fields": [
                    "event_date",
                    "country",
                    "source_primary",
                    "url_primary",
                    "summary",
                ],
                "location_available": bool(event.get("location")),
                "coords_available": bool(event.get("coords")),
            },
        ),
        timeline_entry(
            "classification",
            source_updated_at or ingested_at,
            "Event classified",
            {
                "event_type": event.get("type", "other"),
                "raw_confidence": event.get("conf"),
                "classification_model": "claude-haiku-4-5-20251001",
            },
        ),
        timeline_entry(
            "canonicalization",
            source_updated_at or ingested_at,
            "Canonical event assembled",
            {
                "merge_strategy": merge_strategy,
                "source_event_id": event.get("sentinel_id"),
            },
        ),
    ]

    return {
        "event_id": event.get("id", ""),
        "event_date": event_date,
        "year": year,
        "month": month,
        "day": day,
        "country": country,
        "subnational_location": event.get("location") or None,
        "location_text": event.get("location") or None,
        "latitude": coords[0],
        "longitude": coords[1],
        "headline": event.get("title", ""),
        "source_primary": source_primary,
        "source_all": source_all,
        "url_primary": url_primary,
        "url_all": url_all,
        "language": None,
        "event_type": event.get("type", "other"),
        "event_subtype": event.get("subtype") or None,
        "salience": salience,
        "confidence": CONFIDENCE_MAP.get(event.get("conf", "low"), "low"),
        "summary": event.get("summary") or None,
        "classification_reason": event.get("ai_analysis") or None,
        "classification_rule_ids": [],
        "actors": actors,
        "actor_primary_name": actor_primary_name,
        "actor_primary_type": ACTOR_TYPE_MAP.get(actor_primary_name, "other") if actor_primary_name else None,
        "actor_secondary_name": actor_secondary_name,
        "actor_secondary_type": ACTOR_TYPE_MAP.get(actor_secondary_name, "other") if actor_secondary_name else None,
        "duplicate_group_id": None,
        "duplicate_status": "distinct",
        "review_status": "auto",
        "review_priority": review_priority,
        "review_notes": None,
        "reviewed_by": None,
        "reviewed_at": None,
        "provenance": {
            "source_type": event.get("source_type"),
            "ingested_at": ingested_at,
            "classification_model": "claude-haiku-4-5-20251001",
            "merge_strategy": merge_strategy,
            "source_event_id": event.get("sentinel_id"),
            "deed_type": event.get("deed_type"),
            "axis": event.get("axis"),
            "raw_confidence": event.get("conf"),
            "has_external_url": bool(event.get("url") or event.get("links")),
            "article_link_count": len(linked_reports),
            "article_record_ids": [row["article_id"] for row in linked_reports],
            "linked_reports": linked_reports,
            "timeline": timeline,
        },
        "created_at": ingested_at,
        "updated_at": source_updated_at or ingested_at,
        "published_at": None,
    }


def validate_minimal(record: dict) -> list[str]:
    errors: list[str] = []
    required = [
        "event_id", "event_date", "year", "month", "day", "country",
        "headline", "source_primary", "url_primary", "event_type",
        "salience", "confidence", "review_status", "created_at", "updated_at",
    ]
    for key in required:
        value = record.get(key)
        if value in (None, ""):
            errors.append(f"missing:{key}")
    return errors


def main() -> None:
    raw, events = load_events()
    source_updated_at = raw.get("updated") if isinstance(raw, dict) else None

    canonical_rows = [canonicalize_event(event, source_updated_at) for event in events]
    article_catalog: dict[str, dict] = {}
    event_article_links: list[dict] = []
    for row in canonical_rows:
        for report in (row.get("provenance") or {}).get("linked_reports", []):
            article_catalog.setdefault(
                report["article_id"],
                {
                    "article_id": report["article_id"],
                    "source_name": report.get("source_name"),
                    "url": report.get("url"),
                    "link_domain": report.get("link_domain"),
                    "headline": report.get("headline"),
                    "source_type": report.get("source_type"),
                    "first_linked_at": report.get("linked_at"),
                },
            )
            event_article_links.append(
                {
                    "event_id": row.get("event_id"),
                    "article_id": report["article_id"],
                    "article_rank": report.get("article_rank"),
                    "report_role": report.get("report_role"),
                    "source_name": report.get("source_name"),
                    "url": report.get("url"),
                    "link_domain": report.get("link_domain"),
                    "linked_at": report.get("linked_at"),
                }
            )
    validation_errors = [
        {"event_id": row.get("event_id"), "errors": validate_minimal(row)}
        for row in canonical_rows
    ]
    validation_errors = [row for row in validation_errors if row["errors"]]

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_file": str(EVENTS_IN.relative_to(ROOT)),
        "source_updated_at": source_updated_at,
        "count": len(canonical_rows),
        "validation_error_count": len(validation_errors),
        "events": canonical_rows,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    JSONL_OUT.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in canonical_rows),
        encoding="utf-8",
    )
    ARTICLES_OUT.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(UTC).isoformat(),
                "source_file": str(EVENTS_IN.relative_to(ROOT)),
                "count": len(article_catalog),
                "articles": list(article_catalog.values()),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    ARTICLE_LINKS_OUT.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(UTC).isoformat(),
                "source_file": str(EVENTS_IN.relative_to(ROOT)),
                "count": len(event_article_links),
                "links": event_article_links,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Wrote canonical JSON to {JSON_OUT}")
    print(f"Wrote canonical JSONL to {JSONL_OUT}")
    print(f"Wrote canonical article catalog to {ARTICLES_OUT}")
    print(f"Wrote canonical event/article links to {ARTICLE_LINKS_OUT}")
    print(f"Events assembled: {len(canonical_rows)}")
    print(f"Unique linked articles: {len(article_catalog)}")
    print(f"Event/article links: {len(event_article_links)}")
    print(f"Validation errors: {len(validation_errors)}")


if __name__ == "__main__":
    main()
