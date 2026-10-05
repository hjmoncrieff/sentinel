import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import rebuild_downstream as rd


def test_every_step_exists():
    for script in rd.steps("publish", synthesis=True):
        assert (ROOT / script).is_file(), script


def test_synthesis_is_opt_in_and_review_stops_before_publish():
    default = rd.steps("publish", synthesis=False)
    assert not set(rd.SYNTHESIS_STEPS) & set(default)
    assert default[-1] == rd.PUBLISH_STEPS[0]
    assert rd.steps("review", synthesis=False) == rd.REVIEW_STEPS
    # Council analyses must exist before synthesis, and synthesis before publishing.
    full = rd.steps("publish", synthesis=True)
    assert full.index("scripts/analysis/run_council.py") < full.index(rd.SYNTHESIS_STEPS[0]) < full.index(rd.PUBLISH_STEPS[0])
