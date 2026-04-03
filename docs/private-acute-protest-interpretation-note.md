# Private Acute Protest Interpretation Note

Purpose:

- interpret the protest-heavy acute-political-risk benchmark cases
- clarify when protest-linked months should count as true acute deterioration
- keep this separate from direct score changes until a cleaner rule is justified

Source artifact:

- `data/review/acute_political_risk_protest_review.json`

## Current Benchmark Read

Current protest-heavy benchmark counts:

- `gold_positive`: `1`
- `hard_negative`: `9`

This means protest-heavy months are currently much more common in the
`hard_negative` tier than in the `gold_positive` tier.

That supports the current modeling stance:

- protests are relevant
- but protest-heavy months should not automatically be treated as acute
  political-risk positives

## Positive Reference Case

Current protest-heavy `gold_positive` case:

- `El Salvador`
  - `2022-05-01`

Current profile:

- `acute_political_risk_signal_score_next_1m = 4`
- `high_severity_episode_count = 1`
- `episode_type_protest_security_escalation_count = 1`
- `protest_acute_signal_score = 3.0`
- `protest_background_load_score = 0.0`
- `transition_contestation_load_score = 4.25`
- `transition_specificity_gap = 0.35`

Interpretation:

- protest-linked escalation matters here because it is attached to a
  high-severity episode
- the protest signal is acute rather than diffuse
- background contestation load is limited

So the current positive reference pattern is:

- protest-security escalation
- plus high severity
- plus low protest background load
- plus non-negative specificity gap

## Hard-Negative Patterns

The current protest-heavy `hard_negative` cases split into three broad groups.

### 1. Broad contestation overload

Examples:

- `Colombia 2024-04-01`
- `Colombia 2024-06-01`
- `Guatemala 2020-12-01`
- `Haiti 2021-03-01`

Typical pattern:

- multiple protest or conflict-linked signals
- high `transition_contestation_load_score`
- negative `transition_specificity_gap`
- weak or absent clean rupture structure

Interpretation:

- these are severe and watch-worthy
- but they look more like broad unrest / contestation burden than acute
  political-risk deterioration in the stricter benchmark sense

### 2. Protest-escalation without enough specificity

Examples:

- `Brazil 2023-01-01`
- `Honduras 2022-02-01`
- `Peru 2024-05-01`

Typical pattern:

- some protest-security escalation signal
- but limited severity or fragmentation depth
- not enough supporting structure to distinguish acute deterioration from noisy
  contention

Interpretation:

- protest-security escalation alone is not enough
- it needs either stronger severity, stronger fragmentation, or a cleaner shock
  structure

### 3. Mixed near-miss rupture-watch cases

Examples:

- `Mexico 2020-07-01`
- `Venezuela 2025-09-01`

Typical pattern:

- stronger acute-looking protest or severity cues
- but still embedded in broader contestation or ambiguous near-miss structure

Interpretation:

- these are the closest protest-heavy negatives to true acute positives
- they should remain good stress-test months for future feature design

## Working Interpretation Rule

For now, a protest-linked month should lean toward true acute deterioration
only when most of the following are true:

- `episode_type_protest_security_escalation_count > 0`
- `high_severity_episode_count > 0`
- `protest_background_load_score` stays low
- `transition_specificity_gap >= 0`
- the month is not dominated by broad conflict/protest accumulation

It should lean toward `hard_negative` or broad contestation when:

- `transition_contestation_load_score` is high
- `protest_background_load_score` is high
- conflict/protest volume is broad rather than concentrated
- specificity gap is clearly negative

## Modeling Implication

Current recommendation:

- keep `protest_acute_signal_score` and `protest_background_load_score` in the
  panel
- keep using them for interpretation and benchmark review
- do not feed them directly into the acute-risk score again until a future pass
  can isolate a cleaner protest-linked positive rule

The next useful protest-specific feature direction is likely:

- protest escalation with low background overload
- rather than protest intensity by itself

## First Candidate Feature Check

The panel now also carries a benchmark-only candidate field:

- `protest_escalation_specificity_score`

It is designed to reward:

- protest-security escalation
- plus high severity / fragmentation / shock reinforcement
- while penalizing:
  - protest background overload
  - broad contestation overload

Current benchmark read:

- `gold_positive`
  - mean: `0.142`
  - nonzero rows: `2`
- `hard_negative`
  - mean: `0.291`
  - nonzero rows: `5`

Interpretation:

- the candidate is behaving as a sparse filter rather than a broad protest
  measure
- but it still appears somewhat more often in `hard_negative` than in
  `gold_positive`
- so it is not yet ready to alter the acute-risk score

Current stance:

- keep `protest_escalation_specificity_score` in the panel as a candidate
  benchmark feature
- do not let it drive scoring until a cleaner positive separation pattern
  exists
