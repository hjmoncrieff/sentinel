#!/usr/bin/env python3
"""Mirror SENTINEL documentation into the local Obsidian vault.

This runner copies the project documentation set into the standing Obsidian
documentation directory:

    /Users/hjmoncrieff/Library/CloudStorage/Dropbox/MyObsidiainVault/Sentinel Documentation

It is intentionally narrow. The mirror is for documentation, guides, workflow
notes, setup notes, and diagrams, not for the full live data layer.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET = Path(
    "/Users/hjmoncrieff/Library/CloudStorage/Dropbox/MyObsidiainVault/"
    "Sentinel Documentation"
)
MANIFEST_NAME = ".sentinel-doc-sync-manifest.json"


def build_source_list() -> list[Path]:
    sources: list[Path] = []

    for pattern in ("docs/*.md", "docs/*.svg"):
        sources.extend(sorted(ROOT.glob(pattern)))

    sources.append(ROOT / "data" / "CODEBOOK.md")

    # Keep the set deterministic and unique.
    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in sources:
        resolved = path.resolve()
        if resolved in seen or not path.exists():
            continue
        seen.add(resolved)
        deduped.append(path)
    return deduped


def relative_target_path(source: Path) -> Path:
    if source.name == "CODEBOOK.md":
        return Path("data") / source.name
    if source.parts[-2] == "docs":
        return Path("docs") / source.name
    return source.relative_to(ROOT)


def sync_docs(target_root: Path) -> dict:
    target_root.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    managed_now: set[str] = set()

    for source in build_source_list():
        rel = relative_target_path(source)
        destination = target_root / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied.append(str(rel))
        managed_now.add(str(rel))

    manifest_path = target_root / MANIFEST_NAME
    previous_manifest = {"managed_files": []}
    if manifest_path.exists():
        previous_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    removed: list[str] = []
    for rel in previous_manifest.get("managed_files", []):
        if rel in managed_now:
            continue
        stale = target_root / rel
        if stale.exists():
            stale.unlink()
            removed.append(rel)

    manifest = {
        "source_root": str(ROOT),
        "target_root": str(target_root),
        "managed_files": sorted(managed_now),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    return {
        "target_root": str(target_root),
        "copied_count": len(copied),
        "removed_count": len(removed),
        "copied": copied,
        "removed": removed,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_TARGET,
        help="Override the Obsidian mirror target directory.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = sync_docs(args.target)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
