"""
Lawful full-text extraction helpers for public-source ingestion.

This module intentionally supports only sources the registry marks as
`public_fulltext`. It does not attempt to bypass paywalls or restricted
delivery systems.
"""

from __future__ import annotations

import logging
import re

import requests

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - optional dependency fallback
    BeautifulSoup = None


log = logging.getLogger("sentinel.extract_article_text")

EXTRACT_TIMEOUT = 20
EXTRACT_HEADERS = {"User-Agent": "SENTINEL-research-bot/1.0"}
MIN_BODY_WORDS = 80

BODY_SELECTORS = (
    "article",
    "main article",
    "main",
    '[itemprop="articleBody"]',
    ".article-content",
    ".entry-content",
    ".post-content",
    ".article-body",
    ".story-body",
    ".content-body",
)


def should_extract_full_text(fetch_full_text: bool, policy: str | None) -> bool:
    return bool(fetch_full_text and policy == "public_fulltext")


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def _extract_from_html(html: str) -> str:
    if not BeautifulSoup:
        return ""

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "form"]):
        tag.decompose()

    for selector in BODY_SELECTORS:
        nodes = soup.select(selector)
        chunks = []
        for node in nodes:
            text = _clean_text(node.get_text(" ", strip=True))
            if len(text.split()) >= MIN_BODY_WORDS:
                chunks.append(text)
        if chunks:
            return max(chunks, key=lambda value: len(value.split()))

    paragraphs = [
        _clean_text(node.get_text(" ", strip=True))
        for node in soup.find_all("p")
    ]
    paragraphs = [paragraph for paragraph in paragraphs if len(paragraph.split()) >= 8]
    return _clean_text(" ".join(paragraphs))


def extract_article_text(url: str) -> dict:
    """
    Return a normalized extraction payload.

    Possible statuses:
    - disabled
    - missing_url
    - missing_parser
    - too_short
    - ok
    - fetch_error
    """
    if not url:
        return {"body_text": "", "body_word_count": 0, "extraction_status": "missing_url"}
    if not BeautifulSoup:
        return {"body_text": "", "body_word_count": 0, "extraction_status": "missing_parser"}

    try:
        response = requests.get(url, timeout=EXTRACT_TIMEOUT, headers=EXTRACT_HEADERS)
        response.raise_for_status()
    except Exception as exc:
        log.debug("Full-text fetch failed for %s: %s", url, exc)
        return {"body_text": "", "body_word_count": 0, "extraction_status": "fetch_error"}

    body_text = _extract_from_html(response.text)
    word_count = len(body_text.split())
    if word_count < MIN_BODY_WORDS:
        return {
            "body_text": body_text[:4000],
            "body_word_count": word_count,
            "extraction_status": "too_short",
        }
    return {
        "body_text": body_text[:40000],
        "body_word_count": word_count,
        "extraction_status": "ok",
    }
