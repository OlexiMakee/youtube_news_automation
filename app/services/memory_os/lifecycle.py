import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Any, Tuple, Optional

from app.services.memory_os.config import MemosConfig

class LifecycleManager:
    """Manages the lifecycle operations of Memory OS files (propose, transition, manifest, prune)."""

    def __init__(self, config: Optional[MemosConfig] = None):
        self.config = config or MemosConfig()

    def _sha256_file(self, path: Path) -> str:
        if not path.exists():
            return ""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    def _load_jsonl(self, path: Path) -> List[Dict[str, Any]]:
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

    def _write_jsonl(self, path: Path, items: List[Dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item) + "\n")

    def _append_jsonl(self, path: Path, item: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(item) + "\n")

    def _validate_evidence(self, evidence_list: List[str]) -> bool:
        for item in evidence_list:
            if not item.startswith("http"):
                if not (self.config.root_dir / item).exists():
                    return False
        return True

    def propose(self, node_id: str, node_type: str, summary: str, evidence: str, 
                related_nodes: Optional[str] = None, validator: Optional[str] = None) -> int:
        nodes_file = self.config.memory_dir / "nodes.jsonl"
        events_file = self.config.memory_dir / "events.jsonl"

        nodes = self._load_jsonl(nodes_file)
        for n in nodes:
            if n["id"] == node_id:
                print(f"ERROR: Node '{node_id}' already exists.")
                return 1

        evidence_list = [e.strip() for e in evidence.split(",") if e.strip()]
        related = [r.strip() for r in related_nodes.split(",") if r.strip()] if related_nodes else []

        new_node = {
            "id": node_id,
            "type": node_type,
            "summary": summary,
            "evidence": evidence_list,
            "status": "draft",
            "freshness": datetime.now().isoformat(timespec="seconds"),
            "trust": "unverified",
            "related_nodes": related
        }

        self._append_jsonl(nodes_file, new_node)
        print(f"INFO: Proposed node '{node_id}' added as draft.")

        new_event = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "event": "memory.node.proposed",
            "node_id": node_id,
            "claim": f"Propose rule/fact: {summary}",
            "evidence": evidence_list,
            "validator": validator or "cli_proposer",
            "status": "pending"
        }
        self._append_jsonl(events_file, new_event)
        return 0

    def transition(self, validator: Optional[str] = None) -> int:
        nodes_file = self.config.memory_dir / "nodes.jsonl"
        edges_file = self.config.memory_dir / "edges.jsonl"
        events_file = self.config.memory_dir / "events.jsonl"

        nodes = self._load_jsonl(nodes_file)
        edges = self._load_jsonl(edges_file)
        events = self._load_jsonl(events_file)

        updated_nodes = []
        verified_ids = set()
        new_events = []

        for node in nodes:
            if node["status"] == "draft":
                if not node.get("id") or not node.get("summary") or node.get("type") not in ["rule", "fact", "variable", "connector", "config", "policy"]:
                    print(f"INFO: Rejecting transition for node '{node['id']}': invalid schema.")
                    node["status"] = "stale"
                    for ev in events:
                        if ev.get("node_id") == node["id"] and ev.get("event") == "memory.node.proposed" and ev.get("status") == "pending":
                            ev["status"] = "rejected"
                            ev["claim"] += " [Rejected: schema violation]"
                elif not self._validate_evidence(node["evidence"]):
                    print(f"INFO: Rejecting transition for node '{node['id']}': missing evidence files.")
                    node["status"] = "stale"
                    for ev in events:
                        if ev.get("node_id") == node["id"] and ev.get("event") == "memory.node.proposed" and ev.get("status") == "pending":
                            ev["status"] = "rejected"
                            ev["claim"] += " [Rejected: missing evidence]"
                else:
                    print(f"INFO: Transitioning node '{node['id']}' to verified.")
                    node["status"] = "verified"
                    node["trust"] = "verified"
                    node["freshness"] = datetime.now().isoformat(timespec="seconds")
                    verified_ids.add(node["id"])
                    for ev in events:
                        if ev.get("node_id") == node["id"] and ev.get("event") == "memory.node.proposed" and ev.get("status") == "pending":
                            ev["status"] = "accepted"

                    verification_event = {
                        "timestamp": datetime.now().isoformat(timespec="seconds"),
                        "event": "memory.node.verified",
                        "node_id": node["id"],
                        "claim": f"Verified node: {node['summary']}",
                        "evidence": node["evidence"],
                        "validator": validator or "lifecycle_manager",
                        "status": "accepted"
                    }
                    new_events.append(verification_event)

            updated_nodes.append(node)

        # Handle overrides/refutations
        for edge in edges:
            if edge["type"] in ["overrides", "refutes"]:
                source_id = edge["source"]
                target_id = edge["target"]

                source_verified = False
                for n in updated_nodes:
                    if n["id"] == source_id and n["status"] == "verified":
                        source_verified = True
                        break

                if source_verified:
                    for n in updated_nodes:
                        if n["id"] == target_id and n["status"] not in ["stale", "superseded"]:
                            new_status = "superseded" if edge["type"] == "overrides" else "stale"
                            print(f"INFO: Node '{target_id}' is deprecating to '{new_status}' due to edge '{edge['type']}' from '{source_id}'.")
                            n["status"] = new_status
                            n["freshness"] = datetime.now().isoformat(timespec="seconds")

                            dep_event = {
                                "timestamp": datetime.now().isoformat(timespec="seconds"),
                                "event": "memory.node.deprecated",
                                "node_id": target_id,
                                "claim": f"Deprecated to {new_status} via edge {edge['type']} from {source_id}",
                                "evidence": n["evidence"],
                                "validator": validator or "lifecycle_manager",
                                "status": "accepted"
                            }
                            new_events.append(dep_event)

        self._write_jsonl(nodes_file, updated_nodes)
        self._write_jsonl(events_file, events + new_events)
        print("INFO: Transition processing completed.")
        return 0

    def manifest(self) -> int:
        nodes_file = self.config.memory_dir / "nodes.jsonl"
        edges_file = self.config.memory_dir / "edges.jsonl"
        events_file = self.config.memory_dir / "events.jsonl"

        nodes = self._load_jsonl(nodes_file)
        edges = self._load_jsonl(edges_file)
        events = self._load_jsonl(events_file)

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

        manifest_data = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
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
                "nodes.jsonl": self._sha256_file(nodes_file),
                "edges.jsonl": self._sha256_file(edges_file),
                "events.jsonl": self._sha256_file(events_file)
            }
        }

        manifest_path = self.config.memory_dir / "manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        try:
            rel_manifest = manifest_path.relative_to(self.config.root_dir)
        except ValueError:
            rel_manifest = manifest_path
        print(f"INFO: Wrote manifest to {rel_manifest}")
        return 0

    def prune(self) -> int:
        nodes_file = self.config.memory_dir / "nodes.jsonl"
        edges_file = self.config.memory_dir / "edges.jsonl"

        nodes = self._load_jsonl(nodes_file)
        edges = self._load_jsonl(edges_file)

        pruned_nodes = []
        active_node_ids = set()
        pruned_count = 0

        for n in nodes:
            if n["status"] in ["stale", "superseded"]:
                print(f"INFO: Pruning stale/superseded node '{n['id']}'.")
                pruned_count += 1
            else:
                pruned_nodes.append(n)
                active_node_ids.add(n["id"])

        pruned_edges = []
        pruned_edges_count = 0
        for e in edges:
            if e["source"] in active_node_ids and e["target"] in active_node_ids:
                pruned_edges.append(e)
            else:
                print(f"INFO: Pruning dangling edge: {e['source']} -> {e['target']} ({e['type']})")
                pruned_edges_count += 1

        self._write_jsonl(nodes_file, pruned_nodes)
        self._write_jsonl(edges_file, pruned_edges)
        print(f"INFO: Pruning finished. Removed {pruned_count} nodes and {pruned_edges_count} edges.")
        return 0
