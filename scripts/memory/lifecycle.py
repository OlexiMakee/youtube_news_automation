#!/usr/bin/env python3
import sys
import json
import hashlib
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Any, Tuple

ROOT = Path(__file__).resolve().parents[2]
MEMORY_DIR = ROOT / "memory"

def log_info(msg: str):
    print(f"INFO: {msg}")

def log_error(msg: str):
    print(f"ERROR: {msg}", file=sys.stderr)

def sha256_file(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return items

def write_jsonl(path: Path, items: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item) + "\n")

def append_jsonl(path: Path, item: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(item) + "\n")

def validate_evidence(evidence_list: List[str]) -> bool:
    for item in evidence_list:
        if not item.startswith("http"):
            # Check if file exists relative to project root
            if not (ROOT / item).exists():
                return False
    return True

def cmd_propose(args: argparse.Namespace) -> int:
    nodes = load_jsonl(MEMORY_DIR / "nodes.jsonl")
    for n in nodes:
        if n["id"] == args.id:
            log_error(f"Node '{args.id}' already exists.")
            return 1

    evidence_list = [e.strip() for e in args.evidence.split(",") if e.strip()]
    related_nodes = [r.strip() for r in args.related_nodes.split(",") if r.strip()] if args.related_nodes else []

    new_node = {
        "id": args.id,
        "type": args.type,
        "summary": args.summary,
        "evidence": evidence_list,
        "status": "draft",
        "freshness": datetime.now().isoformat(timespec="seconds") if hasattr(datetime, "now") else "2026-06-02T09:00:00Z",
        "trust": "unverified",
        "related_nodes": related_nodes
    }

    append_jsonl(MEMORY_DIR / "nodes.jsonl", new_node)
    log_info(f"Proposed node '{args.id}' added as draft.")

    new_event = {
        "timestamp": datetime.now().isoformat(timespec="seconds") if hasattr(datetime, "now") else "2026-06-02T09:00:00Z",
        "event": "memory.node.proposed",
        "node_id": args.id,
        "claim": f"Propose rule/fact: {args.summary}",
        "evidence": evidence_list,
        "validator": args.validator or "cli_proposer",
        "status": "pending"
    }
    append_jsonl(MEMORY_DIR / "events.jsonl", new_event)
    return 0

def cmd_transition(args: argparse.Namespace) -> int:
    nodes = load_jsonl(MEMORY_DIR / "nodes.jsonl")
    edges = load_jsonl(MEMORY_DIR / "edges.jsonl")
    events = load_jsonl(MEMORY_DIR / "events.jsonl")

    # Step 1: Transition draft nodes to verified if evidence matches
    updated_nodes = []
    verified_ids = set()
    new_events = []
    
    for node in nodes:
        if node["status"] == "draft":
            # Check schema validation
            if not node.get("id") or not node.get("summary") or node.get("type") not in ["rule", "fact", "variable", "connector", "config", "policy"]:
                log_info(f"Rejecting transition for node '{node['id']}': invalid schema.")
                node["status"] = "stale"
                # Update event
                for ev in events:
                    if ev.get("node_id") == node["id"] and ev.get("event") == "memory.node.proposed" and ev.get("status") == "pending":
                        ev["status"] = "rejected"
                        ev["claim"] += " [Rejected: schema violation]"
            # Check evidence
            elif not validate_evidence(node["evidence"]):
                log_info(f"Rejecting transition for node '{node['id']}': missing evidence files.")
                node["status"] = "stale"
                # Update event
                for ev in events:
                    if ev.get("node_id") == node["id"] and ev.get("event") == "memory.node.proposed" and ev.get("status") == "pending":
                        ev["status"] = "rejected"
                        ev["claim"] += " [Rejected: missing evidence]"
            else:
                log_info(f"Transitioning node '{node['id']}' to verified.")
                node["status"] = "verified"
                node["trust"] = "verified"
                node["freshness"] = datetime.now().isoformat(timespec="seconds") if hasattr(datetime, "now") else "2026-06-02T09:00:00Z"
                verified_ids.add(node["id"])
                # Update event
                for ev in events:
                    if ev.get("node_id") == node["id"] and ev.get("event") == "memory.node.proposed" and ev.get("status") == "pending":
                        ev["status"] = "accepted"
                
                # Add verification event
                verification_event = {
                    "timestamp": datetime.now().isoformat(timespec="seconds") if hasattr(datetime, "now") else "2026-06-02T09:00:00Z",
                    "event": "memory.node.verified",
                    "node_id": node["id"],
                    "claim": f"Verified node: {node['summary']}",
                    "evidence": node["evidence"],
                    "validator": args.validator or "lifecycle_manager",
                    "status": "accepted"
                }
                new_events.append(verification_event)
        
        updated_nodes.append(node)

    # Step 2: Handle edge-based overrides/refutations
    for edge in edges:
        # If source overrides or refutes target
        if edge["type"] in ["overrides", "refutes"]:
            source_id = edge["source"]
            target_id = edge["target"]
            
            # Find if source is verified and active
            source_verified = False
            for n in updated_nodes:
                if n["id"] == source_id and n["status"] == "verified":
                    source_verified = True
                    break
            
            if source_verified:
                for n in updated_nodes:
                    if n["id"] == target_id and n["status"] not in ["stale", "superseded"]:
                        new_status = "superseded" if edge["type"] == "overrides" else "stale"
                        log_info(f"Node '{target_id}' is deprecating to '{new_status}' due to edge '{edge['type']}' from '{source_id}'.")
                        n["status"] = new_status
                        n["freshness"] = datetime.now().isoformat(timespec="seconds") if hasattr(datetime, "now") else "2026-06-02T09:00:00Z"
                        
                        # Add deprecation event
                        dep_event = {
                            "timestamp": datetime.now().isoformat(timespec="seconds") if hasattr(datetime, "now") else "2026-06-02T09:00:00Z",
                            "event": "memory.node.deprecated",
                            "node_id": target_id,
                            "claim": f"Deprecated to {new_status} via edge {edge['type']} from {source_id}",
                            "evidence": n["evidence"],
                            "validator": args.validator or "lifecycle_manager",
                            "status": "accepted"
                        }
                        new_events.append(dep_event)

    write_jsonl(MEMORY_DIR / "nodes.jsonl", updated_nodes)
    write_jsonl(MEMORY_DIR / "events.jsonl", events + new_events)
    log_info("Transition processing completed.")
    return 0

