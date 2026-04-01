#!/usr/bin/env python3
"""
Apply analyst console edits onto the actor-coded canonical layer.

Inputs:
  data/canonical/events_actor_coded.json
  data/review/edits.local.json or data/review/edits.template.json

Outputs:
  data/review/events_with_edits.json
  data/review/review_queue_with_edits.json
"""

from __future__ import annotations

import json
import hashlib
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CANONICAL_IN = ROOT / "data" / "canonical" / "events_actor_coded.json"
QUEUE_IN = ROOT / "data" / "review" / "review_queue.json"
EDITS_LOCAL = ROOT / "data" / "review" / "edits.local.json"
EDITS_TEMPLATE = ROOT / "data" / "review" / "edits.template.json"
EVENTS_OUT = ROOT / "data" / "review" / "events_with_edits.json"
QUEUE_OUT = ROOT / "data" / "review" / "review_queue_with_edits.json"

ALLOWED_EVENT_FIELDS = {
    "event_date",
    "year",
    "month",
    "day",
    "country",
    "subnational_location",
    "location_text",
    "latitude",
    "longitude",
    "headline",
    "source_primary",
    "url_primary",
    "language",
    "summary",
    "event_type",
    "event_subtype",
    "salience",
    "confidence",
    "classification_reason",
    "analyst_reasoning",
    "review_status",
    "review_priority",
    "duplicate_status",
    "human_validated",
    "review_notes",
}
ALLOWED_ACTOR_FIELDS = {
    "actor_name",
    "actor_canonical_name",
    "actor_canonical_type",
    "actor_canonical_subtype",
    "actor_role_in_event",
    "actor_country",
    "coding_confidence",
    "actor_registry_status",
    "actor_uncertain",
    "actor_aliases",
    "actor_relationship_tags",
}


def _dedupe_preserve_order(values: list) -> list:
    seen = set()
    out = []
    for value in values:
        key = json.dumps(value, sort_keys=True, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
        if not value or key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


def _merge_actor_lists(keeper_actors: list[dict], merged_actors: list[dict]) -> list[dict]:
    combined = []
    seen = set()
    for actor in list(keeper_actors or []) + list(merged_actors or []):
        key = (
            actor.get("actor_canonical_name") or actor.get("actor_name") or "",
            actor.get("actor_role_in_event") or "",
            actor.get("actor_country") or "",
        )
        if key in seen:
            continue
        seen.add(key)
        combined.append(deepcopy(actor))
    return combined


def _consolidate_manual_merge(keeper: dict, merged: dict, resolution: dict) -> None:
    keeper_patch = resolution.get("keeper_patch") or {}

    if keeper_patch.get("headline"):
        keeper["headline"] = keeper_patch["headline"]
    elif not keeper.get("headline") and merged.get("headline"):
        keeper["headline"] = merged.get("headline")

    if keeper_patch.get("summary"):
        keeper["summary"] = keeper_patch["summary"]
    elif not keeper.get("summary") and merged.get("summary"):
        keeper["summary"] = merged.get("summary")

    source_all = _dedupe_preserve_order(list(keeper.get("source_all") or []) + list(merged.get("source_all") or []))
    url_all = _dedupe_preserve_order(list(keeper.get("url_all") or []) + list(merged.get("url_all") or []))
    keeper["source_all"] = source_all
    keeper["url_all"] = url_all
    if not keeper.get("source_primary") and source_all:
        keeper["source_primary"] = source_all[0]
    if not keeper.get("url_primary") and url_all:
        keeper["url_primary"] = url_all[0]

    keeper["actors"] = _merge_actor_lists(keeper.get("actors") or [], merged.get("actors") or [])
    recompute_actor_summary_fields(keeper)

    keeper_prov = keeper.setdefault("provenance", {})
    merged_prov = merged.get("provenance") or {}
    keeper_reports = list(keeper_prov.get("linked_reports") or [])
    merged_reports = list(merged_prov.get("linked_reports") or [])
    keeper_prov["linked_reports"] = _dedupe_preserve_order(keeper_reports + merged_reports)
    keeper_article_ids = list(keeper_prov.get("article_record_ids") or [])
    merged_article_ids = list(merged_prov.get("article_record_ids") or [])
    keeper_prov["article_record_ids"] = _dedupe_preserve_order(keeper_article_ids + merged_article_ids)
    keeper_prov["article_link_count"] = len(keeper_prov.get("linked_reports") or [])
    keeper_prov["merge_strategy"] = "manual_event_merge"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_edits_path() -> Path:
    if EDITS_LOCAL.exists():
        return EDITS_LOCAL
    return EDITS_TEMPLATE


def role_can_edit(role_rules: dict, field_path: str) -> bool:
    editable_fields = role_rules.get("editable_fields", [])
    return "*" in editable_fields or field_path in editable_fields


def role_can_set_status(role_rules: dict, value: str | None) -> bool:
    if value is None:
        return True
    return value in role_rules.get("allowed_review_statuses", [])


def append_provenance_timeline(event: dict, stage: str, label: str, at: str | None, details: dict | None = None, status: str = "completed") -> None:
    provenance = event.setdefault("provenance", {})
    timeline = provenance.setdefault("timeline", [])
    timeline.append({
        "stage": stage,
        "label": label,
        "status": status,
        "at": at,
        "details": details or {},
    })
    timeline.sort(key=lambda item: str(item.get("at") or ""))


def make_manual_actor_id(event_id: str, actor_name: str, role: str, index: int) -> str:
    basis = f"{event_id}|{actor_name}|{role}|{index}"
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:12]


