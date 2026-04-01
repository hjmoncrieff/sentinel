#!/usr/bin/env python3
"""
Initialize local-only analyst files from safe templates.

This script creates:
- data/review/users.local.json
- data/review/edits.local.json
- data/review/registry_edits.local.json

It never overwrites existing local files unless --force is provided.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REVIEW_DIR = ROOT / "data" / "review"

FILES = [
    ("users.template.json", "users.local.json"),
    ("edits.template.json", "edits.local.json"),
    ("registry_edits.template.json", "registry_edits.local.json"),
]


def copy_file(src: Path, dst: Path, force: bool) -> None:
    if dst.exists() and not force:
        print(f"Skipped existing {dst.relative_to(ROOT)}")
        return
    shutil.copyfile(src, dst)
    print(f"Created {dst.relative_to(ROOT)} from {src.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize local-only analyst files.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing local files.")
    args = parser.parse_args()

    for template_name, local_name in FILES:
        src = REVIEW_DIR / template_name
        dst = REVIEW_DIR / local_name
        if not src.exists():
            raise FileNotFoundError(f"Missing template: {src}")
        copy_file(src, dst, args.force)

    print("")
    print("Next steps:")
    print("1. Generate password hashes with: python3 scripts/review/hash_password.py")
    print("2. Replace the placeholder password_sha256 values in data/review/users.local.json")
    print("3. Start the analyst server with: python3 scripts/review/run_analyst_server.py")


if __name__ == "__main__":
    main()
