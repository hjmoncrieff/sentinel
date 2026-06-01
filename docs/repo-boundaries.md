# SENTINEL Repo Boundaries

This document defines what belongs in the public GitHub repository, what should
remain local-only, and what should move into Supabase as the analyst backend is
introduced.

## Public GitHub

Keep these tracked:

- dashboard and analyst-console code
- ingestion, QA, review, publish, and analysis scripts
- schemas, taxonomies, and config files that are safe to share
- public-safe documentation
- template files for local setup
- public output artifacts in `data/published/`

## Local Only

Keep these untracked:

- credentials and environment files
- local analyst users and edit logs
- generated HTML exports of docs
- scratch planning files and interview notes
- archived design experiments not needed for the public codebase
- private diagrams, private roadmap notes, and other internal planning material
- large raw replication bundles and temporary source archives

## Supabase

Move mutable operational state here:

- analyst identities and roles
- authentication and sessions
- canonical event records after sync
- analyst edits and review decisions
- QA and duplicate resolutions
- publication approvals
- audit logs

## Source Of Truth

Use one owner for each class of data:

- GitHub: code, public-safe docs, templates, published static artifacts
- Local pipeline: ingestion, transformation, experimental analysis
- Supabase: authenticated analyst workflow and operational state

Do not maintain the same mutable workflow record in both Git-tracked JSON and
Supabase once the backend migration begins.

## Immediate Cleanup Rules

For the public repo:

- prefer Markdown source over rendered HTML copies
- keep `docs/private-*` local-only
- keep `apps/internal-tools/` local-only unless a tool is intentionally made
  public
- keep `archive/` local-only unless a historical artifact is still actively
  needed
- keep root-level one-off notes out of Git
