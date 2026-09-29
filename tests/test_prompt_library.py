from __future__ import annotations

import pytest

import prompt_library as pl


def test_every_manifest_prompt_has_a_file_and_matching_placeholders():
    for name, spec in pl.load_manifest()["prompts"].items():
        assert (pl.PROMPTS_DIR / f"{name}.md").is_file(), name
        assert pl.placeholders(name) == set(spec["placeholders"]), name
        assert spec["model"].startswith("claude-"), name


def test_every_prompt_file_is_registered():
    registered = set(pl.load_manifest()["prompts"])
    on_disk = {p.stem for p in pl.PROMPTS_DIR.glob("*.md") if p.name != "README.md"}
    assert on_disk == registered


def test_prompt_files_end_with_single_newline():
    for name in pl.load_manifest()["prompts"]:
        raw = (pl.PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
        assert raw.endswith("\n") and not raw.endswith("\n\n"), name


def test_render_fills_placeholders_and_keeps_literal_json_braces():
    out = pl.render_prompt("cluster_events", n=2, items="[0] A\n\n[1] B")
    assert "Below are 2 classified news items" in out
    assert "[0] A\n\n[1] B" in out
    judge = pl.render_prompt(
        "council_quality_judge",
        country="Peru", event_type="purge", salience="high", event_date="2026-01-01",
        headline="H", summary="S", synthesis_text="T", watchpoint="W",
    )
    assert '{"specificity": N, "grounding": N, "calibration": N' in judge


def test_render_does_not_reinterpret_braces_in_values():
    out = pl.render_prompt("classify_events", items="TITLE: {country} {items}")
    assert "TITLE: {country} {items}" in out


def test_render_rejects_missing_and_unexpected_values():
    with pytest.raises(ValueError, match="missing=\\['n'\\]"):
        pl.render_prompt("cluster_events", items="x")
    with pytest.raises(ValueError, match="unexpected=\\['extra'\\]"):
        pl.render_prompt("cluster_events", items="x", n=1, extra=True)


def test_unknown_prompt_raises():
    with pytest.raises(KeyError):
        pl.load_prompt("does_not_exist")
