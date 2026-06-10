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

from extract_article_text import extract_article_text, should_extract_full_text
from normalize_articles import make_article_record
from rss_sources import ARCHIVE_SOURCES

log = logging.getLogger("sentinel.ingest_rss")

RSS_TIMEOUT = 15
USER_AGENT = "SENTINEL-research-bot/1.0"

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
        fetch_limit = int(feed.get("fetch_limit", 20))
        lookback_days = max((datetime.now(timezone.utc) - cutoff).days, 0)
        if lookback_days > 7:
            backfill_limit = int(feed.get("backfill_fetch_limit") or min(max(fetch_limit * 4, 40), 120))
            fetch_limit = max(fetch_limit, backfill_limit)
        do_extract = should_extract_full_text(
            bool(feed.get("fetch_full_text")),
            feed.get("policy"),
        )
        for entry in parsed.entries[:fetch_limit]:
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
            url = entry.get("link", "")
            extracted = (
                extract_article_text(url)
                if do_extract and url
                else {"body_text": "", "body_word_count": 0, "extraction_status": "disabled"}
            )
            items.append(make_article_record(
                title=title,
                description=entry.get("summary") or "",
                url=url,
                date=pub_dt.strftime("%Y-%m-%d"),
                source=feed["name"],
                source_type=feed.get("category", "rss"),
                source_method=feed.get("source_method", "rss"),
                coords=None,
                source_tier=feed.get("tier"),
                source_role=feed.get("role"),
                source_policy=feed.get("policy"),
                source_languages=feed.get("languages"),
                source_quality_weight=feed.get("quality_weight"),
                body_text=extracted.get("body_text", ""),
                body_word_count=extracted.get("body_word_count", 0),
                extraction_status=extracted.get("extraction_status", "disabled"),
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
    base = source["archive_base"]
    name = source["name"]
    since_str = since_dt.strftime("%Y-%m-%dT%H:%M:%S")
    until_str = until_dt.strftime("%Y-%m-%dT%H:%M:%S")
    articles: list[dict] = []
    do_extract = should_extract_full_text(
        bool(source.get("fetch_full_text")),
        source.get("policy"),
    )
    archive_extract_limit = int(source.get("archive_extract_limit", 12))
    extracted_count = 0
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
                excerpt = re.sub(r"<[^>]+>", " ", excerpt).strip()[:800]
                date_str = (post.get("date") or "")[:10]
                url = post.get("link", "")
                if not title or not url:
                    continue
                extracted = {"body_text": "", "body_word_count": 0, "extraction_status": "disabled"}
                if do_extract and url and extracted_count < archive_extract_limit:
                    extracted = extract_article_text(url)
                    extracted_count += 1
                articles.append(make_article_record(
                    title=title,
                    description=excerpt or title,
                    url=url,
                    date=date_str,
                    source=name,
                    source_type=source.get("category", "archive"),
                    source_method="wordpress_archive",
                    coords=None,
                    source_tier=source.get("tier"),
                    source_role=source.get("role"),
                    source_policy=source.get("policy"),
                    source_languages=source.get("languages"),
                    source_quality_weight=source.get("quality_weight"),
                    body_text=extracted.get("body_text", ""),
                    body_word_count=extracted.get("body_word_count", 0),
                    extraction_status=extracted.get("extraction_status", "disabled"),
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
    for source in ARCHIVE_SOURCES:
        try:
            all_articles.extend(fetch_wordpress_archive(source, since_dt, until_dt))
            time.sleep(1.0)
        except Exception as e:
            log.error(f"Archive fetch failed for {source['name']}: {e}")
    return all_articles
