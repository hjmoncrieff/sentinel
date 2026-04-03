#!/usr/bin/env python3
"""
Generate structured council-of-analysts output for every event.

Outputs:
  data/review/council_analyses.json
"""

from __future__ import annotations

import json
import re
import html
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
EDITED_IN = ROOT / "data" / "review" / "events_with_edits.json"
CANONICAL_IN = ROOT / "data" / "canonical" / "events_actor_coded.json"
ARTICLES_IN = ROOT / "data" / "canonical" / "articles.json"
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
TAXONOMY_FALLBACK_FIELDS = (
    "event_category",
    "event_subcategory",
    "event_construct_destinations",
    "event_analyst_lenses",
)
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


def should_replace_taxonomy_value(field: str, current, canonical) -> bool:
    if current in (None, "", []):
        return True
    if canonical in (None, "", []):
        return False
    if field == "event_subcategory" and current in GENERIC_TAXONOMY_VALUES and current != canonical:
        return True
    if field == "event_analyst_lenses" and canonical and current != canonical:
        return True
    return False


def load_source() -> tuple[Path, dict]:
    source = EDITED_IN if EDITED_IN.exists() else CANONICAL_IN
    payload = json.loads(source.read_text(encoding="utf-8"))
    if source == EDITED_IN and CANONICAL_IN.exists():
        canonical = json.loads(CANONICAL_IN.read_text(encoding="utf-8"))
        canonical_by_event = {
            str(row.get("event_id")): row
            for row in canonical.get("events", [])
            if row.get("event_id")
        }
        merged_by_event = {
            str(row.get("event_id")): row
            for row in payload.get("events", [])
            if row.get("event_id")
        }
        for row in payload.get("events", []):
            canonical_row = canonical_by_event.get(str(row.get("event_id")))
            if not canonical_row:
                continue
            for field in TAXONOMY_FALLBACK_FIELDS:
                value = row.get(field)
                canonical_value = canonical_row.get(field)
                if should_replace_taxonomy_value(field, value, canonical_value):
                    row[field] = canonical_value
        for event_id, canonical_row in canonical_by_event.items():
            if event_id not in merged_by_event:
                payload.setdefault("events", []).append(canonical_row)
    return source, payload


def load_articles() -> dict[str, dict]:
    if not ARTICLES_IN.exists():
        return {}
    payload = json.loads(ARTICLES_IN.read_text(encoding="utf-8"))
    lookup: dict[str, dict] = {}
    for row in payload.get("articles", []):
        if row.get("article_id"):
            lookup[row["article_id"]] = row
    return lookup


def reviewed_by_human(event: dict) -> bool:
    return bool(event.get("human_validated")) or event.get("review_status") in HUMAN_REVIEW_STATUSES


def actor_names(event: dict) -> list[str]:
    names = []
    for actor in event.get("actors", []) or []:
        name = actor.get("actor_canonical_name") or actor.get("actor_name")
        if name:
            names.append(str(name))
    return names


def actor_groups(event: dict) -> list[str]:
    groups = []
    for actor in event.get("actors", []) or []:
        group = actor.get("actor_canonical_group") or actor.get("actor_group")
        if group:
            groups.append(str(group))
    return groups


def actor_types(event: dict) -> list[str]:
    types = []
    for actor in event.get("actors", []) or []:
        actor_type = actor.get("actor_canonical_type") or actor.get("actor_type")
        if actor_type:
            types.append(str(actor_type))
    return types


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


