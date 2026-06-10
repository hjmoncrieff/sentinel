from __future__ import annotations

import json

from scripts.analysis.build_country_dossiers import (
    CANONICAL_COUNTRIES as DOSSIER_CANONICAL_COUNTRIES,
    build_public_payload,
)
from scripts.analysis.validate_country_dossiers import (
    CANONICAL_COUNTRIES,
    SCHEMA,
    load_schema,
    required_fields_from_schema,
    validate_payload,
)


def _make_country_row(country: str) -> dict:
    return {
        "country": country,
        "iso2": "XX",
        "iso3": "XXX",
        "subregion": "Test",
        "generated_at": "2026-06-06T00:00:00Z",
        "public_freshness": {
            "structural_as_of_year": 2025,
            "events_as_of_date": "2026-06-06",
            "monitor_generated_at": "2026-06-06T00:00:00Z",
            "series_coverage_note": "Coverage through 2025.",
        },
        "public_summary": {
            "overall_risk_score": 2.5,
            "overall_risk_level": "medium",
            "leading_construct": "civilian_control",
            "leading_label": "Civilian Control",
            "leading_trend": "stable",
            "summary_text": "Monitoring remains steady.",
            "watchpoints": ["Leadership reshuffles", "Force posture changes"],
        },
        "public_structural_cards": [
            {
                "code": "mil_exp_pct_gdp",
                "label": "Military Spending",
                "current_value": 1.6,
                "display_value": "1.6%",
                "unit": "percent",
                "as_of_year": 2025,
                "trend_series": [1.2, 1.4, 1.6],
            }
        ],
        "public_construct_series": [
            {
                "code": "civilian_control",
                "label": "Civilian Control",
            }
        ],
        "public_predictive_series": [
            {
                "code": "regime_vulnerability",
                "label": "Regime Vulnerability",
                "current_score": 48.1,
                "display_score": "48.1/100",
                "level": "guarded",
                "trend_label": "stable",
                "as_of_year": 2025,
                "trend_series": [
                    {"year": 2023, "score": 42.0},
                    {"year": 2024, "score": 45.5},
                    {"year": 2025, "score": 48.1},
                ],
            }
        ],
        "public_context": {
            "capital": "Test Capital",
            "regime": "Democracy",
            "cmr_status": "Stable",
            "cmr_class": "Stable",
            "note": "Baseline note.",
            "key_positions": [{"title": "Defense Minister", "name": "Alex Doe"}],
            "next_election": {"date": "2027-01-01", "type": "presidential"},
            "country_watch": "Watch succession dynamics.",
            "special_profile_id": None,
        },
    }


def _make_payload() -> dict:
    rows = [_make_country_row(country) for country in sorted(CANONICAL_COUNTRIES)]
    return {
        "generated_at": "2026-06-06T00:00:00Z",
        "count": len(rows),
        "countries": rows,
    }


