"""
Shared article normalization helpers for SENTINEL ingestion sources.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


NEWSAPI_SOURCE_ALLOWLIST = {
    "ABC News",
    "Abcnews.com",
    "Al Jazeera English",
    "BBC News",
    "CBS News",
    "CBC News",
    "Democracy Now!",
    "DW (English)",
    "El País",
    "Folha de S.Paulo",
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
    "The Guardian",
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


TRACKING_QUERY_PREFIXES = (
    "utm_",
    "mc_",
)
TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "igshid",
    "mkt_tok",
    "ref",
    "ref_src",
    "ref_url",
    "s",
    "smid",
    "spm",
}


def canonicalize_url(url: str) -> str:
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return url.strip()

    scheme = (parsed.scheme or "https").lower()
    netloc = (parsed.netloc or "").lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]

    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    filtered_query = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=False):
        lowered = key.lower()
        if lowered in TRACKING_QUERY_KEYS or any(lowered.startswith(prefix) for prefix in TRACKING_QUERY_PREFIXES):
            continue
        filtered_query.append((key, value))
    query = urlencode(filtered_query, doseq=True)

    return urlunparse((scheme, netloc, path, "", query, ""))


def stable_article_id(*, title: str, url: str, date: str, source: str) -> str:
    canonical_url = canonicalize_url(url)
    basis = f"{canonical_url}|{(title or '').strip()}|{date}|{source}"
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
    source_tier: int | None = None,
    source_role: str | None = None,
    source_policy: str | None = None,
    source_languages: list[str] | None = None,
    source_quality_weight: float | None = None,
    body_text: str = "",
    body_word_count: int = 0,
    extraction_status: str = "not_attempted",
) -> dict:
    cleaned_title = (title or "").strip()
    cleaned_url = url or ""
    canonical_url = canonicalize_url(cleaned_url)
    normalized_at = datetime.now(UTC).isoformat()
    cleaned_description = (description or "")[:1200].strip()
    cleaned_body_text = (body_text or "")[:40000].strip()
    return {
        "article_id": stable_article_id(
            title=cleaned_title,
            url=cleaned_url,
            date=date,
            source=source,
        ),
        "title": cleaned_title,
        "description": cleaned_description,
        "url": cleaned_url,
        "url_canonical": canonical_url,
        "date": date,
        "source": source,
        "source_type": source_type,
        "source_method": source_method,
        "source_tier": source_tier,
        "source_role": source_role,
        "source_policy": source_policy,
        "source_languages": list(source_languages or []),
        "source_quality_weight": source_quality_weight,
        "source_domain": infer_source_domain(cleaned_url),
        "normalized_at": normalized_at,
        "coords": coords,
        "body_text": cleaned_body_text,
        "body_word_count": body_word_count,
        "extraction_status": extraction_status,
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
