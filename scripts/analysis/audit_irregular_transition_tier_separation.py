#!/usr/bin/env python3
"""
Audit which features best separate gold positives from hard negatives.

This stage is a private/internal diagnostic. It focuses only on the benchmark
tiers and helps identify whether new candidate features improve the core
gold-vs-hard distinction that currently blocks stronger model fitting.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL = ROOT / "data" / "modeling" / "country_month_panel.json"
BENCHMARK = ROOT / "data" / "modeling" / "irregular_transition_benchmark_tiers.json"
OUT = ROOT / "data" / "review" / "irregular_transition_tier_separation.json"

FEATURES = [
    "event_type_coup_count",
    "high_severity_episode_count",
    "episode_construct_regime_vulnerability_count",
    "escalating_episode_count",
    "episode_start_count",
    "deed_type_destabilizing_count",
    "event_shock_flag",
    "high_salience_event_count",
    "event_type_conflict_count",
    "event_type_protest_count",
    "state_capacity_composite",
    "external_pressure_sanctions_active",
    "economic_fragility_fx_stress",
    "time_since_last_coup",
    "coup_count_5y",
    "regime_shift_flag",
    "polyarchy_delta_1y",
    "trade_openness_delta_3y",
    "oda_received_delta_3y",
    "transition_rupture_precursor_score",
    "transition_contestation_load_score",
    "transition_specificity_gap",
]


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def avg(values: list[float]) -> float:
    return round(mean(values), 3) if values else 0.0


def coerce_float(value: object) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except Exception:
        return 0.0


def main() -> None:
    panel_payload = load_json(PANEL)
    panel_rows = panel_payload.get("rows", []) if isinstance(panel_payload, dict) else panel_payload
    panel_lookup = {
        (str(row.get("country") or ""), str(row.get("panel_date") or "")): row
        for row in panel_rows
    }

    benchmark_payload = load_json(BENCHMARK)
    benchmark_rows = benchmark_payload.get("rows", []) if isinstance(benchmark_payload, dict) else benchmark_payload
    gold_rows: list[dict] = []
    hard_rows: list[dict] = []
    for row in benchmark_rows:
        match = panel_lookup.get((str(row.get("country") or ""), str(row.get("panel_date") or "")))
        if not match:
            continue
        tier = str(row.get("tier") or "")
        if tier == "gold_positive":
            gold_rows.append(match)
        elif tier == "hard_negative":
            hard_rows.append(match)

    feature_comparison = []
    for feature in FEATURES:
        gold_values = [coerce_float(row.get(feature)) for row in gold_rows]
        hard_values = [coerce_float(row.get(feature)) for row in hard_rows]
        gold_mean = avg(gold_values)
        hard_mean = avg(hard_values)
        feature_comparison.append({
            "feature": feature,
            "gold_positive_mean": gold_mean,
            "hard_negative_mean": hard_mean,
            "mean_gap": round(gold_mean - hard_mean, 3),
            "absolute_gap": round(abs(gold_mean - hard_mean), 3),
        })
    feature_comparison.sort(key=lambda item: item["absolute_gap"], reverse=True)

    output = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_internal_tier_separation_audit",
        "benchmark_file": str(BENCHMARK.relative_to(ROOT)),
        "panel_file": str(PANEL.relative_to(ROOT)),
        "summary": {
            "gold_positive_rows": len(gold_rows),
            "hard_negative_rows": len(hard_rows),
        },
        "candidate_feature_snapshot": {
            feature: {
                "gold_positive_mean": avg([coerce_float(row.get(feature)) for row in gold_rows]),
                "hard_negative_mean": avg([coerce_float(row.get(feature)) for row in hard_rows]),
            }
            for feature in [
                "transition_rupture_precursor_score",
                "transition_contestation_load_score",
                "transition_specificity_gap",
            ]
        },
        "feature_comparison": feature_comparison,
        "current_takeaway": [
            "Features with large positive gaps are stronger among gold positives than hard negatives.",
            "Features with large negative gaps are stronger among hard negatives than gold positives.",
            "The new transition-specificity features should help test rupture-vs-contestation separation directly.",
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote tier separation audit to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