def test_build_public_payload_returns_canonical_country_rows() -> None:
    structural_rows = []
    monitor_rows = []
    context_rows = []
    predictive_panel_rows = []
    latent_rows = []

    for index, (country, iso2, iso3, subregion) in enumerate(DOSSIER_CANONICAL_COUNTRIES):
        structural_rows.extend([
            {
                "country": country,
                "year": 2023,
                "iso2": iso2,
                "iso3": iso3,
                "subregion": subregion,
                "polyarchy": round(0.55 + index * 0.005, 3),
                "mil_constrain": round(0.45 + index * 0.004, 3),
                "mil_exec": round(0.18 + index * 0.003, 3),
                "wgi_rule_of_law": round(-0.4 + index * 0.03, 3),
                "mil_exp_pct_gdp": round(1.0 + index * 0.05, 3),
                "inflation_consumer_prices_pct": round(2.5 + index * 0.4, 3),
            },
            {
                "country": country,
                "year": 2024,
                "iso2": iso2,
                "iso3": iso3,
                "subregion": subregion,
                "polyarchy": round(0.57 + index * 0.005, 3),
                "mil_constrain": round(0.47 + index * 0.004, 3),
                "mil_exec": round(0.2 + index * 0.003, 3),
                "wgi_rule_of_law": round(-0.35 + index * 0.03, 3),
                "mil_exp_pct_gdp": round(1.1 + index * 0.05, 3),
                "inflation_consumer_prices_pct": round(3.0 + index * 0.4, 3),
            },
        ])
        monitor_rows.append({
            "country": country,
            "generated_at": "2026-06-06T00:00:00Z",
            "predictive_summary": {
                "overall_risk_score": 48.0 if country == "Brazil" else round(35.0 + index, 1),
                "overall_risk_level": "elevated" if country == "Brazil" else "medium",
                "leading_construct": "regime_vulnerability",
                "leading_label": "Regime Vulnerability",
                "leading_trend": "stable",
                "summary_text": f"{country} monitor summary.",
                "watchpoints": [f"{country} watchpoint 1", f"{country} watchpoint 2"],
            },
            "risk_constructs": [
                {"code": "regime_vulnerability", "label": "Regime Vulnerability", "score": 48.0 if country == "Brazil" else round(35.0 + index, 1), "level": "elevated", "trend_label": "stable"},
                {"code": "militarization", "label": "Militarization", "score": round(30.0 + index, 1), "level": "medium", "trend_label": "stable"},
                {"code": "security_fragmentation", "label": "Security Fragmentation", "score": round(28.0 + index, 1), "level": "medium", "trend_label": "rising"},
            ],
            "top_pulse_events": [
                {"event_date": "2026-06-05"},
            ],
        })
        context_rows.append({
            "country": country,
            "capital": f"{country} City",
            "regime": "Democracy",
            "cmr_status": "Stable",
            "cmr_class": "Stable",
            "note": f"{country} note.",
            "key_positions": [{"title": "Defense Minister", "name": f"{country} Minister"}],
            "next_election": {"date": "2027-01-01", "type": "presidential"},
            "country_watch": f"{country} watch.",
            "special_profile_id": None,
        })
        predictive_panel_rows.extend([
            {
                "country": country,
                "panel_date": "2024-06-01",
                "acute_political_risk_signal_score_next_3m": 1,
                "episode_construct_regime_vulnerability_count_12m": 1,
                "episode_construct_militarization_count_12m": 1,
                "episode_construct_security_fragmentation_count_12m": 1,
                "security_fragmentation_jump_signal_score_next_3m": 1,
                "event_type_oc_count_12m": 1,
                "event_type_conflict_count_12m": 0,
                "event_type_protest_count_12m": 0,
                "fragmenting_episode_count_12m": 0,
                "regime_shift_flag": 0,
                "sentinel_exception_rule_militarization_count_y": 0,
            },
            {
                "country": country,
                "panel_date": "2025-12-01",
                "acute_political_risk_signal_score_next_3m": 2,
                "episode_construct_regime_vulnerability_count_12m": 2,
                "episode_construct_militarization_count_12m": 1,
                "episode_construct_security_fragmentation_count_12m": 2,
                "security_fragmentation_jump_signal_score_next_3m": 2,
                "event_type_oc_count_12m": 1,
                "event_type_conflict_count_12m": 1,
                "event_type_protest_count_12m": 1,
                "fragmenting_episode_count_12m": 1,
                "regime_shift_flag": 1 if country == "Brazil" else 0,
                "sentinel_exception_rule_militarization_count_y": 1 if country == "Brazil" else 0,
            },
        ])
        latent_rows.extend([
            {
                "country": country,
                "year": 2024,
                "civilian_control_latent_v0_score": round(65.0 - index * 0.8, 3),
                "militarization_latent_v0_score": round(30.0 + index * 1.1, 3),
            },
            {
                "country": country,
                "year": 2025,
                "civilian_control_latent_v0_score": round(63.0 - index * 0.8, 3),
                "militarization_latent_v0_score": round(31.0 + index * 1.1, 3),
            },
        ])

    payload = build_public_payload(
        structural_rows=structural_rows,
        monitor_rows=monitor_rows,
        context_rows=context_rows,
        predictive_panel_rows=predictive_panel_rows,
        latent_rows=latent_rows,
    )

    assert payload["count"] == 25
    brazil = next((row for row in payload["countries"] if row["country"] == "Brazil"), None)
    assert brazil is not None
    assert brazil["public_summary"]["overall_risk_score"] == 48.0
    assert brazil["public_structural_cards"][0]["code"] == "polyarchy"
    assert brazil["public_predictive_series"][0]["code"] == "regime_vulnerability"
    assert brazil["public_predictive_series"][0]["trend_series"][-1]["year"] == 2025


