#!/usr/bin/env python3
"""Pull Supabase registry edits into the local analyst registry edit file."""

from __future__ import annotations

from pathlib import Path

from common import ROOT, finish_sync_run, now_iso, postgrest_request, start_sync_run, write_json

OUT = ROOT / "data" / "review" / "registry_edits.local.json"


def map_registry_edit(row: dict) -> dict:
    payload = row.get("payload") or {}
    return {
        "edit_id": row.get("registry_edit_id"),
        "action": row.get("action") or payload.get("action") or "upsert_registry_entry",
        "registry_id": payload.get("registry_id"),
        "source_registry_id": payload.get("source_registry_id"),
        "target_registry_id": payload.get("target_registry_id"),
        "source_event_id": payload.get("source_event_id"),
        "source_actor_id": payload.get("source_actor_id"),
        "alias": payload.get("alias"),
        "editor_name": row.get("editor_name"),
        "editor_role": row.get("editor_role"),
        "edited_at": row.get("created_at"),
        "comment": payload.get("comment"),
        "entry": payload.get("entry") or {},
    }


def main() -> None:
    sync_run_id = start_sync_run("pull_registry_edits", {})
    count = 0
    try:
        rows = postgrest_request(
            "GET",
            "registry_edits",
            query={
                "select": "registry_edit_id,action,payload,editor_name,editor_role,created_at",
                "order": "created_at.asc",
            },
        )
        edits = [map_registry_edit(row) for row in rows] if isinstance(rows, list) else []
        payload = {
            "schema_version": "1.0",
            "updated_at": now_iso(),
            "edits": edits,
        }
        write_json(OUT, payload)
        count = len(edits)
        finish_sync_run(sync_run_id, status="completed", rows_processed=count)
        print(f"Wrote {OUT.relative_to(ROOT)}")
        print(f"Registry edits pulled: {count}")
    except Exception as exc:  # noqa: BLE001
        finish_sync_run(sync_run_id, status="failed", rows_processed=count, error_message=str(exc))
        raise


if __name__ == "__main__":
    main()
