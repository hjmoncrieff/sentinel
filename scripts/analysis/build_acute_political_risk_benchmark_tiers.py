#!/usr/bin/env python3
"""
Build a tiered benchmark set for acute political-risk modeling.

This stage consolidates the current reviewed acute-risk benchmark material into
three interpretable tiers:

- gold_positive
- hard_negative
- easy_negative
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL = ROOT / "data" / "modeling" / "country_month_panel.json"
GOLD = ROOT / "data" / "modeling" / "gold_acute_political_risk_labels.json"
REVIEW = ROOT / "data" / "review" / "acute_political_risk_target_review.json"
OUT = ROOT / "data" / "modeling" / "acute_political_risk_benchmark_tiers.json"

MAX_HARD_PER_COUNTRY = 2
MAX_EASY_PER_COUNTRY = 2
MIN_YEAR = 1990


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def hard_negative_candidate(row: dict) -> bool:
    score = int(row.get("acute_political_risk_signal_score_next_1m") or 0)
    if score < 2:
        return False
    return any(
        int(row.get(field) or 0) > 0
        for field in [
            "high_severity_episode_count",
            "fragmenting_episode_count",
            "event_shock_flag",
            "episode_construct_regime_vulnerability_count",
            "episode_construct_security_fragmentation_count",
        ]
    )


def easy_negative_candidate(row: dict) -> bool:
    score = int(row.get("acute_political_risk_signal_score_next_1m") or 0)
    if score > 1:
        return False
    return all(
        int(row.get(field) or 0) == 0
        for field in [
            "high_severity_episode_count",
            "fragmenting_episode_count",
            "event_shock_flag",
            "episode_construct_regime_vulnerability_count",
            "episode_construct_security_fragmentation_count",
        ]
    )


def build() -> dict:
    panel_payload = load_json(PANEL)
    panel_rows = panel_payload.get("rows", []) if isinstance(panel_payload, dict) else panel_payload
    review_payload = load_json(REVIEW)
    review_countries = [str(row.get("country") or "") for row in review_payload.get("countries", [])]
    gold_payload = load_json(GOLD)
    gold_rows = gold_payload.get("rows", []) if isinstance(gold_payload, dict) else gold_payload
    gold_keys = {(str(row.get("country") or ""), str(row.get("panel_date") or "")) for row in gold_rows}

    tier_rows = []

    for row in gold_rows:
        tier_rows.append({
            "country": str(row.get("country") or ""),
            "panel_date": str(row.get("panel_date") or ""),
            "target_name": "acute_political_risk_next_1m",
            "tier": "gold_positive",
            "label": 1,
            "tier_reason": "stricter adjudicated acute-risk gold positive",
            "source_file": str(GOLD.relative_to(ROOT)),
            "source_rating": row.get("rating"),
            "proxy_score_1m": row.get("proxy_score_1m"),
            "note": row.get("note"),
        })

    for country in review_countries:
        country_rows = [
            row for row in panel_rows
            if row.get("country") == country
            and int(row.get("year") or 0) >= MIN_YEAR
            and (country, str(row.get("panel_date") or "")) not in gold_keys
            and int(row.get("acute_political_risk_next_1m") or 0) == 0
        ]

        hard_rows = [
            row for row in country_rows
            if hard_negative_candidate(row)
        ]
        hard_rows.sort(
            key=lambda row: (
                -int(row.get("acute_political_risk_signal_score_next_1m") or 0),
                -int(row.get("high_severity_episode_count") or 0),
                -int(row.get("fragmenting_episode_count") or 0),
                -int(row.get("event_shock_flag") or 0),
                str(row.get("panel_date") or ""),
            )
        )
        for row in hard_rows[:MAX_HARD_PER_COUNTRY]:
            tier_rows.append({
                "country": country,
                "panel_date": str(row.get("panel_date") or ""),
                "target_name": "acute_political_risk_next_1m",
                "tier": "hard_negative",
                "label": 0,
                "tier_reason": "near-miss acute-risk month with stress markers but no gold-positive adjudication",
                "source_file": str(PANEL.relative_to(ROOT)),
                "proxy_score_1m": row.get("acute_political_risk_signal_score_next_1m"),
                "proxy_label_1m": row.get("acute_political_risk_signal_label_next_1m"),
            })

        chosen_hard_dates = {str(row.get("panel_date") or "") for row in hard_rows[:MAX_HARD_PER_COUNTRY]}
        easy_rows = [
            row for row in country_rows
            if str(row.get("panel_date") or "") not in chosen_hard_dates and easy_negative_candidate(row)
        ]
        easy_rows.sort(
            key=lambda row: (
                int(row.get("acute_political_risk_signal_score_next_1m") or 0),
                -int(row.get("year") or 0),
                str(row.get("panel_date") or ""),
            )
        )
        for row in easy_rows[:MAX_EASY_PER_COUNTRY]:
            tier_rows.append({
                "country": country,
                "panel_date": str(row.get("panel_date") or ""),
                "target_name": "acute_political_risk_next_1m",
                "tier": "easy_negative",
                "label": 0,
                "tier_reason": "low-signal or background acute-risk month with minimal stress markers",
                "source_file": str(PANEL.relative_to(ROOT)),
                "proxy_score_1m": row.get("acute_political_risk_signal_score_next_1m"),
                "proxy_label_1m": row.get("acute_political_risk_signal_label_next_1m"),
            })

    deduped: dict[tuple[str, str, str], dict] = {}
    for row in tier_rows:
        deduped[(row["country"], row["panel_date"], row["tier"])] = row
    tier_rows = [deduped[key] for key in sorted(deduped)]

    summary = {
        "gold_positive_rows": sum(1 for row in tier_rows if row["tier"] == "gold_positive"),
        "hard_negative_rows": sum(1 for row in tier_rows if row["tier"] == "hard_negative"),
        "easy_negative_rows": sum(1 for row in tier_rows if row["tier"] == "easy_negative"),
        "countries": sorted({row["country"] for row in tier_rows}),
        "minimum_year": MIN_YEAR,
    }

    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_internal_acute_political_risk_benchmark_tier_set",
        "target_name": "acute_political_risk_next_1m",
        "description": (
            "Tiered benchmark reference set for acute political-risk modeling. "
            "This groups current reviewed benchmark material into gold positives, "
            "hard negatives, and easy negatives."
        ),
        "source_files": {
            "panel": str(PANEL.relative_to(ROOT)),
            "gold_labels": str(GOLD.relative_to(ROOT)),
            "review_artifact": str(REVIEW.relative_to(ROOT)),
        },
        "tier_rules": {
            "gold_positive": "rows included in the stricter acute political-risk gold subset",
            "hard_negative": (
                "non-gold months from benchmark countries with acute-risk watch "
                "scores and real stress markers such as fragmenting episodes, "
                "high-severity episodes, or shock flags"
            ),
            "easy_negative": "non-gold months from benchmark countries with low acute-risk scores and minimal stress markers",
        },
        "summary": summary,
        "rows": tier_rows,
    }


def main() -> None:
    payload = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote acute-risk benchmark tiers to {OUT.relative_to(ROOT)}")
    print(
        "Rows:",
        payload["summary"]["gold_positive_rows"] + payload["summary"]["hard_negative_rows"] + payload["summary"]["easy_negative_rows"],
    )


if __name__ == "__main__":
    main()
