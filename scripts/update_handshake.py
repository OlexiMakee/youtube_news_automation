# HANDSHAKE_PROMPT: Read agent_context/HANDSHAKE.md first; continue NEXT only; keep patches tiny; backend-test by default; leave UI clicks to user.
"""Write a tiny handoff file for the next agent."""

from __future__ import annotations

import argparse
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HANDSHAKE_PATH = ROOT / "agent_context" / "HANDSHAKE.md"
PROMPT = (
    "Read this first; obey AGENT_RULES.md tiers; continue the NEXT HANDOVER only; "
    "keep patches scoped; backend-test by default; UI click-through stays with user."
)


def _git_status() -> str:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
            timeout=5,
        )
    except Exception as exc:
        return f"unavailable: {exc}"

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        return "clean"
    shown = lines[:12]
    suffix = "" if len(lines) <= 12 else f"\n- ... {len(lines) - 12} more"
    return "\n".join(f"- {line}" for line in shown) + suffix


def main() -> int:
    parser = argparse.ArgumentParser(description="Update agent_context/HANDSHAKE.md")
    parser.add_argument("--last", default="Updated agent handoff.")
    parser.add_argument("--place", default="Agent onboarding.")
    parser.add_argument("--next", default="Continue the next handover target from this file.")
    parser.add_argument("--files", default="agent_context/HANDSHAKE.md, scripts/update_handshake.py")
    parser.add_argument("--agent", default="Codex")
    parser.add_argument("--tier", default="codex medium limits")
    parser.add_argument("--target", default="Small scoped roadmap patch.")
    parser.add_argument("--with-status", action="store_true", help="Include a capped git status snapshot.")
    args = parser.parse_args()
    status = _git_status() if args.with_status else "skipped; run with --with-status if needed"

    content = f"""<!-- HANDSHAKE_PROMPT: {PROMPT} -->
# Agent Handshake

## Current Session Status
- Active Agent: {args.agent}
- Budget Tier applied: `{args.tier}`
- Target: {args.target}

## Completed Today
- [x] {args.last}

## Blocked / Pending
- [ ] Keep live DB migrations blocked until explicit user confirmation.

## Next Handover
- Target Command: choose the smallest tier that fits the next task.
- Context Payload:
  1. Read `agent_context/AGENT_RULES.md`.
  2. Continue from: {args.next}
  3. Scope: {args.place}

## Last Change
- Updated at: {datetime.now().isoformat(timespec="seconds")}
- Files: {args.files}
- Status: {status}
"""
    HANDSHAKE_PATH.write_text(content, encoding="utf-8")
    print(f"wrote {HANDSHAKE_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