def clean_text(text: str | None) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    raw = html.unescape(raw)
    cleaned = re.sub(r"<[^>]+>", " ", raw)
    cleaned = re.sub(r"<.*$", " ", cleaned)
    cleaned = re.sub(r'href="[^"]*', " ", cleaned)
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    cleaned = re.sub(r"<[^ ]*", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def article_context(event: dict, article_lookup: dict[str, dict]) -> dict:
    reports = ((event.get("provenance") or {}).get("linked_reports") or [])[:3]
    article_rows = []
    for report in reports:
        article = article_lookup.get(report.get("article_id")) or {}
        headline = report.get("headline") or article.get("headline")
        description = report.get("description") or article.get("description")
        article_rows.append({
            "headline": clean_text(headline),
            "description": clean_text(description),
            "source_name": report.get("source_name") or article.get("source_name"),
        })
    descriptive = [row["description"] for row in article_rows if row["description"]]
    headlines = [row["headline"] for row in article_rows if row["headline"]]
    context_line = descriptive[0] if descriptive else clean_text(event.get("summary"))
    if headlines and context_line:
        headline_prefix = headlines[0].strip()
        if context_line.lower().startswith(headline_prefix.lower()):
            context_line = context_line[len(headline_prefix):].strip(" .:-")
    supporting = readable_join(headlines[1:3]) if len(headlines) > 1 else ""
    return {
        "primary_context": context_line,
        "primary_headline": headlines[0] if headlines else clean_text(event.get("headline")),
        "supporting_headlines": supporting,
    }


def lens_plan(event: dict) -> dict[str, dict]:
    event_type = str(event.get("event_type") or "other")
    event_category = str(event.get("event_category") or "").strip().lower()
    analyst_lenses = {str(item).strip().lower() for item in (event.get("event_analyst_lenses") or [])}
    deed = deed_type(event)
    groups = set(actor_groups(event))
    types = set(actor_types(event))
    salience = salience_level(event)

    plan = {
        "cmr": {"active": False, "weight": 0, "reason": ""},
        "political_risk": {"active": False, "weight": 0, "reason": ""},
        "regional_security": {"active": False, "weight": 0, "reason": ""},
        "international": {"active": False, "weight": 0, "reason": ""},
        "economist": {"active": False, "weight": 0, "reason": ""},
    }

    if event_type in {"coup", "purge", "reform", "aid", "coop", "exercise", "procurement"}:
        plan["cmr"] = {"active": True, "weight": 3 if event_type in {"coup", "purge", "reform"} else 2, "reason": "The event directly bears on command politics, mission design, or the political role of state security institutions."}
    elif "military" in groups or "police" in groups or "executive" in groups:
        plan["cmr"] = {"active": True, "weight": 2, "reason": "State coercive actors or executive-security links are central to the event."}

    if event_type in {"coup", "purge", "protest"} or deed in {"precursor", "symptom", "destabilizing", "resistance"}:
        plan["political_risk"] = {"active": True, "weight": 3 if deed in {"symptom", "destabilizing"} or event_type == "coup" else 2, "reason": "The event bears on regime vulnerability through institutional erosion, elite contestation, or coercive political management."}
    elif salience in {"high", "medium"} and event_type in {"reform", "conflict", "oc"}:
        plan["political_risk"] = {"active": True, "weight": 2, "reason": "The event has plausible implications for near-term political stability and executive control."}

    if event_type in {"conflict", "oc"} or "armed_non_state_actor" in groups or "organized_crime" in types or "armed_group" in types:
        plan["regional_security"] = {"active": True, "weight": 3, "reason": "The event bears on fragmentation, territorial control, or the interaction between the state and armed non-state actors."}
    elif event_type == "protest":
        plan["regional_security"] = {"active": True, "weight": 2, "reason": "The event may affect fragmentation if protest escalation changes coercive control or state reach."}
    elif event_type in {"aid", "coop", "exercise"} and ("foreign_government" in types or "international_org" in types):
        plan["regional_security"] = {"active": True, "weight": 1, "reason": "External security actors are present, but fragmentation implications appear secondary."}

    if (
        event_category == "international"
        or "international" in analyst_lenses
        or event_type in {"aid", "coop", "exercise", "procurement"}
        or "foreign_government" in types
        or "international_org" in types
    ):
        plan["international"] = {
            "active": True,
            "weight": 3 if event_category == "international" or event_type in {"aid", "coop"} else 2,
            "reason": "External actors, alignment shifts, or foreign pressure are central enough to require a dedicated international reading.",
        }

    if (
        event_category == "economic"
        or "economist" in analyst_lenses
        or event_type in {"procurement", "oc"}
        or any(token in str(event.get("event_subtype") or "").lower() for token in {"debt", "inflation", "fx", "fiscal", "budget", "price", "economic", "currency"})
    ):
        plan["economist"] = {
            "active": True,
            "weight": 3 if event_category == "economic" else 1 if event_type == "procurement" else 2,
            "reason": "The event has a meaningful macro, fiscal, or illicit-economy mechanism that can change political risk.",
        }

    # Keep single-lens activation for routine institutional events.
    active_count = sum(1 for row in plan.values() if row["active"])
    if active_count == 0:
        plan["political_risk"] = {"active": True, "weight": 1, "reason": "Default light-touch political-risk monitoring applies even when the event is not strongly diagnostic for the other lenses."}
    return plan


def weighted_overall(active_analyses: dict[str, dict], plan: dict[str, dict]) -> str:
    weights = {"low": 1, "medium": 2, "high": 3}
    total = 0
    weight_sum = 0
    for code, analysis in active_analyses.items():
        weight = plan.get(code, {}).get("weight", 0)
        total += weight * weights.get(analysis.get("risk_level"), 1)
        weight_sum += weight
    if not weight_sum:
        return "low"
    avg = total / weight_sum
    if avg >= 2.5:
        return "high"
    if avg >= 1.5:
        return "medium"
    return "low"


def deed_type(event: dict) -> str:
    return str(event.get("deed_type") or "").strip().lower()


def deed_label(event: dict) -> str:
    mapping = {
        "precursor": "erosion precursor",
        "symptom": "institutional erosion symptom",
        "destabilizing": "destabilizing erosion episode",
        "resistance": "institutional resistance signal",
    }
    return mapping.get(deed_type(event), "")


def deed_effect_domain(event: dict) -> str:
    mapping = {
        "precursor": "institutional stress and democratic backsliding",
        "symptom": "institutional erosion and coercive governance",
        "destabilizing": "regime destabilization and institutional rupture",
        "resistance": "institutional resistance and democratic defense",
    }
    return mapping.get(deed_type(event), "")


def deed_interpretive_line(event: dict) -> str:
    country = event.get("country") or "the country"
    mapping = {
        "precursor": f"In DEED terms, this is best read as a precursor: a warning sign that the institutional rules of the game in {country} may be weakening before a fuller rupture is visible.",
        "symptom": f"In DEED terms, this is best read as a symptom: the event suggests that erosion in {country} is no longer only rhetorical and is being expressed through institutions or coercive practice.",
        "destabilizing": f"In DEED terms, this is best read as destabilizing: the episode points to institutional stress in {country} that could accelerate elite rupture, coercive escalation, or constitutional breakdown.",
        "resistance": f"In DEED terms, this is best read as resistance: the event suggests that actors in {country} are still contesting erosion rather than simply accommodating it.",
    }
    return mapping.get(deed_type(event), "")


def event_subcategory(event: dict) -> str:
    return str(event.get("event_subcategory") or "").strip().lower()


def subcategory_line(event: dict, lens: str) -> str:
    country = event.get("country") or "the country"
    subtype = event_subcategory(event)
    lines = {
        "trafficking_logistics_and_route_shift": {
            "political_risk": f"In {country}, the mechanism is not only violence but the relocation of trafficking infrastructure, which can widen the gap between formal authority and the actors who actually move money, goods, and protection.",
            "regional_security": f"In {country}, this looks like a route-and-hub problem: control is being contested through logistics corridors, not only through open clashes.",
            "economist": f"In {country}, the key economic mechanism is the financing power that comes from controlling routes, storage, and brokerage points.",
            "synthesis": f"The mechanism here is logistical entrenchment: armed actors gain leverage when they can route traffic, rents, and protection through durable corridors."
        },
        "criminal_violence_and_social_control": {
            "political_risk": f"In {country}, this is about whether spectacular violence is beginning to shape public authority and political behavior, not just criminal fear.",
            "regional_security": f"In {country}, the issue is localized social control: violence is being used to govern communities and signal who rules on the ground.",
            "economist": f"In {country}, coercion matters economically because violent domination protects extortion, protection rents, and illicit market access.",
            "synthesis": f"The mechanism here is coercive social control: violence is doing political work by reshaping fear, compliance, and local authority."
        },
        "criminal_interdiction_and_state_response": {
            "regional_security": f"In {country}, this is less about who attacked whom than about whether state interdiction is actually disrupting criminal reach or merely forcing it to adapt.",
            "economist": f"In {country}, interdiction matters economically because it can change transport costs, risk premia, and the profitability of illicit routes.",
            "synthesis": f"The mechanism here is adaptive pressure: state action may disrupt criminal operations, but it can also displace them geographically or organizationally."
        },
        "peace_process_electoral_stress": {
            "political_risk": f"In {country}, elections matter here because they can reopen bargains over who will honor, dilute, or reverse the peace track.",
            "international": f"In {country}, outside actors matter because electoral uncertainty changes how guarantors, donors, and diplomatic partners assess the peace process.",
            "synthesis": f"The mechanism here is political uncertainty around implementation: the negotiation track is being filtered through electoral competition."
        },
        "transitional_justice_and_accountability": {
            "political_risk": f"In {country}, accountability is politically consequential because it can redistribute blame, weaken old protection networks, and provoke backlash from affected institutions.",
            "synthesis": f"The mechanism here is institutional accountability: judicial action is testing whether past coercive power can still be shielded from scrutiny."
        },
        "peace_process_breakdown_and_spoilers": {
            "political_risk": f"In {country}, this is not just a failed dialogue moment; it increases the chance that armed and political actors will revert to harder bargaining through force.",
            "regional_security": f"In {country}, spoilers matter because breakdown can quickly move local security orders back toward fragmentation and retaliation.",
            "synthesis": f"The mechanism here is spoiler escalation: failed talks or attacks narrow the room for settlement and widen the room for coercive competition."
        },
        "operational_security_cooperation": {
            "military": f"In {country}, the important issue is whether operational cooperation changes who sets mission priorities and how domestic force is actually used.",
            "regional_security": f"In {country}, joint operations matter if they redirect where the state concentrates force and which territories become priority zones.",
            "international": f"In {country}, this is operational alignment, not just symbolism: outside partners are shaping how security action is organized in practice.",
            "synthesis": f"The mechanism here is operational alignment: foreign-backed cooperation is changing practice on the ground, not only diplomatic posture."
        },
        "foreign_training_and_force_assistance": {
            "military": f"In {country}, training assistance matters because it can build new professional habits, dependencies, and channels of outside influence inside the force.",
            "international": f"In {country}, this is a partnership signal as much as a training event: it says something about who is being trusted to shape the security sector.",
            "synthesis": f"The mechanism here is capability shaping through partnership: training relationships can alter doctrine, preferences, and external dependence over time."
        },
        "regional_security_alignment_and_strategy": {
            "international": f"In {country}, the event is strategically important because it points to a broader coalition or doctrine rather than a one-off cooperative step.",
            "synthesis": f"The mechanism here is strategic alignment: the event tells us more about regional security direction than about a single operational decision."
        },
        "executive_removal_and_irregular_transfer": {
            "cmr": f"In {country}, the key question is who controlled the handoff from leader removal to interim authority, and whether the chain of command stayed intact or was repurposed politically.",
            "political_risk": f"In {country}, this is a direct test of whether executive succession is still governed by rules or by whoever can impose control fastest.",
            "international": f"In {country}, outside recognition and pressure matter because they can quickly shape whether the irregular transfer hardens or unravels.",
            "synthesis": f"The mechanism here is irregular succession under coercive pressure: leader removal and interim authority are being settled through force and recognition, not only procedure."
        },
        "historical_coup_memory_and_legacy": {
            "cmr": f"In {country}, the event matters less as a live rupture than as a reminder of how the armed forces have been remembered, justified, or politically narrated over time.",
            "synthesis": f"The mechanism here is memory politics: the event shapes how past coercive rupture is interpreted in the present."
        },
        "elite_security_reshuffle": {
            "cmr": f"In {country}, this looks like selective control over senior posts rather than a neutral personnel change, which makes it relevant to loyalty management.",
            "political_risk": f"In {country}, reshuffles matter because they can reveal insecurity at the top and attempts to lock in more dependable coercive allies.",
            "synthesis": f"The mechanism here is elite security management: personnel changes are being used to reshape trust and control inside the coercive apparatus."
        },
        "foreign_training_and_force_assistance": {},
        "security_force_labor_and_institutional_contention": {
            "political_risk": f"In {country}, the issue is not street protest alone but contention inside the security apparatus itself, which can expose friction between the executive and coercive institutions.",
            "regional_security": f"In {country}, internal labor or status disputes matter if they weaken day-to-day control capacity or fracture operational discipline.",
            "synthesis": f"The mechanism here is institutional contention inside the coercive apparatus: pressure is coming from actors the state also depends on to enforce order."
        },
        "protest_repression_and_security_response": {
            "political_risk": f"In {country}, repression shifts the event from ordinary protest into a test of how far the state will go to manage dissent coercively.",
            "regional_security": f"In {country}, the important question is whether security deployment remains crowd control or starts to change local coercive authority more broadly.",
            "synthesis": f"The mechanism here is coercive protest management: the state's response, not just the protest itself, is changing the event's political meaning."
        },
        "institutional_professionalization_and_inclusion": {
            "cmr": f"In {country}, this points to who is allowed to rise inside the force and what kind of institutional identity the leadership wants to project.",
            "synthesis": f"The mechanism here is institutional shaping through promotion and symbolism: leadership is signaling what kind of force it wants to build."
        },
        "domestic_security_militarization": {
            "cmr": f"In {country}, the core issue is mission transfer: domestic security functions are being moved more firmly under military command.",
            "political_risk": f"In {country}, this matters politically because military management of internal order can outlast the immediate reform and reshape executive tools of control.",
            "synthesis": f"The mechanism here is mission expansion into domestic order: military institutions are gaining a more direct role in internal governance."
        },
        "multinational_force_posture_and_interoperability": {
            "military": f"In {country}, the exercise matters because interoperability can build habits, expectations, and readiness ties that persist beyond the drill itself.",
            "international": f"In {country}, multinational exercise design is also a signal of who the country expects to align with in future security scenarios.",
            "synthesis": f"The mechanism here is force-posture signaling through interoperability: training is shaping both readiness and external alignment."
        },
        "state_offensive_and_counterinsurgent_action": {
            "political_risk": f"In {country}, offensive action matters politically because failure, collateral damage, or overreach can feed executive vulnerability instead of restoring control.",
            "regional_security": f"In {country}, this is about whether state force is consolidating territorial control or exposing how hard that control is to sustain.",
            "synthesis": f"The mechanism here is offensive coercion under stress: the state is trying to restore control through force, but the operation itself can reveal its limits."
        },
        "armed_violence_and_localized_breakdown": {
            "regional_security": f"In {country}, the event points to localized breakdown where armed actors can punish, displace, or govern communities more effectively than the state.",
            "synthesis": f"The mechanism here is localized breakdown of order: armed violence is revealing where state protection is absent, weak, or contested."
        },
        "conflict_aftershock_and_regime_spillover": {
            "political_risk": f"In {country}, the event matters because conflict dynamics are spilling into regime politics, succession, or elite legitimacy rather than staying confined to the battlefield.",
            "synthesis": f"The mechanism here is spillover from conflict into regime politics: coercive confrontation is no longer separable from the political order itself."
        },
    }
    return lines.get(subtype, {}).get(lens, "")


def public_classification(event: dict, role_domains: list[str], relationship_types: list[str], interaction_types: list[str]) -> dict:
    event_type = str(event.get("event_type") or "other")
    deed = deed_type(event)
    frame = deed_label(event) or classify_event_frame(event, role_domains, interaction_types)
    if deed:
        effect = deed_effect_domain(event) or "institutional erosion and coercive governance"
    elif event_type in {"coup", "purge", "protest"}:
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
        "deed_type": deed or None,
        "relationship_cues": [readable_label(item) for item in relationship_types[:2]],
        "interaction_cues": [readable_label(item) for item in interaction_types[:2]],
    }


