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


class _FailingMessages:
    def create(self, **kwargs):
        raise TypeError("Messages.create() got an unexpected keyword argument 'temperature'")


class _FailingClient:
    messages = _FailingMessages()


def test_classify_aborts_when_every_batch_fails():
    # Regression (2026-09-29): an SDK upgrade broke every call, yet the run
    # "succeeded" and published nothing. A total failure must now raise.
    import pytest

    articles = [
        {"article_id": f"a{i}", "title": f"Army deploys troops in Colombia {i}", "description": "",
         "url": f"https://x.test/{i}", "date": "2026-09-01", "source": "Test"}
        for i in range(3)
    ]
    with pytest.raises(RuntimeError, match="classification batches failed"):
        pc.classify_articles(_FailingClient(), articles, {})


def test_deterministic_sampling_goes_through_extra_body():
    # anthropic>=1 removed the `temperature` keyword; it must not reappear as one.
    import inspect

    src = inspect.getsource(pc)
    assert "temperature=0" not in src
    assert pc.DETERMINISTIC == {"temperature": 0}


def test_official_scrapers_drop_items_before_cutoff():
    # Regression (2026-09-29): Google News returned DEA releases from 2016-2024,
    # which were stored as new events.
    from datetime import datetime, timezone

    cutoff = datetime(2026, 8, 30, tzinfo=timezone.utc)
    assert pc._before_cutoff("2016-05-05", cutoff)
    assert not pc._before_cutoff("2026-08-30", cutoff)
    assert not pc._before_cutoff(None, cutoff)
    assert not pc._before_cutoff("2016-05-05", None)


def test_geolocate_ignores_common_words_and_foreign_places():
    # Regression (2026-09-29): "para" (Spanish) and "Río" matched Brazilian places,
    # misplacing 14% of events.
    col = pc.COUNTRY_CENTROIDS["Colombia"]
    assert pc.geolocate("Gobierno anuncia plan para la paz en el Río Magdalena", "Colombia") == col
    assert pc.geolocate("Protesta en Rio de Janeiro", "Venezuela") == pc.COUNTRY_CENTROIDS["Venezuela"]
    assert pc.geolocate("Protest in Rio de Janeiro", "Brazil") == pc.PLACE_COORDS["rio de janeiro"]
    assert pc.geolocate("Ataque en Cali", "Colombia") == pc.PLACE_COORDS["cali"]
    assert pc.geolocate("calidad del aire", "Colombia") == col  # whole words only


def test_backfill_scope_gate_drops_global_wire_stories():
    kept = pc.scope_filter_backfill([
        {"title": "Army deploys to Haiti capital", "description": "", "source": "Reuters LatAm"},
        {"title": "Army deploys after decree in Kyiv", "description": "", "source": "Reuters LatAm"},
        {"title": "Ministro anuncia reforma", "description": "", "source": "Peru MINDEF"},
    ])
    assert [a["title"] for a in kept] == ["Army deploys to Haiti capital", "Ministro anuncia reforma"]


def test_report_excerpt_strips_markup_and_caps_length():
    assert pc.report_excerpt(None) is None
    assert pc.report_excerpt("<p>Army&nbsp;deploys <b>troops</b></p>") == "Army deploys troops"
    long = pc.report_excerpt("word " * 400)
    assert len(long) <= pc.REPORT_EXCERPT_CHARS + 1 and long.endswith("…")


def test_geolocate_knows_santa_marta():
    assert pc.geolocate("Santa Marta", "Colombia") == pc.PLACE_COORDS["santa marta"]


def test_clean_headline_strips_google_news_publisher_only():
    assert pc.clean_headline("Fuerzas Militares refuerzan medidas en frontera - Revista Semana", "google_news_rss") == "Fuerzas Militares refuerzan medidas en frontera"
    assert pc.clean_headline("Army deploys - Reuters", "rss") == "Army deploys - Reuters"
    assert pc.clean_headline("Short - X", "google_news_rss") == "Short - X"  # too short to trust the strip


def test_fill_source_metadata_uses_feed_registry():
    arts = [{"source": "InSight Crime", "source_tier": None}, {"source": "Unknown Blog"}]
    pc.fill_source_metadata(arts)
    assert arts[0]["source_tier"] == 1
    assert "source_tier" not in arts[1]


def test_classify_prompt_asks_for_content_type_and_english():
    from prompt_library import render_prompt
    text = render_prompt("classify_events", items="[1] x")
    assert '"content":"event|analysis|profile"' in text
    assert "in English" in text


def test_coded_role_keeps_one_valid_value():
    assert pc.coded_role("military|external", pc.ACTOR_ROLES) == "military"
    assert pc.coded_role("population", pc.ACTOR_ROLES) is None
    assert pc.coded_role("population", pc.TARGET_ROLES) == "population"
    assert pc.coded_role(None, pc.ACTOR_ROLES) is None


