#!/usr/bin/env python3
"""
Review proxy irregular-transition positives country by country.

This runner is private/internal. It helps separate plausible rupture signals
from broad conflict/governance stress before the project moves to adjudicated
targets.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL = ROOT / "data" / "modeling" / "country_month_panel.json"
OUT = ROOT / "data" / "review" / "irregular_transition_target_review.json"

REVIEW_COUNTRIES = [
    "Colombia",
    "Bolivia",
    "Chile",
    "Honduras",
    "Mexico",
    "Haiti",
    "Venezuela",
    "Brazil",
    "El Salvador",
]


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def next_month(panel_date: str) -> str:
    year, month = map(int, panel_date[:7].split("-"))
    total = year * 12 + (month - 1) + 1
    next_year = total // 12
    next_month_num = total % 12 + 1
    return f"{next_year:04d}-{next_month_num:02d}-01"


def classify_case(candidate: dict) -> tuple[str, str]:
    if candidate.get("event_type_coup_count", 0) > 0:
        if candidate.get("high_severity_episode_count", 0) > 0:
            return "strong", "next month contains a coup-coded and high-severity episode"
        return "strong", "next month contains a coup-coded event"
    if candidate.get("high_severity_episode_count", 0) > 0 and candidate.get("episode_construct_regime_vulnerability_count", 0) > 0:
        return "plausible", "next month contains a high-severity regime-vulnerability episode"
    if (
        candidate.get("escalating_episode_count", 0) > 0
        and candidate.get("episode_construct_regime_vulnerability_count", 0) > 0
        and candidate.get("deed_type_destabilizing_count", 0) > 0
        and candidate.get("event_type_conflict_count", 0) > 0
    ):
        return "plausible", "next month contains an escalating destabilizing regime-linked conflict sequence"
    if candidate.get("deed_type_destabilizing_count", 0) >= 2 and candidate.get("event_type_conflict_count", 0) >= 2:
        return "review", "next month shows concentrated destabilizing conflict but not a clear rupture episode"
    return "weak", "next month looks more like severe contestation than a clean irregular-transition signal"


def review() -> dict:
    payload = load_json(PANEL)
    rows = payload.get("rows", []) if isinstance(payload, dict) else payload
    by_country: dict[str, list[dict]] = {}
    for country in REVIEW_COUNTRIES:
        country_rows = [row for row in rows if row.get("country") == country]
        country_rows.sort(key=lambda row: row["panel_date"])
        by_country[country] = country_rows

    countries = []
    for country in REVIEW_COUNTRIES:
        country_rows = by_country[country]
        row_by_date = {row["panel_date"]: row for row in country_rows}
        positives = [row for row in country_rows if int(row.get("irregular_transition_next_1m", 0)) == 1]
        cases = []
        counts = {"strong": 0, "plausible": 0, "review": 0, "weak": 0}
        for row in positives:
            next_row = row_by_date.get(next_month(row["panel_date"]))
            if not next_row:
                continue
            rating, note = classify_case(next_row)
            counts[rating] += 1
            cases.append({
                "trigger_month": row["panel_date"],
                "next_month": next_row["panel_date"],
                "score_1m": row.get("irregular_transition_signal_score_next_1m"),
                "label_1m": row.get("irregular_transition_signal_label_next_1m"),
                "rating": rating,
                "note": note,
                "next_month_profile": {
                    "event_type_coup_count": next_row.get("event_type_coup_count", 0),
                    "high_severity_episode_count": next_row.get("high_severity_episode_count", 0),
                    "escalating_episode_count": next_row.get("escalating_episode_count", 0),
                    "episode_construct_regime_vulnerability_count": next_row.get("episode_construct_regime_vulnerability_count", 0),
                    "deed_type_destabilizing_count": next_row.get("deed_type_destabilizing_count", 0),
                    "event_type_conflict_count": next_row.get("event_type_conflict_count", 0),
                    "event_type_protest_count": next_row.get("event_type_protest_count", 0),
                },
            })
        countries.append({
            "country": country,
            "positive_case_count": len(cases),
            "rating_summary": counts,
            "cases": cases,
        })

    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_internal_target_review",
        "source_file": str(PANEL.relative_to(ROOT)),
        "target_rule": payload.get("target_definitions", {}).get("irregular_transition_next_1m", {}).get("rule_version"),
        "review_countries": REVIEW_COUNTRIES,
        "countries": countries,
    }


def main() -> None:
    payload = review()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote target review to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
