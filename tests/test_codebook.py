from __future__ import annotations

import codebook
from prompt_library import render_prompt


def test_codebook_has_the_approved_shape():
    assert len(codebook.type_codes()) == 18
    assert "cooperation" in codebook.type_codes() and "coop" not in codebook.type_codes()
    assert "exercise" not in codebook.type_codes()
    assert len(codebook.deed_categories()) == 35
    assert {"intelligence", "prison_system", "criminal_org"} <= set(codebook.actor_groups())


def test_deed_axis_comes_from_the_category_group():
    assert codebook.deed_axis("4.1.8") == "horizontal"
    assert codebook.deed_axis("4.2.1") == "vertical"
    assert codebook.deed_axis(None) is None


def test_validate_catches_what_the_schema_cannot():
    item = {"relevant": True, "type": "purge", "subtype": "offensive", "secondary_types": ["purge"],
            "deed_type": "symptom", "deed_category": "3.2.6", "axis": "horizontal", "evidence": []}
    problems = " | ".join(codebook.validate(item))
    for expected in ("subtype offensive", "repeats the primary", "does not sit under symptom", "no evidence"):
        assert expected in problems


def test_normalize_derives_axis_and_trims():
    item = codebook.normalize({"type": "purge", "secondary_types": ["purge", "friction", "reform", "coup"],
                               "deed_category": "4.1.8", "axis": "vertical", "actors": [{}] * 6, "evidence": ["a", "b", "c"]})
    assert item["axis"] == "horizontal"
    assert item["secondary_types"] == ["friction", "reform"]
    assert len(item["actors"]) == 4 and len(item["evidence"]) == 2


def test_schema_and_prompt_render():
    schema = codebook.item_schema()
    assert schema["additionalProperties"] is False and set(schema["required"]) == set(schema["properties"])
    system = render_prompt("code_event_v3_system", codebook=codebook.render_definitions())
    assert "If deed_type = symptom, choose from 4.x" in system and "cooperation" in system


def test_v3_scripts_import():
    # Regression (2026-09-29): a misplaced `global` made enrich_ledes fail to compile.
    import importlib

    for name in ("enrich_ledes", "classify_v3", "review.gold_v3", "review.sample_gold_set"):
        importlib.import_module(name)
