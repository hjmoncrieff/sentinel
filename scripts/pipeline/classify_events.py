#!/usr/bin/env python3
"""
Standalone classification runner for SENTINEL.

This stage reads normalized/filtered article records and produces classified
event candidates before they are merged into the live event store.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import anthropic  # type: ignore  # noqa: E402

from pipeline_core import (  # noqa: E402
    STAGING_DIR,
    classify_articles,
    generate_analysis,
    load_existing,
    log,
)


DEFAULT_INPUT = STAGING_DIR / "filtered_articles.json"
DEFAULT_OUTPUT = STAGING_DIR / "classified_events.json"


def load_articles(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload.get("articles", [])
    if isinstance(payload, list):
        return payload
    raise ValueError(f"Unsupported article payload in {path}")


def write_events(path: Path, events: list[dict], source_path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_path": str(source_path.relative_to(ROOT)),
                "count": len(events),
                "events": events,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SENTINEL classification stage on filtered article records")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Filtered article JSON input")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Classified event output JSON")
    parser.add_argument("--skip-analysis", action="store_true", help="Skip high-salience AI analysis generation")
    args = parser.parse_args()

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set.")
    if not args.input.exists():
        raise FileNotFoundError(f"Input file does not exist: {args.input}")

    client = anthropic.Anthropic(api_key=anthropic_key)
    existing = load_existing()
    existing_ids = set(existing.keys())
    articles = load_articles(args.input)
    log.info(f"Classification stage: {len(articles)} filtered articles loaded from {args.input}")

    events = classify_articles(client, articles, existing_ids)
    if not args.skip_analysis:
        high_new = [ev for ev in events if ev["id"] not in existing_ids and ev.get("salience") == "high"]
        log.info(f"Classification stage: generating analysis for {len(high_new)} high-salience new events")
        for event in high_new:
            event["ai_analysis"] = generate_analysis(client, event)
            time.sleep(0.5)

    write_events(args.output, events, args.input)
    log.info(f"Classification stage output written to {args.output}")


if __name__ == "__main__":
    main()
