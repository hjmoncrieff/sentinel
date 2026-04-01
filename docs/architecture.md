# SENTINEL Architecture

## Goal

SENTINEL is evolving from a static event dashboard into a research operations platform with two surfaces:

- Public dashboard: read-only publication layer for curated and published event data.
- Analyst console: credentialed workspace for review, QA, duplicate resolution, actor coding, and AI-assisted analysis.

The near-term architecture preserves the current GitHub Pages workflow while introducing a stronger internal data model and review workflow.

## Current Baseline

The repository currently centers on:

- `scripts/fetch_events.py`: ingestion and AI classification
- `scripts/generate_clean_events.py`: cleaned export generation
- `data/events.json`: live event store
- `index.html`: single-file public dashboard

This baseline remains intact for now. Phase 1 adds new layers around it without breaking the current dashboard.

## Target Data Flow

1. Source ingestion
   RSS, GDELT, NewsAPI, ACLED, and future structured sources produce article-level records.
2. Staging normalization
   Raw reports are normalized into a common article schema.
3. Duplicate detection
   Reports are clustered into likely event groups using deterministic and semantic rules.
4. Event classification
   Events are coded to a controlled taxonomy with rule references.
5. Actor coding
   Primary, secondary, and additional actors are extracted and normalized.
6. QA and review
   Flags are generated and routed to a credentialed analyst interface.
7. Council analysis
   Multiple analytic agents produce distinct interpretations over reviewed events.
8. Publication
   Public-safe outputs are written for the dashboard.

## Repository Shape

Near-term target layout:

```text
SENTINEL/
├── apps/
│   └── analyst-console/
├── config/
│   ├── agents/
│   ├── schemas/
│   └── taxonomy/
├── data/
│   ├── canonical/
│   ├── published/
│   ├── review/
│   ├── staging/
│   └── cleaned/
├── docs/
├── prompts/
├── scripts/
│   ├── pipeline/
│   ├── review/
│   ├── qa/
│   └── publish/
└── tests/
```

## Canonical Event Record

The canonical event record is the system of record for event-level data. It should contain:

- event identity and date fields
- location and coordinates
- article provenance
- event type and salience
- actor coding
- duplicate metadata
- review metadata
- publication metadata

The canonical schema lives in `config/schemas/canonical_event.schema.json`.

## Separation of Layers

- `data/staging/`: machine-generated intermediate outputs, including normalized article batches and event/article link snapshots
- `data/review/`: QA reports and analyst workflow artifacts
- `data/canonical/`: reviewed event records and linked analyses
- `data/published/`: dashboard-facing files only

The public dashboard should ultimately read from `data/published/`, not directly from internal workflow artifacts.

## Analyst Console

The analyst console is the operational layer. Core pages:

- Inbox
- High-salience review queue
- Duplicates
- QA report
- Event detail editor
- Provenance view: "How this event got here"
- Council analysis

Phase 1 includes only a static scaffold for this surface.

## Agent Council

Analytic agents should not define the event record. They should interpret it after ingestion, deduplication, and review.

Initial council roles:

- CMR analyst
- Political risk analyst
- Regional security analyst
- Synthesis analyst

Operational agents:

- Event classifier
- Actor coder
- Duplicate analyst

Each agent should emit structured JSON with explicit rationale, confidence, and rule references.
