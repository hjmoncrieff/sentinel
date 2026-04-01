#!/usr/bin/env python3
"""Print a SHA-256 password hash for local analyst-console credentials."""

from __future__ import annotations

import getpass
import hashlib


def main() -> None:
    password = getpass.getpass("Password: ")
    print(hashlib.sha256(password.encode("utf-8")).hexdigest())


if __name__ == "__main__":
    main()
