#!/usr/bin/env python3
"""Run the standard SENTINEL local <-> Supabase sync cycle."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PULL_REGISTRY = ROOT / "scripts" / "sync" / "pull_registry_edits_from_supabase.py"
APPLY_REGISTRY = ROOT / "scripts" / "review" / "apply_registry_edits.py"
RUN_REGISTRY_QA = ROOT / "scripts" / "qa" / "run_registry_qa.py"
RUN_CODE_ACTORS = ROOT / "scripts" / "pipeline" / "code_actors.py"
RUN_REVIEW_QUEUE = ROOT / "scripts" / "review" / "build_review_queue.py"
RUN_PUBLISH = ROOT / "scripts" / "publish" / "publish_dashboard_data.py"
PUSH_SNAPSHOTS = ROOT / "scripts" / "sync" / "push_console_snapshots_to_supabase.py"
EXPORT_PUBLISHED = ROOT / "scripts" / "sync" / "export_published_from_supabase.py"


def run_step(label: str, script: Path) -> None:
    print(f"\n== {label} ==")
    subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True)


def main() -> None:
    run_step("Pull registry edits from Supabase", PULL_REGISTRY)
    run_step("Apply registry edits locally", APPLY_REGISTRY)
    run_step("Rebuild actor-coded canonical layer", RUN_CODE_ACTORS)
    run_step("Rebuild registry QA layer", RUN_REGISTRY_QA)
    run_step("Rebuild review queue", RUN_REVIEW_QUEUE)
    run_step("Rebuild published dashboard layer", RUN_PUBLISH)
    run_step("Push refreshed snapshots to Supabase", PUSH_SNAPSHOTS)
    run_step("Export published dashboard artifacts", EXPORT_PUBLISHED)
    print("\nSupabase sync cycle completed.")


if __name__ == "__main__":
    main()
