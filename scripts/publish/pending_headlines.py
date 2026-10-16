"""Public list of collected headlines that could not be coded because the model API was unavailable.

When the Anthropic API refuses requests (no credit, revoked key, account disabled), the nightly
run cannot classify anything. Rather than publish nothing, the pipeline writes the keyword-filtered
headlines it collected to data/published/pending_headlines.json, and the public site shows them as
"collected, not yet coded". They never enter data/events.json: once the API works again, the
catch-up lookback (up to 10 days) collects the same articles and codes them normally, and the next
successful run removes this file.

Only public-safe fields are written: headline, link, source name, date and a country guessed from
the headline. No article text is republished.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PENDING_FILE = ROOT / "data" / "published" / "pending_headlines.json"
COUNTRIES_FILE = ROOT / "config" / "taxonomy" / "countries.json"
MAX_HEADLINES = 300

# The 25 monitored countries, with Spanish, Portuguese and French spellings for headlines in those languages.
_ALIASES = {
    "Mexico": ["México"], "Peru": ["Perú"], "Panama": ["Panamá"], "Haiti": ["Haití", "Haïti"],
    "Brazil": ["Brasil"], "Dominican Republic": ["República Dominicana", "Rep. Dominicana"],
    "Trinidad and Tobago": ["Trinidad y Tobago", "Trinidad"], "Belize": ["Belice"], "Suriname": ["Surinam"],
    "Colombia": [], "Venezuela": [], "Ecuador": [], "Bolivia": [], "Chile": [], "Argentina": [],
    "Paraguay": [], "Uruguay": [], "Honduras": [], "Guatemala": [], "El Salvador": [], "Nicaragua": [],
    "Costa Rica": [], "Cuba": [], "Jamaica": [], "Guyana": [],
}


def _country_patterns() -> list[tuple[str, re.Pattern]]:
    # The monitored countries only: the taxonomy also lists "Regional" and some unmonitored states.
    names = [n for n in json.loads(COUNTRIES_FILE.read_text(encoding="utf-8"))["countries"] if n in _ALIASES]
    out = []
    for name in names:
        forms = [name, *_ALIASES.get(name, [])]
        out.append((name, re.compile(r"\b(" + "|".join(re.escape(f) for f in forms) + r")\b", re.IGNORECASE)))
    return out


def guess_country(text: str, patterns: list[tuple[str, re.Pattern]]) -> str | None:
    """The single country a headline names, or None when it names none or several."""
    hits = {name for name, pattern in patterns if pattern.search(text or "")}
    return hits.pop() if len(hits) == 1 else None


def is_api_unavailable(exc: BaseException) -> bool:
    """True when the model API refuses every request for account reasons, not for one bad input."""
    try:
        import anthropic
    except ImportError:  # pragma: no cover - the pipeline always has the SDK
        return False
    if isinstance(exc, (anthropic.AuthenticationError, anthropic.PermissionDeniedError)):
        return True
    message = str(exc).lower()
    return isinstance(exc, anthropic.BadRequestError) and ("credit balance" in message or "billing" in message)


def write_pending(articles: list[dict], reason: str, path: Path = PENDING_FILE) -> int:
    """Write the public pending list from pre-filtered articles; returns how many were written."""
    patterns = _country_patterns()
    seen, rows = set(), []
    for article in sorted(articles, key=lambda a: a.get("date") or "", reverse=True):
        title = (article.get("title") or "").strip()
        url = article.get("url") or ""
        key = url or title.lower()
        if not title or not url.startswith("http") or key in seen:
            continue
        seen.add(key)
        rows.append({
            "title": title,
            "url": url,
            "source": article.get("source") or "",
            "date": article.get("date") or "",
            "country": guess_country(title, patterns),
        })
        if len(rows) >= MAX_HEADLINES:
            break
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "note": "Collected and keyword-filtered, but not yet coded or checked. Countries are guessed from the headline.",
        "headlines": rows,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return len(rows)


def clear_pending(path: Path = PENDING_FILE) -> bool:
    """Remove the pending list after a run that coded normally; returns whether there was one."""
    if path.exists():
        path.unlink()
        return True
    return False
