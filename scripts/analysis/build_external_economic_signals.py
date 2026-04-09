#!/usr/bin/env python3
"""
Build a private country-month external/economic signal layer.

This stage derives a first real internal monthly signal artifact from the
reviewed event store, then overlays tracked benchmark seeds and optional local
manual overrides. It is intentionally private/internal and is meant to feed the
country-month modeling panel rather than any public-facing surface.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent.parent
COUNTRY_YEAR = ROOT / "data" / "cleaned" / "country_year.json"
GREENBOOK = ROOT / "data" / "cleaned" / "greenbook.json"
EUSANCT = ROOT / "data" / "cleaned" / "eusanct.json"
FINANCIAL_CRISES = ROOT / "data" / "cleaned" / "financial_crises.json"
EVENTS = ROOT / "data" / "review" / "events_with_edits.json"
BENCHMARK_SIGNALS = ROOT / "data" / "modeling" / "benchmark_country_month_signals.json"
MANUAL_SIGNALS_LOCAL = ROOT / "data" / "modeling" / "manual_country_month_signals.local.json"
MANUAL_SIGNALS_TEMPLATE = ROOT / "data" / "modeling" / "manual_country_month_signals.template.json"
OUT_JSON = ROOT / "data" / "modeling" / "external_economic_country_month.json"

SIGNAL_FIELDS = [
    "external_pressure_sanctions_active",
    "external_pressure_sanctions_delta",
    "external_pressure_imf_program_active",
    "external_pressure_imf_program_break",
    "external_pressure_us_security_shift",
    "economic_fragility_inflation_stress",
    "economic_fragility_fx_stress",
    "economic_fragility_debt_stress",
    "economic_policy_capital_controls_flag",
    "economic_policy_nationalization_signal",
]

TIGHTENING_RE = re.compile(r"\b(sanction|embargo|blacklist|ofac|treasury|restrict|tariff|penalt)", re.I)
EASING_RE = re.compile(r"\b(lift|ease|relax|rollback|remove)\b", re.I)
IMF_RE = re.compile(r"\b(imf|international monetary fund)\b", re.I)
IMF_BREAK_RE = re.compile(r"\b(break|collapse|suspend|stall|fail|rupture|default)\b", re.I)
US_RE = re.compile(r"\b(u\.s\.|us\b|united states|washington|fbi|dea|treasury|justice department)\b", re.I)
US_POSITIVE_RE = re.compile(r"\b(cooperat|training|exercise|procurement|aid|office|deploy|mission|support)\b", re.I)
US_NEGATIVE_RE = re.compile(r"\b(charge|investigat|sanction|restrict|rupture|suspend|expel|close)\b", re.I)
INFLATION_RE = re.compile(r"\b(inflation|price surge|consumer prices|cost of living)\b", re.I)
FX_RE = re.compile(r"\b(devaluation|currency|exchange rate|fx|reserve|dollar shortage|parallel market)\b", re.I)
DEBT_RE = re.compile(r"\b(debt|default|bond|restructur|sovereign spread|debt service)\b", re.I)
CAPITAL_CONTROL_RE = re.compile(r"\b(capital controls?|currency controls?|exchange controls?|withdrawal limits?)\b", re.I)
NATIONALIZATION_RE = re.compile(r"\b(nationaliz|expropriat|asset seizure|state takeover)\b", re.I)

DOLLARIZED_COUNTRIES = {"Ecuador", "El Salvador", "Panama"}


@dataclass(frozen=True)
class MonthKey:
    country: str
    iso3: str
    year: int
    month: int

    @property
    def panel_date(self) -> str:
        return f"{self.year:04d}-{self.month:02d}-01"


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def clamp_signed(value: float, low: float = -100.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def as_float(value) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_positive(value: float | None, low: float, high: float) -> float:
    if value is None:
        return 0.0
    if value <= low:
        return 0.0
    if value >= high:
        return 100.0
    return clamp(((value - low) / (high - low)) * 100.0)


def normalize_negative_floor(value: float | None, floor: float) -> float:
    if value is None:
        return 0.0
    if value >= 0:
        return 0.0
    if value <= floor:
        return 100.0
    return clamp((abs(value) / abs(floor)) * 100.0)


def invert_positive(value: float | None, low: float, high: float) -> float:
    if value is None:
        return 0.0
    if value <= low:
        return 100.0
    if value >= high:
        return 0.0
    return clamp(((high - value) / (high - low)) * 100.0)


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def load_country_year_rows() -> list[dict]:
    payload = load_json(COUNTRY_YEAR)
    return payload.get("rows", []) if isinstance(payload, dict) else payload


def load_events() -> list[dict]:
    payload = load_json(EVENTS)
    return payload.get("events", []) if isinstance(payload, dict) else payload


def load_greenbook_payload() -> dict:
    if not GREENBOOK.exists():
        return {}
    payload = load_json(GREENBOOK)
    return payload if isinstance(payload, dict) else {}


def load_rows_payload(path: Path) -> list[dict]:
    if not path.exists():
        return []
    payload = load_json(path)
    return payload.get("rows", []) if isinstance(payload, dict) else []


def parse_year_month(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    try:
        stamp = datetime.strptime(str(value)[:10], "%Y-%m-%d")
    except ValueError:
        return None
    return stamp.year, stamp.month


def confidence_weight(value: str | None) -> float:
    text = str(value or "").strip().lower()
    if text in {"high", "green"}:
        return 1.0
    if text in {"medium", "med", "yellow"}:
        return 0.75
    return 0.5


def salience_weight(value: str | None) -> float:
    text = str(value or "").strip().lower()
    if text == "high":
        return 1.15
    if text == "medium":
        return 0.8
    return 0.55


def build_month_index(country_rows: list[dict]) -> list[MonthKey]:
    keys: list[MonthKey] = []
    for row in country_rows:
        country = str(row.get("country") or "").strip()
        year = int(row.get("year") or 0)
        iso3 = str(row.get("iso3") or "").strip()
        if not country or not year:
            continue
        for month in range(1, 13):
            keys.append(MonthKey(country=country, iso3=iso3, year=year, month=month))
    return sorted(keys, key=lambda item: (item.country, item.year, item.month))


def text_blob(event: dict) -> str:
    fields = [
        "headline",
        "summary",
        "classification_reason",
        "review_notes",
        "actor_primary_name",
        "actor_secondary_name",
    ]
    return " ".join(str(event.get(field) or "") for field in fields)


def seed_rows_to_map(rows: list[dict]) -> dict[tuple[str, str], dict]:
    out: dict[tuple[str, str], dict] = {}
    for row in rows:
        country = str(row.get("country") or "").strip()
        panel_date = str(row.get("panel_date") or "").strip()
        if country and panel_date:
            out[(country, panel_date)] = row
    return out


def load_seed_rows() -> tuple[list[str], dict[tuple[str, str], dict]]:
    sources: list[str] = []
    merged: dict[tuple[str, str], dict] = {}
    if BENCHMARK_SIGNALS.exists():
        payload = load_json(BENCHMARK_SIGNALS)
        merged.update(seed_rows_to_map(payload.get("rows", []) if isinstance(payload, dict) else []))
        sources.append(str(BENCHMARK_SIGNALS.relative_to(ROOT)))
    if MANUAL_SIGNALS_LOCAL.exists():
        payload = load_json(MANUAL_SIGNALS_LOCAL)
        merged.update(seed_rows_to_map(payload.get("rows", []) if isinstance(payload, dict) else []))
        sources.append(str(MANUAL_SIGNALS_LOCAL.relative_to(ROOT)))
    return sources, merged


def build_event_signal_shocks(events: list[dict]) -> dict[tuple[str, int, int], dict]:
    monthly: dict[tuple[str, int, int], dict] = defaultdict(lambda: {
        "sanctions_delta_shock": 0.0,
        "imf_active_shock": 0.0,
        "imf_break_shock": 0.0,
        "us_security_shift_shock": 0.0,
        "inflation_shock": 0.0,
        "fx_shock": 0.0,
        "debt_shock": 0.0,
        "capital_controls_flag": 0.0,
        "nationalization_signal": 0.0,
        "keyword_signal_count": 0,
    })

    for event in events:
        country = str(event.get("country") or "").strip()
        if not country or country == "Regional":
            continue
        stamp = parse_year_month(event.get("event_date"))
        if stamp is None:
            continue
        year, month = stamp
        text = text_blob(event)
        lower = text.lower()
        weight = confidence_weight(event.get("confidence")) * salience_weight(event.get("salience"))
        bucket = monthly[(country, year, month)]
        event_type = str(event.get("event_type") or "").strip().lower()

        if TIGHTENING_RE.search(text):
            if "sanction" in lower or "embargo" in lower or "ofac" in lower:
                direction = -18.0 if EASING_RE.search(text) else 22.0
                bucket["sanctions_delta_shock"] += direction * weight
                bucket["keyword_signal_count"] += 1

        if IMF_RE.search(text):
            bucket["imf_active_shock"] += 16.0 * weight
            bucket["keyword_signal_count"] += 1
            if IMF_BREAK_RE.search(text):
                bucket["imf_break_shock"] += 26.0 * weight

        if US_RE.search(text):
            if event_type in {"aid", "exercise", "procurement", "coop"} or US_POSITIVE_RE.search(text):
                bucket["us_security_shift_shock"] += 18.0 * weight
                bucket["keyword_signal_count"] += 1
            if US_NEGATIVE_RE.search(text):
                bucket["us_security_shift_shock"] -= 18.0 * weight

        if INFLATION_RE.search(text):
            bucket["inflation_shock"] += 18.0 * weight
            bucket["keyword_signal_count"] += 1
        if FX_RE.search(text):
            bucket["fx_shock"] += 18.0 * weight
            bucket["keyword_signal_count"] += 1
        if DEBT_RE.search(text):
            bucket["debt_shock"] += 18.0 * weight
            bucket["keyword_signal_count"] += 1
        if CAPITAL_CONTROL_RE.search(text):
            bucket["capital_controls_flag"] = max(bucket["capital_controls_flag"], 100.0)
            bucket["fx_shock"] += 15.0 * weight
            bucket["keyword_signal_count"] += 1
        if NATIONALIZATION_RE.search(text):
            bucket["nationalization_signal"] = max(bucket["nationalization_signal"], clamp(70.0 * weight))
            bucket["keyword_signal_count"] += 1

    return monthly


def structural_lookup(country_rows: list[dict]) -> dict[tuple[str, int], dict]:
    return {
        (str(row.get("country") or "").strip(), int(row.get("year") or 0)): row
        for row in country_rows
        if row.get("country") and row.get("year")
    }


def build_greenbook_lookup() -> dict[tuple[str, int], dict[str, float]]:
    payload = load_greenbook_payload()
    countries = payload.get("countries", []) if isinstance(payload, dict) else []
    year_values: dict[tuple[str, int], dict[str, float]] = {}
    max_military = 0.0
    for country_row in countries:
        country = str(country_row.get("country") or "").strip()
        for point in country_row.get("series", []) or []:
            year = int(point.get("year") or 0)
            military = max(0.0, float(point.get("military") or 0.0))
            total = max(0.0, float(point.get("total") or 0.0))
            year_values[(country, year)] = {
                "military": military,
                "total": total,
            }
            max_military = max(max_military, military)

    if max_military <= 0:
        return {}

    for key, row in year_values.items():
        military = row["military"]
        prev = year_values.get((key[0], key[1] - 1), {})
        prev_military = float(prev.get("military") or 0.0)
        row["military_norm"] = round(clamp((math.log1p(military) / math.log1p(max_military)) * 100.0), 2)
        if prev_military > 0:
            pct_change = ((military - prev_military) / prev_military) * 100.0
        elif military > 0:
            pct_change = 100.0
        else:
            pct_change = 0.0
        row["military_change_pct"] = round(clamp_signed(pct_change), 2)
    return year_values


def build_country_year_lookup(rows: list[dict], country_field: str = "country") -> dict[tuple[str, int], dict]:
    return {
        (str(row.get(country_field) or "").strip(), int(row.get("year") or 0)): row
        for row in rows
        if row.get(country_field) and row.get("year")
    }


def structural_baseline_signals(row: dict) -> dict[str, float]:
    country = str(row.get("country") or "").strip()
    inflation = as_float(row.get("inflation_consumer_prices_pct"))
    real_rate = as_float(row.get("real_interest_rate"))
    current_account = as_float(row.get("current_account_pct_gdp"))
    reserves = as_float(row.get("reserves_months_imports"))
    debt_service = as_float(row.get("debt_service_pct_exports"))
    fdi = as_float(row.get("fdi_net_inflows_pct_gdp"))
    resource_rents = as_float(row.get("resource_rents_pct_gdp"))

    inflation_stress = (
        0.7 * normalize_positive(inflation, 5.0, 40.0)
        + 0.3 * normalize_negative_floor(real_rate, -5.0)
    )
    fx_stress = (
        0.45 * invert_positive(reserves, 2.0, 8.0)
        + 0.4 * normalize_negative_floor(current_account, -10.0)
        + 0.15 * normalize_positive(resource_rents, 5.0, 30.0)
    )
    debt_stress = (
        0.45 * normalize_positive(debt_service, 12.0, 45.0)
        + 0.20 * normalize_negative_floor(current_account, -10.0)
        + 0.15 * invert_positive(fdi, 1.0, 8.0)
        + 0.20 * invert_positive(reserves, 2.0, 8.0)
    )
    if country in DOLLARIZED_COUNTRIES:
        fx_stress *= 0.55
    return {
        "inflation_stress": round(clamp(inflation_stress), 2),
        "fx_stress": round(clamp(fx_stress), 2),
        "debt_stress": round(clamp(debt_stress), 2),
    }


def derive_rows() -> list[dict]:
    country_rows = load_country_year_rows()
    keys = build_month_index(country_rows)
    structural = structural_lookup(country_rows)
    greenbook = build_greenbook_lookup()
    eusanct = build_country_year_lookup(load_rows_payload(EUSANCT))
    crises = build_country_year_lookup(load_rows_payload(FINANCIAL_CRISES))
    shocks = build_event_signal_shocks(load_events())
    _, seed_map = load_seed_rows()

    rows: list[dict] = []
    by_country: dict[str, list[MonthKey]] = defaultdict(list)
    for key in keys:
        by_country[key.country].append(key)

    for country, month_keys in by_country.items():
        month_keys.sort(key=lambda item: (item.year, item.month))
        sanctions_active = 0.0
        imf_active = 0.0
        previous_sanctions_active = 0.0
        sanctions_memory = 0.0
        crisis_memory = 0.0
        inflation_memory = 0.0
        fx_memory = 0.0
        debt_memory = 0.0

        for key in month_keys:
            bucket = shocks.get((country, key.year, key.month), {})
            annual = structural.get((country, key.year), {})
            baseline = structural_baseline_signals(annual) if annual else {
                "inflation_stress": 0.0,
                "fx_stress": 0.0,
                "debt_stress": 0.0,
            }
            assistance = greenbook.get((country, key.year), {})
            sanctions = eusanct.get((country, key.year), {})
            crises_row = crises.get((country, key.year), {})
            us_assistance_baseline = float(assistance.get("military_norm") or 0.0)
            us_assistance_change = float(assistance.get("military_change_pct") or 0.0)
            sanctions_structural = float(sanctions.get("sanctions_intensity_score") or 0.0)
            crisis_structural = float(crises_row.get("crisis_intensity_score") or 0.0)
            seed = seed_map.get((country, key.panel_date))
            seed_sanctions = float(seed.get("external_pressure_sanctions_active") or 0.0) if seed else 0.0
            seed_imf = float(seed.get("external_pressure_imf_program_active") or 0.0) if seed else 0.0
            seed_inflation = float(seed.get("economic_fragility_inflation_stress") or 0.0) if seed else 0.0
            seed_fx = float(seed.get("economic_fragility_fx_stress") or 0.0) if seed else 0.0
            seed_debt = float(seed.get("economic_fragility_debt_stress") or 0.0) if seed else 0.0

            sanctions_delta = float(bucket.get("sanctions_delta_shock", 0.0))
            sanctions_reinforcement = clamp(
                max(0.0, sanctions_delta)
                + (seed_sanctions * 0.15)
                + (8.0 if bucket.get("keyword_signal_count", 0) and sanctions_delta > 0 else 0.0)
            )
            sanctions_memory = clamp(max(
                sanctions_structural * 0.75,
                seed_sanctions,
                sanctions_memory * 0.95 + sanctions_reinforcement * 0.28,
            ))
            sanctions_active = clamp(
                (sanctions_memory * 0.62)
                + (sanctions_active * 0.38)
                + sanctions_reinforcement
            )
            if sanctions_delta < 0:
                sanctions_active = clamp(sanctions_active + sanctions_delta)

            imf_active = clamp(max(seed_imf, imf_active * 0.95 + float(bucket.get("imf_active_shock", 0.0))))
            imf_break = clamp(float(bucket.get("imf_break_shock", 0.0)))
            if imf_break > 0:
                imf_active = clamp(imf_active - (imf_break * 0.25))
            if imf_active == 0.0:
                imf_active = round(clamp(baseline["debt_stress"] * 0.18), 2)

            us_shift = clamp_signed(
                (us_assistance_baseline * 0.12)
                + (us_assistance_change * 0.38)
                + float(bucket.get("us_security_shift_shock", 0.0))
            )

            crisis_memory = clamp(max(crisis_structural, crisis_memory * 0.985))
            inflation_memory = clamp(max(seed_inflation, inflation_memory * 0.94))
            fx_memory = clamp(max(seed_fx, fx_memory * 0.94))
            debt_memory = clamp(max(seed_debt, debt_memory * 0.92))

            inflation_stress = clamp(
                baseline["inflation_stress"]
                + float(bucket.get("inflation_shock", 0.0))
                + (crisis_memory * 0.18)
                + inflation_memory
            )
            fx_stress = clamp(
                baseline["fx_stress"]
                + float(bucket.get("fx_shock", 0.0))
                + (sanctions_active * 0.18)
                + (crisis_memory * 0.22)
                + fx_memory
            )
            debt_stress = clamp(
                (baseline["debt_stress"] * 0.82)
                + float(bucket.get("debt_shock", 0.0))
                + (imf_break * 0.22)
                + (crisis_memory * 0.15)
                + debt_memory
            )

            row = {
                "country": country,
                "iso3": key.iso3,
                "panel_date": key.panel_date,
                "external_pressure_sanctions_active": round(sanctions_active, 2),
                "external_pressure_sanctions_delta": round(sanctions_active - previous_sanctions_active, 2),
                "external_pressure_imf_program_active": round(imf_active, 2),
                "external_pressure_imf_program_break": round(imf_break, 2),
                "external_pressure_us_security_shift": round(us_shift, 2),
                "economic_fragility_inflation_stress": round(inflation_stress, 2) if inflation_stress > 0 else None,
                "economic_fragility_fx_stress": round(fx_stress, 2) if fx_stress > 0 else None,
                "economic_fragility_debt_stress": round(debt_stress, 2) if debt_stress > 0 else None,
                "economic_policy_capital_controls_flag": round(float(bucket.get("capital_controls_flag", 0.0)), 2) or None,
                "economic_policy_nationalization_signal": round(float(bucket.get("nationalization_signal", 0.0)), 2) or None,
                "signal_origin": "event_derived_then_seed_override",
                "keyword_signal_count": int(bucket.get("keyword_signal_count", 0)),
                "structural_year_available": int(bool(annual)),
                "structural_macro_baseline_present": int(any(value > 0 for value in baseline.values())),
                "us_assistance_baseline_present": int(bool(assistance)),
                "us_assistance_military_norm": round(us_assistance_baseline, 2) if assistance else None,
                "us_assistance_military_change_pct": round(us_assistance_change, 2) if assistance else None,
                "sanctions_dataset_present": int(bool(sanctions)),
                "sanctions_intensity_score": round(sanctions_structural, 2) if sanctions else None,
                "financial_crisis_dataset_present": int(bool(crises_row)),
                "financial_crisis_intensity_score": round(crisis_structural, 2) if crises_row else None,
            }

            if seed:
                for field in SIGNAL_FIELDS:
                    if field in seed and seed.get(field) is not None:
                        row[field] = seed.get(field)
                row["signal_origin"] = "seed_override_on_derived"
                if seed.get("notes"):
                    row["notes"] = seed.get("notes")

            sanctions_memory = max(
                sanctions_memory * 0.98,
                float(row.get("external_pressure_sanctions_active") or 0.0) * 0.88,
            )
            inflation_memory = max(inflation_memory * 0.92, float(row.get("economic_fragility_inflation_stress") or 0.0) * 0.12)
            fx_memory = max(fx_memory * 0.92, float(row.get("economic_fragility_fx_stress") or 0.0) * 0.12)
            debt_memory = max(debt_memory * 0.88, float(row.get("economic_fragility_debt_stress") or 0.0) * 0.08)

            row["external_pressure_signal_present"] = int(any(
                row.get(field) not in (None, 0, 0.0, "")
                for field in [
                    "external_pressure_sanctions_active",
                    "external_pressure_sanctions_delta",
                    "external_pressure_imf_program_active",
                    "external_pressure_imf_program_break",
                    "external_pressure_us_security_shift",
                ]
            ))
            row["economic_fragility_signal_present"] = int(any(
                row.get(field) not in (None, 0, 0.0, "")
                for field in [
                    "economic_fragility_inflation_stress",
                    "economic_fragility_fx_stress",
                    "economic_fragility_debt_stress",
                ]
            ))
            row["policy_shock_signal_present"] = int(any(
                row.get(field) not in (None, 0, 0.0, "")
                for field in [
                    "economic_policy_capital_controls_flag",
                    "economic_policy_nationalization_signal",
                ]
            ))

            previous_sanctions_active = row["external_pressure_sanctions_active"] or 0.0
            rows.append(row)

    # Keep seed sources referenced even if the local file is absent.
    source_files = [
        str(COUNTRY_YEAR.relative_to(ROOT)),
        str(GREENBOOK.relative_to(ROOT)) if GREENBOOK.exists() else None,
        str(EUSANCT.relative_to(ROOT)) if EUSANCT.exists() else None,
        str(FINANCIAL_CRISES.relative_to(ROOT)) if FINANCIAL_CRISES.exists() else None,
        str(EVENTS.relative_to(ROOT)),
        str(BENCHMARK_SIGNALS.relative_to(ROOT)) if BENCHMARK_SIGNALS.exists() else None,
        str(MANUAL_SIGNALS_LOCAL.relative_to(ROOT)) if MANUAL_SIGNALS_LOCAL.exists() else None,
        str(MANUAL_SIGNALS_TEMPLATE.relative_to(ROOT)) if MANUAL_SIGNALS_TEMPLATE.exists() else None,
    ]
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_internal_signal_artifact",
        "description": (
            "Country-month external pressure and economic signal layer derived "
            "from reviewed events, then overlaid with tracked benchmark seeds "
            "and optional local manual overrides."
        ),
        "unit_of_analysis": "country_month",
        "field_status": {
            "external_pressure": "event_derived_and_seed_override_ready",
            "economic_fragility": "event_derived_and_seed_override_ready",
            "policy_shocks": "event_derived_and_seed_override_ready",
        },
        "source_files": [value for value in source_files if value],
        "count": len(rows),
        "seeded_coverage": {
            "external_pressure_rows": sum(int(row.get("external_pressure_signal_present", 0)) for row in rows),
            "economic_fragility_rows": sum(int(row.get("economic_fragility_signal_present", 0)) for row in rows),
            "policy_shock_rows": sum(int(row.get("policy_shock_signal_present", 0)) for row in rows),
        },
        "rows": rows,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(rows)} rows to {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    derive_rows()
