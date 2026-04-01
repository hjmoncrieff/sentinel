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
    text = str(code or "")
    if text.startswith("REL_"):
        text = text[4:]
    if text.startswith("INT_"):
        text = text[4:]
    return text.replace("_", " ").lower()


def classify_event_frame(event: dict, role_domains: list[str], interaction_types: list[str]) -> str:
    event_type = str(event.get("event_type") or "other")
    if event_type in {"coup", "purge"}:
        return "civil-military balance"
    if event_type in {"protest", "reform"}:
        return "security governance"
    if event_type in {"coop", "aid", "exercise", "procurement"}:
        return "external security alignment"
    if event_type in {"conflict", "oc"}:
        return "territorial security and organized violence"
    if "public_security" in role_domains:
        return "public-security role of the state"
    if "INT_JOINT_OPERATION" in interaction_types:
        return "security cooperation"
    return "civil-military and security politics"


def actor_focus_text(event: dict) -> str:
    actors = actor_names(event)
    if not actors:
        return ""
    named = actors[:2]
    if len(named) == 1:
        return f"The reporting centers on {named[0]}."
    return f"The reporting centers on {named[0]} and {named[1]}."


def confidence_context(event: dict) -> str:
    confidence = str(event.get("confidence") or "").lower()
    if confidence == "low":
        return "Reporting remains thin, so this should be treated as an early signal rather than a settled development."
    if confidence == "medium":
        return "The reporting is credible enough to flag a live development, but some details may still shift as coverage expands."
    return "The reporting base is comparatively strong, which makes this a more reliable indicator of a real shift or episode."


def salience_level(event: dict) -> str:
    return str(event.get("salience") or "low").lower()


def salience_interpretive_note(event: dict) -> str:
    salience = salience_level(event)
    country = event.get("country") or "the country"
    event_type = str(event.get("event_type") or "other")
    if salience == "high":
        if event_type in {"coup", "purge", "protest"}:
            return f"Because this is a high-salience event, it should be read not only as an incident but as a possible indicator of a wider shift in elite control, command relations, or coercive authority in {country}."
        if event_type in {"conflict", "oc"}:
            return f"Because this is a high-salience event, it may reveal more than localized violence: it can signal a broader change in how force, territorial control, or criminal pressure are being negotiated in {country}."
        if event_type in {"coop", "aid", "exercise", "procurement", "reform"}:
            return f"Because this is a high-salience event, it deserves interpretation at the strategic level, since it may shape the future direction of security policy and institutional alignment in {country}, not just the immediate news cycle."
        return f"Because this is a high-salience event, it should be interpreted as a potentially meaningful signal about the wider trajectory of security politics in {country}."
    if salience == "medium":
        return "This matters enough to monitor closely, but it should still be interpreted alongside follow-on reporting before drawing larger conclusions."
    return "At this salience level, the aim is to keep the event on the monitor rather than to treat it as strong evidence of a broader turn."


def salience_watchpoint(event: dict, disagreement: bool) -> str:
    salience = salience_level(event)
    country = event.get("country") or "the country"
    event_type = str(event.get("event_type") or "other")
    if disagreement:
        return "The main point to monitor next is whether subsequent reporting confirms this as an isolated incident or the start of a wider shift."
    if salience == "high":
        if event_type in {"coup", "purge"}:
            return f"The key next indicator is whether political leaders or security commanders in {country} make additional moves that confirm a broader struggle over control of the chain of command."
        if event_type in {"protest", "conflict", "oc"}:
            return f"The key next indicator is whether state security actors in {country} escalate, widen their role, or trigger countermoves by armed challengers or organized groups."
        return f"The key next indicator is whether officials in {country} follow this event with concrete institutional, operational, or diplomatic moves that reveal a deeper strategic shift."
    if salience == "medium":
        return "The main question is whether this episode remains contained or begins to shape broader security and political behavior."
    return "For now, the main question is simply whether the event recurs or connects to a larger developing pattern."


