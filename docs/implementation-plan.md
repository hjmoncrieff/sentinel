# SENTINEL Implementation Plan

## Guiding Principle

Build around the current repository rather than rewrite it. The existing static dashboard and nightly pipeline stay live while new review and validation layers are introduced in parallel.

## Phase 1

Phase 1 is designed to be low-risk and immediately useful.

### Deliverables

1. Machine-readable schema for canonical event records
2. Machine-readable taxonomy for event and actor coding
3. Duplicate-detection script that runs on the current `data/events.json`
4. QA report script that runs on the current `data/events.json`
5. Static analyst-console scaffold
6. Repo docs that define the target operating model

### Files Added In This Phase

- `docs/architecture.md`
- `docs/implementation-plan.md`
- `docs/pipeline-operations.md`
- `docs/system-workflow.md`
- `config/schemas/canonical_event.schema.json`
- `config/schemas/qa_flag.schema.json`
- `config/schemas/duplicate_candidate.schema.json`
- `config/taxonomy/event_types.json`
- `config/taxonomy/actor_types.json`
- `scripts/qa/run_qa.py`
- `scripts/pipeline/detect_duplicates.py`
- `apps/analyst-console/index.html`

### Recommended Next Files For Phase 2

- `scripts/pipeline/classify_events.py`
- `scripts/pipeline/code_actors.py`
- `scripts/pipeline/build_canonical_events.py`
- `scripts/review/build_review_queue.py`
- `scripts/publish/publish_dashboard_data.py`
- `docs/user-guide.md`
- `config/agents/*.json`
- `prompts/classification/*.md`
- `prompts/council/*.md`

## Current Repo Mapping

### Keep As-Is For Now

- `scripts/run_pipeline.py`
- `scripts/generate_clean_events.py`
- `index.html`
- `.github/workflows/fetch_events.yml`

### Wrap With New Layers

- `data/events.json` becomes the current source input to QA and duplicate detection
- `data/cleaned/events_clean.json` remains the current research export
- `data/review/` becomes the home for QA reports and duplicate candidates

## Proposed Execution Order

### Step 1

Use `scripts/qa/run_qa.py` after each pipeline run.

Output:

- `data/review/qa_report.json`

### Step 2

Use `scripts/pipeline/detect_duplicates.py` after QA.

Output:

- `data/review/duplicate_candidates.json`

### Step 3

Add an analyst review workflow that reads those artifacts.

### Step 4

Only after review exists, introduce the council of analytic agents.

## Phase 2 Goals

- Build canonical event assembly from event and article records
- Add actor coding
- Add rule-bound classifier with codebook references
- Add provenance timelines
- Export public-safe published data

## Phase 3 Goals

- Split `index.html` into modular assets
- Move country metadata out of inline JS
- Build a real authenticated analyst console

## Review Workflow Model

Review status values:

- `auto`
- `flagged`
- `reviewed`
- `published`
- `rejected`

Priority levels:

- `high`
- `medium`
- `low`

High-salience events and duplicate uncertainties should always enter the review queue.