def cmd_manifest(args: argparse.Namespace) -> int:
    nodes = load_jsonl(MEMORY_DIR / "nodes.jsonl")
    edges = load_jsonl(MEMORY_DIR / "edges.jsonl")
    events = load_jsonl(MEMORY_DIR / "events.jsonl")

    # Counts
    node_statuses = {}
    node_types = {}
    for n in nodes:
        node_statuses[n["status"]] = node_statuses.get(n["status"], 0) + 1
        node_types[n["type"]] = node_types.get(n["type"], 0) + 1

    edge_types = {}
    for e in edges:
        edge_types[e["type"]] = edge_types.get(e["type"], 0) + 1

    event_statuses = {}
    for ev in events:
        event_statuses[ev["status"]] = event_statuses.get(ev["status"], 0) + 1

    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds") if hasattr(datetime, "now") else "2026-06-02T09:00:00Z",
        "counts": {
            "nodes": len(nodes),
            "node_statuses": node_statuses,
            "node_types": node_types,
            "edges": len(edges),
            "edge_types": edge_types,
            "events": len(events),
            "event_statuses": event_statuses
        },
        "checksums": {
            "nodes.jsonl": sha256_file(MEMORY_DIR / "nodes.jsonl"),
            "edges.jsonl": sha256_file(MEMORY_DIR / "edges.jsonl"),
            "events.jsonl": sha256_file(MEMORY_DIR / "events.jsonl")
        }
    }

    manifest_path = MEMORY_DIR / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        
    log_info(f"Wrote manifest to {manifest_path.relative_to(ROOT)}")
    return 0

def cmd_prune(args: argparse.Namespace) -> int:
    nodes = load_jsonl(MEMORY_DIR / "nodes.jsonl")
    edges = load_jsonl(MEMORY_DIR / "edges.jsonl")

    # Filter active nodes
    pruned_nodes = []
    active_node_ids = set()
    pruned_count = 0

    for n in nodes:
        if n["status"] in ["stale", "superseded"]:
            log_info(f"Pruning stale/superseded node '{n['id']}'.")
            pruned_count += 1
        else:
            pruned_nodes.append(n)
            active_node_ids.add(n["id"])

    # Filter edges (no dangling references to pruned nodes)
    pruned_edges = []
    pruned_edges_count = 0
    for e in edges:
        if e["source"] in active_node_ids and e["target"] in active_node_ids:
            pruned_edges.append(e)
        else:
            log_info(f"Pruning dangling edge: {e['source']} -> {e['target']} ({e['type']})")
            pruned_edges_count += 1

    write_jsonl(MEMORY_DIR / "nodes.jsonl", pruned_nodes)
    write_jsonl(MEMORY_DIR / "edges.jsonl", pruned_edges)
    log_info(f"Pruning finished. Removed {pruned_count} nodes and {pruned_edges_count} edges.")
    return 0

def main() -> int:
    parser = argparse.ArgumentParser(description="Memory OS Lifecycle Transition Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Propose
    p_propose = subparsers.add_parser("propose", help="Propose a new rule or fact memory node.")
    p_propose.add_argument("--id", required=True, help="Namespace ID of node.")
    p_propose.add_argument("--type", choices=["rule", "fact", "variable"], required=True)
    p_propose.add_argument("--summary", required=True, help="Short text summary.")
    p_propose.add_argument("--evidence", required=True, help="Comma-separated evidence file paths.")
    p_propose.add_argument("--related-nodes", help="Comma-separated related node IDs.")
    p_propose.add_argument("--validator", help="Validator context ID.")

    # Transition
    p_trans = subparsers.add_parser("transition", help="Transition draft nodes through trust states.")
    p_trans.add_argument("--validator", help="Validator context ID.")

    # Manifest
    subparsers.add_parser("manifest", help="Compute metrics and SHA256 checksum manifest.")

    # Prune
    subparsers.add_parser("prune", help="Purge stale or superseded memory nodes.")

    args = parser.parse_args()

    if args.command == "propose":
        return cmd_propose(args)
    elif args.command == "transition":
        return cmd_transition(args)
    elif args.command == "manifest":
        return cmd_manifest(args)
    elif args.command == "prune":
        return cmd_prune(args)

    return 0

if __name__ == "__main__":
    sys.exit(main())