def recompute_actor_summary_fields(event: dict) -> None:
    actors = event.get("actors", [])
    primary = next((actor for actor in actors if actor.get("actor_role_in_event") == "initiator"), actors[0] if actors else None)
    secondary = next((actor for actor in actors if actor.get("actor_role_in_event") == "target"), None)
    event["actor_primary_name"] = primary.get("actor_canonical_name") if primary else None
    event["actor_primary_type"] = primary.get("actor_canonical_type") if primary else None
    event["actor_secondary_name"] = secondary.get("actor_canonical_name") if secondary else None
    event["actor_secondary_type"] = secondary.get("actor_canonical_type") if secondary else None


def apply_edit(event: dict, edit: dict, clearance_roles: dict) -> tuple[dict, list[str]]:
    role = edit.get("editor_role", "ra")
    role_rules = clearance_roles.get(role, clearance_roles.get("ra", {}))
    patch = edit.get("patch", {}) or {}
    actor_patches = edit.get("actor_patches", []) or []
    warnings: list[str] = []

    for field, value in patch.items():
        if field not in ALLOWED_EVENT_FIELDS:
            warnings.append(f"Ignored unsupported event field {field!r}.")
            continue
        if not role_can_edit(role_rules, field):
            warnings.append(f"Role {role!r} cannot edit {field!r}.")
            continue
        if field == "review_status" and not role_can_set_status(role_rules, value):
            warnings.append(f"Role {role!r} cannot set review_status={value!r}.")
            continue
        event[field] = value

    if "event_date" in patch and patch.get("event_date"):
        try:
            year_str, month_str, day_str = str(patch["event_date"]).split("-")
            event["year"] = int(year_str)
            event["month"] = int(month_str)
            event["day"] = int(day_str)
        except ValueError:
            warnings.append(f"Could not derive year/month/day from event_date={patch['event_date']!r}.")

    actors = event.get("actors", [])
    actors_by_id = {actor.get("actor_id"): actor for actor in actors if actor.get("actor_id")}
    for actor_patch in actor_patches:
        action = actor_patch.get("action", "update")
        actor_id = actor_patch.get("actor_id")
        if action == "remove":
            if not role_can_edit(role_rules, "actors.remove"):
                warnings.append(f"Role {role!r} cannot remove actors.")
                continue
            actor = actors_by_id.get(actor_id)
            if not actor:
                warnings.append(f"Actor removal skipped for unknown actor_id {actor_id!r}.")
                continue
            actors = [row for row in actors if row.get("actor_id") != actor_id]
            actors_by_id = {row.get("actor_id"): row for row in actors if row.get("actor_id")}
            continue

        patch_values = actor_patch.get("patch", {}) or {}
        for field in patch_values.keys():
            field_path = f"actors.{field}"
            if field not in ALLOWED_ACTOR_FIELDS:
                warnings.append(f"Ignored unsupported actor field {field!r}.")
                continue
            if not role_can_edit(role_rules, field_path):
                warnings.append(f"Role {role!r} cannot edit {field_path!r}.")

        if action == "create":
            if not role_can_edit(role_rules, "actors.create"):
                warnings.append(f"Role {role!r} cannot create actors.")
                continue
            canonical_name = patch_values.get("actor_canonical_name") or patch_values.get("actor_name")
            canonical_type = patch_values.get("actor_canonical_type") or "other"
            role_in_event = patch_values.get("actor_role_in_event") or "other"
            new_actor = {
                "actor_name": patch_values.get("actor_name") or canonical_name or "Unnamed actor",
                "actor_type": canonical_type,
                "actor_subtype": patch_values.get("actor_canonical_subtype"),
                "actor_country": patch_values.get("actor_country"),
                "actor_role_in_event": role_in_event,
                "actor_id": actor_patch.get("temp_actor_id") or make_manual_actor_id(
                    event.get("event_id", ""),
                    canonical_name or "Unnamed actor",
                    role_in_event,
                    len(actors) + 1,
                ),
                "actor_canonical_name": canonical_name or "Unnamed actor",
                "actor_canonical_type": canonical_type,
                "actor_canonical_subtype": patch_values.get("actor_canonical_subtype"),
                "coding_method": "analyst_manual",
                "coding_confidence": patch_values.get("coding_confidence") or "medium",
                "actor_registry_status": patch_values.get("actor_registry_status") or "needs_registry_entry",
                "actor_uncertain": bool(patch_values.get("actor_uncertain")),
                "actor_aliases": patch_values.get("actor_aliases") if isinstance(patch_values.get("actor_aliases"), list) else [part.strip() for part in str(patch_values.get("actor_aliases") or "").split(",") if part.strip()],
                "actor_relationship_tags": patch_values.get("actor_relationship_tags") if isinstance(patch_values.get("actor_relationship_tags"), list) else [part.strip() for part in str(patch_values.get("actor_relationship_tags") or "").split(",") if part.strip()],
            }
            actors.append(new_actor)
            actors_by_id[new_actor["actor_id"]] = new_actor
            continue

        actor = actors_by_id.get(actor_id)
        if not actor:
            warnings.append(f"Actor patch skipped for unknown actor_id {actor_id!r}.")
            continue
        for field, value in patch_values.items():
            field_path = f"actors.{field}"
            if field not in ALLOWED_ACTOR_FIELDS:
                continue
            if not role_can_edit(role_rules, field_path):
                continue
            if field in {"actor_aliases", "actor_relationship_tags"}:
                if isinstance(value, list):
                    actor[field] = value
                elif value in (None, ""):
                    actor[field] = []
                else:
                    actor[field] = [part.strip() for part in str(value).split(",") if part.strip()]
                continue
            if field == "actor_uncertain":
                actor[field] = bool(value)
                continue
            actor[field] = value

    event["actors"] = actors
    recompute_actor_summary_fields(event)

    event.setdefault("review_history", []).append({
        "edit_id": edit.get("edit_id"),
        "editor_name": edit.get("editor_name"),
        "editor_role": role,
        "edited_at": edit.get("edited_at"),
        "comment": edit.get("comment"),
        "status": edit.get("status", "draft"),
        "warnings": warnings,
    })
    append_provenance_timeline(
        event,
        "human_review",
        "Analyst edit applied",
        edit.get("edited_at"),
        {
            "editor_role": role,
            "editor_name": edit.get("editor_name"),
            "changed_fields": sorted(list(patch.keys())),
            "actor_patch_count": len(actor_patches),
            "actor_actions": [actor_patch.get("action", "update") for actor_patch in actor_patches],
            "status": edit.get("status", "draft"),
        },
    )
    event["updated_at"] = edit.get("edited_at") or event.get("updated_at")
    event["reviewed_by"] = edit.get("editor_name") or event.get("reviewed_by")
    return event, warnings