def test_build_public_payload_validates_with_realistic_monitor_timestamp() -> None:
    structural_rows = []
    monitor_rows = []
    context_rows = []
    predictive_panel_rows = []
    latent_rows = []

    for index, (country, iso2, iso3, subregion) in enumerate(DOSSIER_CANONICAL_COUNTRIES):
        structural_rows.extend([
            {
                "country": country,
                "year": 2023,
                "iso2": iso2,
                "iso3": iso3,
                "subregion": subregion,
                "polyarchy": round(0.5 + index * 0.004, 3),
                "mil_constrain": round(0.42 + index * 0.003, 3),
                "mil_exec": round(0.16 + index * 0.002, 3),
                "wgi_rule_of_law": round(-0.3 + index * 0.02, 3),
                "mil_exp_pct_gdp": round(1.2 + index * 0.03, 3),
                "inflation_consumer_prices_pct": round(3.5 + index * 0.25, 3),
            },
            {
                "country": country,
                "year": 2024,
                "iso2": iso2,
                "iso3": iso3,
                "subregion": subregion,
                "polyarchy": round(0.52 + index * 0.004, 3),
                "mil_constrain": round(0.44 + index * 0.003, 3),
                "mil_exec": round(0.18 + index * 0.002, 3),
                "wgi_rule_of_law": round(-0.25 + index * 0.02, 3),
                "mil_exp_pct_gdp": round(1.3 + index * 0.03, 3),
                "inflation_consumer_prices_pct": round(3.9 + index * 0.25, 3),
            },
        ])
        monitor_rows.append({
            "country": country,
            "generated_at": "2026-06-06T00:00:00+00:00",
            "predictive_summary": {
                "overall_risk_score": round(40.0 + index * 0.5, 2),
                "overall_risk_level": None if country == "Brazil" else "medium",
                "leading_construct": None if country == "Brazil" else "regime_vulnerability",
                "leading_label": None if country == "Brazil" else "Regime Vulnerability",
                "leading_trend": None if country == "Brazil" else "stable",
                "summary_text": None if country == "Brazil" else f"{country} summary.",
                "watchpoints": [f"{country} watchpoint", None],
            },
            "risk_constructs": [
                {
                    "code": "regime_vulnerability",
                    "label": "Regime Vulnerability",
                    "score": 41.5,
                    "level": "elevated",
                    "trend_label": "stable",
                },
                {
                    "code": "militarization",
                    "label": "Militarization",
                    "score": 37.0,
                    "level": "medium",
                    "trend_label": "stable",
                },
            ],
            "top_pulse_events": [
                {"event_date": "2026-06-05"},
                {"event_date": "2026-06-04"},
            ],
        })
        context_rows.append({
            "country": country,
            "capital": f"{country} City",
            "regime": "Democracy",
            "cmr_status": "Stable",
            "cmr_class": "Stable",
            "note": f"{country} note.",
            "key_positions": [{"title": "Defense Minister", "name": f"{country} Minister"}],
            "next_election": {"date": "2027-01-01", "type": "presidential"},
            "country_watch": f"{country} watch.",
            "special_profile_id": None,
        })
        predictive_panel_rows.append({
            "country": country,
            "panel_date": "2025-12-01",
            "acute_political_risk_signal_score_next_3m": 1,
            "episode_construct_regime_vulnerability_count_12m": 1,
            "episode_construct_militarization_count_12m": 1,
            "episode_construct_security_fragmentation_count_12m": 1,
            "security_fragmentation_jump_signal_score_next_3m": 1,
            "event_type_oc_count_12m": 1,
            "event_type_conflict_count_12m": 0,
            "event_type_protest_count_12m": 0,
            "fragmenting_episode_count_12m": 0,
            "regime_shift_flag": 0,
            "sentinel_exception_rule_militarization_count_y": 0,
        })
        latent_rows.append({
            "country": country,
            "year": 2024,
            "civilian_control_latent_v0_score": round(58.0 - index * 0.3, 3),
            "militarization_latent_v0_score": round(33.0 + index * 0.2, 3),
        })

    payload = build_public_payload(
        structural_rows=structural_rows,
        monitor_rows=monitor_rows,
        context_rows=context_rows,
        predictive_panel_rows=predictive_panel_rows,
        latent_rows=latent_rows,
    )
    result = validate_payload(payload)
    brazil = next(row for row in payload["countries"] if row["country"] == "Brazil")

    assert result["status"] == "valid"
    assert result["errors"] == []
    assert payload["count"] == 25
    assert brazil["public_freshness"]["monitor_generated_at"] == "2026-06-06T00:00:00Z"
    assert brazil["public_summary"]["overall_risk_level"] == ""
    assert brazil["public_summary"]["leading_construct"] == ""
    assert brazil["public_summary"]["leading_label"] == ""
    assert brazil["public_summary"]["leading_trend"] == ""
    assert brazil["public_summary"]["summary_text"] == ""


