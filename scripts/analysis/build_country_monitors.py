#!/usr/bin/env python3
"""
Build layered SENTINEL country monitors and predictive risk constructs.

Outputs:
  data/published/country_monitors.json

This builder keeps the monitor-family layer transparent, then aggregates those
families into a small set of country-level risk constructs:

- regime_vulnerability
- militarization
- security_fragmentation
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
MODEL_CONFIG = ROOT / "config" / "baseline_pulse_model.json"
MISSION_PROFILES = ROOT / "config" / "military_role_profiles.json"
COUNTRY_YEAR = ROOT / "data" / "cleaned" / "country_year.json"
ACLED_INDEX = ROOT / "data" / "cleaned" / "acled_index.json"
EDITED_EVENTS = ROOT / "data" / "review" / "events_with_edits.json"
CANONICAL_EVENTS = ROOT / "data" / "canonical" / "events_actor_coded.json"
LIVE_EVENTS = ROOT / "data" / "events.json"
EXTERNAL_ECONOMIC = ROOT / "data" / "modeling" / "external_economic_country_month.json"
OUT = ROOT / "data" / "published" / "country_monitors.json"

HUMAN_REVIEW_STATUSES = {
    "ra_reviewed",
    "analyst_reviewed",
    "coordinator_approved",
    "reviewed",
    "published",
}

ACLED_LEVEL_SCORE = {
    "low": 25.0,
    "turbulent": 50.0,
    "high": 75.0,
    "extreme": 100.0,
}

INPUT_LABELS = {
    "m3_conscription": "conscription structure",
    "m3_military_veto": "military veto power",
    "m3_impunity": "military impunity",
    "m3_public_security_role": "military public-security role",
    "m3_military_economic_role": "military economic role",
    "executive_military_history": "executive-military entanglement",
    "historical_coup_exposure": "historical coup exposure",
    "acled_conflict_level": "conflict baseline",
    "criminality_baseline": "criminality baseline",
    "oc_actor_density": "organized-crime actor density",
    "territorial_fragmentation_signal": "territorial spread of coercive stress",
    "territorial_state_capacity": "state-capacity weakness",
    "violence_history": "violence history",
    "military_constraint_weakness": "weak civilian constraints on the military",
    "regime_authoritarianism": "authoritarian regime structure",
    "historical_us_security_exposure": "historical US security exposure",
    "alliance_posture": "alliance posture",
    "arms_dependence_profile": "arms dependence profile",
    "security_partner_depth": "security partner depth",
    "democratic_fragility": "democratic fragility",
    "governance_erosion": "governance erosion",
    "deed_erosion_signal": "institutional erosion signal",
    "military_governance_role": "military governance role",
    "military_domestic_coercion_role": "military domestic-coercion role",
    "military_governance_administration_role": "military governance-administration role",
    "military_economic_control_role": "military economic-control role",
    "security_governance_gap": "security governance gap",
    "external_pressure_sanctions_active": "active external sanctions pressure",
    "external_pressure_imf_program_active": "IMF program exposure",
    "external_pressure_us_security_shift": "US security shift pressure",
    "economic_fragility_inflation_stress": "inflation stress",
    "economic_fragility_fx_stress": "FX stress",
    "economic_fragility_debt_stress": "debt stress",
    "coup_recency_risk": "recent coup-memory risk",
    "recent_coup_intensity": "recent coup intensity",
    "regime_shift_pressure": "major regime-shift pressure",
    "democratic_backsliding_shift": "recent democratic backsliding",
    "aid_dependence_shift": "aid-dependence shift",
    "trade_dislocation_shift": "trade dislocation shift",
}

TREND_VALUE = {"rising": 1.0, "stable": 0.0, "easing": -1.0}


@dataclass
class EventContribution:
    event_id: str
    event_type: str
    event_date: str
    salience: str
    confidence: str
    contribution: float


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def as_float(value) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def load_events() -> tuple[Path, list[dict]]:
    source = EDITED_EVENTS if EDITED_EVENTS.exists() else CANONICAL_EVENTS
    payload = load_json(source)
    return source, payload.get("events", []) if isinstance(payload, dict) else payload


def live_event_rows() -> list[dict]:
    if not LIVE_EVENTS.exists():
        return []
    payload = load_json(LIVE_EVENTS)
    return payload.get("events", []) if isinstance(payload, dict) else payload


def latest_country_rows() -> dict[str, dict]:
    payload = load_json(COUNTRY_YEAR)
    rows = payload.get("rows", []) if isinstance(payload, dict) else payload
    by_country: dict[str, dict] = {}
    per_country: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        country = row.get("country")
        if not country:
            continue
        per_country[country].append(row)

    for country, country_rows in per_country.items():
        ranked = sorted(country_rows, key=lambda item: int(item.get("year", 0)), reverse=True)
        merged = dict(ranked[0])
        field_years: dict[str, int] = {}
        for row in ranked:
            year = int(row.get("year", 0) or 0)
            for key, value in row.items():
                if key in {"country", "year"}:
                    continue
                if merged.get(key) is None and value is not None:
                    merged[key] = value
                    field_years[key] = year
        if field_years:
            merged["_backfilled_fields"] = {
                key: {"year": year}
                for key, year in field_years.items()
            }
        by_country[country] = merged
    return by_country


def acled_lookup() -> dict[str, dict]:
    payload = load_json(ACLED_INDEX)
    rows = payload.get("rows", payload.get("data", payload.get("countries", []))) if isinstance(payload, dict) else payload
    return {str(row.get("country")): row for row in rows if row.get("country")}


def deed_lookup() -> dict[str, float]:
    rows = live_event_rows()
    deed_weights = {
        "precursor": 0.55,
        "symptom": 1.0,
        "destabilizing": 1.15,
        "resistance": -0.25,
    }
    salience_weights = {
        "high": 1.0,
        "medium": 0.7,
        "med": 0.7,
        "low": 0.35,
    }
    by_country: dict[str, float] = defaultdict(float)
    for row in rows:
        country = str(row.get("country") or "")
        deed_type = str(row.get("deed_type") or "").strip().lower()
        if not country or not deed_type or deed_type == "null":
            continue
        weight = deed_weights.get(deed_type)
        if weight is None:
            continue
        salience = salience_weights.get(str(row.get("salience") or "").strip().lower(), 0.6)
        confidence = normalize_confidence(row.get("confidence"))
        confidence_weight = {
            "high": 1.0,
            "medium": 0.8,
            "low": 0.6,
        }.get(confidence, 0.6)
        by_country[country] += weight * salience * confidence_weight
    return {
        country: round(clamp((1.0 - math.exp(-value / 12.0)) * 100.0), 2)
        for country, value in by_country.items()
        if value > 0
    }


def external_economic_lookup() -> dict[str, dict]:
    if not EXTERNAL_ECONOMIC.exists():
        return {}
    payload = load_json(EXTERNAL_ECONOMIC)
    rows = payload.get("rows", []) if isinstance(payload, dict) else payload
    by_country: dict[str, dict] = {}
    for row in rows:
        country = str(row.get("country") or "").strip()
        panel_date = str(row.get("panel_date") or "")
        if not country or not panel_date:
            continue
        current = by_country.get(country)
        if current is None or panel_date > str(current.get("panel_date") or ""):
            by_country[country] = row
    return by_country


def event_signal_lookup(events: list[dict]) -> dict[str, dict[str, float]]:
    per_country: dict[str, dict[str, object]] = defaultdict(lambda: {
        "oc_actor_events": 0,
        "oc_type_events": 0,
        "stress_events": 0,
        "stress_locations": set(),
    })
    stress_types = {"oc", "conflict", "protest", "coup", "purge"}
    for event in events:
        country = str(event.get("country") or "")
        if not country or country == "Regional":
            continue
        bucket = per_country[country]
        event_type = str(event.get("event_type") or "")
        actors = event.get("actors") or []
        if event_type == "oc":
            bucket["oc_type_events"] += 1
        if any((actor.get("actor_canonical_type") == "organized_crime" or actor.get("actor_type") == "organized_crime") for actor in actors):
            bucket["oc_actor_events"] += 1
        if event_type in stress_types:
            bucket["stress_events"] += 1
            loc = event.get("subnational_location") or event.get("location_text")
            if loc:
                bucket["stress_locations"].add(str(loc).strip())

    out: dict[str, dict[str, float]] = {}
    for country, bucket in per_country.items():
        oc_raw = float(bucket["oc_type_events"]) * 1.0 + float(bucket["oc_actor_events"]) * 0.7
        stress_events = float(bucket["stress_events"])
        spread_raw = stress_events * 0.45 + len(bucket["stress_locations"]) * 1.7
        out[country] = {
            "oc_actor_density": round(clamp((1.0 - math.exp(-oc_raw / 16.0)) * 100.0), 2),
            "territorial_fragmentation_signal": round(clamp((1.0 - math.exp(-spread_raw / 18.0)) * 100.0), 2),
        }
    return out


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError:
        return None


def normalize_confidence(value: str | None) -> str:
    text = str(value or "").strip().lower()
    if text in {"high", "green"}:
        return "high"
    if text in {"medium", "yellow", "med"}:
        return "medium"
    return "low"


def reviewed_state(event: dict) -> str:
    if event.get("human_validated"):
        return "human_validated"
    if event.get("review_status") in HUMAN_REVIEW_STATUSES:
        return "human_reviewed"
    return "machine_only"


def confidence_multiplier(config: dict, event: dict) -> float:
    level = normalize_confidence(event.get("confidence"))
    return float(config["pulse_design"]["confidence_multiplier"].get(level, 0.4))


def salience_multiplier(config: dict, event: dict) -> float:
    level = str(event.get("salience") or "low").lower()
    return float(config["pulse_design"]["salience_multiplier"].get(level, 0.3))


def validation_multiplier(config: dict, event: dict) -> float:
    return float(config["pulse_design"]["human_validation_multiplier"].get(reviewed_state(event), 0.9))


def recency_decay(config: dict, event: dict, now: datetime) -> float:
    event_dt = parse_date(event.get("event_date"))
    if not event_dt:
        return 0.0
    age_days = max((now - event_dt).days, 0)
    short_days = int(config["pulse_design"]["short_window_days"])
    medium_days = int(config["pulse_design"]["medium_window_days"])
    long_days = int(config["pulse_design"]["long_window_days"])
    if age_days <= short_days:
        return 1.0
    if age_days <= medium_days:
        return 0.6
    if age_days <= long_days:
        return 0.25
    return 0.0


def scale_binary(value: float | int | None) -> float | None:
    if value is None:
        return None
    return 100.0 if float(value) >= 1 else 0.0


def scale_unit(value: float | int | None, invert: bool = False) -> float | None:
    if value is None:
        return None
    numeric = float(value)
    if 0.0 <= numeric <= 1.0:
        score = numeric * 100.0
    else:
        score = clamp(numeric)
    return 100.0 - score if invert else score


def scale_wgi(value: float | int | None, invert: bool = False) -> float | None:
    if value is None:
        return None
    numeric = float(value)
    score = ((numeric + 2.5) / 5.0) * 100.0
    score = clamp(score)
    return 100.0 - score if invert else score


def scale_hwi(value: float | int | None) -> float | None:
    if value is None:
        return None
    return clamp((float(value) / 20.0) * 100.0)


def scale_polity(value: float | int | None, invert: bool = False) -> float | None:
    if value is None:
        return None
    numeric = float(value)
    score = ((numeric + 10.0) / 20.0) * 100.0
    score = clamp(score)
    return 100.0 - score if invert else score


def scale_coup_exposure(row: dict) -> float | None:
    attempts = row.get("coup_attempts")
    event = row.get("coup_event")
    if attempts is None and event is None:
        return None
    score = 0.0
    if attempts is not None:
        score += min(float(attempts), 3.0) * 20.0
    if event:
        score += 40.0
    return clamp(score)


def scale_coup_recency_risk(row: dict) -> float | None:
    years = as_float(row.get("time_since_last_coup"))
    if years is None:
        return None
    if years <= 1:
        return 100.0
    if years <= 3:
        return 85.0
    if years <= 5:
        return 70.0
    if years <= 10:
        return 52.0
    if years <= 20:
        return 32.0
    if years <= 35:
        return 18.0
    return 8.0


def scale_recent_coup_intensity(row: dict) -> float | None:
    counts = []
    count_5y = as_float(row.get("coup_count_5y"))
    count_10y = as_float(row.get("coup_count_10y"))
    if count_5y is not None:
        counts.append(min(count_5y, 3.0) / 3.0 * 100.0)
    if count_10y is not None:
        counts.append(min(count_10y, 5.0) / 5.0 * 100.0)
    return round(sum(counts) / len(counts), 2) if counts else None


def scale_regime_shift_pressure(row: dict) -> float | None:
    shift_flag = as_float(row.get("regime_shift_flag"))
    polyarchy_delta = as_float(row.get("polyarchy_delta_1y"))
    breakdown = as_float(row.get("democracy_breakdown"))
    transition = as_float(row.get("democracy_transition"))
    parts = []
    if shift_flag is not None and shift_flag >= 1:
        parts.append(85.0)
    if polyarchy_delta is not None and polyarchy_delta < 0:
        parts.append(clamp(abs(polyarchy_delta) / 0.25 * 100.0))
    if breakdown is not None and breakdown > 0:
        parts.append(100.0)
    if transition is not None and transition < 0:
        parts.append(70.0)
    return round(sum(parts) / len(parts), 2) if parts else None


def scale_democratic_backsliding_shift(row: dict) -> float | None:
    polyarchy_1y = as_float(row.get("polyarchy_delta_1y"))
    repression_shift = as_float(row.get("repression_shift_flag"))
    repression_delta = as_float(row.get("cs_repress_delta_1y"))
    direct_election = as_float(row.get("executive_direct_election"))
    parts = []
    if polyarchy_1y is not None and polyarchy_1y < 0:
        parts.append(clamp(abs(polyarchy_1y) / 0.12 * 100.0))
    if repression_shift is not None and repression_shift >= 1:
        parts.append(78.0)
    if repression_delta is not None and repression_delta > 0:
        parts.append(clamp(repression_delta / 0.3 * 100.0))
    if direct_election is not None and direct_election <= 0:
        parts.append(35.0)
    return round(sum(parts) / len(parts), 2) if parts else None


def scale_aid_dependence_shift(row: dict) -> float | None:
    level = as_float(row.get("oda_received_pct_gni"))
    delta = as_float(row.get("oda_received_delta_3y"))
    parts = []
    if level is not None:
        parts.append(clamp(level / 12.0 * 100.0))
    if delta is not None:
        parts.append(clamp(abs(delta) / 4.0 * 100.0))
    return round(sum(parts) / len(parts), 2) if parts else None


def scale_trade_dislocation_shift(row: dict) -> float | None:
    delta = as_float(row.get("trade_openness_delta_3y"))
    level = as_float(row.get("trade_openness_pct_gdp"))
    parts = []
    if delta is not None:
        parts.append(clamp(abs(delta) / 15.0 * 100.0))
    if level is not None and level < 35.0:
        parts.append(clamp((35.0 - level) / 35.0 * 100.0))
    return round(sum(parts) / len(parts), 2) if parts else None


def scale_acled(country: str, acled: dict[str, dict]) -> float | None:
    row = acled.get(country)
    if not row:
        return None
    return ACLED_LEVEL_SCORE.get(str(row.get("index_level") or "").lower())


def scale_criminality(country: str, acled: dict[str, dict]) -> float | None:
    row = acled.get(country)
    if not row:
        return None
    danger = row.get("danger_ranking")
    fragmentation = row.get("fragmentation_ranking")
    if danger is None and fragmentation is None:
        return None
    parts = []
    if danger is not None:
        parts.append(clamp((26 - float(danger)) / 25.0 * 100.0))
    if fragmentation is not None:
        parts.append(clamp((26 - float(fragmentation)) / 25.0 * 100.0))
    return round(sum(parts) / len(parts), 2) if parts else None


def scale_state_capacity(row: dict) -> float | None:
    parts = []
    composite = row.get("state_capacity_composite")
    if composite is not None:
        try:
            parts.append(clamp(100.0 - float(composite)))
        except (TypeError, ValueError):
            pass
    parts.extend([
        scale_wgi(row.get("wgi_govt_effectiveness"), invert=True),
        scale_wgi(row.get("wgi_rule_of_law"), invert=True),
    ])
    parts = [item for item in parts if item is not None]
    return round(sum(parts) / len(parts), 2) if parts else None


def scale_security_governance_gap(
    country: str,
    row: dict,
    acled: dict[str, dict],
    profiles: dict[str, list[dict]],
) -> float | None:
    state_weakness = scale_state_capacity(row)
    criminality = scale_criminality(country, acled)
    coercive_role = score_military_role_dimension(country, profiles, "domestic_coercion")
    governance_role = score_military_role_dimension(country, profiles, "governance_administration")
    parts = []
    if state_weakness is not None:
        parts.append(state_weakness * 0.50)
    if criminality is not None:
        parts.append(criminality * 0.20)
    role_gaps = []
    if coercive_role is not None:
        role_gaps.append(100.0 - coercive_role)
    if governance_role is not None:
        role_gaps.append(100.0 - governance_role)
    if role_gaps:
        parts.append((sum(role_gaps) / len(role_gaps)) * 0.30)
    if not parts:
        return None
    return round(clamp(sum(parts)), 2)


def scale_violence_history(row: dict) -> float | None:
    parts = [
        scale_unit(row.get("political_violence")),
        scale_unit(row.get("physinteg"), invert=True),
    ]
    parts = [item for item in parts if item is not None]
    return round(sum(parts) / len(parts), 2) if parts else None


def scale_democratic_fragility(row: dict) -> float | None:
    parts = [
        scale_unit(row.get("polyarchy"), invert=True),
        scale_polity(row.get("polity2"), invert=True),
        scale_wgi(row.get("wgi_political_stability"), invert=True),
    ]
    parts = [item for item in parts if item is not None]
    return round(sum(parts) / len(parts), 2) if parts else None


def scale_governance_erosion(row: dict) -> float | None:
    parts = [
        scale_wgi(row.get("wgi_control_corruption"), invert=True),
        scale_wgi(row.get("wgi_govt_effectiveness"), invert=True),
        scale_wgi(row.get("wgi_rule_of_law"), invert=True),
    ]
    parts = [item for item in parts if item is not None]
    return round(sum(parts) / len(parts), 2) if parts else None


def scale_military_constraint_weakness(row: dict) -> float | None:
    value = row.get("mil_constrain")
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    minimum = -2.5
    maximum = 2.5
    return round(clamp((maximum - numeric) / (maximum - minimum) * 100.0), 2)


def scale_regime_authoritarianism(row: dict) -> float | None:
    value = row.get("regime_type")
    if value is None:
        return None
    mapping = {
        0: 100.0,
        1: 78.0,
        2: 34.0,
        3: 10.0,
    }
    try:
        key = int(float(value))
    except (TypeError, ValueError):
        return None
    return mapping.get(key)


def mission_profiles() -> dict[str, list[dict]]:
    if not MISSION_PROFILES.exists():
        return {}
    payload = load_json(MISSION_PROFILES)
    return payload if isinstance(payload, dict) else {}


def role_dimension_weight(text: str) -> dict[str, float]:
    lowered = text.lower()
    dims = {
        "domestic_coercion": 0.0,
        "governance_administration": 0.0,
        "economic_control": 0.0,
        "external_defense": 0.0,
    }
    if "no standing army" in lowered:
        return dims
    if any(key in lowered for key in [
        "mass arrests", "protest suppression", "domestic policing", "joint patrol",
        "internal security", "internal armed conflict", "counter-insurgency",
        "counter-narcotics", "anti-gang", "gang containment", "states of emergency",
        "prison", "civil society repression", "organized-crime", "border enforcement",
        "migration containment"
    ]):
        dims["domestic_coercion"] = 1.0
    if any(key in lowered for key in [
        "infrastructure", "administrative", "mission support", "border patrol",
        "canal security", "oil field protection", "resource security", "base hosting",
        "public security", "governance", "intelligence mandate"
    ]):
        dims["governance_administration"] = max(dims["governance_administration"], 0.85)
    if any(key in lowered for key in [
        "economic empire", "infrastructure control", "illicit mining protection",
        "resource security"
    ]):
        dims["economic_control"] = 1.0
    if any(key in lowered for key in [
        "external defence", "sovereignty", "peacekeeping", "maritime patrol",
        "territorial presence", "garrison support"
    ]):
        dims["external_defense"] = 0.35
    if any(key in lowered for key in [
        "regime security", "political role", "political pillar", "counterintelligence",
        "intelligence", "coup-proofing"
    ]):
        dims["domestic_coercion"] = max(dims["domestic_coercion"], 1.0)
        dims["governance_administration"] = max(dims["governance_administration"], 0.9)
    return dims


def score_military_role_profile(country: str, profiles: dict[str, list[dict]]) -> float | None:
    roles = profiles.get(country) or []
    if not roles:
        return None

    status_weight = {
        "primary": 1.0,
        "expanded": 1.0,
        "controversial": 0.95,
        "active": 0.7,
        "routine": 0.35,
    }

    def role_weight(text: str) -> float:
        lowered = text.lower()
        if "no standing army" in lowered:
            return 0.0
        if any(key in lowered for key in [
            "regime security", "political role", "political pillar", "intelligence",
            "counterintelligence", "domestic policing", "prison", "infrastructure",
            "economic empire", "mass arrests", "protest suppression",
            "civil society repression", "military governance role"
        ]):
            return 1.0
        if any(key in lowered for key in [
            "internal security", "internal armed conflict", "counter-insurgency",
            "counter-narcotics", "anti-gang", "states of emergency",
            "organized-crime", "gang containment", "resource security",
            "joint patrol", "migration containment"
        ]):
            return 0.82
        if any(key in lowered for key in [
            "border", "migration", "maritime", "canal security", "oil field protection",
            "mission support", "base hosting"
        ]):
            return 0.58
        if any(key in lowered for key in [
            "peacekeeping", "external defence", "disaster relief", "civil emergency",
            "territorial presence", "garrison support"
        ]):
            return 0.18
        return 0.35

    weighted = []
    for item in roles:
        role = str(item.get("role") or "")
        status = str(item.get("status") or "routine").lower()
        weighted.append(role_weight(role) * status_weight.get(status, 0.35))

    if not weighted:
        return None
    raw = sum(weighted)
    return round(clamp((raw / 4.0) * 100.0), 2)


def score_military_role_dimension(country: str, profiles: dict[str, list[dict]], dimension: str) -> float | None:
    roles = profiles.get(country) or []
    if not roles:
        return None
    status_weight = {
        "primary": 1.0,
        "expanded": 1.0,
        "controversial": 0.95,
        "active": 0.7,
        "routine": 0.35,
    }
    weighted = []
    for item in roles:
        role = str(item.get("role") or "")
        status = str(item.get("status") or "routine").lower()
        dims = role_dimension_weight(role)
        dim_weight = dims.get(dimension, 0.0)
        if dim_weight <= 0:
            continue
        weighted.append(dim_weight * status_weight.get(status, 0.35))
    if not weighted:
        return 0.0
    divisor = {
        "domestic_coercion": 2.4,
        "governance_administration": 2.2,
        "economic_control": 1.6,
        "external_defense": 2.5,
    }.get(dimension, 2.0)
    return round(clamp((sum(weighted) / divisor) * 100.0), 2)


def structural_input_score(
    input_code: str,
    country: str,
    row: dict,
    acled: dict[str, dict],
    deed: dict[str, float],
    event_signals: dict[str, dict[str, float]],
    profiles: dict[str, list[dict]],
    external_signals: dict[str, dict],
) -> tuple[float | None, str]:
    country_signals = event_signals.get(country, {})
    external_row = external_signals.get(country, {})
    mapping = {
        "m3_conscription": (scale_binary(row.get("m3_conscription")), "country_year.m3_conscription"),
        "m3_military_veto": (scale_binary(row.get("m3_mil_veto")), "country_year.m3_mil_veto"),
        "m3_impunity": (scale_binary(row.get("m3_mil_impunity")), "country_year.m3_mil_impunity"),
        "m3_public_security_role": (scale_binary(row.get("m3_mil_crime_police")), "country_year.m3_mil_crime_police"),
        "m3_military_economic_role": (scale_binary(row.get("m3_mil_eco")), "country_year.m3_mil_eco"),
        "executive_military_history": (scale_unit(row.get("mil_exec")), "country_year.mil_exec"),
        "historical_coup_exposure": (scale_coup_exposure(row), "country_year.coup_attempts/coup_event"),
        "acled_conflict_level": (scale_acled(country, acled), "acled_index.index_level"),
        "criminality_baseline": (scale_criminality(country, acled), "acled_index.danger_ranking/fragmentation_ranking"),
        "oc_actor_density": (country_signals.get("oc_actor_density"), "review.events.actors/event_type"),
        "territorial_fragmentation_signal": (country_signals.get("territorial_fragmentation_signal"), "review.events.locations"),
        "territorial_state_capacity": (scale_state_capacity(row), "country_year.state_capacity_composite/wgi_govt_effectiveness/wgi_rule_of_law"),
        "security_governance_gap": (scale_security_governance_gap(country, row, acled, profiles), "derived.state_capacity+criminality+coercive_role_gap"),
        "violence_history": (scale_violence_history(row), "country_year.political_violence/physinteg"),
        "democratic_fragility": (scale_democratic_fragility(row), "country_year.polyarchy/polity2/wgi_political_stability"),
        "governance_erosion": (scale_governance_erosion(row), "country_year.wgi_control_corruption/wgi_govt_effectiveness/wgi_rule_of_law"),
        "deed_erosion_signal": (deed.get(country), "data.events.deed_type"),
        "military_constraint_weakness": (scale_military_constraint_weakness(row), "country_year.mil_constrain"),
        "regime_authoritarianism": (scale_regime_authoritarianism(row), "country_year.regime_type"),
        "military_governance_role": (score_military_role_profile(country, profiles), "config.military_role_profiles"),
        "military_domestic_coercion_role": (score_military_role_dimension(country, profiles, "domestic_coercion"), "config.military_role_profiles.domestic_coercion"),
        "military_governance_administration_role": (score_military_role_dimension(country, profiles, "governance_administration"), "config.military_role_profiles.governance_administration"),
        "military_economic_control_role": (score_military_role_dimension(country, profiles, "economic_control"), "config.military_role_profiles.economic_control"),
        "external_pressure_sanctions_active": (as_float(external_row.get("external_pressure_sanctions_active")), "modeling.external_economic_country_month.external_pressure_sanctions_active"),
        "external_pressure_imf_program_active": (as_float(external_row.get("external_pressure_imf_program_active")), "modeling.external_economic_country_month.external_pressure_imf_program_active"),
        "external_pressure_us_security_shift": (abs(as_float(external_row.get("external_pressure_us_security_shift")) or 0.0), "modeling.external_economic_country_month.external_pressure_us_security_shift"),
        "economic_fragility_inflation_stress": (as_float(external_row.get("economic_fragility_inflation_stress")), "modeling.external_economic_country_month.economic_fragility_inflation_stress"),
        "economic_fragility_fx_stress": (as_float(external_row.get("economic_fragility_fx_stress")), "modeling.external_economic_country_month.economic_fragility_fx_stress"),
        "economic_fragility_debt_stress": (as_float(external_row.get("economic_fragility_debt_stress")), "modeling.external_economic_country_month.economic_fragility_debt_stress"),
        "coup_recency_risk": (scale_coup_recency_risk(row), "country_year.time_since_last_coup"),
        "recent_coup_intensity": (scale_recent_coup_intensity(row), "country_year.coup_count_5y/coup_count_10y"),
        "regime_shift_pressure": (scale_regime_shift_pressure(row), "country_year.regime_shift_flag/polyarchy_delta_1y/democracy_breakdown"),
        "democratic_backsliding_shift": (scale_democratic_backsliding_shift(row), "country_year.polyarchy_delta_1y/cs_repress_delta_1y/repression_shift_flag"),
        "aid_dependence_shift": (scale_aid_dependence_shift(row), "country_year.oda_received_pct_gni/oda_received_delta_3y"),
        "trade_dislocation_shift": (scale_trade_dislocation_shift(row), "country_year.trade_openness_pct_gdp/trade_openness_delta_3y"),
        "historical_us_security_exposure": (None, "not_yet_available"),
        "alliance_posture": (None, "not_yet_available"),
        "arms_dependence_profile": (None, "not_yet_available"),
        "security_partner_depth": (None, "not_yet_available"),
    }
    return mapping.get(input_code, (None, "unknown_input"))


def baseline_monitor(
    monitor: dict,
    country: str,
    row: dict,
    acled: dict[str, dict],
    deed: dict[str, float],
    event_signals: dict[str, dict[str, float]],
    profiles: dict[str, list[dict]],
    external_signals: dict[str, dict],
) -> tuple[float, list[dict], str]:
    components = []
    for input_code in monitor.get("baseline_inputs", []):
        value, source = structural_input_score(input_code, country, row, acled, deed, event_signals, profiles, external_signals)
        components.append({
            "input": input_code,
            "label": INPUT_LABELS.get(input_code, input_code),
            "source": source,
            "score": value,
            "available": value is not None,
        })
    available_scores = [item["score"] for item in components if item["score"] is not None]
    if available_scores:
        return round(sum(available_scores) / len(available_scores), 2), components, "observed"
    return 50.0, components, "neutral_fallback"


def pulse_monitor(config: dict, monitor: dict, country: str, events: list[dict], now: datetime) -> tuple[float, dict, list[dict]]:
    allowed_types = set(monitor.get("pulse_event_types", []))
    type_weights = {str(k): float(v) for k, v in monitor.get("pulse_weights", {}).items()}
    window_days = int(config["pulse_design"]["long_window_days"])

    raw_contributions: list[EventContribution] = []
    short_raw = 0.0
    medium_raw = 0.0
    long_raw = 0.0
    dominant_totals: dict[str, float] = defaultdict(float)

    for event in events:
        if str(event.get("country") or "") != country:
            continue
        event_type = str(event.get("event_type") or event.get("type") or "")
        if event_type not in allowed_types:
            continue
        event_dt = parse_date(event.get("event_date") or event.get("date"))
        if not event_dt:
            continue
        age_days = max((now - event_dt).days, 0)
        if age_days > window_days:
            continue
        recency = recency_decay(config, event, now)
        if recency <= 0:
            continue
        contribution = (
            type_weights.get(event_type, 0.0)
            * salience_multiplier(config, event)
            * confidence_multiplier(config, event)
            * validation_multiplier(config, event)
            * recency
        )
        if contribution <= 0:
            continue
        raw_contributions.append(
            EventContribution(
                event_id=str(event.get("event_id") or event.get("id")),
                event_type=event_type,
                event_date=str(event.get("event_date") or event.get("date")),
                salience=str(event.get("salience") or ""),
                confidence=normalize_confidence(event.get("confidence")),
                contribution=round(contribution, 4),
            )
        )
        dominant_totals[event_type] += contribution
        long_raw += contribution
        if age_days <= int(config["pulse_design"]["short_window_days"]):
            short_raw += contribution
        if age_days <= int(config["pulse_design"]["medium_window_days"]):
            medium_raw += contribution

    normalized = round(clamp((1.0 - math.exp(-long_raw)) * 100.0), 2)
    if short_raw > max(medium_raw * 0.8, 0.1):
        trend = "rising"
    elif medium_raw > 0.15 and short_raw < medium_raw * 0.4:
        trend = "easing"
    else:
        trend = "stable"

    dominant_signal = None
    if dominant_totals:
        dominant_signal = max(dominant_totals.items(), key=lambda item: item[1])[0]

    summary = {
        "raw_pulse": round(long_raw, 4),
        "pulse_score": normalized,
        "trend_label": trend,
        "dominant_recent_signal": dominant_signal,
        "window_days": window_days,
        "short_window_raw": round(short_raw, 4),
        "medium_window_raw": round(medium_raw, 4),
        "event_count": len(raw_contributions),
    }
    top_events = sorted(raw_contributions, key=lambda item: item.contribution, reverse=True)[:5]
    return normalized, summary, [item.__dict__ for item in top_events]


def score_level(config: dict, score: float) -> str:
    for item in config.get("predictive_layers", {}).get("score_levels", []):
        if score >= float(item.get("min", 0)):
            return str(item.get("label", "low"))
    return "low"


def fit_affine_transform(pairs: list[tuple[float, float]]) -> tuple[float, float]:
    if len(pairs) < 2:
        return 1.0, 0.0
    xs = [x for x, _ in pairs]
    ys = [y for _, y in pairs]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    var_x = sum((x - mean_x) ** 2 for x in xs)
    if var_x <= 1e-9:
        return 1.0, mean_y - mean_x
    cov_xy = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
    slope = cov_xy / var_x
    intercept = mean_y - slope * mean_x
    return slope, intercept


def apply_anchor_calibration(config: dict, rows: list[dict]) -> dict:
    calibration = config.get("calibration", {})
    anchor_scores = calibration.get("anchor_scores", {})
    by_country = {row["country"]: row for row in rows}
    transforms = {}
    for construct_code, anchors in anchor_scores.items():
        if construct_code == "overall_risk":
            continue
        pairs = []
        for country, target in anchors.items():
            row = by_country.get(country)
            if not row:
                continue
            construct = next((item for item in row["risk_constructs"] if item["code"] == construct_code), None)
            if construct is None:
                continue
            pairs.append((float(construct["score"]), float(target)))
        slope, intercept = fit_affine_transform(pairs)
        transforms[construct_code] = {
            "slope": round(slope, 6),
            "intercept": round(intercept, 6),
            "anchor_count": len(pairs),
        }

    for row in rows:
        for construct in row["risk_constructs"]:
            transform = transforms.get(construct["code"])
            raw_score = float(construct["score"])
            if not transform:
                calibrated = raw_score
            else:
                calibrated = clamp(raw_score * transform["slope"] + transform["intercept"])
            construct["raw_score"] = round(raw_score, 2)
            construct["score"] = round(calibrated, 2)
            construct["level"] = score_level(config, calibrated)
        row["predictive_summary"] = build_predictive_summary(config, row["risk_constructs"], row["country"])

    overall_pairs = []
    overall_anchors = anchor_scores.get("overall_risk", {})
    for country, target in overall_anchors.items():
        row = by_country.get(country)
        if not row:
            continue
        overall_pairs.append((float(row["predictive_summary"]["overall_risk_score"]), float(target)))
    overall_slope, overall_intercept = fit_affine_transform(overall_pairs)
    transforms["overall_risk"] = {
        "slope": round(overall_slope, 6),
        "intercept": round(overall_intercept, 6),
        "anchor_count": len(overall_pairs),
    }
    for row in rows:
        raw_overall = float(row["predictive_summary"]["overall_risk_score"])
        calibrated_overall = clamp(raw_overall * overall_slope + overall_intercept)
        row["predictive_summary"]["raw_overall_risk_score"] = round(raw_overall, 2)
        row["predictive_summary"]["overall_risk_score"] = round(calibrated_overall, 2)
        row["predictive_summary"]["overall_risk_level"] = score_level(config, calibrated_overall)
    return {
        "method": calibration.get("method", "none"),
        "transforms": transforms,
        "anchor_scores": anchor_scores,
    }


def resolve_construct_component(
    component: dict,
    country: str,
    structural_row: dict,
    acled: dict[str, dict],
    deed: dict[str, float],
    event_signals: dict[str, dict[str, float]],
    monitor_index: dict[str, dict],
    profiles: dict[str, list[dict]],
    external_signals: dict[str, dict],
) -> tuple[float | None, str, str | None]:
    kind = str(component.get("kind"))
    code = str(component.get("code"))
    if kind == "monitor_composite":
        monitor = monitor_index.get(code)
        if not monitor:
            return None, code, None
        return float(monitor.get("composite_score", 0.0)), monitor.get("label", code), str(monitor.get("trend_label") or "stable")
    if kind == "monitor_pulse":
        monitor = monitor_index.get(code)
        if not monitor:
            return None, code, None
        return float(monitor.get("pulse_score", 0.0)), f"{monitor.get('label', code)} pulse", str(monitor.get("trend_label") or "stable")
    if kind == "structural_input":
        value, _source = structural_input_score(code, country, structural_row, acled, deed, event_signals, profiles, external_signals)
        return value, INPUT_LABELS.get(code, code), None
    return None, code, None


def construct_watchpoints(construct_code: str, drivers: list[dict], monitor_index: dict[str, dict]) -> list[str]:
    dominant_signals = [
        monitor.get("dominant_recent_signal")
        for monitor in monitor_index.values()
        if monitor.get("dominant_recent_signal")
    ]
    signal_text = dominant_signals[0] if dominant_signals else "recent security reporting"
    if construct_code == "regime_vulnerability":
        return [
            f"watch for whether {signal_text} starts affecting elite cohesion or executive authority",
            "watch for security-force intervention in politics, emergency powers, or abrupt command changes",
        ]
    if construct_code == "militarization":
        return [
            "watch for the armed forces moving deeper into domestic security or administrative roles",
            "watch for new legal or operational mandates that normalize coercive institutions in civilian governance",
        ]
    return [
        "watch for criminal, insurgent, or protest dynamics spreading geographically or institutionally",
        "watch for evidence that state capacity is fragmenting across police, military, and local authorities",
    ]


def join_labels(labels: list[str]) -> str:
    clean = [str(label).strip() for label in labels if str(label).strip()]
    if not clean:
        return ""
    if len(clean) == 1:
        return clean[0]
    if len(clean) == 2:
        return f"{clean[0]} and {clean[1]}"
    return f"{', '.join(clean[:-1])}, and {clean[-1]}"


def construct_condition_line(code: str, country: str, level: str, trend_label: str, driver_labels: list[str]) -> str:
    drivers = join_labels(driver_labels[:3])
    if code == "regime_vulnerability":
        base = f"{country} shows {level} near-term regime vulnerability"
        if trend_label == "rising":
            return f"{base}, with pressure building around {drivers}." if drivers else f"{base}, and the direction of pressure is rising."
        if trend_label == "easing":
            return f"{base}, but the immediate pressure has eased somewhat despite continued strain in {drivers}." if drivers else f"{base}, though the immediate pressure has eased somewhat."
        return f"{base}, centered on {drivers}." if drivers else f"{base}, with strain concentrated in the current governing order."
    if code == "militarization":
        base = f"{country} currently sits at a {level} level of militarization"
        if trend_label == "rising":
            return f"{base}, and the military role is expanding most clearly through {drivers}." if drivers else f"{base}, and the military role is still expanding."
        if trend_label == "easing":
            return f"{base}, though the recent tempo has moderated even as {drivers} remain important." if drivers else f"{base}, though the recent tempo has moderated."
        return f"{base}, with the strongest signal coming from {drivers}." if drivers else f"{base}, with military influence embedded in core governance roles."
    if code == "security_fragmentation":
        base = f"{country} faces a {level} level of security fragmentation"
        if trend_label == "rising":
            return f"{base}, with coercive competition spreading through {drivers}." if drivers else f"{base}, and the coercive environment is still becoming more dispersed."
        if trend_label == "easing":
            return f"{base}, but the current pattern is less expansionary than before even though {drivers} still matter." if drivers else f"{base}, though the pace of fragmentation has eased for now."
        return f"{base}, shaped most by {drivers}." if drivers else f"{base}, with fragmentation concentrated in the current security environment."
    return f"{country} shows {level} concern, driven by {drivers}." if drivers else f"{country} shows {level} concern."


def construct_implication_line(code: str, country: str, trend_label: str, drivers: list[dict]) -> str:
    dominant = (drivers[0]["label"] if drivers else "").replace(" pulse", "")
    if code == "regime_vulnerability":
        if trend_label == "rising":
            return f"If this pattern persists, governing authority in {country} is more likely to face institutional contestation, coercive overreach, or sharper elite-security dependence."
        if dominant:
            return f"The main implication is that {country}'s governing order remains vulnerable where {dominant.lower()} is already weakening routine accountability."
        return f"The main implication is that strain in {country}'s governing order remains politically consequential."
    if code == "militarization":
        if dominant:
            return f"The key question is whether {dominant.lower()} becomes further normalized as an ordinary state function in {country}."
        return f"The key question is whether military roles in {country} continue to move beyond defense into routine governance."
    if code == "security_fragmentation":
        if trend_label == "rising":
            return f"The practical risk is that violence, criminal competition, or coercive stress in {country} becomes harder to contain geographically and institutionally."
        if dominant:
            return f"The practical risk is that {dominant.lower()} keeps security stress in {country} dispersed rather than contained."
        return f"The practical risk is that coercive stress in {country} remains unevenly distributed across territory and institutions."
    return ""


def build_risk_constructs(
    config: dict,
    country: str,
    structural_row: dict,
    acled: dict[str, dict],
    deed: dict[str, float],
    event_signals: dict[str, dict[str, float]],
    monitor_rows: list[dict],
    profiles: dict[str, list[dict]],
    external_signals: dict[str, dict],
) -> list[dict]:
    monitor_index = {str(item["code"]): item for item in monitor_rows}
    constructs = []
    for construct in config.get("risk_constructs", []):
        weighted_score = 0.0
        total_weight = 0.0
        trend_score = 0.0
        trend_weight = 0.0
        components = []
        for component in construct.get("component_weights", []):
            weight = float(component.get("weight", 0.0))
            value, label, trend = resolve_construct_component(component, country, structural_row, acled, deed, event_signals, monitor_index, profiles, external_signals)
            contribution = None if value is None else round(value * weight, 2)
            components.append({
                "kind": component.get("kind"),
                "code": component.get("code"),
                "label": label,
                "weight": weight,
                "score": None if value is None else round(value, 2),
                "weighted_contribution": contribution,
                "trend_label": trend,
            })
            if value is not None:
                weighted_score += value * weight
                total_weight += weight
            if trend is not None:
                trend_score += TREND_VALUE.get(trend, 0.0) * weight
                trend_weight += weight

        score = round(weighted_score / total_weight, 2) if total_weight else 50.0
        avg_trend = trend_score / trend_weight if trend_weight else 0.0
        if avg_trend > 0.2:
            trend_label = "rising"
        elif avg_trend < -0.2:
            trend_label = "easing"
        else:
            trend_label = "stable"

        drivers = sorted(
            [item for item in components if item["weighted_contribution"] is not None],
            key=lambda item: item["weighted_contribution"],
            reverse=True,
        )[:3]
        driver_labels = [item["label"] for item in drivers]
        level = score_level(config, score)
        condition = construct_condition_line(str(construct.get("code")), country, level, trend_label, driver_labels)
        implication = construct_implication_line(str(construct.get("code")), country, trend_label, drivers)
        summary_text = " ".join(part for part in [condition, implication] if part).strip()
        constructs.append({
            "code": construct.get("code"),
            "label": construct.get("label"),
            "goal": construct.get("goal"),
            "score": score,
            "level": level,
            "trend_label": trend_label,
            "horizon_days": int(construct.get("horizon_days", 90)),
            "components": components,
            "drivers": drivers,
            "summary_text": summary_text,
            "watchpoints": construct_watchpoints(str(construct.get("code")), drivers, monitor_index),
        })
    return constructs


def build_predictive_summary(config: dict, constructs: list[dict], country: str) -> dict:
    weights = config.get("predictive_layers", {}).get("overall_risk_weights", {})
    total = 0.0
    total_weight = 0.0
    for construct in constructs:
        weight = float(weights.get(construct["code"], 0.0))
        if weight <= 0:
            continue
        total += construct["score"] * weight
        total_weight += weight
    overall_score = round(total / total_weight, 2) if total_weight else 50.0
    leading = max(constructs, key=lambda item: item["score"]) if constructs else None
    secondary = None
    if len(constructs) > 1:
        secondary = sorted(constructs, key=lambda item: item["score"], reverse=True)[1]
    summary_text = ""
    if leading:
        leading_drivers = []
        seen_driver_keys = set()
        for driver in leading["drivers"]:
            clean_label = str(driver["label"]).replace(" pulse", "")
            clean_key = clean_label.strip().casefold()
            if clean_key not in seen_driver_keys:
                leading_drivers.append(clean_label)
                seen_driver_keys.add(clean_key)
        parts = [f"{country} currently sits in the {score_level(config, overall_score)} overall risk tier."]
        lead_line = f"The strongest near-term pressure comes from {leading['label'].lower()}"
        if leading.get("trend_label") == "rising":
            lead_line += ", and it is still rising"
        elif leading.get("trend_label") == "easing":
            lead_line += ", though it has eased somewhat recently"
        if leading_drivers:
            lead_line += f", especially through {join_labels(leading_drivers[:2]).lower()}"
        lead_line += "."
        parts.append(lead_line)
        if secondary and (secondary["score"] >= 45 or leading["score"] - secondary["score"] <= 12):
            parts.append(
                f"A second layer of pressure comes from {secondary['label'].lower()}, which remains {secondary['trend_label']} over the next {secondary['horizon_days']} days."
            )
        summary_text = " ".join(parts)
    return {
        "overall_risk_score": overall_score,
        "overall_risk_level": score_level(config, overall_score),
        "leading_construct": leading["code"] if leading else None,
        "leading_label": leading["label"] if leading else None,
        "leading_trend": leading["trend_label"] if leading else "stable",
        "regime_vulnerability_score": next((item["score"] for item in constructs if item["code"] == "regime_vulnerability"), None),
        "summary_text": summary_text,
        "watchpoints": leading["watchpoints"][:2] if leading else [],
    }


def build_country_rows(config: dict, structural_rows: dict[str, dict], acled: dict[str, dict], events: list[dict]) -> list[dict]:
    now = datetime.now(UTC)
    profiles = mission_profiles()
    deed = deed_lookup()
    event_signals = event_signal_lookup(events)
    external_signals = external_economic_lookup()
    countries = sorted({
        country
        for country in set(structural_rows.keys()) | {str(ev.get("country")) for ev in events if ev.get("country")}
        if country and country != "Regional"
    })
    rows = []
    for country in countries:
        structural = structural_rows.get(country, {})
        monitors = []
        for monitor in config.get("country_monitors", []):
            baseline_score, baseline_components, baseline_mode = baseline_monitor(monitor, country, structural, acled, deed, event_signals, profiles, external_signals)
            pulse_score, pulse_summary, top_events = pulse_monitor(config, monitor, country, events, now)
            composite = round(
                baseline_score * float(monitor.get("baseline_weight", 0.5))
                + pulse_score * float(monitor.get("pulse_weight", 0.5)),
                2,
            )
            monitors.append({
                "code": monitor.get("code"),
                "label": monitor.get("label"),
                "goal": monitor.get("goal"),
                "baseline_score": baseline_score,
                "pulse_score": pulse_score,
                "composite_score": composite,
                "trend_label": pulse_summary["trend_label"],
                "dominant_recent_signal": pulse_summary["dominant_recent_signal"],
                "baseline_mode": baseline_mode,
                "baseline_components": baseline_components,
                "pulse_summary": pulse_summary,
                "top_pulse_events": top_events,
            })

        constructs = build_risk_constructs(config, country, structural, acled, deed, event_signals, monitors, profiles, external_signals)
        predictive_summary = build_predictive_summary(config, constructs, country)
        rows.append({
            "country": country,
            "generated_at": now.isoformat(),
            "monitors": monitors,
            "risk_constructs": constructs,
            "predictive_summary": predictive_summary,
        })
    calibration_meta = apply_anchor_calibration(config, rows)
    for row in rows:
        row["calibration"] = {
            "method": calibration_meta["method"],
            "applied": True,
        }
    return rows, calibration_meta


def main(output: Path = OUT) -> None:
    config = load_json(MODEL_CONFIG)
    structural_rows = latest_country_rows()
    acled = acled_lookup()
    source_path, events = load_events()
    country_rows, calibration_meta = build_country_rows(config, structural_rows, acled, events)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "generation_method": "layered_country_risk_v0_2",
        "status": "predictive_scaffold",
        "source_files": {
            "model_config": str(MODEL_CONFIG.relative_to(ROOT)),
            "mission_profiles": str(MISSION_PROFILES.relative_to(ROOT)),
            "structural_country_year": str(COUNTRY_YEAR.relative_to(ROOT)),
            "acled_index": str(ACLED_INDEX.relative_to(ROOT)),
            "event_source": str(source_path.relative_to(ROOT)),
        },
        "calibration": calibration_meta,
        "count": len(country_rows),
        "countries": country_rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote country monitors to {output}")
    print(f"Country rows generated: {len(country_rows)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build SENTINEL layered country monitors and predictive constructs")
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    main(args.output)
