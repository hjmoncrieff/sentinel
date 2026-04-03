#!/usr/bin/env python3
"""
Review proxy security-fragmentation-jump positives country by country.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL = ROOT / "data" / "modeling" / "country_month_panel.json"
OUT = ROOT / "data" / "review" / "security_fragmentation_jump_target_review.json"

REVIEW_COUNTRIES = [
    "Brazil",
    "Colombia",
    "Ecuador",
    "El Salvador",
    "Guatemala",
    "Haiti",
    "Honduras",
    "Mexico",
    "Peru",
    "Venezuela",
]


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def offset_month(panel_date: str, months: int) -> str:
    year, month = map(int, panel_date[:7].split("-"))
    total = year * 12 + (month - 1) + months
    next_year = total // 12
    next_month_num = total % 12 + 1
    return f"{next_year:04d}-{next_month_num:02d}-01"


def classify_case(candidate: dict) -> tuple[str, str]:
    if (
        candidate.get("high_severity_episode_count", 0) > 0
        and candidate.get("episode_construct_security_fragmentation_count", 0) > 0
        and (
            candidate.get("event_type_conflict_count", 0) > 0
            or candidate.get("event_type_oc_count", 0) > 0
            or candidate.get("event_shock_flag", 0) > 0
        )
    ):
        return "strong", "future month contains a high-severity fragmentation-linked jump"
    if (
        candidate.get("fragmenting_episode_count", 0) > 0
        and candidate.get("episode_construct_security_fragmentation_count", 0) > 0
    ):
        return "plausible", "future month contains a fragmenting security-fragmentation sequence"
    if (
        candidate.get("episode_construct_security_fragmentation_count", 0) > 0
        and (
            candidate.get("event_type_conflict_count", 0) > 0
            or candidate.get("event_type_oc_count", 0) > 0
            or candidate.get("external_pressure_signal_present", 0) > 0
            or candidate.get("economic_fragility_signal_present", 0) > 0
        )
    ):
        return "review", "future month contains broader fragmentation stress but not yet a clear jump"
    return "weak", "future month looks more like background stress than a clear fragmentation jump"


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
        positives = [row for row in country_rows if int(row.get("security_fragmentation_jump_next_3m", 0)) == 1]
        cases = []
        counts = {"strong": 0, "plausible": 0, "review": 0, "weak": 0}
        for row in positives:
            future_rows = [
                row_by_date.get(offset_month(row["panel_date"], i))
                for i in (1, 2, 3)
            ]
            future_rows = [candidate for candidate in future_rows if candidate]
            if not future_rows:
                continue
            best = max(
                future_rows,
                key=lambda candidate: int(candidate.get("security_fragmentation_jump_signal_score_next_1m", 0) or 0),
            )
            rating, note = classify_case(best)
            counts[rating] += 1
            cases.append({
                "trigger_month": row["panel_date"],
                "future_reference_month": best["panel_date"],
                "score_3m": row.get("security_fragmentation_jump_signal_score_next_3m"),
                "label_3m": row.get("security_fragmentation_jump_signal_label_next_3m"),
                "rating": rating,
                "note": note,
                "future_profile": {
                    "high_severity_episode_count": best.get("high_severity_episode_count", 0),
                    "fragmenting_episode_count": best.get("fragmenting_episode_count", 0),
                    "episode_construct_security_fragmentation_count": best.get("episode_construct_security_fragmentation_count", 0),
                    "event_shock_flag": best.get("event_shock_flag", 0),
                    "event_type_conflict_count": best.get("event_type_conflict_count", 0),
                    "event_type_oc_count": best.get("event_type_oc_count", 0),
                    "event_type_protest_count": best.get("event_type_protest_count", 0),
                    "external_pressure_signal_present": best.get("external_pressure_signal_present", 0),
                    "economic_fragility_signal_present": best.get("economic_fragility_signal_present", 0),
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
        "status": "private_internal_security_fragmentation_jump_review",
        "source_file": str(PANEL.relative_to(ROOT)),
        "target_rule": payload.get("target_definitions", {}).get("security_fragmentation_jump_next_3m", {}).get("rule_version"),
        "review_countries": REVIEW_COUNTRIES,
        "countries": countries,
    }


def main() -> None:
    payload = review()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote security-fragmentation-jump review to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