def test_build_public_payload_handles_empty_scores_and_null_next_election_fields() -> None:
    structural_rows = []
    monitor_rows = []
    context_rows = []
    predictive_panel_rows = []
    latent_rows = []

    for index, (country, iso2, iso3, subregion) in enumerate(DOSSIER_CANONICAL_COUNTRIES):
        structural_rows.append({
            "country": country,
            "year": 2024,
            "iso2": iso2,
            "iso3": iso3,
            "subregion": subregion,
            "polyarchy": round(0.6 + index * 0.003, 3),
            "mil_constrain": round(0.5 + index * 0.003, 3),
            "mil_exec": round(0.2 + index * 0.002, 3),
            "wgi_rule_of_law": round(-0.2 + index * 0.02, 3),
            "mil_exp_pct_gdp": round(1.0 + index * 0.04, 3),
            "inflation_consumer_prices_pct": round(3.0 + index * 0.3, 3),
        })
        monitor_rows.append({
            "country": country,
            "generated_at": "2026-06-06T00:00:00+00:00",
            "predictive_summary": {
                "overall_risk_score": None if country == "Brazil" else ("" if country == "Chile" else "bad"),
                "overall_risk_level": "medium",
                "leading_construct": "regime_vulnerability",
                "leading_label": "Regime Vulnerability",
                "leading_trend": "stable",
                "summary_text": f"{country} summary.",
                "watchpoints": [f"{country} watchpoint"],
            },
            "risk_constructs": [
                {"code": "regime_vulnerability", "label": "Regime Vulnerability"},
            ],
            "top_pulse_events": [{"event_date": "2026-06-05"}],
        })
        context_rows.append({
            "country": country,
            "capital": f"{country} City",
            "regime": "Democracy",
            "cmr_status": "Stable",
            "cmr_class": "Stable",
            "note": f"{country} note.",
            "key_positions": [{"title": "Defense Minister", "name": f"{country} Minister"}],
            "next_election": {"date": None, "type": None},
            "country_watch": f"{country} watch.",
            "special_profile_id": None,
        })
        predictive_panel_rows.append({
            "country": country,
            "panel_date": "2025-12-01",
            "acute_political_risk_signal_score_next_3m": 0,
            "episode_construct_regime_vulnerability_count_12m": 0,
            "episode_construct_militarization_count_12m": 0,
            "episode_construct_security_fragmentation_count_12m": 0,
            "security_fragmentation_jump_signal_score_next_3m": 0,
            "event_type_oc_count_12m": 0,
            "event_type_conflict_count_12m": 0,
            "event_type_protest_count_12m": 0,
            "fragmenting_episode_count_12m": 0,
            "regime_shift_flag": 0,
            "sentinel_exception_rule_militarization_count_y": 0,
        })
        latent_rows.append({
            "country": country,
            "year": 2024,
            "civilian_control_latent_v0_score": round(62.0 - index * 0.2, 3),
            "militarization_latent_v0_score": round(29.0 + index * 0.2, 3),
        })

    payload = build_public_payload(
        structural_rows=structural_rows,
        monitor_rows=monitor_rows,
        context_rows=context_rows,
        predictive_panel_rows=predictive_panel_rows,
        latent_rows=latent_rows,
    )
    result = validate_payload(payload)
    brazil = next(row for row in payload["countries"] if row["country"] == "Brazil")
    chile = next(row for row in payload["countries"] if row["country"] == "Chile")

    assert result["status"] == "valid"
    assert brazil["public_summary"]["overall_risk_score"] == 0.0
    assert chile["public_summary"]["overall_risk_score"] == 0.0
    assert brazil["public_context"]["next_election"]["date"] == "1900-01-01"
    assert brazil["public_context"]["next_election"]["type"] == "unknown"


def test_schema_requires_public_payload_fields() -> None:
    schema = load_schema()

    assert schema["required"] == ["generated_at", "countries"]
    assert schema["properties"]["count"]["type"] == "integer"
    assert schema["properties"]["countries"]["items"]["properties"]["public_structural_cards"]["items"]["properties"]["current_value"]["type"] == ["number", "null"]
    assert schema["properties"]["countries"]["items"]["properties"]["public_predictive_series"]["items"]["properties"]["current_score"]["type"] == "number"
    row_required = schema["properties"]["countries"]["items"]["required"]
    assert row_required == [
        "country",
        "iso2",
        "iso3",
        "subregion",
        "generated_at",
        "public_freshness",
        "public_summary",
        "public_structural_cards",
        "public_construct_series",
        "public_predictive_series",
        "public_context",
    ]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["countries"]["items"]["additionalProperties"] is False
    assert schema["properties"]["generated_at"]["pattern"] == "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z$"


