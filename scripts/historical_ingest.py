#!/usr/bin/env python3
"""
Historical archive ingestion for SENTINEL.

This is separate from the fast monitoring pipeline. It plans and runs deep
backfill (e.g. 2000+) from the sources registered in
config/historical_sources.json, and writes article-level staging batches that
the main pipeline then classifies.

Work is split into units of (source, calendar month). Each unit writes one
JSONL file and is recorded in a checkpoint, so an interrupted or rate-limited
run resumes where it stopped. After each run an archive-quality report flags
coverage gaps, cross-batch duplicates, and source imbalance.

Usage:
  # Plan only (unchanged behaviour)
  python3 scripts/historical_ingest.py --since 2015-01-01
  python3 scripts/historical_ingest.py --since 2015-01-01 --json

  # Execute
  python3 scripts/historical_ingest.py --since 2015-01-01 --until 2015-12-31 --run
  python3 scripts/historical_ingest.py --since 2015-01-01 --until 2015-12-31 --run --dry-run
  python3 scripts/historical_ingest.py --since 2015-01-01 --until 2015-12-31 --run \
      --source insight_crime_archive --max-units 12
  python3 scripts/historical_ingest.py ... --run --retry-empty   # re-fetch zero-article months

  # Then classify the staged articles
  python3 scripts/run_pipeline.py --from-staging data/staging/historical/2015-01-01_2015-12-31

Output layout (data/staging/historical/ is gitignored):
  data/staging/historical/<since>_<until>/
    <source_id>__<YYYY-MM>.jsonl   article records (normalize_articles schema)
    _checkpoint.json               completed / failed units
    _qa.json                       archive-quality report
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "config" / "historical_sources.json"
STAGING_DIR = ROOT / "data" / "staging"
HISTORICAL_DIR = STAGING_DIR / "historical"

CHECKPOINT_NAME = "_checkpoint.json"
QA_NAME = "_qa.json"
IMBALANCE_SHARE = 0.6  # flag any source contributing more than this share of articles

log = logging.getLogger("sentinel.historical")

Connector = Callable[[dict, datetime, datetime], list[dict]]


@dataclass
class HistoricalRequest:
    since: str
    until: str
    groups: list[str]
    dry_run: bool
    sources: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Unit:
    source_id: str
    month: str  # YYYY-MM
    start: datetime
    end: datetime

    @property
    def key(self) -> str:
        return f"{self.source_id}:{self.month}"

    @property
    def filename(self) -> str:
        return f"{self.source_id}__{self.month}.jsonl"


# ── Manifest / planning ────────────────────────────────────────────────────────

def load_manifest(path: Path = MANIFEST_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_date(value: str) -> str:
    datetime.strptime(value, "%Y-%m-%d")
    return value


def build_plan(request: HistoricalRequest, manifest: dict) -> dict:
    source_groups = manifest.get("source_groups", [])
    selected = []
    for group in source_groups:
        if request.groups and group.get("group_id") not in request.groups:
            continue
        selected.append({
            "group_id": group.get("group_id"),
            "label": group.get("label"),
            "priority": group.get("priority"),
            "sources": [
                {
                    "source_id": source.get("source_id"),
                    "label": source.get("label"),
                    "connector_type": source.get("connector_type"),
                    "historical_ready": source.get("historical_ready"),
                    "coverage_start": source.get("coverage_start"),
                    "notes": source.get("notes")
                }
                for source in group.get("sources", [])
            ]
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "request": {
            "since": request.since,
            "until": request.until,
            "groups": request.groups or [group.get("group_id") for group in selected],
            "dry_run": request.dry_run
        },
        "manifest_path": str(MANIFEST_PATH.relative_to(ROOT)),
        "status": "planning_only",
        "recommended_output_dir": str(run_dir_for(request).relative_to(ROOT)),
        "notes": [
            "Deep historical ingest should be treated as a separate pipeline from the fast monitoring workflow.",
            "RSS feeds and recent-search APIs are not sufficient for complete 2000+ coverage.",
            "Structured datasets and source-specific archive connectors should be prioritized before generic search APIs."
        ],
        "source_groups": selected
    }


def print_summary(plan: dict) -> None:
    req = plan["request"]
    print("SENTINEL historical ingestion plan")
    print(f"Window: {req['since']} -> {req['until']}")
    print(f"Mode: {'dry-run' if req['dry_run'] else 'planning'}")
    print("")
    for group in plan["source_groups"]:
        print(f"- {group['label']} [{group['group_id']}]")
        for source in group["sources"]:
            print(
                f"  - {source['label']} | {source['connector_type']} | "
                f"historical_ready={source['historical_ready']} | "
                f"coverage_start={source['coverage_start'] or 'unknown'}"
            )


# ── Units ──────────────────────────────────────────────────────────────────────

def run_dir_for(request: HistoricalRequest, base: Path = HISTORICAL_DIR) -> Path:
    return base / f"{request.since}_{request.until}"


def month_windows(since: str, until: str) -> list[tuple[str, datetime, datetime]]:
    """Calendar-month windows covering [since, until] inclusive, clipped at both ends."""
    start = datetime.strptime(since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    stop = datetime.strptime(until, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    # `until` is inclusive: the window ends at the start of the following day.
    stop = datetime.combine(stop.date(), datetime.min.time(), tzinfo=timezone.utc).replace(hour=23, minute=59, second=59)
    windows = []
    cursor = start.replace(day=1)
    while cursor <= stop:
        nxt = cursor.replace(year=cursor.year + 1, month=1) if cursor.month == 12 else cursor.replace(month=cursor.month + 1)
        windows.append((cursor.strftime("%Y-%m"), max(cursor, start), min(nxt, stop)))
        cursor = nxt
    return windows


def select_sources(manifest: dict, request: HistoricalRequest, connectors: dict[str, Connector]) -> tuple[list[dict], list[dict]]:
    """Return (runnable sources, skipped sources with reasons)."""
    runnable, skipped = [], []
    for group in manifest.get("source_groups", []):
        if request.groups and group.get("group_id") not in request.groups:
            continue
        for source in group.get("sources", []):
            if request.sources and source.get("source_id") not in request.sources:
                continue
            reason = None
            if source.get("connector_type") not in connectors:
                reason = f"no runner for connector_type={source.get('connector_type')}"
            elif source.get("historical_ready") is False:
                reason = "historical_ready=false"
            elif source.get("connector_type") == "wordpress_archive" and not source.get("endpoint"):
                reason = "no endpoint configured"
            if reason:
                skipped.append({"source_id": source.get("source_id"), "reason": reason})
            else:
                runnable.append(source)
    return runnable, skipped


def build_units(sources: list[dict], request: HistoricalRequest) -> list[Unit]:
    units = []
    windows = month_windows(request.since, request.until)
    for source in sources:
        floor = source.get("coverage_start")
        for month, start, end in windows:
            if floor and end.date() <= date.fromisoformat(floor):
                continue  # before the source's archive begins
            units.append(Unit(source["source_id"], month, start, end))
    return units


# ── Connectors ─────────────────────────────────────────────────────────────────

def default_connectors(conservative: bool = False) -> dict[str, Connector]:
    """Real network connectors, imported lazily so planning and tests stay offline."""

    def gdelt(source: dict, start: datetime, end: datetime) -> list[dict]:
        from ingest_gdelt import fetch_gdelt_range, normalize_gdelt
        return normalize_gdelt(fetch_gdelt_range(start, end, conservative=conservative))

    def wordpress(source: dict, start: datetime, end: datetime) -> list[dict]:
        from ingest_rss import fetch_wordpress_archive
        return fetch_wordpress_archive({"name": source["label"], "base": source["endpoint"]}, start, end)

    return {"gdelt": gdelt, "wordpress_archive": wordpress}


# ── Checkpoint + execution ─────────────────────────────────────────────────────

def _atomic_write_json(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_checkpoint(run_dir: Path) -> dict:
    path = run_dir / CHECKPOINT_NAME
    if not path.exists():
        return {"completed": {}, "failed": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def run_units(
    units: list[Unit],
    sources_by_id: dict[str, dict],
    connectors: dict[str, Connector],
    run_dir: Path,
    *,
    max_units: int | None = None,
    retry_empty: bool = False,
    pause_seconds: float = 0.0,
) -> dict:
    """Execute pending units, checkpointing after each. Returns the checkpoint."""
    run_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = load_checkpoint(run_dir)
    done = checkpoint["completed"]

    pending = [
        u for u in units
        if u.key not in done or (retry_empty and done[u.key].get("count") == 0)
    ]
    if max_units is not None:
        pending = pending[:max_units]
    log.info(f"Units: {len(units)} total, {len(units) - len(pending)} already complete, running {len(pending)}")

    for i, unit in enumerate(pending, 1):
        source = sources_by_id[unit.source_id]
        try:
            articles = connectors[source["connector_type"]](source, unit.start, unit.end)
        except Exception as exc:  # connector crashed: leave the unit pending for resume
            checkpoint["failed"][unit.key] = {"error": str(exc), "at": datetime.now(timezone.utc).isoformat()}
            _atomic_write_json(run_dir / CHECKPOINT_NAME, checkpoint)
            log.error(f"[{i}/{len(pending)}] {unit.key} failed: {exc}")
            continue

        seen, rows = set(), []
        for article in articles:
            key = article.get("article_id") or article.get("url")
            if key in seen:
                continue
            seen.add(key)
            rows.append(article)
        (run_dir / unit.filename).write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
        )
        done[unit.key] = {"count": len(rows), "file": unit.filename, "finished_at": datetime.now(timezone.utc).isoformat()}
        checkpoint["failed"].pop(unit.key, None)
        _atomic_write_json(run_dir / CHECKPOINT_NAME, checkpoint)
        log.info(f"[{i}/{len(pending)}] {unit.key}: {len(rows)} articles")
        if pause_seconds and i < len(pending):
            time.sleep(pause_seconds)

    return checkpoint


# ── Archive QA ─────────────────────────────────────────────────────────────────

def archive_qa(units: list[Unit], run_dir: Path, skipped: list[dict]) -> dict:
    """Gaps, cross-batch duplicates, and source imbalance for a run directory."""
    checkpoint = load_checkpoint(run_dir)
    done = checkpoint["completed"]
    per_source: dict[str, dict] = defaultdict(lambda: {"articles": 0, "months_complete": 0, "empty_months": [], "pending_months": []})
    first_seen: dict[str, str] = {}
    duplicates = Counter()

    for unit in units:
        row = per_source[unit.source_id]
        state = done.get(unit.key)
        if state is None:
            row["pending_months"].append(unit.month)
            continue
        row["months_complete"] += 1
        row["articles"] += state["count"]
        if state["count"] == 0:
            row["empty_months"].append(unit.month)
        path = run_dir / unit.filename
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            article = json.loads(line)
            key = article.get("url") or article.get("article_id")
            if key in first_seen and first_seen[key] != unit.key:
                duplicates[unit.source_id] += 1
            first_seen.setdefault(key, unit.key)

    total = sum(r["articles"] for r in per_source.values())
    flags = []
    for source_id, row in sorted(per_source.items()):
        share = (row["articles"] / total) if total else 0.0
        row["share"] = round(share, 3)
        row["cross_batch_duplicates"] = duplicates.get(source_id, 0)
        if row["empty_months"]:
            flags.append({"source_id": source_id, "flag": "coverage_gap", "months": row["empty_months"]})
        if total and len(per_source) > 1 and share > IMBALANCE_SHARE:
            flags.append({"source_id": source_id, "flag": "source_imbalance", "share": row["share"]})
        if row["cross_batch_duplicates"]:
            flags.append({"source_id": source_id, "flag": "cross_batch_duplicates", "count": row["cross_batch_duplicates"]})
    for key, failure in sorted(checkpoint.get("failed", {}).items()):
        flags.append({"unit": key, "flag": "connector_error", "error": failure.get("error")})

    pending = sum(len(r["pending_months"]) for r in per_source.values())
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(run_dir),
        "status": "complete" if pending == 0 and not checkpoint.get("failed") else "incomplete",
        "units_total": len(units),
        "units_pending": pending,
        "articles_total": total,
        "sources": dict(sorted(per_source.items())),
        "skipped_sources": skipped,
        "flags": flags,
        "notes": [
            "Connectors log and swallow request errors, so a zero-article month may be a failed request rather than a true gap; re-run with --retry-empty.",
        ],
    }
    _atomic_write_json(run_dir / QA_NAME, report)
    return report


def execute(
    request: HistoricalRequest,
    manifest: dict,
    *,
    connectors: dict[str, Connector],
    base_dir: Path = HISTORICAL_DIR,
    max_units: int | None = None,
    retry_empty: bool = False,
    pause_seconds: float = 0.0,
) -> dict:
    sources, skipped = select_sources(manifest, request, connectors)
    units = build_units(sources, request)
    run_dir = run_dir_for(request, base_dir)
    if request.dry_run:
        return {
            "run_dir": str(run_dir),
            "units": [u.key for u in units],
            "skipped_sources": skipped,
        }
    run_units(
        units, {s["source_id"]: s for s in sources}, connectors, run_dir,
        max_units=max_units, retry_empty=retry_empty, pause_seconds=pause_seconds,
    )
    return archive_qa(units, run_dir, skipped)


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Historical ingestion planner and runner for SENTINEL")
    parser.add_argument("--since", type=validate_date, required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--until", type=validate_date, default=datetime.now(timezone.utc).strftime("%Y-%m-%d"), help="End date YYYY-MM-DD (inclusive)")
    parser.add_argument("--group", action="append", default=[], help="Source-group filter from config/historical_sources.json")
    parser.add_argument("--source", action="append", default=[], help="Source-id filter (repeatable)")
    parser.add_argument("--json", action="store_true", help="Print the plan (or run report) as JSON")
    parser.add_argument("--dry-run", action="store_true", help="With --run: list the units that would execute, without fetching")
    parser.add_argument("--run", action="store_true", help="Execute the ingest (default is planning only)")
    parser.add_argument("--max-units", type=int, default=None, help="Stop after this many (source, month) units")
    parser.add_argument("--retry-empty", action="store_true", help="Re-fetch completed units that returned zero articles")
    parser.add_argument("--pause", type=float, default=2.0, help="Seconds to wait between units (politeness / rate limits)")
    parser.add_argument("--conservative", action="store_true", help="Use GDELT's smaller, slower request profile")
    args = parser.parse_args()

    if args.until < args.since:
        parser.error("--until must be on or after --since")

    manifest = load_manifest()
    request = HistoricalRequest(
        since=args.since,
        until=args.until,
        groups=args.group,
        dry_run=args.dry_run,
        sources=args.source,
    )

    if not args.run:
        plan = build_plan(request, manifest)
        if args.json:
            print(json.dumps(plan, ensure_ascii=False, indent=2))
        else:
            print_summary(plan)
        return

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    report = execute(
        request, manifest,
        connectors=default_connectors(conservative=args.conservative),
        max_units=args.max_units,
        retry_empty=args.retry_empty,
        pause_seconds=args.pause,
    )
    if args.json or request.dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    print(f"Run directory: {report['run_dir']}")
    print(f"Status: {report['status']} ({report['units_total'] - report['units_pending']}/{report['units_total']} units, {report['articles_total']} articles)")
    for flag in report["flags"]:
        print(f"  flag: {json.dumps(flag, ensure_ascii=False)}")
    for skip in report["skipped_sources"]:
        print(f"  skipped {skip['source_id']}: {skip['reason']}")
    print(f"Next: python3 scripts/run_pipeline.py --from-staging {Path(report['run_dir']).relative_to(ROOT)}")


if __name__ == "__main__":
    main()
