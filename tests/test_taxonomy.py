from __future__ import annotations

import json
import re
from pathlib import Path

from prompt_library import load_prompt

ROOT = Path(__file__).resolve().parent.parent
TAXONOMY = json.loads((ROOT / "config" / "taxonomy" / "event_types.json").read_text(encoding="utf-8"))
REQUIRED_KEYS = {
    "code", "label", "description", "exclusions", "precedence_rank", "type", "category",
    "category_label", "event_category", "event_subcategory", "construct_destinations",
    "analyst_lenses",
}


def taxonomy_codes() -> set[str]:
    return {row["code"] for row in TAXONOMY["event_types"]}


def test_taxonomy_rows_are_complete_and_unique():
    rows = TAXONOMY["event_types"]
    assert len({r["code"] for r in rows}) == len(rows)
    assert len({r["precedence_rank"] for r in rows}) == len(rows)
    for row in rows:
        assert REQUIRED_KEYS <= row.keys(), row["code"]


def test_every_classifier_type_is_in_the_taxonomy():
    # Regression: coup_proofing was emitted by the classifier but missing here, so its
    # events silently fell back to the generic "other" overlay.
    match = re.search(r'"type":"([a-z_|]+)"', load_prompt("classify_events"))
    assert match, "classifier prompt no longer declares its type enum"
    emitted = set(match.group(1).split("|"))
    assert emitted <= taxonomy_codes(), emitted - taxonomy_codes()
