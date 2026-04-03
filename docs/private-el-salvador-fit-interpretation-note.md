# El Salvador Fit-Path Interpretation Note

Date: 2026-04-02

Purpose:

- review the remaining El Salvador gold-labeled months that the stricter
  `proxy_irregular_transition_fit_v1` rule still misses
- decide whether they should be lifted into the fit rule or remain broader
  watch-only cases

Cases reviewed:

- `2020-09-01 -> 2020-10-01`
- `2022-04-01 -> 2022-05-01`
- `2023-11-01 -> 2023-12-01`

Observed shared pattern:

- next month contains a `high` severity episode
- the episode links to `regime_vulnerability`
- the dominant event type is still `conflict`
- the dominant DEED signal is still `symptom`
- there is no coup signal
- there is no purge signal
- there is no destabilizing DEED reinforcement
- contestation load remains substantial relative to rupture specificity

Case-specific read:

- `2020-09-01 -> 2020-10-01`
  - `high_severity_episode_count = 1`
  - `episode_construct_regime_vulnerability_count = 1`
  - `event_type_conflict_count = 1`
  - `deed_type_destabilizing_count = 0`
  - `transition_specificity_gap = -3.25`
  - interpretation:
    - serious regime-vulnerability watch signal
    - not clean enough to count as a stricter rupture-fit case

- `2022-04-01 -> 2022-05-01`
  - `high_severity_episode_count = 1`
  - `episode_construct_regime_vulnerability_count = 1`
  - `event_type_conflict_count = 1`
  - `deed_type_destabilizing_count = 0`
  - `transition_specificity_gap = -3.05`
  - interpretation:
    - very similar to the 2020 case
    - analytically important for watch logic
    - still not rupture-specific enough for the stricter fit layer

- `2023-11-01 -> 2023-12-01`
  - `high_severity_episode_count = 1`
  - `episode_construct_regime_vulnerability_count = 1`
  - `event_shock_flag = 1`
  - `high_salience_event_count = 2`
  - `event_type_conflict_count = 3`
  - `deed_type_destabilizing_count = 0`
  - `transition_specificity_gap = -4.65`
  - interpretation:
    - strongest of the three
    - still dominated by conflict-heavy symptomatic deterioration rather than a
      cleaner rupture-specific mechanism

Interpretive conclusion:

- these three El Salvador months are defensible as:
  - internal reviewed positives
  - strong rupture-watch cases
- they are weaker as:
  - stricter fit-time rupture positives

Recommended modeling stance:

- keep them inside:
  - adjudicated `v1`
  - gold/history memory for analyst review
- do not automatically force them into the stricter fit rule yet
- treat them as the clearest current example of:
  - high-severity regime-vulnerability watch
  - without enough rupture specificity for fit-time promotion

Operational implication:

- the watch path should still surface these cases
- the fit path should remain stricter until more comparable benchmark cases are
  reviewed

Future refinement trigger:

- revisit this decision if we add more executive-power concentration,
  institutional override, or election/institutional-break variables that make
  these cases more rupture-specific without relying on broad contestation
