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
