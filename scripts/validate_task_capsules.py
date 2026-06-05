"""Validate agent task capsule JSONL files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_os import MemoryOSConfig, MemoryValidator

def validate_rows(lines: Iterable[str]) -> List[str]:
    config = MemoryOSConfig()
    validator = MemoryValidator(config)
    return validator.validate_rows(lines)

def validate_file(path: Path) -> List[str]:
    config = MemoryOSConfig()
    validator = MemoryValidator(config)
    return validator.validate_file(path)

def main() -> int:
    parser = argparse.ArgumentParser(description="Validate task capsule JSONL.")
    parser.add_argument(
        "path",
        nargs="?",
        default="agent_context/task_capsules.jsonl",
        help="Path to task_capsules.jsonl",
    )
    args = parser.parse_args()

    errors = validate_file(Path(args.path))
    if errors:
        for error in errors:
            print(error)
        return 1

    print("task capsules ok")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