def subtype_text(event: dict) -> str:
    subtype = str(event.get("event_subtype") or "").strip()
    if not subtype:
        return ""
    return subtype.replace("_", " ").lower()


def public_classification(event: dict, role_domains: list[str], relationship_types: list[str], interaction_types: list[str]) -> dict:
    event_type = str(event.get("event_type") or "other")
    frame = classify_event_frame(event, role_domains, interaction_types)
    if event_type in {"coup", "purge", "protest"}:
        effect = "civil-military tension"
    elif event_type in {"conflict", "oc"}:
        effect = "coercive control and territorial order"
    elif event_type in {"coop", "aid", "exercise", "procurement"}:
        effect = "security posture and alignment"
    else:
        effect = "security-sector positioning"
    return {
        "primary_frame": frame,
        "effect_domain": effect,
        "relationship_cues": [readable_label(item) for item in relationship_types[:2]],
        "interaction_cues": [readable_label(item) for item in interaction_types[:2]],
    }


def synthesis_opening(event: dict, overall: str, role_domains: list[str]) -> str:
    country = event.get("country") or "this country"
    event_type = str(event.get("event_type") or "other")
    subtype = str(event.get("event_subtype") or "").strip()
    domain_text = readable_join([domain.replace("_", " ") for domain in role_domains[:2]])
    salience = salience_level(event)
    if event_type == "coup":
        if salience == "low":
            return f"In {country}, this is a notable signal of stress between civilian authority and the armed forces."
        return f"In {country}, this event matters because it points to direct stress on the constitutional balance between civilian authorities and the armed forces."
    if event_type == "purge":
        if salience == "low":
            return f"In {country}, this is a meaningful sign of change inside the security hierarchy."
        return f"In {country}, this event matters because changes inside the security hierarchy can reshape command cohesion, loyalty, and the balance between political leadership and the officer corps."
    if event_type == "protest":
        if salience == "low":
            return f"In {country}, this event is worth watching because it links public contention to the behavior of security forces."
        return f"In {country}, this event matters because it links public contention to the behavior of security forces and therefore to the legitimacy of coercive state power."
    if event_type in {"conflict", "oc"}:
        if salience == "low":
            return f"In {country}, this event is relevant because it touches the balance of coercive control and security pressure."
        return f"In {country}, this event matters because it bears on who controls coercive force in practice and whether security institutions are containing or deepening instability."
    if event_type in {"reform", "coop", "aid", "exercise", "procurement"}:
        if salience == "low":
            return f"In {country}, this event is relevant because it may influence the direction of security institutions over time."
        return f"In {country}, this event matters because it may alter how security institutions are organized, equipped, or externally aligned over time."
    detail = f" under the subtype {subtype}" if subtype else ""
    domain_phrase = f" in the domain of {domain_text}" if domain_text else ""
    if salience == "low":
        return f"In {country}, this {event_type} event{detail} is a monitoring signal about how coercive institutions are positioned within the political order{domain_phrase}."
    return f"In {country}, this {event_type} event{detail} matters because it can affect how coercive institutions are positioned within the political order{domain_phrase}."


