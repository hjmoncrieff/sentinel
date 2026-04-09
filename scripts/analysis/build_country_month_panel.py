#!/usr/bin/env python3
"""
Build the first private SENTINEL country-month modeling panel.

Outputs:
  data/modeling/country_month_panel.json
  data/modeling/country_month_panel.csv

This artifact is intentionally private/internal. It is a modeling layer that
connects structural annual data with monthly event-derived pulse features and
first-pass proxy targets for future predictive modeling.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
COUNTRY_YEAR = ROOT / "data" / "cleaned" / "country_year.json"
EVENTS = ROOT / "data" / "review" / "events_with_edits.json"
EPISODES = ROOT / "data" / "modeling" / "episodes.json"
ADJUDICATED_TARGETS = ROOT / "data" / "modeling" / "adjudicated_irregular_transition_labels.json"
GOLD_TARGETS = ROOT / "data" / "modeling" / "gold_irregular_transition_labels.json"
FEATURE_CONTRACT = ROOT / "config" / "modeling" / "panel_feature_contract.json"
EXTERNAL_ECON_SIGNALS = ROOT / "data" / "modeling" / "external_economic_country_month.json"
MANUAL_SIGNALS_TEMPLATE = ROOT / "data" / "modeling" / "manual_country_month_signals.template.json"
BENCHMARK_SIGNALS = ROOT / "data" / "modeling" / "benchmark_country_month_signals.json"
MANUAL_SIGNALS_LOCAL = ROOT / "data" / "modeling" / "manual_country_month_signals.local.json"
OUT_JSON = ROOT / "data" / "modeling" / "country_month_panel.json"
OUT_CSV = ROOT / "data" / "modeling" / "country_month_panel.csv"

STRUCTURAL_FIELDS = [
    "polyarchy",
    "liberal_democracy",
    "participatory_democracy",
    "deliberative_democracy",
    "egalitarian_democracy",
    "regime_type",
    "physinteg",
    "mil_constrain",
    "mil_exec",
    "exec_confidence",
    "judicial_constraints",
    "legislative_constraints",
    "rule_of_law_vdem",
    "public_sector_corruption",
    "executive_corruption",
    "corruption_index",
    "clientelism",
    "civil_society_participation",
    "party_institutionalization",
    "state_authority",
    "coup_total_events",
    "coup_event",
    "coup_attempts",
    "executive_direct_election",
    "election_repression",
    "voter_turnout",
    "democracy_breakdown",
    "democracy_transition",
    "polity2",
    "cs_repress",
    "political_violence",
    "mil_exp_pct_gdp",
    "mil_exp_usd",
    "mil_personnel",
    "wgi_rule_of_law",
    "wgi_govt_effectiveness",
    "wgi_control_corruption",
    "wgi_political_stability",
    "gdp_const_2015_usd",
    "gdp_per_capita_const_usd",
    "inflation_consumer_prices_pct",
    "real_interest_rate",
    "official_exchange_rate",
    "fdi_net_inflows_pct_gdp",
    "debt_service_pct_exports",
    "current_account_pct_gdp",
    "reserves_months_imports",
    "resource_rents_pct_gdp",
    "trade_openness_pct_gdp",
    "oda_received_pct_gni",
    "population",
    "m3_conscription",
    "m3_mil_veto",
    "m3_mil_impunity",
    "m3_mil_crime_police",
    "m3_mil_eco",
    "m3_hwi",
    "state_capacity_composite",
    "state_capacity_coverage",
    "time_since_last_coup",
    "time_since_last_coup_attempt",
    "coup_count_5y",
    "coup_attempt_count_5y",
    "coup_count_10y",
    "coup_attempt_count_10y",
    "polyarchy_delta_1y",
    "polyarchy_delta_3y",
    "mil_exec_delta_1y",
    "cs_repress_delta_1y",
    "state_capacity_delta_3y",
    "inflation_delta_1y",
    "trade_openness_delta_3y",
    "oda_received_delta_3y",
    "voter_turnout_delta_1y",
    "regime_shift_flag",
    "repression_shift_flag",
    "macro_stress_shift_flag",
]

EVENT_TYPE_FIELDS = [
    "aid",
    "conflict",
    "coup",
    "exercise",
    "oc",
    "other",
    "peace",
    "procurement",
    "protest",
    "purge",
    "reform",
]

DEED_TYPE_FIELDS = [
    "destabilizing",
    "precursor",
    "resistance",
    "symptom",
]

AXIS_FIELDS = [
    "horizontal",
    "vertical",
]

HUMAN_REVIEW_STATUSES = {
    "analyst_reviewed",
    "coordinator_approved",
    "published",
    "ra_reviewed",
    "reviewed",
}

TARGET_RULE_VERSION = "proxy_irregular_transition_v6"
FIT_TARGET_RULE_VERSION = "proxy_irregular_transition_fit_v1"
ACUTE_POLITICAL_RISK_RULE_VERSION = "proxy_acute_political_risk_v1"
SECURITY_FRAGMENTATION_JUMP_RULE_VERSION = "proxy_security_fragmentation_jump_v2"
TARGET_POSITIVE_EVENT_TYPES = {"coup"}
TARGET_POSITIVE_DEED_TYPES = {"destabilizing"}
TARGET_POSITIVE_REVIEW_STATES = {"human_reviewed", "human_validated", "machine_only"}

EXTERNAL_ECONOMIC_FIELDS = [
    "external_pressure_sanctions_active",
    "external_pressure_sanctions_delta",
    "external_pressure_imf_program_active",
    "external_pressure_imf_program_break",
    "external_pressure_us_security_shift",
    "economic_fragility_inflation_stress",
    "economic_fragility_fx_stress",
    "economic_fragility_debt_stress",
    "economic_policy_capital_controls_flag",
    "economic_policy_nationalization_signal",
]

EPISODE_TYPES = [
    "coercive_fragmentation_episode",
    "destabilization_episode",
    "elite_security_reordering",
    "external_security_alignment_episode",
    "general_security_episode",
    "governance_reform_episode",
    "institutional_erosion_episode",
    "institutional_reordering_episode",
    "irregular_transition_episode",
    "protest_security_escalation",
]

EPISODE_SEVERITIES = ["high", "medium", "low"]

EPISODE_CONSTRUCTS = [
    "regime_vulnerability",
    "militarization",
    "security_fragmentation",
]


@dataclass(frozen=True)
class MonthKey:
    country: str
    year: int
    month: int
    iso3: str

    @property
    def panel_date(self) -> str:
        return f"{self.year:04d}-{self.month:02d}-01"

    @property
    def ym(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_year_month(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    try:
        dt = datetime.strptime(str(value)[:10], "%Y-%m-%d")
    except ValueError:
        return None
    return dt.year, dt.month


def event_confidence_bucket(value: str | None) -> str:
    text = str(value or "").strip().lower()
    if text in {"high", "green"}:
        return "high"
    if text in {"medium", "med", "yellow"}:
        return "medium"
    return "low"


def is_human_reviewed(event: dict) -> bool:
    if event.get("human_validated"):
        return True
    return str(event.get("review_status") or "").strip().lower() in HUMAN_REVIEW_STATUSES


def review_state_bucket(event: dict) -> str:
    if event.get("human_validated"):
        return "human_validated"
    if is_human_reviewed(event):
        return "human_reviewed"
    return "machine_only"


def load_country_year_rows() -> list[dict]:
    payload = load_json(COUNTRY_YEAR)
    return payload.get("rows", []) if isinstance(payload, dict) else payload


def load_events() -> list[dict]:
    payload = load_json(EVENTS)
    return payload.get("events", []) if isinstance(payload, dict) else payload


def load_episodes() -> list[dict]:
    if not EPISODES.exists():
        return []
    payload = load_json(EPISODES)
    return payload.get("episodes", []) if isinstance(payload, dict) else payload


def load_adjudicated_targets() -> dict[tuple[str, str], dict]:
    if not ADJUDICATED_TARGETS.exists():
        return {}
    payload = load_json(ADJUDICATED_TARGETS)
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    out: dict[tuple[str, str], dict] = {}
    for row in rows:
        country = str(row.get("country") or "").strip()
        panel_date = str(row.get("panel_date") or "").strip()
        target_name = str(row.get("target_name") or "").strip()
        if not country or not panel_date or target_name != "irregular_transition_next_1m":
            continue
        out[(country, panel_date)] = row
    return out


def load_gold_targets() -> dict[tuple[str, str], dict]:
    if not GOLD_TARGETS.exists():
        return {}
    payload = load_json(GOLD_TARGETS)
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    out: dict[tuple[str, str], dict] = {}
    for row in rows:
        country = str(row.get("country") or "").strip()
        panel_date = str(row.get("panel_date") or "").strip()
        target_name = str(row.get("target_name") or "").strip()
        if not country or not panel_date or target_name != "irregular_transition_next_1m":
            continue
        out[(country, panel_date)] = row
    return out


def load_feature_contract() -> dict:
    if not FEATURE_CONTRACT.exists():
        return {}
    payload = load_json(FEATURE_CONTRACT)
    return payload if isinstance(payload, dict) else {}


def rows_to_country_month_map(rows: list[dict]) -> dict[tuple[str, str], dict]:
    out: dict[tuple[str, str], dict] = {}
    for row in rows:
        country = str(row.get("country") or "").strip()
        panel_date = str(row.get("panel_date") or "").strip()
        if not country or not panel_date:
            continue
        out[(country, panel_date)] = row
    return out


def load_external_economic_signal_rows() -> tuple[list[str], dict[tuple[str, str], dict]]:
    if not EXTERNAL_ECON_SIGNALS.exists():
        return [], {}
    payload = load_json(EXTERNAL_ECON_SIGNALS)
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    sources = payload.get("source_files", []) if isinstance(payload, dict) else []
    return [str(EXTERNAL_ECON_SIGNALS.relative_to(ROOT)), *sources], rows_to_country_month_map(rows)


def load_seeded_country_month_signals() -> tuple[list[str], dict[tuple[str, str], dict]]:
    sources: list[str] = []
    merged: dict[tuple[str, str], dict] = {}
    if BENCHMARK_SIGNALS.exists():
        payload = load_json(BENCHMARK_SIGNALS)
        rows = payload.get("rows", []) if isinstance(payload, dict) else []
        merged.update(rows_to_country_month_map(rows))
        sources.append(str(BENCHMARK_SIGNALS.relative_to(ROOT)))
    if MANUAL_SIGNALS_LOCAL.exists():
        payload = load_json(MANUAL_SIGNALS_LOCAL)
        rows = payload.get("rows", []) if isinstance(payload, dict) else []
        merged.update(rows_to_country_month_map(rows))
        sources.append(str(MANUAL_SIGNALS_LOCAL.relative_to(ROOT)))
    return sources, merged


def build_month_index(country_rows: list[dict]) -> dict[tuple[str, int, int], MonthKey]:
    month_index: dict[tuple[str, int, int], MonthKey] = {}
    for row in country_rows:
        country = row.get("country")
        iso3 = str(row.get("iso3") or "")
        year = int(row.get("year") or 0)
        if not country or not year:
            continue
        for month in range(1, 13):
            month_index[(country, year, month)] = MonthKey(country=country, year=year, month=month, iso3=iso3)
    return month_index


def structural_row_lookup(country_rows: list[dict]) -> dict[tuple[str, int], dict]:
    lookup: dict[tuple[str, int], dict] = {}
    for row in country_rows:
        country = row.get("country")
        year = int(row.get("year") or 0)
        if country and year:
            lookup[(country, year)] = row
    return lookup


def build_event_month_features(events: list[dict]) -> dict[tuple[str, int, int], dict]:
    monthly: dict[tuple[str, int, int], dict] = defaultdict(lambda: {
        "event_count": 0,
        "high_salience_event_count": 0,
        "medium_salience_event_count": 0,
        "low_salience_event_count": 0,
        "high_confidence_event_count": 0,
        "medium_confidence_event_count": 0,
        "low_confidence_event_count": 0,
        "human_reviewed_event_count": 0,
        "human_validated_event_count": 0,
        "distinct_event_count": 0,
        "merged_event_count": 0,
        "review_priority_high_count": 0,
        "review_priority_medium_count": 0,
        "review_priority_low_count": 0,
        "machine_only_event_count": 0,
        "event_target_proxy_positive_count": 0,
        "dominant_event_type": None,
        "dominant_deed_type": None,
        "dominant_axis": None,
        "salience_mix_label": "no_signal",
        "confidence_mix_label": "no_signal",
        "deed_mix_label": "no_signal",
        "review_state_mix_label": "no_signal",
        "_type_counter": Counter(),
        "_deed_counter": Counter(),
        "_axis_counter": Counter(),
        "_review_counter": Counter(),
    })
    for event in events:
        country = str(event.get("country") or "").strip()
        if not country or country == "Regional":
            continue
        ym = parse_year_month(event.get("event_date"))
        if ym is None:
            continue
        year, month = ym
        bucket = monthly[(country, year, month)]
        bucket["event_count"] += 1

        salience = str(event.get("salience") or "").strip().lower()
        if salience == "high":
            bucket["high_salience_event_count"] += 1
        elif salience == "medium":
            bucket["medium_salience_event_count"] += 1
        else:
            bucket["low_salience_event_count"] += 1

        confidence = event_confidence_bucket(event.get("confidence"))
        bucket[f"{confidence}_confidence_event_count"] += 1

        if is_human_reviewed(event):
            bucket["human_reviewed_event_count"] += 1
        if event.get("human_validated"):
            bucket["human_validated_event_count"] += 1
        if review_state_bucket(event) == "machine_only":
            bucket["machine_only_event_count"] += 1
        bucket["_review_counter"][review_state_bucket(event)] += 1

        duplicate_status = str(event.get("duplicate_status") or "").strip().lower()
        if duplicate_status == "merged":
            bucket["merged_event_count"] += 1
        else:
            bucket["distinct_event_count"] += 1

        review_priority = str(event.get("review_priority") or "").strip().lower()
        if review_priority in {"high", "medium", "low"}:
            bucket[f"review_priority_{review_priority}_count"] += 1

        event_type = str(event.get("event_type") or "").strip().lower() or "other"
        if event_type not in EVENT_TYPE_FIELDS:
            event_type = "other"
        bucket[f"event_type_{event_type}_count"] = bucket.get(f"event_type_{event_type}_count", 0) + 1
        bucket["_type_counter"][event_type] += 1

        deed_type = str(event.get("deed_type") or "").strip().lower()
        if deed_type in DEED_TYPE_FIELDS:
            bucket[f"deed_type_{deed_type}_count"] = bucket.get(f"deed_type_{deed_type}_count", 0) + 1
            bucket["_deed_counter"][deed_type] += 1

        axis = str(event.get("axis") or "").strip().lower()
        if axis in AXIS_FIELDS:
            bucket[f"axis_{axis}_count"] = bucket.get(f"axis_{axis}_count", 0) + 1
            bucket["_axis_counter"][axis] += 1

        if is_irregular_transition_positive_event(event):
            bucket["event_target_proxy_positive_count"] += 1

    for bucket in monthly.values():
        if bucket["_type_counter"]:
            bucket["dominant_event_type"] = bucket["_type_counter"].most_common(1)[0][0]
        if bucket["_deed_counter"]:
            bucket["dominant_deed_type"] = bucket["_deed_counter"].most_common(1)[0][0]
        if bucket["_axis_counter"]:
            bucket["dominant_axis"] = bucket["_axis_counter"].most_common(1)[0][0]
        bucket["salience_mix_label"] = derive_mix_label(
            {
                "high": bucket["high_salience_event_count"],
                "medium": bucket["medium_salience_event_count"],
                "low": bucket["low_salience_event_count"],
            },
            total=bucket["event_count"],
        )
        bucket["confidence_mix_label"] = derive_mix_label(
            {
                "high": bucket["high_confidence_event_count"],
                "medium": bucket["medium_confidence_event_count"],
                "low": bucket["low_confidence_event_count"],
            },
            total=bucket["event_count"],
        )
        bucket["deed_mix_label"] = derive_mix_label(
            {label: bucket.get(f"deed_type_{label}_count", 0) for label in DEED_TYPE_FIELDS},
            total=sum(bucket.get(f"deed_type_{label}_count", 0) for label in DEED_TYPE_FIELDS),
        )
        bucket["review_state_mix_label"] = derive_mix_label(
            dict(bucket["_review_counter"]),
            total=bucket["event_count"],
        )
        del bucket["_type_counter"]
        del bucket["_deed_counter"]
        del bucket["_axis_counter"]
        del bucket["_review_counter"]
        for event_type in EVENT_TYPE_FIELDS:
            bucket.setdefault(f"event_type_{event_type}_count", 0)
        for deed_type in DEED_TYPE_FIELDS:
            bucket.setdefault(f"deed_type_{deed_type}_count", 0)
        for axis in AXIS_FIELDS:
            bucket.setdefault(f"axis_{axis}_count", 0)
    return monthly


def build_episode_month_features(episodes: list[dict]) -> dict[tuple[str, int, int], dict]:
    monthly: dict[tuple[str, int, int], dict] = defaultdict(lambda: {
        "episode_count": 0,
        "episode_start_count": 0,
        "active_episode_count": 0,
        "high_severity_episode_count": 0,
        "medium_severity_episode_count": 0,
        "low_severity_episode_count": 0,
        "escalating_episode_count": 0,
        "fragmenting_episode_count": 0,
        "institutionalizing_episode_count": 0,
        "dominant_episode_type": None,
        "dominant_episode_severity": None,
        "_type_counter": Counter(),
        "_severity_counter": Counter(),
    })

    for episode in episodes:
        country = str(episode.get("country") or "").strip()
        start = parse_year_month(episode.get("episode_start"))
        end = parse_year_month(episode.get("episode_end_estimate"))
        if not country or start is None or end is None:
            continue
        start_y, start_m = start
        end_y, end_m = end
        status = str(episode.get("episode_status") or "").strip().lower()
        direction = str(episode.get("episode_direction") or "").strip().lower()
        severity = str(episode.get("episode_severity") or "").strip().lower()
        episode_type = str(episode.get("episode_type") or "").strip().lower()
        links = {str(item).strip() for item in (episode.get("construct_links") or [])}

        current_y, current_m = start_y, start_m
        while (current_y, current_m) <= (end_y, end_m):
            bucket = monthly[(country, current_y, current_m)]
            bucket["episode_count"] += 1
            if (current_y, current_m) == (start_y, start_m):
                bucket["episode_start_count"] += 1
            if status in {"active", "stabilizing"} and (current_y, current_m) == (end_y, end_m):
                bucket["active_episode_count"] += 1
            if severity in EPISODE_SEVERITIES:
                bucket[f"{severity}_severity_episode_count"] += 1
                bucket["_severity_counter"][severity] += 1
            if direction == "escalating":
                bucket["escalating_episode_count"] += 1
            if direction == "fragmenting":
                bucket["fragmenting_episode_count"] += 1
            if direction == "institutionalizing":
                bucket["institutionalizing_episode_count"] += 1
            if episode_type in EPISODE_TYPES:
                bucket[f"episode_type_{episode_type}_count"] = bucket.get(f"episode_type_{episode_type}_count", 0) + 1
                bucket["_type_counter"][episode_type] += 1
            for link in EPISODE_CONSTRUCTS:
                if link in links:
                    bucket[f"episode_construct_{link}_count"] = bucket.get(f"episode_construct_{link}_count", 0) + 1

            current_y, current_m = month_offset(current_y, current_m, 1)

    for bucket in monthly.values():
        if bucket["_type_counter"]:
            bucket["dominant_episode_type"] = bucket["_type_counter"].most_common(1)[0][0]
        if bucket["_severity_counter"]:
            bucket["dominant_episode_severity"] = bucket["_severity_counter"].most_common(1)[0][0]
        del bucket["_type_counter"]
        del bucket["_severity_counter"]
        for episode_type in EPISODE_TYPES:
            bucket.setdefault(f"episode_type_{episode_type}_count", 0)
        for link in EPISODE_CONSTRUCTS:
            bucket.setdefault(f"episode_construct_{link}_count", 0)
    return monthly


def derive_mix_label(counter: dict[str, int], total: int) -> str:
    if total <= 0 or not counter:
        return "no_signal"
    ranked = sorted(counter.items(), key=lambda item: item[1], reverse=True)
    top_label, top_count = ranked[0]
    share = top_count / total if total else 0.0
    if share >= 0.7:
        return f"{top_label}_dominant"
    if share >= 0.45:
        return f"{top_label}_leading"
    return "mixed"


def event_month_map(rows: list[dict]) -> dict[tuple[str, int, int], dict]:
    return {
        (row["country"], row["year"], row["month"]): row
        for row in rows
    }


def month_offset(year: int, month: int, delta: int) -> tuple[int, int]:
    total = year * 12 + (month - 1) + delta
    return total // 12, total % 12 + 1


def is_irregular_transition_positive_event(event: dict) -> bool:
    if str(event.get("duplicate_status") or "").strip().lower() == "merged":
        return False
    if review_state_bucket(event) not in TARGET_POSITIVE_REVIEW_STATES:
        return False
    confidence = event_confidence_bucket(event.get("confidence"))
    if confidence == "low":
        return False
    event_type = str(event.get("event_type") or "").strip().lower()
    if event_type in TARGET_POSITIVE_EVENT_TYPES:
        return True
    deed_type = str(event.get("deed_type") or "").strip().lower()
    salience = str(event.get("salience") or "").strip().lower()
    return (
        event_type == "purge"
        and salience == "high"
        and deed_type in TARGET_POSITIVE_DEED_TYPES
    )


def add_rolling_features(rows: list[dict]) -> None:
    per_country: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        per_country[row["country"]].append(row)

    rolling_fields = [
        "event_count",
        "high_salience_event_count",
        "medium_salience_event_count",
        "human_reviewed_event_count",
        "human_validated_event_count",
        "machine_only_event_count",
        "event_type_conflict_count",
        "event_type_oc_count",
        "event_type_protest_count",
        "event_type_purge_count",
        "event_type_coup_count",
        "deed_type_symptom_count",
        "deed_type_precursor_count",
        "deed_type_destabilizing_count",
        "deed_type_resistance_count",
        "axis_vertical_count",
        "axis_horizontal_count",
        "event_target_proxy_positive_count",
        "episode_count",
        "episode_start_count",
        "active_episode_count",
        "high_severity_episode_count",
        "medium_severity_episode_count",
        "low_severity_episode_count",
        "escalating_episode_count",
        "fragmenting_episode_count",
        "institutionalizing_episode_count",
        "episode_construct_regime_vulnerability_count",
        "episode_construct_militarization_count",
        "episode_construct_security_fragmentation_count",
    ]

    for country_rows in per_country.values():
        country_rows.sort(key=lambda item: item["panel_date"])
        windows = {field: deque(maxlen=12) for field in rolling_fields}
        recent_event_counts: deque[int] = deque(maxlen=3)

        for row in country_rows:
            for field in rolling_fields:
                history = windows[field]
                row[f"{field}_3m"] = sum(list(history)[-2:]) + row[field]
                row[f"{field}_6m"] = sum(list(history)[-5:]) + row[field]
                row[f"{field}_12m"] = sum(history) + row[field]
                history.append(row[field])

            prior_mean = sum(recent_event_counts) / len(recent_event_counts) if recent_event_counts else 0.0
            row["event_count_3m_prev_mean"] = round(prior_mean, 2)
            row["event_shock_flag"] = int(
                row["event_count"] >= max(3, round(prior_mean * 2))
                and row["event_count"] > prior_mean
            )
            row["high_salience_share"] = round(
                row["high_salience_event_count"] / row["event_count"], 3
            ) if row["event_count"] else 0.0
            row["high_confidence_share"] = round(
                row["high_confidence_event_count"] / row["event_count"], 3
            ) if row["event_count"] else 0.0
            deed_total = sum(row[f"deed_type_{code}_count"] for code in DEED_TYPE_FIELDS)
            row["deed_signal_share"] = round(
                deed_total / row["event_count"], 3
            ) if row["event_count"] else 0.0
            row["human_review_share"] = round(
                row["human_reviewed_event_count"] / row["event_count"], 3
            ) if row["event_count"] else 0.0
            row["episode_escalation_share"] = round(
                row["escalating_episode_count"] / row["episode_count"], 3
            ) if row["episode_count"] else 0.0
            recent_event_counts.append(row["event_count"])


def add_transition_specificity_features(rows: list[dict]) -> None:
    for row in rows:
        protest_escalation = float(row.get("episode_type_protest_security_escalation_count", 0) or 0)
        protest_events = float(row.get("event_type_protest_count", 0) or 0)
        conflict_events = float(row.get("event_type_conflict_count", 0) or 0)
        high_severity = float(row.get("high_severity_episode_count", 0) or 0)
        fragmenting = float(row.get("fragmenting_episode_count", 0) or 0)
        shock = float(row.get("event_shock_flag", 0) or 0)
        protest_acute_signal = (
            protest_escalation * 2.0
            + min(protest_events, 2.0) * 0.6
            + min(conflict_events, 2.0) * 0.4
            + high_severity * 0.6
            + shock * 0.5
        )
        protest_background_load = max(
            protest_events * 1.3
            + conflict_events * 1.0
            + float(row.get("event_count", 0) or 0) * 0.15
            - protest_escalation * 1.2,
            0.0,
        )
        rupture_precursor = (
            float(row.get("event_type_coup_count", 0) or 0) * 4.0
            + float(row.get("event_type_purge_count", 0) or 0) * 2.5
            + float(row.get("high_severity_episode_count", 0) or 0) * 2.0
            + float(row.get("deed_type_destabilizing_count", 0) or 0) * 1.4
            + float(row.get("event_shock_flag", 0) or 0) * 1.4
            + float(row.get("high_salience_event_count", 0) or 0) * 0.8
            + protest_acute_signal * 0.6
        )
        contestation_load = (
            protest_background_load
            + float(row.get("escalating_episode_count", 0) or 0) * 1.6
            + float(row.get("episode_start_count", 0) or 0) * 1.1
            + float(row.get("episode_construct_regime_vulnerability_count", 0) or 0) * 1.35
            + float(row.get("event_count", 0) or 0) * 0.2
        )
        specificity_gap = rupture_precursor - contestation_load
        protest_escalation_specificity = max(
            protest_escalation * (
                1.0
                + min(high_severity, 1.0) * 1.5
                + min(fragmenting, 1.0) * 0.75
                + min(shock, 1.0) * 0.4
            )
            + max(specificity_gap, 0.0) * 0.6
            - protest_background_load * 1.2
            - max(contestation_load - 4.0, 0.0) * 0.5,
            0.0,
        )
        row["protest_acute_signal_score"] = round(protest_acute_signal, 3)
        row["protest_background_load_score"] = round(protest_background_load, 3)
        row["protest_escalation_specificity_score"] = round(protest_escalation_specificity, 3)
        row["transition_rupture_precursor_score"] = round(rupture_precursor, 3)
        row["transition_contestation_load_score"] = round(contestation_load, 3)
        row["transition_specificity_gap"] = round(specificity_gap, 3)


def add_target_columns(rows: list[dict]) -> None:
    per_country: dict[str, list[dict]] = defaultdict(list)
    adjudicated = load_adjudicated_targets()
    gold = load_gold_targets()
    for row in rows:
        per_country[row["country"]].append(row)

    for country_rows in per_country.values():
        country_rows.sort(key=lambda item: item["panel_date"])
        indexed = event_month_map(country_rows)
        for row in country_rows:
            year = row["year"]
            month = row["month"]
            next_1 = indexed.get((row["country"], *month_offset(year, month, 1)))
            next_2 = indexed.get((row["country"], *month_offset(year, month, 2)))
            next_3 = indexed.get((row["country"], *month_offset(year, month, 3)))

            def transition_signal_score(candidate: dict | None, *, fit_mode: bool = False) -> int:
                if not candidate:
                    return 0
                score = 0
                rupture_score = float(candidate.get("transition_rupture_precursor_score", 0) or 0.0)
                contestation_load = float(candidate.get("transition_contestation_load_score", 0) or 0.0)
                specificity_gap = float(candidate.get("transition_specificity_gap", 0) or 0.0)
                rupture_sequence = (
                    not fit_mode
                    and
                    candidate.get("high_severity_episode_count", 0) > 0
                    and candidate.get("episode_construct_regime_vulnerability_count", 0) > 0
                    and candidate.get("event_shock_flag", 0) > 0
                    and candidate.get("episode_start_count", 0) > 0
                    and candidate.get("high_salience_event_count", 0) >= 2
                    and rupture_score >= 4.5
                )
                fit_shock_rupture_sequence = (
                    fit_mode
                    and candidate.get("high_severity_episode_count", 0) > 0
                    and candidate.get("event_shock_flag", 0) > 0
                    and candidate.get("episode_start_count", 0) > 0
                    and candidate.get("high_salience_event_count", 0) >= 2
                    and rupture_score >= 4.5
                    and contestation_load <= 8.5
                )
                fit_structured_high_severity = (
                    fit_mode
                    and candidate.get("high_severity_episode_count", 0) > 0
                    and candidate.get("high_salience_event_count", 0) >= 2
                    and rupture_score >= 3.5
                    and specificity_gap >= 0.0
                    and contestation_load <= 4.5
                )
                fit_escalating_high_severity = (
                    fit_mode
                    and candidate.get("high_severity_episode_count", 0) > 0
                    and candidate.get("episode_construct_regime_vulnerability_count", 0) > 0
                    and candidate.get("high_salience_event_count", 0) >= 2
                    and rupture_score >= 3.5
                    and contestation_load <= 6.5
                    and candidate.get("event_type_conflict_count", 0) <= 1
                )
                fit_structured_destabilizing = (
                    fit_mode
                    and candidate.get("high_severity_episode_count", 0) > 0
                    and candidate.get("episode_construct_regime_vulnerability_count", 0) > 0
                    and candidate.get("deed_type_destabilizing_count", 0) > 0
                    and rupture_score >= 4.0
                    and contestation_load <= 5.6
                    and candidate.get("event_type_conflict_count", 0) == 0
                )
                if candidate.get("event_type_coup_count", 0) > 0:
                    score += 4
                if (
                    rupture_score >= 6.0
                    and candidate.get("episode_construct_regime_vulnerability_count", 0) > 0
                ):
                    score += 3
                elif (
                    rupture_score >= 3.5
                    and candidate.get("high_severity_episode_count", 0) > 0
                    and candidate.get("episode_construct_regime_vulnerability_count", 0) > 0
                ):
                    score += 2
                elif (
                    rupture_score >= 2.0
                    and candidate.get("deed_type_destabilizing_count", 0) > 0
                    and candidate.get("high_salience_event_count", 0) > 0
                ):
                    score += 1
                if (
                    candidate.get("event_type_purge_count", 0) > 0
                    and candidate.get("deed_type_destabilizing_count", 0) > 0
                    and candidate.get("high_salience_event_count", 0) > 0
                ):
                    score += 3
                if (
                    candidate.get("event_shock_flag", 0) > 0
                    and candidate.get("deed_type_destabilizing_count", 0) > 0
                ):
                    score += 2
                if (
                    candidate.get("event_type_protest_count", 0) > 0
                    and candidate.get("high_salience_event_count", 0) > 0
                    and candidate.get("event_type_conflict_count", 0) > 0
                    and candidate.get("deed_type_destabilizing_count", 0) > 0
                ):
                    score += 1
                if rupture_sequence:
                    score += 2
                if fit_shock_rupture_sequence:
                    score += 2
                if fit_structured_high_severity:
                    score += 2
                if fit_escalating_high_severity:
                    score += 2
                if fit_structured_destabilizing:
                    score += 2
                if specificity_gap >= 0.5:
                    score += 1
                if contestation_load >= 6.0 and rupture_score < 3.0 and not rupture_sequence:
                    score -= 1
                elif specificity_gap <= -4.0 and rupture_score < 3.5 and not rupture_sequence:
                    score -= 2
                elif specificity_gap <= -2.0 and rupture_score < 2.5 and not rupture_sequence:
                    score -= 1
                return max(score, 0)

            watch_score_1m = transition_signal_score(next_1, fit_mode=False)
            watch_score_3m = max(
                transition_signal_score(candidate, fit_mode=False)
                for candidate in (next_1, next_2, next_3)
            )
            fit_score_1m = transition_signal_score(next_1, fit_mode=True)
            fit_score_3m = max(
                transition_signal_score(candidate, fit_mode=True)
                for candidate in (next_1, next_2, next_3)
            )
            positive_1m = int(watch_score_1m >= 4)
            positive_3m = int(watch_score_3m >= 4)

            def acute_political_risk_score(candidate: dict | None) -> int:
                if not candidate:
                    return 0
                score = 0
                high_severity = int(candidate.get("high_severity_episode_count", 0) or 0)
                fragmenting = int(candidate.get("fragmenting_episode_count", 0) or 0)
                shock = int(candidate.get("event_shock_flag", 0) or 0)
                conflict_count = int(candidate.get("event_type_conflict_count", 0) or 0)
                protest_count = int(candidate.get("event_type_protest_count", 0) or 0)
                contestation_load = float(candidate.get("transition_contestation_load_score", 0) or 0.0)
                if candidate.get("event_type_coup_count", 0) > 0:
                    score += 4
                if (
                    high_severity > 0
                    and (
                        candidate.get("episode_construct_regime_vulnerability_count", 0) > 0
                        or candidate.get("episode_construct_security_fragmentation_count", 0) > 0
                    )
                ):
                    score += 3
                if (
                    fragmenting > 0
                    and candidate.get("episode_construct_security_fragmentation_count", 0) > 0
                ):
                    score += 2
                if (
                    shock > 0
                    and (
                        candidate.get("high_salience_event_count", 0) > 0
                        or candidate.get("episode_start_count", 0) > 0
                    )
                ):
                    score += 2
                if (
                    candidate.get("deed_type_destabilizing_count", 0) > 0
                    and (
                        conflict_count > 0
                        or protest_count > 0
                    )
                    and (
                        high_severity > 0
                        or fragmenting > 0
                        or shock > 0
                    )
                ):
                    score += 1
                if (
                    candidate.get("external_pressure_signal_present", 0) > 0
                    and (
                        float(candidate.get("external_pressure_sanctions_active", 0) or 0.0) >= 50.0
                        or float(candidate.get("external_pressure_us_security_shift", 0) or 0.0) >= 40.0
                        or float(candidate.get("external_pressure_imf_program_break", 0) or 0.0) > 0.0
                    )
                ):
                    score += 1
                if (
                    candidate.get("economic_fragility_signal_present", 0) > 0
                    and (
                        float(candidate.get("economic_fragility_fx_stress", 0) or 0.0) >= 60.0
                        or float(candidate.get("economic_fragility_debt_stress", 0) or 0.0) >= 70.0
                        or float(candidate.get("economic_fragility_inflation_stress", 0) or 0.0) >= 60.0
                    )
                ):
                    score += 1
                if (
                    candidate.get("regime_shift_flag", 0) > 0
                    or candidate.get("repression_shift_flag", 0) > 0
                    or candidate.get("macro_stress_shift_flag", 0) > 0
                ):
                    score += 1
                if (
                    (high_severity > 0 or fragmenting > 0)
                    and (
                        candidate.get("episode_construct_regime_vulnerability_count", 0) > 0
                        or candidate.get("episode_construct_security_fragmentation_count", 0) > 0
                    )
                    and candidate.get("external_pressure_signal_present", 0) > 0
                    and (
                        candidate.get("economic_fragility_signal_present", 0) > 0
                        or candidate.get("macro_stress_shift_flag", 0) > 0
                    )
                ):
                    score += 1
                if (
                    contestation_load < 1.0
                    and candidate.get("external_pressure_signal_present", 0) > 0
                    and candidate.get("economic_fragility_signal_present", 0) > 0
                    and candidate.get("macro_stress_shift_flag", 0) > 0
                ):
                    score += 1
                if (
                    contestation_load >= 4.0
                    and candidate.get("event_type_coup_count", 0) <= 0
                    and high_severity <= 0
                    and fragmenting <= 0
                ):
                    score -= 2
                elif (
                    contestation_load >= 4.0
                    and candidate.get("event_type_coup_count", 0) <= 0
                    and shock <= 0
                    and high_severity <= 0
                    and fragmenting <= 0
                ):
                    score -= 1
                if (
                    (conflict_count > 0 or protest_count > 0)
                    and high_severity <= 0
                    and fragmenting <= 0
                    and shock <= 0
                ):
                    score -= 1
                return max(score, 0)

            acute_score_1m = acute_political_risk_score(next_1)
            acute_score_3m = max(
                acute_political_risk_score(candidate) for candidate in (next_1, next_2, next_3)
            )

            def security_fragmentation_jump_score(candidate: dict | None) -> int:
                if not candidate:
                    return 0
                score = 0
                high_severity = int(candidate.get("high_severity_episode_count", 0) or 0)
                fragmenting = int(candidate.get("fragmenting_episode_count", 0) or 0)
                security_link = int(candidate.get("episode_construct_security_fragmentation_count", 0) or 0)
                conflict_count = int(candidate.get("event_type_conflict_count", 0) or 0)
                oc_count = int(candidate.get("event_type_oc_count", 0) or 0)
                protest_count = int(candidate.get("event_type_protest_count", 0) or 0)
                shock = int(candidate.get("event_shock_flag", 0) or 0)
                destabilizing = int(candidate.get("deed_type_destabilizing_count", 0) or 0)
                contestation_load = float(candidate.get("transition_contestation_load_score", 0) or 0.0)
                rupture_precursor = float(candidate.get("transition_rupture_precursor_score", 0) or 0.0)
                protest_background = float(candidate.get("protest_background_load_score", 0) or 0.0)

                if fragmenting > 0 and security_link > 0:
                    score += 3
                if high_severity > 0 and security_link > 0:
                    score += 2
                if shock > 0 and security_link > 0:
                    score += 1
                if destabilizing > 0 and (conflict_count > 0 or oc_count > 0):
                    score += 1
                if oc_count > 0 and security_link > 0:
                    score += 1
                if (
                    candidate.get("external_pressure_signal_present", 0) > 0
                    or candidate.get("economic_fragility_signal_present", 0) > 0
                ) and security_link > 0:
                    score += 1
                if fragmenting <= 0 and high_severity <= 0 and security_link > 0:
                    score -= 1
                if (
                    protest_count > 0
                    and conflict_count <= 0
                    and oc_count <= 0
                    and fragmenting <= 0
                    and high_severity <= 0
                ):
                    score -= 1
                if contestation_load >= 4.0 and fragmenting <= 0 and high_severity <= 0 and shock <= 0:
                    score -= 1
                if protest_background >= 1.5 and fragmenting <= 0 and high_severity <= 0:
                    score -= 1
                if protest_background >= 0.75 and fragmenting <= 0 and high_severity <= 0 and shock <= 0:
                    score -= 1
                if rupture_precursor >= 2.0 and fragmenting <= 0 and shock <= 0:
                    score -= 1
                if contestation_load >= 5.0 and security_link <= 0:
                    score -= 1
                return max(score, 0)

            frag_score_1m = security_fragmentation_jump_score(next_1)
            frag_score_3m = max(
                security_fragmentation_jump_score(candidate) for candidate in (next_1, next_2, next_3)
            )

            row["irregular_transition_next_1m"] = positive_1m
            row["irregular_transition_next_3m"] = positive_3m
            row["irregular_transition_signal_score_next_1m"] = watch_score_1m
            row["irregular_transition_signal_score_next_3m"] = watch_score_3m
            row["irregular_transition_signal_label_next_1m"] = (
                "elevated" if watch_score_1m >= 4 else "watch" if watch_score_1m >= 2 else "background"
            )
            row["irregular_transition_signal_label_next_3m"] = (
                "elevated" if watch_score_3m >= 4 else "watch" if watch_score_3m >= 2 else "background"
            )
            row["irregular_transition_target_rule"] = TARGET_RULE_VERSION
            row["irregular_transition_fit_score_next_1m"] = fit_score_1m
            row["irregular_transition_fit_score_next_3m"] = fit_score_3m
            row["irregular_transition_fit_label_next_1m"] = (
                "elevated" if fit_score_1m >= 4 else "watch" if fit_score_1m >= 2 else "background"
            )
            row["irregular_transition_fit_label_next_3m"] = (
                "elevated" if fit_score_3m >= 4 else "watch" if fit_score_3m >= 2 else "background"
            )
            row["irregular_transition_fit_target_rule"] = FIT_TARGET_RULE_VERSION
            row["irregular_transition_label_source"] = "proxy_rule"
            row["irregular_transition_adjudicated_note"] = None
            row["irregular_transition_gold_next_1m"] = None
            row["irregular_transition_gold_label_available"] = 0
            row["irregular_transition_observation_window_complete_1m"] = int(next_1 is not None)
            row["irregular_transition_observation_window_complete_3m"] = int(
                all(candidate is not None for candidate in (next_1, next_2, next_3))
            )
            row["acute_political_risk_next_1m"] = int(acute_score_1m >= 4)
            row["acute_political_risk_next_3m"] = int(acute_score_3m >= 4)
            row["acute_political_risk_signal_score_next_1m"] = acute_score_1m
            row["acute_political_risk_signal_score_next_3m"] = acute_score_3m
            row["acute_political_risk_signal_label_next_1m"] = (
                "elevated" if acute_score_1m >= 4 else "watch" if acute_score_1m >= 2 else "background"
            )
            row["acute_political_risk_signal_label_next_3m"] = (
                "elevated" if acute_score_3m >= 4 else "watch" if acute_score_3m >= 2 else "background"
            )
            row["acute_political_risk_target_rule"] = ACUTE_POLITICAL_RISK_RULE_VERSION
            row["acute_political_risk_observation_window_complete_1m"] = int(next_1 is not None)
            row["acute_political_risk_observation_window_complete_3m"] = int(
                all(candidate is not None for candidate in (next_1, next_2, next_3))
            )
            row["security_fragmentation_jump_next_1m"] = int(frag_score_1m >= 4)
            row["security_fragmentation_jump_next_3m"] = int(frag_score_3m >= 4)
            row["security_fragmentation_jump_signal_score_next_1m"] = frag_score_1m
            row["security_fragmentation_jump_signal_score_next_3m"] = frag_score_3m
            row["security_fragmentation_jump_signal_label_next_1m"] = (
                "elevated" if frag_score_1m >= 4 else "watch" if frag_score_1m >= 2 else "background"
            )
            row["security_fragmentation_jump_signal_label_next_3m"] = (
                "elevated" if frag_score_3m >= 4 else "watch" if frag_score_3m >= 2 else "background"
            )
            row["security_fragmentation_jump_target_rule"] = SECURITY_FRAGMENTATION_JUMP_RULE_VERSION
            row["security_fragmentation_jump_observation_window_complete_1m"] = int(next_1 is not None)
            row["security_fragmentation_jump_observation_window_complete_3m"] = int(
                all(candidate is not None for candidate in (next_1, next_2, next_3))
            )
            adjudicated_row = adjudicated.get((row["country"], row["panel_date"]))
            if adjudicated_row:
                row["irregular_transition_next_1m"] = int(adjudicated_row.get("label", positive_1m))
                row["irregular_transition_label_source"] = str(
                    adjudicated_row.get("label_source") or "adjudicated_benchmark_review"
                )
                row["irregular_transition_adjudicated_note"] = adjudicated_row.get("note")
            gold_row = gold.get((row["country"], row["panel_date"]))
            if gold_row:
                row["irregular_transition_gold_next_1m"] = int(gold_row.get("label", 1))
                row["irregular_transition_gold_label_available"] = 1


def build_panel_rows() -> list[dict]:
    country_rows = load_country_year_rows()
    structural_lookup = structural_row_lookup(country_rows)
    month_index = build_month_index(country_rows)
    event_monthly = build_event_month_features(load_events())
    episode_monthly = build_episode_month_features(load_episodes())

    rows: list[dict] = []
    keys = sorted(month_index.values(), key=lambda item: (item.country, item.year, item.month))
    for key in keys:
        structural = structural_lookup.get((key.country, key.year), {})
        events = event_monthly.get((key.country, key.year, key.month), {})
        row = {
            "country": key.country,
            "iso3": key.iso3,
            "year": key.year,
            "month": key.month,
            "panel_date": key.panel_date,
            "panel_month_id": key.ym,
        }
        for field in STRUCTURAL_FIELDS:
            row[field] = structural.get(field)
        row.update({
            "feature_family_structural": 1,
            "feature_family_event_pulse": 1,
            "feature_family_rolling": 1,
            "feature_family_targets": 1,
            "feature_family_external_placeholder": 1,
            "feature_family_economic_placeholder": 1,
            "event_count": 0,
            "high_salience_event_count": 0,
            "medium_salience_event_count": 0,
            "low_salience_event_count": 0,
            "high_confidence_event_count": 0,
            "medium_confidence_event_count": 0,
            "low_confidence_event_count": 0,
            "human_reviewed_event_count": 0,
            "human_validated_event_count": 0,
            "machine_only_event_count": 0,
            "distinct_event_count": 0,
            "merged_event_count": 0,
            "review_priority_high_count": 0,
            "review_priority_medium_count": 0,
            "review_priority_low_count": 0,
            "event_target_proxy_positive_count": 0,
            "dominant_event_type": None,
            "dominant_deed_type": None,
            "dominant_axis": None,
            "episode_count": 0,
            "episode_start_count": 0,
            "active_episode_count": 0,
            "high_severity_episode_count": 0,
            "medium_severity_episode_count": 0,
            "low_severity_episode_count": 0,
            "escalating_episode_count": 0,
            "fragmenting_episode_count": 0,
            "institutionalizing_episode_count": 0,
            "dominant_episode_type": None,
            "dominant_episode_severity": None,
            "salience_mix_label": "no_signal",
            "confidence_mix_label": "no_signal",
            "deed_mix_label": "no_signal",
            "review_state_mix_label": "no_signal",
            "external_pressure_sanctions_active": None,
            "external_pressure_sanctions_delta": None,
            "external_pressure_imf_program_active": None,
            "external_pressure_imf_program_break": None,
            "external_pressure_us_security_shift": None,
            "economic_fragility_inflation_stress": None,
            "economic_fragility_fx_stress": None,
            "economic_fragility_debt_stress": None,
            "economic_policy_capital_controls_flag": None,
            "economic_policy_nationalization_signal": None,
            "external_pressure_signal_present": 0,
            "economic_fragility_signal_present": 0,
            "policy_shock_signal_present": 0,
            "protest_acute_signal_score": 0.0,
            "protest_background_load_score": 0.0,
            "protest_escalation_specificity_score": 0.0,
            "transition_rupture_precursor_score": 0.0,
            "transition_contestation_load_score": 0.0,
            "transition_specificity_gap": 0.0,
            "irregular_transition_fit_score_next_1m": 0,
            "irregular_transition_fit_score_next_3m": 0,
            "irregular_transition_fit_label_next_1m": "background",
            "irregular_transition_fit_label_next_3m": "background",
            "irregular_transition_fit_target_rule": FIT_TARGET_RULE_VERSION,
            "acute_political_risk_next_1m": 0,
            "acute_political_risk_next_3m": 0,
            "acute_political_risk_signal_score_next_1m": 0,
            "acute_political_risk_signal_score_next_3m": 0,
            "acute_political_risk_signal_label_next_1m": "background",
            "acute_political_risk_signal_label_next_3m": "background",
            "acute_political_risk_target_rule": ACUTE_POLITICAL_RISK_RULE_VERSION,
            "acute_political_risk_observation_window_complete_1m": 0,
            "acute_political_risk_observation_window_complete_3m": 0,
            "security_fragmentation_jump_next_1m": 0,
            "security_fragmentation_jump_next_3m": 0,
            "security_fragmentation_jump_signal_score_next_1m": 0,
            "security_fragmentation_jump_signal_score_next_3m": 0,
            "security_fragmentation_jump_signal_label_next_1m": "background",
            "security_fragmentation_jump_signal_label_next_3m": "background",
            "security_fragmentation_jump_target_rule": SECURITY_FRAGMENTATION_JUMP_RULE_VERSION,
            "security_fragmentation_jump_observation_window_complete_1m": 0,
            "security_fragmentation_jump_observation_window_complete_3m": 0,
        })
        for event_type in EVENT_TYPE_FIELDS:
            row[f"event_type_{event_type}_count"] = 0
        for deed_type in DEED_TYPE_FIELDS:
            row[f"deed_type_{deed_type}_count"] = 0
        for axis in AXIS_FIELDS:
            row[f"axis_{axis}_count"] = 0
        for episode_type in EPISODE_TYPES:
            row[f"episode_type_{episode_type}_count"] = 0
        for link in EPISODE_CONSTRUCTS:
            row[f"episode_construct_{link}_count"] = 0
        row.update(events)
        row.update(episode_monthly.get((key.country, key.year, key.month), {}))
        rows.append(row)

    add_rolling_features(rows)
    add_transition_specificity_features(rows)
    add_target_columns(rows)
    return rows


def apply_external_economic_signals(rows: list[dict]) -> list[str]:
    derived_sources, derived = load_external_economic_signal_rows()
    if not derived:
        return derived_sources
    for row in rows:
        match = derived.get((row["country"], row["panel_date"]))
        if not match:
            continue
        for field in EXTERNAL_ECONOMIC_FIELDS:
            if field in match:
                row[field] = match.get(field)
        for flag in (
            "external_pressure_signal_present",
            "economic_fragility_signal_present",
            "policy_shock_signal_present",
        ):
            if flag in match:
                row[flag] = match.get(flag)
    return list(dict.fromkeys(derived_sources))


def apply_manual_country_month_signals(rows: list[dict]) -> list[str]:
    sources, manual = load_seeded_country_month_signals()
    if not manual:
        return sources
    for row in rows:
        match = manual.get((row["country"], row["panel_date"]))
        if not match:
            continue
        for field in EXTERNAL_ECONOMIC_FIELDS:
            if field in match:
                row[field] = match.get(field)
        row["external_pressure_signal_present"] = int(
            any(row.get(field) not in (None, 0, 0.0, "") for field in [
                "external_pressure_sanctions_active",
                "external_pressure_sanctions_delta",
                "external_pressure_imf_program_active",
                "external_pressure_imf_program_break",
                "external_pressure_us_security_shift",
            ])
        )
        row["economic_fragility_signal_present"] = int(
            any(row.get(field) not in (None, 0, 0.0, "") for field in [
                "economic_fragility_inflation_stress",
                "economic_fragility_fx_stress",
                "economic_fragility_debt_stress",
            ])
        )
        row["policy_shock_signal_present"] = int(
            any(row.get(field) not in (None, 0, 0.0, "") for field in [
                "economic_policy_capital_controls_flag",
                "economic_policy_nationalization_signal",
            ])
        )
    return sources


def write_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = build_panel_rows()
    external_sources = apply_external_economic_signals(rows)
    manual_sources = apply_manual_country_month_signals(rows)
    feature_contract = load_feature_contract()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "private_internal_modeling_artifact",
        "description": (
            "Country-month modeling panel that joins annual structural data "
            "with monthly event-derived pulse features and conservative proxy "
            "targets for future irregular-transition modeling."
        ),
        "unit_of_analysis": "country_month",
        "coverage": {
            "countries": "Latin America and Caribbean countries in the SENTINEL structural layer",
            "time_span": {
                "start": rows[0]["panel_date"] if rows else None,
                "end": rows[-1]["panel_date"] if rows else None,
            },
        },
        "contract_status": {
            "structural_fields": "stable_for_iteration",
            "event_pulse_fields": "stable_for_iteration",
            "episode_fields": "first_private_sequence_layer",
            "rolling_features": "experimental_but_ready",
            "target_fields": "proxy_experimental",
            "external_pressure_fields": "derived_then_seed_override",
            "economic_fragility_fields": "derived_then_seed_override",
        },
        "field_families": {
            "structural_baseline": STRUCTURAL_FIELDS,
            "event_pulse": [
                "event_count",
                "high_salience_event_count",
                "medium_salience_event_count",
                "low_salience_event_count",
                "high_confidence_event_count",
                "medium_confidence_event_count",
                "low_confidence_event_count",
                "human_reviewed_event_count",
                "human_validated_event_count",
                "machine_only_event_count",
                "distinct_event_count",
                "merged_event_count",
                "review_priority_high_count",
                "review_priority_medium_count",
                "review_priority_low_count",
                "dominant_event_type",
                "dominant_deed_type",
                "dominant_axis",
                "salience_mix_label",
                "confidence_mix_label",
                "deed_mix_label",
                "review_state_mix_label",
            ] + [f"event_type_{code}_count" for code in EVENT_TYPE_FIELDS]
              + [f"deed_type_{code}_count" for code in DEED_TYPE_FIELDS]
              + [f"axis_{code}_count" for code in AXIS_FIELDS],
            "episode_features": [
                "episode_count",
                "episode_start_count",
                "active_episode_count",
                "high_severity_episode_count",
                "medium_severity_episode_count",
                "low_severity_episode_count",
                "escalating_episode_count",
                "fragmenting_episode_count",
                "institutionalizing_episode_count",
                "dominant_episode_type",
                "dominant_episode_severity",
                "episode_escalation_share",
                "protest_acute_signal_score",
                "protest_background_load_score",
                "protest_escalation_specificity_score",
            ] + [f"episode_type_{code}_count" for code in EPISODE_TYPES]
              + [f"episode_construct_{code}_count" for code in EPISODE_CONSTRUCTS],
            "rolling_features": [
                "event_count_3m",
                "event_count_6m",
                "event_count_12m",
                "event_count_3m_prev_mean",
                "event_shock_flag",
                "high_salience_share",
                "high_confidence_share",
                "deed_signal_share",
                "human_review_share",
                "episode_escalation_share",
                "transition_rupture_precursor_score",
                "transition_contestation_load_score",
                "transition_specificity_gap",
                "external_pressure_signal_present",
                "economic_fragility_signal_present",
                "policy_shock_signal_present",
            ],
            "targets": [
                "irregular_transition_next_1m",
                "irregular_transition_next_3m",
                "irregular_transition_signal_score_next_1m",
                "irregular_transition_signal_score_next_3m",
                "irregular_transition_signal_label_next_1m",
                "irregular_transition_signal_label_next_3m",
                "irregular_transition_target_rule",
                "irregular_transition_fit_score_next_1m",
                "irregular_transition_fit_score_next_3m",
                "irregular_transition_fit_label_next_1m",
                "irregular_transition_fit_label_next_3m",
                "irregular_transition_fit_target_rule",
                "irregular_transition_label_source",
                "irregular_transition_adjudicated_note",
                "irregular_transition_gold_next_1m",
                "irregular_transition_gold_label_available",
                "irregular_transition_observation_window_complete_1m",
                "irregular_transition_observation_window_complete_3m",
                "acute_political_risk_next_1m",
                "acute_political_risk_next_3m",
                "acute_political_risk_signal_score_next_1m",
                "acute_political_risk_signal_score_next_3m",
                "acute_political_risk_signal_label_next_1m",
                "acute_political_risk_signal_label_next_3m",
                "acute_political_risk_target_rule",
                "acute_political_risk_observation_window_complete_1m",
                "acute_political_risk_observation_window_complete_3m",
                "security_fragmentation_jump_next_1m",
                "security_fragmentation_jump_next_3m",
                "security_fragmentation_jump_signal_score_next_1m",
                "security_fragmentation_jump_signal_score_next_3m",
                "security_fragmentation_jump_signal_label_next_1m",
                "security_fragmentation_jump_signal_label_next_3m",
                "security_fragmentation_jump_target_rule",
                "security_fragmentation_jump_observation_window_complete_1m",
                "security_fragmentation_jump_observation_window_complete_3m",
            ],
            "external_pressure_placeholders": [
                "external_pressure_sanctions_active",
                "external_pressure_sanctions_delta",
                "external_pressure_imf_program_active",
                "external_pressure_imf_program_break",
                "external_pressure_us_security_shift",
            ],
            "economic_fragility_placeholders": [
                "economic_fragility_inflation_stress",
                "economic_fragility_fx_stress",
                "economic_fragility_debt_stress",
                "economic_policy_capital_controls_flag",
                "economic_policy_nationalization_signal",
            ],
        },
        "feature_contract_file": str(FEATURE_CONTRACT.relative_to(ROOT)) if FEATURE_CONTRACT.exists() else None,
        "external_economic_signal_file": str(EXTERNAL_ECON_SIGNALS.relative_to(ROOT)) if EXTERNAL_ECON_SIGNALS.exists() else None,
        "manual_signal_sources": list(dict.fromkeys([
            str(MANUAL_SIGNALS_TEMPLATE.relative_to(ROOT)) if MANUAL_SIGNALS_TEMPLATE.exists() else None,
            str(BENCHMARK_SIGNALS.relative_to(ROOT)) if BENCHMARK_SIGNALS.exists() else None,
            *manual_sources,
        ])),
        "external_economic_signal_sources": list(dict.fromkeys(external_sources)),
        "seeded_signal_coverage": {
            "external_pressure_rows": sum(int(row.get("external_pressure_signal_present", 0)) for row in rows),
            "economic_fragility_rows": sum(int(row.get("economic_fragility_signal_present", 0)) for row in rows),
            "policy_shock_rows": sum(int(row.get("policy_shock_signal_present", 0)) for row in rows),
        },
        "target_definitions": {
            "irregular_transition_next_1m": {
                "status": "internal_watch_label_with_selective_adjudicated_override",
                "rule_version": TARGET_RULE_VERSION,
                "positive_when": (
                    "the next country-month reaches the broader internal watch "
                    "score threshold used for analyst-facing rupture-watch logic"
                ),
                "override_path": (
                    "where a reviewed benchmark label exists, the 1m label is "
                    "overridden by the adjudicated target layer and tracked in "
                    "irregular_transition_label_source"
                ),
            },
            "irregular_transition_next_3m": {
                "status": "internal_watch_label",
                "rule_version": TARGET_RULE_VERSION,
                "positive_when": (
                    "any of the next three country-months reaches the broader "
                    "internal watch score threshold under the same rule"
                ),
            },
            "irregular_transition_fit_score_next_1m": {
                "status": "fit_ready_proxy_score",
                "rule_version": FIT_TARGET_RULE_VERSION,
                "meaning": (
                    "Stricter next-month rupture score for fit-time validation, "
                    "without the broader rupture-watch escape hatch used for "
                    "internal monitoring."
                ),
            },
            "irregular_transition_fit_score_next_3m": {
                "status": "fit_ready_proxy_score",
                "rule_version": FIT_TARGET_RULE_VERSION,
                "meaning": (
                    "Maximum stricter rupture score across the next three months "
                    "for fit-time validation."
                ),
            },
            "irregular_transition_gold_next_1m": {
                "status": "gold_fit_target",
                "source": str(GOLD_TARGETS.relative_to(ROOT)) if GOLD_TARGETS.exists() else None,
                "meaning": (
                    "Higher-confidence 1m training/validation target derived "
                    "from the stricter gold irregular-transition subset."
                ),
            },
            "acute_political_risk_next_1m": {
                "status": "proxy_label",
                "rule_version": ACUTE_POLITICAL_RISK_RULE_VERSION,
                "meaning": (
                    "Broader acute political-risk proxy for the next month, "
                    "capturing high-severity regime-vulnerability, fragmentation, "
                    "shock, external-pressure, and economic-stress deterioration."
                ),
            },
            "acute_political_risk_next_3m": {
                "status": "proxy_label",
                "rule_version": ACUTE_POLITICAL_RISK_RULE_VERSION,
                "meaning": (
                    "Broader acute political-risk proxy across the next three "
                    "months using the same deterioration logic."
                ),
            },
            "security_fragmentation_jump_next_1m": {
                "status": "proxy_label",
                "rule_version": SECURITY_FRAGMENTATION_JUMP_RULE_VERSION,
                "meaning": (
                    "Short-horizon proxy for a jump in security fragmentation "
                    "pressure in the next month."
                ),
            },
            "security_fragmentation_jump_next_3m": {
                "status": "proxy_label",
                "rule_version": SECURITY_FRAGMENTATION_JUMP_RULE_VERSION,
                "meaning": (
                    "Construct-oriented proxy for a jump in security fragmentation "
                    "pressure across the next three months."
                ),
            },
        },
        "construct_integration_notes": {
            "regime_vulnerability": (
                "state_capacity_composite enters as weakness plus regime and "
                "erosion variables; DEED pulse contributes through event counts, "
                "episode sequence features, and future target proxies"
            ),
            "militarization": (
                "state capacity should not be treated symmetrically; it mainly "
                "conditions militarization through weak civilian governance, "
                "mission substitution, and later episode/process signals rather "
                "than direct regime stress"
            ),
            "security_fragmentation": (
                "state capacity enters through territorial weakness and uneven "
                "coercive order; episode features should become increasingly "
                "important as fragmentation sequences are identified"
            ),
        },
        "public_boundary": (
            "This artifact is private/internal and should not be surfaced in "
            "the public dashboard or public-facing copy."
        ),
        "source_files": [
            str(COUNTRY_YEAR.relative_to(ROOT)),
            str(EVENTS.relative_to(ROOT)),
            str(EPISODES.relative_to(ROOT)) if EPISODES.exists() else None,
            str(ADJUDICATED_TARGETS.relative_to(ROOT)) if ADJUDICATED_TARGETS.exists() else None,
            str(GOLD_TARGETS.relative_to(ROOT)) if GOLD_TARGETS.exists() else None,
            str(FEATURE_CONTRACT.relative_to(ROOT)) if FEATURE_CONTRACT.exists() else None,
            str(EXTERNAL_ECON_SIGNALS.relative_to(ROOT)) if EXTERNAL_ECON_SIGNALS.exists() else None,
        ],
        "feature_contract": feature_contract,
        "count": len(rows),
        "countries": sorted({row["country"] for row in rows}),
        "rows": rows,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_csv(rows, OUT_CSV)
    print(f"Wrote {len(rows)} country-month rows to {OUT_JSON.relative_to(ROOT)}")
    print(f"Wrote CSV mirror to {OUT_CSV.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
