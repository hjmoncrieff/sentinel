#!/usr/bin/env python3
"""
Build a private adjudication queue for security-fragmentation-jump review.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REVIEW = ROOT / "data" / "review" / "security_fragmentation_jump_target_review.json"
OUT = ROOT / "data" / "review" / "adjudication_queue_security_fragmentation_jump.json"
LOCAL_DECISIONS = ROOT / "data" / "review" / "adjudicated_security_fragmentation_jump_decisions.local.json"

QUEUE_RATINGS = {"plausible", "review"}


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def load_local_decision_keys() -> set[tuple[str, str, str]]:
    if not LOCAL_DECISIONS.exists():
        return set()
    payload = load_json(LOCAL_DECISIONS)
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    keys: set[tuple[str, str, str]] = set()
    for row in rows:
        country = str(row.get("country") or "").strip()
        panel_date = str(row.get("panel_date") or "").strip()
        target_name = str(row.get("target_name") or "").strip()
        if country and panel_date and target_name:
            keys.add((country, panel_date, target_name))
    return keys


def build() -> dict:
    payload = load_json(REVIEW)
    countries = payload.get("countries", []) if isinstance(payload, dict) else []
    local_keys = load_local_decision_keys()
    rows = []
    for country_row in countries:
        country = str(country_row.get("country") or "")
        for case in country_row.get("cases", []):
            rating = str(case.get("rating") or "")
            if rating not in QUEUE_RATINGS:
                continue
            key = (country, str(case.get("trigger_month") or ""), "security_fragmentation_jump_next_3m")
            if key in local_keys:
                continue
            rows.append({
                "country": country,
                "panel_date": str(case.get("trigger_month") or ""),
                "future_reference_month": str(case.get("future_reference_month") or ""),
                "target_name": "security_fragmentation_jump_next_3m",
                "current_proxy_label": 1,
                "current_proxy_score_3m": case.get("score_3m"),
                "current_proxy_signal_label": case.get("label_3m"),
                "review_rating": rating,
                "review_note": case.get("note"),
                "recommended_action": (
                    "promote_to_local_adjudication"
                    if rating == "plausible"
                    else "hold_for_manual_review"
                ),
            })
    rows.sort(key=lambda item: (item["country"], item["panel_date"]))
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_internal_security_fragmentation_jump_adjudication_queue",
        "source_file": str(REVIEW.relative_to(ROOT)),
        "local_decision_file": str(LOCAL_DECISIONS.relative_to(ROOT)) if LOCAL_DECISIONS.exists() else None,
        "description": (
            "Working queue of security-fragmentation-jump proxy positives that "
            "are not yet promoted into a reviewed adjudication layer."
        ),
        "ratings_included": sorted(QUEUE_RATINGS),
        "count": len(rows),
        "rows": rows,
    }


def main() -> None:
    payload = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote security-fragmentation-jump adjudication queue to {OUT.relative_to(ROOT)}")
    print(f"Rows written: {payload['count']}")


if __name__ == "__main__":
    main()