def synthesis_country_effect(event: dict, overall: str, relationship_types: list[str], interaction_types: list[str]) -> str:
    country = event.get("country") or "the country"
    event_type = str(event.get("event_type") or "other")
    rels = {readable_label(item) for item in relationship_types}
    ints = {readable_label(item) for item in interaction_types}
    salience = salience_level(event)

    if event_type in {"protest", "conflict", "oc"}:
        if "tutelary veto" in rels or "praetorian" in rels:
            if salience == "low":
                return f"If similar episodes accumulate, security actors in {country} may start to look more politically consequential."
            return f"If this pattern persists, it would suggest that security actors in {country} are becoming more politically consequential, not merely operational."
        if "confrontation" in ints:
            if salience == "low":
                return f"The immediate implication for {country} is more pressure on how the state manages coercion and public order."
            return f"The broader implication for {country} is a higher risk that coercive governance becomes normalized as a response to social or territorial stress."
        if salience == "low":
            return f"The immediate implication for {country} is added pressure on state capacity and on the credibility of civilian control."
        return f"The broader implication for {country} is pressure on state capacity and on the credibility of civilian control over the security apparatus."

    if event_type == "purge":
        if "partisan pillar" in rels or "bargaining" in rels:
            if salience == "low":
                return f"The practical effect may be to make the security hierarchy in {country} more politically dependent on the executive."
            return f"The broader effect could be to make the security hierarchy in {country} more politically dependent on the executive, even if short-run control appears stronger."
        if salience == "low":
            return f"The practical effect may be greater uncertainty inside command relationships in {country}."
        return f"The broader effect could be to unsettle command relationships in {country} and increase uncertainty about internal military cohesion."

    if event_type == "coup":
        if salience == "low":
            return f"The immediate implication for {country} is fresh doubt about whether political disputes will stay within constitutional channels."
        return f"The broader effect for {country} is to raise doubts about whether political disputes will continue to be resolved within constitutional channels."

    if event_type in {"reform", "coop", "aid", "exercise", "procurement"}:
        if "joint operation" in ints:
            if salience == "low":
                return f"The practical effect may be a gradual shift in the partners or operating assumptions shaping security policy in {country}."
            return f"Over time, this could shift the security posture of {country} by reinforcing particular doctrines, partners, or operational priorities."
        if salience == "low":
            return f"The practical effect may be a modest change in the institutional direction of the security sector in {country}."
        return f"Over time, this could change the institutional direction of the security sector in {country}, even if immediate effects remain limited."

    if salience == "low":
        return f"For now, the event is best treated as a limited signal about the current direction of civil-military and security politics in {country}."
    return f"Taken together, the event is best read as a signal about the current trajectory of civil-military and security politics in {country}."