def synthesis_opening(event: dict, overall: str, role_domains: list[str]) -> str:
    country = event.get("country") or "this country"
    event_type = str(event.get("event_type") or "other")
    deed = deed_type(event)
    subtype = str(event.get("event_subtype") or "").strip()
    domain_text = readable_join([domain.replace("_", " ") for domain in role_domains[:2]])
    salience = salience_level(event)
    if deed == "symptom":
        return f"In {country}, this event matters because it points to institutional erosion that is already being expressed through state practice, coercive behavior, or the weakening of normal accountability channels."
    if deed == "precursor":
        return f"In {country}, this event matters because it may be an early warning sign that institutional safeguards are weakening even before a clearer rupture appears."
    if deed == "destabilizing":
        return f"In {country}, this event matters because it suggests that institutional stress is moving into a more destabilizing phase with clearer implications for regime vulnerability."
    if deed == "resistance":
        return f"In {country}, this event matters because it suggests that institutional resistance to erosion is still active and politically consequential."
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
    deed = deed_type(event)
    rels = {readable_label(item) for item in relationship_types}
    ints = {readable_label(item) for item in interaction_types}
    salience = salience_level(event)

    if deed == "symptom":
        if salience == "low":
            return f"The practical effect may be to normalize a little more coercive or weakly accountable governance in {country}."
        return f"The broader effect could be to normalize a more coercive and weakly accountable style of governance in {country}, making later institutional correction harder."
    if deed == "precursor":
        if salience == "low":
            return f"The practical effect is to raise concern that the institutional direction of {country} may be worsening."
        return f"The broader effect is to raise concern that institutional deterioration in {country} may be deepening before a more visible rupture occurs."
    if deed == "destabilizing":
        if salience == "low":
            return f"The practical effect is to increase doubt about whether political order in {country} will remain contained within ordinary institutional channels."
        return f"The broader effect is to increase doubt about whether political order in {country} can remain contained within ordinary institutional channels."
    if deed == "resistance":
        if salience == "low":
            return f"The practical effect is to show that institutional pushback remains possible in {country}."
        return f"The broader effect is to show that institutional pushback remains possible in {country}, even if the balance still favors erosion."

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
    deed = deed_type(event)
    if deed == "symptom":
        return "The key question is whether later reporting shows this symptom being absorbed into normal governance practice or provoking institutional pushback."
    if deed == "precursor":
        return "The key question is whether later reporting confirms this as an early warning sign of broader erosion rather than a contained episode."
    if deed == "destabilizing":
        return "The key question is whether this becomes part of a wider sequence of destabilizing moves, emergency measures, or elite-security rupture."
    if deed == "resistance":
        return "The key question is whether institutional resistance can impose real limits or whether the erosion pattern resumes."
    if not reviewed and salience_level(event) == "medium":
        return "This interpretation should be treated as provisional until more reporting clarifies whether the event is isolated or part of a developing pattern."
    if not reviewed and salience_level(event) == "low":
        return "For now, the main question is simply whether later reporting confirms this as part of a larger pattern."
    return salience_watchpoint(event, disagreement)


