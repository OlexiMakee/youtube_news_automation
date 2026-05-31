#!/usr/bin/env python3
"""Deprecated compatibility wrapper for the old v2 migration command."""

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.migrate_db import main as migrate_main


if __name__ == "__main__":
    if "--rollback" in sys.argv:
        print("Refusing deprecated --rollback. Restore a DB backup instead.", file=sys.stderr)
        sys.exit(2)

    print("scripts/migrate_db_v2.py is deprecated; using scripts/migrate_db.py.")
    forwarded = ["--apply" if arg == "--execute" else arg for arg in sys.argv[1:]]
    sys.exit(migrate_main(forwarded))
