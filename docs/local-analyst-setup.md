# Local Analyst Setup

This note now serves as a short setup reference. The full operating playbook is
in `docs/user-guide.md`.

## Goal

Keep the public repo free of:

- passwords
- analyst identity data
- live review edits

## Core Setup

```bash
python3 scripts/review/init_local_analyst_env.py
python3 scripts/review/hash_password.py
```

Then:

- add real password hashes to `data/review/users.local.json`
- start the server with `python3 scripts/review/run_analyst_server.py`

## Safe Files To Commit

Safe:

- `data/review/users.template.json`
- `data/review/edits.template.json`
- `data/review/registry_edits.template.json`

Never commit:

- `data/review/users.local.json`
- `data/review/edits.local.json`
- `data/review/registry_edits.local.json`
- `data/review/events_with_edits.json`
- `data/review/review_queue_with_edits.json`

For the full daily sequence, review workflow, duplicate handling, QA workflow,
and publication flow, use `docs/user-guide.md`.