def synthesis_pattern_fit(event: dict, overall: str) -> str:
    country = event.get("country") or "the country"
    event_type = str(event.get("event_type") or "other")
    deed = deed_type(event)
    salience = salience_level(event)
    if deed == "symptom":
        return f"This looks less like isolated noise and more like another data point in a broader pattern of institutional erosion in {country}."
    if deed == "precursor":
        return f"This is best treated as an early warning sign rather than proof of a full institutional break in {country}."
    if deed == "destabilizing":
        return f"This reads as a sharper escalation marker, suggesting that stress in {country} may be moving beyond background deterioration."
    if deed == "resistance":
        return f"This sits somewhat against the erosion trend by showing that institutional resistance remains visible in {country}."
    if event_type in {"coup", "purge"}:
        return f"This fits a pattern in which control over coercive institutions is becoming more politically consequential in {country}."
    if event_type in {"conflict", "oc"}:
        return f"This fits a broader pattern of coercive strain and contested authority rather than a purely local disturbance in {country}."
    if event_type in {"reform", "coop", "aid", "exercise", "procurement"}:
        return f"This is best read as part of a longer-moving institutional trajectory rather than as a one-off administrative development in {country}."
    if salience == "low":
        return f"For now, this is a weak pattern signal in {country}, but it is still useful because repeated low-level signals often precede clearer institutional shifts."
    return f"This is best understood as a reinforcing signal about the current direction of security and institutional politics in {country}."


def synthesis_mechanism(event: dict, relationship_types: list[str], interaction_types: list[str]) -> str:
    country = event.get("country") or "the country"
    deed = deed_type(event)
    rels = {readable_label(item) for item in relationship_types}
    ints = {readable_label(item) for item in interaction_types}
    if deed == "symptom":
        return f"The mechanism here is gradual normalization: practices that weaken accountability in {country} risk becoming embedded in routine governance."
    if deed == "precursor":
        return f"The mechanism here is anticipatory drift: political or security actors in {country} appear to be testing or widening room for institutional weakening."
    if deed == "destabilizing":
        return f"The mechanism here is acceleration under stress: institutional conflict in {country} is feeding a more destabilizing cycle rather than remaining contained."
    if deed == "resistance":
        return f"The mechanism here is institutional contestation: the event suggests that erosion in {country} is meeting organized pushback rather than simple acquiescence."
    if "tutelary veto" in rels or "praetorian" in rels:
        return f"The mechanism here is political empowerment of coercive actors, which can make security institutions in {country} more decisive in questions that should remain civilian."
    if "joint operation" in ints:
        return f"The mechanism here is institutional reinforcement through cooperation, doctrine, or mission expansion, which can reshape how security authority is exercised in {country}."
    if "confrontation" in ints:
        return f"The mechanism here is coercive management of stress, where security responses in {country} begin to substitute for more ordinary political or institutional resolution."
    return f"The mechanism here is cumulative institutional pressure: the episode adds to existing strain on how authority, accountability, and coercive power are organized in {country}."


def synthesis_institutional_implication(event: dict) -> str:
    country = event.get("country") or "the country"
    event_type = str(event.get("event_type") or "other")
    deed = deed_type(event)
    if deed == "symptom":
        return f"The main institutional implication is that oversight and accountability in {country} may be weakening in practice, not just in rhetoric."
    if deed == "precursor":
        return f"The institutional implication is that safeguards in {country} may be under pressure even if formal rules have not yet clearly broken."
    if deed == "destabilizing":
        return f"The institutional implication is that ordinary channels of conflict management in {country} may be giving way to more coercive or exceptional forms of rule."
    if deed == "resistance":
        return f"The institutional implication is that checks inside {country} still matter and may shape how far erosion can proceed."
    if event_type in {"purge", "coup"}:
        return f"The institutional implication is greater uncertainty over command cohesion, political loyalty, and the boundaries of civilian control in {country}."
    if event_type in {"protest", "conflict", "oc"}:
        return f"The institutional implication is greater pressure on the boundary between public-order management and coercive overreach in {country}."
    if event_type in {"reform", "coop", "aid", "exercise", "procurement"}:
        return f"The institutional implication is a likely shift in doctrine, mission priority, or external alignment within the security sector of {country}."
    return f"The institutional implication is a subtle change in how authority and security governance are being organized in {country}."


