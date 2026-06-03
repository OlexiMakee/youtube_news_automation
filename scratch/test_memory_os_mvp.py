import os
import sys
import json
import shutil
import tempfile
import unittest
import yaml
from pathlib import Path
from unittest.mock import patch
from app.services.memory_os import load_toml_file

# Add root dir to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

ROOT = Path(root_dir)

from scripts.memory.validate_memory import validate_nodes, validate_edges, validate_events
import scripts.memory.validate_memory as validate_mod

from scripts.memory.quantize_task import calculate_score, calculate_step_score, resolve_profile
import scripts.memory.search_memory as search_mod

class TestMemoryOSMvp(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.memory_dir = Path(self.test_dir) / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # Patch validate_memory and search_memory paths
        self.orig_root = validate_mod.ROOT
        self.orig_mem = validate_mod.MEMORY_DIR
        
        validate_mod.ROOT = Path(self.test_dir)
        validate_mod.MEMORY_DIR = self.memory_dir
        
        self.orig_search_root = search_mod.ROOT
        self.orig_search_mem = search_mod.MEMORY_DIR
        
        search_mod.ROOT = Path(self.test_dir)
        search_mod.MEMORY_DIR = self.memory_dir

    def tearDown(self):
        validate_mod.ROOT = self.orig_root
        validate_mod.MEMORY_DIR = self.orig_mem
        search_mod.ROOT = self.orig_search_root
        search_mod.MEMORY_DIR = self.orig_search_mem
        shutil.rmtree(self.test_dir)

    def test_validate_nodes_success(self):
        # Create a valid evidence file
        evidence_file = Path(self.test_dir) / "test_file.txt"
        evidence_file.touch()
        
        nodes_file = self.memory_dir / "nodes.jsonl"
        node_data = {
            "id": "test.rule",
            "type": "rule",
            "summary": "This is a test rule.",
            "evidence": ["test_file.txt"],
            "status": "verified",
            "freshness": "2026-06-02T08:00:00Z",
            "trust": "verified",
            "related_nodes": []
        }
        with open(nodes_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(node_data) + "\n")
            
        self.assertTrue(validate_nodes())

    def test_validate_nodes_failures(self):
        nodes_file = self.memory_dir / "nodes.jsonl"
        
        # Missing field
        node_data = {
            "id": "test.rule",
            "type": "rule",
            "summary": "Missing fields"
        }
        with open(nodes_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(node_data) + "\n")
        self.assertFalse(validate_nodes())

        # Invalid enum type
        node_data = {
            "id": "test.rule",
            "type": "invalid_type",
            "summary": "Invalid type enum",
            "evidence": [],
            "status": "verified",
            "freshness": "2026-06-02T08:00:00Z",
            "trust": "verified"
        }
        with open(nodes_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(node_data) + "\n")
        self.assertFalse(validate_nodes())

        # Missing evidence file
        node_data = {
            "id": "test.rule",
            "type": "rule",
            "summary": "Missing evidence file",
            "evidence": ["nonexistent_file.txt"],
            "status": "verified",
            "freshness": "2026-06-02T08:00:00Z",
            "trust": "verified"
        }
        with open(nodes_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(node_data) + "\n")
        self.assertFalse(validate_nodes())

    def test_validate_multiple_nodes_partial_failure(self):
        # Create a valid evidence file
        evidence_file = Path(self.test_dir) / "test_file.txt"
        evidence_file.touch()
        
        nodes_file = self.memory_dir / "nodes.jsonl"
        # Node 1 is invalid (missing field 'status')
        node_1 = {
            "id": "test.rule1",
            "type": "rule",
            "summary": "This is a test rule 1.",
            "evidence": ["test_file.txt"],
            "freshness": "2026-06-02T08:00:00Z",
            "trust": "verified"
        }
        # Node 2 is perfectly valid
        node_2 = {
            "id": "test.rule2",
            "type": "rule",
            "summary": "This is a test rule 2.",
            "evidence": ["test_file.txt"],
            "status": "verified",
            "freshness": "2026-06-02T08:00:00Z",
            "trust": "verified",
            "related_nodes": []
        }
        
        with open(nodes_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(node_1) + "\n")
            f.write(json.dumps(node_2) + "\n")
            
        # Overall validation should return False (since node_1 is invalid)
        # But node_2 should still be processed without crashing/skipping.
        with patch('scripts.memory.validate_memory.log_error') as mock_log:
            self.assertFalse(validate_nodes())
            # Check that missing field status on L1 was reported
            mock_log.assert_any_call("nodes.jsonl:L1 missing required field 'status'")


    def test_validate_edges(self):
        nodes_file = self.memory_dir / "nodes.jsonl"
        edges_file = self.memory_dir / "edges.jsonl"
        
        # Write valid mock nodes first
        with open(nodes_file, "w", encoding="utf-8") as f:
            f.write(json.dumps({"id": "node.a", "type": "rule", "summary": "A", "evidence": [], "status": "verified", "freshness": "2026-06-02", "trust": "verified", "related_nodes": []}) + "\n")
            f.write(json.dumps({"id": "node.b", "type": "rule", "summary": "B", "evidence": [], "status": "verified", "freshness": "2026-06-02", "trust": "verified", "related_nodes": []}) + "\n")

        # Valid edge
        edge_data = {
            "source": "node.a",
            "target": "node.b",
            "type": "depends_on"
        }
        with open(edges_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(edge_data) + "\n")
        self.assertTrue(validate_edges())
        
        # Invalid type
        edge_data = {
            "source": "node.a",
            "target": "node.b",
            "type": "invalid_relation"
        }
        with open(edges_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(edge_data) + "\n")
        self.assertFalse(validate_edges())

    def test_validate_events(self):
        events_file = self.memory_dir / "events.jsonl"
        
        # Valid event
        event_data = {
            "timestamp": "2026-06-02T08:00:00Z",
            "event": "memory.update.proposed",
            "node_id": "node.a",
            "claim": "Test claim",
            "validator": "static_indexer",
            "status": "accepted"
        }
        with open(events_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(event_data) + "\n")
        self.assertTrue(validate_events())

        # Invalid status
        event_data["status"] = "invalid_status"
        with open(events_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(event_data) + "\n")
        self.assertFalse(validate_events())

    def test_task_quantizer_scoring(self):
        # Database/schema related task
        score_db = calculate_score("run schema migration for governance", risk=0.5)
        self.assertTrue(score_db >= 40)
        
        # Simple task
        score_simple = calculate_score("fix typo in index.html", risk=0.0)
        self.assertTrue(score_simple <= 15)

        step_simple = calculate_step_score("fix typo in index.html", risk=0.0)
        self.assertEqual(step_simple, 1)

        step_architecture = calculate_step_score("architecture refactor with schema migration", risk=0.8)
        self.assertGreaterEqual(step_architecture, 11)

    def test_task_quantizer_profile(self):
        p_nano = resolve_profile(1)
        self.assertEqual(p_nano["profile"], "nano")
        self.assertEqual(p_nano["step_score"], 1)
        self.assertEqual(p_nano["step_name"], "nano")
        self.assertFalse(p_nano["escalate"])

        p_pretty_little = resolve_profile(5)
        self.assertEqual(p_pretty_little["profile"], "pretty little")
        self.assertEqual(p_pretty_little["step_score"], 5)
        self.assertEqual(p_pretty_little["step_name"], "pretty little")
        self.assertFalse(p_pretty_little["escalate"])

        p_giant = resolve_profile(12)
        self.assertEqual(p_giant["profile"], "giant")
        self.assertEqual(p_giant["step_score"], 12)
        self.assertTrue(p_giant["escalate"])

    def test_task_quantizer_legacy_score_profile(self):
        p_micro = resolve_profile(13)
        self.assertEqual(p_micro["profile"], "micro")
        self.assertEqual(p_micro["step_score"], 2)
        self.assertEqual(p_micro["step_name"], "micro")
        self.assertEqual(p_micro["legacy_score"], 13)
        self.assertFalse(p_micro["escalate"])

        p_large = resolve_profile(85)
        self.assertEqual(p_large["profile"], "large")
        self.assertEqual(p_large["step_score"], 11)
        self.assertEqual(p_large["legacy_score"], 85)
        self.assertTrue(p_large["escalate"])

    def test_search_memory_lexical(self):
        nodes_file = self.memory_dir / "nodes.jsonl"
        node1 = {
            "id": "openrouter.free",
            "type": "rule",
            "summary": "Must use free OpenRouter endpoints.",
            "evidence": ["AGENTS.md"],
            "status": "verified",
            "freshness": "2026-06-02T08:00:00Z",
            "trust": "verified",
            "related_nodes": []
        }
        node2 = {
            "id": "ollama.cloud",
            "type": "rule",
            "summary": "Ollama local endpoints are forbidden.",
            "evidence": ["AGENTS.md"],
            "status": "verified",
            "freshness": "2026-06-02T08:00:00Z",
            "trust": "verified",
            "related_nodes": []
        }
        with open(nodes_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(node1) + "\n" + json.dumps(node2) + "\n")
            
        results = search_mod.search_memory("openrouter")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "openrouter.free")

    def test_search_memory_graph_traversal(self):
        nodes_file = self.memory_dir / "nodes.jsonl"
        edges_file = self.memory_dir / "edges.jsonl"
        
        node_a = {
            "id": "node.a",
            "type": "rule",
            "summary": "Start node",
            "evidence": [],
            "status": "verified",
            "freshness": "2026-06-02",
            "trust": "verified",
            "related_nodes": ["node.b"]
        }
        node_b = {
            "id": "node.b",
            "type": "rule",
            "summary": "Connected node definitional",
            "evidence": [],
            "status": "verified",
            "freshness": "2026-06-02",
            "trust": "verified",
            "related_nodes": []
        }
        node_c = {
            "id": "node.c",
            "type": "rule",
            "summary": "Connected node edge",
            "evidence": [],
            "status": "verified",
            "freshness": "2026-06-02",
            "trust": "verified",
            "related_nodes": []
        }
        with open(nodes_file, "w", encoding="utf-8") as f:
            f.write("\n".join(json.dumps(n) for n in [node_a, node_b, node_c]) + "\n")
            
        # Edge link node.b -> node.c
        edge = {"source": "node.b", "target": "node.c", "type": "depends_on"}
        with open(edges_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(edge) + "\n")
            
        # Depth 1 traversal from node.a should find node.a and node.b
        results_d1 = search_mod.search_memory("start", depth=1)
        ids_d1 = {r["id"] for r in results_d1}
        self.assertIn("node.a", ids_d1)
        self.assertIn("node.b", ids_d1)
        self.assertNotIn("node.c", ids_d1)

        # Depth 2 traversal from node.a should find node.a, node.b, and node.c
        results_d2 = search_mod.search_memory("start", depth=2)
        ids_d2 = {r["id"] for r in results_d2}
        self.assertIn("node.a", ids_d2)
        self.assertIn("node.b", ids_d2)
        self.assertIn("node.c", ids_d2)

    def test_toml_workflows_parsing(self):
        # Read the real workflow definitions to ensure TOML parser can parse them successfully
        workflow_paths = [
            ROOT / "workflows" / "chat.nano.toml",
            ROOT / "workflows" / "code.small.toml",
            ROOT / "workflows" / "architecture.giant.toml"
        ]
        for path in workflow_paths:
            self.assertTrue(path.exists())
            data = load_toml_file(str(path))
            self.assertIsNotNone(data)
            self.assertIn("id", data)
            self.assertIn("level_min", data)
            self.assertIn("level_max", data)
            self.assertIn("step_min", data)
            self.assertIn("step_max", data)
            self.assertGreaterEqual(data["step_min"], 1)
            self.assertLessEqual(data["step_max"], 12)

if __name__ == "__main__":
    unittest.main()
