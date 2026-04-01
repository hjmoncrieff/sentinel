# SENTINEL System Workflow

## Purpose

This document describes the staged operating system that SENTINEL is becoming. It complements `docs/architecture.md` and `docs/pipeline-operations.md` by focusing on workflow boundaries and file contracts.

The project is designed as an AI-first system. Most routine work should be done
by automated ingestion, coding, QA, and analysis layers. Human users should
mainly intervene for correction, corroboration, duplicate resolution, manual
event consolidation when near-duplicates were missed upstream, and publication
control.

## Stage Model

### 1. Ingest

Primary files:

- `scripts/fetch_events.py`
- `scripts/rss_sources.py`
- `scripts/normalize_articles.py`
- `scripts/ingest_gdelt.py`

Outputs:

- live event store input data
- review-layer source audit

### 2. Review Diagnostics

Primary files:

- `scripts/qa/run_qa.py`
- `scripts/qa/run_registry_qa.py`
- `scripts/pipeline/detect_duplicates.py`
- `scripts/review/build_review_queue.py`
- `scripts/review/apply_analyst_edits.py`

Outputs:

- `data/review/qa_report.json`
- `data/review/registry_qa_report.json`
- `data/review/duplicate_candidates.json`
- `data/review/review_queue.json`
- `data/review/edits.local.json`
- `data/review/events_with_edits.json`
- `data/review/review_queue_with_edits.json`

### 3. Canonicalize

Primary files:

- `scripts/pipeline/build_canonical_events.py`
- `scripts/pipeline/code_actors.py`
- `scripts/pipeline/update_actor_registry.py`

Outputs:

- `data/canonical/events.json`
- `data/canonical/events.jsonl`
- `data/canonical/events_actor_coded.json`
- `data/canonical/events_actor_coded.jsonl`
- `data/canonical/actor_mentions.json`
- `config/actors/actor_registry.json`

### 4. Publish

Primary file:

- `scripts/publish/publish_dashboard_data.py`

Output:

- `data/published/events_public.json`

The published payload is public-safe and now carries review-state metadata for
the dashboard:

- `review_status`
- `review_priority`
- `human_validated`
- `provenance_summary.reviewed_by_human`

Private analyst fields such as `analyst_reasoning`, detailed review notes, and
local credential data remain outside the published layer.

Publication policy is now explicit:

- low-confidence events require human corroboration before publication
- merged duplicates are withheld
- records in blocked review states such as `flagged`, `needs_revision`, and
  `rejected` are withheld

### 5. Council Analysis

Primary file:

- `scripts/analysis/run_council.py`

Output:

- `data/review/council_analyses.json`

Council analysis now runs across every event, not only reviewed events, but the
resulting records are explicitly labeled as `AI-generated analysis`.

The council layer is informed by structured analyst knowledge assets:

- `config/agents/analyst_knowledge.json`
- `config/agents/council_guidance.json`
- `config/agents/council_roles.json`
- `config/agents/ai_workers.json`

The worker registry makes the AI-first architecture more explicit. It separates
routine automation into named roles such as:

- event classifier
- actor coder
- duplicate analyst
- QA scorer
- publication policy agent
- council analysts

## Data-Layer Contract

### `data/staging/`

Machine-generated intermediates. Not analyst reviewed.

Current staging artifacts include:

- `data/staging/raw_articles.json`
- `data/staging/filtered_articles.json`
- `data/staging/event_article_links.json`

### `data/review/`

Operational artifacts for analyst workflow and QA prioritization.

This layer now also holds human edit persistence and clearance-aware review state.
It is also where analysts can reverse high-consequence actions without deleting
the audit trail, such as undoing duplicate decisions, undoing QA resolutions, or
restoring rejected and publication-facing decisions.

### `data/canonical/`

Schema-aligned event and actor layers used for internal analysis and review.
These records now include a structured provenance timeline under
`provenance.timeline`.

The canonical builder also emits first-pass source/report linkage assets:

- `data/canonical/articles.json`
- `data/canonical/event_article_links.json`

These are derived from merged source and URL arrays in the live event store and
serve as the current bridge between clustered events and the underlying reports
that produced them.

### `data/published/`

Public-safe outputs intended for the dashboard and other read-only surfaces.

## Review Queue Logic

The review queue combines:

- event salience
- QA flags
- duplicate uncertainty
- upstream AI-worker supervision signals
- council-recommended analyst actions

This is an intervention queue, not the main production path. It is meant to
surface the subset of cases where human attention is most useful.

## Analyst Clearance Model

The analyst console now assumes three review tiers:

- `RA`
- `Analyst`
- `Coordinator`

These tiers are defined in `data/review/edits.local.json` during local operations, with `data/review/edits.template.json` providing the committed safe template. The current static console enforces them in the browser by disabling out-of-scope fields. The repo-side apply step enforces the same model when edits are materialized into review-layer outputs.

The intended role split is:

- `RA`: summary cleanup, review notes, actor coding cleanup
- `Analyst`: core event coding plus actor coding plus intermediate review states
- `Coordinator`: final approval and downstream-ready review states

These roles supervise AI output rather than replacing it with manual coding by
default.

Actor follow-up is part of this supervision loop. Analysts can create actors,
mark them uncertain, add aliases and relationship tags, and move them through a
lightweight registry workflow:

- `needs_registry_entry`
- `registry_seeded`
- `registry_confirmed`

The analyst console now also supports bulk actor follow-up actions in the
`Actor Registry` queue so reviewers can seed or confirm registry status and
clear actor uncertainty across multiple selected events without opening every
record one by one. Registry QA issues can then be resolved from the same
workspace by merging duplicate registry entries or dropping a conflicting alias
from one entry without forcing a full merge.

The workflow bridge from review to durable knowledge is
`scripts/pipeline/update_actor_registry.py`, which promotes reviewed actor
records into `config/actors/actor_registry.json`.

## Edit Persistence Workflow

Because the analyst console is still static, edit persistence happens in two steps:

1. Analysts make edits in the browser and save local drafts.
2. Analysts export the combined payload back into `data/review/edits.local.json`.
3. The repo applies those edits with `scripts/review/apply_analyst_edits.py`.

This keeps the workflow file-based for now while preserving a clean transition
path toward a future authenticated backend. The larger design goal remains
AI-first production with targeted human intervention.

## Local Authenticated Analyst Server

SENTINEL now includes a small local authenticated server:

- `scripts/review/run_analyst_server.py`

This server:

- serves the repo as a local web root
- handles analyst login and session state
- enforces role-based edit permissions
- writes analyst edits directly into `data/review/edits.local.json`
- reruns `scripts/review/apply_analyst_edits.py` after successful saves

Credential data lives in:

- `data/review/users.local.json`

This remains a local operations tool, not a production deployment path.

## Near-Term Target

The next version of SENTINEL should behave like this:

1. run ingest
2. generate QA, duplicates, and review queue
3. assemble canonical events
4. enrich actors
5. generate AI council analysis
6. expose review artifacts in the analyst console
7. publish a public-safe dataset

This is the shift from a script collection to a system.
