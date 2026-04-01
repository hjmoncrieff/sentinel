# SENTINEL Next Steps

This document tracks the highest-value follow-up work after the current
AI-first dashboard, analyst console, review workflow, provenance, and actor
registry milestones.

## 1. Public Event Quality

- strengthen `Why It Matters` so synthesis is consistently country-specific,
  interpretive, and publication-ready
- improve public event descriptions for multi-source events
- standardize canonical titles more aggressively after analyst merges
- add merge-target search and suggestions in the analyst console so analysts do
  not need to type raw event IDs
- surface cleaner public source attribution for clustered events

## 2. Event Merge And Deduplication

- add merge-assist search by title, country, date, and actor overlap
- let analysts preview merge outcomes before saving
- add field-level keeper selection for title, summary, date, and location
- feed false-positive duplicate reasons back into duplicate QA statistics
- improve upstream duplicate detection using manual-merge history as training
  signal

## 3. Actor Coding And Registry

- make actor identification more registry-first in the coding pipeline
- extract candidate actors more explicitly before heuristic normalization
- auto-propose registry entries for named unmatched actors
- add registry QA actions for alias reassignment, not only alias dropping or
  entry merging
- build a dedicated registry browser/queue with search, filters, and audit
  history
- connect registry confidence and relationship tags more directly to QA and
  council recommendations

## 4. AI Worker Architecture

- split upstream workers more cleanly into dedicated modules:
  - classifier
  - actor coder
  - duplicate scorer
  - QA scorer
  - publication scorer
- persist worker-level outputs in a more formal contract
- expose worker disagreement more clearly in the analyst console
- use analyst corrections as feedback inputs for future scoring logic

## 5. Analyst Console

- add merge previews and merge-target suggestions
- add more direct editing for registry entries with registry-level audit views
- improve actor relationship editing with controlled vocabularies
- add bulk follow-up workflows for registry QA issues
- refine queue prioritization with stronger AI disagreement and uncertainty
  signals
- keep simplifying labels and section copy so the interface stays concise

## 6. Public Dashboard

- continue tightening wording consistency across tabs
- keep reducing internal/backend language in public views
- improve empty states and explanatory copy for maps and cards
- decide whether public event analysis should remain AI-written, lightly edited,
  or move toward a more templated editorial style
- consider a lightweight public methodology panel for event interpretation

## 7. Provenance And Transparency

- deepen event/article linkage earlier in the ingestion stack
- preserve more article metadata at normalization time
- standardize provenance stage semantics across every pipeline step
- decide what level of provenance belongs in public views versus internal views

## 8. Operations And Governance

- define a stable run order script or task runner for the full pipeline
- document analyst versus coordinator approval authority more explicitly
- add registry-governance rules for who can seed versus confirm entries
- improve recovery/undo coverage for all high-consequence actions
- consider a small local database once concurrent analyst activity grows

## 9. Security And Deployment

- keep the public/private split strict as the site moves toward deployment
- audit which data products are safe to publish by default
- review GitHub deployment assumptions before the public launch
- consider a deployment checklist for dashboard publish steps

## 10. Documentation Cleanup

- keep `README.md` public-facing and concise
- keep `docs/user-guide.md` as the operator playbook
- reduce overlap among `system-workflow`, `pipeline-operations`, and
  `implementation-plan`
- add a short maintainer checklist for repo hygiene before releases
