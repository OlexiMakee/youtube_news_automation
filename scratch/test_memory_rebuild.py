import os
import sys
import json
import shutil
import tempfile
import unittest
from pathlib import Path

# Add root dir to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.services.memory_os.config import MemosConfig
from app.services.memory_os.lifecycle import LifecycleManager
from app.services.memory_os.validator import MemoryValidator
from app.services.memory_os.compactor import MemoryCompactor


class TestMemoryRebuild(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root_path = Path(self.test_dir)
        self.memory_dir = self.root_path / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup config
        self.config = MemosConfig()
        self.config.root_dir = self.root_path
        self.config.data["memory_dir"] = "memory"
        self.config.data["capsules_file"] = "agent_context/task_capsules.jsonl"
        self.config.data["snapshot_file"] = "agent_context/memory_snapshot.json"
        
        # Ensure agent_context exists
        (self.root_path / "agent_context").mkdir(parents=True, exist_ok=True)

        self.nodes_file = self.memory_dir / "nodes.jsonl"
        self.edges_file = self.memory_dir / "edges.jsonl"
        self.events_file = self.memory_dir / "events.jsonl"
        self.capsules_file = self.root_path / "agent_context" / "task_capsules.jsonl"

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _write_jsonl(self, path: Path, items: list) -> None:
        with open(path, "w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item) + "\n")

    def _load_jsonl(self, path: Path) -> list:
        if not path.exists():
            return []
        items = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    items.append(json.loads(line))
        return items

    def test_lifecycle_transition_stale_to_verified(self):
        # 1. Propose a node without creating evidence file first
        lm = LifecycleManager(self.config)
        lm.propose(
            node_id="test.rebuild_rule",
            node_type="rule",
            summary="A rule that will go stale first",
            evidence="missing_evidence.txt"
        )
        
        # 2. Transition it - it should go stale due to missing evidence
        lm.transition()
        nodes = self._load_jsonl(self.nodes_file)
        self.assertEqual(nodes[0]["status"], "stale")
        
        # 3. Create the evidence file
        (self.root_path / "missing_evidence.txt").touch()
        
        # 4. Transition it again - it should now go verified
        lm.transition()
        nodes = self._load_jsonl(self.nodes_file)
        self.assertEqual(nodes[0]["status"], "verified")
        self.assertEqual(nodes[0]["trust"], "verified")

    def test_lifecycle_prune_self_referential_edge(self):
        # Create active nodes
        node_active = {
            "id": "node.active",
            "type": "rule",
            "summary": "Active",
            "evidence": [],
            "status": "verified",
            "freshness": "2026-06-02T08:45:00Z",
            "trust": "verified",
            "related_nodes": []
        }
        self._write_jsonl(self.nodes_file, [node_active])
        
        # Create valid and self-referential edges
        edges = [
            {"source": "node.active", "target": "node.active", "type": "overrides"}
        ]
        self._write_jsonl(self.edges_file, edges)
        
        # Prune
        lm = LifecycleManager(self.config)
        lm.prune()
        
        # The self-referential edge should be completely removed
        pruned_edges = self._load_jsonl(self.edges_file)
        self.assertEqual(len(pruned_edges), 0)

    def test_validator_detects_self_referential_and_dangling_edges(self):
        # Create active node
        node = {
            "id": "node.valid",
            "type": "rule",
            "summary": "Valid node",
            "evidence": [],
            "status": "verified",
            "freshness": "2026-06-02T08:45:00Z",
            "trust": "verified",
            "related_nodes": []
        }
        self._write_jsonl(self.nodes_file, [node])
        
        # Create invalid edges (one dangling, one self-referential)
        edges = [
            {"source": "node.valid", "target": "node.dangling", "type": "depends_on"},
            {"source": "node.valid", "target": "node.valid", "type": "depends_on"}
        ]
        self._write_jsonl(self.edges_file, edges)
        
        validator = MemoryValidator(self.config)
        errors = validator.validate_edges()
        
        self.assertTrue(any("self-referential edge is invalid" in err for err in errors))
        self.assertTrue(any("target node 'node.dangling' not found" in err for err in errors))

    def test_compactor_archiving_logic(self):
        # Create mock capsules
        capsules = [
            {"timestamp": "2026-06-03T10:00:00Z", "task": "Task 1", "files_modified": [], "hurdles_regression": "", "resolution": "", "lessons_learned": ""},
            {"timestamp": "2026-06-03T11:00:00Z", "task": "Task 2", "files_modified": [], "hurdles_regression": "", "resolution": "", "lessons_learned": ""},
            {"timestamp": "2026-06-03T12:00:00Z", "task": "Task 3", "files_modified": [], "hurdles_regression": "", "resolution": "", "lessons_learned": ""}
        ]
        self._write_jsonl(self.capsules_file, capsules)
        
        # Create events marking Task 1 and Task 2 as compacted
        events = [
            {"timestamp": "2026-06-03T12:05:00Z", "event": "memory.task_capsules.compacted", "node_id": "memory.task_capsules.compactor", "claim": "", "evidence": [], "status": "accepted", "compacted_timestamps": ["2026-06-03T10:00:00Z", "2026-06-03T11:00:00Z"]}
        ]
        self._write_jsonl(self.events_file, events)
        
        compactor = MemoryCompactor(self.config)
        # Run archiving, keeping only 1 compacted capsule in the active file
        compactor.archive_compacted_capsules(keep_recent=1)
        
        # Verify active capsules: Task 3 (uncompacted) + Task 2 (most recent compacted)
        active_capsules = self._load_jsonl(self.capsules_file)
        self.assertEqual(len(active_capsules), 2)
        active_timestamps = {cap["timestamp"] for cap in active_capsules}
        self.assertIn("2026-06-03T12:00:00Z", active_timestamps)  # Uncompacted
        self.assertIn("2026-06-03T11:00:00Z", active_timestamps)  # Retained compacted (Task 2 is more recent than Task 1)
        self.assertNotIn("2026-06-03T10:00:00Z", active_timestamps)
        
        # Verify archived capsules: contains Task 1 and Task 2
        archive_path = self.root_path / "agent_context" / "archived_task_capsules.jsonl"
        self.assertTrue(archive_path.exists())
        archived_capsules = self._load_jsonl(archive_path)
        self.assertEqual(len(archived_capsules), 2)
        archived_timestamps = {cap["timestamp"] for cap in archived_capsules}
        self.assertIn("2026-06-03T10:00:00Z", archived_timestamps)
        self.assertIn("2026-06-03T11:00:00Z", archived_timestamps)


if __name__ == "__main__":
    unittest.main()
