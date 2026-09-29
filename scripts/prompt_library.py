"""
Versioned LLM prompt loader for SENTINEL.

Prompt text lives in `prompts/<name>.md`; `prompts/manifest.json` records each
prompt's consumer, model, and required placeholders. Placeholders are written as
`{name}` and substituted strictly: a missing or unexpected value raises instead
of silently sending a malformed prompt. Literal JSON braces in prompt files need
no escaping because only `{lowercase_identifier}` tokens are treated as fields.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT / "prompts"
MANIFEST_PATH = PROMPTS_DIR / "manifest.json"

PLACEHOLDER_RE = re.compile(r"\{([a-z_][a-z0-9_]*)\}")


@lru_cache(maxsize=1)
def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def prompt_spec(name: str) -> dict:
    prompts = load_manifest()["prompts"]
    if name not in prompts:
        raise KeyError(f"Unknown prompt {name!r}; registered: {sorted(prompts)}")
    return prompts[name]


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    """Return the raw prompt text (the file's single trailing newline is dropped)."""
    prompt_spec(name)
    text = (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    return text[:-1] if text.endswith("\n") else text


def placeholders(name: str) -> set[str]:
    return set(PLACEHOLDER_RE.findall(load_prompt(name)))


def render_prompt(name: str, **values: object) -> str:
    """Fill every `{placeholder}` in a prompt; keys must match exactly."""
    template = load_prompt(name)
    expected = placeholders(name)
    missing = expected - values.keys()
    unexpected = values.keys() - expected
    if missing or unexpected:
        raise ValueError(
            f"Prompt {name!r} placeholder mismatch: "
            f"missing={sorted(missing)} unexpected={sorted(unexpected)}"
        )
    return PLACEHOLDER_RE.sub(lambda m: str(values[m.group(1)]), template)


def model_for(name: str) -> str:
    """Model ID registered for a prompt in the manifest."""
    return prompt_spec(name)["model"]
