from __future__ import annotations

import json

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
                "code": "mil_spend_pct_gdp",
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
        "countries": rows,
    }


def test_schema_requires_public_payload_fields() -> None:
    schema = load_schema()

    assert schema["required"] == ["generated_at", "countries"]
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
        "public_context",
    }
