#!/usr/bin/env python3
"""
Build a private reviewed-negative queue for irregular-transition modeling.

This stage proposes lower-intensity and background country-months that can be
reviewed as explicit negatives for the fit-ready sample. The goal is to broaden
the sample beyond severe-vs-severe comparisons without changing the operational
monitoring target.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL = ROOT / "data" / "modeling" / "country_month_panel.json"
GOLD = ROOT / "data" / "modeling" / "gold_irregular_transition_labels.json"
ADJUDICATED = ROOT / "data" / "modeling" / "adjudicated_irregular_transition_labels.json"
REVIEW = ROOT / "data" / "review" / "irregular_transition_target_review.json"
OUT = ROOT / "data" / "review" / "irregular_transition_negative_queue.json"
LOCAL_NEGATIVE_DECISIONS = ROOT / "data" / "review" / "reviewed_negative_decisions.local.json"

MAX_PER_COUNTRY = 3
MIN_YEAR = 2018


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def load_local_negative_keys() -> set[tuple[str, str, str]]:
    if not LOCAL_NEGATIVE_DECISIONS.exists():
        return set()
    payload = load_json(LOCAL_NEGATIVE_DECISIONS)
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    keys: set[tuple[str, str, str]] = set()
    for row in rows:
        country = str(row.get("country") or "").strip()
        panel_date = str(row.get("panel_date") or "").strip()
        target_name = str(row.get("target_name") or "").strip()
        if country and panel_date and target_name:
            keys.add((country, panel_date, target_name))
    return keys


def load_reviewed_negative_keys() -> tuple[set[tuple[str, str]], set[str]]:
    reviewed_keys: set[tuple[str, str]] = set()
    countries: set[str] = set()

    adjudicated_payload = load_json(ADJUDICATED)
    adjudicated_rows = adjudicated_payload.get("rows", []) if isinstance(adjudicated_payload, dict) else []
    for row in adjudicated_rows:
        if str(row.get("rating") or "").strip().lower() != "reviewed_watch":
            continue
        key = (str(row.get("country") or ""), str(row.get("panel_date") or ""))
        reviewed_keys.add(key)
        countries.add(key[0])

    review_payload = load_json(REVIEW)
    review_countries = review_payload.get("countries", []) if isinstance(review_payload, dict) else []
    for country_row in review_countries:
        country = str(country_row.get("country") or "")
        for case in country_row.get("cases", []):
            if str(case.get("rating") or "").strip().lower() != "weak":
                continue
            key = (country, str(case.get("trigger_month") or ""))
            reviewed_keys.add(key)
            countries.add(country)

    local_keys = load_local_negative_keys()
    for country, panel_date, target_name in local_keys:
        if target_name != "irregular_transition_next_1m":
            continue
        reviewed_keys.add((country, panel_date))
        countries.add(country)

    return reviewed_keys, countries


def current_positive_keys() -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()

    gold_payload = load_json(GOLD)
    gold_rows = gold_payload.get("rows", []) if isinstance(gold_payload, dict) else []
    for row in gold_rows:
        keys.add((str(row.get("country") or ""), str(row.get("panel_date") or "")))

    adjudicated_payload = load_json(ADJUDICATED)
    adjudicated_rows = adjudicated_payload.get("rows", []) if isinstance(adjudicated_payload, dict) else []
    for row in adjudicated_rows:
        if int(row.get("label") or 0) != 1:
            continue
        keys.add((str(row.get("country") or ""), str(row.get("panel_date") or "")))

    return keys


def classify_candidate(row: dict) -> tuple[str | None, int]:
    score = int(row.get("irregular_transition_signal_score_next_1m") or 0)
    label = str(row.get("irregular_transition_signal_label_next_1m") or "")
    event_count = int(row.get("event_count") or 0)
    episode_count = int(row.get("episode_count") or 0)
    high_salience = int(row.get("high_salience_event_count") or 0)
    high_severity_episode = int(row.get("high_severity_episode_count") or 0)
    coup_count = int(row.get("event_type_coup_count") or 0)
    destabilizing = int(row.get("deed_type_destabilizing_count") or 0)
    regime_episode = int(row.get("episode_construct_regime_vulnerability_count") or 0)

    if score > 2 or label == "elevated":
        return None, -1
    if coup_count > 0 or high_severity_episode > 0:
        return None, -1
    if destabilizing > 1 or regime_episode > 1:
        return None, -1
    if high_salience > 1:
        return None, -1

    if score <= 1 and (event_count > 0 or episode_count > 0 or label == "watch"):
        return "low_intensity_negative_candidate", 0
    if score == 0 and event_count == 0 and episode_count == 0:
        return "background_negative_candidate", 1
    if score == 2 and high_salience == 0 and destabilizing == 0:
        return "borderline_negative_candidate", 2
    return None, -1


def build() -> dict:
    panel_payload = load_json(PANEL)
    rows = panel_payload.get("rows", []) if isinstance(panel_payload, dict) else []

    positive_keys = current_positive_keys()
    reviewed_negative_keys, negative_countries = load_reviewed_negative_keys()
    local_negative_keys = load_local_negative_keys()

    by_country: dict[str, list[dict]] = {}
    all_countries = sorted({str(row.get("country") or "") for row in rows})

    for row in rows:
        country = str(row.get("country") or "")
        panel_date = str(row.get("panel_date") or "")
        target_name = "irregular_transition_next_1m"
        key = (country, panel_date)
        local_key = (country, panel_date, target_name)
        if not country or not panel_date:
            continue
        if int(row.get("irregular_transition_observation_window_complete_1m") or 0) != 1:
            continue
        if int(row.get("year") or 0) < MIN_YEAR:
            continue
        if key in positive_keys or key in reviewed_negative_keys or local_key in local_negative_keys:
            continue

        candidate_type, candidate_rank = classify_candidate(row)
        if not candidate_type:
            continue

        priority_bucket = "expand_country_coverage" if country not in negative_countries else "deepen_existing_negative_country"
        by_country.setdefault(country, []).append({
            "country": country,
            "panel_date": panel_date,
            "target_name": target_name,
            "current_proxy_score_1m": int(row.get("irregular_transition_signal_score_next_1m") or 0),
            "current_proxy_signal_label": str(row.get("irregular_transition_signal_label_next_1m") or ""),
            "candidate_type": candidate_type,
            "priority_bucket": priority_bucket,
            "recommended_review_label": 0,
            "event_count": int(row.get("event_count") or 0),
            "episode_count": int(row.get("episode_count") or 0),
            "high_salience_event_count": int(row.get("high_salience_event_count") or 0),
            "dominant_event_type": row.get("dominant_event_type"),
            "dominant_episode_type": row.get("dominant_episode_type"),
            "review_hint": (
                "Useful low-intensity negative candidate for the fit sample."
                if candidate_type == "low_intensity_negative_candidate"
                else (
                    "Useful quiet/background negative candidate for the fit sample."
                    if candidate_type == "background_negative_candidate"
                    else "Borderline negative candidate; review carefully before using for fit."
                )
            ),
            "_sort_priority": 0 if priority_bucket == "expand_country_coverage" else 1,
            "_sort_candidate_rank": candidate_rank,
        })

    queue_rows = []
    for country, country_rows in by_country.items():
        country_rows.sort(
            key=lambda item: (
                item["_sort_priority"],
                item["_sort_candidate_rank"],
                item["panel_date"],
            ),
            reverse=False,
        )
        selected = sorted(country_rows[:MAX_PER_COUNTRY], key=lambda item: item["panel_date"], reverse=True)
        for row in selected:
            row.pop("_sort_priority", None)
            row.pop("_sort_candidate_rank", None)
            queue_rows.append(row)

    priority_order = {"expand_country_coverage": 0, "deepen_existing_negative_country": 1}
    queue_rows.sort(
        key=lambda item: (
            priority_order.get(item["priority_bucket"], 9),
            item["country"],
            item["panel_date"],
        ),
        reverse=False,
    )

    countries_without_reviewed_negatives = sorted(set(all_countries) - negative_countries)

    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_internal_negative_review_queue",
        "panel_file": str(PANEL.relative_to(ROOT)),
        "gold_file": str(GOLD.relative_to(ROOT)),
        "adjudicated_file": str(ADJUDICATED.relative_to(ROOT)),
        "review_file": str(REVIEW.relative_to(ROOT)),
        "local_decision_file": (
            str(LOCAL_NEGATIVE_DECISIONS.relative_to(ROOT)) if LOCAL_NEGATIVE_DECISIONS.exists() else None
        ),
        "description": (
            "Candidate lower-intensity and background country-months that can be "
            "reviewed as explicit negatives for irregular-transition model fitting."
        ),
        "selection_rules": {
            "min_year": MIN_YEAR,
            "max_candidates_per_country": MAX_PER_COUNTRY,
            "exclude": [
                "gold positives",
                "adjudicated positives",
                "already reviewed negatives",
                "existing local negative decisions",
                "months without a complete 1m observation window",
                "months with coup or high-severity episode signals",
            ],
            "candidate_types": [
                "low_intensity_negative_candidate",
                "background_negative_candidate",
                "borderline_negative_candidate",
            ],
        },
        "summary": {
            "reviewed_negative_country_count": len(negative_countries),
            "countries_without_reviewed_negatives": countries_without_reviewed_negatives,
            "queue_rows": len(queue_rows),
            "expand_country_coverage_rows": sum(1 for row in queue_rows if row["priority_bucket"] == "expand_country_coverage"),
            "deepen_existing_negative_country_rows": sum(1 for row in queue_rows if row["priority_bucket"] == "deepen_existing_negative_country"),
        },
        "rows": queue_rows,
    }


def main() -> None:
    payload = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote negative review queue to {OUT.relative_to(ROOT)}")
    print(f"Rows written: {payload['summary']['queue_rows']}")


if __name__ == "__main__":
    main()
