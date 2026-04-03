#!/usr/bin/env python3
"""
Build a stricter gold security-fragmentation-jump label subset from the
reviewed adjudicated layer.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ADJUDICATED = ROOT / "data" / "modeling" / "adjudicated_security_fragmentation_jump_labels.json"
OUT = ROOT / "data" / "modeling" / "gold_security_fragmentation_jump_labels.json"

MIN_PROXY_SCORE = 4
REQUIRED_NOTE_SIGNALS = [
    "high-severity",
    "shock",
    "dense",
    "clear",
    "conflict reinforcement",
    "organized-crime reinforcement",
]


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def qualifies(row: dict) -> bool:
    if int(row.get("label") or 0) != 1:
        return False
    score = int(row.get("proxy_score_3m") or 0)
    if score < MIN_PROXY_SCORE:
        return False
    note = str(row.get("note") or "").strip().lower()
    return any(signal in note for signal in REQUIRED_NOTE_SIGNALS)


def build() -> dict:
    payload = load_json(ADJUDICATED)
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    gold_rows = [row for row in rows if qualifies(row)]
    gold_rows.sort(key=lambda item: (item["country"], item["panel_date"]))
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_internal_gold_security_fragmentation_jump_subset",
        "source_file": str(ADJUDICATED.relative_to(ROOT)),
        "target_name": "security_fragmentation_jump_next_3m",
        "description": (
            "Stricter gold subset derived from the adjudicated "
            "security-fragmentation-jump layer for higher-confidence "
            "validation and future fitting."
        ),
        "gold_rule": {
            "required_label": 1,
            "minimum_proxy_score_3m": MIN_PROXY_SCORE,
            "required_note_signals": REQUIRED_NOTE_SIGNALS,
        },
        "count": len(gold_rows),
        "countries": sorted({row["country"] for row in gold_rows}),
        "rows": gold_rows,
    }


def main() -> None:
    payload = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote gold security-fragmentation-jump labels to {OUT.relative_to(ROOT)}")
    print(f"Labels written: {payload['count']}")


if __name__ == "__main__":
    main()
