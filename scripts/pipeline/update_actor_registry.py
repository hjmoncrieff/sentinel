#!/usr/bin/env python3
"""
Promote reviewed actors into the durable SENTINEL actor registry.

This bridges analyst workflow and the persistent registry by reading the
edited review layer when available and updating config/actors/actor_registry.json.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = ROOT / "config" / "actors" / "actor_registry.json"
SEED_PATH = ROOT / "config" / "actors" / "nsva_registry_seed.json"
REVIEW_EVENTS_PATH = ROOT / "data" / "review" / "events_with_edits.json"
CANONICAL_EVENTS_PATH = ROOT / "data" / "canonical" / "events_actor_coded.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def slugify(text: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return text or "unknown"


def registry_key(name: str, actor_type: str, country: str | None) -> str:
    return f"{name.strip().lower()}|{actor_type.strip().lower()}|{(country or '').strip().lower()}"


def make_registry_id(name: str, actor_type: str, country: str | None) -> str:
    country_part = slugify(country or "regional")
    return f"actor_{country_part}_{slugify(actor_type)}_{slugify(name)}"


def ensure_registry() -> dict:
    if REGISTRY_PATH.exists():
        return load_json(REGISTRY_PATH)

    seed = load_json(SEED_PATH)
    actors = []
    for item in seed.get("actors", []):
        actors.append({
            "registry_id": make_registry_id(item.get("canonical_name") or "unknown", item.get("actor_type") or "other", item.get("country")),
            "canonical_name": item.get("canonical_name"),
            "canonical_type": item.get("actor_type"),
            "canonical_subtype": item.get("subtype"),
            "primary_country": item.get("country"),
            "aliases": list(item.get("aliases") or []),
            "relationship_tags": [],
            "registry_status": "registry_confirmed" if item.get("source_confidence") == "high" else "registry_seeded",
            "source_confidence": item.get("source_confidence") or "medium",
            "seed_source": "nsva_registry_seed",
            "evidence": {
                "seeded_from": "config/actors/nsva_registry_seed.json",
                "reviewed_event_ids": [],
            },
        })
    return {
        "version": "1.0",
        "updated": datetime.now(UTC).date().isoformat(),
        "status": "active",
        "source_note": "Primary internal actor registry for SENTINEL.",
        "actors": actors,
    }


def load_events() -> list[dict]:
    source = REVIEW_EVENTS_PATH if REVIEW_EVENTS_PATH.exists() else CANONICAL_EVENTS_PATH
    payload = load_json(source)
    return payload.get("events", [])


def normalize_list(value) -> list[str]:
    if isinstance(value, list):
        values = value
    elif value in (None, ""):
        values = []
    else:
        values = [part.strip() for part in str(value).split(",")]
    out = []
    seen = set()
    for item in values:
        cleaned = str(item).strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out


def promote_registry(registry: dict, events: list[dict]) -> tuple[dict, dict]:
    actors = registry.setdefault("actors", [])
    by_key = {
        registry_key(item.get("canonical_name") or "", item.get("canonical_type") or "", item.get("primary_country")): item
        for item in actors
    }
    created = 0
    updated = 0

    for event in events:
        if str(event.get("review_status") or "").lower() in {"rejected"}:
            continue
        for actor in event.get("actors", []):
            status = actor.get("actor_registry_status")
            if status not in {"registry_seeded", "registry_confirmed"}:
                continue
            canonical_name = actor.get("actor_canonical_name") or actor.get("actor_name")
            canonical_type = actor.get("actor_canonical_type") or actor.get("actor_type") or "other"
            canonical_subtype = actor.get("actor_canonical_subtype") or actor.get("actor_subtype")
            primary_country = actor.get("actor_country") or event.get("country")
            key = registry_key(canonical_name or "", canonical_type, primary_country)
            aliases = normalize_list(actor.get("actor_aliases")) + normalize_list(actor.get("actor_name"))
            relationship_tags = normalize_list(actor.get("actor_relationship_tags"))

            existing = by_key.get(key)
            if existing is None:
                existing = {
                    "registry_id": make_registry_id(canonical_name or "unknown", canonical_type, primary_country),
                    "canonical_name": canonical_name,
                    "canonical_type": canonical_type,
                    "canonical_subtype": canonical_subtype,
                    "primary_country": primary_country,
                    "aliases": [],
                    "relationship_tags": [],
                    "registry_status": status,
                    "source_confidence": "medium",
                    "seed_source": "analyst_review_bridge",
                    "evidence": {
                        "seeded_from": "data/review/events_with_edits.json" if REVIEW_EVENTS_PATH.exists() else "data/canonical/events_actor_coded.json",
                        "reviewed_event_ids": [],
                    },
                }
                actors.append(existing)
                by_key[key] = existing
                created += 1
            else:
                updated += 1

            if status == "registry_confirmed":
                existing["registry_status"] = "registry_confirmed"
            elif existing.get("registry_status") not in {"registry_confirmed"}:
                existing["registry_status"] = "registry_seeded"

            if canonical_subtype and not existing.get("canonical_subtype"):
                existing["canonical_subtype"] = canonical_subtype

            existing_aliases = normalize_list(existing.get("aliases"))
            existing["aliases"] = normalize_list(existing_aliases + aliases)
            existing["relationship_tags"] = normalize_list(normalize_list(existing.get("relationship_tags")) + relationship_tags)
            evidence = existing.setdefault("evidence", {})
            reviewed_ids = evidence.setdefault("reviewed_event_ids", [])
            if event.get("event_id") and event["event_id"] not in reviewed_ids:
                reviewed_ids.append(event["event_id"])
            evidence["reviewed_event_count"] = len(reviewed_ids)
            if actor.get("coding_confidence") in {"high", "medium", "low"}:
                existing["latest_actor_coding_confidence"] = actor.get("coding_confidence")
            if event.get("updated_at") or event.get("reviewed_at"):
                existing["last_seen_at"] = event.get("updated_at") or event.get("reviewed_at")

    registry["updated"] = datetime.now(UTC).date().isoformat()
    registry["actors"] = sorted(actors, key=lambda item: (
        str(item.get("primary_country") or ""),
        str(item.get("canonical_type") or ""),
        str(item.get("canonical_name") or ""),
    ))
    return registry, {"created": created, "updated": updated, "count": len(registry["actors"])}


def main() -> None:
    registry = ensure_registry()
    events = load_events()
    registry, stats = promote_registry(registry, events)
    REGISTRY_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {REGISTRY_PATH}")
    print(
        "Registry entries: {count} | Created: {created} | Updated: {updated}".format(
            **stats
        )
    )


if __name__ == "__main__":
    main()
