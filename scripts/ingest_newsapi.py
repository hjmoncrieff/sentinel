#!/usr/bin/env python3
"""
NewsAPI ingestion utilities for SENTINEL.

This module isolates recent-search collection logic from the main event
pipeline.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

import requests

from normalize_articles import make_article_record, should_keep_newsapi_source
from query_lexicon import DEFAULT_NEWSAPI_BUNDLES, build_newsapi_query

log = logging.getLogger("sentinel.ingest_newsapi")

NEWSAPI_URL = "https://newsapi.org/v2/everything"

NEWSAPI_QUERY_SPECS = [
    {"label": "governance", "language": "en", "families": DEFAULT_NEWSAPI_BUNDLES["governance"], "country_scope": "core_pipeline"},
    {"label": "governance", "language": "es", "families": DEFAULT_NEWSAPI_BUNDLES["governance"], "country_scope": "core_pipeline"},
    {"label": "crime", "language": "en", "families": DEFAULT_NEWSAPI_BUNDLES["crime"], "country_scope": "priority_cmr_focus"},
    {"label": "crime", "language": "es", "families": DEFAULT_NEWSAPI_BUNDLES["crime"], "country_scope": "priority_cmr_focus"},
    {"label": "crime", "language": "pt", "families": DEFAULT_NEWSAPI_BUNDLES["crime"], "country_scope": "priority_cmr_focus"},
    {"label": "conflict", "language": "en", "families": DEFAULT_NEWSAPI_BUNDLES["conflict"], "country_scope": "priority_cmr_focus"},
    {"label": "conflict", "language": "es", "families": DEFAULT_NEWSAPI_BUNDLES["conflict"], "country_scope": "priority_cmr_focus"},
    {"label": "external", "language": "en", "families": DEFAULT_NEWSAPI_BUNDLES["external"], "country_scope": "core_pipeline"},
]


def fetch_newsapi(api_key: str, since: str | None = None) -> list[dict]:
    if since is None:
        since = (datetime.now(timezone.utc) - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")
    seen_urls: set[str] = set()
    all_articles: list[dict] = []
    for i, query_cfg in enumerate(NEWSAPI_QUERY_SPECS, 1):
        query = build_newsapi_query(
            query_cfg["families"],
            language=query_cfg["language"],
            country_scope=query_cfg["country_scope"],
        )
        if not query:
            log.warning(f"NewsAPI query {i}: empty query generated for {query_cfg['label']} / {query_cfg['language']}")
            continue
        params = {
            "q": query,
            "language": query_cfg["language"],
            "sortBy": "publishedAt",
            "pageSize": "50",
            "from": since,
            "apiKey": api_key,
        }
        try:
            resp = requests.get(NEWSAPI_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") != "ok":
                msg_text = data.get("message", data.get("status", ""))
                if "too old" in msg_text.lower() or "upgrade" in msg_text.lower() or "maximumAge" in msg_text:
                    log.warning(f"NewsAPI query {i}: date too old for plan — {msg_text}")
                else:
                    log.error(f"NewsAPI query {i}: {msg_text}")
                continue
            batch = data.get("articles") or []
            log.info(f"NewsAPI query {i} ({query_cfg['label']}/{query_cfg['language']}): {len(batch)} raw articles")
            for article in batch:
                url = article.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    article["_sentinel_language"] = query_cfg["language"]
                    article["_sentinel_query_label"] = query_cfg["label"]
                    article["_sentinel_query_families"] = list(query_cfg["families"])
                    all_articles.append(article)
        except Exception as e:
            log.error(f"NewsAPI query {i} failed: {e}")
        time.sleep(0.5)
    log.info(f"NewsAPI total unique articles: {len(all_articles)}")
    return all_articles


def normalize_newsapi(articles: list[dict]) -> list[dict]:
    out = []
    for article in articles:
        title = (article.get("title") or "").strip()
        if not title or title == "[Removed]":
            continue
        published = article.get("publishedAt") or ""
        date = published[:10] if published else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        source_name = (article.get("source") or {}).get("name") or "NewsAPI"
        if not should_keep_newsapi_source(source_name):
            continue
        out.append(make_article_record(
            title=title,
            description=article.get("description") or title,
            url=article.get("url", ""),
            date=date,
            source=source_name,
            source_type="news_api",
            source_method="newsapi",
            coords=None,
            source_tier=2,
            source_role="verification",
            source_policy="public_metadata",
            source_languages=[article.get("_sentinel_language")] if article.get("_sentinel_language") else [],
            source_quality_weight=0.68,
            extraction_status="disabled",
        ))
        if article.get("_sentinel_query_label"):
            out[-1]["retrieval_query_label"] = article["_sentinel_query_label"]
        if article.get("_sentinel_query_families"):
            out[-1]["retrieval_query_families"] = list(article["_sentinel_query_families"])
    return out
