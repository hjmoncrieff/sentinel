#!/usr/bin/env python3
"""
Publish public-safe dashboard data from the current canonical layer.

Outputs:
  data/published/events_public.json
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
EDITED_IN = ROOT / "data" / "review" / "events_with_edits.json"
CANONICAL_IN = ROOT / "data" / "canonical" / "events_actor_coded.json"
OUT = ROOT / "data" / "published" / "events_public.json"
POLICY_IN = ROOT / "config" / "publish_policy.json"
COUNCIL_IN = ROOT / "data" / "review" / "council_analyses.json"
QA_IN = ROOT / "data" / "review" / "qa_report.json"
TAXONOMY_FALLBACK_FIELDS = [
    "event_type_domain",
    "event_category_family",
    "event_category_label",
    "event_category",
    "event_subcategory",
    "event_construct_destinations",
    "event_analyst_lenses",
]
GENERIC_TAXONOMY_VALUES = {
    "other_institutional_relevance",
    "armed_non_state_and_illicit_order",
    "conflict_management_and_settlement",
    "external_security_alignment",
    "irregular_transfer_and_command_break",
    "command_and_coercive_control",
    "external_security_support",
    "contention_and_state_response",
    "institutional_security_reordering",
    "force_posture_and_training",
    "armed_fragmentation_and_territorial_control",
}


PUBLIC_EVENT_FIELDS = [
    "event_id",
    "event_date",
    "country",
    "subnational_location",
    "latitude",
    "longitude",
    "headline",
    "source_primary",
    "source_all",
    "url_primary",
    "url_all",
    "event_type",
    "legacy_event_family",
    "event_type_domain",
    "event_category_family",
    "event_category_label",
    "event_category",
    "event_subcategory",
    "event_construct_destinations",
    "event_analyst_lenses",
    "event_subtype",
    "deed_type",
    "axis",
    "salience",
    "confidence",
    "summary",
    "actors",
    "review_status",
    "review_priority",
    "human_validated",
]

HUMAN_REVIEW_STATUSES = {
    "ra_reviewed",
    "analyst_reviewed",
    "coordinator_approved",
    "reviewed",
    "published",
}

STAGE_ORDER = {
    "ingestion": 10,
    "normalization": 20,
    "classification": 30,
    "canonicalization": 40,
    "actor_coding": 50,
    "qa": 60,
    "duplicate_review": 70,
    "human_review": 80,
    "council_analysis": 90,
    "publication_decision": 100,
    "publication": 110,
}


def is_reviewed_by_human(event: dict) -> bool:
    return bool(event.get("human_validated")) or event.get("review_status") in HUMAN_REVIEW_STATUSES


def enrich_with_canonical(events: list[dict]) -> list[dict]:
    if not CANONICAL_IN.exists():
        return events
    canonical = json.loads(CANONICAL_IN.read_text(encoding="utf-8"))
    canonical_by_event = {
        str(row.get("event_id")): row
        for row in canonical.get("events", [])
        if row.get("event_id")
    }
    enriched: list[dict] = []
    for row in events:
        merged = dict(row)
        canonical_row = canonical_by_event.get(str(row.get("event_id")))
        if canonical_row:
            for field in TAXONOMY_FALLBACK_FIELDS:
                value = merged.get(field)
                canonical_value = canonical_row.get(field)
                replace = value in (None, "", [])
                if field == "event_subcategory" and value in GENERIC_TAXONOMY_VALUES and value != canonical_value:
                    replace = True
                if field == "event_analyst_lenses" and canonical_value and value != canonical_value:
                    replace = True
                if replace:
                    merged[field] = canonical_value
        enriched.append(merged)
    return enriched


def load_publication_source() -> tuple[list[dict], str]:
    canonical_payload = json.loads(CANONICAL_IN.read_text(encoding="utf-8"))
    canonical_events = canonical_payload.get("events", [])
    canonical_by_event = {
        str(row.get("event_id")): row
        for row in canonical_events
        if row.get("event_id")
    }

    if not EDITED_IN.exists():
        return canonical_events, str(CANONICAL_IN.relative_to(ROOT))

    edited_payload = json.loads(EDITED_IN.read_text(encoding="utf-8"))
    edited_events = edited_payload.get("events", [])
    merged_by_event = dict(canonical_by_event)

    for row in edited_events:
        event_id = str(row.get("event_id"))
        if event_id:
          merged_by_event[event_id] = row

    merged_events = list(merged_by_event.values())
    return merged_events, f"{EDITED_IN.relative_to(ROOT)} + missing rows from {CANONICAL_IN.relative_to(ROOT)}"


def should_publish(event: dict, policy: dict) -> tuple[bool, str | None]:
    if event.get("merged_into_event_id"):
        return False, "merged_into_other_event"

    review_status = event.get("review_status")
    if review_status in set(policy.get("withhold_review_statuses", [])):
        return False, f"review_status:{review_status}"

    duplicate_status = event.get("duplicate_status")
    if duplicate_status in set(policy.get("withhold_duplicate_statuses", [])):
        return False, f"duplicate_status:{duplicate_status}"

    confidence = event.get("confidence")
    if (
        policy.get("low_confidence_requires_review")
        and confidence in set(policy.get("withhold_confidence_values", []))
        and not is_reviewed_by_human(event)
    ):
        return False, "low_confidence_requires_human_review"

    return True, None


def summarize_withheld(withheld: list[dict]) -> dict:
    summary: dict[str, int] = {}
    for row in withheld:
        reason = row.get("reason") or "unknown"
        summary[reason] = summary.get(reason, 0) + 1
    return dict(sorted(summary.items(), key=lambda item: (-item[1], item[0])))


def stage_sort_key(row: dict) -> tuple[int, str]:
    stage = str(row.get("stage") or "")
    return (STAGE_ORDER.get(stage, 999), str(row.get("at") or ""))


def latest_semantic_stage(timeline: list[dict]) -> str | None:
    if not timeline:
        return None
    return max(timeline, key=stage_sort_key).get("stage")


def augment_timeline_for_publication(
    event: dict,
    council_by_event: dict[str, dict],
    qa_flags_by_event: dict[str, list[dict]],
    publish: bool,
    withheld_reason: str | None,
) -> list[dict]:
    timeline = list((event.get("provenance") or {}).get("timeline") or [])
    qa_flags = qa_flags_by_event.get(event.get("event_id"), [])
    if qa_flags:
        timeline.append({
            "stage": "qa",
            "label": "QA report generated",
            "status": "flagged" if qa_flags else "completed",
            "at": None,
            "details": {
                "flag_count": len(qa_flags),
                "high_severity_count": len([flag for flag in qa_flags if flag.get("severity") == "high"]),
            },
        })
    council_row = council_by_event.get(event.get("event_id"))
    if council_row:
        timeline.append({
            "stage": "council_analysis",
            "label": "AI council analysis generated",
            "status": "completed",
            "at": council_row.get("generated_at"),
            "details": {
                "analysis_tag": council_row.get("analysis_tag"),
                "reviewed_by_human": council_row.get("reviewed_by_human"),
            },
        })
    timeline.append({
        "stage": "publication_decision",
        "label": "Publication policy evaluated",
        "status": "completed" if publish else "withheld",
        "at": datetime.now(UTC).isoformat(),
        "details": {
            "published": publish,
            "withheld_reason": withheld_reason,
        },
    })
    if publish:
        timeline.append({
            "stage": "publication",
            "label": "Published to dashboard layer",
            "status": "completed",
            "at": datetime.now(UTC).isoformat(),
            "details": {
                "output_file": str(OUT.relative_to(ROOT)),
            },
        })
    # dedupe by stage+label+at to avoid uncontrolled growth if upstream already emitted a step
    unique = []
    seen = set()
    for row in timeline:
        key = (row.get("stage"), row.get("label"), row.get("at"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return sorted(unique, key=stage_sort_key)


def public_linked_reports(event: dict) -> list[dict]:
    reports = ((event.get("provenance") or {}).get("linked_reports") or [])[:6]
    return [
        {
            "article_id": row.get("article_id"),
            "article_rank": row.get("article_rank"),
            "report_role": row.get("report_role"),
            "source_name": row.get("source_name"),
            "url": row.get("url"),
            "link_domain": row.get("link_domain"),
            "headline": row.get("headline"),
            "description": row.get("description"),
        }
        for row in reports
    ]


def main() -> None:
    source_events, source_label = load_publication_source()
    policy = json.loads(POLICY_IN.read_text(encoding="utf-8"))
    council = json.loads(COUNCIL_IN.read_text(encoding="utf-8")) if COUNCIL_IN.exists() else {"events": []}
    qa = json.loads(QA_IN.read_text(encoding="utf-8")) if QA_IN.exists() else {"flags": []}
    events = enrich_with_canonical(source_events)
    council_by_event = {row.get("event_id"): row for row in council.get("events", [])}
    qa_flags_by_event: dict[str, list[dict]] = {}
    for flag in qa.get("flags", []):
        qa_flags_by_event.setdefault(flag.get("event_id"), []).append(flag)

    public_events = []
    withheld = []
    for event in events:
        publish, withheld_reason = should_publish(event, policy)
        timeline = augment_timeline_for_publication(event, council_by_event, qa_flags_by_event, publish, withheld_reason)
        if not publish:
            withheld.append(
                {
                    "event_id": event.get("event_id"),
                    "salience": event.get("salience"),
                    "review_status": event.get("review_status"),
                    "human_validated": bool(event.get("human_validated")),
                    "reason": withheld_reason,
                    "timeline_stage_count": len(timeline),
                }
            )
            continue
        row = {field: event.get(field) for field in PUBLIC_EVENT_FIELDS}
        row["human_validated"] = bool(event.get("human_validated"))
        council_row = council_by_event.get(event.get("event_id")) or {}
        synthesis = (council_row.get("analyses") or {}).get("synthesis") or {}
        row["provenance_summary"] = {
            "merge_strategy": (event.get("provenance") or {}).get("merge_strategy"),
            "source_type": (event.get("provenance") or {}).get("source_type"),
            "has_external_url": (event.get("provenance") or {}).get("has_external_url"),
            "article_link_count": (event.get("provenance") or {}).get("article_link_count"),
            "review_status": event.get("review_status"),
            "human_validated": bool(event.get("human_validated")),
            "reviewed_by_human": is_reviewed_by_human(event),
            "timeline_stage_count": len(timeline),
            "latest_stage": latest_semantic_stage(timeline),
        }
        row["public_analysis"] = synthesis.get("public_analysis") or synthesis.get("assessment")
        row["public_takeaways"] = synthesis.get("public_takeaways")
        row["public_risk_level"] = synthesis.get("risk_level")
        row["linked_reports"] = public_linked_reports(event)
        row["provenance_timeline"] = [
            {
                "stage": item.get("stage"),
                "label": item.get("label"),
                "status": item.get("status"),
                "at": item.get("at"),
            }
            for item in timeline[-8:]
        ]
        public_events.append(row)

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_file": source_label,
        "policy": policy,
        "input_count": len(events),
        "count": len(public_events),
        "withheld_count": len(withheld),
        "withheld_summary": summarize_withheld(withheld),
        "events": public_events,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote published dashboard data to {OUT}")
    print(f"Events published: {len(public_events)}")
    print(f"Events withheld: {len(withheld)}")


if __name__ == "__main__":
    main()
