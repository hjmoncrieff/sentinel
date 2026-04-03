#!/usr/bin/env python3
"""
Audit the reviewed fit-ready sample for irregular-transition modeling.

This stage highlights:
- sample composition
- country coverage imbalances
- crude feature separation between positives and reviewed negatives

It is a private/internal planning artifact used to decide what to review next
and which features need refinement before stronger model fitting.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
MODEL_VALIDATION = ROOT / "data" / "review" / "irregular_transition_model_validation.json"
OUT = ROOT / "data" / "review" / "irregular_transition_fit_sample_audit.json"

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
]


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 3) if values else 0.0


def main() -> None:
    payload = load_json(MODEL_VALIDATION)
    rows = payload.get("rows", []) if isinstance(payload, dict) else []

    positives = [row for row in rows if int(row.get("y_true") or 0) == 1]
    negatives = [row for row in rows if int(row.get("y_true") or 0) == 0]

    by_country: dict[str, dict] = {}
    for row in rows:
        country = str(row.get("country") or "")
        bucket = by_country.setdefault(country, {"rows": 0, "positives": 0, "negatives": 0})
        bucket["rows"] += 1
        bucket["positives"] += int(row.get("y_true") == 1)
        bucket["negatives"] += int(row.get("y_true") == 0)

    feature_separation = []
    for feature in FEATURES:
        pos_values = [float(row.get(feature) or 0) for row in positives]
        neg_values = [float(row.get(feature) or 0) for row in negatives]
        pos_mean = mean(pos_values)
        neg_mean = mean(neg_values)
        feature_separation.append({
            "feature": feature,
            "positive_mean": pos_mean,
            "negative_mean": neg_mean,
            "mean_gap": round(pos_mean - neg_mean, 3),
            "absolute_gap": round(abs(pos_mean - neg_mean), 3),
        })
    feature_separation.sort(key=lambda item: item["absolute_gap"], reverse=True)

    output = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_internal_fit_sample_audit",
        "source_file": str(MODEL_VALIDATION.relative_to(ROOT)),
        "summary": {
            "rows": len(rows),
            "positives": len(positives),
            "negatives": len(negatives),
            "countries_with_negatives": sorted({row["country"] for row in negatives}),
            "countries_with_positives": sorted({row["country"] for row in positives}),
        },
        "country_balance": [
            {"country": country, **bucket}
            for country, bucket in sorted(by_country.items())
        ],
        "feature_separation": feature_separation,
        "current_risks": [
            "reviewed negatives are still sparse and concentrated in a small set of countries",
            "some current features invert intuition because the negative sample is dominated by severe contestation rather than quiet months",
            "state_capacity_composite is currently almost non-separating in the reviewed fit sample",
        ],
        "recommended_next_actions": [
            "expand reviewed negative cases beyond Colombia, El Salvador, Honduras, Mexico, and Venezuela",
            "add explicit low-intensity reviewed negatives so the model learns more than severe-vs-severe distinctions",
            "revisit episode features that currently look non-separating or inverted in the fit sample",
            "keep the threshold baseline as the benchmark until the reviewed sample broadens",
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote fit-sample audit to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
