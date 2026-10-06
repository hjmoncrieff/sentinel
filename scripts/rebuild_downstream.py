#!/usr/bin/env python3
"""
Rebuild every layer derived from data/events.json, in dependency order.

Run this after any change to data/events.json. Both GitHub workflows call it,
so the order lives in one place:

  - fetch_events.yml runs it after the nightly pipeline;
  - supabase_sync.yml runs it with --through review before the Supabase cycle,
    because data/review/ is gitignored and a fresh checkout has none of it.

Council synthesis (Sonnet) and its quality check run only when the environment
variable RUN_COUNCIL_SYNTHESIS is "true". Saved synthesis is restored from
Supabase on every rebuild (restore_council_synthesis.py), so it is paid for once.

Usage:
  python3 scripts/rebuild_downstream.py [--through review|publish]
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REVIEW_STEPS = [
    "scripts/qa/run_qa.py",
    "scripts/qa/run_registry_qa.py",
    "scripts/pipeline/detect_duplicates.py",
    "scripts/analysis/build_country_monitors.py",
    "scripts/analysis/validate_country_monitors.py",
    "scripts/pipeline/build_canonical_events.py",
    "scripts/pipeline/code_actors.py",
    "scripts/review/build_review_queue.py",
    # Rebuilt every time: a stale events_with_edits.json feeds removed events back into the
    # council, the monitors and the published layer (found 2026-10-05).
    "scripts/review/apply_analyst_edits.py",
    "scripts/analysis/run_council.py",
    "scripts/analysis/restore_council_synthesis.py",
]
SYNTHESIS_STEPS = [
    "scripts/analysis/run_council_synthesis.py",
    "scripts/analysis/validate_council_quality.py",
]
PUBLISH_STEPS = ["scripts/publish/publish_dashboard_data.py"]


def steps(through: str, synthesis: bool) -> list[str]:
    out = list(REVIEW_STEPS)
    if synthesis:
        out += SYNTHESIS_STEPS
    if through == "publish":
        out += PUBLISH_STEPS
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--through", choices=("review", "publish"), default="publish",
                        help="review: stop before publishing (the Supabase cycle publishes itself)")
    args = parser.parse_args()
    synthesis = os.environ.get("RUN_COUNCIL_SYNTHESIS", "").lower() == "true"
    if not synthesis:
        print("Council synthesis skipped (RUN_COUNCIL_SYNTHESIS is not true)")
    for script in steps(args.through, synthesis):
        print(f"\n== {script} ==", flush=True)
        # The sync cycle (--through review) pushes council analyses back to Supabase, so
        # it must not continue if the saved synthesis could not be restored first.
        extra = ["--strict"] if script.endswith("restore_council_synthesis.py") and args.through == "review" else []
        subprocess.run([sys.executable, str(ROOT / script), *extra], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
