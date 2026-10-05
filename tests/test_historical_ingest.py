from __future__ import annotations

import json
from datetime import datetime

import historical_ingest as hi


def _manifest() -> dict:
    return {
        "source_groups": [
            {"group_id": "wp", "sources": [
                {"source_id": "wp_ok", "label": "WP OK", "connector_type": "wordpress_archive",
                 "historical_ready": True, "endpoint": "https://wp.test/wp-json/wp/v2/posts"},
                {"source_id": "wp_noendpoint", "label": "WP none", "connector_type": "wordpress_archive",
                 "historical_ready": "partial", "endpoint": None},
            ]},
            {"group_id": "structured", "sources": [
                {"source_id": "gdelt_api", "label": "GDELT", "connector_type": "gdelt",
                 "historical_ready": True, "coverage_start": "2015-02-19"},
                {"source_id": "acled", "label": "ACLED", "connector_type": "structured_dataset", "historical_ready": True},
                {"source_id": "folha", "label": "Folha", "connector_type": "gdelt", "historical_ready": False},
            ]},
        ]
    }


def _article(url: str, source: str) -> dict:
    return {"article_id": url[-8:], "url": url, "title": url, "date": "2015-01-15", "source": source}


def test_month_windows_clip_and_include_until():
    windows = hi.month_windows("2015-01-15", "2015-03-02")
    assert [m for m, _, _ in windows] == ["2015-01", "2015-02", "2015-03"]
    assert windows[0][1] == datetime(2015, 1, 15, tzinfo=windows[0][1].tzinfo)
    assert windows[-1][2].day == 2 and windows[-1][2].hour == 23


def test_select_sources_reports_skip_reasons():
    connectors = {"gdelt": None, "wordpress_archive": None}
    req = hi.HistoricalRequest(since="2015-01-01", until="2015-03-31", groups=[], dry_run=False)
    runnable, skipped = hi.select_sources(_manifest(), req, connectors)
    assert [s["source_id"] for s in runnable] == ["wp_ok", "gdelt_api"]
    assert {s["source_id"]: s["reason"] for s in skipped} == {
        "wp_noendpoint": "no endpoint configured",
        "acled": "no runner for connector_type=structured_dataset",
        "folha": "historical_ready=false",
    }


def test_units_respect_coverage_start():
    req = hi.HistoricalRequest(since="2015-01-01", until="2015-03-31", groups=[], dry_run=False)
    runnable, _ = hi.select_sources(_manifest(), req, {"gdelt": None, "wordpress_archive": None})
    keys = [u.key for u in hi.build_units(runnable, req)]
    assert keys == ["wp_ok:2015-01", "wp_ok:2015-02", "wp_ok:2015-03", "gdelt_api:2015-02", "gdelt_api:2015-03"]


def test_execute_resumes_checkpoints_and_reports_qa(tmp_path):
    calls: list[str] = []

    def wp(source, start, end):
        month = start.strftime("%Y-%m")
        calls.append(f"wp:{month}")
        if month == "2015-02":
            return []  # suspected gap
        shared = _article("https://wp.test/shared-story", "WP OK")
        return [_article(f"https://wp.test/{month}-a", "WP OK"), shared, shared]

    def gdelt(source, start, end):
        calls.append(f"gdelt:{start:%Y-%m}")
        raise RuntimeError("429 Too Many Requests")

    connectors = {"wordpress_archive": wp, "gdelt": gdelt}
    req = hi.HistoricalRequest(since="2015-01-01", until="2015-03-31", groups=[], dry_run=False)

    # First pass stops early; second pass resumes without refetching completed units.
    hi.execute(req, _manifest(), connectors=connectors, base_dir=tmp_path, max_units=2)
    assert calls == ["wp:2015-01", "wp:2015-02"]
    report = hi.execute(req, _manifest(), connectors=connectors, base_dir=tmp_path)
    assert calls[2:] == ["wp:2015-03", "gdelt:2015-02", "gdelt:2015-03"]

    run_dir = tmp_path / "2015-01-01_2015-03-31"
    jan = (run_dir / "wp_ok__2015-01.jsonl").read_text().splitlines()
    assert len(jan) == 2  # in-batch duplicate removed

    assert report["status"] == "incomplete"  # gdelt units failed and stay pending
    flags = {(f.get("source_id") or f.get("unit"), f["flag"]) for f in report["flags"]}
    assert ("wp_ok", "coverage_gap") in flags
    assert ("wp_ok", "cross_batch_duplicates") in flags
    assert ("gdelt_api:2015-02", "connector_error") in flags
    assert report["sources"]["gdelt_api"]["pending_months"] == ["2015-02", "2015-03"]

    # --retry-empty refetches only the zero-article month.
    calls.clear()
    hi.execute(req, _manifest(), connectors={"wordpress_archive": wp, "gdelt": lambda *a: []},
               base_dir=tmp_path, retry_empty=True)
    assert calls == ["wp:2015-02"]
    checkpoint = json.loads((run_dir / hi.CHECKPOINT_NAME).read_text())
    assert checkpoint["failed"] == {}


