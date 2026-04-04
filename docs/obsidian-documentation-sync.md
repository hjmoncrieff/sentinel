# Obsidian Documentation Sync

SENTINEL mirrors its documentation set into the local Obsidian vault at:

- `/Users/hjmoncrieff/Library/CloudStorage/Dropbox/MyObsidiainVault/Sentinel Documentation`

This is a standing project rule.

## What gets mirrored

The mirror is for documentation and analyst-reference material, not for the
full live data layer.

Current scope:

- `docs/*.md`
- `docs/*.svg`
- `data/CODEBOOK.md`

That includes:

- workflows
- guides
- setup notes
- private architecture and modeling notes
- taxonomy reference
- console UI to-do notes
- diagram assets used by the docs

## Runner

Use:

```bash
python3 scripts/sync_obsidian_docs.py
```

Optional override:

```bash
python3 scripts/sync_obsidian_docs.py --target "/path/to/another/doc/mirror"
```

## Rule

Whenever a major documentation, workflow, guide, setup, or codebook change is
made in SENTINEL, the Obsidian mirror should be refreshed in the same work
session.

This is meant to keep the project’s working knowledge base synchronized between
the repo and the private Obsidian vault.
