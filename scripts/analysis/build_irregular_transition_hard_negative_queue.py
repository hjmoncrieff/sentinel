#!/usr/bin/env python3
"""
Build a private hard-negative benchmark queue for irregular-transition modeling.

This stage isolates a very small set of country-months that still look
transition-like because of episode or structural-memory signals, but are not in
the current positive or gold layers. These are meant to be difficult reviewed
negatives for benchmark testing rather than routine background negatives.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL = ROOT / "data" / "modeling" / "country_month_panel.json"
GOLD = ROOT / "data" / "modeling" / "gold_irregular_transition_labels.json"
ADJUDICATED = ROOT / "data" / "modeling" / "adjudicated_irregular_transition_labels.json"
LOCAL_NEGATIVE_DECISIONS = ROOT / "data" / "review" / "reviewed_negative_decisions.local.json"
OUT = ROOT / "data" / "review" / "irregular_transition_hard_negative_queue.json"

MIN_YEAR = 1990


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def positive_keys() -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for path in (GOLD, ADJUDICATED):
        payload = load_json(path)
        rows = payload.get("rows", []) if isinstance(payload, dict) else payload
        for row in rows:
            country = str(row.get("country") or "")
            panel_date = str(row.get("panel_date") or "")
            if not country or not panel_date:
                continue
            if path == ADJUDICATED and int(row.get("label") or 0) != 1:
                continue
            keys.add((country, panel_date))
    return keys


def local_negative_keys() -> set[tuple[str, str]]:
    if not LOCAL_NEGATIVE_DECISIONS.exists():
        return set()
    payload = load_json(LOCAL_NEGATIVE_DECISIONS)
    rows = payload.get("rows", []) if isinstance(payload, dict) else payload
    keys: set[tuple[str, str]] = set()
    for row in rows:
        if int(row.get("label") or 0) != 0:
            continue
        if str(row.get("target_name") or "irregular_transition_next_1m") != "irregular_transition_next_1m":
            continue
        country = str(row.get("country") or "")
        panel_date = str(row.get("panel_date") or "")
        if country and panel_date:
            keys.add((country, panel_date))
    return keys


def hard_negative_reason(row: dict) -> list[str]:
    reasons: list[str] = []
    if int(row.get("regime_shift_flag") or 0) >= 1:
        reasons.append("major regime-shift flag active")
    polyarchy_delta = row.get("polyarchy_delta_1y")
    try:
        if polyarchy_delta is not None and float(polyarchy_delta) < -0.01:
            reasons.append("meaningful one-year democratic decline")
    except (TypeError, ValueError):
        pass
    if int(row.get("high_severity_episode_count") or 0) > 0:
        reasons.append("contains a high-severity episode without a reviewed transition label")
    if int(row.get("escalating_episode_count") or 0) > 0:
        reasons.append("contains an escalating episode")
    if int(row.get("high_salience_event_count") or 0) > 0:
        reasons.append("contains high-salience events")
    return reasons


def build() -> dict:
    payload = load_json(PANEL)
    rows = payload.get("rows", []) if isinstance(payload, dict) else payload
    positives = positive_keys()
    reviewed_negatives = local_negative_keys()

    queue_rows = []
    for row in rows:
        country = str(row.get("country") or "")
        panel_date = str(row.get("panel_date") or "")
        if not country or not panel_date:
            continue
        if int(row.get("year") or 0) < MIN_YEAR:
            continue
        if int(row.get("irregular_transition_observation_window_complete_1m") or 0) != 1:
            continue
        key = (country, panel_date)
        if key in positives or key in reviewed_negatives:
            continue
        if int(row.get("irregular_transition_next_1m") or 0) != 0:
            continue

        score = int(row.get("irregular_transition_signal_score_next_1m") or 0)
        if score < 2:
            continue

        regime_shift = int(row.get("regime_shift_flag") or 0) >= 1
        try:
            polyarchy_drop = float(row.get("polyarchy_delta_1y") or 0.0) < -0.01
        except (TypeError, ValueError):
            polyarchy_drop = False
        high_severity_episode = int(row.get("high_severity_episode_count") or 0) > 0
        escalating_episode = int(row.get("escalating_episode_count") or 0) > 0

        if not any([regime_shift, polyarchy_drop, high_severity_episode, escalating_episode]):
            continue

        queue_rows.append({
            "country": country,
            "panel_date": panel_date,
            "target_name": "irregular_transition_next_1m",
            "current_proxy_score_1m": score,
            "current_proxy_signal_label": str(row.get("irregular_transition_signal_label_next_1m") or ""),
            "event_count": int(row.get("event_count") or 0),
            "episode_count": int(row.get("episode_count") or 0),
            "high_salience_event_count": int(row.get("high_salience_event_count") or 0),
            "high_severity_episode_count": int(row.get("high_severity_episode_count") or 0),
            "escalating_episode_count": int(row.get("escalating_episode_count") or 0),
            "episode_construct_regime_vulnerability_count": int(row.get("episode_construct_regime_vulnerability_count") or 0),
            "regime_shift_flag": int(row.get("regime_shift_flag") or 0),
            "polyarchy_delta_1y": row.get("polyarchy_delta_1y"),
            "time_since_last_coup": row.get("time_since_last_coup"),
            "coup_count_5y": int(row.get("coup_count_5y") or 0),
            "review_hint": "Hard negative candidate: transition-like stress without a current reviewed positive label.",
            "benchmark_reasoning": hard_negative_reason(row),
            "recommended_review_label": 0,
        })

    queue_rows.sort(
        key=lambda item: (
            -int(item["current_proxy_score_1m"]),
            -int(item["high_severity_episode_count"]),
            -int(item["regime_shift_flag"]),
            item["country"],
            item["panel_date"],
        )
    )

    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_internal_hard_negative_benchmark_queue",
        "description": (
            "Hard negative candidates for irregular-transition modeling: "
            "months that still look transition-like because of episode or "
            "historical-memory signals, but are not currently reviewed positives."
        ),
        "panel_file": str(PANEL.relative_to(ROOT)),
        "gold_file": str(GOLD.relative_to(ROOT)),
        "adjudicated_file": str(ADJUDICATED.relative_to(ROOT)),
        "local_negative_file": (
            str(LOCAL_NEGATIVE_DECISIONS.relative_to(ROOT)) if LOCAL_NEGATIVE_DECISIONS.exists() else None
        ),
        "selection_rules": {
            "min_year": MIN_YEAR,
            "exclude": [
                "gold positives",
                "adjudicated positives",
                "already reviewed negatives",
                "months without a complete 1m observation window",
                "routine low-signal background negatives",
            ],
            "include": [
                "proxy score >= 2",
                "regime-shift or democratic-backsliding signal, or",
                "high-severity / escalating episode without a reviewed positive label",
            ],
        },
        "summary": {
            "queue_rows": len(queue_rows),
            "countries": sorted({row["country"] for row in queue_rows}),
        },
        "rows": queue_rows,
    }


def main() -> None:
    payload = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote hard negative queue to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
