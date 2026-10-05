#!/usr/bin/env python3
"""
Keep the public site's country reference current.

For each selected country, Claude researches the current officeholders, service
commanders and elections with web search and records them, each with a source
URL. The result is merged into apps/public-site/reference/countries.json and
every change is appended to apps/public-site/reference/changes.json.

Which countries are refreshed:
  --countries "Colombia,Peru"   exactly these
  --all                         every country
  --triggered                   countries whose recent published events signal a
                                change of government, cabinet or command
  --stale-days N                countries not refreshed in N days (oldest first)
--triggered and --stale-days combine; --max-countries caps one run's cost.

The nightly workflow runs `--triggered --stale-days 30 --max-countries 3`, so a
change in the news is picked up the same night and every entry is re-checked at
least monthly.

What is and is not overwritten:
  - officials, head of government, elections, the summary note and the watch
    note are replaced with the researched, sourced values;
  - a post the research could not confirm keeps no name (never a guess, never
    the old value carried over) and is shown as unconfirmed;
  - cmr_status / cmr_class, military roles and in-depth monitor content are
    analytical judgements and are never touched;
  - a country whose entry has "locked": true is skipped (an analyst owns it).

Usage:
  python3 scripts/reference/refresh_country_reference.py --countries Colombia [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from prompt_library import model_for, render_prompt  # noqa: E402

REFERENCE = ROOT / "apps" / "public-site" / "reference" / "countries.json"
CHANGES = ROOT / "apps" / "public-site" / "reference" / "changes.json"
PUBLISHED = ROOT / "data" / "published" / "events_public.json"

MAX_SEARCHES = 10
MAX_TOKENS = 8000
MAX_CONTINUATIONS = 4
TRIGGER_WINDOW_DAYS = 7
TRIGGER_COOLDOWN_DAYS = 5   # an event does not re-trigger a country refreshed this recently
# Headlines and summaries that suggest the people in the reference file may have changed.
TRIGGER = re.compile(
    r"inaugurat|sworn in|swears in|takes office|president-elect|wins? (the )?(presidential|runoff|election)|"
    r"toma de posesi[óo]n|investidura|presidente elect[oa]|asume (la presidencia|como (presidente|ministr|comandante))|"
    r"new (defen[cs]e minister|army chief|armed forces chief|military command|cabinet)|cabinet reshuffle|"
    r"(defen[cs]e minister|army chief|commander|police chief)[^.]{0,40}(resign|dismiss|sack|replac|fired)|"
    r"nuev[oa] (ministr[oa] de defensa|comandante|c[úu]pula)|c[úu]pula militar|"
    r"(ministr[oa] de defensa|comandante)[^.]{0,40}(renunci|destitu|relev|remoci)|"
    r"novo (ministro da defesa|comandante)|toma posse|empossad",
    re.IGNORECASE,
)
TRIGGER_TYPES = {"coup", "purge"}

# Strict tool schemas allow few nullable fields, so "unknown" is an empty string here;
# merge() turns empty strings back into None.
_TEXT = {"type": "string"}
PERSON = {
    "type": "object",
    "properties": {
        "post": {"type": "string", "enum": ["head_of_state", "head_of_government", "vice_president", "defence_minister",
                                            "armed_forces_chief", "army_commander", "navy_commander", "air_force_commander", "police_chief"]},
        "name": {"type": "string", "description": "Full name, or an empty string if not confirmed"},
        "title": {"type": "string", "description": "The post's own title in English, e.g. 'President', 'Minister of National Defence'"},
        "since": {"type": "string", "description": "YYYY-MM or YYYY, or an empty string"},
        "source_url": {"type": "string", "description": "Page supporting the entry, or an empty string"},
        "note": {"type": "string", "description": "Why unconfirmed, vacant or not applicable; otherwise an empty string"},
    },
    "required": ["post", "name", "title", "since", "source_url", "note"],
    "additionalProperties": False,
}
ELECTION = {
    "type": "object",
    "properties": {"type": _TEXT, "date": _TEXT, "note": _TEXT, "source_url": _TEXT},
    "required": ["type", "date", "note", "source_url"],
    "additionalProperties": False,
}
RECORD_TOOL = {
    "name": "record_reference",
    "description": "Record the researched reference data for the country. Call exactly once, after research.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "officials": {"type": "array", "items": PERSON, "description": "One entry per post that exists in this country"},
            "next_election": ELECTION,
            "last_election": ELECTION,
            "summary_note": {"type": "string"},
            "watch_note": {"type": "string"},
            "changes": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["officials", "next_election", "last_election", "summary_note", "watch_note", "changes"],
        "additionalProperties": False,
    },
}
POSTS = ["head_of_state", "head_of_government", "vice_president", "defence_minister", "armed_forces_chief",
         "army_commander", "navy_commander", "air_force_commander", "police_chief"]


def load_events() -> list[dict]:
    if not PUBLISHED.exists():
        return []
    return json.loads(PUBLISHED.read_text(encoding="utf-8")).get("events", [])


def recent_events_text(events: list[dict], country: str, limit: int = 15) -> str:
    rows = sorted((e for e in events if e.get("country") == country), key=lambda e: e.get("event_date") or "", reverse=True)[:limit]
    return "\n".join(f"- {e.get('event_date')}: {e.get('headline')}" for e in rows) or "(none)"


def triggered_countries(events: list[dict], today: date, window: int = TRIGGER_WINDOW_DAYS) -> dict[str, str]:
    """Country → the headline that suggests its reference data may have changed."""
    cutoff = (today - timedelta(days=window)).isoformat()
    hits: dict[str, str] = {}
    for e in sorted(events, key=lambda e: e.get("event_date") or "", reverse=True):
        if (e.get("event_date") or "") < cutoff or e.get("country") in hits:
            continue
        text = f"{e.get('headline') or ''} {e.get('summary') or ''}"
        if e.get("event_type") in TRIGGER_TYPES or TRIGGER.search(text):
            hits[e["country"]] = e.get("headline") or ""
    return hits


def select(countries: list[dict], args, events: list[dict], today: date) -> list[tuple[dict, str]]:
    by_name = {c["name"]: c for c in countries}
    picked: dict[str, str] = {}
    if args.countries:
        for name in (n.strip() for n in args.countries.split(",")):
            if name not in by_name:
                raise SystemExit(f"Unknown country: {name}")
            picked[name] = "requested"
    if args.all:
        picked.update({c["name"]: "full refresh" for c in countries})
    if args.triggered:
        recent = (today - timedelta(days=TRIGGER_COOLDOWN_DAYS)).isoformat()
        for name, headline in triggered_countries(events, today).items():
            if name in by_name and (by_name[name].get("auto_updated") or "") < recent:
                picked.setdefault(name, f"event: {headline[:90]}")
    if args.stale_days is not None:
        cutoff = (today - timedelta(days=args.stale_days)).isoformat()
        stale = sorted((c for c in countries if (c.get("auto_updated") or "") < cutoff), key=lambda c: c.get("auto_updated") or "")
        for c in stale:
            picked.setdefault(c["name"], f"not refreshed since {c.get('auto_updated') or 'ever'}")
    rows = [(by_name[n], why) for n, why in picked.items() if not by_name[n].get("locked")]
    return rows[: args.max_countries] if args.max_countries else rows


def research(client, country: dict, events: list[dict], today: date) -> tuple[dict | None, dict]:
    """One researched record for a country, plus token and search usage."""
    current = {k: country.get(k) for k in ("head_of_government", "regime", "officials", "positions", "election", "note", "watch")}
    prompt = render_prompt(
        "reference_refresh", today=today.isoformat(), country=country["name"],
        current=json.dumps(current, ensure_ascii=False, indent=1), recent_events=recent_events_text(events, country["name"]),
    )
    messages = [{"role": "user", "content": prompt}]
    usage = {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0, "searches": 0, "requests": 0}
    for _ in range(MAX_CONTINUATIONS + 1):
        response = client.messages.create(
            model=model_for("reference_refresh"),
            max_tokens=MAX_TOKENS,
            tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": MAX_SEARCHES}, RECORD_TOOL],
            output_config={"effort": "medium"},
            messages=messages,
        )
        usage["requests"] += 1
        for key in ("input_tokens", "output_tokens", "cache_read_input_tokens"):
            usage[key] += getattr(response.usage, key, 0) or 0
        server = getattr(response.usage, "server_tool_use", None)
        usage["searches"] += getattr(server, "web_search_requests", 0) or 0
        if response.stop_reason == "refusal":
            return None, usage
        for block in response.content:
            if block.type == "tool_use" and block.name == "record_reference":
                return block.input, usage
        if response.stop_reason == "pause_turn":
            # The server-side search loop paused; resend with the partial turn to resume it.
            messages = [messages[0], {"role": "assistant", "content": response.content}]
            continue
        # Ended without recording: ask once more for the tool call.
        messages = [messages[0], {"role": "assistant", "content": response.content},
                    {"role": "user", "content": "Call record_reference now with what you established. Use an empty string for anything unconfirmed."}]
    return None, usage


def _official(post: str, person: dict | None) -> dict | None:
    if not person or not (person.get("title") or person.get("name")):
        return None
    return {"post": post, "title": person.get("title") or post.replace("_", " ").title(), "name": person.get("name") or None,
            "since": person.get("since") or None, "source_url": person.get("source_url") or None, "note": person.get("note") or None}


def merge(country: dict, record: dict, today: date, model: str) -> list[str]:
    """Apply a researched record to a country entry in place. Returns a list of what changed."""
    before = {o["post"]: o.get("name") for o in country.get("officials") or []}
    old_hog = country.get("head_of_government")
    by_post = {p.get("post"): p for p in record.get("officials") or []}
    officials = [o for o in (_official(post, by_post.get(post)) for post in POSTS) if o]
    # A head of government who is the head of state is listed once.
    state = next((o for o in officials if o["post"] == "head_of_state"), None)
    officials = [o for o in officials if not (o["post"] == "head_of_government" and (not o["name"] or (state and o["name"] == state["name"])))]
    # A name without a source is not publishable: keep the post, drop the name.
    for o in officials:
        if o["name"] and not o["source_url"]:
            o["note"], o["name"] = (o.get("note") or "No source found for this name."), None
    changed = []
    for o in officials:
        if o["post"] in before and before[o["post"]] != o["name"]:
            changed.append(f"{o['title']}: {before[o['post']] or 'unconfirmed'} → {o['name'] or 'unconfirmed'}")
    country["officials"] = officials
    leader = (by_post.get("head_of_government") or {}).get("name") or (by_post.get("head_of_state") or {}).get("name")
    if leader:
        if old_hog and old_hog != leader and not before:
            changed.append(f"Head of government: {old_hog} → {leader}")
        country["head_of_government"] = leader
    # The older dashboard format, kept so both sites read the same people.
    country["positions"] = [{"t": o["title"], "n": o["name"]} for o in officials if o["name"]]
    for key, field in (("next_election", "election"), ("last_election", "last_election")):
        value = {k: (v or None) for k, v in (record.get(key) or {}).items()}
        if value.get("type") or value.get("date"):
            if key == "next_election" and (country.get("election") or {}).get("date") != value.get("date"):
                changed.append(f"Next election: {(country.get('election') or {}).get('date') or '—'} → {value.get('date')}")
            country[field] = value
    if record.get("summary_note"):
        country["note"] = record["summary_note"]
    if record.get("watch_note"):
        country["watch"] = record["watch_note"]
    country["auto_updated"] = today.isoformat()
    country["auto_model"] = model
    return changed + [c for c in record.get("changes") or [] if c not in changed]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--countries")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--triggered", action="store_true")
    parser.add_argument("--stale-days", type=int, default=None)
    parser.add_argument("--max-countries", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true", help="List the countries that would be refreshed and why; no API calls")
    args = parser.parse_args()

    today = datetime.now(UTC).date()
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
    events = load_events()
    rows = select(reference["countries"], args, events, today)
    for country, why in rows:
        print(f"{country['name']}: {why}")
    if args.dry_run or not rows:
        print(f"{len(rows)} countries selected." + (" Dry run; nothing changed." if args.dry_run else ""))
        return
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ERROR: ANTHROPIC_API_KEY not set.")

    import anthropic
    client = anthropic.Anthropic()
    model = model_for("reference_refresh")
    log = json.loads(CHANGES.read_text(encoding="utf-8")) if CHANGES.exists() else {"changes": []}
    totals = {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0, "searches": 0, "requests": 0}
    done = failed = 0
    for country, why in rows:
        try:
            record, usage = research(client, country, events, today)
        except anthropic.APIError as exc:
            print(f"  {country['name']}: API error ({type(exc).__name__}: {str(exc)[:300]}); left unchanged")
            failed += 1
            if "credit balance" in str(exc).lower() or isinstance(exc, anthropic.AuthenticationError):
                print("Stopping: the API account cannot be used (billing or authentication).")
                break
            continue
        for key in totals:
            totals[key] += usage[key]
        if not record:
            print(f"  {country['name']}: no record returned; left unchanged")
            failed += 1
            continue
        changes = merge(country, record, today, model)
        confirmed = sum(1 for o in country["officials"] if o["name"])
        print(f"  {country['name']}: {confirmed}/{len(country['officials'])} posts confirmed, {usage['searches']} searches"
              + (f"; changes: {'; '.join(changes)}" if changes else "; no changes"))
        log["changes"].append({"date": today.isoformat(), "country": country["name"], "trigger": why, "model": model, "changes": changes})
        done += 1
        # Save after each country so an interrupted run keeps its work.
        REFERENCE.write_text(json.dumps(reference, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        CHANGES.write_text(json.dumps(log, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Refreshed {done} countries, {failed} failed. Usage: {json.dumps(totals)}")


if __name__ == "__main__":
    main()