def test_validate_payload_rejects_noncanonical_country_rows() -> None:
    payload = _make_payload()
    payload["countries"][0]["country"] = "Atlantis"

    result = validate_payload(payload)

    assert result["status"] == "invalid"
    assert result["count"] == len(CANONICAL_COUNTRIES)
    assert any("noncanonical country: Atlantis" in error for error in result["errors"])


def test_validate_payload_accepts_fully_valid_payload() -> None:
    result = validate_payload(_make_payload())

    assert result["status"] == "valid"
    assert result["errors"] == []
    assert result["count"] == len(CANONICAL_COUNTRIES)


def test_validate_payload_rejects_duplicate_and_missing_canonical_countries() -> None:
    payload = _make_payload()
    payload["countries"][0]["country"] = payload["countries"][1]["country"]

    result = validate_payload(payload)

    replaced_country = sorted(CANONICAL_COUNTRIES)[0]
    duplicate_country = sorted(CANONICAL_COUNTRIES)[1]
    assert result["status"] == "invalid"
    assert any(f"duplicates canonical country: {duplicate_country}" in error for error in result["errors"])
    assert any(f"Missing canonical country row: {replaced_country}" in error for error in result["errors"])


def test_validate_payload_rejects_private_fields_in_public_payload() -> None:
    payload = _make_payload()
    payload["countries"][0]["private_notes"] = "internal only"

    result = validate_payload(payload)

    assert result["status"] == "invalid"
    assert result["count"] == len(CANONICAL_COUNTRIES)
    assert any("private field not allowed in public payload: private_notes" in error for error in result["errors"])


def test_validate_payload_rejects_countries_when_not_a_list() -> None:
    payload = _make_payload()
    payload["countries"] = {"country": "Brazil"}

    result = validate_payload(payload)

    assert result["status"] == "invalid"
    assert result["count"] == 0
    assert "Top-level field 'countries' must be a list." in result["errors"]


def test_validate_payload_rejects_invalid_generated_at_format() -> None:
    payload = _make_payload()
    payload["generated_at"] = "2026-06-06"

    result = validate_payload(payload)

    assert result["status"] == "invalid"
    assert "Top-level field 'generated_at' must match the required timestamp pattern." in result["errors"]


def test_validate_payload_rejects_invalid_iso_formats() -> None:
    payload = _make_payload()
    payload["countries"][0]["iso2"] = "X"
    payload["countries"][0]["iso3"] = "XXXX"

    result = validate_payload(payload)

    assert result["status"] == "invalid"
    assert "Country row 0 field 'iso2' must match the required pattern." in result["errors"]
    assert "Country row 0 field 'iso3' must match the required pattern." in result["errors"]


def test_validate_payload_rejects_unexpected_extra_row_field() -> None:
    payload = _make_payload()
    payload["countries"][0]["extra_field"] = "not allowed"

    result = validate_payload(payload)

    assert result["status"] == "invalid"
    assert "Country row 0 has unexpected field: extra_field" in result["errors"]


def test_validate_payload_rejects_non_string_country_and_subregion() -> None:
    payload = _make_payload()
    payload["countries"][0]["country"] = 123
    payload["countries"][0]["subregion"] = ["Andean"]

    result = validate_payload(payload)

    assert result["status"] == "invalid"
    assert "Country row 0 field 'country' must be of type string." in result["errors"]
    assert "Country row 0 field 'subregion' must be of type string." in result["errors"]


def test_validate_payload_rejects_public_field_type_mismatches() -> None:
    payload = _make_payload()
    payload["countries"][0]["public_structural_cards"] = {}
    payload["countries"][0]["public_context"] = []

    result = validate_payload(payload)

    assert result["status"] == "invalid"
    assert "Country row 0 field 'public_structural_cards' must be of type array." in result["errors"]
    assert "Country row 0 field 'public_context' must be of type object." in result["errors"]


