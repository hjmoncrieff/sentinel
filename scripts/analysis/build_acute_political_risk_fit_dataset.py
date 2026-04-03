#!/usr/bin/env python3
"""
Build the reviewed fit-ready acute political-risk dataset.

This produces a private artifact combining:
- gold acute-risk positives
- hard acute-risk negatives
- easy acute-risk negatives

The output is intended for future fitting work and uses the acute-risk signal
fields from the country-month panel.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL = ROOT / "data" / "modeling" / "country_month_panel.json"
GOLD = ROOT / "data" / "modeling" / "gold_acute_political_risk_labels.json"
BENCHMARK_TIERS = ROOT / "data" / "modeling" / "acute_political_risk_benchmark_tiers.json"
OUT = ROOT / "data" / "modeling" / "acute_political_risk_fit_dataset.json"

FIT_FEATURES = [
    "acute_political_risk_signal_score_next_1m",
    "high_severity_episode_count",
    "fragmenting_episode_count",
    "episode_construct_regime_vulnerability_count",
    "episode_construct_security_fragmentation_count",
    "event_shock_flag",
    "deed_type_destabilizing_count",
    "event_type_coup_count",
    "event_type_conflict_count",
    "event_type_protest_count",
    "external_pressure_signal_present",
    "economic_fragility_signal_present",
    "macro_stress_shift_flag",
    "external_pressure_sanctions_active",
    "economic_fragility_fx_stress",
    "economic_fragility_debt_stress",
    "economic_fragility_inflation_stress",
    "state_capacity_composite",
    "regime_shift_flag",
    "repression_shift_flag",
    "transition_rupture_precursor_score",
    "transition_contestation_load_score",
    "transition_specificity_gap",
]


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def build_sample() -> tuple[list[dict], dict]:
    panel_payload = load_json(PANEL)
    panel_rows = panel_payload.get("rows", []) if isinstance(panel_payload, dict) else panel_payload
    panel_lookup = {
        (str(row.get("country") or ""), str(row.get("panel_date") or "")): row
        for row in panel_rows
    }

    gold_payload = load_json(GOLD)
    gold_rows = gold_payload.get("rows", []) if isinstance(gold_payload, dict) else []
    gold_keys = {
        (str(row.get("country") or ""), str(row.get("panel_date") or ""))
        for row in gold_rows
    }

    benchmark_payload = load_json(BENCHMARK_TIERS)
    benchmark_rows = benchmark_payload.get("rows", []) if isinstance(benchmark_payload, dict) else benchmark_payload

    rows: list[dict] = []
    for row in benchmark_rows:
        key = (str(row.get("country") or ""), str(row.get("panel_date") or ""))
        panel_row = panel_lookup.get(key)
        if not panel_row:
            continue
        tier = str(row.get("tier") or "")
        y_true = 1 if tier == "gold_positive" else 0
        rows.append({
            "country": key[0],
            "panel_date": key[1],
            "y_true": y_true,
            "label_group": tier,
            "benchmark_tier": tier,
            "signal_score_1m": int(panel_row.get("acute_political_risk_signal_score_next_1m") or 0),
            "signal_label_1m": str(panel_row.get("acute_political_risk_signal_label_next_1m") or ""),
            "target_rule": str(panel_row.get("acute_political_risk_target_rule") or ""),
            **{feature: panel_row.get(feature) for feature in FIT_FEATURES},
        })

    rows.sort(key=lambda item: (item["country"], item["panel_date"], item["y_true"]))
    metadata = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_internal_acute_political_risk_fit_dataset",
        "panel_file": str(PANEL.relative_to(ROOT)),
        "gold_file": str(GOLD.relative_to(ROOT)),
        "benchmark_file": str(BENCHMARK_TIERS.relative_to(ROOT)),
        "target_rule": rows[0].get("target_rule") if rows else None,
        "summary": {
            "rows": len(rows),
            "gold_positive_rows": sum(1 for row in rows if row["label_group"] == "gold_positive"),
            "hard_negative_rows": sum(1 for row in rows if row["label_group"] == "hard_negative"),
            "easy_negative_rows": sum(1 for row in rows if row["label_group"] == "easy_negative"),
        },
        "fit_features": FIT_FEATURES,
    }
    return rows, metadata


def main() -> None:
    rows, metadata = build_sample()
    payload = {**metadata, "rows": rows}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote acute-risk fit dataset to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
