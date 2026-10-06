#!/usr/bin/env python3
"""Apply analyst decisions from the console's review queue to the repository.

The console writes one row to Supabase `content_reviews` per decision. This step reads
the rows not yet applied, oldest first, and applies each to
apps/public-site/reference/countries.json through review_reference.decide(), the same
code the command line uses. A decision is applied only if its item_key still matches
what is awaiting review; otherwise it is stamped as superseded. Every row handled is
stamped with applied_at, so nothing is applied twice.

Rows of kind "scenario" are left alone: nothing produces scenarios yet.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime

from common import ROOT, finish_sync_run, now_iso, postgrest_request, start_sync_run

sys.path.insert(0, str(ROOT / "scripts" / "reference"))
from review_reference import CHANGES, REFERENCE, decide, item_key  # noqa: E402


def apply_rows(rows: list[dict], reference: dict, log: dict, today) -> list[tuple[dict, str]]:
    """Apply decisions in order. Returns (row, note) for each row that was handled."""
    handled = []
    for row in rows:
        if row.get("kind") != "reference_proposal":
            continue
        country = next((c for c in reference["countries"] if c["name"] == row.get("subject")), None)
        if not country or item_key(country) != row.get("item_key"):
            handled.append((row, "superseded: no longer awaiting review"))
            continue
        action = row.get("decision")
        if row["item_key"].split("|")[1] == "signoff":
            if action != "approve":
                handled.append((row, "ignored: a sign-off can only be approved"))
                continue
            action = "signoff"
        logged = decide(reference, log, country["name"], action, row.get("reviewer_name") or "analyst", today)
        handled.append((row, logged))
    return handled


def main() -> None:
    sync_run_id = start_sync_run("pull_content_reviews", {})
    count = 0
    try:
        try:
            rows = postgrest_request("GET", "content_reviews", query={
                "select": "content_review_id,kind,subject,item_key,decision,reviewer_name,created_at",
                "applied_at": "is.null", "order": "created_at.asc"})
        except RuntimeError as exc:
            # The table arrives with migration 20261006090000. Until it is applied there
            # are no decisions to read, and the rest of the sync must still run.
            if "(404)" not in str(exc) and "PGRST205" not in str(exc):
                raise
            print("content_reviews table not found; migration not applied yet. Skipping.")
            finish_sync_run(sync_run_id, status="completed", rows_processed=0)
            return
        rows = rows if isinstance(rows, list) else []
        reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
        log = json.loads(CHANGES.read_text(encoding="utf-8")) if CHANGES.exists() else {"changes": []}
        handled = apply_rows(rows, reference, log, datetime.now(UTC).date())
        if any(note in ("approved", "dismissed", "signed_off") for _, note in handled):
            REFERENCE.write_text(json.dumps(reference, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            CHANGES.write_text(json.dumps(log, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        for row, note in handled:
            postgrest_request("PATCH", "content_reviews", query={"content_review_id": f"eq.{row['content_review_id']}"},
                              payload={"applied_at": now_iso(), "applied_note": note}, prefer="return=minimal")
            print(f"{row['subject']}: {note}")
            count += 1
        finish_sync_run(sync_run_id, status="completed", rows_processed=count)
        print(f"Content reviews handled: {count}")
    except Exception as exc:  # noqa: BLE001
        finish_sync_run(sync_run_id, status="failed", rows_processed=count, error_message=str(exc))
        raise


if __name__ == "__main__":
    main()
