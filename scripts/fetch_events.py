#!/usr/bin/env python3
"""
Legacy compatibility wrapper for SENTINEL.

`fetch_events.py` is retired as the primary command. Use:

    python3 scripts/run_pipeline.py

This wrapper remains only to avoid breaking older local habits and automation
while the repo transitions to the staged runner layout.
"""

from __future__ import annotations

import warnings

from pipeline_core import main


if __name__ == "__main__":
    warnings.warn(
        "scripts/fetch_events.py is retired as the primary entry point. "
        "Use `python3 scripts/run_pipeline.py` instead.",
        DeprecationWarning,
        stacklevel=1,
    )
    main()
