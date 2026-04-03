#!/usr/bin/env python3
"""
Review protest-heavy acute political-risk benchmark cases.

This runner is private/internal. It is meant to help interpret whether protest
activity behaves like acute deterioration signal or broad contestation
background in the current panel, without immediately changing the scoring rule.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL = ROOT / "data" / "modeling" / "country_month_panel.json"
BENCHMARK = ROOT / "data" / "modeling" / "acute_political_risk_benchmark_tiers.json"
OUT = ROOT / "data" / "review" / "acute_political_risk_protest_review.json"

TARGET_TIERS = {"gold_positive", "hard_negative"}


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def coerce_float(value: object) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except Exception:
        return 0.0


def round_mean(values: list[float]) -> float:
    return round(mean(values), 3) if values else 0.0


def summarize_rows(rows: list[dict]) -> dict:
    return {
        "rows": len(rows),
        "mean_event_type_protest_count": round_mean([coerce_float(row.get("event_type_protest_count")) for row in rows]),
        "mean_event_type_conflict_count": round_mean([coerce_float(row.get("event_type_conflict_count")) for row in rows]),
        "mean_protest_acute_signal_score": round_mean([coerce_float(row.get("protest_acute_signal_score")) for row in rows]),
        "mean_protest_background_load_score": round_mean([coerce_float(row.get("protest_background_load_score")) for row in rows]),
        "mean_transition_contestation_load_score": round_mean([coerce_float(row.get("transition_contestation_load_score")) for row in rows]),
        "mean_acute_political_risk_signal_score_next_1m": round_mean([coerce_float(row.get("acute_political_risk_signal_score_next_1m")) for row in rows]),
    }


def case_payload(row: dict, tier: str) -> dict:
    return {
        "country": row.get("country"),
        "panel_date": row.get("panel_date"),
        "tier": tier,
        "acute_political_risk_signal_score_next_1m": row.get("acute_political_risk_signal_score_next_1m"),
        "acute_political_risk_signal_label_next_1m": row.get("acute_political_risk_signal_label_next_1m"),
        "event_type_protest_count": row.get("event_type_protest_count"),
        "event_type_conflict_count": row.get("event_type_conflict_count"),
        "high_severity_episode_count": row.get("high_severity_episode_count"),
        "fragmenting_episode_count": row.get("fragmenting_episode_count"),
        "episode_type_protest_security_escalation_count": row.get("episode_type_protest_security_escalation_count"),
        "protest_acute_signal_score": row.get("protest_acute_signal_score"),
        "protest_background_load_score": row.get("protest_background_load_score"),
        "transition_contestation_load_score": row.get("transition_contestation_load_score"),
        "transition_specificity_gap": row.get("transition_specificity_gap"),
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

    tier_rows: dict[str, list[dict]] = {tier: [] for tier in TARGET_TIERS}
    protest_cases: dict[str, list[dict]] = {tier: [] for tier in TARGET_TIERS}

    for item in benchmark_rows:
        tier = str(item.get("tier") or "")
        if tier not in TARGET_TIERS:
            continue
        row = panel_lookup.get((str(item.get("country") or ""), str(item.get("panel_date") or "")))
        if not row:
            continue
        tier_rows[tier].append(row)
        if (
            coerce_float(row.get("event_type_protest_count")) > 0
            or coerce_float(row.get("protest_acute_signal_score")) >= 1.0
            or coerce_float(row.get("protest_background_load_score")) >= 1.0
        ):
            protest_cases[tier].append(case_payload(row, tier))

    output = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_internal_acute_political_risk_protest_review",
        "panel_file": str(PANEL.relative_to(ROOT)),
        "benchmark_file": str(BENCHMARK.relative_to(ROOT)),
        "summary": {
            "gold_positive": summarize_rows(tier_rows["gold_positive"]),
            "hard_negative": summarize_rows(tier_rows["hard_negative"]),
        },
        "protest_case_counts": {
            tier: len(rows) for tier, rows in protest_cases.items()
        },
        "protest_cases": {
            tier: rows for tier, rows in protest_cases.items()
        },
        "current_takeaway": [
            "Protest activity is now split into acute-signal and background-load fields in the panel.",
            "These protest-specific fields are currently interpretive aids; their first direct use in acute-risk scoring increased false positives and was backed out.",
            "This review artifact should help identify which protest-heavy months are true acute deterioration versus broad contestation near misses.",
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote acute protest review to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
