#!/usr/bin/env python3
"""Portable Memos control CLI for project-local Memory OS operations."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.memory_os import (
    MemosConfig,
    MemoryValidator,
    MemoryCompactor,
    LifecycleManager,
    MemorySearcher,
    MemoryOS
)
from scripts.memory.audit_memos import audit, to_markdown

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
    config_path = os.environ.get("MEMOS_CONFIG_PATH") or (root / "memos.config.json")
    config = MemosConfig(config_path=str(config_path) if Path(config_path).exists() else None)
    
    validator = MemoryValidator(config)
    errors = []
    
    errors.extend(validator.validate_file())
    errors.extend(validator.validate_nodes())
    errors.extend(validator.validate_edges())
    errors.extend(validator.validate_events())
    errors.extend(validator.validate_proposals_file())

    from scripts.memory.validate_workflows import build_report as build_workflow_report
    workflow_report = build_workflow_report(root)
    errors.extend(f"workflows: {error}" for error in workflow_report["errors"])

    if errors:
        print("\n".join(errors))
        return 1
    print("memos validation ok")
    return 0

def cmd_snapshot(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    # Find script path relative to this script's directory
    script_dir = Path(__file__).resolve().parent
    command = [sys.executable, str(script_dir / "compact_memory.py")]
    if args.write:
        command.append("--write")
    return subprocess.run(command, cwd=str(root), check=False).returncode

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
    root = Path(args.root).resolve()
    config_path = os.environ.get("MEMOS_CONFIG_PATH") or (root / "memos.config.json")
    config = MemosConfig(config_path=str(config_path) if Path(config_path).exists() else None)
    compactor = MemoryCompactor(config)
    return compactor.compact_capsules(provider=args.provider, model=args.model)

def cmd_search(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config_path = args.config or os.environ.get("MEMOS_CONFIG_PATH")
    config = MemosConfig(config_path)
    searcher = MemorySearcher(config)

    matches = searcher.search_memory(args.query, args.depth)

    if args.json:
        print(json.dumps(matches, indent=2))
    else:
        nodes = [m for m in matches if m["type"] != "code_file"]
        code_files = [m for m in matches if m["type"] == "code_file"]

        if not nodes and not code_files:
            print(f"No matches found for query '{args.query}'")
            return 0

        if nodes:
            print(f"Found {len(nodes)} matched memory nodes:")
            for node in nodes:
                print(f"\n[{node['id']}] ({node['type']})")
                print(f"  Summary: {node['summary']}")
                print(f"  Status: {node['status']} | Trust: {node['trust']}")
                if node.get("evidence"):
                    print(f"  Evidence: {', '.join(node['evidence'])}")

        if code_files:
            if nodes:
                print("\n" + "="*50 + "\n")
            print(f"Found {len(code_files)} matched codebase files:")
            for item in code_files:
                print(f"\n[{item['id']}] ({item['layer']}) - Rank {item['rank']} ({item['match_type']})")
                if item.get("classes"):
                    print(f"  Classes: {', '.join(item['classes'])}")
                if item.get("functions"):
                    print(f"  Functions: {', '.join(item['functions'])}")
                if item.get("routes"):
                    print(f"  Routes: {', '.join(item['routes'])}")
                if item.get("dependencies"):
                    print(f"  Dependencies: {', '.join(item['dependencies'])}")
                if item.get("headings"):
                    print(f"  Headings: {', '.join(item['headings'])}")
                preview = item["summary"][:240]
                print(f"  Preview: {preview}...")
    return 0

def cmd_user_memory(args: argparse.Namespace) -> int:
    db_path = str(Path(args.root).resolve() / "data" / "memory_os.db")
    memory_os = MemoryOS(db_path=db_path)

    if args.action == "list":
        memories = memory_os.get_memories(limit=args.limit)
        if not memories:
            print("No user memories found.")
            return 0
        print(f"Found {len(memories)} user memories:")
        for mem in memories:
            print(f"\n- ID: {mem['id']}")
            print(f"  Type: {mem['type']}")
            if mem.get('summary'):
                print(f"  Summary: {mem['summary']}")
            print(f"  Importance: {mem['importance']}")
            print(f"  Content: {mem['content']}")
            print(f"  Timestamp: {datetime.fromtimestamp(mem['timestamp']).isoformat()}")
            
    elif args.action == "add":
        if not args.id or not args.type or not args.content:
            print("Error: --id, --type, and --content are required to add/update user memory.", file=sys.stderr)
            return 1
        memory_os.add_or_update_memory(
            memory_id=args.id,
            mem_type=args.type,
            content=args.content,
            summary=args.summary,
            importance=args.importance,
            timestamp=args.timestamp
        )
        print(f"Successfully added/updated user memory '{args.id}'")
        
    elif args.action == "delete":
        if not args.id:
            print("Error: --id is required to delete a user memory.", file=sys.stderr)
            return 1
        conn = memory_os.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE id = ?", (args.id,))
            conn.commit()
            if cursor.rowcount > 0:
                print(f"Successfully deleted user memory '{args.id}'")
            else:
                print(f"User memory '{args.id}' not found.")
        finally:
            conn.close()
            
    elif args.action == "search":
        if not args.query:
            print("Error: --query is required to search user memories.", file=sys.stderr)
            return 1
        conn = memory_os.get_connection()
        try:
            cursor = conn.cursor()
            q = f"%{args.query}%"
            cursor.execute(
                "SELECT id, type, content, summary, importance, timestamp FROM memories "
                "WHERE id LIKE ? OR content LIKE ? OR summary LIKE ? "
                "ORDER BY importance DESC, timestamp DESC LIMIT ?",
                (q, q, q, args.limit)
            )
            rows = [dict(r) for r in cursor.fetchall()]
            if not rows:
                print(f"No user memories match query '{args.query}'")
                return 0
            print(f"Found {len(rows)} matching user memories:")
            for mem in rows:
                print(f"\n- ID: {mem['id']}")
                print(f"  Type: {mem['type']}")
                if mem.get('summary'):
                    print(f"  Summary: {mem['summary']}")
                print(f"  Importance: {mem['importance']}")
                print(f"  Content: {mem['content']}")
        finally:
            conn.close()
            
    return 0

def cmd_context(args: argparse.Namespace) -> int:
    from app.services.prompt_builder import SystemPromptBuilder, DashboardContextBuilder
    channel_ids = [c.strip() for c in args.channels.split(",")] if args.channels else None
    
    db_context = DashboardContextBuilder.build(
        channel_ids=channel_ids,
        start_date=args.start_date,
        end_date=args.end_date,
        limit=args.limit
    )
    
    system_prompt = SystemPromptBuilder.build(db_context, role=args.role)
    print(system_prompt)
    return 0

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Memos project-local Memory OS CLI.")
    parser.add_argument("--root", default=str(ROOT), help="Project root")
    parser.add_argument("--config", help="Path to memos.config.json file")
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

    search_parser = subparsers.add_parser(
        "search",
        help="Query Memory OS nodes, codebase symbols, and traverse relations."
    )
    search_parser.add_argument("query", help="Keyword query or exact symbol.")
    search_parser.add_argument("--depth", type=int, default=1, help="Graph traversal recursion depth.")
    search_parser.add_argument("--json", action="store_true", help="Output raw JSON instead of human-readable text.")
    search_parser.set_defaults(func=cmd_search)

    user_mem_parser = subparsers.add_parser(
        "user-memory",
        help="Manage User-Facing Memory OS memories."
    )
    user_mem_parser.add_argument("action", choices={"list", "add", "delete", "search"}, help="Action to perform")
    user_mem_parser.add_argument("--id", help="Memory ID (required for add/delete)")
    user_mem_parser.add_argument("--type", help="Memory type, e.g. fact, preference, alert_rule (required for add)")
    user_mem_parser.add_argument("--content", help="Memory text content (required for add)")
    user_mem_parser.add_argument("--summary", help="Short summary/title (optional)")
    user_mem_parser.add_argument("--importance", type=float, default=0.0, help="Importance score [0.0..1.0] (optional)")
    user_mem_parser.add_argument("--timestamp", type=int, help="Unix timestamp (optional)")
    user_mem_parser.add_argument("--query", help="Search query string (required for search)")
    user_mem_parser.add_argument("--limit", type=int, default=50, help="Max memories to return")
    user_mem_parser.set_defaults(func=cmd_user_memory)

    context_parser = subparsers.add_parser(
        "context",
        help="Compile and display system prompt context."
    )
    context_parser.add_argument("--role", default="admin", choices={"admin", "user"}, help="User role")
    context_parser.add_argument("--channels", help="Comma-separated list of channel IDs to filter context")
    context_parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    context_parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    context_parser.add_argument("--limit", type=int, default=10, help="Max top videos to include")
    context_parser.set_defaults(func=cmd_context)

    return parser

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    
    config_path = args.config
    if not config_path and args.root:
        root_path = Path(args.root).resolve()
        candidate = root_path / "memos.config.json"
        if candidate.exists():
            config_path = str(candidate)
            
    if config_path:
        os.environ["MEMOS_CONFIG_PATH"] = config_path
        
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())
