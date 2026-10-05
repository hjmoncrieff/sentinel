"""The redesigned site builds from the published layer, and its pages and data are sound."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PRIVATE_FIELDS = ("review_notes", "analyst_reasoning", "reviewed_by", "review_history", "llm_synthesis", "raw_output")

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


@pytest.fixture(scope="module")
def site(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("public-site")
    subprocess.run(["node", str(ROOT / "apps/public-site/build.mjs"), "--out", str(out), "--base", "/x/", "--legacy", "/old/"],
                   check=True, cwd=ROOT, capture_output=True)
    return out


def test_every_page_is_built(site):
    reference = json.loads((ROOT / "apps/public-site/reference/countries.json").read_text(encoding="utf-8"))["countries"]
    assert len(reference) == 25
    for rel in ["index.html", "feed/index.html", "countries/index.html", *[f"countries/{c['iso3'].lower()}/index.html" for c in reference]]:
        html = (site / rel).read_text(encoding="utf-8")
        assert "<title>" in html and 'name="description"' in html, rel
        assert "undefined" not in re.sub(r"<script.*?</script>", "", html, flags=re.S), rel


def test_internal_links_and_assets_resolve(site):
    for page in site.rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        for target in re.findall(r'(?:href|src)="/x/([^"#?]*)', html):
            path = site / target
            assert path.is_file() or (path / "index.html").is_file(), f"{page.relative_to(site)} → {target}"


def test_feed_data_is_public_and_complete(site):
    text = (site / "data/feed.json").read_text(encoding="utf-8")
    assert not any(field in text for field in PRIVATE_FIELDS)
    feed = json.loads(text)
    published = json.loads((ROOT / "data/published/events_public.json").read_text(encoding="utf-8"))["events"]
    assert len(feed["events"]) == len([e for e in published if e.get("event_id") and e.get("event_date")])
    dates = [e["date"] for e in feed["events"]]
    assert dates == sorted(dates, reverse=True)
    assert all(e["sources"] for e in feed["events"])


def test_build_only_modules_do_not_ship(site):
    shipped = {p.name for p in (site / "assets").rglob("*") if p.is_file()}
    assert "model.mjs" not in shipped and "geo.mjs" not in shipped
