#!/usr/bin/env python3
"""Portable Memos control CLI for project-local Memory OS operations."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.memory.audit_memos import audit, to_markdown
from scripts.validate_task_capsules import validate_file


DEFAULT_WORKFLOWS = """# Workflows

Use two explicit workstreams:
- `product`: customer-facing product work.
- `memos`: internal shorthand for Memory OS work, agent workflow, telemetry, repo analysis, and self-improvement tools.

Naming guard: `memos` is a command/workflow alias for Memory OS. It is not the
final product name and is unrelated to the existing Memos note-taking app.

Step scale: 1 nano, 2 micro, 3 tiny, 4 little, 5 pretty little, 6 light mid,
7 mid, 8 high mid, 9 mid high, 10 big, 11 large, 12 giant.
"""

DEFAULT_AGENTS_BLOCK = """\n## Memos Integration

- Read `agent_context/WORKFLOWS.md` before choosing task scope.
- Route work through `product` or `memos`.
- Treat `memos` as an internal Memory OS alias, not a final product name.
- Use the 12-step scale from `nano` to `giant`.
- Run `python scripts/memos.py audit` before broad Memory OS changes.
"""

DEFAULT_WORKFLOW_TOMLS = {
    "chat.nano.toml": """id = "chat.nano"
step_min = 1
step_max = 2
level_min = 1
level_max = 18
model_policy = "cheap_free"
tools = ["search_memory"]
verification = ["schema_check"]

[memory_policy]
max_cards = 3
max_tokens = 1200

[escalation]
if_uncertainty_above = 0.6
escalate_to = "chat.standard"
""",
    "code.small.toml": """id = "code.small"
step_min = 3
step_max = 8
level_min = 26
level_max = 64
model_policy = "codex"
tools = ["search_memory", "validate_memory"]
verification = ["test_run_required"]

[memory_policy]
max_cards = 10
max_tokens = 4000

[escalation]
if_risk_above = 0.5
escalate_to = "code.standard"
""",
    "architecture.giant.toml": """id = "architecture.giant"
step_min = 9
step_max = 12
level_min = 65
level_max = 100
model_policy = "large_reasoning"
tools = ["repo_index", "symbol_search", "test_runner", "adr_writer"]
verification = ["dry_run_required", "user_approval_required"]

[memory_policy]
root_files = ["AGENTS.md", "INDEX.md", "README.md"]
graph_depth = 3
require_evidence = true