def test_validate_payload_rejects_malformed_structural_card_item() -> None:
    payload = _make_payload()
    payload["countries"][0]["public_structural_cards"][0] = {
        "code": "mil_spend_pct_gdp",
        "label": "Military Spending",
        "current_value": 1.6,
        "display_value": "1.6%",
        "unit": "percent",
        "as_of_year": 2025,
        "trend_series": {},
    }

    result = validate_payload(payload)

    assert result["status"] == "invalid"
    assert (
        "Country row 0 field 'public_structural_cards' item 0 field 'trend_series' "
        "must be of type array."
    ) in result["errors"]


def test_validate_payload_rejects_invalid_structural_card_current_value_object() -> None:
    payload = _make_payload()
    payload["countries"][0]["public_structural_cards"][0]["current_value"] = {"value": 1.6}

    result = validate_payload(payload)

    assert result["status"] == "invalid"
    assert (
        "Country row 0 field 'public_structural_cards' item 0 field 'current_value' "
        "must be of type ['number', 'null']."
    ) in result["errors"]


def test_validate_payload_rejects_non_string_watchpoints() -> None:
    payload = _make_payload()
    payload["countries"][0]["public_summary"]["watchpoints"] = ["ok", 5]

    result = validate_payload(payload)

    assert result["status"] == "invalid"
    assert (
        "Country row 0 field 'public_summary' field 'watchpoints' item 1 must be of type string."
    ) in result["errors"]


def test_validate_payload_rejects_invalid_trend_series_item_type() -> None:
    payload = _make_payload()
    payload["countries"][0]["public_structural_cards"][0]["trend_series"] = [1.2, "bad"]

    result = validate_payload(payload)

    assert result["status"] == "invalid"
    assert (
        "Country row 0 field 'public_structural_cards' item 0 field 'trend_series' item 1 "
        "must be of type number."
    ) in result["errors"]


def test_validate_payload_rejects_malformed_public_construct_series_item() -> None:
    payload = _make_payload()
    payload["countries"][0]["public_construct_series"][0] = {"code": "civilian_control"}

    result = validate_payload(payload)

    assert result["status"] == "invalid"
    assert (
        "Country row 0 field 'public_construct_series' item 0 missing required field: label"
    ) in result["errors"]


def test_validate_payload_rejects_malformed_public_predictive_series_item() -> None:
    payload = _make_payload()
    payload["countries"][0]["public_predictive_series"][0] = {
        "code": "regime_vulnerability",
        "label": "Regime Vulnerability",
        "current_score": 48.1,
        "display_score": "48.1/100",
        "level": "guarded",
        "trend_label": "stable",
        "as_of_year": 2025,
        "trend_series": [{"year": "2025", "score": 48.1}],
    }

    result = validate_payload(payload)

    assert result["status"] == "invalid"
    assert (
        "Country row 0 field 'public_predictive_series' item 0 field 'trend_series' item 0 field 'year' "
        "must be of type integer."
    ) in result["errors"]


def test_validate_payload_rejects_malformed_key_positions_item() -> None:
    payload = _make_payload()
    payload["countries"][0]["public_context"]["key_positions"][0] = {"title": "Defense Minister"}

    result = validate_payload(payload)

    assert result["status"] == "invalid"
    assert (
        "Country row 0 field 'public_context' field 'key_positions' item 0 missing required field: name"
    ) in result["errors"]


def test_validate_payload_rejects_malformed_next_election_object() -> None:
    payload = _make_payload()
    payload["countries"][0]["public_context"]["next_election"] = {"date": "2027/01/01"}

    result = validate_payload(payload)

    assert result["status"] == "invalid"
    assert (
        "Country row 0 field 'public_context' field 'next_election' missing required field: type"
    ) in result["errors"]
    assert (
        "Country row 0 field 'public_context' field 'next_election' field 'date' "
        "must match the required pattern."
    ) in result["errors"]


def test_validate_payload_rejects_invalid_special_profile_id_type() -> None:
    payload = _make_payload()
    payload["countries"][0]["public_context"]["special_profile_id"] = 7

    result = validate_payload(payload)

    assert result["status"] == "invalid"
    assert (
        "Country row 0 field 'public_context' field 'special_profile_id' "
        "must be of type ['string', 'null']."
    ) in result["errors"]


def test_validator_required_fields_match_schema() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    top_level_required, country_required = required_fields_from_schema(schema)

    assert top_level_required == {"generated_at", "countries"}
    assert country_required == {
        "country",
        "iso2",
        "iso3",
        "subregion",
        "generated_at",
        "public_freshness",
        "public_summary",
        "public_structural_cards",
        "public_construct_series",
        "public_predictive_series",
        "public_context",
    }
