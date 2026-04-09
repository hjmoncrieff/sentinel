#!/usr/bin/env python3
"""
Build a private/internal country signal-panel artifact from the country-month panel.

Default pilot target:
  Venezuela

Outputs:
  data/modeling/internal_signal_panel_<country>.json
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL_IN = ROOT / "data" / "modeling" / "country_month_panel.json"
SPEC_IN = ROOT / "config" / "modeling" / "internal_signal_panel_spec.json"
EVENTS_IN = ROOT / "data" / "review" / "events_with_edits.json"
OUT_DIR = ROOT / "data" / "modeling"


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def slugify(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return text.strip("_") or "country"


def clamp_100(value: float) -> float:
    return max(0.0, min(100.0, value))


def label_for_score(score: float) -> str:
    if score >= 80:
        return "process_acceleration"
    if score >= 60:
        return "active_episode"
    if score >= 40:
        return "forming_episode"
    if score >= 20:
        return "watch"
    return "background"


def component_score(row: dict, field: str) -> float:
    value = row.get(field)
    if value in (None, ""):
        return 0.0
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0

    if field == "state_capacity_composite":
        # Lower state capacity should increase fragmentation pressure.
        return clamp_100(100.0 - numeric)
    if field.endswith("_flag"):
        return clamp_100(numeric)
    if field.startswith("external_pressure_") or field.startswith("economic_fragility_") or field.startswith("economic_policy_"):
        return clamp_100(numeric)
    if field == "event_shock_flag":
        return 100.0 if numeric > 0 else 0.0

    # Event counts and related signals: treat each count as a 20-point step.
    return clamp_100(numeric * 20.0)


def aggregate_series(row: dict, series_spec: dict) -> dict:
    components = []
    for field in series_spec.get("component_fields", []):
        score = component_score(row, field)
        components.append({
            "field": field,
            "value": row.get(field),
            "score": round(score, 2),
        })
    series_score = round(sum(item["score"] for item in components) / len(components), 2) if components else 0.0
    return {
        "code": series_spec["code"],
        "label": series_spec["label"],
        "score": series_score,
        "signal_label": label_for_score(series_score),
        "components": components,
        "construct_destinations": series_spec.get("construct_destinations", []),
    }


def build_markers(country: str, months: set[str]) -> list[dict]:
    payload = load_json(EVENTS_IN)
    events = payload.get("events", []) if isinstance(payload, dict) else payload
    out = []
    for event in events:
        if event.get("country") != country:
            continue
        event_date = str(event.get("event_date") or "")
        panel_date = f"{event_date[:7]}-01" if len(event_date) >= 7 else ""
        if panel_date not in months:
            continue
        salience = str(event.get("salience") or "").strip().lower()
        deed_type = str(event.get("deed_type") or "").strip().lower()
        event_type = str(event.get("event_type") or "").strip().lower()
        marker_type = None
        if salience == "high":
            marker_type = "major_event"
        elif event_type in {"coup", "purge"} or deed_type in {"destabilizing", "precursor"}:
            marker_type = "episode_start_candidate"
        if not marker_type:
            continue
        out.append({
            "panel_date": panel_date,
            "event_id": event.get("event_id"),
            "headline": event.get("headline"),
            "event_type": event_type,
            "deed_type": deed_type or None,
            "marker_type": marker_type,
        })
    out.sort(key=lambda item: (item["panel_date"], item["event_id"] or ""))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Build private internal signal panel output for one country.")
    parser.add_argument("--country", default=None, help="Country name. Defaults to the priority pilot country from the signal spec.")
    parser.add_argument("--months", type=int, default=18, help="Trailing number of months to include. Default: 18.")
    args = parser.parse_args()

    spec = load_json(SPEC_IN)
    panel = load_json(PANEL_IN)
    rows = panel.get("rows", []) if isinstance(panel, dict) else panel

    country = args.country or spec.get("priority_pilot_country") or "Venezuela"
    country_rows = [row for row in rows if row.get("country") == country]
    country_rows.sort(key=lambda row: row.get("panel_date") or "")
    if args.months > 0:
        country_rows = country_rows[-args.months:]
    months = {row["panel_date"] for row in country_rows}

    series_by_month = []
    construct_baskets = spec.get("construct_signal_baskets", {})

    for row in country_rows:
        series = [aggregate_series(row, item) for item in spec.get("signal_series", [])]
        series_index = {item["code"]: item for item in series}

        construct_pressure = {}
        for construct, members in construct_baskets.items():
            if construct == spec.get("construct_integration", {}).get("topline_output"):
                continue
            scores = [series_index[code]["score"] for code in members if code in series_index]
            score = round(sum(scores) / len(scores), 2) if scores else 0.0
            construct_pressure[construct] = {
                "score": score,
                "signal_label": label_for_score(score),
            }

        overall_members = construct_baskets.get("overall_risk_internal", [])
        overall_scores = [construct_pressure[item]["score"] for item in overall_members if item in construct_pressure]
        overall_score = round(sum(overall_scores) / len(overall_scores), 2) if overall_scores else 0.0

        series_by_month.append({
            "panel_date": row["panel_date"],
            "signals": series,
            "construct_pressure": construct_pressure,
            "overall_risk_internal": {
                "score": overall_score,
                "signal_label": label_for_score(overall_score),
            },
        })

    latest = series_by_month[-1] if series_by_month else None
    markers = build_markers(country, months)
    output = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_internal_signal_panel",
        "country": country,
        "window_months": len(series_by_month),
        "source_files": [
            str(PANEL_IN.relative_to(ROOT)),
            str(SPEC_IN.relative_to(ROOT)),
            str(EVENTS_IN.relative_to(ROOT)),
        ],
        "latest_snapshot": latest,
        "markers": markers,
        "series": series_by_month,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"internal_signal_panel_{slugify(country)}.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Wrote internal signal panel to {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