def synthesis_forward_risk(event: dict, overall: str) -> str:
    country = event.get("country") or "the country"
    deed = deed_type(event)
    salience = salience_level(event)
    if deed == "symptom":
        return f"If this pattern continues, the main risk is that coercive or weakly accountable practices in {country} become normalized and therefore harder to reverse."
    if deed == "precursor":
        return f"If this pattern continues, the main risk is that early warning signs in {country} turn into clearer institutional erosion or executive-security overreach."
    if deed == "destabilizing":
        return f"If this pattern continues, the main risk is a faster move in {country} toward institutional rupture, emergency governance, or elite-security confrontation."
    if deed == "resistance":
        return f"If this pattern continues, the main question is whether resistance in {country} can slow erosion or merely raise the political cost of it."
    if overall == "high":
        return f"If similar events accumulate, the main risk is that the current stress in {country} begins to reshape the broader political order rather than remaining sector-specific."
    if salience == "low":
        return f"If similar signals recur, the main risk is not immediate rupture but a gradual hardening of institutional direction in {country}."
    return f"If this pattern continues, the main risk is a deeper entrenchment of current security and political dynamics in {country}."


def ensure_sentence(text: str) -> str:
    cleaned = clean_text(text)
    if not cleaned:
        return ""
    if cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned


def sentence_case(text: str) -> str:
    cleaned = clean_text(text)
    if not cleaned:
        return ""
    return cleaned[0].upper() + cleaned[1:]


def trim_to_sentence(text: str, limit: int = 220) -> str:
    cleaned = ensure_sentence(text)
    if len(cleaned) <= limit:
        return cleaned
    clipped = cleaned[:limit].rsplit(" ", 1)[0].rstrip(" ,;:")
    if clipped[-1] not in ".!?":
        clipped += "."
    return clipped


