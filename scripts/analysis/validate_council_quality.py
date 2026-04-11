#!/usr/bin/env python3
"""
LLM-as-judge validation for council synthesis quality.

For every event that has an llm_synthesis block in council_analyses.json,
call Claude Haiku to score the synthesis on three dimensions:

  1. Specificity  — names actors, institutions, concrete actions (not generic claims)
  2. Grounding    — tied to the specific event content, not free-floating theory
  3. Calibration  — appropriate uncertainty without over-hedging or over-confidence

Scores: 1 (poor) – 5 (excellent) per dimension.
Events scoring below REVIEW_THRESHOLD on any dimension are flagged for analyst review.

Outputs:
  data/review/council_quality_scores.json

Usage:
  python scripts/analysis/validate_council_quality.py          # score new entries only
  python scripts/analysis/validate_council_quality.py --force  # re-score everything
  python scripts/analysis/validate_council_quality.py --country "Venezuela"
  python scripts/analysis/validate_council_quality.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
COUNCIL_PATH  = ROOT / "data" / "review" / "council_analyses.json"
QUALITY_PATH  = ROOT / "data" / "review" / "council_quality_scores.json"

JUDGE_MODEL     = "claude-haiku-4-5-20251001"
MAX_TOKENS      = 300
INTER_CALL_SLEEP = 0.25
RETRY_SLEEP      = 5.0
REVIEW_THRESHOLD = 3          # flag any dimension scoring ≤ this
HIGH_SCORE       = 4          # composite ≥ this considered good


JUDGE_SYSTEM = """\
You are a quality-control reviewer for an intelligence analysis platform.
You evaluate written analytical syntheses on three dimensions.
Respond ONLY with a JSON object — no markdown, no explanation outside the JSON.\
"""

JUDGE_PROMPT_TEMPLATE = """\
## Event Context
Country: {country}
Type: {event_type} | Salience: {salience} | Date: {event_date}
Headline: {headline}
Summary: {summary}

## Synthesis to Evaluate
{synthesis_text}

## Watchpoint
{watchpoint}

## Scoring Task
Score this synthesis on three dimensions from 1 (poor) to 5 (excellent):

1. **Specificity** — Does the synthesis name specific actors, institutions, locations, or mechanisms?
   - 1 = entirely generic claims ("tensions may escalate", "the military plays a role")
   - 5 = names concrete actors, institutions, actions, and mechanisms relevant to this event

2. **Grounding** — Is the analysis tied to the actual event described above, or is it free-floating theory?
   - 1 = could have been written without reading the event at all
   - 5 = clearly derived from the specific event content; references headline/context details

3. **Calibration** — Does it express appropriate uncertainty without over-hedging or over-confidence?
   - 1 = either wildly overconfident ("this will cause a coup") or paralysed by hedges ("it is possible that perhaps…")
   - 5 = makes clear analytical claims while acknowledging the limits of available evidence

Also list up to 3 brief flags (specific phrases or issues you noticed, or leave empty if none).

