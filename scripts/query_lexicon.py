"""
Utilities for working with SENTINEL's centralized event-query lexicon.

This module keeps retrieval and pre-filter logic sourced from one registry so
the pipeline, NewsAPI discovery, and Google News source wrappers can evolve
from the same analytical vocabulary.
"""

from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEXICON_PATH = ROOT / "config" / "queries" / "event_query_lexicon.json"

DEFAULT_PREFILTER_FAMILIES = (
    "armed_conflict_and_territorial_control",
    "organized_crime_and_transnational_security",
    "criminal_violence_and_illicit_economies",
    "state_repression_and_exceptional_rule",
    "security_sector_reform_and_oversight",
    "external_security_support_and_alignment",
    "military_exercises_and_force_posture",
    "procurement_and_arms",
    "peace_process_and_ddr",
    "corruption_capture_and_judicial_pressure",
    "border_tension_and_sovereignty",
    "coup_and_command_break",
)

DEFAULT_NEWSAPI_BUNDLES = {
    "crime": (
        "organized_crime_and_transnational_security",
        "criminal_violence_and_illicit_economies",
    ),
    "conflict": (
        "armed_conflict_and_territorial_control",
        "border_tension_and_sovereignty",
    ),
    "governance": (
        "state_repression_and_exceptional_rule",
        "security_sector_reform_and_oversight",
        "corruption_capture_and_judicial_pressure",
        "coup_and_command_break",
    ),
    "external": (
        "external_security_support_and_alignment",
        "military_exercises_and_force_posture",
        "procurement_and_arms",
        "peace_process_and_ddr",
    ),
}


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("’", "'")
    return " ".join(text.split())