def simplify_public_line(text: str, country: str) -> str:
    cleaned = ensure_sentence(text)
    if not cleaned:
        return ""
    patterns = [
        (rf"^In {re.escape(country)}, this event matters because\s*", ""),
        (rf"^In {re.escape(country)}, this event matters\s*", ""),
        (rf"^In {re.escape(country)},\s*", ""),
        (r"^The event reporting suggests\s*", ""),
        (r"^The event itself appears to center on\s*", ""),
        (r"^The broader effect is to\s*", ""),
        (r"^The broader effect could be to\s*", ""),
        (r"^The practical effect is to\s*", ""),
        (r"^The practical effect may be to\s*", ""),
        (r"^The institutional implication is that\s*", ""),
        (r"^The main institutional implication is that\s*", ""),
        (r"^The mechanism here is\s*", ""),
        (r"^The key question is whether\s*", "The question now is whether "),
        (r"^If this pattern continues, the main risk is\s*", "If this continues, the risk is "),
        (r"^If similar events accumulate, the main risk is\s*", "If similar events accumulate, the risk is "),
        (r"^If similar signals recur, the main risk is\s*", "If similar signals recur, the risk is "),
    ]
    for pattern, replacement in patterns:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    replacements = {
        "institutional erosion": "institutional weakening",
        "coercive governance": "rule through coercion",
        "coercive management": "a coercive response",
        "executive-security overreach": "executive overreach backed by security forces",
        "coercive apparatus": "security apparatus",
        "territorial control": "control on the ground",
        "regime vulnerability": "political vulnerability",
        "civilian control": "civilian control",
        "security-sector": "security",
        "institutional safeguards": "political safeguards",
        "coercive actors": "security actors",
    }
    for src, dst in replacements.items():
        cleaned = re.sub(src, dst, cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return sentence_case(cleaned)


def public_opening(event: dict, context: dict) -> str:
    country = event.get("country") or "the country"
    summary = clean_text(event.get("summary"))
    if summary and not looks_like_feed_blurb(summary):
        return trim_to_sentence(summary, 180)
    primary = clean_text(context.get("primary_context"))
    if primary and not looks_like_feed_blurb(primary):
        return trim_to_sentence(primary, 180)
    headline = clean_text(context.get("primary_headline"))
    if headline and not looks_like_feed_blurb(headline):
        return trim_to_sentence(headline, 140)
    return ensure_sentence(f"Recent reporting points to a politically relevant security development in {country}.")


def public_lens_priority(plan: dict[str, dict]) -> list[str]:
    order = sorted(
        [(code, row.get("weight", 0)) for code, row in plan.items() if row.get("active")],
        key=lambda item: (-item[1], item[0]),
    )
    mapping = {
        "cmr": "military",
        "political_risk": "political",
        "regional_security": "security",
        "international": "international",
        "economist": "economic",
    }
    return [mapping.get(code, code) for code, _ in order]


def looks_like_feed_blurb(text: str) -> bool:
    lowered = str(text or "").strip().lower()
    if not lowered:
        return False
    bad_starts = {
        "on the radar:",
        "watch:",
        "newsletter:",
        "weekly:",
        "analysis:",
        "news roundup",
        "roundup:",
    }
    if any(lowered.startswith(prefix) for prefix in bad_starts):
        return True
    if "news roundup" in lowered[:40]:
        return True
    if lowered.count(";") >= 2:
        return True
    if lowered.count(",") >= 4 and len(lowered.split()) < 40:
        return True
    return False


def simple_causal_line(text: str, country: str) -> str:
    cleaned = simplify_public_line(text, country)
    cleaned = re.sub(r"^in\s+" + re.escape(country) + r",?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    cleaned = re.sub(r"^the broader implication for .*? is ", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^the broader effect could be to ", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^this fits a broader pattern of ", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^the mechanism here is ", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^if similar events accumulate, the main risk is that ", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"^A coercive response of stress, where security responses in .*? begin to substitute for more ordinary political or institutional resolution\.?$",
        "Security responses are beginning to substitute for more ordinary political or institutional resolution.",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(rf"\b{re.escape(country.lower())}\b", country, cleaned, flags=re.IGNORECASE)
    return ensure_sentence(cleaned)


def public_watch_line(text: str, country: str) -> str:
    cleaned = simplify_public_line(text, country)
    cleaned = re.sub(r"^the key question is whether ", "Watch whether ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^the main question is whether ", "Watch whether ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^the key next indicator is whether ", "Watch whether ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^for now, the main question is simply whether ", "Watch whether ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^this interpretation should be treated as provisional until ", "Watch for confirmation as ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(rf"\b{re.escape(country.lower())}\b", country, cleaned, flags=re.IGNORECASE)
    return ensure_sentence(cleaned)


def render_public_analysis(event: dict, analyses: dict[str, dict], combined: dict, context: dict, plan: dict[str, dict]) -> str:
    country = event.get("country") or "the country"
    takeaways = combined.get("public_takeaways") or {}
    opening = public_opening(event, context)
    significance = simple_causal_line(takeaways.get("significance", ""), country)
    country_effect = simple_causal_line(takeaways.get("country_effect", ""), country)
    mechanism = simple_causal_line(takeaways.get("mechanism", ""), country)
    pattern_fit = simple_causal_line(takeaways.get("pattern_fit", ""), country)
    forward = simple_causal_line(takeaways.get("forward_risk", ""), country)
    watch = public_watch_line(takeaways.get("watchpoint", ""), country)
    active = public_lens_priority(plan)
    sentences = [opening]
    for candidate in (significance, mechanism, country_effect, pattern_fit):
        if candidate and candidate.lower() not in " ".join(sentences).lower():
            sentences.append(candidate)
            break
    for candidate in (forward, watch):
        if candidate and candidate.lower() not in " ".join(sentences).lower():
            sentences.append(candidate)
            break
    if len(sentences) == 1 and active:
        sentences.append(
            ensure_sentence(
                f"The clearest implication is for {country}'s {active[0]} risk."
            )
        )
    if salience_level(event) == "low":
        return " ".join(sentences[:2]).strip()
    if len(sentences) >= 3:
        return f"{' '.join(sentences[:2]).strip()}\n\n{sentences[2].strip()}".strip()
    return " ".join(sentences).strip()


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
                "deed_type": event.get("deed_type"),
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


def cmr_analysis(event: dict, knowledge: dict, guidance: dict, context: dict, plan: dict) -> dict:
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
        "coup": f"In {country}, the event points to direct stress on the chain of command and on whether civilian authority still sets the boundary of military action.",
        "purge": f"In {country}, the event suggests that command appointments or dismissals are being used to manage loyalty, discipline, or political dependence inside the security hierarchy.",
        "protest": f"In {country}, the event matters for civil-military analysis because public contention is being filtered through the behavior of police or military institutions.",
        "reform": f"In {country}, the event matters because it can change who defines the remit, oversight, or autonomy of security institutions.",
        "coop": f"In {country}, the event matters because external cooperation can reinforce specific missions, doctrines, or chains of influence inside the security sector.",
    }.get(event_type, f"In {country}, the event matters for civil-military analysis because it affects how coercive institutions are positioned inside the political order{subtype_clause}.")
    if context.get("primary_context"):
        assessment += f" The reporting suggests {context['primary_context']}."
    mechanism_line = subcategory_line(event, "cmr")
    if mechanism_line:
        assessment += f" {mechanism_line}"
    if relationship_types:
        assessment += f" The main mechanism here is {readable_label(relationship_types[0])}, which helps explain how security actors relate to civilian authority."
    if role_domains:
        assessment += f" The institutional arena in play is {readable_join([item.replace('_', ' ') for item in role_domains[:2]])}."
    if salience_level(event) == "high":
        assessment += f" At high salience, the central question is whether this episode changes who commands, constrains, or politically relies on the security apparatus in {country}."
    if context.get("supporting_headlines"):
        assessment += f" Related coverage also points to {context['supporting_headlines']}."
    return {
        "lens": "cmr",
        "assessment": assessment,
        "risk_level": risk_level(event, {"coup", "purge"}, {"protest", "reform", "coop"}),
        "signals": signals,
        "confidence": 0.62 if event.get("salience") == "high" else 0.54,
        "analyst_weight": plan.get("cmr", {}).get("weight", 0),
        "activation_reason": plan.get("cmr", {}).get("reason"),
        "ai_generated": True,
        "knowledge_trace": {
            "role_domains": role_domains,
            "relationship_types": relationship_types,
            "guidance_priorities": role_info.get("priorities", [])[:3],
        },
    }


def political_risk_analysis(event: dict, knowledge: dict, guidance: dict, context: dict, plan: dict) -> dict:
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
        "coup": f"In {country}, this event raises the possibility that core disputes over power are moving outside ordinary institutional channels.",
        "purge": f"In {country}, this event may signal elite distrust, anticipatory consolidation, or a bid to tighten executive control over the security chain.",
        "protest": f"In {country}, this event matters because unrest may be pushing the regime toward a more coercive way of managing political pressure.",
        "conflict": f"In {country}, this event matters because deeper territorial or coercive stress can spill into regime vulnerability when the state looks less able to impose order.",
        "oc": f"In {country}, this event matters because competition between the state and criminal actors can weaken public authority and expose state vulnerability.",
    }.get(event_type, f"In {country}, this event is a short-run signal about regime vulnerability, institutional confidence, and the political management of coercive stress.")
    if context.get("primary_context"):
        assessment += f" The event reporting suggests {context['primary_context']}."
    mechanism_line = subcategory_line(event, "political_risk")
    if mechanism_line:
        assessment += f" {mechanism_line}"
    if relationship_types:
        assessment += f" The strongest structural cue is {readable_label(relationship_types[0])}, which suggests the event is politically structured rather than merely administrative."
    if event.get("salience") == "high":
        assessment += " Because the event is already high-salience, follow-on reactions from political elites or security actors would matter quickly."
    else:
        assessment += " The key issue is whether it remains isolated or becomes part of a broader accumulation of regime stress."
    if salience_level(event) == "high":
        assessment += f" In that sense, this is a higher-value signal about whether authority in {country} is becoming more contested, brittle, or dependent on coercive management."
    return {
        "lens": "political_risk",
        "assessment": assessment,
        "risk_level": risk_level(event, {"coup", "conflict", "oc"}, {"purge", "protest", "procurement"}),
        "signals": signals,
        "confidence": 0.64 if event.get("salience") == "high" else 0.55,
        "analyst_weight": plan.get("political_risk", {}).get("weight", 0),
        "activation_reason": plan.get("political_risk", {}).get("reason"),
        "ai_generated": True,
        "knowledge_trace": {
            "relationship_types": relationship_types,
            "guidance_priorities": role_info.get("priorities", [])[:3],
        },
    }


def regional_security_analysis(event: dict, knowledge: dict, guidance: dict, context: dict, plan: dict) -> dict:
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
        "coop": f"In {country}, this event matters for fragmentation because outside security coordination can change how the state distributes coercive capacity across the territory.",
        "aid": f"In {country}, this event matters for fragmentation because external support can strengthen some security actors faster than the state’s overall capacity to govern violence.",
        "exercise": f"In {country}, this event matters for fragmentation only if training or deployment changes how force is projected across contested territory.",
        "procurement": f"In {country}, this event matters if new equipment or doctrine changes who can impose force, patrol, or hold territory.",
        "oc": f"In {country}, this event matters because organized-crime pressure bears directly on fragmentation: it can widen the gap between formal state authority and real control on the ground.",
        "conflict": f"In {country}, this event matters because armed confrontation can reveal whether coercive control is fragmenting across local authorities, armed challengers, and criminal actors.",
        "protest": f"In {country}, this event matters for fragmentation only if protest escalation changes who controls streets, neighborhoods, or coercive response in practice.",
    }.get(event_type, f"In {country}, this event should be watched for what it says about fragmentation, territorial control, and the distribution of coercive authority.")
    if context.get("primary_context"):
        assessment += f" The reporting suggests {context['primary_context']}."
    mechanism_line = subcategory_line(event, "regional_security")
    if mechanism_line:
        assessment += f" {mechanism_line}"
    if interaction_types:
        assessment += f" The leading interaction cue is {readable_label(interaction_types[0])}, which helps explain how fragmentation pressure is being produced."
    if any(name in {"United States", "External actors"} or "United States" in name for name in actors):
        assessment += " External involvement matters here mainly if it changes state capacity, territorial deployment, or the incentives of armed challengers."
    if salience_level(event) == "high":
        assessment += f" At high salience, the key question is whether this event marks a broader shift in who actually controls violence, territory, or coercive leverage in {country}."
    return {
        "lens": "regional_security",
        "assessment": assessment,
        "risk_level": risk_level(event, {"conflict", "oc"}, {"coop", "aid", "exercise", "procurement"}),
        "signals": signals,
        "confidence": 0.61 if event.get("salience") == "high" else 0.53,
        "analyst_weight": plan.get("regional_security", {}).get("weight", 0),
        "activation_reason": plan.get("regional_security", {}).get("reason"),
        "ai_generated": True,
        "knowledge_trace": {
            "interaction_types": interaction_types,
            "guidance_priorities": role_info.get("priorities", [])[:3],
        },
    }


