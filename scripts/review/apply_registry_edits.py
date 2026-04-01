#!/usr/bin/env python3
"""
Apply local-only registry edits onto the durable actor registry.

Inputs:
  config/actors/actor_registry.json
  data/review/registry_edits.local.json or data/review/registry_edits.template.json

Output:
  config/actors/actor_registry.json
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = ROOT / "config" / "actors" / "actor_registry.json"
REGISTRY_EDITS_LOCAL = ROOT / "data" / "review" / "registry_edits.local.json"
REGISTRY_EDITS_TEMPLATE = ROOT / "data" / "review" / "registry_edits.template.json"

ALLOWED_REGISTRY_FIELDS = {
    "canonical_name",
    "canonical_type",
    "canonical_subtype",
    "primary_country",
    "aliases",
    "relationship_tags",
    "registry_status",
    "source_confidence",
}


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_registry_edits_path() -> Path:
    if REGISTRY_EDITS_LOCAL.exists():
        return REGISTRY_EDITS_LOCAL
    return REGISTRY_EDITS_TEMPLATE


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


def slugify(text: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(text or "").lower()).strip("_")
    return text or "unknown"


def make_registry_id(name: str, actor_type: str, country: str | None) -> str:
    return f"actor_{slugify(country or 'regional')}_{slugify(actor_type)}_{slugify(name)}"


def registry_key(entry: dict) -> str:
    return "|".join([
        str(entry.get("canonical_name") or "").strip().lower(),
        str(entry.get("canonical_type") or "").strip().lower(),
        str(entry.get("primary_country") or "").strip().lower(),
    ])


def apply_registry_edit(registry: dict, edit: dict) -> tuple[dict, list[str]]:
    warnings: list[str] = []
    actors = registry.setdefault("actors", [])
    payload = edit.get("entry") or {}
    action = edit.get("action") or "upsert_registry_entry"
    if action == "remove_alias_from_registry_entry":
        registry_id = edit.get("registry_id")
        alias_to_remove = str(edit.get("alias") or "").strip()
        if not registry_id or not alias_to_remove:
            warnings.append("Alias removal requires registry_id and alias.")
            return registry, warnings
        target = next((actor for actor in actors if actor.get("registry_id") == registry_id), None)
        if not target:
            warnings.append("Alias removal skipped because the registry entry was not found.")
            return registry, warnings
        target["aliases"] = [
            alias for alias in normalize_list(target.get("aliases"))
            if alias.strip().lower() != alias_to_remove.lower()
        ]
        target["last_modified_at"] = edit.get("edited_at") or datetime.now(UTC).isoformat()
        target["last_modified_by"] = edit.get("editor_name")
        target["last_modified_role"] = edit.get("editor_role")
        evidence = target.setdefault("evidence", {})
        if edit.get("comment"):
            evidence["latest_registry_comment"] = edit.get("comment")
        registry["updated"] = datetime.now(UTC).date().isoformat()
        registry["actors"] = sorted(actors, key=lambda item: (
            str(item.get("primary_country") or ""),
            str(item.get("canonical_type") or ""),
            str(item.get("canonical_name") or ""),
        ))
        return registry, warnings
    if action == "merge_registry_entries":
        source_id = edit.get("source_registry_id")
        target_id = edit.get("target_registry_id")
        if not source_id or not target_id or source_id == target_id:
            warnings.append("Registry merge requires distinct source_registry_id and target_registry_id.")
            return registry, warnings
        source = next((actor for actor in actors if actor.get("registry_id") == source_id), None)
        target = next((actor for actor in actors if actor.get("registry_id") == target_id), None)
        if not source or not target:
            warnings.append("Registry merge skipped because source or target entry was not found.")
            return registry, warnings

        target["aliases"] = normalize_list(normalize_list(target.get("aliases")) + normalize_list(source.get("aliases")) + [source.get("canonical_name")])
        target["relationship_tags"] = normalize_list(normalize_list(target.get("relationship_tags")) + normalize_list(source.get("relationship_tags")))
        target["registry_status"] = "registry_confirmed" if (
            target.get("registry_status") == "registry_confirmed" or source.get("registry_status") == "registry_confirmed"
        ) else (target.get("registry_status") or source.get("registry_status") or "registry_seeded")
        target["source_confidence"] = "high" if (
            target.get("source_confidence") == "high" or source.get("source_confidence") == "high"
        ) else (target.get("source_confidence") or source.get("source_confidence") or "medium")
        evidence = target.setdefault("evidence", {})
        reviewed = evidence.setdefault("reviewed_event_ids", [])
        source_reviewed = source.get("evidence", {}).get("reviewed_event_ids", [])
        for event_id in source_reviewed:
            if event_id not in reviewed:
                reviewed.append(event_id)
        evidence["reviewed_event_count"] = len(reviewed)
        merges = evidence.setdefault("merged_registry_ids", [])
        if source_id not in merges:
            merges.append(source_id)
        if edit.get("comment"):
            evidence["latest_registry_comment"] = edit.get("comment")
        target["last_modified_at"] = edit.get("edited_at") or datetime.now(UTC).isoformat()
        target["last_modified_by"] = edit.get("editor_name")
        target["last_modified_role"] = edit.get("editor_role")
        registry["actors"] = [actor for actor in actors if actor.get("registry_id") != source_id]
        registry["updated"] = datetime.now(UTC).date().isoformat()
        registry["actors"] = sorted(registry["actors"], key=lambda item: (
            str(item.get("primary_country") or ""),
            str(item.get("canonical_type") or ""),
            str(item.get("canonical_name") or ""),
        ))
        return registry, warnings
    if action != "upsert_registry_entry":
        warnings.append(f"Unsupported registry action {action!r}.")
        return registry, warnings

    for key in payload.keys():
        if key not in ALLOWED_REGISTRY_FIELDS:
            warnings.append(f"Ignored unsupported registry field {key!r}.")

    clean = {key: value for key, value in payload.items() if key in ALLOWED_REGISTRY_FIELDS}
    clean["aliases"] = normalize_list(clean.get("aliases"))
    clean["relationship_tags"] = normalize_list(clean.get("relationship_tags"))
    registry_id = edit.get("registry_id") or clean.get("registry_id")
    target = None
    if registry_id:
        target = next((actor for actor in actors if actor.get("registry_id") == registry_id), None)
    if target is None and clean.get("canonical_name") and clean.get("canonical_type"):
        key = "|".join([
            str(clean.get("canonical_name") or "").strip().lower(),
            str(clean.get("canonical_type") or "").strip().lower(),
            str(clean.get("primary_country") or "").strip().lower(),
        ])
        target = next((actor for actor in actors if registry_key(actor) == key), None)

    if target is None:
        target = {
            "registry_id": registry_id or make_registry_id(
                clean.get("canonical_name") or "unknown",
                clean.get("canonical_type") or "other",
                clean.get("primary_country"),
            ),
            "canonical_name": clean.get("canonical_name"),
            "canonical_type": clean.get("canonical_type"),
            "canonical_subtype": clean.get("canonical_subtype"),
            "primary_country": clean.get("primary_country"),
            "aliases": clean.get("aliases", []),
            "relationship_tags": clean.get("relationship_tags", []),
            "registry_status": clean.get("registry_status") or "registry_seeded",
            "source_confidence": clean.get("source_confidence") or "medium",
            "seed_source": "analyst_console",
            "evidence": {
                "seeded_from": "data/review/registry_edits.local.json",
                "reviewed_event_ids": [],
            },
        }
        actors.append(target)
    else:
        for key, value in clean.items():
            if key in {"aliases", "relationship_tags"}:
                target[key] = normalize_list(normalize_list(target.get(key)) + normalize_list(value))
            elif value not in (None, ""):
                target[key] = value

    target["last_modified_at"] = edit.get("edited_at") or datetime.now(UTC).isoformat()
    target["last_modified_by"] = edit.get("editor_name")
    target["last_modified_role"] = edit.get("editor_role")
    evidence = target.setdefault("evidence", {})
    reviewed = evidence.setdefault("reviewed_event_ids", [])
    source_event_id = edit.get("source_event_id")
    if source_event_id and source_event_id not in reviewed:
        reviewed.append(source_event_id)
    evidence["reviewed_event_count"] = len(reviewed)
    if edit.get("source_actor_id"):
        evidence["latest_source_actor_id"] = edit.get("source_actor_id")
    if edit.get("comment"):
        evidence["latest_registry_comment"] = edit.get("comment")

    registry["updated"] = datetime.now(UTC).date().isoformat()
    registry["actors"] = sorted(actors, key=lambda item: (
        str(item.get("primary_country") or ""),
        str(item.get("canonical_type") or ""),
        str(item.get("canonical_name") or ""),
    ))
    return registry, warnings


def main() -> None:
    registry = load_json(REGISTRY_PATH)
    edits_payload = load_json(resolve_registry_edits_path())
    warnings: list[str] = []
    for edit in edits_payload.get("edits", []):
        registry, edit_warnings = apply_registry_edit(registry, edit)
        warnings.extend(edit_warnings)
    write_json(REGISTRY_PATH, registry)
    print(f"Wrote {REGISTRY_PATH}")
    print(f"Registry entries: {len(registry.get('actors', []))}")
    print(f"Warnings: {len(warnings)}")
    for warning in warnings[:10]:
        print(f"WARNING: {warning}")


if __name__ == "__main__":
    main()
