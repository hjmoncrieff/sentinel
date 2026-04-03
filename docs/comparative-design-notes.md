# SENTINEL Comparative Design Notes

This note captures useful design lessons from external political-risk and
monitoring systems that are relevant to SENTINEL's architecture. It is not a
public-facing methods statement and it is not a commitment to replicate any one
provider's product design.

## Current Reference Point

One especially useful benchmark is the GeoQuant FAQ document, which describes a
political-risk system built around structural baselines, high-frequency media
signals, human review, and composite indicators.

Source:

- GeoQuant FAQ PDF:
  https://assets.ctfassets.net/nvl7oyu82ssb/5xX5bUq1dlf3Y6jXCkq3zN/dbac23d9c0461098b7a6972dd623b625/GeoQuant-FAQ.pdf

## Main Lessons For SENTINEL

### 1. Baseline + Pulse Is A Strong Design

The most important conceptual lesson is to separate:

- structural baseline conditions
- high-frequency event shocks

For SENTINEL, that suggests a future architecture where country monitoring can
combine:

- slower-moving structural CMR, militarization, and criminality baselines
- faster-moving event or article-driven pulse signals

This is likely more informative than relying only on recent event counts or only
on static country profiles.

### 2. Event Detection Should Be Separate From Event Effect

The benchmark model does more than identify relevant articles. It also tries to
estimate:

- direction of effect
- strength or intensity
- likely duration

For SENTINEL, that implies a future improvement path where event records may
eventually carry:

- relevance
- impact direction
- expected duration
- confidence

This would make the public monitor and the internal analyst workflow more
analytically useful.

### 3. Human Review Should Feed System Improvement

The benchmark model treats analysts as part of the model-improvement loop rather
than only as final validators.

That reinforces the direction already planned for SENTINEL:

- human edits should become gold data
- reviewed records should improve retrieval, rules, and later training
- the analyst console should be a supervision and learning layer, not only a
  correction layer

### 4. Source Curation Is Part Of Model Quality

The benchmark system emphasizes careful source selection, multilingual coverage,
and source-quality control.

For SENTINEL, source curation should continue to be treated as model
infrastructure, not just ingestion plumbing.

That includes:

- local and regional source depth
- language coverage
- source bias awareness
- exclusion of weak-signal or high-noise channels when appropriate

### 5. Taxonomy Design Matters As Much As Model Design

The benchmark system is strongly taxonomy-driven.

For SENTINEL, this reinforces the need to keep investing in:

- event taxonomy
- actor taxonomy
- relationship taxonomy
- review and publication taxonomies

Cleaner ontology will likely improve system quality more reliably than trying to
jump too quickly to a larger or more complex model.

### 6. Trends Matter, Not Only Individual Events

The benchmark system uses both levels and change over time.

SENTINEL should move in that direction too:

- event-level monitoring remains central
- but country trajectories, slopes, and recent-change indicators should become
  more explicit in the country and regional layers

## What SENTINEL Should Not Copy Directly

SENTINEL should not default to becoming a generic 0-100 political-risk score
product.

Its comparative advantage is different:

- richer event records
- clearer provenance
- actor and relationship coding
- analyst-guided interpretation
- CMR- and security-specific regional depth

Scores may become useful later, but they should support SENTINEL's event and
analysis model rather than replace it.

## Practical Future Use

These notes support several planned workstreams:

- baseline + pulse design
- impact and duration fields
- continuous learning from human review
- stronger source-governance rules
- country-level trend and trajectory outputs

This note should be read alongside:

- `docs/next-steps.md`
- `docs/system-workflow.md`
- `docs/ai-analyst-knowledge.md`