def international_analysis(event: dict, guidance: dict, context: dict, plan: dict) -> dict:
    event_type = event.get("event_type") or "other"
    country = event.get("country") or "the country"
    actors = actor_names(event)
    role_info = role_guidance(guidance, "international")
    signals = []
    if event_type in {"aid", "coop", "exercise", "procurement"}:
        signals.append("external_security_alignment")
    if any("United States" in actor or actor in {"IMF", "World Bank", "Organization of American States", "United Nations", "European Union"} for actor in actors):
        signals.append("major_external_actor_present")
    if any(token in str(event.get("event_subtype") or "").lower() for token in {"sanction", "treaty", "summit", "imf", "debt", "aid"}):
        signals.append("external_pressure_channel")
    if not signals:
        signals.append("external_context_watch")
    signals = list(dict.fromkeys(signals))
    assessment = {
        "aid": f"In {country}, this event matters internationally because external support can reshape leverage, alignment, and the balance between domestic and foreign-backed coercive capacity.",
        "coop": f"In {country}, this event matters internationally because it can alter the country's security alignment and the amount of outside influence over domestic security choices.",
        "exercise": f"In {country}, this event matters internationally if the exercise signals a broader shift in alliance posture, external reassurance, or regional signaling.",
        "procurement": f"In {country}, this event matters internationally when acquisition choices reveal dependence, alignment, or sanctions-evasion behavior.",
    }.get(event_type, f"In {country}, this event matters internationally if it changes foreign leverage, diplomatic pressure, or the country's room to maneuver externally.")
    if context.get("primary_context"):
        assessment += f" The reporting suggests {context['primary_context']}."
    mechanism_line = subcategory_line(event, "international")
    if mechanism_line:
        assessment += f" {mechanism_line}"
    if any("United States" in actor for actor in actors):
        assessment += " U.S. involvement makes the external signaling content more consequential for short-run political risk."
    elif any(actor in {"IMF", "World Bank", "Organization of American States", "United Nations", "European Union"} for actor in actors):
        assessment += " Multilateral involvement matters because it can raise or constrain political options beyond the event itself."
    return {
        "lens": "international",
        "assessment": assessment,
        "risk_level": risk_level(event, {"aid", "coop", "procurement"}, {"exercise", "peace"}),
        "signals": signals,
        "confidence": 0.58 if event.get("salience") == "high" else 0.5,
        "analyst_weight": plan.get("international", {}).get("weight", 0),
        "activation_reason": plan.get("international", {}).get("reason"),
        "ai_generated": True,
        "knowledge_trace": {
            "guidance_priorities": role_info.get("priorities", [])[:3],
            "visible_external_actors": actors[:4],
        },
    }


def economist_analysis(event: dict, guidance: dict, context: dict, plan: dict) -> dict:
    event_type = event.get("event_type") or "other"
    country = event.get("country") or "the country"
    subtype = str(event.get("event_subtype") or "").strip().lower()
    role_info = role_guidance(guidance, "economist")
    signals = []
    if event_type == "oc":
        signals.append("illicit_economy_pressure")
    if event_type == "procurement":
        signals.append("fiscal_or_resource_commitment")
    if any(token in subtype for token in {"debt", "inflation", "fx", "fiscal", "budget", "currency", "subsidy", "price"}):
        signals.append("macro_policy_stress")
    if any(token in clean_text(context.get("primary_context")).lower() for token in {"inflation", "currency", "debt", "budget", "fiscal", "price", "economic", "fuel"}):
        signals.append("economic_mechanism_visible")
    if not signals:
        signals.append("economic_background_watch")
    signals = list(dict.fromkeys(signals))
    assessment = {
        "oc": f"In {country}, this event matters economically because illicit rents, extortion, and criminal penetration can change how resources and coercion are financed.",
        "procurement": f"In {country}, this event matters economically because procurement choices can signal fiscal priorities, external dependency, or the willingness to absorb costly security commitments.",
    }.get(event_type, f"In {country}, this event matters economically if it changes macro stress, distributional pressure, or the state's fiscal room to manage political risk.")
    if context.get("primary_context"):
        assessment += f" The reporting suggests {context['primary_context']}."
    mechanism_line = subcategory_line(event, "economist")
    if mechanism_line:
        assessment += f" {mechanism_line}"
    if "macro_policy_stress" in signals:
        assessment += " The relevant question is whether the event turns existing economic strain into a more immediate political constraint."
    elif "illicit_economy_pressure" in signals:
        assessment += " The political meaning comes less from headline macro indicators than from how illicit revenues distort incentives and weaken public authority."
    return {
        "lens": "economist",
        "assessment": assessment,
        "risk_level": risk_level(event, {"oc", "procurement"}, {"peace", "exercise"}),
        "signals": signals,
        "confidence": 0.56 if event.get("salience") == "high" else 0.49,
        "analyst_weight": plan.get("economist", {}).get("weight", 0),
        "activation_reason": plan.get("economist", {}).get("reason"),
        "ai_generated": True,
        "knowledge_trace": {
            "guidance_priorities": role_info.get("priorities", [])[:3],
            "subtype": event.get("event_subtype"),
        },
    }


