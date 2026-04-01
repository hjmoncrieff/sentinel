#!/usr/bin/env python3
"""
SENTINEL actor coding scaffold.

Reads the canonical event layer and enriches actor fields into more useful,
analysis-ready actor objects and a flat actor-mentions table.

Outputs:
  data/canonical/events_actor_coded.json
  data/canonical/events_actor_coded.jsonl
  data/canonical/actor_mentions.json
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CANONICAL_IN = ROOT / "data" / "canonical" / "events.json"
OUT_DIR = ROOT / "data" / "canonical"
EVENTS_JSON_OUT = OUT_DIR / "events_actor_coded.json"
EVENTS_JSONL_OUT = OUT_DIR / "events_actor_coded.jsonl"
MENTIONS_JSON_OUT = OUT_DIR / "actor_mentions.json"
REGISTRY_IN = ROOT / "config" / "actors" / "nsva_registry_seed.json"
ACTOR_REGISTRY_IN = ROOT / "config" / "actors" / "actor_registry.json"

STATIC_NAMED_ACTOR_PATTERNS = [
    ("United States", "foreign_government", "state", [r"\bu\.s\.\b", r"\bunited states\b", r"\bamerican\b", r"\bsouthcom\b", r"\bdea\b", r"\bnavy seal", r"\bgreen beret"]),
]


GENERIC_LABELS = {
    "military": "Armed forces",
    "executive": "Executive branch",
    "judiciary": "Judiciary",
    "legislature": "Legislature",
    "civil_society": "Civil society actors",
    "population": "Civilian population / protesters",
    "external": "Foreign / external actors",
    "oc_group": "Organized crime actors",
    "other": "Other actor",
}


def load_canonical_events() -> dict:
    return json.loads(CANONICAL_IN.read_text(encoding="utf-8"))


GENERIC_SUBTYPES = {
    "military": "state_security_force",
    "executive": "state_institution",
    "judiciary": "state_institution",
    "legislature": "state_institution",
    "civil_society": "civic_actor",
    "population": "civilian_group",
    "external": "external_state_actor",
    "oc_group": "criminal_network",
    "other": "unspecified",
}


def load_registry_patterns() -> list[tuple[str, str, str | None, list[str]]]:
    sources = []
    if ACTOR_REGISTRY_IN.exists():
        sources.append(json.loads(ACTOR_REGISTRY_IN.read_text(encoding="utf-8")))
    if REGISTRY_IN.exists():
        sources.append(json.loads(REGISTRY_IN.read_text(encoding="utf-8")))
    patterns: list[tuple[str, str, str | None, list[str]]] = []
    for raw in sources:
        for actor in raw.get("actors", []):
            aliases = list(actor.get("aliases") or [])
            canonical_name = actor.get("canonical_name")
            actor_type = actor.get("canonical_type") or actor.get("actor_type")
            actor_subtype = actor.get("canonical_subtype") or actor.get("subtype")
            if canonical_name:
                aliases.append(canonical_name)
            regexes = []
            for alias in aliases:
                alias_lower = alias.lower()
                escaped = re.escape(alias_lower)
                if re.fullmatch(r"[a-z0-9\-]+", alias_lower):
                    escaped = rf"\b{escaped}\b"
                regexes.append(escaped)
            if regexes and canonical_name and actor_type:
                patterns.append((canonical_name, actor_type, actor_subtype, regexes))
    return patterns


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "unknown"


def detect_named_actor(text: str) -> tuple[str | None, str | None, str | None]:
    lowered = text.lower()
    for label, actor_type, actor_subtype, patterns in STATIC_NAMED_ACTOR_PATTERNS + load_registry_patterns():
        for pattern in patterns:
            if re.search(pattern, lowered):
                return label, actor_type, actor_subtype
    return None, None, None


def default_display_name(raw_name: str | None, actor_type: str | None, country: str | None) -> str:
    if not raw_name:
        return "Unknown actor"
    if raw_name == "external":
        return "External actors"
    if raw_name in GENERIC_LABELS:
        base = GENERIC_LABELS[raw_name]
        if country and raw_name != "external":
            return f"{base} of {country}"
        return base
    if actor_type == "foreign_government":
        return raw_name
    return raw_name.replace("_", " ").title()


def default_actor_subtype(raw_name: str | None, actor_type: str | None) -> str | None:
    if raw_name in GENERIC_SUBTYPES:
        return GENERIC_SUBTYPES[raw_name]
    if actor_type == "foreign_government":
        return "state"
    if actor_type == "organized_crime":
        return "criminal_network"
    if actor_type == "armed_group":
        return "armed_non_state_group"
    return None


def actor_id(label: str, actor_type: str, country: str | None) -> str:
    key = f"{label}|{actor_type}|{country or ''}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def enrich_actor(actor: dict, event: dict) -> dict:
    country = event.get("country")
    text = " ".join(filter(None, [
        event.get("headline"),
        event.get("summary"),
        event.get("subnational_location"),
    ]))

    raw_name = actor.get("actor_name")
    actor_type = actor.get("actor_type") or "other"

    named_label, named_type, named_subtype = detect_named_actor(text)

    # Prefer named detection for generic external or organized-crime contexts.
    # Do not override generic military actors from title mentions alone, because
    # that can mislabel domestic armed forces as "United States" in cooperation stories.
    used_named_detection = raw_name in {"external", "oc_group"} and bool(named_label)
    if used_named_detection:
        canonical_name = named_label
        canonical_type = named_type or actor_type
        canonical_subtype = named_subtype or actor.get("actor_subtype") or default_actor_subtype(raw_name, canonical_type)
    else:
        canonical_name = default_display_name(raw_name, actor_type, country)
        canonical_type = actor_type
        canonical_subtype = actor.get("actor_subtype") or default_actor_subtype(raw_name, canonical_type)

    canonical_id = actor_id(canonical_name, canonical_type, country)

    return {
        **actor,
        "actor_id": canonical_id,
        "actor_canonical_name": canonical_name,
        "actor_canonical_type": canonical_type,
        "actor_subtype": canonical_subtype,
        "actor_canonical_subtype": canonical_subtype,
        "coding_method": "heuristic_v1",
        "coding_confidence": "medium" if used_named_detection else "low",
    }


def build_mentions(events: list[dict]) -> list[dict]:
    mentions: list[dict] = []
    for event in events:
        for idx, actor in enumerate(event.get("actors", []), start=1):
            mentions.append({
                "mention_id": f"{event['event_id']}_{idx}",
                "event_id": event["event_id"],
                "event_date": event["event_date"],
                "country": event.get("country"),
                "headline": event.get("headline"),
                "actor_id": actor.get("actor_id"),
                "actor_canonical_name": actor.get("actor_canonical_name"),
                "actor_canonical_type": actor.get("actor_canonical_type"),
                "actor_canonical_subtype": actor.get("actor_canonical_subtype"),
                "actor_role_in_event": actor.get("actor_role_in_event"),
                "actor_country": actor.get("actor_country"),
                "coding_method": actor.get("coding_method"),
                "coding_confidence": actor.get("coding_confidence"),
            })
    return mentions


def append_provenance_step(event: dict, stage: str, label: str, details: dict | None = None) -> None:
    provenance = event.setdefault("provenance", {})
    timeline = provenance.setdefault("timeline", [])
    if any(item.get("stage") == stage for item in timeline):
        return
    timeline.append({
        "stage": stage,
        "label": label,
        "status": "completed",
        "at": datetime.now(UTC).isoformat(),
        "details": details or {},
    })
    timeline.sort(key=lambda item: str(item.get("at") or ""))


def main() -> None:
    payload = load_canonical_events()
    events = payload.get("events", [])
    enriched_events = []

    for event in events:
        enriched = dict(event)
        enriched_actors = [enrich_actor(actor, enriched) for actor in event.get("actors", [])]
        enriched["actors"] = enriched_actors

        if enriched_actors:
            primary = next((actor for actor in enriched_actors if actor.get("actor_role_in_event") == "initiator"), enriched_actors[0])
            enriched["actor_primary_name"] = primary.get("actor_canonical_name")
            enriched["actor_primary_type"] = primary.get("actor_canonical_type")
            secondary = next((actor for actor in enriched_actors if actor.get("actor_role_in_event") == "target"), None)
            if secondary:
                enriched["actor_secondary_name"] = secondary.get("actor_canonical_name")
                enriched["actor_secondary_type"] = secondary.get("actor_canonical_type")

        append_provenance_step(
            enriched,
            "actor_coding",
            "Actors coded",
            {
                "actor_count": len(enriched_actors),
                "actor_coding_method": "heuristic_v1",
            },
        )

        enriched_events.append(enriched)

    mentions = build_mentions(enriched_events)

    out_payload = {
        **payload,
        "generated_at": datetime.now(UTC).isoformat(),
        "actor_coding_method": "heuristic_v1",
        "actor_mentions_count": len(mentions),
        "events": enriched_events,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    EVENTS_JSON_OUT.write_text(json.dumps(out_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    EVENTS_JSONL_OUT.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in enriched_events), encoding="utf-8")
    MENTIONS_JSON_OUT.write_text(
        json.dumps({
            "generated_at": datetime.now(UTC).isoformat(),
            "count": len(mentions),
            "mentions": mentions,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Wrote actor-coded events to {EVENTS_JSON_OUT}")
    print(f"Wrote actor-coded JSONL to {EVENTS_JSONL_OUT}")
    print(f"Wrote actor mentions to {MENTIONS_JSON_OUT}")
    print(f"Events processed: {len(enriched_events)}")
    print(f"Actor mentions: {len(mentions)}")


if __name__ == "__main__":
    main()
