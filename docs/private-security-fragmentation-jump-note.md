# SENTINEL Private Security Fragmentation Jump Target Note

This note is private/internal. It starts the first construct-oriented target
after the broader acute-political-risk pass.

## Proposed Target

- `security_fragmentation_jump_next_1m`
- `security_fragmentation_jump_next_3m`

Interpretation:

- near-term jump in security-fragmentation pressure
- narrower than generic acute political risk
- broader than a single conflict or protest event

## First Proxy Logic

Current first proxy version:

- `proxy_security_fragmentation_jump_v2`

The first proxy now lives in:

- `scripts/analysis/build_country_month_panel.py`

and writes fields into:

- `data/modeling/country_month_panel.json`

Core signal families:

- fragmenting episodes linked to `security_fragmentation`
- high-severity fragmentation-linked episodes
- conflict / organized-crime destabilizing stress
- event-shock reinforcement
- external and economic stress layered onto fragmentation-linked sequences

## First Workflow Stage

The target is now at the first review and early adjudication stage.

Current review path:

- `scripts/analysis/review_security_fragmentation_jump_targets.py`
- output:
  - `data/review/security_fragmentation_jump_target_review.json`

Current adjudication-queue path:

- `scripts/analysis/build_security_fragmentation_jump_adjudication_queue.py`
- output:
  - `data/review/adjudication_queue_security_fragmentation_jump.json`

Local decision template:

- `data/review/adjudicated_security_fragmentation_jump_decisions.template.json`
- local decisions:
  - `data/review/adjudicated_security_fragmentation_jump_decisions.local.json`
- adjudicated-label builder:
  - `scripts/analysis/build_adjudicated_security_fragmentation_jump_labels.py`
- adjudicated-label artifact:
  - `data/modeling/adjudicated_security_fragmentation_jump_labels.json`

Current checkpoint:

- reviewed benchmark positives across the first country set: `234`
- first adjudication queue size: `111`
- adjudicated rows after full queue clearance: `119`
- adjudicated countries now covered:
  - `Brazil`
  - `Colombia`
  - `Ecuador`
  - `El Salvador`
  - `Guatemala`
  - `Haiti`
  - `Honduras`
  - `Mexico`
  - `Peru`
  - `Venezuela`
- adjudication queue:
  - now `0`

This can now be treated as:

- `security fragmentation jump adjudicated layer v1`

Gold-subset builder:

- `scripts/analysis/build_gold_security_fragmentation_jump_labels.py`
- output:
  - `data/modeling/gold_security_fragmentation_jump_labels.json`

First gold validation:

- `scripts/analysis/validate_gold_security_fragmentation_jump_targets.py`
- output:
  - `data/review/gold_security_fragmentation_jump_validation.json`

Current gold checkpoint:

- gold rows: `36`
- gold countries:
  - `Brazil`
  - `Colombia`
  - `El Salvador`
  - `Guatemala`
  - `Haiti`
  - `Honduras`
  - `Mexico`
  - `Venezuela`
- gold recall: `100.0%`
- proxy precision against gold: `10.976%`

So the first read is clear:

- the proxy catches the current gold subset fully
- the main problem is specificity, not missed clean cases

Tiered benchmark builder:

- `scripts/analysis/build_security_fragmentation_jump_benchmark_tiers.py`
- output:
  - `data/modeling/security_fragmentation_jump_benchmark_tiers.json`

Tier-separation audit:

- `scripts/analysis/audit_security_fragmentation_jump_tier_separation.py`
- output:
  - `data/review/security_fragmentation_jump_tier_separation.json`

Current tiered benchmark checkpoint:

- gold positives: `36`
- hard negatives: `14`
- easy negatives: `20`

Current feature-separation read:

- strongest positive separator:
  - `security_fragmentation_jump_signal_score_next_3m`
- strongest hard-negative separators:
  - `transition_rupture_precursor_score`
  - `transition_contestation_load_score`

Current interpretation:

- hard negatives are more contestation-heavy than clean gold fragmentation jumps
- the next refinement problem remains specificity rather than recall

Latest refinement read:

- the `v2` contestation-discount pass did not materially change the current
  gold or tiered benchmark metrics
- that suggests the remaining overfire is more structural than a small
  threshold/penalty issue

## Why This Target

This is a strong next construct-oriented target because it aligns directly with:

- the episode layer
- the existing `security_fragmentation` country construct
- many of the benchmark countries where acute deterioration is driven by
  fragmentation rather than clean irregular transition
