from __future__ import annotations

import json
from pathlib import Path

import build_gold_layer as gold

ROOT = Path(__file__).resolve().parent.parent
POLICY = json.loads((ROOT / "config" / "gold_policy.json").read_text(encoding="utf-8"))


def _event(event_id: str, **fields) -> dict:
    return {"event_id": event_id, "event_date": "2026-01-01", "event_type": "purge", **fields}


def test_select_gold_events_tiers_and_exclusions():
    events = [
        _event("a", review_status="coordinator_approved"),
        _event("b", review_status="analyst_reviewed"),
        _event("c", review_status="auto", human_validated=True),
        _event("d", review_status="auto"),
        _event("e", review_status="rejected"),
        _event("f", review_status="analyst_reviewed", merged_into_event_id="b"),
        _event("g", review_status="analyst_reviewed", review_history=[{"warnings": ["Role 'ra' cannot edit"]}]),
    ]
    accepted, negatives, excluded = gold.select_gold_events(events, POLICY)
    assert [row["event_id"] for row in accepted] == ["a", "b", "c"]
    assert [row["gold_tier"] for row in accepted] == ["coordinator_approved", "analyst_reviewed", "human_validated"]
    assert [row["event_id"] for row in negatives] == ["e"]
    assert excluded == {"merged_away": 1, "edit_warnings": 1}


def test_corrections_keep_latest_qualifying_change_only():
    machine = {"x": {"event_id": "x", "event_type": "other", "salience": "low", "summary": "m"}}
    edits = [
        {"edit_id": "1", "event_id": "x", "editor_role": "analyst", "edited_at": "2026-01-01", "patch": {"event_type": "purge"}},
        {"edit_id": "2", "event_id": "x", "editor_role": "coordinator", "edited_at": "2026-01-02", "patch": {"event_type": "coup_proofing"}},
        {"edit_id": "3", "event_id": "x", "editor_role": "ra", "edited_at": "2026-01-03", "patch": {"summary": "ra rewrite"}},
        {"edit_id": "4", "event_id": "x", "editor_role": "analyst", "edited_at": "2026-01-04", "patch": {"salience": "low"}},
        {"edit_id": "5", "event_id": "x", "editor_role": "analyst", "edited_at": "2026-01-05", "status": "discarded", "patch": {"salience": "high"}},
        {"edit_id": "6", "event_id": "missing", "editor_role": "analyst", "patch": {"event_type": "coup"}},
    ]
    rows = gold.extract_corrections(edits, machine, POLICY)
    assert rows == [{
        "event_id": "x", "field": "event_type", "machine_value": "other", "human_value": "coup_proofing",
        "editor_role": "coordinator", "edited_at": "2026-01-02", "edit_id": "2", "comment": None,
    }]


def test_decision_extractors_skip_drafts_undone_and_template_rows():
    dupes = gold.extract_duplicate_decisions([
        {"candidate_id": "c1", "status": "merged", "keeper_event_id": "k", "merged_event_ids": ["m"]},
        {"candidate_id": "c2", "status": "undone"},
        {"candidate_id": "c3", "status": "distinct", "event_ids": ["a", "b"]},
    ])
    assert [(d["candidate_id"], d["decision"]) for d in dupes] == [("c1", "merged"), ("c3", "distinct")]

    qa = gold.extract_qa_decisions([{"flag_id": "f1", "status": "resolved"}, {"flag_id": "f2", "status": "undone"}])
    assert [q["flag_id"] for q in qa] == ["f1"]

    labels = gold.extract_labels({
        "data/review/x.local.json": {"rows": [{"country": "Country Name"}, {"country": "Peru", "label": 1}]},
    })
    assert labels == [{"country": "Peru", "label": 1, "label_file": "data/review/x.local.json"}]


def test_build_writes_all_outputs(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "gold_policy.json").write_text(json.dumps(POLICY))
    review = tmp_path / "data" / "review"
    canonical = tmp_path / "data" / "canonical"
    review.mkdir(parents=True)
    canonical.mkdir(parents=True)
    (canonical / "events_actor_coded.json").write_text(json.dumps({"events": [_event("a", salience="low")]}))
    (review / "events_with_edits.json").write_text(json.dumps({"events": [_event("a", salience="high", review_status="analyst_reviewed")]}))
    (review / "edits.local.json").write_text(json.dumps({"edits": [
        {"edit_id": "1", "event_id": "a", "editor_role": "analyst", "edited_at": "t", "patch": {"salience": "high"}},
    ]}))

    summary = gold.build(root=tmp_path, out_dir=tmp_path / "data" / "gold")
    assert summary["counts"]["events"] == 1
    assert summary["counts"]["corrections"] == 1
    assert summary["gold_tiers"] == {"analyst_reviewed": 1}
    written = sorted(p.name for p in (tmp_path / "data" / "gold").iterdir())
    assert written == sorted([
        "corrections.jsonl", "duplicate_decisions.jsonl", "events.jsonl", "labels.jsonl",
        "negatives.jsonl", "qa_decisions.jsonl", "summary.json",
    ])
