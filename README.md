# SENTINEL

SENTINEL is an AI-first research platform for tracking civil-military
relations, political stability, and regional security events in Latin America
and the Caribbean. It combines automated event collection, classification,
actor coding, QA, and AI-generated analysis with a lighter human oversight
layer for review, validation, and publication decisions.

## What The Repo Contains

- a public dashboard in `index.html`
- a local analyst console in `apps/analyst-console/` for oversight, correction,
  and publication control
- ingestion and processing scripts in `scripts/`
- event, review, canonical, and published datasets in `data/`
- architecture and methodology notes in `docs/`

## Data Layers

- `data/events.json`
  Current live event store produced by the ingestion pipeline.
- `data/review/`
  QA outputs, duplicate candidates, review queues, and local analyst workflow
  artifacts.
- `data/canonical/`
  Schema-aligned internal event and actor datasets.
- `data/published/events_public.json`
  Public-safe event dataset for the dashboard, including review metadata such as
  `review_status`, `human_validated`, and provenance summary flags.

## Running The Public Dashboard

Serve the repo locally and open the dashboard in a browser:

```bash
python3 -m http.server
```

Then visit `http://127.0.0.1:8000/`.

## Architecture

SENTINEL is organized as a staged workflow:

1. ingest and normalize source material
2. generate QA and duplicate diagnostics
3. assemble canonical event records
4. code actors and enrich internal event structure
5. run modular AI workers for classification, actor coding, QA, publication checks, and AI-tagged council analysis
6. review exceptions, corrections, and publication decisions in the analyst console
7. publish a public-safe dataset for the dashboard

The public dashboard reads only from published outputs. Analyst credentials,
local review edits, private reasoning, and other sensitive workflow artifacts
are intentionally kept out of the public data layer.

Each event now carries a structured provenance timeline so both internal and
public-facing views can show how the record moved from ingestion through
classification, review, and publication. Canonical events also retain linked
report metadata so provenance can identify the specific articles or reports
that fed a clustered event.

The publication layer can enforce release rules. The current policy withholds
low-confidence events until they are corroborated by a human analyst, while
credible events can still be published and monitored publicly.

Internal council analysis is generated for every event, but it is explicitly
tagged as AI-generated analysis and kept separate from human review state.
The council now also records compact upstream AI-worker outputs and recommends
specific analyst follow-up actions such as actor review, duplicate review, or
human corroboration.

The AI worker registry that defines these production roles lives in
`config/agents/ai_workers.json`.

The intended operating model is AI-first:

- AI does the routine heavy lifting
- humans supervise uncertainty, sensitive cases, and release decisions
- the analyst console is an intervention layer, not the primary production engine

## Documentation

Public-facing and public-safe docs:

- `docs/architecture.md`
- `docs/ai-analyst-knowledge.md`
- `docs/next-steps.md`
- `docs/pipeline-operations.md`
- `docs/system-workflow.md`
- `docs/security-privacy.md`
- `data/CODEBOOK.md`

Operator playbook:

- `docs/user-guide.md`

## Security Note

This repository is designed to keep operationally sensitive analyst data out of
Git-tracked public outputs. Local credential files, private analyst reasoning,
and live review edits should remain in ignored local files only.
