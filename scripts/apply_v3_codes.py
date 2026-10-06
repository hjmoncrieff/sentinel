#!/usr/bin/env python3
"""
Turn codebook v3 codings of staged articles into event records in data/events.json.

Each relevant coded article becomes a candidate event carrying its full v3
coding under `v3`, plus the v2 fields the current site and pipeline read
(type via codebook.legacy_family, conf from certainty, actor/target, salience,
deed_type, axis). Candidates are grouped per country with the existing
same-incident clustering step and merged into the event store with the
pipeline's save_events. Articles already linked to a stored event are skipped.

Usage:
  python3 scripts/apply_v3_codes.py <run_dir> <codes.jsonl> [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import codebook  # noqa: E402
import pipeline_core as pc  # noqa: E402
from enrich_ledes import apply_ledes  # noqa: E402

log = logging.getLogger("apply_v3")
CONF = {"high": "green", "medium": "yellow", "low": "red"}


def load_staged(run_dir: Path) -> dict[str, dict]:
    articles = [json.loads(line) for f in sorted(run_dir.glob("*.jsonl"))
                for line in f.read_text(encoding="utf-8").splitlines() if line.strip()]
    apply_ledes(articles, run_dir)
    pc.fill_source_metadata(articles)
    return {a["article_id"]: a for a in articles if a.get("article_id")}


def to_event(article: dict, item: dict, now: str, coded_by: str = "claude-sonnet-5-5") -> dict:
    country = item.get("country") or "Regional"
    legacy_type, legacy_sub = codebook.legacy_family(item.get("type"), item.get("subtype"))
    precise = item.get("date_precision") == "day" and item.get("event_date")
    date = item["event_date"] if precise else article.get("date")
    parts = [item.get("location_place"), item.get("location_admin1")]
    place = ", ".join(dict.fromkeys(x for x in parts if x))
    coords = article.get("coords") or pc.geolocate(article.get("title", ""), country, place)
    actor, target = codebook.legacy_actor_target(item.get("actors") or [])
    url = article.get("publisher_url") or article.get("url") or ""
    iid = pc.stable_id(country, legacy_type, date, url or article.get("title", ""))
    return {
        "id": iid,
        "sentinel_id": pc.make_sentinel_id(country, date, iid),
        "type": legacy_type,
        "subtype": legacy_sub,
        "content_type": item.get("content_type") or "event",
        "deed_type": None if item.get("deed_type") == "not_applicable" else item.get("deed_type"),
        "axis": None if item.get("axis") == "not_applicable" else item.get("axis"),
        "actor": actor,
        "target": target,
        "title": pc.clean_headline(article.get("title", ""), article.get("source_method")),
        "summary": item.get("summary") or "",
        "country": country,
        "location": place or None,
        "date": date,
        "source": article.get("source"),
        "sources": [article.get("source")],
        "conf": CONF.get(item.get("certainty"), "yellow"),
        "salience": item.get("salience") or "low",
        "coords": coords,
        "url": url,
        "links": [url] if url else [],
        "source_article_ids": [article["article_id"]],
        "linked_reports": [{
            "article_id": article["article_id"], "article_rank": 1, "report_role": "primary",
            "source_name": article.get("source"), "url": url, "link_domain": article.get("source_domain"),
            "headline": article.get("title"), "description": pc.report_excerpt(article.get("description")),
            "source_type": article.get("source_type"), "source_method": article.get("source_method"),
            "source_tier": article.get("source_tier"), "source_role": article.get("source_role"),
            "source_policy": article.get("source_policy"), "source_quality_weight": article.get("source_quality_weight"),
            "linked_at": article.get("normalized_at") or now,
        }],
        "source_diversity": 1,
        "trusted_source_count": 1 if (article.get("source_tier") or 99) <= 2 else 0,
        "ai_analysis": None,
        "ingested_at": now,
        "v3": {**item, "publication_date": article.get("date"), "codebook_version": codebook.load()["version"],
               "coded_by": coded_by},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("codes", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    staged = load_staged(args.run_dir)
    existing = {e["id"]: e for e in json.loads(pc.DATA_FILE.read_text(encoding="utf-8"))["events"]}
    seen_articles = {aid for e in existing.values() for aid in (e.get("source_article_ids") or [])}
    now = datetime.now(timezone.utc).isoformat()

    candidates, skipped = [], defaultdict(int)
    for line in args.codes.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        item, aid = row.get("item"), row.get("article_id")
        if not item:
            skipped["error"] += 1
        elif not item.get("relevant"):
            skipped["not_relevant"] += 1
        elif aid in seen_articles:
            skipped["already_stored"] += 1
        elif aid not in staged:
            skipped["missing_article"] += 1
        else:
            candidates.append(to_event(staged[aid], item, now))
    log.info(f"{len(candidates)} candidate events; skipped {dict(skipped)}")
    if args.dry_run:
        return

    client = pc.anthropic.Anthropic()
    by_country: dict[str, list] = defaultdict(list)
    for ev in candidates:
        by_country[ev["country"]].append(ev)
    merged: list[dict] = []
    for _country, evs in by_country.items():
        for i in range(0, len(evs), pc.CLUSTER_BATCH):
            chunk = evs[i:i + pc.CLUSTER_BATCH]
            for idxs in pc._cluster_events(client, chunk) if len(chunk) > 1 else [[0]]:
                group = [chunk[j] for j in idxs if j < len(chunk)]
                if group:
                    merged.append(pc._merge_cluster(group))
    added = pc.save_events(existing, merged)
    log.info(f"Clustered {len(candidates)} → {len(merged)} events; {added} new in {pc.DATA_FILE}")


if __name__ == "__main__":
    main()
