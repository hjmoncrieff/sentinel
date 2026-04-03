#!/usr/bin/env python3
"""
Build the reviewed fit-ready irregular-transition dataset.

This produces a private artifact combining:
- gold positives
- reviewed-watch negatives
- weak-review negatives
- local reviewed negatives

The output is intended for future fitting work and uses the stricter fit-path
signal fields from the country-month panel.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL = ROOT / "data" / "modeling" / "country_month_panel.json"
ADJUDICATED = ROOT / "data" / "modeling" / "adjudicated_irregular_transition_labels.json"
GOLD = ROOT / "data" / "modeling" / "gold_irregular_transition_labels.json"
REVIEW = ROOT / "data" / "review" / "irregular_transition_target_review.json"
LOCAL_NEGATIVE_DECISIONS = ROOT / "data" / "review" / "reviewed_negative_decisions.local.json"
BENCHMARK_TIERS = ROOT / "data" / "modeling" / "irregular_transition_benchmark_tiers.json"
OUT = ROOT / "data" / "modeling" / "irregular_transition_fit_dataset.json"

FIT_FEATURES = [
    "transition_rupture_precursor_score",
    "transition_contestation_load_score",
    "transition_specificity_gap",
    "high_severity_episode_count",
    "episode_construct_regime_vulnerability_count",
    "episode_start_count",
    "escalating_episode_count",
    "event_shock_flag",
    "event_type_coup_count",
    "event_type_purge_count",
    "event_type_conflict_count",
    "event_type_protest_count",
    "deed_type_destabilizing_count",
    "high_salience_event_count",
    "external_pressure_sanctions_active",
    "economic_fragility_fx_stress",
    "state_capacity_composite",
    "time_since_last_coup",
    "regime_shift_flag",
]


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def build_sample() -> tuple[list[dict], dict]:
    panel_payload = load_json(PANEL)
    panel_rows = panel_payload.get("rows", []) if isinstance(panel_payload, dict) else []
    panel_lookup = {
        (str(row.get("country") or ""), str(row.get("panel_date") or "")): row
        for row in panel_rows
    }

    gold_payload = load_json(GOLD)
    gold_rows = gold_payload.get("rows", []) if isinstance(gold_payload, dict) else []
    gold_keys = {
        (str(row.get("country") or ""), str(row.get("panel_date") or ""))
        for row in gold_rows
    }

    benchmark_tier_lookup: dict[tuple[str, str], str] = {}
    if BENCHMARK_TIERS.exists():
        benchmark_payload = load_json(BENCHMARK_TIERS)
        benchmark_rows = benchmark_payload.get("rows", []) if isinstance(benchmark_payload, dict) else benchmark_payload
        benchmark_tier_lookup = {
            (str(row.get("country") or ""), str(row.get("panel_date") or "")): str(row.get("tier") or "")
            for row in benchmark_rows
        }

    adjudicated_payload = load_json(ADJUDICATED)
    adjudicated_rows = adjudicated_payload.get("rows", []) if isinstance(adjudicated_payload, dict) else []
    reviewed_watch_keys = {
        (str(row.get("country") or ""), str(row.get("panel_date") or ""))
        for row in adjudicated_rows
        if str(row.get("rating") or "").strip().lower() == "reviewed_watch"
    }

    review_payload = load_json(REVIEW)
    review_countries = review_payload.get("countries", []) if isinstance(review_payload, dict) else []
    weak_keys: set[tuple[str, str]] = set()
    for country_row in review_countries:
        country = str(country_row.get("country") or "")
        for case in country_row.get("cases", []):
            if str(case.get("rating") or "").strip().lower() == "weak":
                weak_keys.add((country, str(case.get("trigger_month") or "")))

    local_negative_keys: set[tuple[str, str]] = set()
    if LOCAL_NEGATIVE_DECISIONS.exists():
        local_payload = load_json(LOCAL_NEGATIVE_DECISIONS)
        local_rows = local_payload.get("rows", []) if isinstance(local_payload, dict) else []
        for row in local_rows:
            if int(row.get("label") or 0) != 0:
                continue
            if str(row.get("target_name") or "irregular_transition_next_1m") != "irregular_transition_next_1m":
                continue
            local_negative_keys.add((str(row.get("country") or ""), str(row.get("panel_date") or "")))

    rows: list[dict] = []

    for key in sorted(gold_keys):
        panel_row = panel_lookup.get(key)
        if not panel_row:
            continue
        rows.append({
            "country": key[0],
            "panel_date": key[1],
            "y_true": 1,
            "label_group": "gold_positive",
            "benchmark_tier": benchmark_tier_lookup.get(key, "gold_positive"),
            "fit_score_1m": int(panel_row.get("irregular_transition_fit_score_next_1m") or 0),
            "fit_label_1m": str(panel_row.get("irregular_transition_fit_label_next_1m") or ""),
            "fit_target_rule": str(panel_row.get("irregular_transition_fit_target_rule") or ""),
            "watch_score_1m": int(panel_row.get("irregular_transition_signal_score_next_1m") or 0),
            "watch_label_1m": str(panel_row.get("irregular_transition_signal_label_next_1m") or ""),
            **{feature: panel_row.get(feature) for feature in FIT_FEATURES},
        })

    negative_keys = sorted((reviewed_watch_keys | weak_keys | local_negative_keys) - gold_keys)
    for key in negative_keys:
        panel_row = panel_lookup.get(key)
        if not panel_row:
            continue
        if key in local_negative_keys:
            label_group = "local_reviewed_negative"
        elif key in reviewed_watch_keys:
            label_group = "reviewed_watch_negative"
        else:
            label_group = "weak_review_negative"
        rows.append({
            "country": key[0],
            "panel_date": key[1],
            "y_true": 0,
            "label_group": label_group,
            "benchmark_tier": benchmark_tier_lookup.get(key, "unclassified_negative"),
            "fit_score_1m": int(panel_row.get("irregular_transition_fit_score_next_1m") or 0),
            "fit_label_1m": str(panel_row.get("irregular_transition_fit_label_next_1m") or ""),
            "fit_target_rule": str(panel_row.get("irregular_transition_fit_target_rule") or ""),
            "watch_score_1m": int(panel_row.get("irregular_transition_signal_score_next_1m") or 0),
            "watch_label_1m": str(panel_row.get("irregular_transition_signal_label_next_1m") or ""),
            **{feature: panel_row.get(feature) for feature in FIT_FEATURES},
        })

    rows.sort(key=lambda item: (item["country"], item["panel_date"], item["y_true"]))
    metadata = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_internal_irregular_transition_fit_dataset",
        "panel_file": str(PANEL.relative_to(ROOT)),
        "gold_file": str(GOLD.relative_to(ROOT)),
        "adjudicated_file": str(ADJUDICATED.relative_to(ROOT)),
        "review_file": str(REVIEW.relative_to(ROOT)),
        "local_negative_file": str(LOCAL_NEGATIVE_DECISIONS.relative_to(ROOT)) if LOCAL_NEGATIVE_DECISIONS.exists() else None,
        "fit_target_rule": rows[0].get("fit_target_rule") if rows else None,
        "summary": {
            "rows": len(rows),
            "gold_positive_rows": sum(1 for row in rows if row["label_group"] == "gold_positive"),
            "reviewed_watch_negative_rows": sum(1 for row in rows if row["label_group"] == "reviewed_watch_negative"),
            "weak_review_negative_rows": sum(1 for row in rows if row["label_group"] == "weak_review_negative"),
            "local_reviewed_negative_rows": sum(1 for row in rows if row["label_group"] == "local_reviewed_negative"),
        },
        "fit_features": FIT_FEATURES,
    }
    return rows, metadata


def main() -> None:
    rows, metadata = build_sample()
    payload = {**metadata, "rows": rows}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote fit dataset to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
