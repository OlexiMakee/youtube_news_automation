import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Any, Optional

from app.services.memory_os.config import MemosConfig
from app.services.llm_clients import LLMClientFactory

SYSTEM_PROMPT = """You are the Memory OS Knowledge Compactor.
Your job is to analyze developer task logs (task capsules) and existing memory nodes, then extract new permanent knowledge nodes (rules, facts, configurations, or policies) and relationships (edges).

Guidelines for Nodes:
1. Extract only durable, architectural, or structural findings. Avoid documenting temporary issues.
2. Group lessons under namespace IDs, e.g., 'provider.openrouter.free_only', 'solid.srp.agent_service', etc.
3. Every node must have:
   - id: unique string namespace id (must match standard namespacing, lowercase, dot-separated).
   - type: one of "rule", "fact", "variable", "connector", "config", "policy".
   - summary: concise summary of the rule/fact/config/policy.
   - evidence: list of file paths that were modified or verified for this node.
4. If a node already exists (matches one of the provided existing node IDs), do not propose a new node under that ID unless you are revising its summary, in which case you must also output an "overrides" edge.

Guidelines for Edges:
1. Create edges between nodes to represent relationships.
2. Every edge must have:
   - source: node ID.
   - target: node ID.
   - type: one of "depends_on", "triggers", "refutes", "overrides", "configures", "secures".

Your output must be ONLY a raw JSON block with the following schema:
{
  "nodes": [
    {
      "id": "node.id.string",
      "type": "rule|fact|variable|connector|config|policy",
      "summary": "Concise lesson details.",
      "evidence": ["relative/file/path.py"]
    }
  ],
  "edges": [
    {
      "source": "source_node_id",
      "target": "target_node_id",
      "type": "depends_on|triggers|refutes|overrides|configures|secures"
    }
  ]
}
Do not write markdown wraps like ```json or any other text before/after. Just the JSON object.
"""

