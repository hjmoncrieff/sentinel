#!/usr/bin/env python3
"""
Build the private gold layer from human-reviewed workflow outputs.

The gold layer collects human judgments that clear the thresholds in
config/gold_policy.json. It feeds evaluation sets, retrieval examples, and any
later task-specific training. It is never published.

Inputs:
  data/canonical/events_actor_coded.json   machine baseline (pre-edit)
  data/review/events_with_edits.json       post-review events (apply_analyst_edits.py)
  data/review/edits.local.json             raw analyst edits and decisions
  data/review/<label decision files>       adjudicated model-target labels

Outputs (data/gold/, gitignored):
  events.jsonl               accepted human-reviewed events, with a gold tier
  negatives.jsonl            events humans rejected (machine coding kept for contrast)
  corrections.jsonl          field-level machine → human correction pairs
  duplicate_decisions.jsonl  analyst merge / distinct decisions
  qa_decisions.jsonl         resolved QA flags
  labels.jsonl               adjudicated country-month target labels
  summary.json               counts, thresholds, and input fingerprints

Usage:
  python3 scripts/review/build_gold_layer.py
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
POLICY_IN = ROOT / "config" / "gold_policy.json"
CANONICAL_IN = ROOT / "data" / "canonical" / "events_actor_coded.json"
EDITED_IN = ROOT / "data" / "review" / "events_with_edits.json"
EDITS_IN = ROOT / "data" / "review" / "edits.local.json"
GOLD_DIR = ROOT / "data" / "gold"

TEMPLATE_PLACEHOLDER_COUNTRY = "Country Name"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def fingerprint(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _has_edit_warnings(event: dict) -> bool:
    return any(entry.get("warnings") for entry in event.get("review_history") or [])


def gold_tier(event: dict, policy: dict) -> str | None:
    """Highest tier an event qualifies for, or None if it is not gold-eligible."""
    status = event.get("review_status")
    if status in policy["eligible_review_statuses"]:
        return status
    if policy.get("accept_human_validated_flag") and event.get("human_validated"):
        return "human_validated"
    return None


def select_gold_events(events: list[dict], policy: dict) -> tuple[list[dict], list[dict], dict]:
    """Split post-review events into accepted gold rows, human negatives, and exclusion counts."""
    accepted: list[dict] = []
    negatives: list[dict] = []
    excluded = {"merged_away": 0, "edit_warnings": 0}
    fields = policy["gold_event_fields"]

    for event in events:
        if policy.get("exclude_merged_away_events") and event.get("merged_into_event_id"):
            excluded["merged_away"] += 1
            continue
        if event.get("review_status") in policy["negative_review_statuses"]:
            negatives.append({
                **{f: event.get(f) for f in fields},
                "review_status": event.get("review_status"),
                "review_notes": event.get("review_notes"),
            })
            continue
        tier = gold_tier(event, policy)
        if tier is None:
            continue
        if policy.get("exclude_events_with_edit_warnings") and _has_edit_warnings(event):
            excluded["edit_warnings"] += 1
            continue
        accepted.append({
            **{f: event.get(f) for f in fields},
            "gold_tier": tier,
            "gold_tier_rank": policy["tier_rank"][tier],
            "review_status": event.get("review_status"),
            "human_validated": bool(event.get("human_validated")),
            "reviewed_by": event.get("reviewed_by"),
        })

    accepted.sort(key=lambda row: (-row["gold_tier_rank"], row.get("event_date") or "", row["event_id"]))
    return accepted, negatives, excluded


def extract_corrections(edits: list[dict], machine_by_id: dict[str, dict], policy: dict) -> list[dict]:
    """Latest qualifying human value per (event, field) where it differs from the machine value."""
    role_rank = policy["editor_role_rank"]
    min_rank = role_rank[policy["min_editor_role_for_corrections"]]
    tracked = set(policy["correction_fields"])
    latest: dict[tuple[str, str], dict] = {}

    for edit in sorted(edits, key=lambda e: (e.get("edited_at") or "", e.get("edit_id") or "")):
        if edit.get("status") == "discarded":
            continue
        if role_rank.get(edit.get("editor_role"), 0) < min_rank:
            continue
        event_id = edit.get("event_id")
        machine = machine_by_id.get(event_id)
        if machine is None:
            continue
        for field, human_value in (edit.get("patch") or {}).items():
            if field not in tracked or human_value == machine.get(field):
                continue
            latest[(event_id, field)] = {
                "event_id": event_id,
                "field": field,
                "machine_value": machine.get(field),
                "human_value": human_value,
                "editor_role": edit.get("editor_role"),
                "edited_at": edit.get("edited_at"),
                "edit_id": edit.get("edit_id"),
                "comment": edit.get("comment"),
            }
    return sorted(latest.values(), key=lambda row: (row["event_id"], row["field"]))


def extract_duplicate_decisions(resolutions: list[dict]) -> list[dict]:
    rows = []
    for res in resolutions:
        if res.get("status") not in {"merged", "distinct"}:
            continue  # drafts and undone decisions are not gold
        rows.append({
            "candidate_id": res.get("candidate_id"),
            "decision": res.get("status"),
            "manual": bool(res.get("manual")),
            "keeper_event_id": res.get("keeper_event_id"),
            "merged_event_ids": res.get("merged_event_ids") or [],
            "event_ids": res.get("event_ids") or [],
            "reason_code": res.get("reason_code"),
            "editor_role": res.get("editor_role"),
            "resolved_at": res.get("resolved_at"),
        })
    return rows


def extract_qa_decisions(resolutions: list[dict]) -> list[dict]:
    return [
        {
            "event_id": res.get("event_id"),
            "flag_id": res.get("flag_id"),
            "resolution_type": res.get("resolution_type"),
            "editor_name": res.get("editor_name"),
            "resolved_at": res.get("resolved_at"),
        }
        for res in resolutions
        if res.get("status") == "resolved"
    ]


def extract_labels(label_payloads: dict[str, dict]) -> list[dict]:
    rows = []
    for rel_path, payload in sorted(label_payloads.items()):
        for row in payload.get("rows") or []:
            if row.get("country") in (None, "", TEMPLATE_PLACEHOLDER_COUNTRY):
                continue
            rows.append({**row, "label_file": rel_path})
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def build(root: Path = ROOT, out_dir: Path = GOLD_DIR) -> dict:
    policy = load_json(root / "config" / "gold_policy.json")
    canonical_path = root / "data" / "canonical" / "events_actor_coded.json"
    edited_path = root / "data" / "review" / "events_with_edits.json"
    edits_path = root / "data" / "review" / "edits.local.json"

    machine_by_id = {e["event_id"]: e for e in load_json(canonical_path).get("events", []) if e.get("event_id")}
    edited_events = load_json(edited_path).get("events", [])
    edits_payload = load_json(edits_path)

    label_paths = sorted({p for pattern in policy["label_decision_globs"] for p in root.glob(pattern)})
    label_payloads = {str(p.relative_to(root)): load_json(p) for p in label_paths}

    accepted, negatives, excluded = select_gold_events(edited_events, policy)
    outputs = {
        "events.jsonl": accepted,
        "negatives.jsonl": negatives,
        "corrections.jsonl": extract_corrections(edits_payload.get("edits") or [], machine_by_id, policy),
        "duplicate_decisions.jsonl": extract_duplicate_decisions(edits_payload.get("duplicate_resolutions") or []),
        "qa_decisions.jsonl": extract_qa_decisions(edits_payload.get("qa_resolutions") or []),
        "labels.jsonl": extract_labels(label_payloads),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in outputs.items():
        write_jsonl(out_dir / name, rows)

    tiers: dict[str, int] = {}
    for row in accepted:
        tiers[row["gold_tier"]] = tiers.get(row["gold_tier"], 0) + 1
    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "policy": policy.get("policy_name"),
        "counts": {name.removesuffix(".jsonl"): len(rows) for name, rows in outputs.items()},
        "gold_tiers": tiers,
        "excluded": excluded,
        "inputs": {
            str(p.relative_to(root)): fingerprint(p)
            for p in [canonical_path, edited_path, edits_path, *label_paths]
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    summary = build()
    print(f"Wrote gold layer to {GOLD_DIR}")
    for name, count in summary["counts"].items():
        print(f"  {name}: {count}")
    if not summary["inputs"].get("data/review/events_with_edits.json"):
        print("Note: data/review/events_with_edits.json missing — run scripts/review/apply_analyst_edits.py first.")


if __name__ == "__main__":
    main()
