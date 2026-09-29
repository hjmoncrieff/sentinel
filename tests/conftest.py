"""Shared pytest setup: make the script directories importable as top-level modules,
mirroring how the scripts are run (`python3 scripts/<dir>/<script>.py`)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

for sub in ("scripts", "scripts/pipeline", "scripts/review", "scripts/publish", "scripts/analysis"):
    path = str(ROOT / sub)
    if path not in sys.path:
        sys.path.insert(0, path)