def test_dry_run_touches_nothing(tmp_path):
    req = hi.HistoricalRequest(since="2015-01-01", until="2015-01-31", groups=[], dry_run=True)
    out = hi.execute(req, _manifest(), connectors={"wordpress_archive": None, "gdelt": None}, base_dir=tmp_path)
    assert out["units"] == ["wp_ok:2015-01"]
    assert not any(tmp_path.iterdir())


def test_real_manifest_is_runnable_for_known_sources():
    req = hi.HistoricalRequest(since="2016-01-01", until="2016-01-31", groups=[], dry_run=True)
    runnable, skipped = hi.select_sources(hi.load_manifest(), req, hi.default_connectors())
    ids = {s["source_id"] for s in runnable}
    assert {"gdelt_api", "insight_crime_archive", "americas_quarterly_archive", "nacla_archive"} <= ids
    assert all(s["reason"] for s in skipped)


def test_week_windows_cover_range_without_overlap():
    from datetime import datetime, timezone

    start = datetime(2026, 8, 1, tzinfo=timezone.utc)
    end = datetime(2026, 9, 1, tzinfo=timezone.utc)
    windows = hi.week_windows(start, end)
    assert windows[0][0] == start and windows[-1][1] == end
    assert all(a[1] == b[0] for a, b in zip(windows, windows[1:]))
    assert all((w[1] - w[0]).days <= 7 for w in windows)


def test_google_news_backfill_queries_are_short_and_windowed():
    # Regression (2026-09-29): Google ignores after:/before: on long OR queries,
    # so backfill queries must drop the live feeds' topic terms.
    from datetime import datetime, timezone

    from ingest_rss import google_news_backfill_feeds, google_news_window_url

    feeds = [
        {"name": "Small", "url": "https://news.google.com/rss/search?q=site:nacla.org+(army+OR+police)&hl=en-US&gl=US&ceid=US:en"},
        {"name": "Wire", "url": "https://news.google.com/rss/search?q=site:apnews.com+(army+OR+coup)&hl=en-US&gl=US&ceid=US:en"},
        {"name": "Wire dup", "url": "https://news.google.com/rss/search?q=site:apnews.com+(election)&hl=en-US&gl=US&ceid=US:en"},
    ]
    queries = google_news_backfill_feeds(feeds, ["Haiti", "El Salvador"])
    urls = [q["url"] for q in queries]
    assert "https://news.google.com/rss/search?q=site:nacla.org&hl=en-US&gl=US&ceid=US:en" in urls
    assert any("site:apnews.com+%22El+Salvador%22" in u for u in urls)
    assert len(urls) == 3 and not any("OR" in u for u in urls)

    windowed = google_news_window_url(urls[0], datetime(2026, 8, 1), datetime(2026, 8, 8))
    assert "site:nacla.org+after:2026-08-01+before:2026-08-08&hl=" in windowed


def test_bot_challenge_pages_are_not_article_text():
    import enrich_ledes as el

    assert el.is_challenge_page("Making sure you're not a bot! Loading... You are seeing this because the administrator")
    assert el.is_challenge_page("...but your activity and behavior on this site made us think that you are a bot.")
    assert not el.is_challenge_page("The president removed the army chief on Thursday after a public dispute over the budget.")
