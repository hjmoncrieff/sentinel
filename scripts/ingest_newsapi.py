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

log = logging.getLogger("sentinel.ingest_newsapi")

NEWSAPI_URL = "https://newsapi.org/v2/everything"

NEWSAPI_QUERIES = [
    (
        '(military OR army OR "armed forces" OR coup OR "defense minister" OR "fuerzas armadas"'
        ' OR ejército OR naval OR "air force") AND (Colombia OR Mexico OR Venezuela OR Brazil'
        ' OR Ecuador OR Peru OR Bolivia OR Honduras OR Guatemala OR "El Salvador" OR Nicaragua'
        ' OR Haiti OR Argentina OR Chile OR Uruguay OR Paraguay OR Cuba OR Panama)'
    ),
    (
        '(guerrilla OR cartel OR narco OR ELN OR FARC OR "Clan del Golfo" OR "organized crime"'
        ' OR "drug trafficking" OR ceasefire OR "peace process" OR insurgent OR paramilitary)'
        ' AND (Latin America OR Colombia OR Mexico OR Venezuela OR Central America OR "South America")'
    ),
    (
        '(protest OR "security sector" OR "security reform" OR "police reform" OR coup'
        ' OR "democratic backsliding" OR "civil-military" OR "state of emergency"'
        ' OR "estado de excepción") AND (Colombia OR Mexico OR Venezuela OR Brazil OR Ecuador'
        ' OR Peru OR Bolivia OR Honduras OR Guatemala OR Argentina OR Chile)'
    ),
]


def fetch_newsapi(api_key: str, since: str | None = None) -> list[dict]:
    if since is None:
        since = (datetime.now(timezone.utc) - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")
    seen_urls: set[str] = set()
    all_articles: list[dict] = []
    for i, query in enumerate(NEWSAPI_QUERIES, 1):
        params = {
            "q": query,
            "language": "en",
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
            log.info(f"NewsAPI query {i}: {len(batch)} raw articles")
            for article in batch:
                url = article.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
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
        ))
    return out
