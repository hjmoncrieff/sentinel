#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TAXONOMY_PATH = ROOT / "config" / "taxonomy" / "event_types.json"
OUTPUT_PATH = ROOT / "docs" / "event-taxonomy-reference.md"


def titleize(value: str) -> str:
    return str(value or "").replace("_", " ").strip().title()


def bullet_list(items: list[str]) -> str:
    cleaned = [item for item in items if item]
    if not cleaned:
        return "-"
    return "<br>".join(f"- `{item}`" for item in cleaned)


def build_reference(payload: dict) -> str:
    rows = payload.get("event_types", [])
    types: dict[str, list[dict]] = defaultdict(list)
    subcategories: dict[tuple[str, str], set[str]] = defaultdict(set)

    for row in rows:
        event_type = str(row.get("type") or row.get("event_category") or "other")
        category = str(row.get("category") or row.get("code") or "other")
        types[event_type].append(row)
        subcategories[(event_type, category)].add(str(row.get("event_subcategory") or ""))

    lines: list[str] = []
    lines.append("# Event Taxonomy Reference")
    lines.append("")
    lines.append(f"_Generated from `config/taxonomy/event_types.json` on {date.today().isoformat()}._")
    lines.append("")
    lines.append("This is the current SENTINEL event hierarchy:")
    lines.append("")
    lines.append("- `Type`: broad analytical domain")
    lines.append("- `Category`: event family within that domain")
    lines.append("- `Subcategory`: narrower mechanism-level interpretation")
    lines.append("")
    lines.append("The pipeline still keeps legacy internal family codes for compatibility, but this document is the public-facing structure reference.")
    lines.append("")
    lines.append("## Type -> Category -> Subcategory")
    lines.append("")
    lines.append("| Type | Category | Category Label | Default Subcategory | Construct Destinations | Analyst Lenses | Description |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")

    for event_type in sorted(types):
        for row in sorted(types[event_type], key=lambda item: int(item.get("precedence_rank", 0)), reverse=True):
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{row.get('type') or row.get('event_category') or ''}`",
                        f"`{row.get('category') or row.get('code') or ''}`",
                        str(row.get("category_label") or row.get("label") or ""),
                        f"`{row.get('event_subcategory') or ''}`",
                        bullet_list(list(row.get("construct_destinations", []))),
                        bullet_list(list(row.get("analyst_lenses", []))),
                        str(row.get("description") or ""),
                    ]
                )
                + " |"
            )

    lines.append("")
    lines.append("## Types")
    lines.append("")
    for event_type in sorted(types):
        lines.append(f"### `{event_type}`")
        lines.append("")
        rows_for_type = sorted(types[event_type], key=lambda item: int(item.get("precedence_rank", 0)), reverse=True)
        categories_included = ", ".join(
            f"`{row.get('category') or row.get('code')}`" for row in rows_for_type
        )
        lines.append(f"- categories: `{len(rows_for_type)}`")
        lines.append(f"- categories included: {categories_included}")
        lines.append("")

    lines.append("## Category -> Subcategory Map")
    lines.append("")
    for event_type in sorted(types):
        lines.append(f"### `{event_type}`")
        lines.append("")
        for row in sorted(types[event_type], key=lambda item: int(item.get("precedence_rank", 0)), reverse=True):
            category = str(row.get("category") or row.get("code") or "")
            subs = sorted(item for item in subcategories[(event_type, category)] if item)
            lines.append(f"- `{category}`")
            if subs:
                lines.append(f"  default: `{subs[0]}`")
            else:
                lines.append("  default: `none`")
        lines.append("")

    lines.append("## Update Rule")
    lines.append("")
    lines.append("Whenever `config/taxonomy/event_types.json` changes, regenerate this file with:")
    lines.append("")
    lines.append("```bash")
    lines.append("python3 scripts/analysis/update_event_taxonomy_reference.py")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    payload = json.loads(TAXONOMY_PATH.read_text())
    OUTPUT_PATH.write_text(build_reference(payload))
    print(f'wrote {OUTPUT_PATH}')


if __name__ == "__main__":
    main()
