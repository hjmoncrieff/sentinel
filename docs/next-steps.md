# SENTINEL Next Steps

This document tracks the highest-value follow-up work after the current
AI-first dashboard, analyst console, review workflow, provenance, and actor
registry milestones.

## 0. Open Items (2026-10-05)

- decide whether to turn on model-written synthesis (`RUN_COUNCIL_SYNTHESIS`; see
  `docs/public-site.md`)
- build a human-adjudicated gold set for codebook v3; current model comparisons are
  agreement figures only (`docs/codebook-v3.md`)
- recode pre-October-2026 events with codebook v3 so salience and types are comparable
  across the archive
- approve the redesigned site section by section and move it from `/next/` to the root;
  record-page addresses change once when that happens
- price each pipeline stage at its own model's rate in the private cost log

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
- continue calibrating the layered risk model in:
  - `docs/baseline-pulse-design.md`
  - `config/baseline_pulse_model.json`
  with a particular focus on regime vulnerability, militarization, security
  fragmentation, and impact-duration calibration over time

## 5. Continuous Learning And Gold Data

- create a `gold` layer for high-quality human-reviewed outputs:
  - corrected events
  - validated actor codings
  - duplicate decisions
  - publication decisions
  - optional analyst reasoning notes
- use analyst and coder edits first as retrieval and rule-improvement inputs,
  not only as one-off corrections
- design a feedback pipeline so human validation can improve:
  - event classification
  - actor identification
  - duplicate detection
  - publication recommendations
- prefer a staged learning path:
  - gold data
  - retrieval-guided improvement
  - evaluation
  - task-specific training or fine-tuning later
- define data-quality thresholds before any model-training step so the system
  learns from reliable human-reviewed examples rather than noisy edits

## 6. Analyst Console

- add merge previews and merge-target suggestions
- add more direct editing for registry entries with registry-level audit views
- improve actor relationship editing with controlled vocabularies
- add bulk follow-up workflows for registry QA issues
- refine queue prioritization with stronger AI disagreement and uncertainty
  signals
- keep simplifying labels and section copy so the interface stays concise

## 7. Public Dashboard

- continue tightening wording consistency across tabs
- keep reducing internal/backend language in public views
- improve empty states and explanatory copy for maps and cards
- decide whether public event analysis should remain AI-written, lightly edited,
  or move toward a more templated editorial style
- consider a lightweight public methodology panel for event interpretation

### Country monitors: deferred (noted 2026-10-05)

Done without the API on 2026-10-05: activity chart, events behind each reading, located-events
map, regional medians, story grouping, in-depth "needs revision" flag, US assistance block,
record pages, methodology page, topic pages, duplicate folding, the reference review queue in
the console. Still to do:

- **Assessment text (needs API credit).** The section is rule-generated and close to
  boilerplate. Replace it with a short Sonnet-written assessment grounded in the country's
  last 90 days of coded events, citing them, with the AI label. Roughly one to two cents per
  country per refresh. Decide first whether it publishes automatically or waits for review.
- **Thin pages (needs API credit).** 24 countries still carry the old hand-entered positions,
  some marked "[verify …]". Run `scripts/reference/refresh_country_reference.py --stale-days 0`
  and review the proposals.
- **Rewrite stale in-depth text.** Colombia's is flagged (written before August 2026).
  Venezuela's is probably stale too but is not flagged until its officials are researched.
- **Scenario approval (needs API credit).** The console's review queue and the
  `content_reviews` table accept `kind = 'scenario'`, but nothing writes scenarios yet.
  Build the generator, add its items to `review_items`, and a handler in
  `scripts/sync/pull_content_reviews_from_supabase.py`.
- **Topic-page essays.** The organized-crime and US-security pages are computed from data;
  the long hand-written essays are still on the old dashboard and need revision before
  they move.
- **Named armed groups.** Group names come from v3-coded events only and spelling variants
  are not merged; the "groups named most often" list appears once there are five.
- **Place list.** `config/taxonomy/places.json` holds about 340 approximate points written
  by hand. Check them against a gazetteer, and add towns as they appear in events.

## 8. Provenance And Transparency

- deepen event/article linkage earlier in the ingestion stack
- preserve more article metadata at normalization time
- standardize provenance stage semantics across every pipeline step
- decide what level of provenance belongs in public views versus internal views

## 9. Operations And Governance

- define a stable run order script or task runner for the full pipeline
- document analyst versus coordinator approval authority more explicitly
- add registry-governance rules for who can seed versus confirm entries
- improve recovery/undo coverage for all high-consequence actions
- consider a small local database once concurrent analyst activity grows

## 10. Historical Ingestion

- turn `scripts/historical_ingest.py` from planner into a real archive-ingest
  runner
- add source-specific connectors for archive-rich publishers
- add resumable state and batch checkpoints
- write historical article-level staging outputs
- define archive-quality QA checks for gaps, duplicates, and source imbalance

## 11. Security And Deployment

- keep the public/private split strict as the site moves toward deployment
- audit which data products are safe to publish by default
- review GitHub deployment assumptions before the public launch
- consider a deployment checklist for dashboard publish steps

## 12. Documentation Cleanup

- keep `README.md` public-facing and concise
- keep a separate local operator playbook outside the public repo
- reduce overlap among `system-workflow`, `pipeline-operations`, and
  `implementation-plan`
- add a short maintainer checklist for repo hygiene before releases