[output]
format = "adr_proposal"
""",
}


def write_if_missing(path: Path, content: str, actions: List[str]) -> None:
    if path.exists():
        actions.append(f"exists {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    actions.append(f"created {path}")


def append_if_absent(path: Path, marker: str, content: str, actions: List[str]) -> None:
    if path.exists():
        text = path.read_text(encoding="utf-8", errors="ignore")
        if marker in text:
            actions.append(f"already integrated {path}")
            return
        path.write_text(text.rstrip() + "\n" + content.lstrip(), encoding="utf-8")
        actions.append(f"updated {path}")
        return
    path.write_text(content.lstrip(), encoding="utf-8")
    actions.append(f"created {path}")


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    actions: List[str] = []
    write_if_missing(root / "agent_context" / "WORKFLOWS.md", DEFAULT_WORKFLOWS, actions)
    write_if_missing(
        root / "agent_context" / "HANDSHAKE.md",
        "# Agent Handshake\n\n## Current Session Status\n- Active Agent: unknown\n- Budget Tier applied: `memos nano` / score 1\n- Target: Initial Memos bootstrap.\n",
        actions,
    )
    write_if_missing(root / "agent_context" / "development_log.md", "# Development Log\n", actions)
    write_if_missing(root / "agent_context" / "task_capsules.jsonl", "", actions)
    write_if_missing(root / "memory" / "nodes.jsonl", "", actions)
    write_if_missing(root / "memory" / "edges.jsonl", "", actions)
    write_if_missing(root / "memory" / "events.jsonl", "", actions)
    for filename, content in DEFAULT_WORKFLOW_TOMLS.items():
        write_if_missing(root / "workflows" / filename, content, actions)
    write_if_missing(
        root / "memos.config.json",
        json.dumps({
            "version": "0.1",
            "created_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            "workflows": ["product", "memos"],
            "step_scale": "1..12",
        }, indent=2, sort_keys=True) + "\n",
        actions,
    )
    print("\n".join(actions))
    return 0


def cmd_integrate(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    actions: List[str] = []
    if not (root / "agent_context" / "WORKFLOWS.md").exists():
        write_if_missing(root / "agent_context" / "WORKFLOWS.md", DEFAULT_WORKFLOWS, actions)
    append_if_absent(root / "AGENTS.md", "## Memos Integration", DEFAULT_AGENTS_BLOCK, actions)
    print("\n".join(actions))
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    report = audit(Path(args.root).resolve())
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(to_markdown(report))
    return 1 if report["capsule_jsonl_errors"] or report["capsule_validation_errors"] else 0


def cmd_validate(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    from scripts.memory.validate_workflows import build_report as build_workflow_report

    errors = validate_file(root / "agent_context" / "task_capsules.jsonl")
    report = audit(root)
    errors.extend(report["capsule_jsonl_errors"])
    for name, meta in report["memory_lifecycle"].items():
        for error in meta.get("errors", []):
            errors.append(f"memory/{name}: {error}")
    workflow_report = build_workflow_report(root)
    errors.extend(f"workflows: {error}" for error in workflow_report["errors"])
    for error in report.get("proposal_validation_errors", []):
        errors.append(f"proposals: {error}")

    if errors:
        print("\n".join(errors))
        return 1
    print("memos validation ok")
    return 0


def cmd_snapshot(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    if root != ROOT:
        print("snapshot currently supports this repository root only", file=sys.stderr)
        return 2
    command = [sys.executable, str(ROOT / "scripts" / "compact_memory.py")]
    if args.write:
        command.append("--write")
    return subprocess.run(command, cwd=str(ROOT), check=False).returncode


def cmd_method_proposals(args: argparse.Namespace) -> int:
    from scripts.analytics.method_review_proposals import generate_method_review_proposals

    root = Path(args.root).resolve()
    try:
        result = generate_method_review_proposals(
            snapshot_path=str(root / args.snapshot_path),
            proposals_path=str(root / args.proposals_path),
            events_path=str(root / args.events_path),
            min_runs_for_proposal=args.min_runs_for_proposal,
            write=args.write,
            lifecycle_event=args.lifecycle_event,
        )
    except Exception as exc:
        print(f"method-proposals failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def cmd_quantize(args: argparse.Namespace) -> int:
    from scripts.memory.quantize_task import calculate_score, resolve_profile

    legacy_score = calculate_score(
        args.task,
        risk=args.risk,
        volume=args.volume,
        uncertainty=args.uncertainty,
    )
    result = {
        "task": args.task,
        "legacy_score": legacy_score,
        **resolve_profile(legacy_score),
    }
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"Task: {result['task']}")
        print(f"Legacy Score: {result['legacy_score']}/100")
        print(f"Step Score: {result['step_score']}/12")
        print(f"Step Name: {result['step_name']}")
        print(f"Workflow ID: {result['workflow_id']}")
        print(f"Model Policy: {result['model_policy']}")
        print(f"Escalate: {str(result['escalate']).lower()}")
    return 0


def cmd_workflows(args: argparse.Namespace) -> int:
    from scripts.memory.validate_workflows import build_report, to_markdown, write_manifest

    root = Path(args.root).resolve()
    report = build_report(root)
    if args.write_manifest:
        write_manifest(report, root / args.manifest_path)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(to_markdown(report))
    return 0 if report["ok"] else 1


def cmd_compact(args: argparse.Namespace) -> int:
    from scripts.memory.compact_capsules import compact_capsules

    root = Path(args.root).resolve()
    return compact_capsules(root, provider=args.provider, model=args.model)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Memos project-local Memory OS CLI.")
    parser.add_argument("--root", default=str(ROOT), help="Project root")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create missing Memos control files.")
    init_parser.set_defaults(func=cmd_init)

    integrate_parser = subparsers.add_parser("integrate", help="Add minimal Memos agent instructions.")
    integrate_parser.set_defaults(func=cmd_integrate)

    audit_parser = subparsers.add_parser("audit", help="Audit Memos control-plane state.")
    audit_parser.add_argument("--format", choices={"json", "markdown"}, default="markdown")
    audit_parser.set_defaults(func=cmd_audit)

    validate_parser = subparsers.add_parser("validate", help="Validate task capsules and lifecycle JSONL.")
    validate_parser.set_defaults(func=cmd_validate)

    snapshot_parser = subparsers.add_parser("snapshot", help="Build compact memory snapshot for this repo.")
    snapshot_parser.add_argument("--write", action="store_true", help="Write agent_context/memory_snapshot.json")
    snapshot_parser.set_defaults(func=cmd_snapshot)

    proposals_parser = subparsers.add_parser(
        "method-proposals",
        help="Convert data method-review insights into admin proposals.",
    )
    proposals_parser.add_argument("--snapshot-path", default="data/data_access_method_review.json")
    proposals_parser.add_argument("--proposals-path", default="agent_proposals/admin_proposals.jsonl")
    proposals_parser.add_argument("--events-path", default="memory/events.jsonl")
    proposals_parser.add_argument("--min-runs-for-proposal", type=int, default=3)
    proposals_parser.add_argument("--write", action="store_true", help="Append new proposals. Dry-run by default.")
    proposals_parser.add_argument("--lifecycle-event", action="store_true", help="Append Memory OS lifecycle event.")
    proposals_parser.set_defaults(func=cmd_method_proposals)

    quantize_parser = subparsers.add_parser("quantize", help="Quantize a task into the 12-step Memory OS scale.")
    quantize_parser.add_argument("--task", required=True, help="Task description")
    quantize_parser.add_argument("--risk", type=float, default=0.0)
    quantize_parser.add_argument("--volume", type=float, default=0.0)
    quantize_parser.add_argument("--uncertainty", type=float, default=0.0)
    quantize_parser.add_argument("--format", choices={"json", "text"}, default="text")
    quantize_parser.set_defaults(func=cmd_quantize)

    workflows_parser = subparsers.add_parser("workflows", help="Validate workflow TOML specs and build a manifest.")
    workflows_parser.add_argument("--format", choices={"json", "markdown"}, default="markdown")
    workflows_parser.add_argument("--write-manifest", action="store_true")
    workflows_parser.add_argument("--manifest-path", default="memory/workflow_manifest.json")
    workflows_parser.set_defaults(func=cmd_workflows)

    compact_parser = subparsers.add_parser(
        "compact",
        help="Parse task capsules to extract new memory nodes and edges via LLM.",
    )
    compact_parser.add_argument("--provider", help="Optional provider override (gemini, openrouter, openai)")
    compact_parser.add_argument("--model", help="Optional model override")
    compact_parser.set_defaults(func=cmd_compact)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
