#!/usr/bin/env python3
"""Push local SENTINEL JSON layers into Supabase console snapshots."""

from __future__ import annotations

import sys
from pathlib import Path

from common import ROOT, finish_sync_run, load_json, now_iso, start_sync_run, upsert_console_snapshot

sys.path.insert(0, str(ROOT / "scripts" / "reference"))
from review_reference import review_items  # noqa: E402

REFERENCE_PATH = ROOT / "apps" / "public-site" / "reference" / "countries.json"


SNAPSHOTS: dict[str, Path] = {
    "review_queue": ROOT / "data" / "review" / "review_queue.json",
    "qa_report": ROOT / "data" / "review" / "qa_report.json",
    "registry_qa_report": ROOT / "data" / "review" / "registry_qa_report.json",
    "duplicate_candidates": ROOT / "data" / "review" / "duplicate_candidates.json",
    "council_analyses": ROOT / "data" / "review" / "council_analyses.json",
    "canonical_events": ROOT / "data" / "canonical" / "events_actor_coded.json",
    "published_events": ROOT / "data" / "published" / "events_public.json",
    "country_dossiers": ROOT / "data" / "published" / "country_dossiers.json",
    "country_monitors": ROOT / "data" / "published" / "country_monitors.json",
    "actor_registry": ROOT / "config" / "actors" / "actor_registry.json",
}


# Trace fields the React console does not read. They are about 40% of the council file,
# and the full 17 MB payload exceeded Supabase's statement timeout from CI (2026-10-05).
# The local data/review/council_analyses.json keeps them.
COUNCIL_EVENT_TRACE_KEYS = ("upstream_worker_outputs", "worker_trace", "analysis_activation")
COUNCIL_LENS_TRACE_KEYS = ("knowledge_trace",)


def slim_council(payload: dict) -> dict:
    events = []
    for event in payload.get("events", []):
        row = {k: v for k, v in event.items() if k not in COUNCIL_EVENT_TRACE_KEYS}
        row["analyses"] = {
            lens: ({k: v for k, v in block.items() if k not in COUNCIL_LENS_TRACE_KEYS} if isinstance(block, dict) else block)
            for lens, block in (event.get("analyses") or {}).items()
        }
        events.append(row)
    return {**payload, "events": events}


def main() -> None:
    sync_run_id = start_sync_run("push_console_snapshots", {"snapshot_keys": sorted(SNAPSHOTS)})
    pushed = 0
    try:
        for snapshot_key, path in SNAPSHOTS.items():
            if not path.exists():
                print(f"Skip {snapshot_key}: {path.relative_to(ROOT)} missing")
                continue
            payload = load_json(path)
            if snapshot_key == "council_analyses":
                payload = slim_council(payload)
            upsert_console_snapshot(snapshot_key, path, payload)
            pushed += 1
            print(f"Pushed {snapshot_key} from {path.relative_to(ROOT)}")
        # What the console's review queue shows: reference changes awaiting an analyst.
        items = review_items(load_json(REFERENCE_PATH))
        upsert_console_snapshot("content_review_items", REFERENCE_PATH, {"generated_at": now_iso(), "items": items})
        pushed += 1
        print(f"Pushed content_review_items ({len(items)} awaiting review)")
        finish_sync_run(sync_run_id, status="completed", rows_processed=pushed)
        print(f"Completed Supabase snapshot push. Snapshots pushed: {pushed}")
    except Exception as exc:  # noqa: BLE001
        finish_sync_run(sync_run_id, status="failed", rows_processed=pushed, error_message=str(exc))
        raise


if __name__ == "__main__":
    main()
