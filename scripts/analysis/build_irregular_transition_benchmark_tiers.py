#!/usr/bin/env python3
"""
Build a tiered benchmark set for irregular-transition modeling.

This stage consolidates the current reviewed fit-ready benchmark material into
three interpretable tiers:

- gold_positive
- hard_negative
- easy_negative

The goal is not to replace the underlying label files, but to give the project
one compact benchmark artifact for validation planning and future model
comparison.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
GOLD = ROOT / "data" / "modeling" / "gold_irregular_transition_labels.json"
LOCAL_NEGATIVES = ROOT / "data" / "review" / "reviewed_negative_decisions.local.json"
OUT = ROOT / "data" / "modeling" / "irregular_transition_benchmark_tiers.json"

HARD_NEGATIVE_TYPES = {"hard_structural_negative_candidate"}


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def classify_negative(row: dict) -> str:
    candidate_type = str(row.get("candidate_type") or "").strip().lower()
    note = str(row.get("note") or "").strip().lower()
    if candidate_type in HARD_NEGATIVE_TYPES:
        return "hard_negative"
    if any(
        phrase in note
        for phrase in [
            "hard negative benchmark",
            "transition-like",
            "democratic decline",
            "regime-shift",
            "high-severity",
            "institutional reordering",
        ]
    ):
        return "hard_negative"
    return "easy_negative"


def build() -> dict:
    gold_payload = load_json(GOLD)
    gold_rows = gold_payload.get("rows", []) if isinstance(gold_payload, dict) else gold_payload

    negative_payload = load_json(LOCAL_NEGATIVES)
    negative_rows = negative_payload.get("rows", []) if isinstance(negative_payload, dict) else negative_payload

    tier_rows = []

    for row in gold_rows:
        tier_rows.append({
            "country": str(row.get("country") or ""),
            "panel_date": str(row.get("panel_date") or ""),
            "target_name": str(row.get("target_name") or "irregular_transition_next_1m"),
            "tier": "gold_positive",
            "label": 1,
            "tier_reason": "stricter adjudicated gold positive",
            "source_file": str(GOLD.relative_to(ROOT)),
            "source_rating": row.get("rating"),
            "proxy_score_1m": row.get("proxy_score_1m"),
            "note": row.get("note"),
        })

    for row in negative_rows:
        if int(row.get("label") or 0) != 0:
            continue
        if str(row.get("target_name") or "irregular_transition_next_1m") != "irregular_transition_next_1m":
            continue
        tier = classify_negative(row)
        tier_rows.append({
            "country": str(row.get("country") or ""),
            "panel_date": str(row.get("panel_date") or ""),
            "target_name": str(row.get("target_name") or "irregular_transition_next_1m"),
            "tier": tier,
            "label": 0,
            "tier_reason": (
                "reviewed negative that still looks transition-like"
                if tier == "hard_negative"
                else "reviewed low-intensity or background negative"
            ),
            "source_file": str(LOCAL_NEGATIVES.relative_to(ROOT)),
            "source_rating": row.get("rating"),
            "candidate_type": row.get("candidate_type"),
            "note": row.get("note"),
        })

    tier_rows.sort(key=lambda item: (item["country"], item["panel_date"], item["tier"]))

    summary = {
        "gold_positive_rows": sum(1 for row in tier_rows if row["tier"] == "gold_positive"),
        "hard_negative_rows": sum(1 for row in tier_rows if row["tier"] == "hard_negative"),
        "easy_negative_rows": sum(1 for row in tier_rows if row["tier"] == "easy_negative"),
        "countries": sorted({row["country"] for row in tier_rows}),
    }

    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_internal_benchmark_tier_set",
        "target_name": "irregular_transition_next_1m",
        "description": (
            "Tiered benchmark reference set for irregular-transition modeling. "
            "This groups current reviewed benchmark material into gold positives, "
            "hard negatives, and easy negatives."
        ),
        "source_files": {
            "gold_labels": str(GOLD.relative_to(ROOT)),
            "local_reviewed_negatives": str(LOCAL_NEGATIVES.relative_to(ROOT)),
        },
        "tier_rules": {
            "gold_positive": "rows included in the stricter gold irregular-transition subset",
            "hard_negative": (
                "reviewed negatives tagged as hard structural/transition-like "
                "cases or whose notes explicitly mark them as benchmark hard negatives"
            ),
            "easy_negative": "all other reviewed local negatives",
        },
        "summary": summary,
        "rows": tier_rows,
    }


def main() -> None:
    payload = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote tiered benchmark set to {OUT.relative_to(ROOT)}")
    print(
        "Rows:",
        payload["summary"]["gold_positive_rows"] + payload["summary"]["hard_negative_rows"] + payload["summary"]["easy_negative_rows"],
    )


if __name__ == "__main__":
    main()
