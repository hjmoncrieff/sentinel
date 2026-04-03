#!/usr/bin/env python3
"""
Validate the stricter fit-path irregular-transition target layer against the
gold subset.

This is a private/internal checkpoint used before model fitting.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL = ROOT / "data" / "modeling" / "country_month_panel.json"
GOLD = ROOT / "data" / "modeling" / "gold_irregular_transition_labels.json"
OUT = ROOT / "data" / "review" / "gold_irregular_transition_validation.json"


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 3)


def main() -> None:
    panel_payload = load_json(PANEL)
    panel_rows = panel_payload.get("rows", []) if isinstance(panel_payload, dict) else []
    gold_payload = load_json(GOLD)
    gold_rows = gold_payload.get("rows", []) if isinstance(gold_payload, dict) else []

    panel_lookup = {
        (str(row.get("country") or ""), str(row.get("panel_date") or "")): row
        for row in panel_rows
    }

    matched = []
    tp = 0
    fn = 0
    elevated = 0
    watch = 0
    by_country: dict[str, dict] = {}

    for gold in gold_rows:
        key = (str(gold.get("country") or ""), str(gold.get("panel_date") or ""))
        panel_row = panel_lookup.get(key)
        if not panel_row:
            continue
        signal_score = int(panel_row.get("irregular_transition_fit_score_next_1m") or 0)
        signal_label = str(panel_row.get("irregular_transition_fit_label_next_1m") or "")
        predicted = int(signal_score >= 4)
        source = str(panel_row.get("irregular_transition_label_source") or "")
        is_hit = predicted == 1
        tp += int(is_hit)
        fn += int(not is_hit)
        elevated += int(signal_label == "elevated")
        watch += int(signal_label == "watch")

        country = key[0]
        bucket = by_country.setdefault(country, {
            "gold_rows": 0,
            "matched_positive": 0,
            "missed": 0,
        })
        bucket["gold_rows"] += 1
        bucket["matched_positive"] += int(is_hit)
        bucket["missed"] += int(not is_hit)

        matched.append({
            "country": country,
            "panel_date": key[1],
            "gold_label": int(gold.get("label") or 0),
            "predicted_label_1m": predicted,
            "signal_score_1m": signal_score,
            "signal_label_1m": signal_label,
            "label_source": source,
            "gold_rating": gold.get("rating"),
            "gold_note": gold.get("note"),
            "match_status": "hit" if is_hit else "miss",
        })

    predicted_positive_rows = [row for row in panel_rows if int(row.get("irregular_transition_fit_score_next_1m") or 0) >= 4]
    gold_keys = {(str(row.get("country") or ""), str(row.get("panel_date") or "")) for row in gold_rows}
    fp = sum(
        1 for row in predicted_positive_rows
        if (str(row.get("country") or ""), str(row.get("panel_date") or "")) not in gold_keys
    )

    output = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_internal_gold_fit_target_validation",
        "panel_file": str(PANEL.relative_to(ROOT)),
        "gold_file": str(GOLD.relative_to(ROOT)),
        "fit_target_rule": panel_rows[0].get("irregular_transition_fit_target_rule") if panel_rows else None,
        "summary": {
            "gold_rows": len(gold_rows),
            "panel_predicted_positive_rows": len(predicted_positive_rows),
            "true_positive_against_gold": tp,
            "false_negative_against_gold": fn,
            "false_positive_against_gold": fp,
            "gold_recall_pct": pct(tp, len(gold_rows)),
            "proxy_precision_against_gold_pct": pct(tp, len(predicted_positive_rows)),
            "gold_rows_with_elevated_signal_pct": pct(elevated, len(gold_rows)),
            "gold_rows_with_watch_signal_pct": pct(watch, len(gold_rows)),
        },
        "by_country": [
            {
                "country": country,
                **bucket,
                "gold_recall_pct": pct(bucket["matched_positive"], bucket["gold_rows"]),
            }
            for country, bucket in sorted(by_country.items())
        ],
        "rows": matched,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote gold validation report to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
