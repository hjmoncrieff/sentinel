#!/usr/bin/env python3
"""
Recode events that predate codebook v3, in place.

Events classified with the v2 prompt (no `v3` block) are recoded from their
primary report. The event keeps its id, sentinel_id, title, date, sources and
links; only the coding changes, and the old coding is kept under `v2`.

  prepare  Write one article record per event to <run_dir>/articles.jsonl (and
           direct.jsonl for links that go straight to the publisher). Fetch
           opening text with scripts/enrich_ledes.py <run_dir> --ids <file>.
  input    Write <run_dir>/to_code.jsonl: the records with their fetched text,
           ready for scripts/classify_v3.py code.
  apply    Merge <codes.jsonl> into data/events.json.

Not recoded: events with a saved analyst edit, hand-curated events
(source_method manual_web_audit), and events without a report URL (ACLED rows).

An event the coder judges out of scope is kept, not deleted: it gets
`v3.relevant = false`, low salience and `v3_review = "judged_out_of_scope"`,
so an analyst can decide.

Usage:
  python3 scripts/recode_archive_v3.py prepare <run_dir>
  python3 scripts/recode_archive_v3.py input <run_dir>
  python3 scripts/recode_archive_v3.py apply <run_dir> <codes.jsonl> [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import codebook  # noqa: E402
import pipeline_core as pc  # noqa: E402
from enrich_ledes import is_google_news_url, load_ledes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EDITS_PATH = ROOT / "data" / "review" / "edits.local.json"
CONF = {"high": "green", "medium": "yellow", "low": "red"}
V2_FIELDS = ("type", "subtype", "content_type", "deed_type", "axis", "actor", "target", "summary", "country", "conf", "salience")
PREFIX = "ev-"


def edited_event_ids() -> set[str]:
    if not EDITS_PATH.exists():
        return set()
    edits = json.loads(EDITS_PATH.read_text(encoding="utf-8")).get("edits", [])
    return {e["event_id"] for e in edits if e.get("event_id") and (e.get("patch") or e.get("actor_patches"))}


def skip_reason(event: dict, edited: set[str]) -> str | None:
    reports = event.get("linked_reports") or []
    url = (reports[0].get("url") if reports else None) or event.get("url") or ""
    if event.get("v3"):
        return "already_v3"
    if event["id"] in edited:
        return "analyst_edited"
    if any(r.get("source_method") == "manual_web_audit" for r in reports):
        return "hand_curated"
    if not url.startswith("http"):
        return "no_report_url"
    return None


def load_events() -> dict:
    return json.loads(pc.DATA_FILE.read_text(encoding="utf-8"))


def cmd_prepare(args) -> None:
    edited = edited_event_ids()
    records, skipped = [], Counter()
    for event in load_events()["events"]:
        reason = skip_reason(event, edited)
        if reason:
            skipped[reason] += 1
            continue
        reports = event.get("linked_reports") or []
        primary = reports[0] if reports else {}
        records.append({
            "article_id": PREFIX + event["id"],
            "event_id": event["id"],
            "title": primary.get("headline") or event["title"],
            "date": event["date"],
            "url": primary.get("url") or event.get("url"),
            "source": primary.get("source_name") or event.get("source"),
            "description": primary.get("description") or "",
            "other_headlines": [r["headline"] for r in reports[1:4] if r.get("headline")],
        })
    args.run_dir.mkdir(parents=True, exist_ok=True)
    direct = [r for r in records if not is_google_news_url(r["url"])]
    for name, rows in (("articles.jsonl", records), ("direct.jsonl", direct)):
        (args.run_dir / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps({"to_recode": len(records), "direct_links": len(direct), "skipped": dict(skipped)}))


def cmd_input(args) -> None:
    ledes = load_ledes(args.run_dir)
    rows, with_text = [], 0
    for line in (args.run_dir / "articles.jsonl").read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        entry = ledes.get(record["article_id"]) or {}
        if entry.get("status") == "ok":
            record["description"], with_text = entry["lede"], with_text + 1
        if record.get("other_headlines") and record.get("description"):
            record["description"] += "\n\nOther reports of the same event: " + " | ".join(record["other_headlines"])
        rows.append(record)
    (args.run_dir / "to_code.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps({"records": len(rows), "with_opening_text": with_text, "headline_only": len(rows) - with_text}))


def recode_event(event: dict, item: dict, coded_by: str, now: str) -> str:
    """Apply one v3 coding to an event in place. Returns 'recoded' or 'out_of_scope'."""
    event["v2"] = {k: event.get(k) for k in V2_FIELDS}
    event["v3"] = {**item, "publication_date": event.get("date"), "codebook_version": codebook.load()["version"],
                   "coded_by": coded_by, "recoded_at": now}
    if not item.get("relevant"):
        event["salience"] = "low"
        event["v3_review"] = "judged_out_of_scope"
        return "out_of_scope"
    legacy_type, legacy_sub = codebook.legacy_family(item.get("type"), item.get("subtype"))
    actor, target = codebook.legacy_actor_target(item.get("actors") or [])
    event.update({
        "type": legacy_type,
        "subtype": legacy_sub,
        "content_type": item.get("content_type") or "event",
        "deed_type": None if item.get("deed_type") == "not_applicable" else item.get("deed_type"),
        "axis": None if item.get("axis") == "not_applicable" else item.get("axis"),
        "actor": actor,
        "target": target,
        "conf": CONF.get(item.get("certainty"), "yellow"),
        "salience": item.get("salience") or "low",
    })
    if item.get("summary"):
        event["summary"] = item["summary"]
    # The country is part of the citable sentinel_id, so it only changes when the old
    # value was the catch-all "Regional" and the coder names a monitored country.
    if event.get("country") == "Regional" and item.get("country"):
        event["country"] = item["country"]
    return "recoded"


def cmd_apply(args) -> None:
    store = load_events()
    by_id = {e["id"]: e for e in store["events"]}
    edited = edited_event_ids()
    now = datetime.now(timezone.utc).isoformat()
    outcome, changes = Counter(), Counter()
    for line in args.codes.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        event = by_id.get((row.get("article_id") or "")[len(PREFIX):])
        if not event:
            outcome["event_missing"] += 1
        elif not row.get("item"):
            outcome["coding_error"] += 1
        elif skip_reason(event, edited):
            outcome[skip_reason(event, edited)] += 1
        else:
            before = (event.get("type"), event.get("salience"))
            result = recode_event(event, row["item"], row.get("model") or "claude-sonnet-5-5", now)
            outcome[result] += 1
            if result == "recoded":
                changes["type_changed"] += before[0] != event["type"]
                changes[f"salience {before[1]} → {event['salience']}"] += 1
    print(json.dumps({"outcome": dict(outcome), "type_changed": changes.pop("type_changed", 0),
                      "salience": dict(sorted(changes.items()))}, ensure_ascii=False, indent=1))
    if not args.dry_run:
        pc.DATA_FILE.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("prepare", "input", "apply"):
        p = sub.add_parser(name)
        p.add_argument("run_dir", type=Path)
        if name == "apply":
            p.add_argument("codes", type=Path)
            p.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    {"prepare": cmd_prepare, "input": cmd_input, "apply": cmd_apply}[args.cmd](args)


if __name__ == "__main__":
    main()
