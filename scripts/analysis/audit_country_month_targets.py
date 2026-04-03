#!/usr/bin/env python3
"""
Audit proxy target distribution in the private SENTINEL country-month panel.

Outputs:
  data/modeling/country_month_target_audit.json
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL = ROOT / "data" / "modeling" / "country_month_panel.json"
OUT = ROOT / "data" / "modeling" / "country_month_target_audit.json"


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 3)


def main() -> None:
    payload = load_json(PANEL)
    rows = payload.get("rows", []) if isinstance(payload, dict) else []

    totals = {
        "rows": len(rows),
        "window_complete_1m": 0,
        "window_complete_3m": 0,
        "watch_positives_1m": 0,
        "watch_positives_3m": 0,
        "fit_positives_1m": 0,
        "fit_positives_3m": 0,
        "adjudicated_1m": 0,
    }
    by_country: dict[str, dict] = defaultdict(lambda: {
        "rows": 0,
        "watch_positives_1m": 0,
        "watch_positives_3m": 0,
        "fit_positives_1m": 0,
        "fit_positives_3m": 0,
        "window_complete_1m": 0,
        "window_complete_3m": 0,
        "first_watch_positive_1m": None,
        "first_watch_positive_3m": None,
        "first_fit_positive_1m": None,
        "first_fit_positive_3m": None,
    })
    by_year: dict[int, dict] = defaultdict(lambda: {
        "rows": 0,
        "watch_positives_1m": 0,
        "watch_positives_3m": 0,
        "fit_positives_1m": 0,
        "fit_positives_3m": 0,
    })

    for row in rows:
        country = row["country"]
        year = int(row["year"])
        watch_positive_1m = int(row.get("irregular_transition_next_1m") or 0)
        watch_positive_3m = int(row.get("irregular_transition_next_3m") or 0)
        fit_positive_1m = int((row.get("irregular_transition_fit_score_next_1m") or 0) >= 4)
        fit_positive_3m = int((row.get("irregular_transition_fit_score_next_3m") or 0) >= 4)
        complete_1m = int(row.get("irregular_transition_observation_window_complete_1m") or 0)
        complete_3m = int(row.get("irregular_transition_observation_window_complete_3m") or 0)
        panel_date = row["panel_date"]

        totals["window_complete_1m"] += complete_1m
        totals["window_complete_3m"] += complete_3m
        totals["watch_positives_1m"] += watch_positive_1m
        totals["watch_positives_3m"] += watch_positive_3m
        totals["fit_positives_1m"] += fit_positive_1m
        totals["fit_positives_3m"] += fit_positive_3m
        country_bucket = by_country[country]
        country_bucket["rows"] += 1
        country_bucket["watch_positives_1m"] += watch_positive_1m
        country_bucket["watch_positives_3m"] += watch_positive_3m
        country_bucket["fit_positives_1m"] += fit_positive_1m
        country_bucket["fit_positives_3m"] += fit_positive_3m
        country_bucket["window_complete_1m"] += complete_1m
        country_bucket["window_complete_3m"] += complete_3m
        if watch_positive_1m and country_bucket["first_watch_positive_1m"] is None:
            country_bucket["first_watch_positive_1m"] = panel_date
        if watch_positive_3m and country_bucket["first_watch_positive_3m"] is None:
            country_bucket["first_watch_positive_3m"] = panel_date
        if fit_positive_1m and country_bucket["first_fit_positive_1m"] is None:
            country_bucket["first_fit_positive_1m"] = panel_date
        if fit_positive_3m and country_bucket["first_fit_positive_3m"] is None:
            country_bucket["first_fit_positive_3m"] = panel_date

        year_bucket = by_year[year]
        year_bucket["rows"] += 1
        year_bucket["watch_positives_1m"] += watch_positive_1m
        year_bucket["watch_positives_3m"] += watch_positive_3m
        year_bucket["fit_positives_1m"] += fit_positive_1m
        year_bucket["fit_positives_3m"] += fit_positive_3m

    totals["adjudicated_1m"] = sum(
        1
        for row in rows
        if str(row.get("irregular_transition_label_source") or "") != "proxy_rule"
    )

    output = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_internal_target_audit",
        "source_file": str(PANEL.relative_to(ROOT)),
        "watch_target_rule": rows[0].get("irregular_transition_target_rule") if rows else None,
        "fit_target_rule": rows[0].get("irregular_transition_fit_target_rule") if rows else None,
        "summary": {
            **totals,
            "watch_positive_rate_1m_pct": pct(totals["watch_positives_1m"], totals["rows"]),
            "watch_positive_rate_3m_pct": pct(totals["watch_positives_3m"], totals["rows"]),
            "fit_positive_rate_1m_pct": pct(totals["fit_positives_1m"], totals["rows"]),
            "fit_positive_rate_3m_pct": pct(totals["fit_positives_3m"], totals["rows"]),
            "adjudicated_1m_pct": pct(totals["adjudicated_1m"], totals["rows"]),
            "window_complete_1m_pct": pct(totals["window_complete_1m"], totals["rows"]),
            "window_complete_3m_pct": pct(totals["window_complete_3m"], totals["rows"]),
        },
        "by_country": [
            {
                "country": country,
                **bucket,
                "watch_positive_rate_1m_pct": pct(bucket["watch_positives_1m"], bucket["rows"]),
                "watch_positive_rate_3m_pct": pct(bucket["watch_positives_3m"], bucket["rows"]),
                "fit_positive_rate_1m_pct": pct(bucket["fit_positives_1m"], bucket["rows"]),
                "fit_positive_rate_3m_pct": pct(bucket["fit_positives_3m"], bucket["rows"]),
            }
            for country, bucket in sorted(by_country.items())
        ],
        "by_year": [
            {
                "year": year,
                **bucket,
                "watch_positive_rate_1m_pct": pct(bucket["watch_positives_1m"], bucket["rows"]),
                "watch_positive_rate_3m_pct": pct(bucket["watch_positives_3m"], bucket["rows"]),
                "fit_positive_rate_1m_pct": pct(bucket["fit_positives_1m"], bucket["rows"]),
                "fit_positive_rate_3m_pct": pct(bucket["fit_positives_3m"], bucket["rows"]),
            }
            for year, bucket in sorted(by_year.items())
        ],
    }

    OUT.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Wrote target audit to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
