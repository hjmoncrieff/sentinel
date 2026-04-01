# SENTINEL Security And Privacy

## Public vs Local Boundary

SENTINEL now treats the repository as a mixed environment with a strict boundary:

- public-safe assets can live in GitHub
- analyst credentials and review edits must stay local

## Never Commit

The following files are local-only and should never be committed:

- `data/review/users.local.json`
- `data/review/edits.local.json`
- `data/review/registry_edits.local.json`
- `data/review/events_with_edits.json`
- `data/review/review_queue_with_edits.json`

## Safe Templates

The repo includes safe templates only:

- `data/review/users.template.json`
- `data/review/edits.template.json`
- `data/review/registry_edits.template.json`

To initialize a local analyst environment:

1. Copy `users.template.json` to `users.local.json`
2. Copy `edits.template.json` to `edits.local.json`
3. Generate password hashes with `python3 scripts/review/hash_password.py`
4. Replace the example values in `users.local.json`

You can also initialize those local files with:

- `python3 scripts/review/init_local_analyst_env.py`

## Analyst Server Boundary

`scripts/review/run_analyst_server.py` is a local operations tool.

It should:

- run only on localhost
- read only local credential/edit files
- refuse to start if local credential files are missing
- remain outside the public website deployment surface

The analyst console now also enforces a client-side host boundary:

- the public dashboard disables the analyst-access link on public hosts
- the analyst console refuses to unlock or load internal workspace data unless
  it is served from a trusted local/private host such as `localhost`,
  `127.0.0.1`, `.local`, or a private RFC1918 address

It is not intended for GitHub Pages or direct public deployment.

## Publication Rule

Only public-safe data should feed the public dashboard:

- `data/published/events_public.json`

Review artifacts, analyst notes, and local credentials are operational data and should not be part of the public publishing path.

This includes private analyst fields such as:

- local review notes
- private analyst reasoning
- QA resolution comments
- duplicate merge comments
- local registry edit comments
