import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from analysis.restore_council_synthesis import restore


def _entry(event_id, llm=None, public="template text"):
    analyses = {"synthesis": {"public_analysis": public, "risk_level": "low", "ai_generated": False}}
    if llm:
        analyses["llm_synthesis"] = llm
    return {"event_id": event_id, "analyses": analyses}


def test_restore_copies_saved_synthesis_and_marks_it_ai_generated():
    fresh = [_entry("e1"), _entry("e2"), _entry("e3")]
    saved = [
        _entry("e1", {"model": "claude-sonnet-5-5", "synthesis": "Model text.", "watchpoint": "Next vote.", "risk_level": "high"}),
        _entry("e2", {"ok": False, "error": "boom"}),          # failed attempts are not restored
        _entry("gone", {"synthesis": "Orphan.", "risk_level": "low"}),
    ]
    assert restore(fresh, saved) == 1
    syn = fresh[0]["analyses"]["synthesis"]
    assert syn["public_analysis"] == "Model text.\n\n**Watch:** Next vote."
    assert syn["ai_generated"] is True and syn["risk_level"] == "high" and syn["llm_model"] == "claude-sonnet-5-5"
    assert "llm_synthesis" not in fresh[1]["analyses"]
    assert fresh[2]["analyses"]["synthesis"]["ai_generated"] is False


def test_restore_never_overwrites_a_newer_local_synthesis():
    fresh = [_entry("e1", {"synthesis": "New.", "risk_level": "low"})]
    assert restore(fresh, [_entry("e1", {"synthesis": "Old.", "risk_level": "high"})]) == 0
    assert fresh[0]["analyses"]["llm_synthesis"]["synthesis"] == "New."