class MemoryCompactor:
    """Compacts task capsules into permanent Memory OS nodes using LLMs."""

    def __init__(self, config: Optional[MemosConfig] = None):
        self.config = config or MemosConfig()

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

    def _append_jsonl(self, path: Path, item: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(item) + "\n")

    def _clean_llm_json(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            first_nl = text.find("\n")
            if first_nl != -1:
                text = text[first_nl:].strip()
            if text.endswith("```"):
                text = text[:-3].strip()
        return text

    def _call_llm(self, user_message: str, provider_override: Optional[str] = None, model_override: Optional[str] = None) -> str:
        providers_to_try = [provider_override] if provider_override else ["gemini", "openrouter", "openai"]

        for provider in providers_to_try:
            api_key, base_url, model = LLMClientFactory.get_provider_config(provider, model_override)
            if not api_key or not base_url:
                continue

            try:
                client = LLMClientFactory.create_client(provider)
                chunks = []
                for chunk in client.stream_chat(
                    api_key=api_key,
                    base_url=base_url,
                    model=model,
                    user_message=user_message,
                    system_prompt=SYSTEM_PROMPT
                ):
                    chunks.append(chunk)
                return "".join(chunks)
            except Exception as exc:
                print(f"Warning: failed to run compaction with provider {provider}: {exc}", file=sys.stderr)
                continue

        raise RuntimeError("No LLM provider configured with valid API keys in environment.")

    def compact_capsules(self, provider: Optional[str] = None, model: Optional[str] = None) -> int:
        task_capsules_path = self.config.capsules_file
        events_path = self.config.memory_dir / "events.jsonl"
        nodes_path = self.config.memory_dir / "nodes.jsonl"
        edges_path = self.config.memory_dir / "edges.jsonl"

        if not task_capsules_path.exists():
            print(f"Error: task_capsules.jsonl not found at {task_capsules_path}", file=sys.stderr)
            return 1

        # 1. Load all task capsules
        capsules = self._load_jsonl(task_capsules_path)

        # 2. Get compacted timestamps from events
        compacted_timestamps = set()
        events = self._load_jsonl(events_path)
        for ev in events:
            if ev.get("event") == "memory.task_capsules.compacted":
                timestamps = ev.get("compacted_timestamps", [])
                for ts in timestamps:
                    compacted_timestamps.add(ts)

        # 3. Identify uncompacted capsules
        uncompacted = [cap for cap in capsules if cap.get("timestamp") not in compacted_timestamps]

        if not uncompacted:
            print("No uncompacted capsules found.")
            return 0

        print(f"Found {len(uncompacted)} uncompacted task capsules. Proceeding with compaction...")

        # Process in batches of 10
        batch_size = 10
        total_batches = (len(uncompacted) + batch_size - 1) // batch_size

        node_append_count = 0
        edge_append_count = 0

        for i in range(0, len(uncompacted), batch_size):
            batch = uncompacted[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} capsules)...")

            # Read existing nodes for reference
            existing_nodes = self._load_jsonl(nodes_path)
            existing_node_info = [{"id": n["id"], "type": n["type"], "summary": n["summary"]} for n in existing_nodes]

            # Build user message for this batch
            user_msg_data = {
                "existing_nodes": existing_node_info,
                "new_tasks": [
                    {
                        "timestamp": cap.get("timestamp"),
                        "task": cap.get("task"),
                        "workflow": cap.get("workflow"),
                        "files_modified": cap.get("files_modified", []),
                        "hurdles_regression": cap.get("hurdles_regression"),
                        "resolution": cap.get("resolution"),
                        "lessons_learned": cap.get("lessons_learned")
                    }
                    for cap in batch
                ]
            }

            user_message = json.dumps(user_msg_data, indent=2, ensure_ascii=False)

            # Call LLM
            try:
                response_text = self._call_llm(user_message, provider, model)
            except Exception as exc:
                print(f"Error during LLM call in batch {batch_num}: {exc}", file=sys.stderr)
                return 1

            # Parse and clean output
            json_text = self._clean_llm_json(response_text)
            try:
                payload = json.loads(json_text)
            except json.JSONDecodeError as exc:
                print(f"Error: LLM returned invalid JSON in batch {batch_num}: {exc}\nRaw Response:\n{response_text}", file=sys.stderr)
                return 1

            proposed_nodes = []
            proposed_edges = []

            if isinstance(payload, list) and len(payload) == 1 and isinstance(payload[0], dict) and ("nodes" in payload[0] or "edges" in payload[0]):
                payload = payload[0]

            if isinstance(payload, dict):
                proposed_nodes = payload.get("nodes", [])
                proposed_edges = payload.get("edges", [])
            elif isinstance(payload, list):
                for item in payload:
                    if isinstance(item, dict):
                        if "source" in item and "target" in item:
                            proposed_edges.append(item)
                        else:
                            proposed_nodes.append(item)

            existing_node_ids = {n["id"] for n in existing_nodes}
            new_node_ids = set()

            valid_node_types = {"rule", "fact", "variable", "connector", "config", "policy"}

            for node in proposed_nodes:
                node_id = node.get("id")
                node_type = node.get("type")
                summary = node.get("summary")
                evidence = node.get("evidence", [])

                if not node_id or not node_type or not summary:
                    print(f"Skipping invalid proposed node: {node}")
                    continue

                if node_type not in valid_node_types:
                    print(f"Skipping proposed node '{node_id}' with invalid type '{node_type}'")
                    continue

                if node_id in existing_node_ids:
                    print(f"Node '{node_id}' already exists in nodes.jsonl. Skipping proposal.")
                    continue

                # Clean evidence: keep only existing files, and always add the capsules file
                cleaned_evidence = []
                for file_path in evidence:
                    if (self.config.root_dir / file_path).exists() and file_path not in cleaned_evidence:
                        cleaned_evidence.append(file_path)
                
                # Check capsules relative path to root_dir
                try:
                    rel_capsules = str(self.config.capsules_file.relative_to(self.config.root_dir))
                except ValueError:
                    rel_capsules = "agent_context/task_capsules.jsonl"
                
                if rel_capsules not in cleaned_evidence:
                    cleaned_evidence.append(rel_capsules)

                new_node = {
                    "id": node_id,
                    "type": node_type,
                    "summary": summary,
                    "evidence": cleaned_evidence,
                    "status": "draft",
                    "freshness": datetime.now().isoformat(timespec="seconds"),
                    "trust": "unverified",
                    "related_nodes": []
                }

                self._append_jsonl(nodes_path, new_node)
                new_node_ids.add(node_id)
                node_append_count += 1
                print(f"Proposed node '{node_id}' added as draft.")

                # Log node proposed event
                new_event = {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "event": "memory.node.proposed",
                    "node_id": node_id,
                    "claim": f"Propose rule/fact: {summary}",
                    "evidence": cleaned_evidence,
                    "validator": "memos_compactor",
                    "status": "pending"
                }
                self._append_jsonl(events_path, new_event)

            # Validate and append edges
            valid_edge_types = {"depends_on", "triggers", "refutes", "overrides", "configures", "secures"}

            for edge in proposed_edges:
                source = edge.get("source")
                target = edge.get("target")
                edge_type = edge.get("type")

                if not source or not target or not edge_type:
                    print(f"Skipping invalid proposed edge: {edge}")
                    continue

                if edge_type not in valid_edge_types:
                    print(f"Skipping proposed edge source='{source}' target='{target}' with invalid type '{edge_type}'")
                    continue

                # Source/target must exist either in existing nodes or new proposed nodes
                all_ids = existing_node_ids.union(new_node_ids)
                if source not in all_ids or target not in all_ids:
                    print(f"Skipping edge {source} -> {target} because source or target node is missing.")
                    continue

                new_edge = {
                    "source": source,
                    "target": target,
                    "type": edge_type
                }
                self._append_jsonl(edges_path, new_edge)
                edge_append_count += 1
                print(f"Appended edge: {source} -> {target} ({edge_type})")

            # Log compaction completion event for this batch
            batch_timestamps = [cap.get("timestamp") for cap in batch]
            
            try:
                rel_capsules = str(self.config.capsules_file.relative_to(self.config.root_dir))
            except ValueError:
                rel_capsules = "agent_context/task_capsules.jsonl"
                
            compaction_event = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "event": "memory.task_capsules.compacted",
                "node_id": "memory.task_capsules.compactor",
                "claim": f"Compacted batch {batch_num}/{total_batches} ({len(batch)} capsules).",
                "evidence": [rel_capsules],
                "validator": "memos_compactor",
                "status": "accepted",
                "compacted_timestamps": batch_timestamps
            }
            self._append_jsonl(events_path, compaction_event)

        print(f"Compaction completed. Proposed {node_append_count} nodes, appended {edge_append_count} edges.")

        # Trigger lifecycle transitions and manifest compilation via classes
        from app.services.memory_os.lifecycle import LifecycleManager
        
        print("Running lifecycle transition validations...")
        lifecycle = LifecycleManager(self.config)
        lifecycle.transition(validator="memos_compactor")
        lifecycle.manifest()

        # Rebuild snapshot
        print("Updating memory snapshot...")
        try:
            import subprocess
            # Rebuild snapshot relative to config
            compact_memory_script = self.config.root_dir / "scripts" / "compact_memory.py"
            if compact_memory_script.exists():
                subprocess.run([sys.executable, str(compact_memory_script), "--write"], check=True)
        except Exception as exc:
            print(f"Warning: snapshot rebuild failed: {exc}", file=sys.stderr)

        return 0
