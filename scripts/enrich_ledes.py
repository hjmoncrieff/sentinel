#!/usr/bin/env python3
"""
Give staged articles real text before classification.

Google News search results (the bulk of any date-windowed backfill) carry only a
headline: their RSS "description" repeats the title. This step takes the
articles that pass the pipeline's relevance gates, resolves each Google News
link to the publisher's page, and stores a short lede: the publisher's own
summary (og:description / meta description) followed by the opening paragraphs,
capped at LEDE_CHARS.

Results go to <run_dir>/_ledes.json, keyed by article_id, and are resumable.
`run_pipeline.py --from-staging <run_dir>` merges them automatically. The lede
feeds classification and stays in the private staging/event layers; the public
site shows only a trimmed excerpt with a link to the source.

It never bypasses paywalls or logins: a blocked or paywalled page is recorded
with its status and the article keeps its headline.

Usage:
  python3 scripts/enrich_ledes.py data/staging/historical/<since>_<until> [--limit N] [--workers 4]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_article_text import BeautifulSoup, _extract_from_html  # noqa: E402

log = logging.getLogger("enrich_ledes")

LEDES_NAME = "_ledes.json"
LEDE_CHARS = 1200
TIMEOUT = 15
BROWSER_UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126 Safari/537.36 SENTINEL-research"
}
GNEWS_BATCH = "https://news.google.com/_/DotsSplashUi/data/batchexecute"
RETRYABLE = {"rate_limited", "fetch_error", "decode_failed"}

_google_lock = threading.Lock()
_google_last = [0.0]
GOOGLE_MIN_INTERVAL = 0.6  # seconds between Google requests across all workers


def _google_wait() -> None:
    with _google_lock:
        delay = GOOGLE_MIN_INTERVAL - (time.monotonic() - _google_last[0])
        if delay > 0:
            time.sleep(delay)
        _google_last[0] = time.monotonic()


def is_google_news_url(url: str) -> bool:
    return "news.google.com/" in (url or "") and "/articles/" in (url or "")


def decode_google_news_url(url: str, session: requests.Session) -> tuple[str | None, str]:
    """Resolve a news.google.com/rss/articles/<id> link to the publisher URL."""
    gid = url.split("/articles/")[1].split("?")[0]
    _google_wait()
    page = session.get(f"https://news.google.com/articles/{gid}", headers=BROWSER_UA, timeout=TIMEOUT)
    if page.status_code == 429:
        return None, "rate_limited"
    sig = re.search(r'data-n-a-sg="([^"]+)"', page.text)
    ts = re.search(r'data-n-a-ts="([^"]+)"', page.text)
    if not (sig and ts):
        return None, "decode_failed"
    inner = (f'["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,null,null,null,null,0,1],'
             f'"X","X",1,[1,1,1],1,1,null,0,0,null,0],"{gid}",{ts.group(1)},"{sig.group(1)}"]')
    body = "f.req=" + quote(json.dumps([[["Fbv4je", inner]]]))
    _google_wait()
    resp = session.post(GNEWS_BATCH, data=body, timeout=TIMEOUT,
                        headers={**BROWSER_UA, "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"})
    if resp.status_code == 429:
        return None, "rate_limited"
    match = re.search(r'\[\\"garturlres\\",\\"(.*?)\\"', resp.text)
    if not match:
        return None, "decode_failed"
    decoded = match.group(1).encode().decode("unicode_escape")
    return decoded, "ok"


def lede_from_html(html: str) -> str:
    """Publisher summary first, then opening paragraphs, capped at LEDE_CHARS."""
    if not BeautifulSoup:
        raise RuntimeError("beautifulsoup4 is required (pip install beautifulsoup4)")
    soup = BeautifulSoup(html, "html.parser")
    summary = ""
    for attrs in ({"property": "og:description"}, {"name": "description"}, {"name": "twitter:description"}):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            summary = re.sub(r"\s+", " ", tag["content"]).strip()
            break
    body = _extract_from_html(html)
    if summary and body.startswith(summary[:60]):
        summary = ""
    text = f"{summary} {body}".strip()
    if len(text) <= LEDE_CHARS:
        return text
    return text[:LEDE_CHARS].rsplit(" ", 1)[0] + "…"


# A bot-challenge or block page returned with HTTP 200. Its text must never be stored
# as an article's opening (14 NACLA pages were, 2026-10-05).
CHALLENGE_PAGE = re.compile(
    r"making sure you're not a bot|made us think that you are a bot|just a moment\.\.\.|checking your browser"
    r"|verify you are (a )?human|are you a robot|enable javascript and cookies to continue",
    re.IGNORECASE,
)


def is_challenge_page(text: str) -> bool:
    return bool(CHALLENGE_PAGE.search(text[:600]))


def _wordpress_apis() -> dict[str, str]:
    """Publisher domain → its public WordPress REST endpoint, for sources that list one."""
    from urllib.parse import urlparse
    from rss_sources import ARCHIVE_SOURCES
    return {urlparse(src["archive_base"]).netloc.removeprefix("www."): src["archive_base"] for src in ARCHIVE_SOURCES}


def lede_from_wordpress_api(publisher_url: str, session: requests.Session) -> str | None:
    """Opening text from the publisher's own REST API (the endpoint the archive connector
    uses), looked up by the post's slug. None when the source has no such endpoint."""
    from urllib.parse import urlparse
    from ingest_rss import USER_AGENT
    parsed = urlparse(publisher_url)
    endpoint = _wordpress_apis().get(parsed.netloc.removeprefix("www."))
    slug = next((part for part in reversed(parsed.path.split("/")) if part), "")
    if not endpoint or not slug:
        return None
    resp = session.get(endpoint, params={"slug": slug, "_fields": "excerpt,content"},
                       headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    if resp.status_code != 200 or "json" not in resp.headers.get("content-type", ""):
        return None
    posts = resp.json()
    if not isinstance(posts, list) or not posts:
        return None
    html = (posts[0].get("content") or {}).get("rendered") or (posts[0].get("excerpt") or {}).get("rendered") or ""
    text = re.sub(r"\s+", " ", BeautifulSoup(html, "html.parser").get_text(" ")).strip()
    if len(text) < 80:
        return None
    return text if len(text) <= LEDE_CHARS else text[:LEDE_CHARS].rsplit(" ", 1)[0] + "…"


def enrich_one(article: dict, session: requests.Session) -> dict:
    url = article.get("url") or ""
    publisher_url, status = url, "ok"
    try:
        if is_google_news_url(url):
            publisher_url, status = decode_google_news_url(url, session)
            if status != "ok":
                return {"status": status}
        page = session.get(publisher_url, headers=BROWSER_UA, timeout=TIMEOUT, allow_redirects=True)
        blocked = page.status_code in (401, 402, 403, 451) or (page.status_code < 400 and is_challenge_page(lede_from_html(page.text)))
        if blocked:
            lede = lede_from_wordpress_api(publisher_url, session)
            if lede:
                return {"status": "ok", "publisher_url": publisher_url, "lede": lede, "via": "wordpress_api"}
            return {"status": "blocked", "publisher_url": publisher_url, "http": page.status_code}
        if page.status_code == 429:
            return {"status": "rate_limited", "publisher_url": publisher_url}
        if page.status_code >= 400:
            return {"status": "fetch_error", "publisher_url": publisher_url, "http": page.status_code}
        lede = lede_from_html(page.text)
        if len(lede) < 80:
            return {"status": "no_text", "publisher_url": publisher_url}
        return {"status": "ok", "publisher_url": publisher_url, "lede": lede}
    except requests.RequestException as exc:
        return {"status": "fetch_error", "publisher_url": publisher_url, "error": str(exc)[:120]}


def gated_articles(run_dir: Path) -> list[dict]:
    """The articles classification will actually see: dedupe, pre-filter, backfill scope gate."""
    import pipeline_core as pc
    logging.getLogger("sentinel").setLevel(logging.WARNING)
    articles = [json.loads(line) for f in sorted(run_dir.glob("*.jsonl"))
                for line in f.read_text(encoding="utf-8").splitlines() if line.strip()]
    return pc.scope_filter_backfill(pc.pre_filter(pc.dedupe_ingested_articles(articles)))


def blocked_sources(ledes: dict, min_tries: int = 5, share: float = 0.8) -> set[str]:
    """Sources whose pages refused at least `share` of at least `min_tries` attempts.
    Fetching them again only spends Google decode requests on pages we cannot read."""
    tries, blocked = Counter(), Counter()
    for entry in ledes.values():
        source = entry.get("source")
        if entry.get("status") in ("ok", "blocked", "no_text"):
            tries[source] += 1
            blocked[source] += entry.get("status") == "blocked"
    return {s for s, n in tries.items() if n >= min_tries and blocked[s] / n >= share}


def load_ledes(run_dir: Path) -> dict:
    path = run_dir / LEDES_NAME
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_ledes(run_dir: Path, ledes: dict) -> None:
    path = run_dir / LEDES_NAME
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(ledes, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def apply_ledes(articles: list[dict], run_dir: Path) -> int:
    """Merge stored ledes into article records (used by run_pipeline --from-staging)."""
    ledes = load_ledes(run_dir)
    applied = 0
    for article in articles:
        entry = ledes.get(article.get("article_id") or "")
        if entry and entry.get("status") == "ok" and entry.get("lede"):
            article["description"] = entry["lede"]
            article["publisher_url"] = entry.get("publisher_url")
            applied += 1
    return applied


def main() -> None:
    global GOOGLE_MIN_INTERVAL
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--limit", type=int, default=None, help="Only process this many pending articles")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--ids", type=Path, default=None,
                        help="JSONL of article records to enrich instead of every gated article (e.g. the gold-set candidates)")
    parser.add_argument("--gate-relevant", action="store_true",
                        help="Only enrich articles the headline gate (_gate.json) marked relevant")
    parser.add_argument("--google-interval", type=float, default=GOOGLE_MIN_INTERVAL,
                        help="Seconds between Google requests across workers (raise it if Google returns 429)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    GOOGLE_MIN_INTERVAL = args.google_interval

    ledes = load_ledes(args.run_dir)
    targets = ([json.loads(line) for line in args.ids.read_text(encoding="utf-8").splitlines() if line.strip()]
               if args.ids else gated_articles(args.run_dir))
    gate_path = args.run_dir / "_gate.json"
    if args.gate_relevant and gate_path.exists():
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        targets = [a for a in targets if gate.get(a.get("article_id"), {}).get("relevant")]
    skip = blocked_sources(ledes)
    if skip:
        log.info(f"Skipping sources that block nearly every request: {sorted(skip)}")
    pending = [a for a in targets if a.get("article_id") and a.get("source") not in skip and
               (a["article_id"] not in ledes or ledes[a["article_id"]].get("status") in RETRYABLE)]
    if args.limit:
        pending = pending[:args.limit]
    log.info(f"{len(targets)} gated articles; {len(pending)} to enrich")

    session = requests.Session()
    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(enrich_one, a, session): a for a in pending}
        for fut in as_completed(futures):
            article = futures[fut]
            ledes[article["article_id"]] = {**fut.result(), "source": article.get("source")}
            done += 1
            if done % 50 == 0:
                save_ledes(args.run_dir, ledes)
                log.info(f"{done}/{len(pending)} · {dict(Counter(v['status'] for v in ledes.values()))}")
    save_ledes(args.run_dir, ledes)
    stats = Counter(v["status"] for v in ledes.values())
    by_source = Counter((v.get("source"), v["status"]) for v in ledes.values())
    log.info(f"Done. {dict(stats)}")
    for (source, status), n in sorted(by_source.items(), key=lambda x: -x[1])[:25]:
        log.info(f"  {source}: {status} × {n}")


if __name__ == "__main__":
    main()
