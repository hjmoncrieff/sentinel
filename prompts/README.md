# prompts/

This directory holds the versioned LLM prompts used by the SENTINEL pipeline. It is public.

Every prompt the pipeline sends to Claude lives here as plain text instead of an inline
Python string. That way, prompt changes show up as reviewable diffs, and you can read
the prompts without digging through code.

## Files

| Prompt | Consumer | Model | Placeholders |
|---|---|---|---|
| `classify_events.md` | `scripts/pipeline_core.py::_classify_batch` | Haiku 4.5 | `items` |
| `cluster_events.md` | `scripts/pipeline_core.py::_cluster_events` | Haiku 4.5 | `items`, `n` |
| `event_analysis.md` | `scripts/pipeline_core.py::generate_analysis` | Haiku 4.5 | `country`, `summary`, `title`, `type` |
| `council_framework.md` | `scripts/analysis/run_council_synthesis.py` (cached system prompt) | Sonnet 4.6 | — |
| `council_synthesis_role.md` | `scripts/analysis/run_council_synthesis.py` (cached system prompt) | Sonnet 4.6 | — |
| `council_quality_judge_system.md` | `scripts/analysis/validate_council_quality.py` | Haiku 4.5 | — |
| `council_quality_judge.md` | `scripts/analysis/validate_council_quality.py` | Haiku 4.5 | 8 event/synthesis fields |

`manifest.json` is the machine-readable registry. It records the consumer, the exact
model ID, the message role, the placeholders, and the purpose of each prompt. The code
reads model IDs from it, via `prompt_library.model_for()`. To change a model, edit the
manifest; don't edit the scripts.

The per-country structural block and the per-event user message in
`run_council_synthesis.py` are still built in code. They contain formatting logic,
not static instructions.

## Placeholder syntax

- Write placeholders as `{lowercase_name}`.
- Literal JSON braces need no escaping. Only `{identifier}` tokens count as fields.
- Rendering is strict. `render_prompt()` raises an error if the values you pass don't
  exactly match the placeholders in the file.

```python
from prompt_library import render_prompt, load_prompt, model_for

render_prompt("cluster_events", n=len(items), items=text)
load_prompt("council_framework")          # no placeholders
model_for("classify_events")              # "claude-haiku-4-5-20251001"
```

## Changing a prompt

1. Edit the `.md` file. Each file ends with exactly one trailing newline, which the loader
   strips.
2. If you add or remove a placeholder, update `manifest.json` and the calling code.
3. Run `pytest tests/test_prompt_library.py`. It checks that the manifest and the files
   agree.
4. Log the change in `CHANGELOG.md`. Prompt edits change the output data, so they count as
   major changes. Note which events or layers will need re-running.

The prompts were extracted from inline code on 2026-09-29. On that date, each rendered
prompt was verified byte-for-byte against the original inline template.
