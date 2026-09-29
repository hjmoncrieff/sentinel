from __future__ import annotations

import pipeline_core as pc


def test_stable_id_is_deterministic_and_whitespace_insensitive():
    a = pc.stable_id("Colombia", "peace", "2026-06-01", "https://x.test/a")
    b = pc.stable_id("colombia", "peace", "2026-06-01", "  HTTPS://X.TEST/A  ")
    assert a == b
    assert len(a) == 12


def test_stable_id_separates_distinct_incidents_in_same_week():
    # Regression: the old country+type+ISO-week key collapsed these into one event.
    first = pc.stable_id("Colombia", "other", "2026-06-01", "https://x.test/election")
    second = pc.stable_id("Colombia", "other", "2026-06-02", "https://x.test/ceasefire")
    same_day_other_url = pc.stable_id("Colombia", "other", "2026-06-01", "https://x.test/other")
    assert len({first, second, same_day_other_url}) == 3


def test_make_sentinel_id_format():
    assert pc.make_sentinel_id("Colombia", "2026-03-15", "a3f7c9deadbe") == "COL_2026_03_a3f7c9"
    assert pc.make_sentinel_id("Atlantis", "2026-03-15", "a3f7c9deadbe").startswith("REG_")


def test_geolocate_respects_country_ownership_of_ambiguous_places():
    # "Salvador" is a Brazilian city; it must not pin an El Salvador event there.
    brazil_salvador = pc.geolocate("Protest in Salvador", "Brazil")
    el_salvador = pc.geolocate("Protest in Salvador", "El Salvador")
    assert brazil_salvador != el_salvador
    assert el_salvador == pc.COUNTRY_CENTROIDS["El Salvador"]


def test_geolocate_falls_back_to_centroid_then_origin():
    assert pc.geolocate("no known place here", "Peru") == pc.COUNTRY_CENTROIDS["Peru"]
    assert pc.geolocate("no known place here", "Atlantis") == [0.0, 0.0]


def _article(title: str, description: str = "") -> dict:
    return {"title": title, "description": description}


def test_pre_filter_keeps_civil_military_and_emergency_signals():
    kept = pc.pre_filter([
        _article("Army deploys to border after decree"),
        _article("Gobierno declara estado de excepción"),
        _article("Forças armadas mobilizadas após enchente"),
        _article("Local bakery wins award"),
    ])
    titles = {a["title"] for a in kept}
    assert "Local bakery wins award" not in titles
    assert len(kept) == 3
