#!/usr/bin/env python3
"""Push local SENTINEL JSON layers into Supabase console snapshots."""

from __future__ import annotations

from pathlib import Path

from common import ROOT, finish_sync_run, load_json, start_sync_run, upsert_console_snapshot


SNAPSHOTS: dict[str, Path] = {
    "review_queue": ROOT / "data" / "review" / "review_queue.json",
    "qa_report": ROOT / "data" / "review" / "qa_report.json",
    "registry_qa_report": ROOT / "data" / "review" / "registry_qa_report.json",
    "duplicate_candidates": ROOT / "data" / "review" / "duplicate_candidates.json",
    "council_analyses": ROOT / "data" / "review" / "council_analyses.json",
    "canonical_events": ROOT / "data" / "canonical" / "events_actor_coded.json",
    "published_events": ROOT / "data" / "published" / "events_public.json",
    "country_monitors": ROOT / "data" / "published" / "country_monitors.json",
    "actor_registry": ROOT / "config" / "actors" / "actor_registry.json",
}


def main() -> None:
    sync_run_id = start_sync_run("push_console_snapshots", {"snapshot_keys": sorted(SNAPSHOTS)})
    pushed = 0
    try:
        for snapshot_key, path in SNAPSHOTS.items():
            if not path.exists():
                print(f"Skip {snapshot_key}: {path.relative_to(ROOT)} missing")
                continue
            payload = load_json(path)
            upsert_console_snapshot(snapshot_key, path, payload)
            pushed += 1
            print(f"Pushed {snapshot_key} from {path.relative_to(ROOT)}")
        finish_sync_run(sync_run_id, status="completed", rows_processed=pushed)
        print(f"Completed Supabase snapshot push. Snapshots pushed: {pushed}")
    except Exception as exc:  # noqa: BLE001
        finish_sync_run(sync_run_id, status="failed", rows_processed=pushed, error_message=str(exc))
        raise


if __name__ == "__main__":
    main()
