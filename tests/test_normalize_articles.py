from __future__ import annotations

from normalize_articles import infer_source_domain, make_article_record, should_keep_newsapi_source


def test_article_record_id_is_stable_and_domain_inferred():
    kwargs = dict(
        title="  Title  ", description="d" * 2000, url="https://www.example.org/a",
        date="2026-01-02", source="Example", source_type="wire", source_method="rss",
    )
    a = make_article_record(**kwargs)
    b = make_article_record(**kwargs)
    assert a["article_id"] == b["article_id"]
    assert len(a["article_id"]) == 16
    assert a["title"] == "Title"
    assert len(a["description"]) == 1200  # cap raised from 500 for richer classifier context
    assert a["source_domain"] == "example.org"


def test_infer_source_domain_handles_empty_and_bad_urls():
    assert infer_source_domain("") is None
    assert infer_source_domain("not a url") is None


def test_newsapi_allowlist_and_fallback_tokens():
    assert should_keep_newsapi_source("NPR")
    assert should_keep_newsapi_source("Reuters Latin America")
    assert not should_keep_newsapi_source("Random Blog")
