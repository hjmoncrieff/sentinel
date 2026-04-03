#!/usr/bin/env python3
"""
Audit upstream source coverage for potential training-history extension.

This stage distinguishes:
- what the current cleaned layers contain
- what the current ingest scripts are configured to pull
- whether the current 1990 floor is a source limit or a runner limit
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

VDEM_CLEAN = ROOT / "data" / "cleaned" / "vdem.json"
WB_CLEAN = ROOT / "data" / "cleaned" / "worldbank.json"
GREENBOOK_CLEAN = ROOT / "data" / "cleaned" / "greenbook.json"
EUSANCT_CLEAN = ROOT / "data" / "cleaned" / "eusanct.json"
CRISES_CLEAN = ROOT / "data" / "cleaned" / "financial_crises.json"

VDEM_SCRIPT = ROOT / "scripts" / "refresh_vdem.py"
WB_SCRIPT = ROOT / "scripts" / "fetch_worldbank.py"
COUNTRY_YEAR_SCRIPT = ROOT / "scripts" / "build_country_year.py"

OUT = ROOT / "data" / "review" / "upstream_training_source_audit.json"


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def detect_year_bounds_from_cleaned(path: Path) -> dict:
    if not path.exists():
        return {"present": False, "min_year": None, "max_year": None, "points": 0}
    payload = load_json(path)
    years: list[int] = []
    if isinstance(payload, dict) and "countries" in payload:
        for country in payload["countries"]:
            if isinstance(country, dict) and "series" in country:
                series_blob = country["series"]
                if isinstance(series_blob, dict):
                    iterable = series_blob.values()
                elif isinstance(series_blob, list):
                    iterable = [series_blob]
                else:
                    iterable = []
                for series in iterable:
                    for row in series:
                        year = row.get("year") if isinstance(row, dict) else None
                        if year not in (None, ""):
                            try:
                                years.append(int(year))
                            except Exception:
                                pass
            else:
                for value in country.values():
                    if isinstance(value, list):
                        for row in value:
                            year = row.get("year") if isinstance(row, dict) else None
                            if year not in (None, ""):
                                try:
                                    years.append(int(year))
                                except Exception:
                                    pass
    elif isinstance(payload, dict) and "rows" in payload:
        for row in payload["rows"]:
            year = row.get("year")
            if year not in (None, ""):
                try:
                    years.append(int(year))
                except Exception:
                    pass
    return {
        "present": True,
        "min_year": min(years) if years else None,
        "max_year": max(years) if years else None,
        "points": len(years),
    }


def detect_script_limits(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    findings: dict[str, str | int | None] = {}

    year_min_match = re.search(r"YEAR_MIN\s*=\s*(\d{4})", text)
    if year_min_match:
        findings["year_min_constant"] = int(year_min_match.group(1))

    date_param_match = re.search(r"\"date\"\s*:\s*\"(\d{4}):(\d{4})\"", text)
    if date_param_match:
        findings["date_param_min"] = int(date_param_match.group(1))
        findings["date_param_max"] = int(date_param_match.group(2))

    range_match = re.search(r"years\s*=\s*list\(range\((\d{4}),\s*(\d{4})\)\)", text)
    if range_match:
        findings["build_range_min"] = int(range_match.group(1))
        findings["build_range_max_exclusive"] = int(range_match.group(2))

    return findings


def main() -> None:
    sources = {
        "vdem_cleaned": {
            "file": str(VDEM_CLEAN.relative_to(ROOT)),
            "cleaned_bounds": detect_year_bounds_from_cleaned(VDEM_CLEAN),
            "script": str(VDEM_SCRIPT.relative_to(ROOT)),
            "script_limits": detect_script_limits(VDEM_SCRIPT),
            "training_extension_assessment": (
                "Current cleaned V-Dem layer is truncated by the refresh runner's YEAR_MIN setting."
            ),
        },
        "worldbank_cleaned": {
            "file": str(WB_CLEAN.relative_to(ROOT)),
            "cleaned_bounds": detect_year_bounds_from_cleaned(WB_CLEAN),
            "script": str(WB_SCRIPT.relative_to(ROOT)),
            "script_limits": detect_script_limits(WB_SCRIPT),
            "training_extension_assessment": (
                "Current cleaned World Bank layer is truncated by the fetch runner's date parameter."
            ),
        },
        "greenbook_cleaned": {
            "file": str(GREENBOOK_CLEAN.relative_to(ROOT)),
            "cleaned_bounds": detect_year_bounds_from_cleaned(GREENBOOK_CLEAN),
            "script": "scripts/clean_greenbook.py",
            "script_limits": {},
            "training_extension_assessment": (
                "Useful for post-1960 external-security history where available, but not a broad structural baseline."
            ),
        },
        "eusanct_cleaned": {
            "file": str(EUSANCT_CLEAN.relative_to(ROOT)),
            "cleaned_bounds": detect_year_bounds_from_cleaned(EUSANCT_CLEAN),
            "script": "scripts/clean_eusanct.py",
            "script_limits": {},
            "training_extension_assessment": (
                "Useful for sanctions history, but not a substitute for broader structural pre-1990 training coverage."
            ),
        },
        "financial_crises_cleaned": {
            "file": str(CRISES_CLEAN.relative_to(ROOT)),
            "cleaned_bounds": detect_year_bounds_from_cleaned(CRISES_CLEAN),
            "script": "scripts/clean_financial_crises.py",
            "script_limits": {},
            "training_extension_assessment": (
                "Useful for crisis memory and legacy features if earlier years are present."
            ),
        },
        "country_year_builder": {
            "script": str(COUNTRY_YEAR_SCRIPT.relative_to(ROOT)),
            "script_limits": detect_script_limits(COUNTRY_YEAR_SCRIPT),
            "training_extension_assessment": (
                "The merged country-year builder currently hardcodes a 1990-2024 range, so extending training history requires changing this build range after upstream inputs are widened."
            ),
        },
    }

    output = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_upstream_training_source_audit",
        "summary": {
            "main_current_constraint": (
                "The current merged structural layer now reaches back to 1960, and any extension earlier than that depends mostly on further runner/build choices plus source availability."
            ),
            "implication": (
                "A pre-1990 private training extension is already feasible; the next question is whether to push the structural window earlier than 1960."
            ),
        },
        "sources": sources,
        "recommended_next_actions": [
            "extend refresh_vdem.py earlier than 1990 for a private training-only artifact",
            "extend fetch_worldbank.py earlier than 1990 where the relevant indicators support it",
            "extend build_country_year.py so a training-only merged layer can include pre-1990 structural rows",
            "keep the operational/live product window unchanged at 1990-present",
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote upstream training-source audit to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
