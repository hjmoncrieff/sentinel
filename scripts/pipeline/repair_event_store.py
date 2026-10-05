#!/usr/bin/env python3
"""
One-off repairs to data/events.json after the 2026-09-29 fixes.

  --geolocation   Re-geolocate events whose coordinates fall outside their own
                  country (the substring-matching bug put 14% of events in Brazil).
                  Events with a plausible location keep it.
  --excerpts      Attach stored source excerpts to linked reports that lack one,
                  using the article records in data/staging/.
  --stale-dea     Remove DEA releases dated before 2026-01-01 that were ingested
                  on 2026-09-29 (the scraper ignored its lookback cutoff).

Usage:
  python3 scripts/pipeline/repair_event_store.py --geolocation --excerpts --stale-dea [--dry-run]
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import pipeline_core as pc  # noqa: E402

FAR_DEGREES = 15


def misplaced(event: dict) -> bool:
    centroid = pc.COUNTRY_CENTROIDS.get(event.get("country"))
    coords = event.get("coords")
    if not centroid or not coords:
        return False
    return abs(coords[0] - centroid[0]) > FAR_DEGREES or abs(coords[1] - centroid[1]) > FAR_DEGREES


def staged_descriptions() -> dict[str, str]:
    out: dict[str, str] = {}
    files = glob.glob(str(ROOT / "data/staging/*_articles.json")) + glob.glob(str(ROOT / "data/staging/historical/*/*.jsonl"))
    for f in files:
        rows = ([json.loads(line) for line in open(f, encoding="utf-8") if line.strip()]
                if f.endswith(".jsonl") else json.load(open(f, encoding="utf-8")).get("articles", []))
        for r in rows:
            text = pc.report_excerpt(r.get("description"))
            if r.get("article_id") and text and len(text) > len(out.get(r["article_id"], "")):
                out[r["article_id"]] = text
    for f in glob.glob(str(ROOT / "data/staging/historical/*/_ledes.json")):
        for aid, entry in json.load(open(f, encoding="utf-8")).items():
            if entry.get("status") == "ok" and entry.get("lede"):
                out[aid] = pc.report_excerpt(entry["lede"])
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--geolocation", action="store_true")
    parser.add_argument("--excerpts", action="store_true")
    parser.add_argument("--stale-dea", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    store = json.loads(pc.DATA_FILE.read_text(encoding="utf-8"))
    events = store["events"]
    report = {}
    if args.stale_dea:
        before = len(events)
        events = [e for e in events if not (e.get("source") == "DEA" and e.get("date", "") < "2026-01-01"
                                             and (e.get("ingested_at") or "").startswith("2026-09-29"))]
        report["stale_dea_removed"] = before - len(events)
    if args.geolocation:
        fixed = 0
        for e in events:
            if misplaced(e):
                e["coords"] = pc.geolocate(f"{e.get('location') or ''} {e.get('title', '')} {e.get('summary') or ''}", e["country"])
                fixed += 1
        report["geolocation_fixed"] = fixed
        report["still_misplaced"] = sum(misplaced(e) for e in events)
    if args.excerpts:
        texts = staged_descriptions()
        added = 0
        for e in events:
            for r in e.get("linked_reports") or []:
                if not r.get("description") and texts.get(r.get("article_id")):
                    r["description"] = texts[r["article_id"]]
                    added += 1
        report["excerpts_added"] = added
    print(json.dumps(report))
    if not args.dry_run:
        store["events"], store["count"] = events, len(events)
        pc.DATA_FILE.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
