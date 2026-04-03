#!/usr/bin/env python3
"""
Build a private benchmark review artifact for the external/economic signal layer.

This runner does not fit a model. It summarizes the current external/economic
monthly signals for a focused benchmark set and emits simple heuristics to guide
the next calibration pass.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SIGNALS = ROOT / "data" / "modeling" / "external_economic_country_month.json"
OUT = ROOT / "data" / "review" / "external_economic_signal_review.json"

BENCHMARK_COUNTRIES = [
    "Venezuela",
    "Ecuador",
    "Mexico",
    "Colombia",
    "El Salvador",
    "Haiti",
]

FIELDS = [
    "external_pressure_sanctions_active",
    "external_pressure_imf_program_active",
    "external_pressure_us_security_shift",
    "economic_fragility_inflation_stress",
    "economic_fragility_fx_stress",
    "economic_fragility_debt_stress",
]


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def round_or_none(value: float | None) -> float | None:
    return None if value is None else round(value, 2)


def summarize_series(rows: list[dict], field: str) -> dict:
    values = [float(row.get(field) or 0.0) for row in rows]
    if not values:
        return {
            "latest": None,
            "mean": None,
            "max": None,
            "active_months": 0,
            "active_share": 0.0,
        }
    active_months = sum(1 for value in values if value > 0)
    return {
        "latest": round_or_none(values[-1]),
        "mean": round(sum(values) / len(values), 2),
        "max": round(max(values), 2),
        "active_months": active_months,
        "active_share": round(active_months / len(values), 3),
    }


def heuristic_notes(country: str, summaries: dict[str, dict]) -> list[str]:
    notes: list[str] = []
    sanctions = summaries["external_pressure_sanctions_active"]
    imf = summaries["external_pressure_imf_program_active"]
    us = summaries["external_pressure_us_security_shift"]
    inflation = summaries["economic_fragility_inflation_stress"]
    fx = summaries["economic_fragility_fx_stress"]
    debt = summaries["economic_fragility_debt_stress"]

    if sanctions["max"] and sanctions["max"] >= 70 and sanctions["latest"] == 0:
        notes.append("Sanctions pressure appears episodic rather than persistent; verify whether decay is too abrupt after benchmark-seeded months.")
    if imf["active_share"] and imf["active_share"] > 0.7 and (imf["mean"] or 0) < 15:
        notes.append("IMF exposure is present as low-grade background pressure in many months; verify whether this baseline is too diffuse.")
    if us["mean"] and us["mean"] > 25 and country in {"Colombia", "Mexico", "El Salvador"}:
        notes.append("US security shift stays elevated over long windows, which may be appropriate structurally but should be checked against the intended interpretation of 'shift' versus 'baseline tie'.")
    if debt["latest"] and debt["latest"] >= 70:
        notes.append("Debt stress is currently severe; confirm that debt-service weighting is not overstating vulnerability relative to other macro channels.")
    if fx["latest"] and fx["latest"] >= 45 and country in {"Ecuador", "El Salvador", "Mexico"}:
        notes.append("FX stress remains materially elevated; check whether reserve/import and current-account thresholds are set too tightly for dollarized or managed-exchange contexts.")
    if inflation["latest"] and inflation["latest"] >= 40:
        notes.append("Inflation stress is high enough to anchor the monthly baseline; confirm that this matches the intended country narrative.")
    if country == "Venezuela" and (inflation["latest"] or 0) == 0 and (fx["latest"] or 0) == 0:
        notes.append("Venezuela loses most macro signal in the latest year because structural coverage is sparse; consider a carry-forward rule for missing macro series in extreme benchmark cases.")
    if country == "Haiti" and (debt["latest"] or 0) >= 70:
        notes.append("Haiti debt stress is structurally high; verify that this is analytically useful rather than crowding out state-capacity and fragmentation signals.")
    return notes


def review(signals_path: Path) -> dict:
    payload = load_json(signals_path)
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    grouped: dict[str, list[dict]] = {country: [] for country in BENCHMARK_COUNTRIES}
    for row in rows:
        country = row.get("country")
        if country in grouped:
            grouped[country].append(row)
    for country_rows in grouped.values():
        country_rows.sort(key=lambda row: row["panel_date"])

    countries = []
    for country in BENCHMARK_COUNTRIES:
        country_rows = grouped[country]
        summaries = {field: summarize_series(country_rows, field) for field in FIELDS}
        latest = country_rows[-1] if country_rows else {}
        countries.append({
            "country": country,
            "window_months": len(country_rows),
            "latest_panel_date": latest.get("panel_date"),
            "current_snapshot": {
                field: latest.get(field) for field in FIELDS
            },
            "series_summary": summaries,
            "heuristic_notes": heuristic_notes(country, summaries),
        })

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "private_internal_benchmark_review",
        "signal_file": str(signals_path.relative_to(ROOT)),
        "benchmark_countries": BENCHMARK_COUNTRIES,
        "countries": countries,
    }


def main() -> None:
    payload = review(SIGNALS)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote benchmark review to {OUT}")
    print(f"Countries reviewed: {len(payload['countries'])}")


if __name__ == "__main__":
    main()
