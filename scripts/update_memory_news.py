#!/usr/bin/env python3
"""
Incremental memory_news update — runs after each scrape.
1. Re-ingests nodes from youtube_news.db
2. Resets edges and rebuilds via link-infer (text method)

Safe to call repeatedly — idempotent.
"""

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "memory_os.config.json"
EDGES = ROOT / "memory" / "news" / "edges.jsonl"
PYTHON = sys.executable
CLI = ROOT / "memory_os_local" / "src" / "memory_os" / "cli.py"
INGEST = ROOT / "scripts" / "ingest_memory_news.py"


def run(cmd: list, label: str) -> bool:
    t0 = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = round(time.time() - t0, 1)
    if result.returncode != 0:
        print(f"  [!] {label} failed ({elapsed}s):\n{result.stderr.strip()}")
        return False
    last_line = result.stdout.strip().split("\n")[-1] if result.stdout.strip() else ""
    print(f"  [✓] {label} ({elapsed}s) — {last_line}")
    return True


def main() -> int:
    print("\n[memory_news] Updating graph after scrape...")

    # 1. Re-ingest nodes
    ok = run([PYTHON, str(INGEST)], "ingest nodes")
    if not ok:
        return 1

    # 2. Reset edges (nodes changed — old edges may be stale)
    EDGES.write_text("")

    # 3. Rebuild edges via text link-infer
    env_extra = {"PYTHONPATH": str(ROOT / "memory_os_local" / "src")}
    import os
    env = {**os.environ, **env_extra}
    result = subprocess.run(
        [PYTHON, str(CLI), "--config", str(CONFIG), "--space", "news", "link-infer", "--method", "cascade", "--resource-mode", "max"],
        capture_output=True, text=True, env=env
    )
    elapsed_label = result.stdout.strip().split("\n")[-1] if result.stdout.strip() else ""
    if result.returncode != 0:
        print(f"  [!] link-infer failed:\n{result.stderr.strip()}")
        return 1
    print(f"  [✓] link-infer — {elapsed_label}")

    print("[memory_news] Graph updated.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
