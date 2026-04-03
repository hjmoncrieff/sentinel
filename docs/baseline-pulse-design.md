# SENTINEL Layered Risk Design

This note defines the current country-monitoring design for SENTINEL.

The model now has two linked levels:

- `monitor families`
  transparent baseline-plus-pulse measures
- `risk constructs`
  higher-order country outlooks built from those measures

Primary config scaffold:

- `config/baseline_pulse_model.json`

Primary builder:

- `scripts/analysis/build_country_monitors.py`

Primary output:

- `data/published/country_monitors.json`

## Why This Exists

SENTINEL already does a good job with:

- event detection
- event interpretation
- actor coding
- analyst review
- provenance

What it still needed was a stronger bridge from:

- `event-level monitoring`

to:

- `country-level outlook`

The layered risk design is that bridge.

## Model Logic

### 1. Baseline

The baseline captures slower-moving structural conditions:

- military prerogatives
- coup exposure
- public-security roles
- conflict baselines
- criminality pressure
- governance weakness
- democratic fragility
- state capacity

These values should move slowly and update when the structural datasets update.

When the newest country-year row is only a partial shell, the builder now
backfills each structural field from the latest non-null prior observation for
that country. This prevents democracy and governance measures from dropping out
just because they lag the calendar year.

### 2. Pulse

The pulse captures recent movement from live events.

Pulse weights increase when events are:

- recent
- high salience
- high confidence
- human reviewed or validated

Pulse is not total country condition. It is short-run movement.

### 3. Monitor Families

SENTINEL currently builds three interpretable monitor families:

#### Civil-Military Stress

Purpose:

- track military political influence, institutional autonomy, and civilian-control strain

#### Security Pressure

Purpose:

- track conflict, organized crime, and coercive stress

#### External Security Alignment

Purpose:

- track shifts in security cooperation, aid, exercises, and procurement

These monitor families remain visible because they explain *why* a higher-level
outlook moves.

### 4. Risk Constructs

The higher-order country outlook now uses three constructs:

#### Regime Vulnerability

Purpose:

- estimate the near-term vulnerability of the governing order

Main ingredients:

- civil-military stress
- security pressure
- democratic fragility
- governance erosion
- territorial state-capacity weakness
- military domestic-coercion role
- weak civilian constraints on the military
- authoritarian regime structure
- DEED-style institutional erosion signal from live events

Organized crime should feed this construct indirectly when it raises coercive
stress, fractures territorial authority, or creates elite-security strain.

The DEED-style layer is especially useful because it captures institutional
"hiccups" that slow structural indicators often miss, such as term-limit
manipulation, emergency-power normalization, politicized repression, or other
clear warning signs of erosion in the live event stream.

#### Militarization

Purpose:

- estimate how far coercive institutions are moving into politics, public
  security, and routine governance

Main ingredients:

- civil-military stress
- explicit military mission and role profiles
- military veto and impunity indicators
- military public-security roles
- executive-military entanglement

The key design choice here is that militarization should not be inferred only
from abstract structural proxies. It should also reflect the concrete
governance, prison, policing, intelligence, border, and administrative roles
the armed forces actually perform in-country.

The current decomposition now separates mission-role exposure into:

- domestic coercion
- governance administration
- economic control
- external defense

The militarization construct gives most weight to the first three, while
external defense remains mostly contextual unless it spills into governance or
domestic-security functions.

#### Security Fragmentation

Purpose:

- estimate whether conflict, organized crime, and weak state capacity are
  fragmenting the coercive environment

Main ingredients:

- security pressure
- criminality baseline
- territorial state-capacity weakness
- violence history

## Interpretation Principle

The public and analyst-facing interpretation should not treat every score as a
general “risk number.”

Instead:

- `monitor families` explain the mechanism
- `risk constructs` explain the country-level implication

Example:

- a country can have moderate militarization but severe security fragmentation
- or high regime vulnerability even when live event volume is not extreme,
  because the structural baseline is weak

That is why the layered model is preferable to a single undifferentiated score.

## Predictive Use

This is not yet a formally validated forecasting model.

But it is now a genuine predictive scaffold because it:

- aggregates structural and event-driven inputs
- distinguishes between mechanisms
- attaches short- to medium-run horizons to constructs
- generates country summaries and watchpoints

The intended use is:

- `baseline` explains underlying exposure
- `pulse` explains recent movement
- `constructs` explain likely near-term risk direction

The construct layer now also consumes the private monthly external/economic
signal artifact where it materially improves interpretation:

- `regime_vulnerability` can absorb sanctions, IMF exposure, inflation stress,
  and debt stress
- `militarization` can absorb US security-shift pressure and debt stress when
  those create openings for expanded coercive roles
- the construct layer now also absorbs longer-run structural memory from the
  expanded `1960-2025` country-year layer, especially:
  - coup recency and recent coup intensity
  - major regime-shift pressure
  - recent democratic backsliding
  - trade and aid dislocation shifts

This deeper historical layer is private/internal and should strengthen model
training and comparative calibration without changing the live product claim
that SENTINEL monitors `1990-present`.
- `security_fragmentation` can absorb sanctions, inflation, FX, and debt stress
  where macro stress is plausibly fragmenting the security environment

One important refinement is that `security_fragmentation` should not be treated
as a simple mirror of debt or macro distress. The model now uses a derived
`security_governance_gap` input to capture settings where:

- state capacity is weak
- criminality pressure is high
- coercive/governance control is too limited to contain fragmentation cleanly

This is especially useful for cases like Haiti, where fragmentation should rise
because of institutional weakness and coercive dispersion, not because the
country is being mistaken for a classical militarization case.

The top-line `overall risk` layer has also been rebalanced so that
`security_fragmentation` carries more weight and `militarization` a bit less.
That keeps countries like Haiti and Colombia from being understated simply
because their main risk is fragmented coercive stress rather than classical
military political power.

## Calibration

The current builder now applies an anchor-country calibration pass.

That means raw construct scores are adjusted against a small set of regional
reference cases, including countries like:

- Venezuela
- El Salvador
- Mexico
- Colombia
- Haiti
- Uruguay
- Costa Rica

The purpose is not to hide the raw model. It is to keep the comparative scale
closer to expert judgment while the system is still sparse and experimental.

The output preserves:

- calibrated construct scores
- raw construct scores
- calibration metadata at the file level

## Current Output

Each country row now includes:

- `monitors`
- `risk_constructs`
- `predictive_summary`

The predictive summary exposes:

- overall risk score
- overall risk level
- leading construct
- regime vulnerability score
- short summary text
- watchpoints

## What To Do Next

1. Improve structural coverage for external alignment and other missing inputs.
2. Calibrate weights against historical ruptures and known stress episodes.
3. Build a gold-data layer from analyst corrections and validated events.
4. Evaluate whether construct thresholds match expert judgment by country.
5. Decide which constructs belong in the public dashboard versus analyst-only views.

## Boundaries

SENTINEL should still avoid collapsing everything into one opaque universal
score.

The right structure is:

- a few transparent monitor families
- a few interpretable higher-order constructs
- explicit watchpoints
- clear provenance

That keeps the system consistent with SENTINEL’s event-driven and analyst-guided
identity.

## Related Documents

- `docs/comparative-design-notes.md`
- `docs/next-steps.md`
- `docs/system-workflow.md`
