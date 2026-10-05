import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import codebook
import recode_archive_v3 as ra


def _event(**over):
    base = {"id": "abc123", "sentinel_id": "PER_2026_03_abc123", "type": "other", "subtype": None, "title": "Army chief dismissed",
            "summary": "old summary", "country": "Peru", "date": "2026-03-02", "conf": "yellow", "salience": "high",
            "url": "https://example.org/a", "linked_reports": [{"url": "https://example.org/a", "source_method": "rss"}]}
    return {**base, **over}


ITEM = {"relevant": True, "content_type": "event", "type": "purge", "subtype": None, "country": "Chile", "salience": "medium",
        "certainty": "high", "deed_type": "not_applicable", "axis": "not_applicable", "actors": [], "summary": "New summary."}


def test_recode_keeps_identity_and_the_old_coding():
    event = _event()
    assert ra.recode_event(event, ITEM, "claude-sonnet-5-5", "2026-10-05T00:00:00+00:00") == "recoded"
    assert (event["id"], event["sentinel_id"], event["title"], event["date"]) == ("abc123", "PER_2026_03_abc123", "Army chief dismissed", "2026-03-02")
    assert event["v2"]["type"] == "other" and event["v2"]["salience"] == "high" and event["v2"]["summary"] == "old summary"
    assert event["type"] == codebook.legacy_family("purge", None)[0]
    assert event["salience"] == "medium" and event["conf"] == "green" and event["summary"] == "New summary."
    assert event["country"] == "Peru"  # the citable id encodes the country, so it is not overwritten
    assert event["v3"]["country"] == "Chile" and event["v3"]["coded_by"] == "claude-sonnet-5-5"


def test_regional_events_take_the_coded_country():
    event = _event(country="Regional")
    ra.recode_event(event, ITEM, "claude-sonnet-5-5", "now")
    assert event["country"] == "Chile"


def test_out_of_scope_events_are_flagged_not_deleted():
    event = _event()
    assert ra.recode_event(event, {"relevant": False, "content_type": "relevance"}, "claude-sonnet-5-5", "now") == "out_of_scope"
    assert event["type"] == "other" and event["salience"] == "low" and event["v3_review"] == "judged_out_of_scope"


def test_protected_events_are_skipped():
    assert ra.skip_reason(_event(), {"abc123"}) == "analyst_edited"
    assert ra.skip_reason(_event(linked_reports=[{"url": "https://x.org", "source_method": "manual_web_audit"}]), set()) == "hand_curated"
    assert ra.skip_reason(_event(url="#", linked_reports=[]), set()) == "no_report_url"
    assert ra.skip_reason(_event(v3={"type": "purge"}), set()) == "already_v3"
    assert ra.skip_reason(_event(), set()) is None


def test_reference_refresh_selection_and_merge():
    import argparse
    from datetime import date

    sys.path.insert(0, str(ROOT / "scripts" / "reference"))
    import refresh_country_reference as rr

    today = date(2026, 10, 5)
    events = [
        {"country": "Colombia", "event_date": "2026-10-03", "headline": "De la Espriella sworn in as president", "event_type": "other"},
        {"country": "Peru", "event_date": "2026-10-03", "headline": "Police seize cocaine shipment in Callao", "event_type": "oc"},
        {"country": "Chile", "event_date": "2026-08-01", "headline": "New defence minister sworn in", "event_type": "other"},  # too old
        {"country": "Haiti", "event_date": "2026-10-02", "headline": "Officers arrested over plot", "event_type": "coup"},
    ]
    assert set(rr.triggered_countries(events, today)) == {"Colombia", "Haiti"}

    countries = [{"name": "Colombia", "auto_updated": "2026-10-04"}, {"name": "Haiti"}, {"name": "Peru", "auto_updated": "2026-08-01"},
                 {"name": "Chile", "auto_updated": "2026-10-01", "locked": True}]
    args = argparse.Namespace(countries=None, all=False, triggered=True, stale_days=30, max_countries=0)
    picked = [c["name"] for c, _ in rr.select(countries, args, events, today)]
    assert picked == ["Haiti", "Peru"]  # Colombia is in its cool-down; Chile is locked

    country = {"name": "Colombia", "head_of_government": "Gustavo Petro", "election": {"date": "Mar/May 2026"}, "cmr_status": "Complex", "note": "old"}
    record = {"officials": [
        {"post": "head_of_state", "name": "Abelardo de la Espriella", "title": "President", "since": "2026-08", "source_url": "https://example.org/a", "note": ""},
        {"post": "defence_minister", "name": "Unsourced Name", "title": "Minister of Defence", "since": "", "source_url": "", "note": ""},
        {"post": "navy_commander", "name": "", "title": "Commander of the Navy", "since": "", "source_url": "", "note": "Not confirmed."},
    ], "next_election": {"type": "Presidential", "date": "2030-05", "note": "", "source_url": "https://example.org/e"},
        "last_election": {"type": "", "date": "", "note": "", "source_url": ""}, "summary_note": "New note.", "watch_note": "Watch.", "changes": []}
    changes = rr.merge(country, record, today, "claude-sonnet-5-5")
    by_post = {o["post"]: o for o in country["officials"]}
    assert country["head_of_government"] == "Abelardo de la Espriella" and country["auto_updated"] == "2026-10-05"
    assert by_post["defence_minister"]["name"] is None  # a name without a source is never published
    assert by_post["navy_commander"]["name"] is None and by_post["navy_commander"]["note"] == "Not confirmed."
    assert country["positions"] == [{"t": "President", "n": "Abelardo de la Espriella"}]
    assert country["cmr_status"] == "Complex" and country["note"] == "New note." and "last_election" not in country
    assert any("Gustavo Petro → Abelardo de la Espriella" in c for c in changes) and any("2030-05" in c for c in changes)
