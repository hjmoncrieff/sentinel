#!/usr/bin/env python3
"""
Build a first private/internal episode layer from reviewed SENTINEL events.

This stage is intentionally conservative. It clusters related events into
bounded episodes so the modeling layer can begin to reason about sequences,
not only raw event counts.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
EVENTS = ROOT / "data" / "review" / "events_with_edits.json"
OUT = ROOT / "data" / "modeling" / "episodes.json"

MAX_GAP_DAYS = 21

HUMAN_REVIEW_STATUSES = {
    "analyst_reviewed",
    "coordinator_approved",
    "published",
    "ra_reviewed",
    "reviewed",
}


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError:
        return None


def normalize_confidence(value: str | None) -> str:
    text = str(value or "").strip().lower()
    if text in {"high", "green"}:
        return "high"
    if text in {"medium", "med", "yellow"}:
        return "medium"
    return "low"


def is_human_reviewed(event: dict[str, Any]) -> bool:
    if event.get("human_validated"):
        return True
    return str(event.get("review_status") or "").strip().lower() in HUMAN_REVIEW_STATUSES


def salience_weight(value: str | None) -> float:
    text = str(value or "").strip().lower()
    if text == "high":
        return 1.0
    if text == "medium":
        return 0.7
    return 0.35


def confidence_weight(value: str | None) -> float:
    text = normalize_confidence(value)
    return {"high": 1.0, "medium": 0.8, "low": 0.55}.get(text, 0.55)


def episode_type_for_event(event: dict[str, Any]) -> str:
    event_type = str(event.get("event_type") or "").strip().lower()
    deed_type = str(event.get("deed_type") or "").strip().lower()
    axis = str(event.get("axis") or "").strip().lower()

    if event_type == "coup":
        return "irregular_transition_episode"
    if event_type == "purge":
        return "elite_security_reordering"
    if event_type in {"protest", "conflict"}:
        if deed_type == "destabilizing":
            return "destabilization_episode"
        return "protest_security_escalation"
    if event_type == "oc":
        return "coercive_fragmentation_episode"
    if event_type in {"aid", "exercise", "procurement", "coop"}:
        return "external_security_alignment_episode"
    if event_type == "reform":
        if axis == "vertical":
            return "institutional_reordering_episode"
        return "governance_reform_episode"
    if deed_type in {"symptom", "precursor", "destabilizing"}:
        return "institutional_erosion_episode"
    return "general_security_episode"


def construct_links_for_episode_type(episode_type: str) -> list[str]:
    mapping = {
        "irregular_transition_episode": ["regime_vulnerability", "militarization"],
        "elite_security_reordering": ["regime_vulnerability", "militarization"],
        "destabilization_episode": ["regime_vulnerability", "security_fragmentation"],
        "protest_security_escalation": ["regime_vulnerability", "security_fragmentation"],
        "coercive_fragmentation_episode": ["security_fragmentation"],
        "external_security_alignment_episode": ["militarization"],
        "institutional_reordering_episode": ["regime_vulnerability", "militarization"],
        "governance_reform_episode": ["regime_vulnerability"],
        "institutional_erosion_episode": ["regime_vulnerability"],
        "general_security_episode": ["security_fragmentation"],
    }
    return mapping.get(episode_type, ["security_fragmentation"])


def process_type_for_episode(episode_type: str) -> str:
    if episode_type in {"irregular_transition_episode", "elite_security_reordering", "institutional_erosion_episode", "destabilization_episode"}:
        return "authoritarian_consolidation"
    if episode_type in {"external_security_alignment_episode", "institutional_reordering_episode"}:
        return "military_governance_expansion"
    if episode_type in {"coercive_fragmentation_episode", "protest_security_escalation", "general_security_episode"}:
        return "security_fragmentation"
    return "institutional_erosion"


def process_cluster_key(event: dict[str, Any]) -> str:
    return process_type_for_episode(episode_type_for_event(event))


def dominant_actor_set(events: list[dict[str, Any]]) -> list[str]:
    counter: Counter[str] = Counter()
    for event in events:
        actors = event.get("actors") or []
        if isinstance(actors, list):
            for actor in actors:
                label = str(
                    actor.get("actor_canonical_name")
                    or actor.get("actor_primary_name")
                    or actor.get("name")
                    or actor.get("actor_name")
                    or ""
                ).strip()
                if label:
                    counter[label] += 1
        for field in ("actor_primary_name", "actor_secondary_name"):
            label = str(event.get(field) or "").strip()
            if label:
                counter[label] += 1
    return [label for label, _count in counter.most_common(4)]


def dominant_mechanism(events: list[dict[str, Any]], episode_type: str) -> str:
    deed_counter = Counter(
        str(event.get("deed_type") or "").strip().lower()
        for event in events
        if str(event.get("deed_type") or "").strip()
    )
    if deed_counter:
        deed = deed_counter.most_common(1)[0][0]
        if deed == "destabilizing":
            return "destabilizing escalation"
        if deed == "symptom":
            return "institutional erosion symptom"
        if deed == "precursor":
            return "precursor stress signal"
    fallback = {
        "irregular_transition_episode": "irregular transition pressure",
        "elite_security_reordering": "elite-security reordering",
        "coercive_fragmentation_episode": "coercive fragmentation",
        "external_security_alignment_episode": "external security alignment shift",
    }
    return fallback.get(episode_type, "security and governance stress")


def episode_direction(events: list[dict[str, Any]]) -> str:
    high_count = sum(1 for event in events if str(event.get("salience") or "").strip().lower() == "high")
    deed_types = {str(event.get("deed_type") or "").strip().lower() for event in events if event.get("deed_type")}
    if high_count >= 2 or "destabilizing" in deed_types:
        return "escalating"
    if any(str(event.get("event_type") or "").strip().lower() == "oc" for event in events):
        return "fragmenting"
    if any(str(event.get("event_type") or "").strip().lower() in {"reform", "procurement", "aid", "exercise", "coop"} for event in events):
        return "institutionalizing"
    return "stabilizing"


def episode_severity(events: list[dict[str, Any]]) -> str:
    score = 0.0
    high_salience_count = 0
    destabilizing_count = 0
    for event in events:
        salience = str(event.get("salience") or "").strip().lower()
        deed_type = str(event.get("deed_type") or "").strip().lower()
        score += salience_weight(event.get("salience")) * confidence_weight(event.get("confidence"))
        if salience == "high":
            high_salience_count += 1
            score += 0.45
        if deed_type == "destabilizing":
            destabilizing_count += 1
            score += 0.35
    if len(events) >= 3:
        score += 0.6
    if high_salience_count >= 2:
        score += 0.8
    if destabilizing_count >= 2:
        score += 0.7
    if any(str(event.get("event_type") or "").strip().lower() == "coup" for event in events):
        score += 2.0
    if any(str(event.get("deed_type") or "").strip().lower() == "destabilizing" for event in events):
        score += 0.8
    if score >= 5.2:
        return "high"
    if score >= 2.8:
        return "medium"
    return "low"


def episode_status(end_date: datetime, now: datetime) -> str:
    age_days = max((now - end_date).days, 0)
    if age_days <= 14:
        return "active"
    if age_days <= 35:
        return "stabilizing"
    return "closed"


def process_relevance(severity: str, construct_links: list[str], event_count: int) -> str:
    if severity == "high" or (len(construct_links) >= 2 and event_count >= 3):
        return "high"
    if severity == "medium" or event_count >= 2:
        return "medium"
    return "low"


def episode_title(country: str, episode_type: str, events: list[dict[str, Any]]) -> str:
    labels = {
        "irregular_transition_episode": "Irregular Transition Episode",
        "elite_security_reordering": "Elite-Security Reordering",
        "destabilization_episode": "Destabilization Episode",
        "protest_security_escalation": "Protest-Security Escalation",
        "coercive_fragmentation_episode": "Coercive Fragmentation Episode",
        "external_security_alignment_episode": "External Security Alignment Episode",
        "institutional_reordering_episode": "Institutional Reordering Episode",
        "governance_reform_episode": "Governance Reform Episode",
        "institutional_erosion_episode": "Institutional Erosion Episode",
        "general_security_episode": "Security Episode",
    }
    base = labels.get(episode_type, "Security Episode")
    earliest = min((parse_date(event.get("event_date")) for event in events), default=None)
    if earliest is None:
        return f"{country} {base}"
    return f"{country} {base} ({earliest.strftime('%Y-%m')})"


def dominant_episode_type(events: list[dict[str, Any]]) -> str:
    counter = Counter(episode_type_for_event(event) for event in events)
    return counter.most_common(1)[0][0] if counter else "general_security_episode"


def load_events() -> list[dict[str, Any]]:
    payload = load_json(EVENTS)
    rows = payload.get("events", []) if isinstance(payload, dict) else payload
    out = []
    for event in rows:
        if str(event.get("country") or "").strip() in {"", "Regional"}:
            continue
        if str(event.get("duplicate_status") or "").strip().lower() == "merged":
            continue
        if parse_date(event.get("event_date")) is None:
            continue
        out.append(event)
    return out


def build_episodes(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in sorted(events, key=lambda item: (str(item.get("country") or ""), str(item.get("event_date") or ""), str(item.get("event_id") or ""))):
        country = str(event.get("country") or "").strip()
        grouped[(country, process_cluster_key(event))].append(event)

    now = datetime.now(UTC)
    episodes: list[dict[str, Any]] = []

    for (country, process_type), items in grouped.items():
        cluster: list[dict[str, Any]] = []
        cluster_start: datetime | None = None
        cluster_end: datetime | None = None
        cluster_index = 0

        for event in items:
            event_dt = parse_date(event.get("event_date"))
            if event_dt is None:
                continue
            if not cluster:
                cluster = [event]
                cluster_start = event_dt
                cluster_end = event_dt
                continue
            gap = (event_dt - cluster_end).days if cluster_end else MAX_GAP_DAYS + 1
            if gap <= MAX_GAP_DAYS:
                cluster.append(event)
                cluster_end = event_dt
                continue

            cluster_index += 1
            episodes.append(finalize_episode(country, process_type, cluster_index, cluster, cluster_start, cluster_end, now))
            cluster = [event]
            cluster_start = event_dt
            cluster_end = event_dt

        if cluster:
            cluster_index += 1
            episodes.append(finalize_episode(country, process_type, cluster_index, cluster, cluster_start, cluster_end, now))

    episodes.sort(key=lambda item: (item["country"], item["episode_start"], item["episode_id"]))
    return episodes


def finalize_episode(
    country: str,
    process_type: str,
    cluster_index: int,
    events: list[dict[str, Any]],
    start_dt: datetime | None,
    end_dt: datetime | None,
    now: datetime,
) -> dict[str, Any]:
    episode_type = dominant_episode_type(events)
    severity = episode_severity(events)
    links = construct_links_for_episode_type(episode_type)
    start_text = start_dt.strftime("%Y-%m-%d") if start_dt else None
    end_text = end_dt.strftime("%Y-%m-%d") if end_dt else None
    event_ids = [str(event.get("event_id") or event.get("id") or "") for event in events if event.get("event_id") or event.get("id")]
    high_salience = sum(1 for event in events if str(event.get("salience") or "").strip().lower() == "high")
    role_rows = []
    for index, event in enumerate(events):
        role = "reinforcing"
        if index == 0:
            role = "trigger"
        elif severity == "high" and str(event.get("salience") or "").strip().lower() == "high":
            role = "turning_point"
        elif str(event.get("salience") or "").strip().lower() == "low":
            role = "background"
        role_rows.append({
            "event_id": str(event.get("event_id") or event.get("id") or ""),
            "event_date": str(event.get("event_date") or ""),
            "event_type": str(event.get("event_type") or ""),
            "episode_role": role,
            "process_relevance": process_relevance(severity, links, len(events)),
        })

    episode_id = f"ep_{country.lower().replace(' ', '_')}_{episode_type}_{cluster_index:03d}"
    process_id = f"proc_{country.lower().replace(' ', '_')}_{process_type}"
    direction = episode_direction(events)

    return {
        "episode_id": episode_id,
        "country": country,
        "episode_type": episode_type,
        "episode_title": episode_title(country, episode_type, events),
        "episode_status": episode_status(end_dt or now, now),
        "episode_start": start_text,
        "episode_end_estimate": end_text,
        "linked_event_ids": event_ids,
        "event_roles": role_rows,
        "event_count": len(events),
        "high_salience_event_count": high_salience,
        "human_reviewed_event_count": sum(1 for event in events if is_human_reviewed(event)),
        "human_validated_event_count": sum(1 for event in events if event.get("human_validated")),
        "dominant_actor_set": dominant_actor_set(events),
        "dominant_mechanism": dominant_mechanism(events, episode_type),
        "episode_direction": direction,
        "episode_severity": severity,
        "process_id": process_id,
        "process_type": process_type,
        "construct_links": links,
        "process_relevance": process_relevance(severity, links, len(events)),
        "summary_text": (
            f"{country} {episode_type.replace('_', ' ')} with {len(events)} linked events, "
            f"{high_salience} high-salience events, and a {severity} severity profile."
        ),
    }


def main() -> None:
    events = load_events()
    episodes = build_episodes(events)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_internal_episode_artifact",
        "description": (
            "First conservative internal episode layer built from reviewed events. "
            "This stage clusters related events into bounded episodes for use in "
            "private modeling and later process detection."
        ),
        "source_file": str(EVENTS.relative_to(ROOT)),
        "episode_gap_days": MAX_GAP_DAYS,
        "count": len(episodes),
        "countries": sorted({episode["country"] for episode in episodes}),
        "episodes": episodes,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(episodes)} episodes to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
