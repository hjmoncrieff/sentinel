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
    topic_pages = ["about/index.html", "organized-crime/index.html", "us-security/index.html"]
    for rel in ["index.html", "feed/index.html", "countries/index.html", *topic_pages, *[f"countries/{c['iso3'].lower()}/index.html" for c in reference]]:
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


def test_country_monitor_sections(site):
    col = (site / "countries/col/index.html").read_text(encoding="utf-8")
    for marker in ('class="act-chart"', 'class="con-ev"', "Region median"):
        assert marker in col, marker
    # The map needs place-level coordinates, which the published layer carries from 2026-10-05.
    published = json.loads((ROOT / "data/published/events_public.json").read_text(encoding="utf-8"))["events"]
    if any(e["country"] == "Colombia" and e.get("location_precision") == "place" for e in published):
        assert 'class="cmap instr"' in col
    # The in-depth text predates the August 2026 change of government.
    assert "Needs revision" in col
    assert "Needs revision" not in (site / "countries/slv/index.html").read_text(encoding="utf-8")
    # A country with no events in the window gets no chart or map, and says so in each reading.
    blz = (site / "countries/blz/index.html").read_text(encoding="utf-8")
    assert 'class="act-chart"' not in blz and 'class="cmap' not in blz


def test_story_grouping_is_strict():
    script = """
      import {groupStories} from './apps/public-site/src/lib/model.mjs';
      const ev = (id, date, title, sal = 'medium') => ({id, date, title, sal, n_sources: 1});
      const out = groupStories([
        ev('a', '2026-09-30', "Mexico's National Guard debuts chihuahua dog recruit named Comando"),
        ev('b', '2026-09-30', 'Comando the chihuahua adopted by the Mexican national guard', 'high'),
        ev('c', '2026-09-29', 'National Guard deployed to Sinaloa after cartel clashes'),
        ev('d', '2026-08-01', "Mexico's National Guard debuts chihuahua dog recruit named Comando"),
      ]);
      console.log(JSON.stringify(out.map(g => [g.lead.id, ...g.others.map(o => o.id)])));
    """
    result = subprocess.run(["node", "--input-type=module", "-e", script], check=True, cwd=ROOT, capture_output=True, text=True)
    assert json.loads(result.stdout) == [["b", "a"], ["c"], ["d"]]


def test_every_event_has_a_record_page_and_old_ids_forward(site):
    feed = json.loads((site / "data/feed.json").read_text(encoding="utf-8"))
    for event in feed["events"][:50] + feed["events"][-50:]:
        html = (site / "events" / event["id"] / "index.html").read_text(encoding="utf-8")
        assert "Cite this record" in html and event["id"] in html
        assert "undefined" not in html
    for old, target in feed["aliases"].items():
        stub = (site / "events" / old / "index.html").read_text(encoding="utf-8")
        assert f"/x/events/{target}/" in stub and 'http-equiv="refresh"' in stub
    ids = {e["id"] for e in feed["events"]}
    assert all(e.get("story") in ids for e in feed["events"] if e.get("story"))


def test_about_page_lists_the_whole_codebook(site):
    html = (site / "about/index.html").read_text(encoding="utf-8")
    codebook = json.loads((ROOT / "config/taxonomy/codebook_v3.json").read_text(encoding="utf-8"))
    for domain in codebook["domains"]:
        for kind in domain["types"]:
            assert f'>{kind["code"]}<' in html, kind["code"]
