#!/usr/bin/env python3
"""
RSS and archive ingestion utilities for SENTINEL.

This module separates source collection from the larger event pipeline so
`run_pipeline.py` can act more like a thin top-level runner.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone

import feedparser
import requests

from normalize_articles import make_article_record

log = logging.getLogger("sentinel.ingest_rss")

RSS_TIMEOUT = 15
USER_AGENT = "SENTINEL-research-bot/1.0"

WP_SOURCES = [
    {
        "name": "InSight Crime",
        "base": "https://insightcrime.org/wp-json/wp/v2/posts",
    },
    {
        "name": "Americas Quarterly",
        "base": "https://americasquarterly.org/wp-json/wp/v2/posts",
    },
    {
        "name": "NACLA",
        "base": "https://nacla.org/wp-json/wp/v2/posts",
    },
]


def fetch_rss(feed: dict, cutoff: datetime) -> list[dict]:
    log.info(f"RSS: {feed['name']}")
    try:
        resp = requests.get(
            feed["url"],
            timeout=RSS_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
        items = []
        for entry in parsed.entries[:20]:
            pub = entry.get("published_parsed") or entry.get("updated_parsed")
            if pub:
                pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                if pub_dt < cutoff:
                    continue
            else:
                pub_dt = datetime.now(timezone.utc)
            title = (entry.get("title") or "").strip()
            if not title:
                continue
            items.append(make_article_record(
                title=title,
                description=entry.get("summary") or "",
                url=entry.get("link", ""),
                date=pub_dt.strftime("%Y-%m-%d"),
                source=feed["name"],
                source_type=feed.get("category", "rss"),
                source_method="rss",
                coords=None,
            ))
        log.info(f"  → {len(items)} items")
        return items
    except requests.Timeout:
        log.warning(f"  RSS timeout {feed['name']} after {RSS_TIMEOUT}s")
        return []
    except Exception as e:
        log.error(f"  RSS error {feed['name']}: {e}")
        return []


def fetch_wordpress_archive(source: dict, since_dt: datetime,
                            until_dt: datetime | None = None,
                            max_pages: int = 50) -> list[dict]:
    """
    Paginate a WordPress REST API to collect posts since since_dt.
    Returns normalized article dicts ready for pre_filter / classify.
    """
    if until_dt is None:
        until_dt = datetime.now(timezone.utc)
    base = source["base"]
    name = source["name"]
    since_str = since_dt.strftime("%Y-%m-%dT%H:%M:%S")
    until_str = until_dt.strftime("%Y-%m-%dT%H:%M:%S")
    articles: list[dict] = []
    for page in range(1, max_pages + 1):
        params = {
            "per_page": 100,
            "page": page,
            "after": since_str,
            "before": until_str,
            "orderby": "date",
            "order": "desc",
            "_fields": "id,date,title,link,excerpt,categories",
        }
        try:
            resp = requests.get(base, params=params, timeout=30, headers={"User-Agent": USER_AGENT})
            if resp.status_code == 400:
                break
            resp.raise_for_status()
            posts = resp.json()
            if not posts:
                break
            for post in posts:
                title = post.get("title", {}).get("rendered", "").strip()
                excerpt = post.get("excerpt", {}).get("rendered", "")
                excerpt = re.sub(r"<[^>]+>", " ", excerpt).strip()[:300]
                date_str = (post.get("date") or "")[:10]
                url = post.get("link", "")
                if not title or not url:
                    continue
                articles.append(make_article_record(
                    title=title,
                    description=excerpt or title,
                    url=url,
                    date=date_str,
                    source=name,
                    source_type="archive",
                    source_method="wordpress_archive",
                    coords=None,
                ))
            log.info(f"{name} page {page}: {len(posts)} posts")
            if len(posts) < 100:
                break
            time.sleep(0.5)
        except Exception as e:
            log.error(f"{name} archive page {page} failed: {e}")
            break
    log.info(f"{name} archive total: {len(articles)} articles")
    return articles


def fetch_all_archives(since_dt: datetime, until_dt: datetime | None = None) -> list[dict]:
    """Scrape all configured WordPress archives."""
    all_articles: list[dict] = []
    for source in WP_SOURCES:
        try:
            all_articles.extend(fetch_wordpress_archive(source, since_dt, until_dt))
            time.sleep(1.0)
        except Exception as e:
            log.error(f"Archive fetch failed for {source['name']}: {e}")
    return all_articles
