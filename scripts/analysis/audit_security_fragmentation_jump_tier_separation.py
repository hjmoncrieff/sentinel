#!/usr/bin/env python3
"""
Audit which features best separate security-fragmentation-jump gold positives
from hard negatives.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL = ROOT / "data" / "modeling" / "country_month_panel.json"
BENCHMARK = ROOT / "data" / "modeling" / "security_fragmentation_jump_benchmark_tiers.json"
OUT = ROOT / "data" / "review" / "security_fragmentation_jump_tier_separation.json"

FEATURES = [
    "security_fragmentation_jump_signal_score_next_3m",
    "high_severity_episode_count",
    "fragmenting_episode_count",
    "episode_construct_security_fragmentation_count",
    "event_shock_flag",
    "high_salience_event_count",
    "deed_type_destabilizing_count",
    "event_type_conflict_count",
    "event_type_oc_count",
    "event_type_protest_count",
    "external_pressure_signal_present",
    "economic_fragility_signal_present",
    "macro_stress_shift_flag",
    "transition_rupture_precursor_score",
    "transition_contestation_load_score",
    "transition_specificity_gap",
    "protest_background_load_score",
    "protest_escalation_specificity_score",
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


def summarize_feature(rows: list[dict], feature: str) -> dict:
    values = [coerce_float(row.get(feature)) for row in rows]
    return {
        "mean": avg(values),
        "nonzero_count": sum(1 for value in values if abs(value) > 1e-9),
    }


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
        "status": "private_internal_security_fragmentation_jump_tier_separation_audit",
        "benchmark_file": str(BENCHMARK.relative_to(ROOT)),
        "panel_file": str(PANEL.relative_to(ROOT)),
        "summary": {
            "gold_positive_rows": len(gold_rows),
            "hard_negative_rows": len(hard_rows),
        },
        "candidate_feature_snapshot": {
            feature: {
                "gold_positive_mean": summarize_feature(gold_rows, feature)["mean"],
                "gold_positive_nonzero_count": summarize_feature(gold_rows, feature)["nonzero_count"],
                "hard_negative_mean": summarize_feature(hard_rows, feature)["mean"],
                "hard_negative_nonzero_count": summarize_feature(hard_rows, feature)["nonzero_count"],
            }
            for feature in [
                "security_fragmentation_jump_signal_score_next_3m",
                "fragmenting_episode_count",
                "episode_construct_security_fragmentation_count",
                "transition_contestation_load_score",
                "transition_specificity_gap",
            ]
        },
        "feature_comparison": feature_comparison,
        "current_takeaway": [
            "Features with large positive gaps are stronger among security-fragmentation-jump gold positives than hard negatives.",
            "Features with large negative gaps are stronger among hard negatives than gold positives.",
            "The benchmark should help separate clean fragmentation jumps from broad fragmentation-heavy overfire.",
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote security-fragmentation-jump tier separation audit to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
