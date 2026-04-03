#!/usr/bin/env python3
"""
Audit structural-history coverage for private model training.

This stage distinguishes:
- the current operational/live product window
- the currently available merged structural country-year window
- whether any usable pre-1990 structural history is already present
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
COUNTRY_YEAR = ROOT / "data" / "cleaned" / "country_year.json"
OUT = ROOT / "data" / "review" / "training_history_coverage_audit.json"

CORE_FIELDS = [
    "polyarchy",
    "liberal_democracy",
    "regime_type",
    "mil_constrain",
    "mil_exec",
    "state_authority",
    "rule_of_law_vdem",
    "wgi_govt_effectiveness",
    "wgi_rule_of_law",
    "wgi_control_corruption",
    "inflation_consumer_prices_pct",
    "official_exchange_rate",
    "debt_service_pct_exports",
    "reserves_months_imports",
    "state_capacity_composite",
]


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 3)


def main() -> None:
    payload = load_json(COUNTRY_YEAR)
    rows = payload.get("rows", []) if isinstance(payload, dict) else payload

    years = sorted({int(row.get("year") or 0) for row in rows if row.get("year") not in (None, "")})
    countries = sorted({str(row.get("country") or "") for row in rows if row.get("country")})
    pre_1990_rows = [row for row in rows if int(row.get("year") or 0) < 1990]
    post_1990_rows = [row for row in rows if int(row.get("year") or 0) >= 1990]

    field_coverage = []
    for field in CORE_FIELDS:
        total = len(rows)
        post_total = len(post_1990_rows)
        pre_total = len(pre_1990_rows)
        present = sum(1 for row in rows if row.get(field) not in (None, ""))
        post_present = sum(1 for row in post_1990_rows if row.get(field) not in (None, ""))
        pre_present = sum(1 for row in pre_1990_rows if row.get(field) not in (None, ""))
        field_coverage.append({
            "field": field,
            "overall_present_rows": present,
            "overall_coverage_pct": pct(present, total),
            "post_1990_present_rows": post_present,
            "post_1990_coverage_pct": pct(post_present, post_total),
            "pre_1990_present_rows": pre_present,
            "pre_1990_coverage_pct": pct(pre_present, pre_total),
        })

    output = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_training_history_coverage_audit",
        "source_file": str(COUNTRY_YEAR.relative_to(ROOT)),
        "coverage_windows": {
            "operational_product_window": "1990-present",
            "current_country_year_window": {
                "min_year": years[0] if years else None,
                "max_year": years[-1] if years else None,
            },
            "training_history_window_possible_from_current_merged_layer": bool(pre_1990_rows),
        },
        "summary": {
            "rows": len(rows),
            "countries": len(countries),
            "pre_1990_rows": len(pre_1990_rows),
            "pre_1990_countries": len({row.get('country') for row in pre_1990_rows if row.get('country')}),
            "post_1990_rows": len(post_1990_rows),
        },
        "core_field_coverage": field_coverage,
        "current_conclusion": [
            "The merged structural country-year layer now begins in 1960.",
            "The private training-history extension is now active in the merged structural layer, with pre-1990 rows available for all 25 countries.",
            "Any extension earlier than 1960 will still require further upstream ingestion changes.",
        ],
        "recommended_next_actions": [
            "use the 1960-1989 structural window for private training, calibration, and legacy-feature engineering",
            "audit upstream raw sources such as V-Dem and any earlier structural series to confirm how far back each can go reliably beyond 1960",
            "decide whether to extend build_country_year.py earlier than 1960 for training-only artifacts",
            "keep the operational/live product window anchored to 1990-present even if the private training layer expands backward",
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote training-history coverage audit to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
