#!/usr/bin/env python3
"""Pull published dashboard artifacts from Supabase into local JSON files."""

from __future__ import annotations

from pathlib import Path

from common import ROOT, fetch_console_snapshots, finish_sync_run, start_sync_run, write_json


EXPORT_TARGETS: dict[str, Path] = {
    "published_events": ROOT / "data" / "published" / "events_public.json",
    "country_monitors": ROOT / "data" / "published" / "country_monitors.json",
}


def main() -> None:
    sync_run_id = start_sync_run("export_published_snapshot", {"snapshot_keys": sorted(EXPORT_TARGETS)})
    written = 0
    try:
        snapshots = fetch_console_snapshots(list(EXPORT_TARGETS))
        for snapshot_key, path in EXPORT_TARGETS.items():
            payload = snapshots.get(snapshot_key)
            if not payload:
                print(f"Skip {snapshot_key}: snapshot missing in Supabase")
                continue
            write_json(path, payload)
            written += 1
            print(f"Wrote {path.relative_to(ROOT)} from {snapshot_key}")
        finish_sync_run(sync_run_id, status="completed", rows_processed=written)
        print(f"Completed Supabase published export. Files written: {written}")
    except Exception as exc:  # noqa: BLE001
        finish_sync_run(sync_run_id, status="failed", rows_processed=written, error_message=str(exc))
        raise


if __name__ == "__main__":
    main()
