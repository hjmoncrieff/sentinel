#!/usr/bin/env python3
"""
Carry saved LLM synthesis forward into a freshly built council_analyses.json.

run_council.py rebuilds data/review/council_analyses.json from scratch, and that
file is gitignored, so a CI checkout never has the previous run's Sonnet
synthesis. The last complete copy lives in Supabase as the `council_analyses`
console snapshot (pushed by the sync cycle). This step copies each event's saved
`llm_synthesis` block back in, so run_council_synthesis.py only pays for events
that have never been synthesised.

Without Supabase credentials it does nothing. With --strict, missing credentials
or a failed fetch is an error: the sync cycle pushes council analyses back to Supabase, and pushing a
copy without the saved synthesis would erase it there.

Usage:
  python3 scripts/analysis/restore_council_synthesis.py [--strict]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "sync"))

from analysis.run_council_synthesis import COUNCIL_PATH, apply_llm_synthesis  # noqa: E402


def restore(entries: list[dict], saved_entries: list[dict]) -> int:
    """Copy saved successful llm_synthesis blocks onto entries that lack one. Returns the count."""
    saved = {}
    for e in saved_entries:
        llm = (e.get("analyses") or {}).get("llm_synthesis") or {}
        if e.get("event_id") and llm.get("synthesis") and llm.get("ok", True):
            saved[e["event_id"]] = llm
    restored = 0
    for e in entries:
        analyses = e.setdefault("analyses", {})
        llm = saved.get(e.get("event_id"))
        if llm and not analyses.get("llm_synthesis"):
            apply_llm_synthesis(analyses, llm)
            restored += 1
    return restored


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--strict", action="store_true", help="Fail if Supabase is configured but the snapshot cannot be read")
    args = parser.parse_args()

    from common import fetch_console_snapshots, load_local_env
    load_local_env()
    if not os.environ.get("SUPABASE_URL"):
        if args.strict:
            raise SystemExit("ERROR: --strict needs SUPABASE_URL; refusing to continue without restoring saved synthesis.")
        print("Supabase not configured; no saved synthesis to restore.")
        return
    try:
        snapshot = fetch_console_snapshots(["council_analyses"]).get("council_analyses") or {}
    except Exception as exc:  # noqa: BLE001 - network, auth, DNS
        if args.strict:
            raise
        print(f"WARNING: could not read saved synthesis from Supabase ({type(exc).__name__}); continuing without it.")
        return
    payload = json.loads(COUNCIL_PATH.read_text(encoding="utf-8"))
    restored = restore(payload.get("events", []), snapshot.get("events", []))
    if restored:
        COUNCIL_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved synthesis restored for {restored} events.")


if __name__ == "__main__":
    main()
