#!/usr/bin/env python3
"""
Build a stricter gold acute political-risk label subset from the reviewed
adjudicated layer.

This stage keeps the broader adjudicated acute-risk layer intact but derives a
narrower, higher-confidence subset for future model fitting and validation.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ADJUDICATED = ROOT / "data" / "modeling" / "adjudicated_acute_political_risk_labels.json"
OUT = ROOT / "data" / "modeling" / "gold_acute_political_risk_labels.json"

GOLD_RATINGS = {"strong", "reviewed"}
MIN_PROXY_SCORE = 4


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def qualifies(row: dict) -> bool:
    rating = str(row.get("rating") or "").strip().lower()
    score = int(row.get("proxy_score_1m") or 0)
    note = str(row.get("note") or "").strip().lower()

    if rating == "strong":
        return True
    if rating not in GOLD_RATINGS:
        return False
    if score < MIN_PROXY_SCORE:
        return False
    return (
        "high-severity" in note
        or "shock" in note
        or "fragmenting conflict-linked" in note
        or "coup-coded" in note
        or "clear broader acute deterioration" in note
    )


def build() -> dict:
    payload = load_json(ADJUDICATED)
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    gold_rows = [row for row in rows if qualifies(row)]
    gold_rows.sort(key=lambda item: (item["country"], item["panel_date"]))
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_internal_gold_acute_political_risk_subset",
        "source_file": str(ADJUDICATED.relative_to(ROOT)),
        "target_name": "acute_political_risk_next_1m",
        "description": (
            "Stricter gold subset derived from the broader adjudicated acute "
            "political-risk layer. This should be used for higher-confidence "
            "validation and future model fitting."
        ),
        "gold_rule": {
            "included_ratings": sorted(GOLD_RATINGS),
            "minimum_proxy_score_1m": MIN_PROXY_SCORE,
            "required_note_signals": [
                "high-severity",
                "shock",
                "fragmenting conflict-linked",
                "coup-coded",
                "clear broader acute deterioration",
            ],
            "always_include_rating": "strong",
        },
        "count": len(gold_rows),
        "countries": sorted({row["country"] for row in gold_rows}),
        "rows": gold_rows,
    }


def main() -> None:
    payload = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote gold acute political-risk labels to {OUT.relative_to(ROOT)}")
    print(f"Labels written: {payload['count']}")


if __name__ == "__main__":
    main()
