# SENTINEL Private Acute Political Risk Target Note

This note is private/internal. It defines the next broader predictive target
after irregular transition.

## Why This Target Exists

`irregular_transition` is useful, but it is narrower than SENTINEL's actual
scope as a political-risk system.

Many analytically important country-months involve:

- sharp regime stress
- fragmentation surges
- coercive deterioration
- institutional weakening
- external or economic shock interacting with political fragility

without becoming a clean irregular-transfer case.

The broader target should capture those acute deterioration periods.

## Proposed Target

- `acute_political_risk_next_1m`
- `acute_political_risk_next_3m`

Interpretation:

- near-term acute worsening in political risk that is material for analysts
- broader than irregular transition
- still narrower than a generic “bad things happened” label

## First Proxy Logic

Current first proxy version:

- `proxy_acute_political_risk_v1`

The first proxy now lives directly in:

- `scripts/analysis/build_country_month_panel.py`

and writes fields into:

- `data/modeling/country_month_panel.json`

Core signal families:

- high-severity episodes linked to:
  - `regime_vulnerability`
  - `security_fragmentation`
- fragmenting episodes
- event-shock deterioration
- destabilizing conflict/protest combinations
- external-pressure spikes
- economic-fragility spikes
- structural shift flags

## Relationship To Existing Targets

- `irregular_transition`
  - narrow rupture / transfer-oriented target
- `acute_political_risk`
  - broader deterioration target

So the architecture should now distinguish:

- rupture-watch logic
- fit-time rupture validation
- broader acute political-risk deterioration logic

## Current Status

This target is now through the first reviewed adjudication pass.

Current checkpoint:

- proxy layer in the country-month panel
- adjudicated acute political-risk layer `v1`
- stricter gold subset now derivable from that reviewed base
- current gold acute-risk subset:
  - `22` reviewed `1m` rows
  - countries:
    - `Bolivia`
    - `Chile`
    - `Colombia`
    - `El Salvador`
    - `Haiti`
    - `Honduras`
    - `Peru`
    - `Venezuela`
- current first gold-validation result:
  - recall `100.0%`
  - precision `43.137%`
  - the remaining problem is specificity, not missed gold cases

Current benchmark-tier checkpoint:

- gold positives: `22`
- hard negatives: `18`
- easy negatives: `22`

Current feature-separation takeaway:

- the strongest current contrast is not a cleaner rupture signal
- it is lower contestation overload in the gold positives
- the first acute-risk tier audit suggests:
  - `transition_contestation_load_score` is much higher in hard negatives
  - `transition_rupture_precursor_score` is also currently higher in hard negatives
  - so the next acute-risk refinement should penalize broad contestation overfire more effectively
- latest refinement checkpoint:
  - gold recall remains `100.0%`
  - proxy precision improved to `45.833%`
  - false positives fell from `29` to `26`

Current protest-interpretation checkpoint:

- protests are included in the acute-risk layer through:
  - `event_type_protest_count`
  - `episode_type_protest_security_escalation_count`
  - `transition_contestation_load_score`
- the panel now also carries protest-split interpretive fields:
  - `protest_acute_signal_score`
  - `protest_background_load_score`
- these fields are meant to separate:
  - protest as acute deterioration signal
  - protest as broad contestation background
- the first direct attempt to feed those protest-split fields back into the
  acute-risk score increased false positives and was intentionally backed out
- current stance:
  - keep the protest split in the panel for interpretation and review
  - do not let it alter the acute-risk rule again until protest-heavy benchmark
    cases are reviewed more directly

Current protest-review path:

- `scripts/analysis/review_acute_political_risk_protest_cases.py`
- output:
  - `data/review/acute_political_risk_protest_review.json`
- current first read:
  - only `1` current `gold_positive` benchmark month is protest-heavy
  - `9` current `hard_negative` benchmark months are protest-heavy
  - protest-heavy hard negatives therefore remain the more common pattern
- narrow interpretation note:
  - `docs/private-acute-protest-interpretation-note.md`
- current interpretation:
  - protest-linked acute positives appear to require:
    - protest-security escalation
    - high severity
    - low protest background load
    - and a non-negative specificity gap
  - most protest-heavy benchmark cases still behave more like contestation-heavy
    near misses than true acute deterioration
  - a first benchmark-only candidate feature now also exists:
    - `protest_escalation_specificity_score`
  - current result:
    - sparse and interpretable
    - but still somewhat more common in `hard_negative` than `gold_positive`
    - so not yet score-ready
    under the current benchmark

Current fit-ready checkpoint:

- fit sample rows: `61`
- gold positives: `22`
- hard negatives: `17`
- easy negatives: `22`
- current baseline threshold result:
  - threshold `4`
  - precision `100.0%`
  - recall `100.0%`
  - specificity `100.0%`

Current first model-comparison result:

- the threshold baseline still wins
- leave-one-out logistic:
  - precision `84.615%`
  - recall `100.0%`
  - specificity `89.744%`
- the fitted model fails hardest on hard negatives

It still needs:

- tiered validation

## Immediate Recommendation

Use this target next for:

- Haiti
- El Salvador
- Ecuador
- Peru
- Venezuela

Those are the kinds of cases where acute political-risk deterioration may be a
better target than irregular transition alone.