Respond with exactly this JSON (no other text):
{{"specificity": N, "grounding": N, "calibration": N, "flags": ["...", "..."]}}\
"""


def load_existing_scores() -> dict[str, dict]:
    """Return existing score records keyed by event_id."""
    if not QUALITY_PATH.exists():
        return {}
    payload = json.loads(QUALITY_PATH.read_text(encoding="utf-8"))
    return {row["event_id"]: row for row in payload.get("events", []) if row.get("event_id")}


def build_judge_prompt(entry: dict) -> str:
    """Build the per-event judge prompt from a council_analyses entry."""
    analyses     = entry.get("analyses") or {}
    llm_syn      = analyses.get("llm_synthesis") or {}
    ctx          = entry.get("event_context") or {}
    synthesis_text = (llm_syn.get("synthesis") or "").strip()
    watchpoint     = (llm_syn.get("watchpoint") or "").strip()

    return JUDGE_PROMPT_TEMPLATE.format(
        country       = entry.get("country", ""),
        event_type    = entry.get("event_type", ""),
        salience      = entry.get("salience", ""),
        event_date    = entry.get("event_date", ""),
        headline      = ctx.get("primary_headline", ""),
        summary       = ctx.get("primary_context", ""),
        synthesis_text = synthesis_text or "(no synthesis text)",
        watchpoint     = watchpoint or "(none)",
    )


def call_judge(
    client: "anthropic.Anthropic",
    prompt: str,
    event_id: str,
) -> dict:
    """Call Haiku as LLM-as-judge. Returns parsed scores dict or error."""
    for attempt in range(3):
        try:
            response = client.messages.create(
                model=JUDGE_MODEL,
                max_tokens=MAX_TOKENS,
                system=JUDGE_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
            raw = re.sub(r"\s*```$", "", raw)
            parsed = json.loads(raw)

            specificity  = int(parsed.get("specificity", 0))
            grounding    = int(parsed.get("grounding", 0))
            calibration  = int(parsed.get("calibration", 0))
            flags        = [str(f) for f in (parsed.get("flags") or []) if f]

            composite = round((specificity + grounding + calibration) / 3, 2)
            needs_review = any(
                s <= REVIEW_THRESHOLD
                for s in (specificity, grounding, calibration)
            )

            return {
                "ok": True,
                "specificity":  specificity,
                "grounding":    grounding,
                "calibration":  calibration,
                "composite":    composite,
                "flags":        flags[:3],
                "needs_review": needs_review,
                "quality_band": (
                    "good"     if composite >= HIGH_SCORE else
                    "marginal" if composite >= 3.0       else
                    "poor"
                ),
                "scored_at":  datetime.now(UTC).isoformat(),
                "judge_model": JUDGE_MODEL,
            }

        except json.JSONDecodeError as exc:
            return {
                "ok": False,
                "error": f"JSON parse error: {exc}",
                "scored_at": datetime.now(UTC).isoformat(),
                "judge_model": JUDGE_MODEL,
            }
        except Exception as exc:
            err_str = str(exc)
            if "rate_limit" in err_str.lower() or "529" in err_str or "overloaded" in err_str.lower():
                wait = RETRY_SLEEP * (attempt + 1)
                print(f"  Rate-limit on attempt {attempt + 1}, waiting {wait}s …")
                time.sleep(wait)
                continue
            return {
                "ok": False,
                "error": err_str,
                "scored_at": datetime.now(UTC).isoformat(),
                "judge_model": JUDGE_MODEL,
            }
    return {
        "ok": False,
        "error": "max retries exceeded",
        "scored_at": datetime.now(UTC).isoformat(),
        "judge_model": JUDGE_MODEL,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Score council syntheses with Haiku LLM-as-judge.")
    parser.add_argument("--force",   action="store_true", help="Re-score even if already scored")
    parser.add_argument("--dry-run", action="store_true", help="Print stats only, no API calls")
    parser.add_argument("--country", metavar="NAME", help="Restrict to one country")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and not args.dry_run:
        print("ERROR: ANTHROPIC_API_KEY not set.")
        raise SystemExit(1)

    if not COUNCIL_PATH.exists():
        print(f"Council analyses not found at {COUNCIL_PATH}.")
        raise SystemExit(1)

    print("Loading council analyses …")
    payload = json.loads(COUNCIL_PATH.read_text(encoding="utf-8"))
    entries = payload.get("events", [])

    existing_scores = load_existing_scores()

    # Identify events to score: must have llm_synthesis and synthesis text
    candidates = []
    for entry in entries:
        analyses = entry.get("analyses") or {}
        llm_syn  = analyses.get("llm_synthesis") or {}
        if not llm_syn.get("synthesis"):
            continue
        if not llm_syn.get("ok", True) and llm_syn.get("error"):
            continue  # skip failed synthesis attempts
        event_id = entry.get("event_id", "")
        if not args.force and event_id in existing_scores:
            continue
        if args.country and entry.get("country") != args.country:
            continue
        candidates.append(entry)

    total_with_llm   = sum(1 for e in entries if (e.get("analyses") or {}).get("llm_synthesis", {}).get("synthesis"))
    already_scored   = len(existing_scores)
    to_score         = len(candidates)

    print(f"Events with LLM synthesis:    {total_with_llm}")
    print(f"Already scored (skipping):    {already_scored if not args.force else 0}")
    print(f"To score now:                 {to_score}")

    if args.dry_run:
        print("Dry run — exiting.")
        return

    if not candidates:
        print("Nothing to score. Exiting.")
        # Still write the output file if it doesn't exist
        if not QUALITY_PATH.exists() and existing_scores:
            _write_output(existing_scores, total_with_llm)
        return

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    new_scores: dict[str, dict] = {}
    errors = 0
    needs_review_count = 0

    for i, entry in enumerate(candidates):
        event_id   = entry.get("event_id", "?")
        country    = entry.get("country", "")
        salience   = entry.get("salience", "")
        event_date = entry.get("event_date", "")
        print(f"[{i+1}/{to_score}] {event_id} {country} ({salience}, {event_date})", end=" … ", flush=True)

        prompt = build_judge_prompt(entry)
        result = call_judge(client, prompt, event_id)

        score_row: dict = {
            "event_id":   event_id,
            "country":    country,
            "salience":   salience,
            "event_date": event_date,
            "event_type": entry.get("event_type", ""),
        }

        if result["ok"]:
            score_row.update({
                "specificity":   result["specificity"],
                "grounding":     result["grounding"],
                "calibration":   result["calibration"],
                "composite":     result["composite"],
                "flags":         result["flags"],
                "needs_review":  result["needs_review"],
                "quality_band":  result["quality_band"],
                "scored_at":     result["scored_at"],
                "judge_model":   result["judge_model"],
                "error":         None,
            })
            band = result["quality_band"]
            nr   = "⚑ REVIEW" if result["needs_review"] else ""
            print(f"✓ composite={result['composite']} [{band}] {nr}")
            if result["needs_review"]:
                needs_review_count += 1
        else:
            errors += 1
            score_row.update({
                "error":        result.get("error"),
                "needs_review": True,
                "quality_band": "error",
                "scored_at":    result["scored_at"],
                "judge_model":  result["judge_model"],
            })
            print(f"✗ {result.get('error', 'unknown')}")

        new_scores[event_id] = score_row

        if INTER_CALL_SLEEP > 0:
            time.sleep(INTER_CALL_SLEEP)

    # Merge with existing scores
    merged = {**existing_scores, **new_scores}
    _write_output(merged, total_with_llm)

    print(f"\n✓ Wrote {QUALITY_PATH}")
    print(f"  Scored: {to_score}  Errors: {errors}  Needs review: {needs_review_count}")

    # Summary by quality band
    bands: dict[str, int] = {}
    for row in merged.values():
        b = str(row.get("quality_band") or "unknown")
        bands[b] = bands.get(b, 0) + 1
    print("  Quality bands:", "  ".join(f"{b}={n}" for b, n in sorted(bands.items())))


def _write_output(scores_by_id: dict[str, dict], total_with_llm: int) -> None:
    events_list = sorted(scores_by_id.values(), key=lambda r: r.get("event_date") or "")
    good_count  = sum(1 for r in events_list if r.get("quality_band") == "good")
    review_count = sum(1 for r in events_list if r.get("needs_review"))
    payload = {
        "generated_at":       datetime.now(UTC).isoformat(),
        "judge_model":        JUDGE_MODEL,
        "review_threshold":   REVIEW_THRESHOLD,
        "events_with_llm_synthesis": total_with_llm,
        "events_scored":      len(events_list),
        "needs_review_count": review_count,
        "good_count":         good_count,
        "events":             events_list,
    }
    QUALITY_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUALITY_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
