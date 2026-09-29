"""Static checks on the public site's pages and launch assets."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SITE_URL = "https://hjmoncrieff.github.io/sentinel/"
PAGES = ["index.html", "404.html", "privacy.html", "terms.html", "thank-you.html"]
LOCAL_REF = re.compile(r'(?:href|src|content)="((?:assets/|site\.webmanifest|privacy\.html|terms\.html|thank-you\.html)[^"?#]*)')


@pytest.mark.parametrize("page", PAGES)
def test_page_has_title_description_and_icons(page):
    html = (ROOT / page).read_text(encoding="utf-8")
    assert re.search(r"<title>[^<]{10,}</title>", html), page
    assert re.search(r'<meta name="description" content="[^"]{50,}"', html), page
    assert 'rel="icon"' in html and "assets/icons/favicon.svg" in html, page
    assert 'name="viewport"' in html, page


@pytest.mark.parametrize("page", PAGES)
def test_local_references_exist(page):
    html = (ROOT / page).read_text(encoding="utf-8")
    missing = [ref for ref in LOCAL_REF.findall(html) if not (ROOT / ref).exists()]
    assert not missing, missing


def test_no_img_without_alt():
    for page in PAGES:
        for tag in re.findall(r"<img\b[^>]*>", (ROOT / page).read_text(encoding="utf-8")):
            assert re.search(r'\balt="', tag), (page, tag)


def test_sitemap_urls_resolve_to_files():
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [el.text for el in ET.parse(ROOT / "sitemap.xml").getroot().findall("s:url/s:loc", ns)]
    assert locs and all(loc.startswith(SITE_URL) for loc in locs)
    for loc in locs:
        rel = loc.removeprefix(SITE_URL) or "index.html"
        assert (ROOT / rel).is_file(), loc


def test_manifest_icons_exist():
    manifest = json.loads((ROOT / "site.webmanifest").read_text(encoding="utf-8"))
    for icon in manifest["icons"]:
        assert (ROOT / icon["src"]).is_file(), icon["src"]


def test_og_image_is_compressed_and_sized():
    og = ROOT / "assets" / "og" / "sentinel-og.png"
    data = og.read_bytes()
    width, height = int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    assert (width, height) == (1200, 630)
    assert len(data) < 100_000


def test_private_surfaces_are_noindex():
    console = (ROOT / "apps" / "analyst-console" / "index.html").read_text(encoding="utf-8")
    assert 'name="robots" content="noindex, nofollow"' in console
    assert "Disallow: /apps/" in (ROOT / "robots.txt").read_text(encoding="utf-8")


def test_privacy_policy_matches_consent_implementation():
    site_js = (ROOT / "assets" / "js" / "site.js").read_text(encoding="utf-8")
    privacy = (ROOT / "privacy.html").read_text(encoding="utf-8")
    key = re.search(r"CONSENT_KEY = '([^']+)'", site_js).group(1)
    provider = re.search(r"provider: '([^']+)'", site_js).group(1)
    assert key in privacy
    assert provider.lower() in privacy.lower()
