# SENTINEL Private Variable And Construct Diagram

This document is private/internal. It tracks how variables and constructs feed
the country measures in the project.

Update this diagram whenever a new structural variable, event-derived signal,
construct, or monitor family is added.

Private visual output:

- [private-construct-diagram.svg](/Users/hjmoncrieff/Library/CloudStorage/Dropbox/SENTINEL/docs/private-construct-diagram.svg)

## Variable-To-Construct Map

```mermaid
flowchart TD
    A[Structural variables\nV-Dem\nWorld Bank\nM3\nhistorical country-year layer]
    B[Event-derived pulse\nreviewed events\nDEED signals\naxis counts\nsalience and confidence]
    C[External pressure\nsanctions\nIMF\nUS security shifts\nplanned/partial]
    D[Economic fragility and shocks\ninflation\ndebt\nFX stress\ncapital controls\nplanned/partial]
    S[Internal signal layer\ncoercive instability\ninstitutional erosion\nsecurity fragmentation\nelite fracture\nexternal pressure\neconomic stress]

    A --> E[Monitor families]
    B --> E
    C --> E
    D --> E
    B --> S
    C --> S
    D --> S

    E --> E1[CMR balance]
    E --> E2[Security pressure]
    E --> E3[External security alignment]

    A --> F[Risk constructs]
    B --> F
    C --> F
    D --> F
    S --> F

    F --> F1[Regime vulnerability]
    F --> F2[Militarization]
    F --> F3[Security fragmentation]
    F --> F4[Overall internal risk]

    E1 --> G[Country monitors]
    E2 --> G
    E3 --> G
    F1 --> G
    F2 --> G
    F3 --> G
    F4 --> I[Internal outputs\nanalyst interpretation\ncalibration\nvalidation]

    G --> H[Public outputs\nsummary cards\ncountry profiles\nselected map layers]
    G --> I[Internal outputs\nanalyst interpretation\ncalibration\nvalidation]
    G --> J[Private modeling outputs\ncountry-month panel\nproxy targets\nfuture predictive models]
```

## Current Construct Logic

- `regime_vulnerability`
  - regime type and democratic fragility
  - governance erosion
  - state-capacity weakness
  - DEED-style institutional erosion
  - selected recent destabilizing signals
- `militarization`
  - military domestic-coercion role
  - military governance-administration role
  - military economic-control role
  - broader civil-military structure
  - supporting pulse from relevant events
- `security_fragmentation`
  - organized-crime density
  - territorial spread of coercive stress
  - conflict and criminality pressure
  - weak state capacity and fragmented coercive order
- `overall internal risk`
  - should aggregate construct-level pressure rather than raw signal counts

Current signal-layer logic:

- the private signal panel is now intended to feed:
  - `regime_vulnerability`
  - `militarization`
  - `security_fragmentation`
  - and a top-line internal-only overall risk layer

Current placeholder families:

- external pressure variables are now reserved in the panel contract
- economic fragility and policy-shock variables are now reserved in the panel
  contract
- those families can now be seeded locally at the country-month level before
  full automated ingestion exists

## Maintenance Rule

When variables or constructs change, update:

- `data/CODEBOOK.md`
- `docs/baseline-pulse-design.md`
- this diagram

in the same change set.
