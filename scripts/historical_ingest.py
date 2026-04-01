#!/usr/bin/env python3
"""
Historical ingestion scaffold for SENTINEL.

This script is intentionally separate from the fast monitoring pipeline.
Its job is to plan and eventually orchestrate deep backfill workflows, especially
for coverage windows such as 2000+ where RSS and recent-search APIs are not
enough.

Current status:
- planning/scaffold layer
- source manifest inspection
- source-group execution plan generation

Future status:
- source-specific archive connectors
- resumable batch execution
- article-level staging output
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "config" / "historical_sources.json"
STAGING_DIR = ROOT / "data" / "staging"


@dataclass
class HistoricalRequest:
    since: str
    until: str
    groups: list[str]
    dry_run: bool


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text())


def validate_date(value: str) -> str:
    datetime.strptime(value, "%Y-%m-%d")
    return value


def build_plan(request: HistoricalRequest, manifest: dict) -> dict:
    source_groups = manifest.get("source_groups", [])
    selected = []
    for group in source_groups:
        if request.groups and group.get("group_id") not in request.groups:
            continue
        selected.append({
            "group_id": group.get("group_id"),
            "label": group.get("label"),
            "priority": group.get("priority"),
            "sources": [
                {
                    "source_id": source.get("source_id"),
                    "label": source.get("label"),
                    "connector_type": source.get("connector_type"),
                    "historical_ready": source.get("historical_ready"),
                    "coverage_start": source.get("coverage_start"),
                    "notes": source.get("notes")
                }
                for source in group.get("sources", [])
            ]
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "request": {
            "since": request.since,
            "until": request.until,
            "groups": request.groups or [group.get("group_id") for group in selected],
            "dry_run": request.dry_run
        },
        "manifest_path": str(MANIFEST_PATH.relative_to(ROOT)),
        "status": "planning_only",
        "recommended_output_dir": str((STAGING_DIR / "historical").relative_to(ROOT)),
        "notes": [
            "Deep historical ingest should be treated as a separate pipeline from the fast monitoring workflow.",
            "RSS feeds and recent-search APIs are not sufficient for complete 2000+ coverage.",
            "Structured datasets and source-specific archive connectors should be prioritized before generic search APIs."
        ],
        "source_groups": selected
    }


def print_summary(plan: dict) -> None:
    req = plan["request"]
    print("SENTINEL historical ingestion plan")
    print(f"Window: {req['since']} -> {req['until']}")
    print(f"Mode: {'dry-run' if req['dry_run'] else 'planning'}")
    print("")
    for group in plan["source_groups"]:
        print(f"- {group['label']} [{group['group_id']}]")
        for source in group["sources"]:
            print(
                f"  - {source['label']} | {source['connector_type']} | "
                f"historical_ready={source['historical_ready']} | "
                f"coverage_start={source['coverage_start'] or 'unknown'}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Historical ingestion planner for SENTINEL")
    parser.add_argument("--since", type=validate_date, required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--until", type=validate_date, default=datetime.now(timezone.utc).strftime("%Y-%m-%d"), help="End date YYYY-MM-DD")
    parser.add_argument("--group", action="append", default=[], help="Optional source-group filter from config/historical_sources.json")
    parser.add_argument("--json", action="store_true", help="Print the full execution plan as JSON")
    parser.add_argument("--dry-run", action="store_true", help="Generate a source execution plan without attempting ingest")
    args = parser.parse_args()

    manifest = load_manifest()
    request = HistoricalRequest(
        since=args.since,
        until=args.until,
        groups=args.group,
        dry_run=args.dry_run
    )
    plan = build_plan(request, manifest)

    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    print_summary(plan)


if __name__ == "__main__":
    main()
