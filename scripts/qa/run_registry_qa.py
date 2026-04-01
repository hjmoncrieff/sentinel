#!/usr/bin/env python3
"""
SENTINEL actor registry QA generator.

Checks the durable actor registry for duplicate/conflicting entries and checks
event actors for registry-match problems. Writes a machine-readable report for
the analyst console and review queue.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = ROOT / "config" / "actors" / "actor_registry.json"
REVIEW_EVENTS_PATH = ROOT / "data" / "review" / "events_with_edits.json"
CANONICAL_EVENTS_PATH = ROOT / "data" / "canonical" / "events_actor_coded.json"
OUT_PATH = ROOT / "data" / "review" / "registry_qa_report.json"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def choose_events_source() -> tuple[Path, list[dict]]:
    source = REVIEW_EVENTS_PATH if REVIEW_EVENTS_PATH.exists() else CANONICAL_EVENTS_PATH
    payload = load_json(source)
    return source, payload.get("events", [])


def issue_id(parts: list[str]) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]


def keyify(*parts: str | None) -> str:
    return "|".join(str(part or "").strip().lower() for part in parts)


def is_generic_actor_name(name: str | None) -> bool:
    raw = str(name or "").strip().lower()
    return raw in {
        "",
        "armed forces",
        "armed forces of colombia",
        "armed forces of mexico",
        "armed forces of el salvador",
        "armed forces of venezuela",
        "executive branch",
        "judiciary",
        "legislature",
        "civil society actors",
        "civilian population / protesters",
        "foreign / external actors",
        "organized crime actors",
        "other actor",
    }


def build_registry_lookup(registry_actors: list[dict]) -> dict[str, list[dict]]:
    lookup: dict[str, list[dict]] = defaultdict(list)
    for actor in registry_actors:
        names = [actor.get("canonical_name"), *(actor.get("aliases") or [])]
        actor_type = actor.get("canonical_type")
        countries = [actor.get("primary_country"), None]
        for name in names:
            for country in countries:
                lookup[keyify(name, actor_type, country)].append(actor)
    return lookup


def find_registry_matches(actor: dict, event_country: str | None, lookup: dict[str, list[dict]]) -> list[dict]:
    names = [actor.get("actor_canonical_name"), actor.get("actor_name"), *(actor.get("actor_aliases") or [])]
    types = [actor.get("actor_canonical_type"), actor.get("actor_type")]
    countries = [actor.get("actor_country"), event_country, None]
    matches: list[dict] = []
    seen = set()
    for name in names:
        for actor_type in types:
            for country in countries:
                for match in lookup.get(keyify(name, actor_type, country), []):
                    rid = match.get("registry_id")
                    if rid and rid not in seen:
                        seen.add(rid)
                        matches.append(match)
    return matches


def make_issue(severity: str, code: str, message: str, *, registry_id: str | None = None, event_id: str | None = None, details: dict | None = None) -> dict:
    ident = issue_id([severity, code, registry_id or "", event_id or "", message])
    return {
        "issue_id": ident,
        "severity": severity,
        "code": code,
        "message": message,
        "registry_id": registry_id,
        "event_id": event_id,
        "details": details or {},
    }


def build_issues(registry_actors: list[dict], events: list[dict]) -> list[dict]:
    issues: list[dict] = []

    canonical_key_groups: dict[str, list[dict]] = defaultdict(list)
    alias_groups: dict[str, list[dict]] = defaultdict(list)
    name_groups: dict[str, list[dict]] = defaultdict(list)

    for actor in registry_actors:
        canonical_key_groups[keyify(actor.get("canonical_name"), actor.get("canonical_type"), actor.get("primary_country"))].append(actor)
        name_groups[keyify(actor.get("canonical_name"))].append(actor)
        for alias in actor.get("aliases") or []:
            alias_groups[keyify(alias, actor.get("canonical_type"))].append(actor)

    for key, grouped in canonical_key_groups.items():
        if len(grouped) <= 1:
            continue
        ids = [item.get("registry_id") for item in grouped]
        for item in grouped:
            issues.append(make_issue(
                "high",
                "duplicate_registry_entry",
                "Registry has duplicate entries with the same canonical name, type, and country.",
                registry_id=item.get("registry_id"),
                details={"registry_ids": ids, "canonical_key": key},
            ))

    for key, grouped in alias_groups.items():
        unique_ids = {item.get("registry_id") for item in grouped}
        if len(unique_ids) <= 1:
            continue
        for item in grouped:
            issues.append(make_issue(
                "medium",
                "registry_alias_collision",
                "The same alias maps to multiple registry entries of the same type.",
                registry_id=item.get("registry_id"),
                details={"alias_key": key, "registry_ids": sorted(unique_ids)},
            ))

    for key, grouped in name_groups.items():
        type_country_pairs = {(item.get("canonical_type"), item.get("primary_country")) for item in grouped}
        if len(type_country_pairs) <= 1:
            continue
        for item in grouped:
            issues.append(make_issue(
                "medium",
                "registry_name_conflict",
                "The same canonical name appears with different type/country assignments in the registry.",
                registry_id=item.get("registry_id"),
                details={"canonical_name_key": key, "assignments": sorted([f"{t}|{c}" for t, c in type_country_pairs])},
            ))

    lookup = build_registry_lookup(registry_actors)
    for event in events:
        event_id = event.get("event_id")
        for actor in event.get("actors") or []:
            matches = find_registry_matches(actor, event.get("country"), lookup)
            canonical_name = actor.get("actor_canonical_name") or actor.get("actor_name")
            if not canonical_name or is_generic_actor_name(canonical_name):
                continue

            if actor.get("actor_registry_status") in {"registry_seeded", "registry_confirmed"} and not matches:
                issues.append(make_issue(
                    "high",
                    "registry_match_missing",
                    "Actor is marked as registry-seeded/confirmed but no durable registry match was found.",
                    event_id=event_id,
                    details={
                        "actor_id": actor.get("actor_id"),
                        "actor_name": canonical_name,
                        "actor_registry_status": actor.get("actor_registry_status"),
                    },
                ))

            if actor.get("actor_uncertain") is True and matches:
                issues.append(make_issue(
                    "low",
                    "uncertain_actor_with_registry_match",
                    "Actor remains marked uncertain even though a registry match exists.",
                    event_id=event_id,
                    registry_id=matches[0].get("registry_id"),
                    details={
                        "actor_id": actor.get("actor_id"),
                        "actor_name": canonical_name,
                    },
                ))

            if actor.get("actor_uncertain") is not True and not matches and actor.get("coding_confidence") in {"high", "medium"}:
                issues.append(make_issue(
                    "medium",
                    "named_actor_unmatched",
                    "Named actor has no registry match and may need promotion or linking.",
                    event_id=event_id,
                    details={
                        "actor_id": actor.get("actor_id"),
                        "actor_name": canonical_name,
                        "coding_confidence": actor.get("coding_confidence"),
                    },
                ))

    return issues


def main() -> None:
    registry = load_json(REGISTRY_PATH)
    events_source, events = choose_events_source()
    registry_actors = registry.get("actors", [])
    issues = build_issues(registry_actors, events)

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "registry_file": str(REGISTRY_PATH.relative_to(ROOT)),
        "events_source_file": str(events_source.relative_to(ROOT)),
        "registry_entry_count": len(registry_actors),
        "issue_count": len(issues),
        "severity_counts": dict(Counter(issue["severity"] for issue in issues)),
        "issues": issues,
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote registry QA report to {OUT_PATH}")
    print(f"Registry entries checked: {len(registry_actors)}")
    print(f"Issues created: {len(issues)}")


if __name__ == "__main__":
    main()
