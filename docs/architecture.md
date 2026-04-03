# SENTINEL Architecture

## Goal

SENTINEL is evolving from a static event dashboard into a research operations platform with three clearly separated surfaces:

- Public dashboard: read-only publication layer for curated and published event data.
- Analyst console: credentialed workspace for review, QA, duplicate resolution, actor coding, and AI-assisted analysis.
- Private modeling layer: internal structural, calibration, and predictive artifacts that support country monitors and future forecasting work but are not part of the public product.

The near-term architecture preserves the current GitHub Pages workflow while introducing a stronger internal data model and review workflow.

## Current Baseline

The repository currently centers on:

- `scripts/run_pipeline.py`: primary fast-path runner
- `scripts/pipeline_core.py`: pipeline implementation
- `scripts/generate_clean_events.py`: cleaned export generation
- `data/events.json`: live event store
- `index.html`: single-file public dashboard

This baseline remains intact for now. Phase 1 adds new layers around it without breaking the current dashboard.

## Target Data Flow

1. Source ingestion
    RSS, GDELT, NewsAPI, ACLED, and future structured sources produce article-level records.
2. Staging normalization
    Raw reports are normalized into a common article schema.
3. Structural refresh
    Slow-moving layers such as V-Dem and World Bank are refreshed into cleaned structural artifacts.
4. Duplicate detection
    Reports are clustered into likely event groups using deterministic and semantic rules.
5. Event classification
    Events are coded to a controlled taxonomy with rule references.
6. Actor coding
    Primary, secondary, and additional actors are extracted and normalized.
7. QA and review
    Flags are generated and routed to a credentialed analyst interface.
8. Council analysis
    Multiple analytic agents produce distinct interpretations over reviewed events.
9. Country monitoring and private modeling
    Structural baselines, event pulse, calibration, and later country-month panels are built in private analytical layers.
10. Publication
    Public-safe outputs are written for the dashboard.
11. Historical ingestion
    Deep archive recovery runs through a separate historical pipeline rather than
    the fast monitoring workflow.

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
- `data/cleaned/`: slow-moving structural inputs used for modeling and country monitors
- `data/modeling/`: future private panel/model artifacts, not for public serving

The public dashboard should ultimately read from `data/published/`, not directly from internal workflow artifacts.

## Surface Boundaries

### Public Dashboard

What belongs here:

- published events
- public-safe country monitor summaries
- public-safe maps, trends, and analytical interpretation

What does not belong here:

- local credentials
- live review queues
- private analyst notes
- raw QA diagnostics
- registry governance internals
- private modeling and calibration artifacts

### Analyst Console

What belongs here:

- review queue
- duplicate and QA workflow
- actor registry workflow
- council analysis
- publication decisions

The console may read from `data/review/`, `data/canonical/`, and selected public
outputs, but it remains an operational workspace rather than a public-facing
monitor.

### Private Modeling Layer

What belongs here:

- cleaned structural refreshes
- country-year joins
- calibration notes
- benchmark validation
- future country-month panels
- future target labels and predictive model outputs

This layer should feed the country-monitor system and future forecasting work,
but it should stay separate from both the public dashboard and the day-to-day
review console until its outputs are mature enough for analyst use.

## Historical Ingestion Boundary

Historical archive recovery should be treated as a separate system boundary.

- `scripts/run_pipeline.py` remains the fast monitoring entry point
- `scripts/historical_ingest.py` is the dedicated planning/orchestration entry
  point for deep backfill
- `config/historical_sources.json` defines the source groups and connector
  priorities for 2000+ coverage work

This separation matters because long-run archive recovery has different source
constraints, completeness risks, and QA requirements than routine monitoring.

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

- Military analyst
- Political analyst
- Security analyst
- Synthesis analyst

Operational agents:

- Event classifier
- Actor coder
- Duplicate analyst

Each agent should emit structured JSON with explicit rationale, confidence, and rule references.