def build_queue_row(event: dict, existing_row: dict | None) -> dict:
    row = deepcopy(existing_row or {})
    row["event_id"] = event.get("event_id")
    row["event_date"] = event.get("event_date")
    row["country"] = event.get("country")
    row["headline"] = event.get("headline")
    row["event_type"] = event.get("event_type")
    row["salience"] = event.get("salience")
    row["confidence"] = event.get("confidence")
    row["review_status"] = event.get("review_status")
    row["review_notes"] = event.get("review_notes")
    row["latest_reviewed_by"] = event.get("reviewed_by")
    row["latest_review_history"] = event.get("review_history", [])[-1] if event.get("review_history") else None
    row["merged_into_event_id"] = event.get("merged_into_event_id")
    row["resolved_qa_flags"] = event.get("resolved_qa_flags", [])
    return row


def apply_qa_resolution(event: dict, resolution: dict) -> dict:
    if resolution.get("status") not in {"resolved", "undone"}:
        return event
    resolved = list(event.get("resolved_qa_flags", []))
    if resolution.get("status") == "resolved":
        if resolution.get("flag_id") and resolution["flag_id"] not in resolved:
            resolved.append(resolution["flag_id"])
    elif resolution.get("flag_id") in resolved:
        resolved = [flag_id for flag_id in resolved if flag_id != resolution.get("flag_id")]
    event["resolved_qa_flags"] = resolved
    event.setdefault("qa_resolution_history", []).append(resolution)
    append_provenance_timeline(
        event,
        "qa",
        "QA resolution updated",
        resolution.get("undone_at") or resolution.get("resolved_at"),
        {
            "flag_id": resolution.get("flag_id"),
            "resolution_type": resolution.get("resolution_type"),
            "editor_name": resolution.get("editor_name"),
            "status": resolution.get("status"),
        },
        status=resolution.get("status") or "resolved",
    )
    event["updated_at"] = resolution.get("resolved_at") or event.get("updated_at")
    event["reviewed_by"] = resolution.get("editor_name") or event.get("reviewed_by")
    return event


