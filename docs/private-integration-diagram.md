# SENTINEL Private Integration Diagram

This document is private/internal. It tracks how decisions and outputs move
from data collection through internal analysis to the public dashboard.

Update this diagram whenever stage boundaries, core runners, or publication
contracts change.

Private visual output:

- [private-integration-diagram.svg](/Users/hjmoncrieff/Library/CloudStorage/Dropbox/SENTINEL/docs/private-integration-diagram.svg)

## End-To-End Integration

```mermaid
flowchart TD
    A[Source collection\nRSS / NewsAPI / GDELT / ACLED] --> B[Ingest and normalization\nrun_pipeline.py\nnormalize_articles.py]
    C[Structural refresh\nrefresh_vdem.py\nfetch_worldbank.py\nbuild_country_year.py] --> G
    B --> D[Review diagnostics\nQA / duplicates / review queue]
    D --> E[Canonical event layer\nclassification\nactor coding\nregistry updates]
    E --> F[Council analysis\ninterpretation\nrecommended actions]
    C --> H[Private modeling layer\ncountry monitors\ncountry-month panel\nproxy targets\nmanual external/economic seeds\nvalidation]
    E --> H
    F --> H
    E --> G[Publication build\npublish_dashboard_data.py]
    F --> G
    H --> I[Internal calibration and forecasting\nprivate only]
    G --> J[Public dashboard\npublished-safe outputs only]
    D --> K[Analyst console\ncredentialed review and publication control]
    E --> K
    F --> K

    classDef public fill:#114b5f,stroke:#7dd3fc,color:#ffffff;
    classDef internal fill:#4c1d95,stroke:#c4b5fd,color:#ffffff;
    classDef private fill:#3f3f46,stroke:#d4d4d8,color:#ffffff;

    class J public;
    class D,E,F,K internal;
    class C,H,I private;
```

## Surface Logic

- public dashboard:
  - only published-safe outputs
  - no local review data
  - no private modeling artifacts
- analyst console:
  - review and publication workspace
  - can consume internal review and council layers
  - should not expose the private modeling layer directly unless intentional
- private modeling layer:
  - structural refresh
  - calibration
  - country-month panels
  - target design
  - forecasting experiments
  - validation notes

## Decision Rule

If a new stage, dataset, or model output is introduced, decide explicitly:

- public
- internal analyst
- private modeling

Then update this diagram in the same pass.