@lru_cache(maxsize=1)
def load_lexicon() -> dict:
    return json.loads(LEXICON_PATH.read_text(encoding="utf-8"))


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        normalized = normalize_text(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out


def get_country_terms(scope: str = "core_pipeline") -> list[str]:
    lexicon = load_lexicon()
    countries = lexicon.get("country_scope_sets", {}).get(scope, [])
    aliases = lexicon.get("country_aliases", {})
    terms: list[str] = []
    for country in countries:
        country_terms = aliases.get(country, {}).get("terms", {})
        for language_terms in country_terms.values():
            terms.extend(language_terms or [])
        terms.append(country)
    regional = lexicon.get("regional_terms", {})
    for language_terms in regional.values():
        terms.extend(language_terms or [])
    return _unique(terms)


def get_negative_terms() -> list[str]:
    lexicon = load_lexicon()
    negatives = lexicon.get("negative_filters", {})
    terms: list[str] = []
    for value in negatives.values():
        if isinstance(value, dict):
            for key, entries in value.items():
                if key == "description":
                    continue
                terms.extend(entries or [])
    return _unique(terms)


def get_actor_terms(actor_set_names: tuple[str, ...] | list[str] | None = None) -> list[str]:
    lexicon = load_lexicon()
    actor_sets = lexicon.get("actor_alias_sets", {})
    names = actor_set_names or tuple(actor_sets.keys())
    terms: list[str] = []
    for name in names:
        aliases = actor_sets.get(name, {}).get("aliases", [])
        terms.extend(aliases or [])
    return _unique(terms)


def get_term_set_terms(term_set_names: tuple[str, ...] | list[str]) -> list[str]:
    lexicon = load_lexicon()
    term_sets = lexicon.get("term_sets", {})
    terms: list[str] = []
    for name in term_set_names:
        value = term_sets.get(name, {})
        if isinstance(value, dict):
            for key, entries in value.items():
                if key == "description":
                    continue
                terms.extend(entries or [])
    return _unique(terms)


def get_query_family_terms(
    family_names: tuple[str, ...] | list[str],
    *,
    include_high_signal: bool = True,
) -> dict[str, list[str]]:
    lexicon = load_lexicon()
    families = lexicon.get("query_families", {})
    out: dict[str, list[str]] = {}
    for family_name in family_names:
        family = families.get(family_name, {})
        terms: list[str] = []
        terms.extend(get_term_set_terms(tuple(family.get("include_term_sets", []))))
        terms.extend(get_actor_terms(tuple(family.get("include_actor_sets", []))))
        if include_high_signal:
            for language_terms in family.get("high_signal_terms", {}).values():
                terms.extend(language_terms or [])
        out[family_name] = _unique(terms)
    return out


def get_prefilter_term_map(
    family_names: tuple[str, ...] | list[str] = DEFAULT_PREFILTER_FAMILIES,
) -> dict[str, list[str]]:
    families = get_query_family_terms(family_names)
    families["__geography__"] = get_country_terms()
    families["__negative__"] = get_negative_terms()
    return families


def build_newsapi_query(
    family_names: tuple[str, ...] | list[str],
    *,
    language: str,
    country_scope: str = "core_pipeline",
    max_terms: int = 10,
    max_country_terms: int = 12,
) -> str:
    lexicon = load_lexicon()
    families = lexicon.get("query_families", {})
    country_aliases = lexicon.get("country_aliases", {})
    country_terms: list[str] = []
    for country in lexicon.get("country_scope_sets", {}).get(country_scope, []):
        entry = country_aliases.get(country, {}).get("terms", {})
        country_terms.extend((entry.get(language) or entry.get("en") or [])[:1])

    query_terms: list[str] = []
    for family_name in family_names:
        family = families.get(family_name, {})
        for term_set_name in family.get("include_term_sets", []):
            term_set = lexicon.get("term_sets", {}).get(term_set_name, {})
            query_terms.extend((term_set.get(language) or term_set.get("en") or [])[:3])
        query_terms.extend((family.get("high_signal_terms", {}).get(language) or family.get("high_signal_terms", {}).get("en") or [])[:3])
        for actor_set_name in family.get("include_actor_sets", []):
            query_terms.extend(get_actor_terms([actor_set_name])[:4])

    query_terms = _unique(query_terms)[:max_terms]
    country_terms = _unique(country_terms)[:max_country_terms]
    if not query_terms or not country_terms:
        return ""

    term_expr = " OR ".join(f'"{term}"' if " " in term else term for term in query_terms)
    country_expr = " OR ".join(f'"{term}"' if " " in term else term for term in country_terms)
    return f"({term_expr}) AND ({country_expr})"


def build_google_news_terms(
    family_names: tuple[str, ...] | list[str],
    *,
    language: str = "es",
    include_countries: tuple[str, ...] | list[str] | None = None,
    max_terms: int = 8,
    max_country_terms: int = 4,
) -> str:
    lexicon = load_lexicon()
    families = lexicon.get("query_families", {})
    terms: list[str] = []
    for family_name in family_names:
        family = families.get(family_name, {})
        for term_set_name in family.get("include_term_sets", []):
            term_set = lexicon.get("term_sets", {}).get(term_set_name, {})
            terms.extend((term_set.get(language) or term_set.get("en") or [])[:2])
        terms.extend((family.get("high_signal_terms", {}).get(language) or family.get("high_signal_terms", {}).get("en") or [])[:2])
    terms = _unique(terms)[:max_terms]

    country_terms: list[str] = []
    if include_countries:
        country_aliases = lexicon.get("country_aliases", {})
        for country in include_countries:
            entry = country_aliases.get(country, {}).get("terms", {})
            country_terms.extend((entry.get(language) or entry.get("en") or [])[:1])
        country_terms = _unique(country_terms)[:max_country_terms]

    all_terms = terms + country_terms
    compact = []
    for term in all_terms:
        cleaned = term.replace(" ", "+")
        compact.append(cleaned)
    return "+OR+".join(compact)


def infer_article_query_families(text: str, *, minimum_hits: int = 2) -> list[str]:
    lowered = normalize_text(text)
    if not lowered:
        return []
    family_terms = get_query_family_terms(DEFAULT_PREFILTER_FAMILIES)
    matches: list[tuple[str, int]] = []
    for family, terms in family_terms.items():
        hits = sum(1 for term in terms if term and term in lowered)
        if hits >= minimum_hits:
            matches.append((family, hits))
    matches.sort(key=lambda item: (-item[1], item[0]))
    return [family for family, _ in matches]
