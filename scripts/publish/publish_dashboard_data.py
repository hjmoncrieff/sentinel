#!/usr/bin/env python3
"""
Publish public-safe dashboard data from the current canonical layer.

Outputs:
  data/published/events_public.json
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.analysis.build_country_dossiers import main as build_country_dossiers_main
from scripts.analysis.validate_country_dossiers import validate_payload as validate_country_dossiers_payload

EDITED_IN = ROOT / "data" / "review" / "events_with_edits.json"
CANONICAL_IN = ROOT / "data" / "canonical" / "events_actor_coded.json"
OUT = ROOT / "data" / "published" / "events_public.json"
COUNTRY_DOSSIERS_OUT = ROOT / "data" / "published" / "country_dossiers.json"
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
    "public_category_key",
    "public_category_label",
    "public_category_rank",
    "event_signal_families",
    "event_signal_labels",
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

PUBLIC_CATEGORY_META = {
    "power_command": {"label": "Power & Command", "rank": 10},
    "security_governance": {"label": "Security Governance", "rank": 20},
    "protest_repression": {"label": "Protest & Repression", "rank": 30},
    "armed_conflict": {"label": "Armed Conflict", "rank": 40},
    "crime_illicit_economies": {"label": "Crime & Illicit Economies", "rank": 50},
    "external_security": {"label": "External Security", "rank": 60},
    "force_build_up": {"label": "Force Build-Up", "rank": 70},
    "peace_negotiation": {"label": "Peace & Negotiation", "rank": 80},
}

SIGNAL_PUBLIC_LABELS = {
    "coup_and_command_break": "Power & Command",
    "security_sector_reform_and_oversight": "Security Governance",
    "state_repression_and_exceptional_rule": "State Repression",
    "armed_conflict_and_territorial_control": "Territorial Conflict",
    "organized_crime_and_transnational_security": "Organized Crime",
    "criminal_violence_and_illicit_economies": "Illicit Economies",
    "external_security_support_and_alignment": "External Alignment",
    "military_exercises_and_force_posture": "Force Posture",
    "procurement_and_arms": "Arms Build-Up",
    "peace_process_and_ddr": "Peace Process",
    "corruption_capture_and_judicial_pressure": "Judicial Pressure",
    "border_tension_and_sovereignty": "Border Tension",
}

SIGNAL_ORDER = {
    key: index
    for index, key in enumerate([
        "coup_and_command_break",
        "security_sector_reform_and_oversight",
        "state_repression_and_exceptional_rule",
        "armed_conflict_and_territorial_control",
        "organized_crime_and_transnational_security",
        "criminal_violence_and_illicit_economies",
        "external_security_support_and_alignment",
        "military_exercises_and_force_posture",
        "procurement_and_arms",
        "peace_process_and_ddr",
        "corruption_capture_and_judicial_pressure",
        "border_tension_and_sovereignty",
    ], start=1)
}

CRIMINAL_ACTOR_MARKERS = (
    "tren de aragua",
    "sinaloa",
    "cartel",
    "cjng",
    "jalisco",
    "gulf cartel",
    "clan del golfo",
    "comando vermelho",
    "pcc",
    "mara",
    "ms-13",
    "barrio 18",
    "choneros",
    "lobos",
    "tiguerones",
    "g9",
    "viv ansanm",
    "colectivos",
)


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


def ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        key = str(value or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def get_event_family(event: dict) -> str:
    return str(
        event.get("event_category_family")
        or event.get("event_type")
        or event.get("legacy_event_family")
        or ""
    ).strip().lower()


def get_event_domain(event: dict) -> str:
    return str(
        event.get("event_type_domain")
        or event.get("event_category")
        or ""
    ).strip().lower()


def get_event_subcategory(event: dict) -> str:
    return str(event.get("event_subcategory") or "").strip().lower()


def get_actor_text(event: dict) -> str:
    values = []
    for item in event.get("actors") or []:
        if isinstance(item, str):
            values.append(item)
        elif isinstance(item, dict):
            values.extend(
                [
                    str(item.get("name") or ""),
                    str(item.get("canonical_name") or ""),
                    str(item.get("alias") or ""),
                ]
            )
    return " ".join(values).lower()


def get_public_category(event: dict) -> tuple[str, str, int]:
    family = get_event_family(event)
    domain = get_event_domain(event)
    subcategory = get_event_subcategory(event)

    if family in {"coup", "purge"}:
        key = "power_command"
    elif family == "reform":
        key = "security_governance"
    elif family == "protest":
        key = "protest_repression"
    elif family == "peace":
        key = "peace_negotiation"
    elif family == "procurement":
        key = "force_build_up"
    elif family in {"aid", "coop", "exercise"}:
        key = "external_security"
    elif family == "oc":
        key = "crime_illicit_economies"
    elif family == "conflict":
        if subcategory in {"criminal_conflict_and_fragmented_order"}:
            key = "crime_illicit_economies"
        elif subcategory in {"coercive_internal_crackdown"}:
            key = "protest_repression"
        else:
            key = "armed_conflict"
    elif family == "other":
        if subcategory in {
            "judicial_and_accountability_shock",
            "electoral_contestation_and_realignment",
            "institutional_drift_and_leadership_project",
            "other_institutional_relevance",
        }:
            key = "security_governance"
        elif subcategory in {
            "diplomatic_pressure_and_external_alignment",
            "external_pressure_and_alignment_watch",
        }:
            key = "external_security"
        elif subcategory in {"executive_removal_and_irregular_transfer"}:
            key = "power_command"
        elif any(token in subcategory for token in ("criminal", "trafficking", "illicit")):
            key = "crime_illicit_economies"
        elif domain == "international":
            key = "external_security"
        elif domain == "security":
            key = "armed_conflict"
        else:
            key = "security_governance"
    else:
        key = {
            "international": "external_security",
            "military": "force_build_up",
            "security": "armed_conflict",
            "political": "security_governance",
        }.get(domain, "security_governance")

    meta = PUBLIC_CATEGORY_META[key]
    return key, meta["label"], meta["rank"]


def get_event_signal_families(event: dict) -> list[str]:
    family = get_event_family(event)
    subcategory = get_event_subcategory(event)
    domain = get_event_domain(event)
    actor_text = get_actor_text(event)
    signals: list[str] = []

    def add(value: str) -> None:
        if value and value not in signals:
            signals.append(value)

    if family in {"coup", "purge"}:
        add("coup_and_command_break")
    if family == "reform":
        add("security_sector_reform_and_oversight")
    if family == "protest":
        add("state_repression_and_exceptional_rule")
    if family == "peace":
        add("peace_process_and_ddr")
    if family == "procurement":
        add("procurement_and_arms")
    if family in {"aid", "coop"}:
        add("external_security_support_and_alignment")
    if family == "exercise":
        add("military_exercises_and_force_posture")
    if family == "oc":
        add("organized_crime_and_transnational_security")
        add("criminal_violence_and_illicit_economies")
    if family == "conflict":
        add("armed_conflict_and_territorial_control")
        if subcategory in {"criminal_conflict_and_fragmented_order", "armed_violence_and_localized_breakdown"}:
            add("criminal_violence_and_illicit_economies")
        if subcategory == "coercive_internal_crackdown":
            add("state_repression_and_exceptional_rule")
        if "border" in subcategory or "spillover" in subcategory:
            add("border_tension_and_sovereignty")
    if family == "other":
        if subcategory in {"judicial_and_accountability_shock"}:
            add("corruption_capture_and_judicial_pressure")
        if subcategory in {
            "electoral_contestation_and_realignment",
            "institutional_drift_and_leadership_project",
            "other_institutional_relevance",
        }:
            add("security_sector_reform_and_oversight")
        if subcategory in {
            "diplomatic_pressure_and_external_alignment",
            "external_pressure_and_alignment_watch",
        }:
            add("external_security_support_and_alignment")
        if subcategory in {"executive_removal_and_irregular_transfer"}:
            add("coup_and_command_break")

    if any(marker in actor_text for marker in CRIMINAL_ACTOR_MARKERS) or any(
        token in subcategory for token in ("criminal", "trafficking", "interdiction", "illicit")
    ):
        add("organized_crime_and_transnational_security")
        add("criminal_violence_and_illicit_economies")

    if "settlement" in subcategory or "peace" in subcategory:
        add("peace_process_and_ddr")
    if "external" in subcategory or domain == "international":
        add("external_security_support_and_alignment")

    return sorted(ordered_unique(signals), key=lambda item: SIGNAL_ORDER.get(item, 999))


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
    build_country_dossiers_main(output=COUNTRY_DOSSIERS_OUT)
    dossier_payload = json.loads(COUNTRY_DOSSIERS_OUT.read_text(encoding="utf-8"))
    dossier_validation = validate_country_dossiers_payload(dossier_payload)
    if dossier_validation.get("status") != "valid":
        error_text = "; ".join(dossier_validation.get("errors", [])) or "unknown validation error"
        raise RuntimeError(f"Country dossier publication failed validation: {error_text}")

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
        row["public_classification"] = synthesis.get("classification") or {}
        row["public_ai_generated"] = bool(synthesis.get("ai_generated"))
        public_category_key, public_category_label, public_category_rank = get_public_category(event)
        signal_families = get_event_signal_families(event)
        row["public_category_key"] = public_category_key
        row["public_category_label"] = public_category_label
        row["public_category_rank"] = public_category_rank
        row["event_signal_families"] = signal_families
        row["event_signal_labels"] = [SIGNAL_PUBLIC_LABELS.get(item, item.replace("_", " ").title()) for item in signal_families]
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
    print(f"Validated country dossiers at {COUNTRY_DOSSIERS_OUT}")
    print(f"Wrote published dashboard data to {OUT}")
    print(f"Events published: {len(public_events)}")
    print(f"Events withheld: {len(withheld)}")


if __name__ == "__main__":
    main()