def synthesis_monitor_line(event: dict, overall: str, reviewed: bool, disagreement: bool) -> str:
    if not reviewed and salience_level(event) == "medium":
        return "This interpretation should be treated as provisional until more reporting clarifies whether the event is isolated or part of a developing pattern."
    if not reviewed and salience_level(event) == "low":
        return "For now, the main question is simply whether later reporting confirms this as part of a larger pattern."
    return salience_watchpoint(event, disagreement)


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
    subtype = subtype_text(event)
    subtype_clause = f" through a {subtype} episode" if subtype else ""
    assessment = {
        "coup": f"From a civil-military perspective, this event points to acute strain in the constitutional chain of command in {country}.",
        "purge": f"From a civil-military perspective, this event suggests politically meaningful movement inside the security hierarchy in {country}.",
        "protest": f"From a civil-military perspective, this event matters because public contention is being mediated by security actors in {country}.",
        "reform": f"From a civil-military perspective, this event bears on who defines the rules, remit, or autonomy of security institutions in {country}.",
        "coop": f"From a civil-military perspective, this event matters because outside cooperation can reinforce particular doctrines, partners, and missions inside the security apparatus of {country}.",
    }.get(event_type, f"From a civil-military perspective, this event matters because it touches the political position of coercive institutions in {country}{subtype_clause}.")
    if relationship_types:
        assessment += f" The strongest relationship cue is {readable_label(relationship_types[0])}, which helps frame how security actors relate to civilian authority."
    if role_domains:
        assessment += f" The most relevant institutional domain here is {readable_join([item.replace('_', ' ') for item in role_domains[:2]])}."
    actor_text = actor_focus_text(event)
    if actor_text:
        assessment += f" {actor_text}"
    if salience_level(event) == "high":
        assessment += f" At high salience, the civil-military question is whether this episode will affect who commands, constrains, or politically relies on the security apparatus in {country}."
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
        "coup": f"From a political-risk perspective, this event raises the possibility that major disputes in {country} are no longer being managed securely through ordinary institutional channels.",
        "purge": f"From a political-risk perspective, this event may reflect elite struggle, anticipatory consolidation, or distrust inside the security chain in {country}.",
        "protest": f"From a political-risk perspective, this event increases the chance that unrest in {country} will be interpreted through a coercive rather than political lens.",
        "conflict": f"From a political-risk perspective, this event suggests deeper stress on territorial order and state reach in {country}.",
        "oc": f"From a political-risk perspective, this event points to ongoing competition between criminal actors and the state in ways that can erode public authority in {country}.",
    }.get(event_type, f"From a political-risk perspective, this event is a signal about short-run stability and institutional confidence in {country}.")
    if relationship_types:
        assessment += f" The strongest cue is {readable_label(relationship_types[0])}, which suggests the event is not only operational but also politically structured."
    if event.get("salience") == "high":
        assessment += " Because the event is already high-salience, follow-on reactions from political elites or security actors would matter quickly."
    else:
        assessment += " The key issue is whether it remains isolated or becomes part of a broader accumulation of stress."
    if salience_level(event) == "high":
        assessment += f" In that sense, this is a higher-value signal about whether authority in {country} is becoming more contested, brittle, or dependent on coercive management."
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
        "coop": f"From a regional-security perspective, this event may tighten bilateral or cross-border security alignment around {country}.",
        "aid": f"From a regional-security perspective, this event may expand the external resources, partners, or operating assumptions shaping the security environment of {country}.",
        "exercise": f"From a regional-security perspective, this event is relevant because exercises often reveal future interoperability and mission priorities around {country}.",
        "procurement": f"From a regional-security perspective, this event could matter if new equipment or doctrine changes how {country} projects force or responds to threats.",
        "oc": f"From a regional-security perspective, this event speaks to organized-crime pressure that may spill across borders or reshape state deployment patterns around {country}.",
        "conflict": f"From a regional-security perspective, this event matters because local conflict can alter wider threat perceptions and force-posture decisions around {country}.",
    }.get(event_type, f"From a regional-security perspective, this event should be watched for spillover, alignment, or force-posture effects beyond {country}.")
    if interaction_types:
        assessment += f" The leading interaction cue is {readable_label(interaction_types[0])}, which helps explain the wider security significance."
    if any(name in {"United States", "External actors"} or "United States" in name for name in actors):
        assessment += " External involvement makes the event more relevant for regional alignment and security cooperation patterns."
    if salience_level(event) == "high":
        assessment += f" At high salience, the regional question is whether this event begins to alter how neighboring states, external partners, or armed challengers read the security trajectory of {country}."
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
    classification = public_classification(event, role_domains, relationship_types, interaction_types)
    disagreement = len({cmr["risk_level"], political["risk_level"], regional["risk_level"]}) > 1
    reviewed = reviewed_by_human(event)
    significance = synthesis_opening(event, overall, role_domains)
    country_effect = synthesis_country_effect(event, overall, relationship_types, interaction_types)
    interpretive_note = salience_interpretive_note(event)
    monitor_line = synthesis_monitor_line(event, overall, reviewed, disagreement)
    assessment_parts = [significance, country_effect]
    if salience_level(event) == "high":
        assessment_parts.extend([interpretive_note, confidence_context(event), monitor_line])
    elif salience_level(event) == "medium":
        assessment_parts.extend([interpretive_note, monitor_line])
    else:
        assessment_parts.extend([confidence_context(event), monitor_line])
    assessment = " ".join([part for part in assessment_parts if part]).strip()
    return {
        "lens": "synthesis",
        "assessment": assessment,
        "public_takeaways": {
            "significance": significance,
            "country_effect": country_effect,
            "confidence_note": interpretive_note if salience_level(event) != "low" else confidence_context(event),
            "watchpoint": monitor_line,
        },
        "classification": classification,
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
        "generation_method": "heuristic_council_v3",
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
        "generation_method": "heuristic_council_v3",
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
