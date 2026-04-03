#!/usr/bin/env python3
"""
SENTINEL canonical event assembler.

Builds a schema-aligned canonical event dataset from the current live event store.

Outputs:
  data/canonical/events.json
  data/canonical/events.jsonl
  data/canonical/articles.json
  data/canonical/event_article_links.json
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent.parent
EVENTS_IN = ROOT / "data" / "events.json"
OUT_DIR = ROOT / "data" / "canonical"
JSON_OUT = OUT_DIR / "events.json"
JSONL_OUT = OUT_DIR / "events.jsonl"
ARTICLES_OUT = OUT_DIR / "articles.json"
ARTICLE_LINKS_OUT = OUT_DIR / "event_article_links.json"
STAGING_FILTERED_IN = ROOT / "data" / "staging" / "filtered_articles.json"
STAGING_RAW_IN = ROOT / "data" / "staging" / "raw_articles.json"
EVENT_TYPES_IN = ROOT / "config" / "taxonomy" / "event_types.json"


CONFIDENCE_MAP = {
    "green": "high",
    "yellow": "medium",
    "red": "low",
    "high": "high",
    "medium": "medium",
    "low": "low",
}


ACTOR_HIERARCHY_MAP = {
    "military": {
        "actor_category": "state_actor",
        "actor_group": "military",
        "actor_type": "state_security_force",
        "actor_subtype": "state_security_force",
    },
    "executive": {
        "actor_category": "state_actor",
        "actor_group": "executive",
        "actor_type": "state_institution",
        "actor_subtype": "state_institution",
    },
    "judiciary": {
        "actor_category": "state_actor",
        "actor_group": "judiciary",
        "actor_type": "state_institution",
        "actor_subtype": "state_institution",
    },
    "legislature": {
        "actor_category": "state_actor",
        "actor_group": "legislature",
        "actor_type": "state_institution",
        "actor_subtype": "state_institution",
    },
    "civil_society": {
        "actor_category": "non_state_actor",
        "actor_group": "civil_society",
        "actor_type": "civic_actor",
        "actor_subtype": "civic_actor",
    },
    "external": {
        "actor_category": "state_actor",
        "actor_group": "foreign_government",
        "actor_type": "foreign_government",
        "actor_subtype": "external_state_actor",
    },
    "oc_group": {
        "actor_category": "non_state_actor",
        "actor_group": "armed_non_state_actor",
        "actor_type": "organized_crime",
        "actor_subtype": "criminal_network",
    },
    "population": {
        "actor_category": "non_state_actor",
        "actor_group": "protesters",
        "actor_type": "civilian_group",
        "actor_subtype": "civilian_group",
    },
}


def load_events() -> tuple[dict, list[dict]]:
    raw = json.loads(EVENTS_IN.read_text(encoding="utf-8"))
    events = raw.get("events", []) if isinstance(raw, dict) else raw
    return raw, events


def load_article_lookup() -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for path in (STAGING_FILTERED_IN, STAGING_RAW_IN):
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload.get("articles", []):
            article_id = row.get("article_id")
            url = row.get("url")
            if article_id and article_id not in lookup:
                lookup[article_id] = row
            if url:
                lookup[f"url:{url}"] = row
    return lookup


def load_event_taxonomy() -> dict[str, dict]:
    if not EVENT_TYPES_IN.exists():
        return {}
    payload = json.loads(EVENT_TYPES_IN.read_text(encoding="utf-8"))
    return {
        str(row.get("code")): row
        for row in payload.get("event_types", [])
        if row.get("code")
    }


def parse_date_parts(date_str: str) -> tuple[int | None, int | None, int | None]:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.year, dt.month, dt.day
    except Exception:
        return None, None, None


def classify_other_overlay(event: dict, actors: list[dict], context_text: str) -> dict:
    text = context_text.lower()
    actor_groups = {
        str(actor.get("actor_group") or actor.get("actor_canonical_group") or "").strip().lower()
        for actor in actors
    }
    actor_types = {
        str(actor.get("actor_type") or actor.get("actor_canonical_type") or "").strip().lower()
        for actor in actors
    }

    def has_any(*terms: str) -> bool:
        return any(term in text for term in terms)

    if has_any("sanction", "blockade", "embargo", "o.a.s.", "oas", "u.s.", "united states", "united nations", "european union", "imf", "world bank", "embassy", "diplomatic", "foreign ministry", "foreign policy"):
        return {
            "event_category": "international",
            "event_subcategory": "diplomatic_pressure_and_external_alignment",
            "construct_destinations": ["regime_vulnerability"],
            "analyst_lenses": ["political", "international"],
        }
    if has_any("debt", "inflation", "currency", "fx", "fiscal", "budget", "subsidy", "fuel price", "price hike", "devaluation", "default", "austerity", "economic crisis", "oil tanker", "oil shipment"):
        return {
            "event_category": "economic",
            "event_subcategory": "macro_stress_and_policy_shock",
            "construct_destinations": ["regime_vulnerability"],
            "analyst_lenses": ["political", "economist"],
        }
    if has_any("election", "vote", "poll", "campaign", "ballot", "mayor", "governor", "presidential race", "electoral"):
        return {
            "event_category": "political",
            "event_subcategory": "electoral_contestation_and_realignment",
            "construct_destinations": ["regime_vulnerability"],
            "analyst_lenses": ["political"],
        }
    if has_any("judge", "court", "supreme court", "justice department", "charges", "prosecutor", "investigation", "tribunal", "attorney general"):
        return {
            "event_category": "political",
            "event_subcategory": "judicial_and_accountability_shock",
            "construct_destinations": ["regime_vulnerability"],
            "analyst_lenses": ["political", "international"] if "foreign_government" in actor_types or "foreign_government" in actor_groups else ["political"],
        }
    if has_any("humanitarian", "search-and-rescue", "search and rescue", "navy", "patrol", "coast guard", "deployment") and (
        "military" in actor_groups or "foreign_government" in actor_types or "external" in actor_groups
    ):
        return {
            "event_category": "military",
            "event_subcategory": "operational_posture_and_presence",
            "construct_destinations": ["militarization"],
            "analyst_lenses": ["military", "international"],
        }
    if has_any("authoritarian", "democratic erosion", "governance style", "institutional erosion", "continuity", "political project"):
        return {
            "event_category": "political",
            "event_subcategory": "institutional_drift_and_leadership_project",
            "construct_destinations": ["regime_vulnerability"],
            "analyst_lenses": ["political"],
        }
    if "foreign_government" in actor_types or "external" in actor_groups:
        return {
            "event_category": "international",
            "event_subcategory": "external_pressure_and_alignment_watch",
            "construct_destinations": ["regime_vulnerability"],
            "analyst_lenses": ["political", "international"],
        }
    return {
        "event_category": "political",
        "event_subcategory": "other_institutional_relevance",
        "construct_destinations": ["regime_vulnerability"],
        "analyst_lenses": ["political"],
    }


def classify_oc_overlay(context_text: str) -> dict:
    text = context_text.lower()

    def has_any(*terms: str) -> bool:
        return any(term in text for term in terms)

    if has_any("massacre", "killed", "murder", "extermination", "slaughter", "attack", "violence"):
        subcategory = "criminal_violence_and_social_control"
    elif has_any("seize", "seizure", "intercept", "raid", "operation", "coast guard", "navy", "semi-submersible"):
        subcategory = "criminal_interdiction_and_state_response"
    elif has_any("hub", "logistic", "trafficking route", "shipment", "corridor", "displac", "smuggling"):
        subcategory = "trafficking_logistics_and_route_shift"
    elif has_any("terrorist organization", "designation", "sanction", "policy", "strategy"):
        subcategory = "criminal_policy_and_legal_reclassification"
    else:
        subcategory = "armed_non_state_and_illicit_order"
    return {
        "event_category": "security",
        "event_subcategory": subcategory,
        "construct_destinations": ["security_fragmentation", "regime_vulnerability"],
        "analyst_lenses": ["security", "political", "economist"],
    }


def classify_coup_overlay(context_text: str) -> dict:
    text = context_text.lower()
    if any(term in text for term in ("historical retrospective", "50 years", "anniversary", "recuerdos del día del golpe", "history of the coup")):
        subcategory = "historical_coup_memory_and_legacy"
    elif any(term in text for term in ("unverified", "vehicle movements", "rumor", "reports of troop movements")):
        subcategory = "coup_watch_and_preemptive_alert"
    elif any(term in text for term in ("arraigned", "acting president", "seizing", "seizure of president", "leader removal", "interim presidency")):
        subcategory = "executive_removal_and_irregular_transfer"
    else:
        subcategory = "irregular_transfer_and_command_break"
    return {
        "event_category": "political",
        "event_subcategory": subcategory,
        "construct_destinations": ["regime_vulnerability", "militarization"],
        "analyst_lenses": ["political", "military"],
    }


def classify_purge_overlay(context_text: str) -> dict:
    text = context_text.lower()
    if any(term in text for term in ("promotes", "promotion", "high command", "loyalists", "appoint")):
        subcategory = "loyalist_promotion_and_command_stack"
    elif any(term in text for term in ("detained officers", "detained at barracks", "arbitrary detention", "mass detention")):
        subcategory = "coercive_detention_and_internal_crackdown"
    elif any(term in text for term in ("exit of", "dismissal of defense minister", "removes intelligence chief", "forced out", "retirement")):
        subcategory = "elite_security_reshuffle"
    elif any(term in text for term in ("scandal", "integrity", "morale", "vergüenza", "computer scandal")):
        subcategory = "institutional_scandal_and_command_stress"
    else:
        subcategory = "command_and_coercive_control"
    return {
        "event_category": "military",
        "event_subcategory": subcategory,
        "construct_destinations": ["militarization", "regime_vulnerability"],
        "analyst_lenses": ["military", "political"],
    }


def classify_aid_overlay(context_text: str) -> dict:
    text = context_text.lower()
    if any(term in text for term in ("training", "special forces", "green berets", "joint training")):
        subcategory = "foreign_training_and_force_assistance"
    elif any(term in text for term in ("fms", "sale", "$", "purchase", "aircraft", "equipment", "base modernization")):
        subcategory = "external_financing_and_capability_transfer"
    elif any(term in text for term in ("agreement renewed", "cooperation agreement", "five years")):
        subcategory = "security_assistance_framework_renewal"
    elif any(term in text for term in ("port visit", "frigate", "naval vessel")):
        subcategory = "symbolic_or_access_oriented_security_support"
    else:
        subcategory = "external_security_support"
    return {
        "event_category": "international",
        "event_subcategory": subcategory,
        "construct_destinations": ["militarization", "security_fragmentation"],
        "analyst_lenses": ["international", "military"],
    }


def classify_peace_overlay(context_text: str) -> dict:
    text = context_text.lower()

    def has_any(*terms: str) -> bool:
        return any(term in text for term in terms)

    if has_any("poll", "election", "vote", "presidential", "campaign"):
        subcategory = "peace_process_electoral_stress"
    elif has_any("court", "sentence", "tribunal", "justice", "accountability", "historic sentence"):
        subcategory = "transitional_justice_and_accountability"
    elif has_any("attack", "destroys chances", "terminates", "rejects", "collapse", "breakdown"):
        subcategory = "peace_process_breakdown_and_spoilers"
    elif has_any("proposal", "negotiation", "talks", "dialogue", "ceasefire", "truce"):
        subcategory = "negotiation_and_settlement_dynamics"
    elif has_any("criminal disputes", "fragment", "armed groups", "gang", "agc", "eln"):
        subcategory = "armed_actor_fragmentation_within_peace_process"
    else:
        subcategory = "conflict_management_and_settlement"
    return {
        "event_category": "political",
        "event_subcategory": subcategory,
        "construct_destinations": ["security_fragmentation", "regime_vulnerability"],
        "analyst_lenses": ["political", "security", "international"],
    }


def classify_protest_overlay(context_text: str) -> dict:
    text = context_text.lower()
    if any(term in text for term in ("water cannons", "tear gas", "dispersed protests", "repression", "detained")):
        subcategory = "protest_repression_and_security_response"
    elif any(term in text for term in ("strike", "mobilize", "corporation", "salary", "federal police")):
        subcategory = "security_force_labor_and_institutional_contention"
    elif any(term in text for term in ("fuel subsidy", "social movement", "popular struggles", "mass protests")):
        subcategory = "mass_mobilization_and_state_pushback"
    elif any(term in text for term in ("colectivos", "armed colectivos", "post-maduro")):
        subcategory = "armed_pro_government_mobilization"
    else:
        subcategory = "contention_and_state_response"
    return {
        "event_category": "political",
        "event_subcategory": subcategory,
        "construct_destinations": ["regime_vulnerability", "security_fragmentation"],
        "analyst_lenses": ["political", "security"],
    }


def classify_reform_overlay(context_text: str) -> dict:
    text = context_text.lower()
    if any(term in text for term in ("national guard", "army command", "military control over domestic security")):
        subcategory = "domestic_security_militarization"
    elif any(term in text for term in ("state of exception", "extension approved", "detained", "human rights complaints")):
        subcategory = "exceptional_rule_and_coercive_governance"
    elif any(term in text for term in ("un gang suppression force", "mss transitions", "kenyan contingent", "un-mandated")):
        subcategory = "security_governance_reconfiguration"
    elif any(term in text for term in ("white paper", "doctrine", "defense policy", "revision")):
        subcategory = "doctrinal_and_institutional_modernization"
    elif any(term in text for term in ("promotion of first female general", "diversification", "inclusion")):
        subcategory = "institutional_professionalization_and_inclusion"
    else:
        subcategory = "institutional_security_reordering"
    return {
        "event_category": "political",
        "event_subcategory": subcategory,
        "construct_destinations": ["regime_vulnerability", "militarization"],
        "analyst_lenses": ["political", "military"],
    }


def classify_coop_overlay(context_text: str) -> dict:
    text = context_text.lower()

    def has_any(*terms: str) -> bool:
        return any(term in text for term in terms)

    if has_any("train", "training", "navy seal", "advis", "marine corps", "fbi office"):
        subcategory = "foreign_training_and_advisory_presence"
    elif has_any("airstrike", "operation", "bombard", "interdiction", "counter-cartel", "drug war"):
        subcategory = "operational_security_cooperation"
    elif has_any("embassy", "reopens embassy", "relations", "thawing", "diplomatic"):
        subcategory = "security_diplomacy_and_reengagement"
    elif has_any("coalition", "strategy", "regional", "push for more", "expanded military-led approach"):
        subcategory = "regional_security_alignment_and_strategy"
    else:
        subcategory = "external_security_alignment"
    return {
        "event_category": "international",
        "event_subcategory": subcategory,
        "construct_destinations": ["security_fragmentation", "militarization"],
        "analyst_lenses": ["international", "military", "security"],
    }


def classify_exercise_overlay(context_text: str) -> dict:
    text = context_text.lower()
    if any(term in text for term in ("multinational", "participating nations", "hemisphere")):
        subcategory = "multinational_force_posture_and_interoperability"
    elif any(term in text for term in ("naval", "maritime")):
        subcategory = "maritime_force_projection_and_training"
    else:
        subcategory = "force_posture_and_training"
    return {
        "event_category": "military",
        "event_subcategory": subcategory,
        "construct_destinations": ["militarization"],
        "analyst_lenses": ["military", "international"],
    }


def classify_procurement_overlay(context_text: str) -> dict:
    text = context_text.lower()
    if any(term in text for term in ("aircraft", "frigate", "submarine", "drone", "missile")):
        subcategory = "major_capability_acquisition"
    elif any(term in text for term in ("contract", "manufacturer", "tender")):
        subcategory = "defense_contracting_and_supplier_choice"
    elif any(term in text for term in ("financing", "loan", "fms", "credit")):
        subcategory = "externally_financed_procurement"
    else:
        subcategory = "force_build_up_and_equipment"
    return {
        "event_category": "military",
        "event_subcategory": subcategory,
        "construct_destinations": ["militarization"],
        "analyst_lenses": ["military", "international", "economist"],
    }


def classify_conflict_overlay(context_text: str) -> dict:
    text = context_text.lower()
    if any(term in text for term in ("airstrike", "bomb", "military operation", "joint operation", "base")):
        subcategory = "state_offensive_and_counterinsurgent_action"
    elif any(term in text for term in ("massacre", "killed", "attack", "violence", "shooting")):
        subcategory = "armed_violence_and_localized_breakdown"
    elif any(term in text for term in ("state of exception", "detained", "mass detention")):
        subcategory = "coercive_internal_crackdown"
    elif any(term in text for term in ("cartel violence", "organized crime hub", "gang")):
        subcategory = "criminal_conflict_and_fragmented_order"
    elif any(term in text for term in ("court", "arraigned", "tribunal")):
        subcategory = "conflict_aftershock_and_regime_spillover"
    else:
        subcategory = "armed_fragmentation_and_territorial_control"
    return {
        "event_category": "security",
        "event_subcategory": subcategory,
        "construct_destinations": ["security_fragmentation", "regime_vulnerability"],
        "analyst_lenses": ["security", "political"],
    }


def apply_taxonomy_overlay(event: dict, taxonomy_row: dict, actors: list[dict]) -> dict:
    overlay = {
        "type": taxonomy_row.get("type") or taxonomy_row.get("event_category"),
        "category": taxonomy_row.get("category") or taxonomy_row.get("code"),
        "category_label": taxonomy_row.get("category_label") or taxonomy_row.get("label"),
        "event_category": taxonomy_row.get("event_category"),
        "event_subcategory": taxonomy_row.get("event_subcategory"),
        "construct_destinations": list(taxonomy_row.get("construct_destinations", [])),
        "analyst_lenses": list(taxonomy_row.get("analyst_lenses", [])),
    }

    context_bits = [
        str(event.get("title") or ""),
        str(event.get("summary") or ""),
        str(event.get("subtype") or ""),
    ]
    context_text = " ".join(bit for bit in context_bits if bit)
    event_type = str(event.get("type") or "other")

    specific = None
    if event_type == "other":
        specific = classify_other_overlay(event, actors, context_text)
    elif event_type == "coup":
        specific = classify_coup_overlay(context_text)
    elif event_type == "purge":
        specific = classify_purge_overlay(context_text)
    elif event_type == "aid":
        specific = classify_aid_overlay(context_text)
    elif event_type == "oc":
        specific = classify_oc_overlay(context_text)
    elif event_type == "protest":
        specific = classify_protest_overlay(context_text)
    elif event_type == "reform":
        specific = classify_reform_overlay(context_text)
    elif event_type == "peace":
        specific = classify_peace_overlay(context_text)
    elif event_type == "coop":
        specific = classify_coop_overlay(context_text)
    elif event_type == "exercise":
        specific = classify_exercise_overlay(context_text)
    elif event_type == "procurement":
        specific = classify_procurement_overlay(context_text)
    elif event_type == "conflict":
        specific = classify_conflict_overlay(context_text)
    if specific:
        specific.setdefault("type", overlay.get("type"))
        specific.setdefault("category", overlay.get("category"))
        specific.setdefault("category_label", overlay.get("category_label"))
        return specific
    return overlay


def to_actor_object(name: str | None, role: str, country: str) -> dict | None:
    if not name:
        return None
    hierarchy = ACTOR_HIERARCHY_MAP.get(name, {
        "actor_category": "other",
        "actor_group": "other",
        "actor_type": "other",
        "actor_subtype": None,
    })
    return {
        "actor_name": name,
        "actor_category": hierarchy["actor_category"],
        "actor_group": hierarchy["actor_group"],
        "actor_type": hierarchy["actor_type"],
        "actor_subtype": hierarchy["actor_subtype"],
        "actor_country": country or None,
        "actor_role_in_event": role,
        "actor_canonical_name": None,
        "actor_canonical_category": hierarchy["actor_category"],
        "actor_canonical_group": hierarchy["actor_group"],
        "actor_canonical_type": hierarchy["actor_type"],
        "actor_canonical_subtype": hierarchy["actor_subtype"],
    }


def actor_hierarchy_for_name(name: str | None) -> dict:
    return ACTOR_HIERARCHY_MAP.get(name, {
        "actor_category": "other",
        "actor_group": "other",
        "actor_type": "other",
        "actor_subtype": None,
    })


def timeline_entry(stage: str, at: str | None, label: str, details: dict | None = None, status: str = "completed") -> dict:
    return {
        "stage": stage,
        "label": label,
        "status": status,
        "at": at,
        "details": details or {},
    }


def unique_nonempty(items: list[str | None]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        values.append(value)
    return values


def infer_domain(url: str | None) -> str | None:
    if not url:
        return None
    try:
        domain = (urlparse(url).netloc or "").lower()
    except Exception:
        return None
    if domain.startswith("www."):
        domain = domain[4:]
    return domain or None


def infer_source_name(url: str | None, fallback: str | None = None) -> str | None:
    if fallback:
        return fallback
    return infer_domain(url)


def article_id_for_url(url: str | None, source_name: str | None) -> str:
    key = f"{url or ''}|{source_name or ''}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def clean_article_description(text: str | None) -> str | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    cleaned = re.sub(r"<[^>]+>", " ", raw)
    cleaned = re.sub(r"<.*$", " ", cleaned)
    cleaned = re.sub(r'href="[^"]*', " ", cleaned)
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:500] if cleaned else None


def build_article_records(
    *,
    event_id: str,
    headline: str,
    summary: str | None,
    source_article_ids: list[str] | None,
    source_primary: str,
    source_all: list[str],
    url_primary: str,
    url_all: list[str],
    source_type: str | None,
    linked_at: str,
    article_lookup: dict[str, dict],
) -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()

    for idx, article_id in enumerate(source_article_ids or [], start=1):
        article = article_lookup.get(article_id)
        if not article:
            continue
        url = article.get("url")
        key = article_id or url or f"article-{idx}"
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "article_id": article_id,
                "event_id": event_id,
                "article_rank": idx,
                "report_role": "primary" if idx == 1 else "supporting",
                "source_name": article.get("source") or source_primary,
                "url": url,
                "link_domain": infer_domain(url),
                "headline": article.get("title") or (headline if idx == 1 else None),
                "description": clean_article_description(article.get("description")) or (summary if idx == 1 else None),
                "source_type": article.get("source_type") or source_type,
                "source_method": article.get("source_method"),
                "article_date": article.get("date"),
                "linked_at": article.get("normalized_at") or linked_at,
            }
        )

    urls = unique_nonempty(url_all or [url_primary])
    sources = unique_nonempty(source_all or [source_primary])

    if not urls and source_primary:
        urls = [url_primary]

    for idx, url in enumerate(urls):
        key = url or f"url-{idx}"
        if key in seen:
            continue
        seen.add(key)
        article = article_lookup.get(f"url:{url}") if url else None
        source_name = infer_source_name(
            url,
            article.get("source") if article else (sources[idx] if idx < len(sources) else (source_primary if idx == 0 else None)),
        ) or source_primary
        role = "primary" if idx == 0 or url == url_primary else "supporting"
        rows.append(
            {
                "article_id": (article or {}).get("article_id") or article_id_for_url(url, source_name),
                "event_id": event_id,
                "article_rank": idx + 1,
                "report_role": role,
                "source_name": source_name,
                "url": url,
                "link_domain": infer_domain(url),
                "headline": (article or {}).get("title") or (headline if role == "primary" else None),
                "description": clean_article_description((article or {}).get("description")) or (summary if role == "primary" else None),
                "source_type": (article or {}).get("source_type") or source_type,
                "source_method": (article or {}).get("source_method"),
                "article_date": (article or {}).get("date"),
                "linked_at": (article or {}).get("normalized_at") or linked_at,
            }
        )

    if not rows and source_primary:
        rows.append(
            {
                "article_id": article_id_for_url(url_primary, source_primary),
                "event_id": event_id,
                "article_rank": 1,
                "report_role": "primary",
                "source_name": source_primary,
                "url": url_primary,
                "link_domain": infer_domain(url_primary),
                "headline": headline,
                "description": summary,
                "source_type": source_type,
                "source_method": None,
                "article_date": None,
                "linked_at": linked_at,
            }
        )

    return rows


def existing_linked_reports(event: dict, article_lookup: dict[str, dict]) -> list[dict]:
    reports = event.get("linked_reports") or []
    out: list[dict] = []
    seen: set[str] = set()
    for idx, report in enumerate(reports, start=1):
        key = report.get("article_id") or report.get("url") or f"report-{idx}"
        if key in seen:
            continue
        seen.add(key)
        article = article_lookup.get(report.get("article_id")) or article_lookup.get(f"url:{report.get('url')}") or {}
        out.append(
            {
                "article_id": report.get("article_id") or article_id_for_url(report.get("url"), report.get("source_name") or report.get("source")),
                "event_id": event.get("id", ""),
                "article_rank": report.get("article_rank") or idx,
                "report_role": report.get("report_role") or ("primary" if idx == 1 else "supporting"),
                "source_name": report.get("source_name") or report.get("source"),
                "url": report.get("url"),
                "link_domain": report.get("link_domain") or infer_domain(report.get("url")),
                "headline": report.get("headline") or (event.get("title") if idx == 1 else None),
                "description": clean_article_description(report.get("description")) or clean_article_description(article.get("description")) or (event.get("summary") if idx == 1 else None),
                "source_type": report.get("source_type") or event.get("source_type"),
                "source_method": report.get("source_method") or article.get("source_method"),
                "article_date": report.get("article_date") or article.get("date"),
                "linked_at": report.get("linked_at") or article.get("normalized_at"),
            }
        )
    return out


def canonicalize_event(
    event: dict,
    source_updated_at: str | None,
    article_lookup: dict[str, dict],
    event_taxonomy: dict[str, dict],
) -> dict:
    event_date = event.get("date", "")
    year, month, day = parse_date_parts(event_date)
    coords = event.get("coords") or [None, None]
    if len(coords) != 2:
        coords = [None, None]

    source_all = event.get("sources") or ([event.get("source")] if event.get("source") else [])
    url_all = event.get("links") or ([event.get("url")] if event.get("url") else [])
    source_primary = source_all[0] if source_all else (event.get("source") or "")
    event_id = event.get("id", "")
    url_primary = url_all[0] if url_all else (event.get("url") or f"sentinel:event:{event_id}")

    actor_primary_name = event.get("actor") or None
    actor_secondary_name = event.get("target") or None
    country = event.get("country", "")
    actor_primary_hierarchy = actor_hierarchy_for_name(actor_primary_name) if actor_primary_name else None
    actor_secondary_hierarchy = actor_hierarchy_for_name(actor_secondary_name) if actor_secondary_name else None

    actors = []
    primary_actor = to_actor_object(actor_primary_name, "initiator", country)
    secondary_actor = to_actor_object(actor_secondary_name, "target", country)
    if primary_actor:
        actors.append(primary_actor)
    if secondary_actor:
        actors.append(secondary_actor)

    salience = event.get("salience", "low")
    review_priority = "high" if salience == "high" else "medium" if salience == "medium" else "low"
    ingested_at = event.get("ingested_at") or source_updated_at or datetime.now(UTC).isoformat()
    merge_strategy = "clustered_source_merge" if len(source_all) > 1 else "single_source"
    linked_reports = existing_linked_reports(event, article_lookup) or build_article_records(
        event_id=event_id,
        headline=event.get("title", ""),
        summary=event.get("summary"),
        source_article_ids=event.get("source_article_ids") or [],
        source_primary=source_primary,
        source_all=source_all,
        url_primary=url_primary,
        url_all=url_all,
        source_type=event.get("source_type"),
        linked_at=ingested_at,
        article_lookup=article_lookup,
    )
    timeline = [
        timeline_entry(
            "ingestion",
            ingested_at,
            "Source ingestion",
            {
                "source_type": event.get("source_type"),
                "source_primary": source_primary,
                "source_count": len(source_all),
                "linked_report_count": len(linked_reports),
                "has_external_url": bool(event.get("url") or event.get("links")),
            },
        ),
        timeline_entry(
            "normalization",
            source_updated_at or ingested_at,
            "Source record normalized",
            {
                "normalized_fields": [
                    "event_date",
                    "country",
                    "source_primary",
                    "url_primary",
                    "summary",
                ],
                "location_available": bool(event.get("location")),
                "coords_available": bool(event.get("coords")),
            },
        ),
        timeline_entry(
            "classification",
            source_updated_at or ingested_at,
            "Event classified",
            {
                "event_type": event.get("type", "other"),
                "raw_confidence": event.get("conf"),
                "classification_model": "claude-haiku-4-5-20251001",
            },
        ),
        timeline_entry(
            "canonicalization",
            source_updated_at or ingested_at,
            "Canonical event assembled",
            {
                "merge_strategy": merge_strategy,
                "source_event_id": event.get("sentinel_id"),
            },
        ),
    ]

    event_type = event.get("type", "other")
    taxonomy_row = event_taxonomy.get(str(event_type), event_taxonomy.get("other", {}))
    taxonomy_overlay = apply_taxonomy_overlay(event, taxonomy_row, actors)

    return {
        "event_id": event.get("id", ""),
        "event_date": event_date,
        "year": year,
        "month": month,
        "day": day,
        "country": country,
        "subnational_location": event.get("location") or None,
        "location_text": event.get("location") or None,
        "latitude": coords[0],
        "longitude": coords[1],
        "headline": event.get("title", ""),
        "source_primary": source_primary,
        "source_all": source_all,
        "url_primary": url_primary,
        "url_all": url_all,
        "language": None,
        "event_type": event_type,
        "legacy_event_family": event_type,
        "event_type_domain": taxonomy_overlay.get("type"),
        "event_category_family": taxonomy_overlay.get("category"),
        "event_category_label": taxonomy_overlay.get("category_label"),
        "event_category": taxonomy_overlay.get("event_category"),
        "event_subcategory": taxonomy_overlay.get("event_subcategory"),
        "event_construct_destinations": list(taxonomy_overlay.get("construct_destinations", [])),
        "event_analyst_lenses": list(taxonomy_overlay.get("analyst_lenses", [])),
        "event_subtype": event.get("subtype") or None,
        "deed_type": event.get("deed_type") or None,
        "axis": event.get("axis") or None,
        "episode_id": None,
        "process_id": None,
        "episode_role": None,
        "process_relevance": None,
        "salience": salience,
        "confidence": CONFIDENCE_MAP.get(event.get("conf", "low"), "low"),
        "summary": event.get("summary") or None,
        "classification_reason": event.get("ai_analysis") or None,
        "classification_rule_ids": [],
        "actors": actors,
        "actor_primary_name": actor_primary_name,
        "actor_primary_category": actor_primary_hierarchy["actor_category"] if actor_primary_hierarchy else None,
        "actor_primary_group": actor_primary_hierarchy["actor_group"] if actor_primary_hierarchy else None,
        "actor_primary_type": actor_hierarchy_for_name(actor_primary_name)["actor_type"] if actor_primary_name else None,
        "actor_secondary_name": actor_secondary_name,
        "actor_secondary_category": actor_secondary_hierarchy["actor_category"] if actor_secondary_hierarchy else None,
        "actor_secondary_group": actor_secondary_hierarchy["actor_group"] if actor_secondary_hierarchy else None,
        "actor_secondary_type": actor_hierarchy_for_name(actor_secondary_name)["actor_type"] if actor_secondary_name else None,
        "duplicate_group_id": None,
        "duplicate_status": "distinct",
        "review_status": "auto",
        "review_priority": review_priority,
        "review_notes": None,
        "reviewed_by": None,
        "reviewed_at": None,
        "provenance": {
            "source_type": event.get("source_type"),
            "ingested_at": ingested_at,
            "classification_model": "claude-haiku-4-5-20251001",
            "merge_strategy": merge_strategy,
            "source_event_id": event.get("sentinel_id"),
            "deed_type": event.get("deed_type"),
            "axis": event.get("axis"),
            "raw_confidence": event.get("conf"),
            "has_external_url": bool(event.get("url") or event.get("links")),
            "article_link_count": len(linked_reports),
            "article_record_ids": [row["article_id"] for row in linked_reports],
            "linked_reports": linked_reports,
            "timeline": timeline,
        },
        "created_at": ingested_at,
        "updated_at": source_updated_at or ingested_at,
        "published_at": None,
    }


def validate_minimal(record: dict) -> list[str]:
    errors: list[str] = []
    required = [
        "event_id", "event_date", "year", "month", "day", "country",
        "headline", "source_primary", "url_primary", "event_type",
        "salience", "confidence", "review_status", "created_at", "updated_at",
    ]
    for key in required:
        value = record.get(key)
        if value in (None, ""):
            errors.append(f"missing:{key}")
    return errors


def main() -> None:
    raw, events = load_events()
    source_updated_at = raw.get("updated") if isinstance(raw, dict) else None
    article_lookup = load_article_lookup()
    event_taxonomy = load_event_taxonomy()

    canonical_rows = [canonicalize_event(event, source_updated_at, article_lookup, event_taxonomy) for event in events]
    article_catalog: dict[str, dict] = {}
    event_article_links: list[dict] = []
    for row in canonical_rows:
        for report in (row.get("provenance") or {}).get("linked_reports", []):
            article_catalog.setdefault(
                report["article_id"],
                {
                    "article_id": report["article_id"],
                    "source_name": report.get("source_name"),
                    "url": report.get("url"),
                    "link_domain": report.get("link_domain"),
                    "headline": report.get("headline"),
                    "description": report.get("description"),
                    "source_type": report.get("source_type"),
                    "source_method": report.get("source_method"),
                    "article_date": report.get("article_date"),
                    "first_linked_at": report.get("linked_at"),
                },
            )
            event_article_links.append(
                {
                    "event_id": row.get("event_id"),
                    "article_id": report["article_id"],
                    "article_rank": report.get("article_rank"),
                    "report_role": report.get("report_role"),
                    "source_name": report.get("source_name"),
                    "url": report.get("url"),
                    "link_domain": report.get("link_domain"),
                    "linked_at": report.get("linked_at"),
                }
            )
    validation_errors = [
        {"event_id": row.get("event_id"), "errors": validate_minimal(row)}
        for row in canonical_rows
    ]
    validation_errors = [row for row in validation_errors if row["errors"]]

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_file": str(EVENTS_IN.relative_to(ROOT)),
        "source_updated_at": source_updated_at,
        "count": len(canonical_rows),
        "validation_error_count": len(validation_errors),
        "events": canonical_rows,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    JSONL_OUT.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in canonical_rows),
        encoding="utf-8",
    )
    ARTICLES_OUT.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(UTC).isoformat(),
                "source_file": str(EVENTS_IN.relative_to(ROOT)),
                "count": len(article_catalog),
                "articles": list(article_catalog.values()),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    ARTICLE_LINKS_OUT.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(UTC).isoformat(),
                "source_file": str(EVENTS_IN.relative_to(ROOT)),
                "count": len(event_article_links),
                "links": event_article_links,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Wrote canonical JSON to {JSON_OUT}")
    print(f"Wrote canonical JSONL to {JSONL_OUT}")
    print(f"Wrote canonical article catalog to {ARTICLES_OUT}")
    print(f"Wrote canonical event/article links to {ARTICLE_LINKS_OUT}")
    print(f"Events assembled: {len(canonical_rows)}")
    print(f"Unique linked articles: {len(article_catalog)}")
    print(f"Event/article links: {len(event_article_links)}")
    print(f"Validation errors: {len(validation_errors)}")


if __name__ == "__main__":
    main()