def apply_duplicate_resolution(events_by_id: dict[str, dict], resolution: dict) -> None:
    if resolution.get("status") == "undone":
        keeper_id = resolution.get("keeper_event_id")
        merged_ids = resolution.get("merged_event_ids", [])
        event_ids = resolution.get("event_ids", []) or [keeper_id, *merged_ids]
        if keeper_id in events_by_id:
            keeper = events_by_id[keeper_id]
            append_provenance_timeline(
                keeper,
                "duplicate_review",
                "Duplicate merge undone",
                resolution.get("undone_at") or resolution.get("resolved_at"),
                {
                    "candidate_id": resolution.get("candidate_id"),
                    "merged_event_ids": merged_ids,
                    "editor_name": resolution.get("editor_name"),
                    "reason_code": resolution.get("reason_code"),
                },
                status="undone",
            )
        for merged_id in merged_ids:
            if merged_id not in events_by_id:
                continue
            merged = events_by_id[merged_id]
            merged.pop("merged_into_event_id", None)
            merged["duplicate_status"] = "distinct"
            append_provenance_timeline(
                merged,
                "duplicate_review",
                "Duplicate merge undone",
                resolution.get("undone_at") or resolution.get("resolved_at"),
                    {
                        "candidate_id": resolution.get("candidate_id"),
                        "restored_from_keeper": keeper_id,
                        "editor_name": resolution.get("editor_name"),
                        "reason_code": resolution.get("reason_code"),
                    },
                    status="undone",
                )
            merged["updated_at"] = resolution.get("undone_at") or merged.get("updated_at")
        if not merged_ids:
            for event_id in [item for item in event_ids if item in events_by_id]:
                event = events_by_id[event_id]
                event["duplicate_status"] = "possible_duplicate"
                append_provenance_timeline(
                    event,
                    "duplicate_review",
                    "Distinct duplicate decision undone",
                    resolution.get("undone_at") or resolution.get("resolved_at"),
                    {
                        "candidate_id": resolution.get("candidate_id"),
                        "editor_name": resolution.get("editor_name"),
                        "reason_code": resolution.get("reason_code"),
                    },
                    status="undone",
                )
                event["updated_at"] = resolution.get("undone_at") or event.get("updated_at")
        return
    if resolution.get("status") == "distinct":
        event_ids = [item for item in (resolution.get("event_ids") or []) if item in events_by_id]
        for event_id in event_ids:
            event = events_by_id[event_id]
            event["duplicate_status"] = "distinct"
            event.setdefault("review_history", []).append({
                "edit_id": resolution.get("resolution_id"),
                "editor_name": resolution.get("editor_name"),
                "editor_role": resolution.get("editor_role"),
                "edited_at": resolution.get("resolved_at"),
                "comment": resolution.get("comment"),
                "status": "duplicate_distinct",
                "reason_code": resolution.get("reason_code"),
                "warnings": [],
            })
            append_provenance_timeline(
                event,
                "duplicate_review",
                "Duplicate candidate rejected",
                resolution.get("resolved_at"),
                {
                    "candidate_id": resolution.get("candidate_id"),
                    "event_ids": event_ids,
                    "editor_name": resolution.get("editor_name"),
                    "reason_code": resolution.get("reason_code"),
                },
            )
            event["updated_at"] = resolution.get("resolved_at") or event.get("updated_at")
        return
    if resolution.get("status") != "merged":
        return
    keeper_id = resolution.get("keeper_event_id")
    merged_ids = resolution.get("merged_event_ids", [])
    if keeper_id in events_by_id:
        keeper = events_by_id[keeper_id]
        keeper["manual_merge"] = {
            "candidate_id": resolution.get("candidate_id"),
            "merged_event_ids": merged_ids,
            "resolved_at": resolution.get("resolved_at"),
            "editor_name": resolution.get("editor_name"),
            "comment": resolution.get("comment"),
            "reason_code": resolution.get("reason_code"),
        }
        keeper["duplicate_status"] = "distinct"
        keeper.setdefault("review_history", []).append({
            "edit_id": resolution.get("resolution_id"),
            "editor_name": resolution.get("editor_name"),
            "editor_role": resolution.get("editor_role"),
                "edited_at": resolution.get("resolved_at"),
                "comment": resolution.get("comment"),
                "status": "manual_merge_keeper" if resolution.get("manual") else "duplicate_merge_keeper",
                "reason_code": resolution.get("reason_code"),
                "warnings": [],
            })
        append_provenance_timeline(
            keeper,
            "duplicate_review",
            "Manual event merge recorded" if resolution.get("manual") else "Duplicate merge recorded",
            resolution.get("resolved_at"),
                {
                    "candidate_id": resolution.get("candidate_id"),
                    "merged_event_ids": merged_ids,
                    "editor_name": resolution.get("editor_name"),
                    "reason_code": resolution.get("reason_code"),
                    "manual": bool(resolution.get("manual")),
                },
            )
        keeper["updated_at"] = resolution.get("resolved_at") or keeper.get("updated_at")
    for merged_id in merged_ids:
        if merged_id not in events_by_id:
            continue
        merged = events_by_id[merged_id]
        if keeper_id in events_by_id:
            _consolidate_manual_merge(events_by_id[keeper_id], merged, resolution)
        merged["merged_into_event_id"] = keeper_id
        merged["duplicate_status"] = "definite_duplicate"
        merged.setdefault("review_history", []).append({
            "edit_id": resolution.get("resolution_id"),
            "editor_name": resolution.get("editor_name"),
            "editor_role": resolution.get("editor_role"),
                "edited_at": resolution.get("resolved_at"),
                "comment": resolution.get("comment"),
                "status": "manual_merged_away" if resolution.get("manual") else "duplicate_merged_away",
                "reason_code": resolution.get("reason_code"),
                "warnings": [],
            })
        append_provenance_timeline(
            merged,
            "duplicate_review",
            "Event manually merged into keeper" if resolution.get("manual") else "Duplicate merged into keeper",
            resolution.get("resolved_at"),
                {
                    "candidate_id": resolution.get("candidate_id"),
                    "keeper_event_id": keeper_id,
                    "editor_name": resolution.get("editor_name"),
                    "reason_code": resolution.get("reason_code"),
                    "manual": bool(resolution.get("manual")),
                },
            )
        merged["updated_at"] = resolution.get("resolved_at") or merged.get("updated_at")


