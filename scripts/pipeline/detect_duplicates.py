#!/usr/bin/env python3
"""
SENTINEL duplicate candidate detector.

Reads data/events.json and writes data/review/duplicate_candidates.json.
This is the deterministic first-pass duplicate layer.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
EVENTS_PATH = ROOT / "data" / "events.json"
OUT_PATH = ROOT / "data" / "review" / "duplicate_candidates.json"


def load_events() -> list[dict]:
    raw = json.loads(EVENTS_PATH.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        return raw.get("events", [])
    return raw


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def normalize_title(title: str | None) -> str:
    if not title:
        return ""
    value = title.lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def classify_pair(left: dict, right: dict) -> dict | None:
    if left.get("id") == right.get("id"):
        return None
    if left.get("country") != right.get("country"):
        return None

    d1 = parse_date(left.get("date"))
    d2 = parse_date(right.get("date"))
    if not d1 or not d2:
        return None

    day_gap = abs((d1 - d2).days)
    if day_gap > 7:
        return None

    left_title = normalize_title(left.get("title"))
    right_title = normalize_title(right.get("title"))
    title_score = similarity(left_title, right_title)

    left_urls = set(left.get("links") or ([left.get("url")] if left.get("url") else []))
    right_urls = set(right.get("links") or ([right.get("url")] if right.get("url") else []))
    shared_url = bool(left_urls & right_urls)

    same_type = left.get("type") == right.get("type")
    same_actor = bool(left.get("actor")) and left.get("actor") == right.get("actor")
    same_target = bool(left.get("target")) and left.get("target") == right.get("target")

    if shared_url:
        status = "definite_duplicate"
        reason = "Records share at least one source URL."
        score = 1.0
    elif title_score >= 0.92 and day_gap <= 3 and same_type:
        status = "definite_duplicate"
        reason = "Titles are near-identical within a short time window and event type matches."
        score = round(title_score, 3)
    elif title_score >= 0.82 and day_gap <= 4 and (same_type or same_actor or same_target):
        status = "possible_duplicate"
        reason = "Titles are highly similar and key event fields overlap."
        score = round(title_score, 3)
    else:
        return None

    candidate_key = "|".join(sorted([left["id"], right["id"]]))
    candidate_id = hashlib.sha1(candidate_key.encode("utf-8")).hexdigest()[:12]
    return {
        "candidate_id": candidate_id,
        "event_ids": sorted([left["id"], right["id"]]),
        "status": status,
        "reason": reason,
        "score": score,
        "details": {
          "country": left.get("country"),
          "day_gap": day_gap,
          "title_score": round(title_score, 3),
          "left_title": left.get("title"),
          "right_title": right.get("title"),
          "same_type": same_type,
          "same_actor": same_actor,
          "same_target": same_target
        }
    }


def main() -> None:
    events = load_events()
    candidates: list[dict] = []

    for idx, left in enumerate(events):
        for right in events[idx + 1:]:
            candidate = classify_pair(left, right)
            if candidate:
                candidates.append(candidate)

    candidates.sort(key=lambda item: (item["status"], -item["score"], item["candidate_id"]))

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_file": str(EVENTS_PATH.relative_to(ROOT)),
        "event_count": len(events),
        "candidate_count": len(candidates),
        "candidates": candidates,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote duplicate candidates to {OUT_PATH}")
    print(f"Events checked: {len(events)}")
    print(f"Candidates found: {len(candidates)}")


if __name__ == "__main__":
    main()
