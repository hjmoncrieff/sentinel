# Private AI Classification Copilot Note

This note describes a later-stage AI copilot layer for event classification and
categorization. It is not part of the current required daily pipeline.

## Purpose

The aim is to improve classification quality on ambiguous and mechanism-rich
events without replacing the current deterministic coding stack.

The copilot should help with:

- `event_type`
- `event_subcategory`
- `event_construct_destinations`
- `event_analyst_lenses`
- actor-role interpretation
- ambiguity detection

## Design Principle

The AI layer should be a second-pass copilot, not the first-pass source of
truth.

Order should remain:

1. deterministic baseline classification
2. actor coding and canonical event construction
3. AI copilot review on selected events
4. disagreement routing and human review
5. approved decisions folded into benchmark and QA layers

This keeps the system auditable and prevents a model from silently rewriting
the event ontology.

## Recommended Scope

The copilot is most valuable for:

- `other` and taxonomy edge cases
- overlapping categories such as:
  - `protest` vs `conflict`
  - `reform` vs political maneuver
  - `coop` vs international pressure
  - `oc` vs broader fragmentation
- construct mapping
- analyst-lens selection
- actor-role interpretation when state and non-state actors mix

It is less useful as a fully autonomous replacement for:

- hard publication decisions
- factual validation
- duplicate truth determination without supporting evidence

## Trigger Logic

The AI copilot should only run when one or more of these conditions are met:

- low classifier confidence
- generic or fallback subcategory
- disagreement between rule outputs
- high salience
- actor ambiguity
- mixed political/security/international mechanisms
- review queue priority above threshold

Routine easy cases should stay on the cheap deterministic path.

## Proposed Outputs

The copilot should emit a structured artifact, not free text only.

Suggested fields:

- `event_id`
- `ai_event_type`
- `ai_event_subcategory`
- `ai_construct_destinations`
- `ai_analyst_lenses`
- `ai_actor_interpretation`
- `ai_confidence`
- `ai_ambiguity_flag`
- `ai_reason_short`
- `ai_disagreement_with_rules`
- `ai_review_recommendation`

## Resolution Logic

The operating rule should be simple:

- rules and AI agree:
  - accept automatically or lightly review
- rules and AI disagree:
  - send to review queue
- AI confidence low:
  - send to review queue
- event high salience:
  - always preserve structured AI recommendation for human inspection

## Data Products

Likely future artifacts:

- `data/review/ai_classification_copilot.json`
- `data/review/ai_classification_disagreements.json`
- `data/review/ai_classification_review_queue.json`

Likely future runner:

- `scripts/analysis/run_ai_classification_copilot.py`

## Model Discipline

If an API model is added later, it should be constrained to:

- structured outputs
- known taxonomy
- known construct vocabulary
- known actor vocabulary
- short rationale

It should not be allowed to:

- invent event facts
- invent actors
- change publication status
- rewrite canonical event contents without trace

## Benchmarking Path

The right learning loop is:

1. collect human-reviewed disagreements
2. turn reviewed outcomes into benchmark cases
3. evaluate copilot agreement and error types
4. only then consider partial automation

This makes the copilot a supervised workflow aid rather than a hidden
classifier.

## Current Recommendation

For now:

- keep deterministic classification as the production path
- keep public prose improvement separate
- treat AI classification copilot as a documented future stage

That is the safest path for a political-risk system where traceability matters.
