#!/usr/bin/env python3
"""
SENTINEL QA report generator.

Reads data/events.json and writes data/review/qa_report.json.
This is intentionally stdlib-only so it can run in CI without extra dependencies.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
EVENTS_PATH = ROOT / "data" / "events.json"
OUT_PATH = ROOT / "data" / "review" / "qa_report.json"

ALLOWED_TYPES = {
    "coup", "purge", "aid", "coop", "protest", "reform",
    "conflict", "exercise", "procurement", "peace", "oc", "other",
}
ALLOWED_SALIENCE = {"high", "medium", "low"}
ALLOWED_CONF = {"green", "yellow", "red", "high", "medium", "low"}


def load_events() -> list[dict]:
    raw = json.loads(EVENTS_PATH.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        return raw.get("events", [])
    return raw


def make_flag(event_id: str, severity: str, code: str, message: str, details: dict | None = None) -> dict:
    key = f"{event_id}|{severity}|{code}|{message}"
    flag_id = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    return {
        "flag_id": flag_id,
        "event_id": event_id,
        "severity": severity,
        "code": code,
        "message": message,
        "details": details,
    }


def valid_date(value: str | None) -> bool:
    if not value:
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def coord_status(coords: object) -> str:
    if coords is None:
        return "missing"
    if not isinstance(coords, list) or len(coords) != 2:
        return "invalid"
    lat, lon = coords
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return "invalid"
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return "invalid"
    return "ok"


def build_flags(events: list[dict]) -> list[dict]:
    flags: list[dict] = []
    ids = Counter(ev.get("id") for ev in events if ev.get("id"))

    for ev in events:
        event_id = ev.get("id", "missing-id")
        ev_type = ev.get("type")
        salience = ev.get("salience")
        conf = ev.get("conf")
        cstatus = coord_status(ev.get("coords"))

        if not ev.get("id"):
            flags.append(make_flag(event_id, "high", "missing_id", "Event is missing an id."))
        elif ids[event_id] > 1:
            flags.append(make_flag(event_id, "high", "duplicate_id", "Event id appears more than once.", {"count": ids[event_id]}))

        if not valid_date(ev.get("date")):
            flags.append(make_flag(event_id, "high", "invalid_date", "Event date is missing or not YYYY-MM-DD.", {"date": ev.get("date")}))

        if not ev.get("country"):
            flags.append(make_flag(event_id, "high", "missing_country", "Event is missing a country."))

        if ev_type not in ALLOWED_TYPES:
            flags.append(make_flag(event_id, "high", "invalid_type", "Event type is outside the controlled taxonomy.", {"type": ev_type}))

        if salience not in ALLOWED_SALIENCE:
            flags.append(make_flag(event_id, "medium", "invalid_salience", "Salience is missing or outside the controlled values.", {"salience": salience}))

        if conf not in ALLOWED_CONF:
            flags.append(make_flag(event_id, "medium", "invalid_confidence", "Confidence is missing or outside the controlled values.", {"conf": conf}))

        if not ev.get("url"):
            flags.append(make_flag(event_id, "high", "missing_url", "Primary source URL is missing."))

        if not ev.get("source"):
            flags.append(make_flag(event_id, "medium", "missing_source", "Primary source is missing."))

        if not ev.get("summary"):
            flags.append(make_flag(event_id, "medium", "missing_summary", "Event summary is missing."))

        if cstatus == "missing":
            flags.append(make_flag(event_id, "medium", "missing_coords", "Coordinates are missing."))
        elif cstatus == "invalid":
            flags.append(make_flag(event_id, "high", "invalid_coords", "Coordinates are invalid.", {"coords": ev.get("coords")}))

        if salience == "high" and not ev.get("ai_analysis"):
            flags.append(make_flag(event_id, "medium", "missing_analysis", "High-salience event is missing AI analysis."))

        if ev_type in {"coup", "purge", "conflict", "oc"} and not ev.get("actor"):
            flags.append(make_flag(event_id, "medium", "missing_actor", "Event type usually requires actor coding, but actor is empty."))

        if ev_type in {"coup", "purge", "conflict", "oc", "protest"} and not ev.get("target"):
            flags.append(make_flag(event_id, "low", "missing_target", "Event may benefit from target coding, but target is empty."))

    return flags


def main() -> None:
    events = load_events()
    flags = build_flags(events)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_file": str(EVENTS_PATH.relative_to(ROOT)),
        "event_count": len(events),
        "flag_count": len(flags),
        "severity_counts": dict(Counter(flag["severity"] for flag in flags)),
        "flags": flags,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote QA report to {OUT_PATH}")
    print(f"Events checked: {len(events)}")
    print(f"Flags created: {len(flags)}")


if __name__ == "__main__":
    main()
