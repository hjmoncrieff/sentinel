#!/usr/bin/env python3
"""
Build canonical public country dossiers from structural, monitor, and context rows.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
COUNTRY_YEAR = ROOT / "data" / "cleaned" / "country_year.json"
COUNTRY_MONITORS = ROOT / "data" / "published" / "country_monitors.json"
COUNTRY_CONTEXT = ROOT / "data" / "published" / "country_context.json"
COUNTRY_MONTH_PANEL = ROOT / "data" / "modeling" / "country_month_panel.json"
STATIC_LATENT = ROOT / "data" / "modeling" / "static_latent_scores_v0.json"
OUT = ROOT / "data" / "published" / "country_dossiers.json"

CANONICAL_COUNTRIES = [
    ("Brazil", "BR", "BRA", "Brazil"),
    ("Colombia", "CO", "COL", "Andean"),
    ("Mexico", "MX", "MEX", "Mexico"),
    ("Venezuela", "VE", "VEN", "Andean"),
    ("Chile", "CL", "CHL", "Southern Cone"),
    ("Argentina", "AR", "ARG", "Southern Cone"),
    ("Peru", "PE", "PER", "Andean"),
    ("Ecuador", "EC", "ECU", "Andean"),
    ("Bolivia", "BO", "BOL", "Andean"),
    ("Cuba", "CU", "CUB", "Caribbean"),
    ("Honduras", "HN", "HND", "Central America"),
    ("Guatemala", "GT", "GTM", "Central America"),
    ("El Salvador", "SV", "SLV", "Central America"),
    ("Nicaragua", "NI", "NIC", "Central America"),
    ("Paraguay", "PY", "PRY", "Southern Cone"),
    ("Uruguay", "UY", "URY", "Southern Cone"),
    ("Haiti", "HT", "HTI", "Caribbean"),
    ("Dominican Republic", "DO", "DOM", "Caribbean"),
    ("Panama", "PA", "PAN", "Central America"),
    ("Costa Rica", "CR", "CRI", "Central America"),
    ("Jamaica", "JM", "JAM", "Caribbean"),
    ("Trinidad and Tobago", "TT", "TTO", "Caribbean"),
    ("Guyana", "GY", "GUY", "Caribbean"),
    ("Suriname", "SR", "SUR", "Caribbean"),
    ("Belize", "BZ", "BLZ", "Central America"),
]

CARD_FIELDS = [
    "polyarchy",
    "mil_constrain",
    "mil_exec",
    "wgi_rule_of_law",
    "mil_exp_pct_gdp",
    "inflation_consumer_prices_pct",
]

CARD_META = {
    "polyarchy": ("Polyarchy", "index"),
    "mil_constrain": ("Military Constraint", "index"),
    "mil_exec": ("Military Executive Entanglement", "index"),
    "wgi_rule_of_law": ("Rule of Law", "index"),
    "mil_exp_pct_gdp": ("Military Spending", "percent"),
    "inflation_consumer_prices_pct": ("Inflation", "percent"),
}

PREDICTIVE_CONSTRUCT_META = {
    "regime_vulnerability": "Regime Vulnerability",
    "militarization": "Militarization",
    "security_fragmentation": "Security Fragmentation",
}

CONTEXT_DEFAULTS = {
    "capital": "",
    "regime": "",
    "cmr_status": "",
    "cmr_class": "",
    "note": "",
    "key_positions": [],
    "country_watch": "",
    "special_profile_id": None,
}

NEXT_ELECTION_DEFAULT = {
    "date": "1900-01-01",
    "type": "unknown",
}


def _now_z() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_timestamp(value: object) -> str:
    if not isinstance(value, str) or not value:
        return ""
    normalized = value.strip()
    if normalized.endswith("Z") and len(normalized) == 20:
        return normalized
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        return normalized
    return parsed.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _string_or_empty(value: object) -> str:
    if value in (None, ""):
        return ""
    return str(value)


def _as_float(value) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _extract_rows(payload) -> list[dict]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("rows", "countries"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    return []


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def load_context_rows(path: Path = COUNTRY_CONTEXT) -> list[dict]:
    if not path.exists():
        return []
    return _extract_rows(load_json(path))


def load_optional_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return _extract_rows(load_json(path))


def _max_event_date(monitor_row: dict) -> str | None:
    dates: list[str] = []
    for event in monitor_row.get("top_pulse_events", []) or []:
        event_date = event.get("event_date") or event.get("date")
        if isinstance(event_date, str) and len(event_date) == 10:
            dates.append(event_date)
    return max(dates) if dates else None


def _series_for_field(country_rows: list[dict], field: str) -> list[float]:
    series: list[tuple[int, float]] = []
    for row in sorted(country_rows, key=lambda item: _as_int(item.get("year")) or -1):
        value = _as_float(row.get(field))
        year = _as_int(row.get("year"))
        if value is None or year is None:
            continue
        series.append((year, value))
    return [value for _, value in series]


def _merge_structural_rows(structural_rows) -> dict[str, dict]:
    merged_by_country: dict[str, dict] = {}
    rows = _extract_rows(structural_rows)
    for country, iso2, iso3, subregion in CANONICAL_COUNTRIES:
        country_rows = [row for row in rows if row.get("country") == country]
        ranked = sorted(
            country_rows,
            key=lambda item: _as_int(item.get("year")) or -1,
            reverse=True,
        )
        merged = {
            "country": country,
            "iso2": iso2,
            "iso3": iso3,
            "subregion": subregion,
            "year": None,
            "_field_years": {},
            "_series": {},
        }
        if ranked:
            merged["year"] = _as_int(ranked[0].get("year"))
        for field in ("iso2", "iso3", "subregion"):
            for row in ranked:
                value = row.get(field)
                if value not in (None, ""):
                    merged[field] = value
                    break
        for field in CARD_FIELDS:
            merged["_series"][field] = _series_for_field(country_rows, field)
            for row in ranked:
                value = row.get(field)
                if value in (None, ""):
                    continue
                merged[field] = value
                merged["_field_years"][field] = _as_int(row.get("year"))
                break
        merged_by_country[country] = merged
    return merged_by_country


def _index_country_rows(rows_payload) -> dict[str, dict]:
    rows = _extract_rows(rows_payload)
    indexed: dict[str, dict] = {}
    for row in rows:
        country = row.get("country")
        if isinstance(country, str) and country and country not in indexed:
            indexed[country] = row
    return indexed


def _display_value(code: str, value) -> str:
    numeric = _as_float(value)
    if numeric is None:
        return "n/a"
    if code in {"polyarchy", "mil_constrain", "mil_exec"}:
        return f"{numeric:.3f}"
    if code == "wgi_rule_of_law":
        return f"{numeric:.2f}"
    return f"{numeric:.1f}%"


def _build_structural_cards(structural: dict) -> list[dict]:
    cards: list[dict] = []
    default_year = _as_int(structural.get("year")) or 0
    field_years = structural.get("_field_years", {})
    series_map = structural.get("_series", {})
    for code in CARD_FIELDS:
        label, unit = CARD_META[code]
        cards.append({
            "code": code,
            "label": label,
            "current_value": structural.get(code),
            "display_value": _display_value(code, structural.get(code)),
            "unit": unit,
            "as_of_year": field_years.get(code) or default_year,
            "trend_series": series_map.get(code, []),
        })
    return cards


def _build_public_summary(monitor_row: dict) -> dict:
    summary = monitor_row.get("predictive_summary", monitor_row.get("public_summary", {}))
    watchpoints = summary.get("watchpoints") or []
    return {
        "overall_risk_score": _as_float(summary.get("overall_risk_score")) or 0.0,
        "overall_risk_level": _string_or_empty(summary.get("overall_risk_level")),
        "leading_construct": _string_or_empty(summary.get("leading_construct")),
        "leading_label": _string_or_empty(summary.get("leading_label")),
        "leading_trend": _string_or_empty(summary.get("leading_trend")),
        "summary_text": _string_or_empty(summary.get("summary_text")),
        "watchpoints": [str(item) for item in watchpoints if item is not None],
    }


def _build_public_construct_series(monitor_row: dict) -> list[dict]:
    constructs = monitor_row.get("risk_constructs", monitor_row.get("public_construct_series", []))
    series: list[dict] = []
    for item in constructs:
        code = item.get("code")
        label = item.get("label")
        if not code or not label:
            continue
        series.append({
            "code": str(code),
            "label": str(label),
        })
    return series


def _saturating_score(value: object, scale: float) -> float | None:
    numeric = _as_float(value)
    if numeric is None:
        return None
    if numeric <= 0:
        return 0.0
    return round((1.0 - math.exp(-numeric / scale)) * 100.0, 2)


def _weighted_mean(parts: list[tuple[float | None, float]]) -> float | None:
    total = 0.0
    total_weight = 0.0
    for value, weight in parts:
        if value is None or weight <= 0:
            continue
        total += value * weight
        total_weight += weight
    if total_weight <= 0:
        return None
    return round(total / total_weight, 2)


def _index_predictive_panel_rows(rows_payload) -> dict[str, dict[int, dict]]:
    by_country: dict[str, dict[int, dict]] = {}
    for row in _extract_rows(rows_payload):
        country = str(row.get("country") or "").strip()
        panel_date = str(row.get("panel_date") or "")
        year = _as_int(panel_date[:4])
        if not country or year is None:
            continue
        by_country.setdefault(country, {})
        current = by_country[country].get(year)
        if current is None or panel_date > str(current.get("panel_date") or ""):
            by_country[country][year] = row
    return by_country


def _index_latent_rows(rows_payload) -> dict[str, dict[int, dict]]:
    by_country: dict[str, dict[int, dict]] = {}
    for row in _extract_rows(rows_payload):
        country = str(row.get("country") or "").strip()
        year = _as_int(row.get("year"))
        if not country or year is None:
            continue
        by_country.setdefault(country, {})[year] = row
    return by_country


def _nearest_latent_row(latent_years: dict[int, dict], year: int) -> dict | None:
    if year in latent_years:
        return latent_years[year]
    prior_years = [candidate for candidate in latent_years if candidate <= year]
    if not prior_years:
        return None
    return latent_years[max(prior_years)]


def _proxy_regime_vulnerability_score(panel_row: dict | None, latent_row: dict | None) -> float | None:
    latent_score = _as_float((latent_row or {}).get("civilian_control_latent_v0_score"))
    civilian_erosion = None if latent_score is None else round(100.0 - latent_score, 2)
    acute_risk = _saturating_score((panel_row or {}).get("acute_political_risk_signal_score_next_3m"), 2.0)
    construct_pressure = _saturating_score((panel_row or {}).get("episode_construct_regime_vulnerability_count_12m"), 3.0)
    regime_shift = 100.0 if _as_float((panel_row or {}).get("regime_shift_flag")) else 0.0
    protest_load = _saturating_score((panel_row or {}).get("event_type_protest_count_12m"), 1.0)
    return _weighted_mean([
        (civilian_erosion, 0.48),
        (acute_risk, 0.20),
        (construct_pressure, 0.18),
        (regime_shift, 0.09),
        (protest_load, 0.05),
    ])


def _proxy_militarization_score(panel_row: dict | None, latent_row: dict | None) -> float | None:
    latent_score = _as_float((latent_row or {}).get("militarization_latent_v0_score"))
    construct_pressure = _saturating_score((panel_row or {}).get("episode_construct_militarization_count_12m"), 1.8)
    exception_rule = 100.0 if _as_float((panel_row or {}).get("sentinel_exception_rule_militarization_count_y")) else 0.0
    coercive_overlap = _saturating_score((panel_row or {}).get("event_type_purge_count_12m"), 1.0)
    return _weighted_mean([
        (latent_score, 0.68),
        (construct_pressure, 0.20),
        (exception_rule, 0.08),
        (coercive_overlap, 0.04),
    ])


def _proxy_security_fragmentation_score(panel_row: dict | None, latent_row: dict | None) -> float | None:
    del latent_row
    fragmentation_jump = _saturating_score((panel_row or {}).get("security_fragmentation_jump_signal_score_next_3m"), 1.8)
    construct_pressure = _saturating_score((panel_row or {}).get("episode_construct_security_fragmentation_count_12m"), 3.0)
    fragmenting_episodes = _saturating_score((panel_row or {}).get("fragmenting_episode_count_12m"), 1.5)
    dispersed_violence = _saturating_score(
        (_as_float((panel_row or {}).get("event_type_oc_count_12m")) or 0.0)
        + (_as_float((panel_row or {}).get("event_type_conflict_count_12m")) or 0.0)
        + (_as_float((panel_row or {}).get("event_type_protest_count_12m")) or 0.0) * 0.5,
        3.0,
    )
    return _weighted_mean([
        (fragmentation_jump, 0.34),
        (construct_pressure, 0.31),
        (fragmenting_episodes, 0.15),
        (dispersed_violence, 0.20),
    ])


def _build_public_predictive_series(
    country: str,
    monitor_row: dict,
    panel_rows_by_country: dict[str, dict[int, dict]],
    latent_rows_by_country: dict[str, dict[int, dict]],
) -> list[dict]:
    panel_years = panel_rows_by_country.get(country, {})
    latent_years = latent_rows_by_country.get(country, {})
    available_years = sorted({
        year
        for year in set(panel_years) | set(latent_years)
        if year >= 1990
    })
    current_constructs = {
        str(item.get("code")): item
        for item in (monitor_row.get("risk_constructs") or [])
        if item.get("code")
    }
    if not available_years and not current_constructs:
        return []

    if not available_years and current_constructs:
        latest_event_date = _max_event_date(monitor_row) or ""
        available_years = [_as_int(latest_event_date[:4]) or datetime.now(UTC).year]

    score_builders = {
        "regime_vulnerability": _proxy_regime_vulnerability_score,
        "militarization": _proxy_militarization_score,
        "security_fragmentation": _proxy_security_fragmentation_score,
    }
    series_rows: list[dict] = []
    last_year = available_years[-1]
    for code, label in PREDICTIVE_CONSTRUCT_META.items():
        points: list[dict] = []
        for year in available_years:
            panel_row = panel_years.get(year)
            latent_row = _nearest_latent_row(latent_years, year)
            score = score_builders[code](panel_row, latent_row)
            if score is None:
                continue
            points.append({
                "year": year,
                "score": score,
            })
        current_construct = current_constructs.get(code) or {}
        current_score = _as_float(current_construct.get("score"))
        if current_score is not None:
            current_point = {"year": last_year, "score": round(current_score, 2)}
            if points and points[-1]["year"] == last_year:
                points[-1] = current_point
            else:
                points.append(current_point)
        if not points:
            continue
        headline_score = current_score if current_score is not None else points[-1]["score"]
        series_rows.append({
            "code": code,
            "label": label,
            "current_score": round(headline_score, 2),
            "display_score": f"{headline_score:.1f}/100",
            "level": _string_or_empty(current_construct.get("level")),
            "trend_label": _string_or_empty(current_construct.get("trend_label")) or "stable",
            "as_of_year": points[-1]["year"],
            "trend_series": points,
        })
    return series_rows


def _build_public_freshness(structural: dict, monitor_row: dict, generated_at: str) -> dict:
    monitor_generated_at = monitor_row.get("generated_at")
    if not isinstance(monitor_generated_at, str) or not monitor_generated_at:
        monitor_generated_at = generated_at
    monitor_generated_at = _normalize_timestamp(monitor_generated_at) or generated_at
    events_as_of_date = (
        monitor_row.get("events_as_of_date")
        or _max_event_date(monitor_row)
        or monitor_generated_at[:10]
    )
    structural_year = _as_int(structural.get("year")) or 0
    return {
        "structural_as_of_year": structural_year,
        "events_as_of_date": str(events_as_of_date),
        "monitor_generated_at": str(monitor_generated_at),
        "series_coverage_note": f"Coverage through {structural_year}.",
    }


def _build_public_context(context_row: dict) -> dict:
    context = dict(CONTEXT_DEFAULTS)
    for key in CONTEXT_DEFAULTS:
        if key in context_row:
            context[key] = context_row.get(key)
    next_election = context_row.get("next_election")
    if isinstance(next_election, dict):
        context["next_election"] = {
            "date": _string_or_empty(next_election.get("date")) or NEXT_ELECTION_DEFAULT["date"],
            "type": _string_or_empty(next_election.get("type")) or NEXT_ELECTION_DEFAULT["type"],
            **(
                {"note": str(next_election["note"])}
                if next_election.get("note") not in (None, "")
                else {}
            ),
        }
    else:
        context["next_election"] = dict(NEXT_ELECTION_DEFAULT)
    context["capital"] = str(context.get("capital") or "")
    context["regime"] = str(context.get("regime") or "")
    context["cmr_status"] = str(context.get("cmr_status") or "")
    context["cmr_class"] = str(context.get("cmr_class") or "")
    context["note"] = str(context.get("note") or "")
    context["country_watch"] = str(context.get("country_watch") or "")
    if context.get("special_profile_id") is not None:
        context["special_profile_id"] = str(context["special_profile_id"])
    key_positions = context.get("key_positions") or []
    context["key_positions"] = [
        {
            "title": str(item.get("title", "")),
            "name": str(item.get("name", "")),
        }
        for item in key_positions
        if isinstance(item, dict)
    ]
    return context


def build_public_payload(
    structural_rows,
    monitor_rows,
    context_rows,
    predictive_panel_rows=None,
    latent_rows=None,
) -> dict:
    generated_at = _now_z()
    structural_index = _merge_structural_rows(structural_rows)
    monitor_index = _index_country_rows(monitor_rows)
    context_index = _index_country_rows(context_rows)
    predictive_panel_index = _index_predictive_panel_rows(predictive_panel_rows or [])
    latent_index = _index_latent_rows(latent_rows or [])

    countries: list[dict] = []
    for country, iso2, iso3, subregion in CANONICAL_COUNTRIES:
        structural = structural_index.get(country, {})
        monitor_row = monitor_index.get(country, {})
        context_row = context_index.get(country, {})
        countries.append({
            "country": country,
            "iso2": str(structural.get("iso2") or iso2),
            "iso3": str(structural.get("iso3") or iso3),
            "subregion": str(structural.get("subregion") or subregion),
            "generated_at": generated_at,
            "public_freshness": _build_public_freshness(structural, monitor_row, generated_at),
            "public_summary": _build_public_summary(monitor_row),
            "public_structural_cards": _build_structural_cards(structural),
            "public_construct_series": _build_public_construct_series(monitor_row),
            "public_predictive_series": _build_public_predictive_series(
                country,
                monitor_row,
                predictive_panel_index,
                latent_index,
            ),
            "public_context": _build_public_context(context_row),
        })

    return {
        "generated_at": generated_at,
        "count": len(countries),
        "countries": countries,
    }


def main(output: Path = OUT) -> None:
    structural_rows = load_json(COUNTRY_YEAR)
    monitor_rows = load_json(COUNTRY_MONITORS)
    context_rows = load_context_rows()
    predictive_panel_rows = load_optional_rows(COUNTRY_MONTH_PANEL)
    latent_rows = load_optional_rows(STATIC_LATENT)
    payload = build_public_payload(
        structural_rows=structural_rows,
        monitor_rows=monitor_rows,
        context_rows=context_rows,
        predictive_panel_rows=predictive_panel_rows,
        latent_rows=latent_rows,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote country dossiers to {output}")
    print(f"Country rows generated: {payload['count']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build SENTINEL public country dossiers")
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    main(args.output)
