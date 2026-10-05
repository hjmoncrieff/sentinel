#!/usr/bin/env python3
"""
Review proposed changes to the country reference.

refresh_country_reference.py stores what it finds as a proposal on each country.
The public page keeps the current values, marked "Under review", until one of:

  python3 scripts/reference/review_reference.py list
  python3 scripts/reference/review_reference.py show Colombia
  python3 scripts/reference/review_reference.py approve Colombia --reviewer HM
  python3 scripts/reference/review_reference.py dismiss Colombia --reviewer HM

Approve publishes the proposed officials, elections and notes and records the
reviewer and date. Dismiss drops the proposal (a false trigger or a wrong
finding). Both are logged in apps/public-site/reference/changes.json. To correct
a single name, edit countries.json by hand and set "reviewed".
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from refresh_country_reference import CHANGES, REFERENCE, apply_proposal  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    for name in ("show", "approve", "dismiss"):
        p = sub.add_parser(name)
        p.add_argument("country")
        if name != "show":
            p.add_argument("--reviewer", required=True, help="Initials or name recorded with the decision")
    args = parser.parse_args()

    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
    pending = [c for c in reference["countries"] if c.get("proposed")]
    if args.cmd == "list":
        for c in pending:
            print(f"{c['name']} (proposed {c['proposed']['date']}; {c['proposed']['trigger']})")
            for change in c["proposed"]["changes"]:
                print(f"    {change}")
        print(f"{len(pending)} countries await review.")
        return
    country = next((c for c in reference["countries"] if c["name"].lower() == args.country.lower()), None)
    if not country:
        raise SystemExit(f"Unknown country: {args.country}")
    if not country.get("proposed"):
        raise SystemExit(f"{country['name']} has no proposal awaiting review.")
    if args.cmd == "show":
        print(json.dumps(country["proposed"], ensure_ascii=False, indent=1))
        return
    today = datetime.now(UTC).date()
    log = json.loads(CHANGES.read_text(encoding="utf-8")) if CHANGES.exists() else {"changes": []}
    if args.cmd == "approve":
        changes = apply_proposal(country, args.reviewer, today)
    else:
        changes = country.pop("proposed")["changes"]
    log["changes"].append({"date": today.isoformat(), "country": country["name"], "action": {"approve": "approved", "dismiss": "dismissed"}[args.cmd],
                           "reviewer": args.reviewer, "changes": changes})
    REFERENCE.write_text(json.dumps(reference, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    CHANGES.write_text(json.dumps(log, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{country['name']}: proposal {log['changes'][-1]['action']} by {args.reviewer}.")


if __name__ == "__main__":
    main()
