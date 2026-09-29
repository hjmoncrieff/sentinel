#!/usr/bin/env python3
"""
Validate public country dossier payloads.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.analysis.build_country_dossiers import OUT as DEFAULT_PAYLOAD

SCHEMA = ROOT / "config" / "schemas" / "country_dossier_public.schema.json"

CANONICAL_COUNTRIES = {
    "Argentina",
    "Belize",
    "Bolivia",
    "Brazil",
    "Chile",
    "Colombia",
    "Costa Rica",
    "Cuba",
    "Dominican Republic",
    "Ecuador",
    "El Salvador",
    "Guatemala",
    "Guyana",
    "Haiti",
    "Honduras",
    "Jamaica",
    "Mexico",
    "Nicaragua",
    "Panama",
    "Paraguay",
    "Peru",
    "Suriname",
    "Trinidad and Tobago",
    "Uruguay",
    "Venezuela",
}

PRIVATE_FIELD_PREFIXES = ("private_",)

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_schema() -> dict:
    return load_json(SCHEMA)


def required_fields_from_schema(schema: dict) -> tuple[set[str], set[str]]:
    top_level_required = set(schema.get("required", []))
    country_required = set(
        schema.get("properties", {})
        .get("countries", {})
        .get("items", {})
        .get("required", [])
    )
    return top_level_required, country_required


def _matches_pattern(value: object, pattern: str) -> bool:
    return isinstance(value, str) and re.fullmatch(pattern, value) is not None


def _matches_schema_type(value: object, expected_type: str) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "null":
        return value is None
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
    return True


def _matches_schema_types(value: object, expected_type: object) -> bool:
    if isinstance(expected_type, str):
        return _matches_schema_type(value, expected_type)
    if isinstance(expected_type, list):
        return any(_matches_schema_type(value, item) for item in expected_type if isinstance(item, str))
    return True


def _validate_object_against_schema(value: object, schema: dict, path: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path} must be of type object.")
        return

    properties = schema.get("properties", {})
    required_fields = schema.get("required", [])

    if schema.get("additionalProperties") is False:
        extra_fields = sorted(set(value) - set(properties))
        for field in extra_fields:
            errors.append(f"{path} has unexpected field: {field}")

    for field in required_fields:
        if field not in value:
            errors.append(f"{path} missing required field: {field}")

    for field, field_schema in properties.items():
        if field not in value:
            continue
        field_value = value[field]
        expected_type = field_schema.get("type")
        field_path = f"{path} field '{field}'"
        if not _matches_schema_types(field_value, expected_type):
            errors.append(f"{field_path} must be of type {expected_type}.")
            continue

        pattern = field_schema.get("pattern")
        if pattern and isinstance(field_value, str) and not _matches_pattern(field_value, pattern):
            errors.append(f"{field_path} must match the required pattern.")

        if field_schema.get("type") == "object":
            _validate_object_against_schema(field_value, field_schema, field_path, errors)

        items_schema = field_schema.get("items")
        if field_schema.get("type") == "array" and items_schema and isinstance(field_value, list):
            item_type = items_schema.get("type")
            for item_index, item in enumerate(field_value):
                item_path = f"{field_path} item {item_index}"
                if item_type and not _matches_schema_types(item, item_type):
                    errors.append(f"{item_path} must be of type {item_type}.")
                    continue
                if item_type == "object":
                    _validate_object_against_schema(item, items_schema, item_path, errors)


def validate_payload(payload: dict) -> dict:
    errors: list[str] = []
    schema = load_schema()
    required_top_level_fields, required_country_fields = required_fields_from_schema(schema)
    top_level_properties = schema.get("properties", {})
    row_schema = top_level_properties.get("countries", {}).get("items", {})
    row_properties = row_schema.get("properties", {})

    if not isinstance(payload, dict):
        return {
            "status": "invalid",
            "errors": ["Payload must be an object."],
            "count": 0,
        }

    if schema.get("additionalProperties") is False:
        extra_top_level_fields = sorted(set(payload) - set(top_level_properties))
        for field in extra_top_level_fields:
            errors.append(f"Unexpected top-level field: {field}")

    missing_top_level = sorted(required_top_level_fields - set(payload))
    for field in missing_top_level:
        errors.append(f"Missing top-level field: {field}")

    generated_at = payload.get("generated_at")
    generated_at_pattern = top_level_properties.get("generated_at", {}).get("pattern")
    if generated_at is not None and not isinstance(generated_at, str):
        errors.append("Top-level field 'generated_at' must be a string.")
    elif generated_at_pattern and generated_at is not None and not _matches_pattern(generated_at, generated_at_pattern):
        errors.append("Top-level field 'generated_at' must match the required timestamp pattern.")

    count_value = payload.get("count")
    count_type = top_level_properties.get("count", {}).get("type")
    if count_value is not None and count_type and not _matches_schema_types(count_value, count_type):
        errors.append(f"Top-level field 'count' must be of type {count_type}.")

    countries = payload.get("countries", [])
    if not isinstance(countries, list):
        return {
            "status": "invalid",
            "errors": errors + ["Top-level field 'countries' must be a list."],
            "count": 0,
        }

    if len(countries) != len(CANONICAL_COUNTRIES):
        errors.append(
            f"Expected {len(CANONICAL_COUNTRIES)} country rows but found {len(countries)}."
        )
    if count_value is not None and isinstance(count_value, int) and count_value != len(countries):
        errors.append(
            f"Top-level field 'count' must equal the number of country rows ({len(countries)})."
        )

    seen_countries: set[str] = set()
    canonical_countries_present: set[str] = set()

    for index, row in enumerate(countries):
        if not isinstance(row, dict):
            errors.append(f"Country row {index} must be an object.")
            continue

        if row_schema.get("additionalProperties") is False:
            extra_row_fields = sorted(set(row) - set(row_properties))
            for field in extra_row_fields:
                errors.append(f"Country row {index} has unexpected field: {field}")

        missing_row_fields = sorted(required_country_fields - set(row))
        for field in missing_row_fields:
            errors.append(f"Country row {index} missing required field: {field}")

        for field in sorted(required_country_fields):
            if field not in row:
                continue
            expected_type = row_properties.get(field, {}).get("type")
            if not _matches_schema_types(row[field], expected_type):
                errors.append(
                    f"Country row {index} field '{field}' must be of type {expected_type}."
                )

        row_generated_at = row.get("generated_at")
        row_generated_at_pattern = row_properties.get("generated_at", {}).get("pattern")
        if row_generated_at_pattern and row_generated_at is not None and not _matches_pattern(
            row_generated_at, row_generated_at_pattern
        ):
            errors.append(f"Country row {index} field 'generated_at' must match the required timestamp pattern.")

        iso2 = row.get("iso2")
        iso2_pattern = row_properties.get("iso2", {}).get("pattern")
        if iso2_pattern and iso2 is not None and not _matches_pattern(iso2, iso2_pattern):
            errors.append(f"Country row {index} field 'iso2' must match the required pattern.")

        iso3 = row.get("iso3")
        iso3_pattern = row_properties.get("iso3", {}).get("pattern")
        if iso3_pattern and iso3 is not None and not _matches_pattern(iso3, iso3_pattern):
            errors.append(f"Country row {index} field 'iso3' must match the required pattern.")

        for field in (
            "public_freshness",
            "public_summary",
            "public_context",
        ):
            if field in row and isinstance(row.get(field), dict):
                _validate_object_against_schema(
                    row[field],
                    row_properties.get(field, {}),
                    f"Country row {index} field '{field}'",
                    errors,
                )

        structural_cards = row.get("public_structural_cards")
        structural_card_schema = row_properties.get("public_structural_cards", {})
        structural_card_items_schema = structural_card_schema.get("items", {})
        if isinstance(structural_cards, list):
            for item_index, item in enumerate(structural_cards):
                item_path = f"Country row {index} field 'public_structural_cards' item {item_index}"
                _validate_object_against_schema(item, structural_card_items_schema, item_path, errors)

        construct_series = row.get("public_construct_series")
        construct_series_schema = row_properties.get("public_construct_series", {})
        construct_series_items_schema = construct_series_schema.get("items", {})
        construct_series_item_type = construct_series_items_schema.get("type")
        if isinstance(construct_series, list) and construct_series_item_type:
            for item_index, item in enumerate(construct_series):
                item_path = f"Country row {index} field 'public_construct_series' item {item_index}"
                if not _matches_schema_types(item, construct_series_item_type):
                    errors.append(
                        f"{item_path} must be of type {construct_series_item_type}."
                    )
                    continue
                if construct_series_item_type == "object":
                    _validate_object_against_schema(item, construct_series_items_schema, item_path, errors)

        predictive_series = row.get("public_predictive_series")
        predictive_series_schema = row_properties.get("public_predictive_series", {})
        predictive_series_items_schema = predictive_series_schema.get("items", {})
        predictive_series_item_type = predictive_series_items_schema.get("type")
        if isinstance(predictive_series, list) and predictive_series_item_type:
            for item_index, item in enumerate(predictive_series):
                item_path = f"Country row {index} field 'public_predictive_series' item {item_index}"
                if not _matches_schema_types(item, predictive_series_item_type):
                    errors.append(
                        f"{item_path} must be of type {predictive_series_item_type}."
                    )
                    continue
                if predictive_series_item_type == "object":
                    _validate_object_against_schema(item, predictive_series_items_schema, item_path, errors)

        country = row.get("country")
        if country not in CANONICAL_COUNTRIES:
            errors.append(f"Country row {index} has noncanonical country: {country}")
        elif country in seen_countries:
            errors.append(f"Country row {index} duplicates canonical country: {country}")
        else:
            seen_countries.add(country)
            canonical_countries_present.add(country)

        for key in row:
            if key.startswith(PRIVATE_FIELD_PREFIXES):
                errors.append(
                    f"Country row {index} contains private field not allowed in public payload: {key}"
                )

    missing_canonical_countries = sorted(CANONICAL_COUNTRIES - canonical_countries_present)
    for country in missing_canonical_countries:
        errors.append(f"Missing canonical country row: {country}")

    return {
        "status": "valid" if not errors else "invalid",
        "errors": errors,
        "count": len(countries),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a public country dossier payload.")
    parser.add_argument(
        "payload",
        type=Path,
        nargs="?",
        default=DEFAULT_PAYLOAD,
        help="Path to a JSON payload file",
    )
    args = parser.parse_args()

    payload = load_json(args.payload)
    result = validate_payload(payload)
    print(json.dumps(result, indent=2))

    if result["status"] != "valid":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
