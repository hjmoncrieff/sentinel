"""Contract checks on the public-safe layer the dashboard serves (data/published/)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from publish_dashboard_data import PUBLIC_EVENT_FIELDS, is_reviewed_by_human

ROOT = Path(__file__).resolve().parent.parent
PUBLISHED = ROOT / "data" / "published" / "events_public.json"
POLICY = json.loads((ROOT / "config" / "publish_policy.json").read_text(encoding="utf-8"))
TAXONOMY_CODES = {
    row["code"]
    for row in json.loads((ROOT / "config" / "taxonomy" / "event_types.json").read_text(encoding="utf-8"))["event_types"]
}

# Fields added by the publisher beyond the canonical allowlist.
PUBLISHER_FIELDS = {
    "linked_reports", "provenance_summary", "provenance_timeline",
    "public_analysis", "public_risk_level", "public_takeaways",
    "public_classification", "public_ai_generated",
    "content_type", "location_precision", "public_coding",
}
# Internal workflow fields that must never reach the public layer.
PRIVATE_FIELDS = {
    "review_notes", "analyst_reasoning", "reviewed_by", "review_history",
    "qa_resolution_history", "manual_merge", "classification_reason",
}


@pytest.fixture(scope="module")
def events() -> list[dict]:
    if not PUBLISHED.exists():
        pytest.skip("published layer not built")
    return json.loads(PUBLISHED.read_text(encoding="utf-8"))["events"]


def test_only_allowlisted_fields_are_published(events):
    allowed = set(PUBLIC_EVENT_FIELDS) | PUBLISHER_FIELDS
    seen = {key for event in events for key in event}
    assert seen <= allowed, seen - allowed
    assert not seen & PRIVATE_FIELDS


def test_event_ids_unique_and_dates_present(events):
    ids = [e["event_id"] for e in events]
    assert len(ids) == len(set(ids))
    assert all(len(e.get("event_date") or "") == 10 for e in events)


def test_publication_policy_is_enforced(events):
    blocked_review = set(POLICY["withhold_review_statuses"])
    blocked_dupes = set(POLICY["withhold_duplicate_statuses"])
    low = set(POLICY["withhold_confidence_values"])
    for e in events:
        assert e.get("review_status") not in blocked_review
        assert e.get("duplicate_status") not in blocked_dupes
        if e.get("confidence") in low:
            assert is_reviewed_by_human(e)


def test_published_types_are_in_the_taxonomy(events):
    assert {e["event_type"] for e in events} <= TAXONOMY_CODES