def synthesis(event: dict, analyses: dict[str, dict], guidance: dict, knowledge: dict, plan: dict, context: dict) -> dict:
    overall = weighted_overall(analyses, plan)
    all_signals = []
    for row in analyses.values():
        all_signals.extend(row.get("signals", []))
    unique_signals = sorted(set(all_signals))
    role_info = role_guidance(guidance, "synthesis")
    role_domains = infer_role_domains(event, knowledge)
    relationship_types = infer_relationship_types(event, knowledge)
    interaction_types = infer_interaction_types(event, knowledge)
    classification = public_classification(event, role_domains, relationship_types, interaction_types)
    disagreement = len({row.get("risk_level") for row in analyses.values() if row.get("risk_level")}) > 1
    reviewed = reviewed_by_human(event)
    significance = synthesis_opening(event, overall, role_domains)
    country_effect = synthesis_country_effect(event, overall, relationship_types, interaction_types)
    pattern_fit = synthesis_pattern_fit(event, overall)
    mechanism = synthesis_mechanism(event, relationship_types, interaction_types)
    institutional_implication = synthesis_institutional_implication(event)
    forward_risk = synthesis_forward_risk(event, overall)
    interpretive_note = salience_interpretive_note(event)
    monitor_line = synthesis_monitor_line(event, overall, reviewed, disagreement)
    salience = salience_level(event)
    if salience == "low":
        pattern_fit = ""
        mechanism = ""
        institutional_implication = ""
        forward_risk = ""
    elif salience == "medium":
        institutional_implication = ""
    assessment_parts = [significance, country_effect]
    if context.get("primary_context") and context.get("primary_context") not in " ".join(assessment_parts):
        assessment_parts.append(f"The event itself appears to center on {context['primary_context']}.")
    subcategory_mechanism = subcategory_line(event, "synthesis")
    if subcategory_mechanism:
        assessment_parts.append(subcategory_mechanism)
    if salience == "high":
        assessment_parts.extend([pattern_fit, mechanism, institutional_implication, forward_risk, interpretive_note, confidence_context(event), monitor_line])
    elif salience == "medium":
        assessment_parts.extend([pattern_fit, mechanism, forward_risk, interpretive_note, monitor_line])
    else:
        assessment_parts.extend([pattern_fit, confidence_context(event), monitor_line])
    assessment = " ".join([part for part in assessment_parts if part]).strip()
    return {
        "lens": "synthesis",
        "assessment": assessment,
        "public_takeaways": {
            "significance": significance,
            "country_effect": country_effect,
            "pattern_fit": pattern_fit,
            "mechanism": mechanism,
            "institutional_implication": institutional_implication,
            "forward_risk": forward_risk,
            "confidence_note": interpretive_note if salience != "low" else confidence_context(event),
            "watchpoint": monitor_line,
        },
        "classification": classification,
        "risk_level": overall,
        "signals": unique_signals[:8],
        "confidence": round(
            sum(float(row.get("confidence") or 0) for code, row in analyses.items() if code != "synthesis")
            / max(1, len([code for code in analyses if code != "synthesis"])),
            2,
        ),
        "active_lens_count": len(analyses),
        "ai_generated": True,
        "knowledge_trace": {
            "guidance_priorities": role_info.get("priorities", [])[:3],
            "interpretive_rules": knowledge.get("interpretive_rules", [])[:3],
            "role_domains": role_domains,
            "relationship_types": relationship_types[:3],
            "interaction_types": interaction_types[:3],
            "lens_disagreement": disagreement,
            "active_lenses": [code for code, row in plan.items() if row.get("active")],
        },
    }


def build_entry(event: dict, knowledge: dict, guidance: dict, workers: dict[str, dict], article_lookup: dict[str, dict]) -> dict:
    context = article_context(event, article_lookup)
    plan = lens_plan(event)
    analyses = {}
    if plan["cmr"]["active"]:
        analyses["cmr"] = cmr_analysis(event, knowledge, guidance, context, plan)
    if plan["political_risk"]["active"]:
        analyses["political_risk"] = political_risk_analysis(event, knowledge, guidance, context, plan)
    if plan["regional_security"]["active"]:
        analyses["regional_security"] = regional_security_analysis(event, knowledge, guidance, context, plan)
    if plan["international"]["active"]:
        analyses["international"] = international_analysis(event, guidance, context, plan)
    if plan["economist"]["active"]:
        analyses["economist"] = economist_analysis(event, guidance, context, plan)
    combined = synthesis(event, analyses, guidance, knowledge, plan, context)
    combined["public_analysis"] = render_public_analysis(event, analyses, combined, context, plan)
    combined["public_style"] = "graduate_polisci_plain_v1"
    reviewed = reviewed_by_human(event)
    analyses["synthesis"] = combined
    upstream_worker_outputs = build_upstream_worker_outputs(event, workers, reviewed)
    recommended_review_actions = recommend_review_actions(event, analyses, upstream_worker_outputs, reviewed)
    return {
        "event_id": event.get("event_id"),
        "event_date": event.get("event_date"),
        "country": event.get("country"),
        "event_type": event.get("event_type"),
        "event_category": event.get("event_category"),
        "event_subcategory": event.get("event_subcategory"),
        "event_construct_destinations": event.get("event_construct_destinations"),
        "event_analyst_lenses": event.get("event_analyst_lenses"),
        "salience": event.get("salience"),
        "review_status": event.get("review_status"),
        "human_validated": bool(event.get("human_validated")),
        "reviewed_by_human": reviewed,
        "analysis_scope": "all_events",
        "analysis_tag": "AI-generated analysis",
        "generation_method": "heuristic_council_v4",
        "generated_at": datetime.now(UTC).isoformat(),
        "analysis_activation": plan,
        "event_context": context,
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
                *(worker_ref(workers, "cmr_analyst") for _ in [0] if plan["cmr"]["active"]),
                *(worker_ref(workers, "political_risk_analyst") for _ in [0] if plan["political_risk"]["active"]),
                *(worker_ref(workers, "regional_security_analyst") for _ in [0] if plan["regional_security"]["active"]),
                *(worker_ref(workers, "international_analyst") for _ in [0] if plan["international"]["active"]),
                *(worker_ref(workers, "economist_analyst") for _ in [0] if plan["economist"]["active"]),
                worker_ref(workers, "synthesis_analyst"),
            ],
        },
        "analyses": analyses,
    }


def main() -> None:
    source_path, payload = load_source()
    events = payload.get("events", [])
    article_lookup = load_articles()
    knowledge = json.loads(ANALYST_KNOWLEDGE.read_text(encoding="utf-8")) if ANALYST_KNOWLEDGE.exists() else DEFAULT_KNOWLEDGE
    guidance = json.loads(COUNCIL_GUIDANCE.read_text(encoding="utf-8")) if COUNCIL_GUIDANCE.exists() else DEFAULT_GUIDANCE
    roles = json.loads(COUNCIL_ROLES.read_text(encoding="utf-8")) if COUNCIL_ROLES.exists() else {}
    workers_payload = json.loads(AI_WORKERS.read_text(encoding="utf-8")) if AI_WORKERS.exists() else DEFAULT_WORKERS
    workers = worker_lookup(workers_payload)
    council_rows = [build_entry(event, knowledge, guidance, workers, article_lookup) for event in events]
    out = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_file": str(source_path.relative_to(ROOT)),
        "generation_method": "heuristic_council_v4",
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