def test_lookback_widens_after_missed_runs(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    store = tmp_path / "events.json"
    monkeypatch.setattr(pc, "DATA_FILE", store)
    now = datetime(2026, 10, 1, 7, tzinfo=timezone.utc)
    assert pc.lookback_days(now) == pc.DAYS_BACK  # no store yet
    store.write_text('{"updated": "2026-09-30T07:30:00+00:00", "events": []}')
    assert pc.lookback_days(now) == pc.DAYS_BACK
    store.write_text('{"updated": "2026-09-25T07:00:00+00:00", "events": []}')
    assert pc.lookback_days(now) == 7
    store.write_text('{"updated": "2026-07-14T07:00:00+00:00", "events": []}')
    assert pc.lookback_days(now) == pc.CATCHUP_MAX_DAYS


def test_v3_nightly_path_builds_events_with_v3_block(monkeypatch):
    import classify_v3
    import codebook

    articles = [
        {"article_id": "a1", "title": "Army chief dismissed after dispute with president", "date": "2026-10-01",
         "url": "https://example.org/a1", "source": "Example", "description": "The president removed the army chief on Thursday after a public dispute."},
        {"article_id": "a2", "title": "Football final draws record crowd", "date": "2026-10-01",
         "url": "https://example.org/a2", "source": "Example", "description": "A record crowd attended the final."},
    ]
    type_code = "purge"
    item = {"relevant": True, "content_type": "event", "type": type_code, "subtype": None, "country": "Peru",
            "event_date": "2026-10-01", "date_precision": "day", "salience": "high", "certainty": "high",
            "deed_type": "not_applicable", "axis": "not_applicable", "actors": [], "summary": "Army chief removed.",
            "location_place": "Lima", "location_admin1": None}
    monkeypatch.setattr(classify_v3, "gate", lambda client, arts, use_batch, model: {
        "a1": {"relevant": True, "content_type": "event", "country": "Peru"},
        "a2": {"relevant": False, "content_type": "event", "country": None}})
    monkeypatch.setattr(classify_v3, "code", lambda client, arts, model, use_batch, workers: {
        a["article_id"]: {"item": item, "problems": [], "usage": {"input_tokens": 10, "output_tokens": 5}} for a in arts})

    events = pc.classify_articles_v3(object(), articles, {})

    assert [e["source_article_ids"] for e in events] == [["a1"]]
    ev = events[0]
    assert ev["country"] == "Peru" and ev["salience"] == "high" and ev["conf"] == "green"
    assert ev["type"] == codebook.legacy_family(type_code, None)[0]
    assert ev["v3"]["type"] == type_code and ev["v3"]["coded_by"] == pc.model_for("code_event_v3")
    assert ev["deed_type"] is None


def test_v3_nightly_path_aborts_when_every_coding_request_fails(monkeypatch):
    import classify_v3
    import pytest

    articles = [{"article_id": "a1", "title": "Coup attempt reported", "date": "2026-10-01", "url": "https://example.org/a1",
                 "source": "Example", "description": "Troops surrounded the palace, officials said on Thursday."}]
    monkeypatch.setattr(classify_v3, "gate", lambda client, arts, use_batch, model: {"a1": {"relevant": True, "content_type": "event", "country": None}})
    monkeypatch.setattr(classify_v3, "code", lambda client, arts, model, use_batch, workers: {"a1": {"error": "APIError: boom"}})
    with pytest.raises(RuntimeError, match="coding requests failed"):
        pc.classify_articles_v3(object(), articles, {})


def test_fold_duplicate_events_merges_same_report_only():
    def ev(eid, title, date, country="Haiti", **extra):
        return {"id": eid, "title": title, "date": date, "country": country, "salience": "medium", "source": "S",
                "linked_reports": [{"article_id": "a-" + eid, "url": f"https://x.test/{eid}", "source_name": "S"}], **extra}

    title = "More than 5,000 people killed or injured in Haiti due to gang violence this year"
    events = [
        ev("old", title, "2026-10-02"),
        ev("new", title.upper() + "!", "2026-10-03", v3={"relevant": True}),
        ev("regional", title, "2026-10-02", country="Regional"),
        ev("later", title, "2026-11-20"),
        ev("elsewhere", title, "2026-10-02", country="Cuba"),
        ev("page1", "Shining Path", "2026-08-05"),
        ev("page2", "Shining Path", "2026-08-05"),
    ]
    kept, folded = pc.fold_duplicate_events(events)
    assert folded == 2
    assert [e["id"] for e in kept] == ["new", "later", "elsewhere", "page1", "page2"]
    new = kept[0]
    assert set(new["merged_ids"]) == {"old", "regional"}
    assert len(new["linked_reports"]) == 3

    kept, folded = pc.fold_duplicate_events([ev("old", title, "2026-10-02"), ev("new", title, "2026-10-02", v3={})], protected={"old"})
    assert folded == 1 and [e["id"] for e in kept] == ["old"]


def test_geolocate_uses_location_field_and_guards_common_words():
    centre = pc.COUNTRY_CENTROIDS
    assert pc.geolocate("", "Colombia", "Meta") == [3.5, -73.0]
    # "meta" is also the Spanish word for goal: never matched in a headline.
    assert pc.geolocate("El gobierno fija una meta de seguridad", "Colombia") == centre["Colombia"]
    # One name, two countries.
    assert pc.geolocate("", "Venezuela", "Bolívar") == [6.5, -63.5]
    assert pc.geolocate("", "Colombia", "Bolivar") == [8.7, -74.5]
    # A gang named after a state does not place the event there.
    assert pc.geolocate("Tren de Aragua factions persist", "Venezuela") == centre["Venezuela"]
    assert pc.geolocate("US sanctions Sinaloa Cartel financiers", "Mexico") == centre["Mexico"]
    assert pc.geolocate("Clashes in Zacatecas leave five dead", "Mexico") == [22.77, -102.58]
    # A place in another country is ignored.
    assert pc.geolocate("", "Chile", "Madrid") == centre["Chile"]


def test_prefilter_covers_july_audit_blind_spots():
    terms = {t for family in pc.PREFILTER_TERM_MAP.values() for t in family}
    for term in ("secuestran a coronel", "ley de amnistia", "justicia transicional", "alianza entre bandas",
                 "remanejamento de tropas", "world cup security"):
        assert term in terms, term
    headline = {"title": "Secuestran a coronel del Ejército en Arauca, Colombia", "description": ""}
    assert pc._article_relevance_score(headline) > 0
