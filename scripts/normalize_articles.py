"""
Shared article normalization helpers for SENTINEL ingestion sources.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from urllib.parse import urlparse


NEWSAPI_SOURCE_ALLOWLIST = {
    "ABC News",
    "Abcnews.com",
    "Al Jazeera English",
    "BBC News",
    "CBS News",
    "CBC News",
    "Democracy Now!",
    "DW (English)",
    "Foreign Policy",
    "Fox News",
    "HuffPost",
    "NPR",
    "NBC News",
    "New York Post",
    "Newser",
    "PBS",
    "POLITICO.eu",
    "The Atlantic",
    "The Intercept",
    "The Times of India",
    "The Week Magazine",
    "TheJournal.ie",
    "Truthout",
}


def infer_source_domain(url: str) -> str | None:
    if not url:
        return None
    try:
        domain = (urlparse(url).netloc or "").lower()
    except Exception:
        return None
    if domain.startswith("www."):
        domain = domain[4:]
    return domain or None


def stable_article_id(*, title: str, url: str, date: str, source: str) -> str:
    basis = f"{(url or '').strip()}|{(title or '').strip()}|{date}|{source}"
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


def make_article_record(
    *,
    title: str,
    description: str,
    url: str,
    date: str,
    source: str,
    source_type: str,
    source_method: str,
    coords: list[float] | None = None,
) -> dict:
    cleaned_title = (title or "").strip()
    cleaned_url = url or ""
    normalized_at = datetime.now(UTC).isoformat()
    return {
        "article_id": stable_article_id(
            title=cleaned_title,
            url=cleaned_url,
            date=date,
            source=source,
        ),
        "title": cleaned_title,
        "description": (description or "")[:500].strip(),
        "url": cleaned_url,
        "date": date,
        "source": source,
        "source_type": source_type,
        "source_method": source_method,
        "source_domain": infer_source_domain(cleaned_url),
        "normalized_at": normalized_at,
        "coords": coords,
    }


def should_keep_newsapi_source(source_name: str) -> bool:
    """
    Keep a curated set of broadly credible outlets and allow a small fallback for
    clearly recognizable major brands.
    """
    if source_name in NEWSAPI_SOURCE_ALLOWLIST:
        return True

    lowered = source_name.lower()
    fallback_tokens = (
        "reuters",
        "associated press",
        "ap ",
        "bloomberg",
        "washington post",
        "wall street journal",
        "economist",
        "guardian",
    )
    return any(token in lowered for token in fallback_tokens)
