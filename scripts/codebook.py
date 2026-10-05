#!/usr/bin/env python3
"""
SENTINEL codebook v3: one source for the taxonomy, the classifier's definitions
and output schema, and validation.

config/taxonomy/codebook_v3.json is the approved codebook (owner decisions of
2026-09-29). Everything that codes events reads it through this module so a
definition changes in one place.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODEBOOK_PATH = ROOT / "config" / "taxonomy" / "codebook_v3.json"
COUNTRIES_PATH = ROOT / "config" / "taxonomy" / "countries.json"

CONTENT_TYPES = ["event", "analysis", "profile"]
SALIENCE = ["high", "medium", "low"]
CERTAINTY = ["high", "medium", "low"]
DATE_PRECISION = ["day", "month", "unknown"]
DEED_TYPES = ["precursor", "symptom", "resistance", "destabilizing", "not_applicable"]
AXES = ["horizontal", "vertical", "exogenous", "domestic", "not_applicable"]
RELATIONSHIPS = ["subordinate", "bargaining", "tutelary_veto", "partisan_pillar", "fractured", "praetorian", "corruption_capture"]
ACTOR_LEVELS = ["central", "subnational", "civil_society", "external"]
DEED_PREFIX = {"precursor": "3.", "symptom": "4.", "destabilizing": "5.", "resistance": "6."}


@lru_cache(maxsize=1)
def load() -> dict:
    return json.loads(CODEBOOK_PATH.read_text(encoding="utf-8"))


def types() -> list[dict]:
    return [t for domain in load()["domains"] for t in domain["types"]]


def type_codes() -> list[str]:
    return [t["code"] for t in types()]


def subtypes_by_type() -> dict[str, list[str]]:
    return {t["code"]: list(t["subtypes"]) for t in types()}


def deed_categories() -> dict[str, str]:
    return dict(load()["deed"]["categories"])


def deed_axis(category: str | None) -> str | None:
    """Axis of a DEED category, from its section group (3.1 → horizontal, …)."""
    if not category:
        return None
    section = ".".join(category.split(".")[:2])
    for _type, sec, _label, axis in load()["deed"]["groups"]:
        if sec == section:
            return axis
    return None


def actor_groups() -> list[str]:
    return [g[1] for g in load()["actors"]["groups"]]


def actor_roles() -> list[str]:
    return list(load()["actors"]["roles"])


@lru_cache(maxsize=1)
def countries() -> list[str]:
    names = json.loads(COUNTRIES_PATH.read_text(encoding="utf-8"))["countries"]
    return [c for c in names if c not in ("United States", "Multiple")]


def _nullable_enum(values: list[str]) -> dict:
    return {"anyOf": [{"type": "string", "enum": values}, {"type": "null"}]}


def _nullable_string() -> dict:
    return {"anyOf": [{"type": "string"}, {"type": "null"}]}


def item_schema() -> dict:
    """JSON schema for one coded article (structured output)."""
    all_subtypes = sorted({s for subs in subtypes_by_type().values() for s in subs})
    tracked = countries()
    actor = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "group": {"type": "string", "enum": actor_groups()},
            "role": {"type": "string", "enum": actor_roles()},
            "level": {"type": "string", "enum": ACTOR_LEVELS},
            "country": _nullable_string(),
        },
        "required": ["name", "group", "role", "level", "country"],
        "additionalProperties": False,
    }
    props = {
        "relevant": {"type": "boolean"},
        "content_type": {"type": "string", "enum": CONTENT_TYPES},
        "type": _nullable_enum(type_codes()),
        "subtype": _nullable_enum(all_subtypes),
        "secondary_types": {"type": "array", "items": {"type": "string", "enum": type_codes()}},
        "country": _nullable_enum(tracked),
        "secondary_countries": {"type": "array", "items": {"type": "string", "enum": tracked}},
        "event_date": _nullable_string(),
        "date_precision": {"type": "string", "enum": DATE_PRECISION},
        "location_place": _nullable_string(),
        "location_admin1": _nullable_string(),
        "actors": {"type": "array", "items": actor},
        "salience": _nullable_enum(SALIENCE),
        "certainty": {"type": "string", "enum": CERTAINTY},
        "deed_type": _nullable_enum(DEED_TYPES),
        "deed_category": _nullable_enum(sorted(deed_categories())),
        "axis": _nullable_enum(AXES),
        "relationship_signal": _nullable_enum(RELATIONSHIPS),
        "summary": _nullable_string(),
        "evidence": {"type": "array", "items": {"type": "string"}},
        "coding_note": _nullable_string(),
    }
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def validate(item: dict) -> list[str]:
    """Rules the schema cannot express. Returns a list of problems (empty = valid)."""
    problems: list[str] = []
    if not item.get("relevant"):
        return problems
    t = item.get("type")
    if not t:
        problems.append("relevant item without a type")
    sub = item.get("subtype")
    if t and sub and sub not in subtypes_by_type().get(t, []):
        problems.append(f"subtype {sub} does not belong to {t}")
    if len(item.get("secondary_types") or []) > 2:
        problems.append("more than two secondary types")
    if t and t in (item.get("secondary_types") or []):
        problems.append("secondary type repeats the primary type")
    if len(item.get("actors") or []) > 4:
        problems.append("more than four actors")
    deed, cat = item.get("deed_type"), item.get("deed_category")
    if not deed:
        problems.append("deed_type missing")
    if cat and deed in DEED_PREFIX and not cat.startswith(DEED_PREFIX[deed]):
        problems.append(f"DEED category {cat} does not sit under {deed}")
    if cat and deed == "not_applicable":
        problems.append("DEED category given with deed_type not_applicable")
    if cat and item.get("axis") and deed_axis(cat) and item["axis"] != deed_axis(cat):
        problems.append(f"axis {item['axis']} disagrees with DEED category {cat} ({deed_axis(cat)})")
    if t == "other" and not item.get("coding_note"):
        problems.append("type other without a coding_note")
    if len(item.get("evidence") or []) == 0:
        problems.append("no evidence quote")
    return problems


def normalize(item: dict) -> dict:
    """Deterministic fixes: derive axis from the DEED category, trim lists."""
    out = dict(item)
    if out.get("deed_category"):
        out["axis"] = deed_axis(out["deed_category"]) or out.get("axis")
    out["secondary_types"] = [s for s in (out.get("secondary_types") or []) if s != out.get("type")][:2]
    out["actors"] = (out.get("actors") or [])[:4]
    out["evidence"] = (out.get("evidence") or [])[:2]
    return out


def render_definitions() -> str:
    """The codebook as prompt text: units, types with boundaries, actors, DEED, field rules."""
    c = load()
    lines = ["# SENTINEL CODEBOOK v3", "", "## Unit of analysis"]
    lines += [f"- {k}: {c['unit'][k]}" for k in ("event", "analysis", "profile", "relevance")]
    lines += ["", "## Event types (pick one primary type; up to two secondary types)"]
    for domain in c["domains"]:
        lines += ["", f"### {domain['label']}", domain["note"]]
        for t in domain["types"]:
            lines.append(f"- {t['code']} ({t['label']}): {t['definition']}")
            if t.get("note"):
                lines.append(f"  Note: {t['note']}")
            if t["include"]:
                lines.append("  Include: " + "; ".join(t["include"]))
            if t["exclude"]:
                lines.append("  Exclude: " + "; ".join(t["exclude"]))
            if t["subtypes"]:
                lines.append("  Subtypes: " + ", ".join(t["subtypes"]))
            if t.get("example"):
                lines.append(f"  Example: {t['example']}")
    a = c["actors"]
    lines += ["", "## Actors (up to four named actors)", "Groups:"]
    lines += [f"- {g}: {cov} (e.g. {ex})" for _cat, g, _t, cov, ex in a["groups"]]
    lines += ["Roles: " + ", ".join(a["roles"]), "Levels: " + ", ".join(ACTOR_LEVELS)]
    lines += [f"- {r}" for r in a["rules"]]
    d = c["deed"]
    lines += ["", "## Democratic erosion (DEED)", d["intro"], "DEED types:"]
    lines += [f"- {k}: {v}" for k, v in d["types"]]
    lines.append("DEED categories, grouped by the DEED type they belong to (use one only when it fits, and only from the group of the DEED type you chose):")
    for dtype, prefix in DEED_PREFIX.items():
        lines.append(f"  If deed_type = {dtype}, choose from {prefix}x:")
        for _t, sec, label, axis in d["groups"]:
            if _t == dtype:
                cats = [f"{n} {name}" for n, name in d["categories"].items() if n.startswith(sec + ".")]
                if cats:
                    lines.append(f"    {sec} {label} (axis {axis}): " + "; ".join(cats))
    lines += [f"- {r}" for r in d["rules"]]
    lines += ["", "## Field rules"]
    for group in c["field_groups"]:
        for f in group["fields"]:
            lines.append(f"- {f['name']} [{f['values']}]: {f['rule']}")
    return "\n".join(lines)


# ── v2 compatibility ──────────────────────────────────────────────────────────
# Every v3 record keeps a v2 family (codebook decision: legacy continuity) so the
# current site, canonical build and risk models keep working during the switch.
_LEGACY_BY_TYPE = {
    "coup": "coup", "purge": "purge", "coup_proofing": "coup_proofing", "reform": "reform",
    "procurement": "procurement", "protest": "protest", "conflict": "conflict", "oc": "oc",
    "peace": "peace", "aid": "aid", "cooperation": "coop",
    "military_role": "other", "emergency_rule": "other", "friction": "other",
    "accountability": "other", "electoral_security": "other", "other": "other",
}
_LEGACY_SUBTYPE = {
    ("military_role", "disaster_response"): "military_disaster_response",
    ("emergency_rule", "emergency_legitimation"): "emergency_legitimation",
}
_V2_ACTOR = {
    "military": "military", "police": "military", "intelligence": "military", "prison_system": "military",
    "executive": "executive", "policy": "executive", "legislature": "legislature", "judiciary": "judiciary",
    "foreign_government": "external", "foreign_military": "external", "international_org": "external",
    "criminal_org": "oc_group", "insurgent_group": "oc_group", "paramilitary_militia": "oc_group",
    "civil_society": "civil_society", "political_party": "civil_society", "media": "civil_society",
    "economic_group": "civil_society", "protesters": "civil_society",
}


def legacy_family(v3_type: str | None, subtype: str | None = None) -> tuple[str, str | None]:
    """(v2 type, v2 subtype) for a v3 type."""
    if v3_type == "cooperation" and subtype and (subtype.startswith("exercise") or subtype == "port_visit"):
        return "exercise", None
    return _LEGACY_BY_TYPE.get(v3_type or "other", "other"), _LEGACY_SUBTYPE.get((v3_type, subtype))


def legacy_actor_target(actors: list[dict]) -> tuple[str | None, str | None]:
    """v2 actor/target codes from the first initiator and the first target or victim."""
    initiator = next((a for a in actors if a.get("role") == "initiator"), actors[0] if actors else None)
    target = next((a for a in actors if a.get("role") in ("target", "victim")), None)
    actor_code = _V2_ACTOR.get((initiator or {}).get("group"))
    if target and target.get("group") == "protesters" and target.get("role") == "victim":
        target_code = "population"
    else:
        target_code = _V2_ACTOR.get((target or {}).get("group"))
    return actor_code, target_code
