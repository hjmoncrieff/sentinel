#!/usr/bin/env python3
"""
Generate structured council-of-analysts output for every event.

Outputs:
  data/review/council_analyses.json
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
EDITED_IN = ROOT / "data" / "review" / "events_with_edits.json"
CANONICAL_IN = ROOT / "data" / "canonical" / "events_actor_coded.json"
OUT = ROOT / "data" / "review" / "council_analyses.json"
ANALYST_KNOWLEDGE = ROOT / "config" / "agents" / "analyst_knowledge.json"
COUNCIL_GUIDANCE = ROOT / "config" / "agents" / "council_guidance.json"
COUNCIL_ROLES = ROOT / "config" / "agents" / "council_roles.json"
AI_WORKERS = ROOT / "config" / "agents" / "ai_workers.json"

HUMAN_REVIEW_STATUSES = {
    "ra_reviewed",
    "analyst_reviewed",
    "coordinator_approved",
    "reviewed",
    "published",
}

DEFAULT_GUIDANCE = {"global_rules": [], "roles": []}
DEFAULT_KNOWLEDGE = {
    "interpretive_rules": [],
    "relationship_types": [],
    "cmr_role_domains": [],
    "cmr_oc_interaction_types": [],
}
DEFAULT_WORKERS = {"workers": []}


def load_source() -> tuple[Path, dict]:
    source = EDITED_IN if EDITED_IN.exists() else CANONICAL_IN
    return source, json.loads(source.read_text(encoding="utf-8"))


def reviewed_by_human(event: dict) -> bool:
    return bool(event.get("human_validated")) or event.get("review_status") in HUMAN_REVIEW_STATUSES


def actor_names(event: dict) -> list[str]:
    names = []
    for actor in event.get("actors", []) or []:
        name = actor.get("actor_canonical_name") or actor.get("actor_name")
        if name:
            names.append(str(name))
    return names


def role_guidance(guidance: dict, code: str) -> dict:
    for role in guidance.get("roles", []):
        if role.get("code") == code:
            return role
    return {"priorities": [], "questions": []}


def worker_lookup(payload: dict) -> dict[str, dict]:
    return {
        str(worker.get("code")): worker
        for worker in payload.get("workers", [])
        if worker.get("code")
    }


def worker_ref(workers: dict[str, dict], code: str) -> dict:
    worker = workers.get(code, {})
    return {
        "code": code,
        "label": worker.get("label", code),
        "stage": worker.get("stage", "analysis"),
        "primary_outputs": worker.get("primary_outputs", []),
    }


def worker_triggered(workers: dict[str, dict], code: str, trigger: str) -> bool:
    worker = workers.get(code, {})
    return trigger in set(worker.get("supervision_triggers", []))


def concept_codes(rows: list[dict]) -> set[str]:
    return {str(row.get("code")) for row in rows if row.get("code")}


def infer_role_domains(event: dict, knowledge: dict) -> list[str]:
    event_type = str(event.get("event_type") or "")
    domains = []
    if event_type in {"conflict", "oc", "protest"}:
        domains.append("public_security")
    if event_type in {"reform", "procurement", "exercise", "aid"}:
        domains.append("external_defense")
    if event_type in {"purge", "coup", "protest"}:
        domains.append("political_influence")
    if event_type in {"coop", "reform"}:
        domains.append("governance_tasks")
    allowed = concept_codes(knowledge.get("cmr_role_domains", []))
    return [domain for domain in domains if domain in allowed] or ["public_security"]


def infer_relationship_types(event: dict, knowledge: dict) -> list[str]:
    event_type = str(event.get("event_type") or "")
    relationships = []
    if event_type == "coup":
        relationships.append("REL_PRAETORIAN")
    if event_type == "purge":
        relationships.extend(["REL_BARGAINING", "REL_PARTISAN_PILLAR"])
    if event_type == "protest":
        relationships.append("REL_TUTELARY_VETO")
    if event_type in {"conflict", "oc"}:
        relationships.append("REL_CORRUPTION_CAPTURE")
    if event.get("human_validated"):
        relationships.append("REL_SUBORDINATE")
    allowed = concept_codes(knowledge.get("relationship_types", []))
    filtered = [rel for rel in relationships if rel in allowed]
    return filtered[:3] or ["REL_SUBORDINATE"]


def infer_interaction_types(event: dict, knowledge: dict) -> list[str]:
    event_type = str(event.get("event_type") or "")
    interactions = []
    if event_type in {"conflict", "oc", "protest"}:
        interactions.append("INT_CONFRONTATION")
    if event_type in {"coop", "aid", "exercise"}:
        interactions.append("INT_JOINT_OPERATION")
    if event_type in {"reform", "procurement"}:
        interactions.append("INT_GOVERNANCE_ROLE")
    if event_type == "oc":
        interactions.append("INT_DEPLOYMENT")
    if event_type == "coup":
        interactions.append("INT_REFUSAL_OR_DEFECTION")
    allowed = concept_codes(knowledge.get("cmr_oc_interaction_types", []))
    filtered = [item for item in interactions if item in allowed]
    return filtered[:3] or ["INT_DEPLOYMENT"]


def risk_level(event: dict, elevated_types: set[str], medium_types: set[str]) -> str:
    salience = event.get("salience")
    event_type = event.get("event_type")
    if event_type in elevated_types or salience == "high":
        return "high"
    if event_type in medium_types or salience == "medium":
        return "medium"
    return "low"


def readable_join(items: list[str]) -> str:
    items = [item for item in items if item]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def readable_label(code: str) -> str:
    return str(code or "").replace("REL_", "").replace("INT_", "").replace("_", " ").lower()


def synthesis_opening(event: dict, overall: str, role_domains: list[str]) -> str:
    country = event.get("country") or "this country"
    event_type = str(event.get("event_type") or "other")
    subtype = str(event.get("event_subtype") or "").strip()
    domain_text = readable_join([domain.replace("_", " ") for domain in role_domains[:2]])
    if event_type == "coup":
        return f"In {country}, this event matters because it points to direct stress on the constitutional balance between civilian authorities and the armed forces."
    if event_type == "purge":
        return f"In {country}, this event matters because changes inside the security hierarchy can reshape command cohesion, loyalty, and the balance between political leadership and the officer corps."
    if event_type == "protest":
        return f"In {country}, this event matters because it links public contention to the behavior of security forces and therefore to the legitimacy of coercive state power."
    if event_type in {"conflict", "oc"}:
        return f"In {country}, this event matters because it bears on who controls coercive force in practice and whether security institutions are containing or deepening instability."
    if event_type in {"reform", "coop", "aid", "exercise", "procurement"}:
        return f"In {country}, this event matters because it may alter how security institutions are organized, equipped, or externally aligned over time."
    detail = f" under the subtype {subtype}" if subtype else ""
    domain_phrase = f" in the domain of {domain_text}" if domain_text else ""
    return f"In {country}, this {event_type} event{detail} matters because it can affect how coercive institutions are positioned within the political order{domain_phrase}."


def synthesis_country_effect(event: dict, overall: str, relationship_types: list[str], interaction_types: list[str]) -> str:
    country = event.get("country") or "the country"
    event_type = str(event.get("event_type") or "other")
    rels = {readable_label(item) for item in relationship_types}
    ints = {readable_label(item) for item in interaction_types}

    if event_type in {"protest", "conflict", "oc"}:
        if "tutelary veto" in rels or "praetorian" in rels:
            return f"If this pattern persists, it would suggest that security actors in {country} are becoming more politically consequential, not merely operational."
        if "confrontation" in ints:
            return f"The broader implication for {country} is a higher risk that coercive governance becomes normalized as a response to social or territorial stress."
        return f"The broader implication for {country} is pressure on state capacity and on the credibility of civilian control over the security apparatus."

    if event_type == "purge":
        if "partisan pillar" in rels or "bargaining" in rels:
            return f"The broader effect could be to make the security hierarchy in {country} more politically dependent on the executive, even if short-run control appears stronger."
        return f"The broader effect could be to unsettle command relationships in {country} and increase uncertainty about internal military cohesion."

    if event_type == "coup":
        return f"The broader effect for {country} is to raise doubts about whether political disputes will continue to be resolved within constitutional channels."

    if event_type in {"reform", "coop", "aid", "exercise", "procurement"}:
        if "joint operation" in ints:
            return f"Over time, this could shift the security posture of {country} by reinforcing particular doctrines, partners, or operational priorities."
        return f"Over time, this could change the institutional direction of the security sector in {country}, even if immediate effects remain limited."

    return f"Taken together, the event is best read as a signal about the current trajectory of civil-military and security politics in {country}."


def synthesis_monitor_line(overall: str, reviewed: bool, disagreement: bool) -> str:
    if disagreement:
        return "The main point to monitor next is whether subsequent reporting confirms this as an isolated incident or the start of a wider shift."
    if overall == "high":
        return "Users should watch for follow-on moves by state security actors, political elites, or armed challengers that confirm a broader change in trajectory."
    if not reviewed:
        return "This interpretation should be treated as provisional until more reporting clarifies whether the event is isolated or part of a developing pattern."
    return "The main question is whether this episode remains contained or begins to shape broader security and political behavior."


def build_upstream_worker_outputs(event: dict, workers: dict[str, dict], reviewed: bool) -> dict[str, dict]:
    confidence = str(event.get("confidence") or "").lower()
    duplicate_status = str(event.get("duplicate_status") or "")
    actor_count = len(event.get("actors") or [])
    publication_blocked = confidence == "low" and not reviewed
    outputs = {
        "event_classifier": {
            "worker": worker_ref(workers, "event_classifier"),
            "outputs": {
                "event_type": event.get("event_type"),
                "event_subtype": event.get("event_subtype"),
                "confidence": event.get("confidence"),
            },
            "triggered_supervision": [
                trigger for trigger in (
                    "low_confidence" if confidence == "low" else None,
                    "taxonomy_edge_case" if event.get("event_type") in {"other", None, ""} else None,
                ) if trigger and worker_triggered(workers, "event_classifier", trigger)
            ],
        },
        "actor_coder": {
            "worker": worker_ref(workers, "actor_coder"),
            "outputs": {
                "actor_count": actor_count,
                "primary_actor": event.get("actor_primary_name"),
                "secondary_actor": event.get("actor_secondary_name"),
            },
            "triggered_supervision": [
                trigger for trigger in (
                    "missing_actor" if actor_count == 0 else None,
                    "actor_role_uncertainty" if any((actor.get("coding_confidence") or "medium") == "low" for actor in (event.get("actors") or [])) else None,
                    "named_actor_ambiguity" if any((actor.get("actor_registry_status") or "") == "needs_registry_entry" for actor in (event.get("actors") or [])) else None,
                ) if trigger and worker_triggered(workers, "actor_coder", trigger)
            ],
        },
        "duplicate_analyst": {
            "worker": worker_ref(workers, "duplicate_analyst"),
            "outputs": {
                "duplicate_status": duplicate_status or "distinct",
                "merged_into_event_id": event.get("merged_into_event_id"),
            },
            "triggered_supervision": [
                trigger for trigger in (
                    "possible_duplicate" if duplicate_status == "possible_duplicate" else None,
                    "keeper_choice_needed" if duplicate_status == "possible_duplicate" else None,
                ) if trigger and worker_triggered(workers, "duplicate_analyst", trigger)
            ],
        },
        "qa_scorer": {
            "worker": worker_ref(workers, "qa_scorer"),
            "outputs": {
                "resolved_qa_flag_count": len(event.get("resolved_qa_flags") or []),
                "review_priority": event.get("review_priority"),
            },
            "triggered_supervision": [
                trigger for trigger in (
                    "field_missing" if not event.get("url_primary") or not event.get("headline") else None,
                ) if trigger and worker_triggered(workers, "qa_scorer", trigger)
            ],
        },
        "publication_policy_agent": {
            "worker": worker_ref(workers, "publication_policy_agent"),
            "outputs": {
                "review_status": event.get("review_status"),
                "human_validated": bool(event.get("human_validated")),
                "publication_blocked": publication_blocked,
            },
            "triggered_supervision": [
                trigger for trigger in (
                    "low_confidence_requires_human_review" if publication_blocked else None,
                    "manual_release_check" if event.get("salience") == "high" and not reviewed else None,
                ) if trigger and worker_triggered(workers, "publication_policy_agent", trigger)
            ],
        },
    }
    return outputs


def recommend_review_actions(event: dict, analyses: dict[str, dict], worker_outputs: dict[str, dict], reviewed: bool) -> list[dict]:
    actions: list[dict] = []
    confidence = str(event.get("confidence") or "").lower()
    if worker_outputs["actor_coder"]["triggered_supervision"]:
        actions.append({
            "code": "actor_follow_up",
            "priority": "high" if len(event.get("actors") or []) == 0 else "medium",
            "reason": "Actor coding is incomplete or uncertain.",
        })
    if worker_outputs["duplicate_analyst"]["triggered_supervision"]:
        actions.append({
            "code": "duplicate_review",
            "priority": "medium",
            "reason": "Potential duplicate conflict still needs a keeper decision.",
        })
    if confidence == "low" and not reviewed:
        actions.append({
            "code": "human_corroboration",
            "priority": "high",
            "reason": "Low-confidence event should be corroborated before publication.",
        })
    if event.get("salience") == "high" and not reviewed:
        actions.append({
            "code": "high_salience_review",
            "priority": "high",
            "reason": "High-salience event should receive human review.",
        })
    risk_levels = {lens: (row or {}).get("risk_level") for lens, row in analyses.items() if lens != "synthesis"}
    if len({level for level in risk_levels.values() if level}) > 1:
        actions.append({
            "code": "resolve_ai_disagreement",
            "priority": "medium",
            "reason": "Council lenses disagree on the event's level of concern.",
        })
    if any((row or {}).get("risk_level") == "high" for row in analyses.values()):
        actions.append({
            "code": "review_high_risk_assessment",
            "priority": "medium",
            "reason": "At least one AI lens assessed the event as high risk.",
        })
    deduped: list[dict] = []
    seen_codes: set[str] = set()
    for action in actions:
        if action["code"] in seen_codes:
            continue
        seen_codes.add(action["code"])
        deduped.append(action)
    return deduped


def cmr_analysis(event: dict, knowledge: dict, guidance: dict) -> dict:
    event_type = event.get("event_type") or "other"
    country = event.get("country") or "the country"
    actors = actor_names(event)
    role_info = role_guidance(guidance, "cmr")
    relationship_types = infer_relationship_types(event, knowledge)
    role_domains = infer_role_domains(event, knowledge)
    signals = []
    if event_type in {"coup", "purge", "protest"}:
        signals.append("civil_military_tension")
    if event_type in {"purge", "reform"}:
        signals.append("command_structure_change")
    if any("Executive branch" in actor for actor in actors):
        signals.append("executive_security_link")
    if any("Armed forces" in actor for actor in actors):
        signals.append("military_involvement")
    if not signals:
        signals.append("routine_monitoring")
    signals.extend(role_domains)
    signals.extend(rel.lower() for rel in relationship_types[:2])
    signals = list(dict.fromkeys(signals))
    assessment = {
        "coup": f"AI-generated CMR analysis: the event may signal a direct challenge to civilian authority or an attempted power intervention in {country}.",
        "purge": f"AI-generated CMR analysis: the event suggests politically salient change inside the security hierarchy in {country}.",
        "protest": f"AI-generated CMR analysis: the event links public contention to state security actors in {country}, which may affect civil-military legitimacy.",
        "reform": f"AI-generated CMR analysis: the event may reshape institutional rules governing security actors in {country}.",
        "coop": f"AI-generated CMR analysis: the event may affect external influence over security institutions in {country}.",
    }.get(event_type, f"AI-generated CMR analysis: the event is relevant to how security institutions are positioned within the political order in {country}.")
    assessment += (
        f" Role domains in view: {', '.join(role_domains)}. "
        f"Relationship cues: {', '.join(relationship_types)}. "
        f"Primary priorities: {', '.join(role_info.get('priorities', [])[:3])}."
    )
    return {
        "lens": "cmr",
        "assessment": assessment,
        "risk_level": risk_level(event, {"coup", "purge"}, {"protest", "reform", "coop"}),
        "signals": signals,
        "confidence": 0.62 if event.get("salience") == "high" else 0.54,
        "ai_generated": True,
        "knowledge_trace": {
            "role_domains": role_domains,
            "relationship_types": relationship_types,
            "guidance_priorities": role_info.get("priorities", [])[:3],
        },
    }


def political_risk_analysis(event: dict, knowledge: dict, guidance: dict) -> dict:
    event_type = event.get("event_type") or "other"
    country = event.get("country") or "the country"
    role_info = role_guidance(guidance, "political_risk")
    relationship_types = infer_relationship_types(event, knowledge)
    signals = []
    if event_type in {"coup", "purge"}:
        signals.append("elite_instability")
    if event_type in {"protest", "conflict", "oc"}:
        signals.append("coercive_stress")
    if event.get("salience") == "high":
        signals.append("high_attention_event")
    if not signals:
        signals.append("baseline_monitoring")
    if any(rel in {"REL_PRAETORIAN", "REL_PARTISAN_PILLAR"} for rel in relationship_types):
        signals.append("institutional_power_shift")
    signals = list(dict.fromkeys(signals))
    assessment = {
        "coup": f"AI-generated political-risk analysis: the event points to severe regime stress or attempted institutional rupture in {country}.",
        "purge": f"AI-generated political-risk analysis: the event may reflect elite conflict or preemptive consolidation in {country}.",
        "protest": f"AI-generated political-risk analysis: the event may increase short-run instability through confrontation between society and the security apparatus in {country}.",
        "conflict": f"AI-generated political-risk analysis: the event may worsen territorial insecurity and state-capacity strain in {country}.",
        "oc": f"AI-generated political-risk analysis: the event may intensify criminal-state competition and undermine local order in {country}.",
    }.get(event_type, f"AI-generated political-risk analysis: the event may alter the short-run stability outlook in {country}.")
    assessment += (
        f" Relationship cues: {', '.join(relationship_types)}. "
        f"Primary priorities: {', '.join(role_info.get('priorities', [])[:3])}."
    )
    return {
        "lens": "political_risk",
        "assessment": assessment,
        "risk_level": risk_level(event, {"coup", "conflict", "oc"}, {"purge", "protest", "procurement"}),
        "signals": signals,
        "confidence": 0.64 if event.get("salience") == "high" else 0.55,
        "ai_generated": True,
        "knowledge_trace": {
            "relationship_types": relationship_types,
            "guidance_priorities": role_info.get("priorities", [])[:3],
        },
    }


def regional_security_analysis(event: dict, knowledge: dict, guidance: dict) -> dict:
    event_type = event.get("event_type") or "other"
    country = event.get("country") or "the country"
    actors = actor_names(event)
    role_info = role_guidance(guidance, "regional_security")
    interaction_types = infer_interaction_types(event, knowledge)
    signals = []
    if event_type in {"conflict", "oc", "coop", "aid", "exercise", "procurement"}:
        signals.append("security_architecture_relevance")
    if any(name in {"United States", "External actors"} or "United States" in name for name in actors):
        signals.append("external_actor_involvement")
    if event_type in {"oc", "conflict"}:
        signals.append("transnational_threat_pressure")
    if not signals:
        signals.append("regional_context_watch")
    signals.extend(interaction.lower() for interaction in interaction_types[:2])
    signals = list(dict.fromkeys(signals))
    assessment = {
        "coop": f"AI-generated regional-security analysis: the event may deepen cross-border or bilateral security alignment affecting {country}.",
        "aid": f"AI-generated regional-security analysis: the event may expand external support channels shaping the security environment around {country}.",
        "exercise": f"AI-generated regional-security analysis: the event may signal interoperability and readiness priorities with regional implications for {country}.",
        "procurement": f"AI-generated regional-security analysis: the event may change force capabilities or deterrence signaling relevant to {country}.",
        "oc": f"AI-generated regional-security analysis: the event may reflect evolving organized-crime pressure with transnational spillover risk around {country}.",
        "conflict": f"AI-generated regional-security analysis: the event may affect broader regional threat dynamics around {country}.",
    }.get(event_type, f"AI-generated regional-security analysis: the event should be monitored for spillover or alignment effects beyond {country}.")
    assessment += (
        f" Interaction cues: {', '.join(interaction_types)}. "
        f"Primary priorities: {', '.join(role_info.get('priorities', [])[:3])}."
    )
    return {
        "lens": "regional_security",
        "assessment": assessment,
        "risk_level": risk_level(event, {"conflict", "oc"}, {"coop", "aid", "exercise", "procurement"}),
        "signals": signals,
        "confidence": 0.61 if event.get("salience") == "high" else 0.53,
        "ai_generated": True,
        "knowledge_trace": {
            "interaction_types": interaction_types,
            "guidance_priorities": role_info.get("priorities", [])[:3],
        },
    }


def synthesis(event: dict, cmr: dict, political: dict, regional: dict, guidance: dict, knowledge: dict) -> dict:
    levels = [cmr["risk_level"], political["risk_level"], regional["risk_level"]]
    if "high" in levels:
        overall = "high"
    elif "medium" in levels:
        overall = "medium"
    else:
        overall = "low"
    unique_signals = sorted(set(cmr["signals"] + political["signals"] + regional["signals"]))
    role_info = role_guidance(guidance, "synthesis")
    role_domains = infer_role_domains(event, knowledge)
    relationship_types = infer_relationship_types(event, knowledge)
    interaction_types = infer_interaction_types(event, knowledge)
    disagreement = len({cmr["risk_level"], political["risk_level"], regional["risk_level"]}) > 1
    reviewed = reviewed_by_human(event)
    assessment = " ".join(
        [
            synthesis_opening(event, overall, role_domains),
            synthesis_country_effect(event, overall, relationship_types, interaction_types),
            synthesis_monitor_line(overall, reviewed, disagreement),
        ]
    ).strip()
    return {
        "lens": "synthesis",
        "assessment": assessment,
        "risk_level": overall,
        "signals": unique_signals[:8],
        "confidence": round((cmr["confidence"] + political["confidence"] + regional["confidence"]) / 3, 2),
        "ai_generated": True,
        "knowledge_trace": {
            "guidance_priorities": role_info.get("priorities", [])[:3],
            "interpretive_rules": knowledge.get("interpretive_rules", [])[:3],
            "role_domains": role_domains,
            "relationship_types": relationship_types[:3],
            "interaction_types": interaction_types[:3],
            "lens_disagreement": disagreement,
        },
    }


def build_entry(event: dict, knowledge: dict, guidance: dict, workers: dict[str, dict]) -> dict:
    cmr = cmr_analysis(event, knowledge, guidance)
    political = political_risk_analysis(event, knowledge, guidance)
    regional = regional_security_analysis(event, knowledge, guidance)
    combined = synthesis(event, cmr, political, regional, guidance, knowledge)
    reviewed = reviewed_by_human(event)
    analyses = {
        "cmr": cmr,
        "political_risk": political,
        "regional_security": regional,
        "synthesis": combined,
    }
    upstream_worker_outputs = build_upstream_worker_outputs(event, workers, reviewed)
    recommended_review_actions = recommend_review_actions(event, analyses, upstream_worker_outputs, reviewed)
    return {
        "event_id": event.get("event_id"),
        "event_date": event.get("event_date"),
        "country": event.get("country"),
        "event_type": event.get("event_type"),
        "salience": event.get("salience"),
        "review_status": event.get("review_status"),
        "human_validated": bool(event.get("human_validated")),
        "reviewed_by_human": reviewed,
        "analysis_scope": "all_events",
        "analysis_tag": "AI-generated analysis",
        "generation_method": "heuristic_council_v2",
        "generated_at": datetime.now(UTC).isoformat(),
        "upstream_worker_outputs": upstream_worker_outputs,
        "recommended_review_actions": recommended_review_actions,
        "worker_trace": {
            "upstream_workers": [
                worker_ref(workers, "event_classifier"),
                worker_ref(workers, "actor_coder"),
                worker_ref(workers, "duplicate_analyst"),
                worker_ref(workers, "qa_scorer"),
                worker_ref(workers, "publication_policy_agent"),
            ],
            "council_workers": [
                worker_ref(workers, "cmr_analyst"),
                worker_ref(workers, "political_risk_analyst"),
                worker_ref(workers, "regional_security_analyst"),
                worker_ref(workers, "synthesis_analyst"),
            ],
        },
        "analyses": analyses,
    }


def main() -> None:
    source_path, payload = load_source()
    events = payload.get("events", [])
    knowledge = json.loads(ANALYST_KNOWLEDGE.read_text(encoding="utf-8")) if ANALYST_KNOWLEDGE.exists() else DEFAULT_KNOWLEDGE
    guidance = json.loads(COUNCIL_GUIDANCE.read_text(encoding="utf-8")) if COUNCIL_GUIDANCE.exists() else DEFAULT_GUIDANCE
    roles = json.loads(COUNCIL_ROLES.read_text(encoding="utf-8")) if COUNCIL_ROLES.exists() else {}
    workers_payload = json.loads(AI_WORKERS.read_text(encoding="utf-8")) if AI_WORKERS.exists() else DEFAULT_WORKERS
    workers = worker_lookup(workers_payload)
    council_rows = [build_entry(event, knowledge, guidance, workers) for event in events]
    out = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_file": str(source_path.relative_to(ROOT)),
        "generation_method": "heuristic_council_v2",
        "analysis_scope": "all_events",
        "analysis_tag": "AI-generated analysis",
        "knowledge_refs": [
            str(ANALYST_KNOWLEDGE.relative_to(ROOT)),
            str(COUNCIL_GUIDANCE.relative_to(ROOT)),
            str(COUNCIL_ROLES.relative_to(ROOT)),
            str(AI_WORKERS.relative_to(ROOT)),
        ],
        "knowledge_version": knowledge.get("version"),
        "guidance_version": guidance.get("version"),
        "role_set_version": roles.get("version"),
        "worker_registry_version": workers_payload.get("version"),
        "count": len(council_rows),
        "reviewed_event_count": sum(1 for row in council_rows if row.get("reviewed_by_human")),
        "events": council_rows,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote council analyses to {OUT}")
    print(f"Council analyses generated: {len(council_rows)}")


if __name__ == "__main__":
    main()
