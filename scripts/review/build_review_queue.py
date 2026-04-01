#!/usr/bin/env python3
"""
Build an AI-supervision review queue from canonical events, QA flags, duplicate candidates,
and council-analysis disagreement signals.

Outputs:
  data/review/review_queue.json
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
EDITED_IN = ROOT / "data" / "review" / "events_with_edits.json"
CANONICAL_IN = ROOT / "data" / "canonical" / "events_actor_coded.json"
QA_IN = ROOT / "data" / "review" / "qa_report.json"
DUP_IN = ROOT / "data" / "review" / "duplicate_candidates.json"
COUNCIL_IN = ROOT / "data" / "review" / "council_analyses.json"
REGISTRY_QA_IN = ROOT / "data" / "review" / "registry_qa_report.json"
AI_WORKERS_IN = ROOT / "config" / "agents" / "ai_workers.json"
OUT = ROOT / "data" / "review" / "review_queue.json"


SEVERITY_WEIGHT = {"high": 3, "medium": 2, "low": 1}
CONFIDENCE_WEIGHT = {"low": 4, "medium": 2, "high": 0}
HUMAN_REVIEW_STATUSES = {
    "ra_reviewed",
    "analyst_reviewed",
    "coordinator_approved",
    "reviewed",
    "published",
}


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def worker_lookup(payload: dict) -> dict[str, dict]:
    return {
        str(worker.get("code")): worker
        for worker in payload.get("workers", [])
        if worker.get("code")
    }


def choose_event_source() -> tuple[Path, dict]:
    source = EDITED_IN if EDITED_IN.exists() else CANONICAL_IN
    return source, load_json(source)


def reviewed_by_human(event: dict) -> bool:
    return bool(event.get("human_validated")) or event.get("review_status") in HUMAN_REVIEW_STATUSES


def summarize_disagreement(council_row: dict | None) -> tuple[int, dict, str]:
    if not council_row:
        return 0, {}, "no_council_analysis"
    analyses = council_row.get("analyses", {})
    lens_levels = {
        lens: (analyses.get(lens) or {}).get("risk_level")
        for lens in ("cmr", "political_risk", "regional_security")
    }
    levels = [level for level in lens_levels.values() if level]
    unique = sorted(set(levels))
    if len(unique) <= 1:
        score = 0
        summary = "aligned"
    elif len(unique) == 2:
        score = 2
        summary = "partial_disagreement"
    else:
        score = 4
        summary = "strong_disagreement"
    return score, lens_levels, summary


def average_council_confidence(council_row: dict | None) -> float | None:
    if not council_row:
        return None
    analyses = council_row.get("analyses", {})
    values = []
    for lens in ("cmr", "political_risk", "regional_security", "synthesis"):
        confidence = (analyses.get(lens) or {}).get("confidence")
        if isinstance(confidence, (int, float)):
            values.append(float(confidence))
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def council_recommended_actions(council_row: dict | None) -> list[dict]:
    if not council_row:
        return []
    return list(council_row.get("recommended_review_actions") or [])


def derive_priority(score: int) -> str:
    if score >= 11:
        return "high"
    if score >= 6:
        return "medium"
    return "low"


def main() -> None:
    source_path, canonical = choose_event_source()
    qa = load_json(QA_IN)
    dup = load_json(DUP_IN)
    council = load_json(COUNCIL_IN)
    registry_qa = load_json(REGISTRY_QA_IN)
    workers = worker_lookup(load_json(AI_WORKERS_IN))

    events = canonical.get("events", [])
    qa_flags_by_event: dict[str, list[dict]] = defaultdict(list)
    for flag in qa.get("flags", []):
        qa_flags_by_event[flag["event_id"]].append(flag)

    dup_by_event: dict[str, list[dict]] = defaultdict(list)
    for candidate in dup.get("candidates", []):
        for event_id in candidate.get("event_ids", []):
            dup_by_event[event_id].append(candidate)
    council_by_event = {row["event_id"]: row for row in council.get("events", [])}
    registry_issues_by_event: dict[str, list[dict]] = defaultdict(list)
    for issue in registry_qa.get("issues", []):
        if issue.get("event_id"):
            registry_issues_by_event[issue["event_id"]].append(issue)

    queue = []
    for event in events:
        event_id = event["event_id"]
        flags = qa_flags_by_event.get(event_id, [])
        dups = dup_by_event.get(event_id, [])
        council_row = council_by_event.get(event_id)
        registry_issues = registry_issues_by_event.get(event_id, [])
        qa_score = sum(SEVERITY_WEIGHT.get(flag["severity"], 0) for flag in flags)
        registry_score = sum(SEVERITY_WEIGHT.get(issue["severity"], 0) for issue in registry_issues)
        duplicate_score = 3 * len([d for d in dups if d.get("status") == "possible_duplicate"]) + 1 * len(
            [d for d in dups if d.get("status") == "definite_duplicate"]
        )
        salience_score = 3 if event.get("salience") == "high" else 2 if event.get("salience") == "medium" else 1
        uncertainty_score = CONFIDENCE_WEIGHT.get(str(event.get("confidence") or "").lower(), 1)
        disagreement_score, council_risk_levels, disagreement_summary = summarize_disagreement(council_row)
        human_review_gap_score = 2 if (event.get("salience") == "high" and not reviewed_by_human(event)) else 0
        publication_block_score = 3 if (str(event.get("confidence") or "").lower() == "low" and not reviewed_by_human(event)) else 0
        recommended_actions = council_recommended_actions(council_row)
        action_score = sum(
            2 if action.get("priority") == "high" else 1
            for action in recommended_actions
        )
        priority_score = (
            qa_score
            + registry_score
            + duplicate_score
            + salience_score
            + uncertainty_score
            + disagreement_score
            + human_review_gap_score
            + publication_block_score
            + action_score
        )

        if priority_score <= 1:
            continue

        suggested_priority = derive_priority(priority_score)
        supervision_reasons = []
        if qa_score:
            supervision_reasons.append("qa_flags")
        if registry_score:
            supervision_reasons.append("registry_qa")
        if duplicate_score:
            supervision_reasons.append("duplicate_conflict")
        if uncertainty_score >= 2:
            supervision_reasons.append("model_uncertainty")
        if disagreement_score:
            supervision_reasons.append("ai_disagreement")
        if human_review_gap_score:
            supervision_reasons.append("high_salience_unreviewed")
        if publication_block_score:
            supervision_reasons.append("publication_corroboration_needed")
        for action in recommended_actions:
            supervision_reasons.append(f"council_action:{action.get('code')}")

        queue.append({
            "event_id": event_id,
            "event_date": event.get("event_date"),
            "country": event.get("country"),
            "headline": event.get("headline"),
            "event_type": event.get("event_type"),
            "salience": event.get("salience"),
            "confidence": event.get("confidence"),
            "review_status": event.get("review_status"),
            "review_priority": suggested_priority,
            "event_review_priority": event.get("review_priority"),
            "priority_score": priority_score,
            "ai_supervision_score": priority_score,
            "uncertainty_score": uncertainty_score,
            "disagreement_score": disagreement_score,
            "human_review_gap_score": human_review_gap_score,
            "publication_block_score": publication_block_score,
            "action_score": action_score,
            "qa_flag_count": len(flags),
            "registry_issue_count": len(registry_issues),
            "duplicate_candidate_count": len(dups),
            "reviewed_by_human": reviewed_by_human(event),
            "council_confidence_avg": average_council_confidence(council_row),
            "council_risk_levels": council_risk_levels,
            "council_disagreement_summary": disagreement_summary,
            "council_recommended_actions": recommended_actions,
            "supervision_reasons": supervision_reasons,
            "ai_workers_in_scope": [
                code for code in (
                    "event_classifier",
                    "actor_coder",
                    "duplicate_analyst",
                    "qa_scorer",
                    "publication_policy_agent",
                    "cmr_analyst",
                    "political_risk_analyst",
                    "regional_security_analyst",
                    "synthesis_analyst",
                )
                if code in workers
            ],
            "qa_flags": flags,
            "registry_issues": registry_issues,
            "duplicate_candidates": dups,
            "provenance": event.get("provenance", {}),
        })

    queue.sort(key=lambda row: (-row["priority_score"], row["event_date"] or "", row["event_id"]))

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_file": str(source_path.relative_to(ROOT)),
        "queue_model": "ai_supervision_queue_v2",
        "worker_registry_file": str(AI_WORKERS_IN.relative_to(ROOT)),
        "count": len(queue),
        "items": queue,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote review queue to {OUT}")
    print(f"Queue items: {len(queue)}")


if __name__ == "__main__":
    main()
