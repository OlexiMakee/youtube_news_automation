import os
import shutil
import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

class TestCompactCapsules(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = Path(self.tmp)
        
        # Create directories
        (self.root / "agent_context").mkdir()
        (self.root / "memory").mkdir()
        (self.root / "scratch").mkdir()
        
        # Touch dummy evidence file so it exists relative to root
        (self.root / "scratch" / "test_compact_capsules.py").touch()
        
        # Create initial nodes
        self.initial_nodes = [
            {"id": "provider.ollama.cloud_only", "type": "rule", "summary": "Ollama cloud check.", "evidence": ["scratch/test_compact_capsules.py"], "status": "verified", "freshness": "2026-06-02T08:45:00Z", "trust": "verified", "related_nodes": []}
        ]
        self._write_jsonl(self.root / "memory" / "nodes.jsonl", self.initial_nodes)
        self._write_jsonl(self.root / "memory" / "edges.jsonl", [])
        self._write_jsonl(self.root / "memory" / "events.jsonl", [])

        # Patch lifecycle module globals to run in our temp root
        import scripts.memory.lifecycle as lifecycle
        self.old_memory_dir = lifecycle.MEMORY_DIR
        self.old_root = lifecycle.ROOT
        lifecycle.MEMORY_DIR = self.root / "memory"
        lifecycle.ROOT = self.root

        def cleanup_lifecycle():
            lifecycle.MEMORY_DIR = self.old_memory_dir
            lifecycle.ROOT = self.old_root
        self.addCleanup(cleanup_lifecycle)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _write_jsonl(self, path: Path, items: list):
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

    def test_no_uncompacted_capsules(self):
        # 1. Setup matching timestamps
        capsule = {
            "timestamp": "2026-06-03T12:00:00Z",
            "workflow": "product",
            "task": "Dummy",
            "lessons_learned": "Nothing."
        }
        self._write_jsonl(self.root / "agent_context" / "task_capsules.jsonl", [capsule])
        
        compacted_event = {
            "timestamp": "2026-06-03T12:01:00Z",
            "event": "memory.task_capsules.compacted",
            "node_id": "memory.task_capsules.compactor",
            "claim": "Compacted",
            "evidence": ["agent_context/task_capsules.jsonl"],
            "validator": "memos_compactor",
            "status": "accepted",
            "compacted_timestamps": ["2026-06-03T12:00:00Z"]
        }
        self._write_jsonl(self.root / "memory" / "events.jsonl", [compacted_event])

        from scripts.memory.compact_capsules import compact_capsules
        with patch("scripts.memory.compact_capsules.call_llm") as mock_call:
            res = compact_capsules(self.root)
            self.assertEqual(res, 0)
            mock_call.assert_not_called()

    @patch("scripts.memory.compact_capsules.call_llm")
    def test_compaction_success(self, mock_call):
        # 1. Setup uncompacted capsule
        capsule = {
            "timestamp": "2026-06-03T12:00:00Z",
            "workflow": "product",
            "task": "Add rule widget alignment",
            "files_modified": ["scratch/test_compact_capsules.py"],
            "lessons_learned": "Avoid nesting absolutely positioned control elements."
        }
        self._write_jsonl(self.root / "agent_context" / "task_capsules.jsonl", [capsule])

        # 2. Mock LLM response return
        llm_response = {
            "nodes": [
                {
                    "id": "ui.widget_alignment",
                    "type": "rule",
                    "summary": "Avoid nesting absolute positioning.",
                    "evidence": ["scratch/test_compact_capsules.py"]
                }
            ],
            "edges": [
                {
                    "source": "provider.ollama.cloud_only",
                    "target": "ui.widget_alignment",
                    "type": "depends_on"
                }
            ]
        }
        mock_call.return_value = json.dumps(llm_response)

        from scripts.memory.compact_capsules import compact_capsules
        
        # Mock subprocess run to avoid executing snapshot generation on fake root
        with patch("subprocess.run") as mock_run:
            res = compact_capsules(self.root)
            self.assertEqual(res, 0)
            
        # 3. Verify nodes
        nodes = self._load_jsonl(self.root / "memory" / "nodes.jsonl")
        self.assertEqual(len(nodes), 2)
        new_node = next(n for n in nodes if n["id"] == "ui.widget_alignment")
        self.assertEqual(new_node["status"], "verified")
        self.assertEqual(new_node["trust"], "verified")
        self.assertIn("scratch/test_compact_capsules.py", new_node["evidence"])

        # 4. Verify edges
        edges = self._load_jsonl(self.root / "memory" / "edges.jsonl")
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]["source"], "provider.ollama.cloud_only")
        self.assertEqual(edges[0]["target"], "ui.widget_alignment")
        self.assertEqual(edges[0]["type"], "depends_on")

        # 5. Verify compaction event
        events = self._load_jsonl(self.root / "memory" / "events.jsonl")
        comp_event = next(e for e in events if e["event"] == "memory.task_capsules.compacted")
        self.assertEqual(comp_event["compacted_timestamps"], ["2026-06-03T12:00:00Z"])

if __name__ == "__main__":
    unittest.main()
