import json
from pathlib import Path
from typing import List, Dict, Any, Iterable, Optional
from app.services.memory_os.config import MemosConfig

REQUIRED_CAPSULE_FIELDS = {
    "timestamp",
    "task",
    "files_modified",
    "hurdles_regression",
    "resolution",
    "lessons_learned",
}
VALID_WORKFLOWS = {"product", "memos"}
VALID_STEP_SCORES = set(range(1, 13))
VALID_STEP_NAMES = {
    "nano", "micro", "tiny", "little", "pretty little", "light mid",
    "mid", "high mid", "mid high", "big", "large", "giant"
}

class MemoryValidator:
    """Validator for Memory OS schemas, task capsules, and workflows."""

    def __init__(self, config: Optional[MemosConfig] = None):
        self.config = config or MemosConfig()

    def _is_non_empty_string(self, value: object) -> bool:
        return isinstance(value, str) and bool(value.strip())

    def validate_nodes(self) -> List[str]:
        nodes_file = self.config.memory_dir / "nodes.jsonl"
        errors: List[str] = []
        if not nodes_file.exists():
            return [f"nodes.jsonl not found at {nodes_file}"]

        valid_types = {"rule", "fact", "variable", "connector", "config", "policy"}
        valid_statuses = {"draft", "observed", "verified", "stale", "superseded"}
        valid_trusts = {"verified", "unverified"}

        with open(nodes_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    node = json.loads(line)
                except json.JSONDecodeError as err:
                    errors.append(f"nodes.jsonl:L{line_num} is invalid JSON: {err}")
                    continue

                # Validate required fields
                req = ["id", "type", "summary", "evidence", "status", "freshness", "trust"]
                node_ok = True
                for field in req:
                    if field not in node:
                        errors.append(f"nodes.jsonl:L{line_num} missing required field '{field}'")
                        node_ok = False

                if not node_ok:
                    continue

                if node["type"] not in valid_types:
                    errors.append(f"nodes.jsonl:L{line_num} invalid type '{node['type']}'")
                if node["status"] not in valid_statuses:
                    errors.append(f"nodes.jsonl:L{line_num} invalid status '{node['status']}'")
                if node["trust"] not in valid_trusts:
                    errors.append(f"nodes.jsonl:L{line_num} invalid trust '{node['trust']}'")

                if not isinstance(node["evidence"], list):
                    errors.append(f"nodes.jsonl:L{line_num} evidence field must be a list")
                else:
                    for item in node["evidence"]:
                        if not isinstance(item, str):
                            errors.append(f"nodes.jsonl:L{line_num} evidence items must be strings")
                        elif not item.startswith("http") and not (self.config.root_dir / item).exists():
                            errors.append(f"nodes.jsonl:L{line_num} evidence file not found: {item}")

        return errors

    def validate_edges(self) -> List[str]:
        edges_file = self.config.memory_dir / "edges.jsonl"
        nodes_file = self.config.memory_dir / "nodes.jsonl"
        errors: List[str] = []
        if not edges_file.exists():
            return []

        # Load all valid node IDs
        valid_node_ids = set()
        if nodes_file.exists():
            with open(nodes_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        node = json.loads(line)
                        if "id" in node:
                            valid_node_ids.add(node["id"])
                    except json.JSONDecodeError:
                        continue

        valid_types = {"depends_on", "triggers", "refutes", "overrides", "configures", "secures"}

        with open(edges_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    edge = json.loads(line)
                except json.JSONDecodeError as err:
                    errors.append(f"edges.jsonl:L{line_num} is invalid JSON: {err}")
                    continue

                req = ["source", "target", "type"]
                edge_ok = True
                for field in req:
                    if field not in edge:
                        errors.append(f"edges.jsonl:L{line_num} missing required field '{field}'")
                        edge_ok = False

                if not edge_ok:
                    continue

                if edge["type"] not in valid_types:
                    errors.append(f"edges.jsonl:L{line_num} invalid type '{edge['type']}'")

                # Check for self-referential edge
                if edge["source"] == edge["target"]:
                    errors.append(f"edges.jsonl:L{line_num} self-referential edge is invalid: source and target are '{edge['source']}'")

                # Check for dangling edge
                if edge["source"] not in valid_node_ids:
                    errors.append(f"edges.jsonl:L{line_num} source node '{edge['source']}' not found in nodes.jsonl")
                if edge["target"] not in valid_node_ids:
                    errors.append(f"edges.jsonl:L{line_num} target node '{edge['target']}' not found in nodes.jsonl")

        return errors

    def validate_events(self) -> List[str]:
        events_file = self.config.memory_dir / "events.jsonl"
        errors: List[str] = []
        if not events_file.exists():
            return []

        valid_statuses = {"accepted", "rejected", "pending", "in_progress"}

        with open(events_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as err:
                    errors.append(f"events.jsonl:L{line_num} is invalid JSON: {err}")
                    continue

                req = ["timestamp", "event", "node_id", "claim", "validator", "status"]
                event_ok = True
                for field in req:
                    if field not in event:
                        errors.append(f"events.jsonl:L{line_num} missing required field '{field}'")
                        event_ok = False

                if not event_ok:
                    continue

                if event["status"] not in valid_statuses:
                    errors.append(f"events.jsonl:L{line_num} invalid status '{event['status']}'")

        return errors

    def validate_proposals_file(self, proposals_file: Optional[Path] = None) -> List[str]:
        target_file = proposals_file or self.config.proposals_file
        if not target_file.exists():
            return []

        errors = []
        valid_roles = {"admin"}
        valid_types = {"bug", "feature"}
        valid_statuses = {"active", "done", "deferred", "rejected"}
        valid_workflows = {"product", "memos"}
        valid_role_tiers = {"developer", "automated", "master_admin", "admin", "user"}

        with open(target_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    prop = json.loads(line)
                except json.JSONDecodeError as err:
                    errors.append(f"line {line_num}: invalid JSON: {err.msg}")
                    continue

                if not isinstance(prop, dict):
                    errors.append(f"line {line_num}: row must be a JSON object")
                    continue

                req = ["id", "ts", "role", "type", "status", "desc"]
                prop_ok = True
                for field in req:
                    if field not in prop:
                        errors.append(f"line {line_num}: missing required field '{field}'")
                        prop_ok = False

                if not prop_ok:
                    continue

                if not isinstance(prop["id"], int):
                    errors.append(f"line {line_num}: 'id' must be an integer")
                if not isinstance(prop["ts"], int):
                    errors.append(f"line {line_num}: 'ts' must be an integer")
                if prop["role"] not in valid_roles:
                    errors.append(f"line {line_num}: invalid role '{prop['role']}'")
                if prop["type"] not in valid_types:
                    errors.append(f"line {line_num}: invalid type '{prop['type']}'")
                if prop["status"] not in valid_statuses:
                    errors.append(f"line {line_num}: invalid status '{prop['status']}'")
                if not isinstance(prop["desc"], str) or len(prop["desc"].strip()) == 0:
                    errors.append(f"line {line_num}: 'desc' must be a non-empty string")

                if "workflow" in prop and prop["workflow"] not in valid_workflows:
                    errors.append(f"line {line_num}: invalid workflow '{prop['workflow']}'")
                if "role_tier" in prop and prop["role_tier"] not in valid_role_tiers:
                    errors.append(f"line {line_num}: invalid role_tier '{prop['role_tier']}'")
                if "priority" in prop and prop["priority"] is not None and not isinstance(prop["priority"], str):
                    errors.append(f"line {line_num}: 'priority' must be a string or null")
                if "el" in prop and not isinstance(prop["el"], str):
                    errors.append(f"line {line_num}: 'el' must be a string")
                if "src" in prop and not isinstance(prop["src"], str):
                    errors.append(f"line {line_num}: 'src' must be a string")
                if "status_updated_at" in prop and not isinstance(prop["status_updated_at"], int):
                    errors.append(f"line {line_num}: 'status_updated_at' must be an integer")
                if "status_note" in prop and not isinstance(prop["status_note"], str):
                    errors.append(f"line {line_num}: 'status_note' must be a string")

        return errors

    def validate_rows(self, lines: Iterable[str]) -> List[str]:
        errors: List[str] = []
        for line_number, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line:
                continue

            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {line_number}: invalid JSON: {exc.msg}")
                continue

            if not isinstance(row, dict):
                errors.append(f"line {line_number}: row must be a JSON object")
                continue

            missing = sorted(field for field in REQUIRED_CAPSULE_FIELDS if field not in row)
            if missing:
                errors.append(f"line {line_number}: missing fields: {', '.join(missing)}")

            for field in REQUIRED_CAPSULE_FIELDS - {"files_modified"}:
                if field in row and not self._is_non_empty_string(row[field]):
                    errors.append(f"line {line_number}: {field} must be a non-empty string")

            if "files_modified" in row and not isinstance(row["files_modified"], list):
                errors.append(f"line {line_number}: files_modified must be a list")

            workflow = row.get("workflow")
            if workflow is not None and workflow not in VALID_WORKFLOWS:
                errors.append(f"line {line_number}: workflow must be product or memos")

            step_score = row.get("step_score")
            if step_score is not None and step_score not in VALID_STEP_SCORES:
                errors.append(f"line {line_number}: step_score must be an integer from 1 to 12")

            step_name = row.get("step_name")
            if step_name is not None and step_name not in VALID_STEP_NAMES:
                errors.append(f"line {line_number}: step_name is not in the 12-step scale")

        return errors

    def validate_file(self, path: Optional[Path] = None) -> List[str]:
        target_path = path or self.config.capsules_file
        if not target_path.exists():
            return [f"{target_path}: file not found"]
        return self.validate_rows(target_path.read_text(encoding="utf-8").splitlines())
