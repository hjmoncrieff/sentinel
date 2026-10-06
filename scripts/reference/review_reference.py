#!/usr/bin/env python3
"""
Review proposed changes to the country reference.

refresh_country_reference.py stores what it finds as a proposal on each country.
The public page keeps the current values, marked "Under review", until one of:

  python3 scripts/reference/review_reference.py list
  python3 scripts/reference/review_reference.py show Colombia
  python3 scripts/reference/review_reference.py approve Colombia --reviewer HM
  python3 scripts/reference/review_reference.py dismiss Colombia --reviewer HM
  python3 scripts/reference/review_reference.py signoff Colombia --reviewer HM

Approve publishes the proposed officials, elections and notes and records the
reviewer and date. Dismiss drops the proposal (a false trigger or a wrong
finding). Both are logged in apps/public-site/reference/changes.json. To correct
a single name, edit countries.json by hand and set "reviewed".

Signoff is for an entry that was updated automatically before the review step
existed (it has `auto_updated` and no `reviewed`): it records the reviewer and
changes nothing else.

The analyst console shows the same items (review_items) and its decisions are
applied by scripts/sync/pull_content_reviews_from_supabase.py through decide().
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from refresh_country_reference import CHANGES, REFERENCE, apply_proposal  # noqa: E402


def item_key(country: dict) -> str | None:
    """Identifies exactly what is awaiting review, so a decision is never applied to a later proposal."""
    if country.get("proposed"):
        return f"{country['name']}|proposal|{country['proposed']['date']}"
    if country.get("auto_updated") and not country.get("reviewed"):
        return f"{country['name']}|signoff|{country['auto_updated']}"
    return None


def review_items(reference: dict) -> list[dict]:
    """What the console queue shows: one item per country with something to review."""
    items = []
    for country in reference["countries"]:
        key = item_key(country)
        if not key:
            continue
        proposal = country.get("proposed")
        record = (proposal or {}).get("record") or {}
        current = {o["post"]: o for o in country.get("officials") or []}
        rows = []
        for official in record.get("officials") or []:
            before = current.get(official.get("post")) or {}
            rows.append({"field": official.get("title") or official.get("post"), "current": before.get("name") or None,
                         "proposed": official.get("name") or None, "source_url": official.get("source_url") or None,
                         "changed": (before.get("name") or None) != (official.get("name") or None)})
        if not proposal:
            rows = [{"field": o.get("title") or o.get("post"), "current": o.get("name") or None, "proposed": o.get("name") or None,
                     "source_url": o.get("source_url") or None, "changed": False} for o in country.get("officials") or []]
        items.append({
            "kind": "reference_proposal",
            "mode": "proposal" if proposal else "signoff",
            "subject": country["name"],
            "item_key": key,
            "date": (proposal or {}).get("date") or country.get("auto_updated"),
            "trigger": (proposal or {}).get("trigger") or "Updated automatically before the review step existed",
            "summary": (proposal or {}).get("changes") or [],
            "rows": rows,
            "note": record.get("summary_note") or country.get("note"),
            "watch": record.get("watch_note") or country.get("watch"),
        })
    return items


def decide(reference: dict, log: dict, name: str, action: str, reviewer: str, today) -> str:
    """Apply one decision in place. action: approve | dismiss | signoff. Returns the logged action."""
    country = next((c for c in reference["countries"] if c["name"].lower() == name.lower()), None)
    if not country:
        raise ValueError(f"Unknown country: {name}")
    if action == "signoff":
        if country.get("proposed") or not country.get("auto_updated") or country.get("reviewed"):
            raise ValueError(f"{country['name']} has nothing to sign off.")
        country["reviewed"], country["reviewed_by"] = today.isoformat(), reviewer
        changes, logged = ["Automatic update signed off as reviewed"], "signed_off"
    else:
        if not country.get("proposed"):
            raise ValueError(f"{country['name']} has no proposal awaiting review.")
        if action == "approve":
            changes, logged = apply_proposal(country, reviewer, today), "approved"
        elif action == "dismiss":
            changes, logged = country.pop("proposed")["changes"], "dismissed"
        else:
            raise ValueError(f"Unknown action: {action}")
    log.setdefault("changes", []).append({"date": today.isoformat(), "country": country["name"], "action": logged,
                                          "reviewer": reviewer, "changes": changes})
    return logged


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    for name in ("show", "approve", "dismiss", "signoff"):
        p = sub.add_parser(name)
        p.add_argument("country")
        if name != "show":
            p.add_argument("--reviewer", required=True, help="Initials or name recorded with the decision")
    args = parser.parse_args()

    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
    if args.cmd == "list":
        items = review_items(reference)
        for item in items:
            print(f"{item['subject']} ({item['mode']}, {item['date']}; {item['trigger']})")
            for change in item["summary"]:
                print(f"    {change}")
        print(f"{len(items)} countries await review.")
        return
    country = next((c for c in reference["countries"] if c["name"].lower() == args.country.lower()), None)
    if not country:
        raise SystemExit(f"Unknown country: {args.country}")
    if args.cmd == "show":
        if not country.get("proposed"):
            raise SystemExit(f"{country['name']} has no proposal awaiting review.")
        print(json.dumps(country["proposed"], ensure_ascii=False, indent=1))
        return
    log = json.loads(CHANGES.read_text(encoding="utf-8")) if CHANGES.exists() else {"changes": []}
    try:
        logged = decide(reference, log, args.country, args.cmd, args.reviewer, datetime.now(UTC).date())
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    REFERENCE.write_text(json.dumps(reference, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    CHANGES.write_text(json.dumps(log, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{country['name']}: {logged.replace('_', ' ')} by {args.reviewer}.")


if __name__ == "__main__":
    main()