def main() -> None:
    canonical = load_json(CANONICAL_IN)
    queue = load_json(QUEUE_IN)
    edits_path = resolve_edits_path()
    edits_payload = load_json(edits_path)

    events = deepcopy(canonical.get("events", []))
    queue_items = deepcopy(queue.get("items", []))
    queue_by_id = {item["event_id"]: item for item in queue_items}

    clearance_roles = (edits_payload.get("clearance_model", {}) or {}).get("roles", {})
    edits = edits_payload.get("edits", []) or []
    qa_resolutions = edits_payload.get("qa_resolutions", []) or []
    duplicate_resolutions = edits_payload.get("duplicate_resolutions", []) or []
    edits.sort(key=lambda edit: (edit.get("edited_at") or "", edit.get("edit_id") or ""))

    events_by_id = {event["event_id"]: event for event in events}
    applied_count = 0
    warnings_total: list[dict] = []

    for edit in edits:
        if edit.get("status") == "discarded":
            continue
        event_id = edit.get("event_id")
        event = events_by_id.get(event_id)
        if not event:
            warnings_total.append({
                "edit_id": edit.get("edit_id"),
                "event_id": event_id,
                "warning": "Event not found in canonical layer.",
            })
            continue
        updated_event, warnings = apply_edit(event, edit, clearance_roles)
        events_by_id[event_id] = updated_event
        queue_by_id[event_id] = build_queue_row(updated_event, queue_by_id.get(event_id))
        applied_count += 1
        for warning in warnings:
            warnings_total.append({
                "edit_id": edit.get("edit_id"),
                "event_id": event_id,
                "warning": warning,
            })

    for resolution in qa_resolutions:
        event_id = resolution.get("event_id")
        event = events_by_id.get(event_id)
        if not event:
            continue
        events_by_id[event_id] = apply_qa_resolution(event, resolution)
        queue_by_id[event_id] = build_queue_row(events_by_id[event_id], queue_by_id.get(event_id))

    for resolution in duplicate_resolutions:
        apply_duplicate_resolution(events_by_id, resolution)
        keeper_id = resolution.get("keeper_event_id")
        if keeper_id in events_by_id:
            queue_by_id[keeper_id] = build_queue_row(events_by_id[keeper_id], queue_by_id.get(keeper_id))
        for merged_id in resolution.get("merged_event_ids", []):
            if merged_id in events_by_id:
                queue_by_id[merged_id] = build_queue_row(events_by_id[merged_id], queue_by_id.get(merged_id))
        for event_id in resolution.get("event_ids", []):
            if event_id in events_by_id:
                queue_by_id[event_id] = build_queue_row(events_by_id[event_id], queue_by_id.get(event_id))

    events_out = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": str(CANONICAL_IN.relative_to(ROOT)),
        "edits_source": str(edits_path.relative_to(ROOT)),
        "count": len(events_by_id),
        "applied_edit_count": applied_count,
        "warning_count": len(warnings_total),
        "warnings": warnings_total,
        "events": list(events_by_id.values()),
    }
    queue_out = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": str(QUEUE_IN.relative_to(ROOT)),
        "edits_source": str(edits_path.relative_to(ROOT)),
        "count": len(queue_by_id),
        "applied_edit_count": applied_count,
        "warning_count": len(warnings_total),
        "warnings": warnings_total,
        "items": sorted(
            queue_by_id.values(),
            key=lambda row: (-row.get("priority_score", 0), row.get("event_date") or "", row.get("event_id") or ""),
        ),
    }

    EVENTS_OUT.write_text(json.dumps(events_out, ensure_ascii=False, indent=2), encoding="utf-8")
    QUEUE_OUT.write_text(json.dumps(queue_out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {EVENTS_OUT}")
    print(f"Wrote {QUEUE_OUT}")
    print(f"Applied edits: {applied_count}")
    print(f"Warnings: {len(warnings_total)}")


if __name__ == "__main__":
    main()
