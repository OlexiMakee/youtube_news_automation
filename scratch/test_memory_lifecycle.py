import os
import sys
import json
import shutil
import tempfile
import unittest
import argparse
from pathlib import Path

# Add root dir to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import scripts.memory.lifecycle as lifecycle_mod

class TestMemoryLifecycle(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.memory_dir = Path(self.test_dir) / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # Patch lifecycle paths
        self.orig_root = lifecycle_mod.ROOT
        self.orig_mem = lifecycle_mod.MEMORY_DIR
        
        lifecycle_mod.ROOT = Path(self.test_dir)
        lifecycle_mod.MEMORY_DIR = self.memory_dir

    def tearDown(self):
        lifecycle_mod.ROOT = self.orig_root
        lifecycle_mod.MEMORY_DIR = self.orig_mem
        shutil.rmtree(self.test_dir)

    def test_propose_command(self):
        # Propose node
        args = argparse.Namespace(
            id="test.rule",
            type="rule",
            summary="A proposed test rule",
            evidence="evidence_file.txt",
            related_nodes=None,
            validator="test_validator"
        )
        res = lifecycle_mod.cmd_propose(args)
        self.assertEqual(res, 0)
        
        # Check files
        nodes = lifecycle_mod.load_jsonl(self.memory_dir / "nodes.jsonl")
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["id"], "test.rule")
        self.assertEqual(nodes[0]["status"], "draft")
        self.assertEqual(nodes[0]["trust"], "unverified")
        
        events = lifecycle_mod.load_jsonl(self.memory_dir / "events.jsonl")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event"], "memory.node.proposed")
        self.assertEqual(events[0]["status"], "pending")

    def test_transition_success_with_evidence(self):
        # Create evidence file
        evidence_file = Path(self.test_dir) / "test_evidence.txt"
        evidence_file.touch()
        
        # Propose node
        args = argparse.Namespace(
            id="test.rule",
            type="rule",
            summary="Test rule with evidence",
            evidence="test_evidence.txt",
            related_nodes=None,
            validator="test_validator"
        )
        lifecycle_mod.cmd_propose(args)
        
        # Transition
        args_t = argparse.Namespace(validator="test_validator")
        res = lifecycle_mod.cmd_transition(args_t)
        self.assertEqual(res, 0)
        
        # Check transitions
        nodes = lifecycle_mod.load_jsonl(self.memory_dir / "nodes.jsonl")
        self.assertEqual(nodes[0]["status"], "verified")
        self.assertEqual(nodes[0]["trust"], "verified")
        
        events = lifecycle_mod.load_jsonl(self.memory_dir / "events.jsonl")
        # Proposed event should be accepted, and a verified event added
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["status"], "accepted")  # proposed event accepted
        self.assertEqual(events[1]["event"], "memory.node.verified")

    def test_transition_reject_missing_evidence(self):
        # Propose node (no evidence file created in test dir)
        args = argparse.Namespace(
            id="test.rule",
            type="rule",
            summary="Test rule missing evidence",
            evidence="missing_evidence.txt",
            related_nodes=None,
            validator="test_validator"
        )
        lifecycle_mod.cmd_propose(args)
        
        # Transition
        args_t = argparse.Namespace(validator="test_validator")
        res = lifecycle_mod.cmd_transition(args_t)
        self.assertEqual(res, 0)
        
        # Check node status is set to stale (rejected)
        nodes = lifecycle_mod.load_jsonl(self.memory_dir / "nodes.jsonl")
        self.assertEqual(nodes[0]["status"], "stale")
        
        events = lifecycle_mod.load_jsonl(self.memory_dir / "events.jsonl")
        self.assertEqual(events[0]["status"], "rejected")

    def test_transition_overrides_relationship(self):
        # Create evidence files
        (Path(self.test_dir) / "file_a.txt").touch()
        (Path(self.test_dir) / "file_b.txt").touch()
        
        # Node A: Old verified rule
        node_a = {
            "id": "rule.old",
            "type": "rule",
            "summary": "Old summary",
            "evidence": ["file_a.txt"],
            "status": "verified",
            "freshness": "2026-06-02",
            "trust": "verified",
            "related_nodes": []
        }
        lifecycle_mod.append_jsonl(self.memory_dir / "nodes.jsonl", node_a)
        
        # Propose Node B: New overriding rule
        args = argparse.Namespace(
            id="rule.new",
            type="rule",
            summary="New summary overriding old",
            evidence="file_b.txt",
            related_nodes=None,
            validator="test_validator"
        )
        lifecycle_mod.cmd_propose(args)
        
        # Add override edge
        edge = {
            "source": "rule.new",
            "target": "rule.old",
            "type": "overrides"
        }
        lifecycle_mod.append_jsonl(self.memory_dir / "edges.jsonl", edge)
        
        # Transition
        args_t = argparse.Namespace(validator="test_validator")
        lifecycle_mod.cmd_transition(args_t)
        
        # Verify rule.new is verified, and rule.old is superseded
        nodes = lifecycle_mod.load_jsonl(self.memory_dir / "nodes.jsonl")
        nodes_by_id = {n["id"]: n for n in nodes}
        self.assertEqual(nodes_by_id["rule.new"]["status"], "verified")
        self.assertEqual(nodes_by_id["rule.old"]["status"], "superseded")

    def test_manifest_generation(self):
        # Add some items
        node = {
            "id": "node.a",
            "type": "fact",
            "summary": "Fact summary",
            "evidence": [],
            "status": "verified",
            "freshness": "2026-06-02",
            "trust": "verified",
            "related_nodes": []
        }
        lifecycle_mod.append_jsonl(self.memory_dir / "nodes.jsonl", node)
        
        edge = {"source": "node.a", "target": "node.b", "type": "depends_on"}
        lifecycle_mod.append_jsonl(self.memory_dir / "edges.jsonl", edge)
        
        # Generate manifest
        res = lifecycle_mod.cmd_manifest(None)
        self.assertEqual(res, 0)
        
        # Check manifest file
        manifest_path = self.memory_dir / "manifest.json"
        self.assertTrue(manifest_path.exists())
        with open(manifest_path, "r") as f:
            data = json.load(f)
        self.assertEqual(data["counts"]["nodes"], 1)
        self.assertEqual(data["counts"]["edges"], 1)
        self.assertIn("nodes.jsonl", data["checksums"])

    def test_prune_superseded_and_dangling(self):
        # Create verified node
        node_active = {
            "id": "node.active",
            "type": "rule",
            "summary": "Active",
            "evidence": [],
            "status": "verified",
            "freshness": "2026-06-02",
            "trust": "verified",
            "related_nodes": []
        }
        # Create superseded node
        node_stale = {
            "id": "node.stale",
            "type": "rule",
            "summary": "Stale",
            "evidence": [],
            "status": "superseded",
            "freshness": "2026-06-02",
            "trust": "verified",
            "related_nodes": []
        }
        # Create second active node
        node_active2 = {
            "id": "node.active2",
            "type": "rule",
            "summary": "Active 2",
            "evidence": [],
            "status": "verified",
            "freshness": "2026-06-02",
            "trust": "verified",
            "related_nodes": []
        }
        lifecycle_mod.append_jsonl(self.memory_dir / "nodes.jsonl", node_active)
        lifecycle_mod.append_jsonl(self.memory_dir / "nodes.jsonl", node_active2)
        lifecycle_mod.append_jsonl(self.memory_dir / "nodes.jsonl", node_stale)
        
        # Edges
        edge_valid = {"source": "node.active", "target": "node.active2", "type": "depends_on"}
        edge_dangling = {"source": "node.active", "target": "node.stale", "type": "overrides"}
        lifecycle_mod.append_jsonl(self.memory_dir / "edges.jsonl", edge_valid)
        lifecycle_mod.append_jsonl(self.memory_dir / "edges.jsonl", edge_dangling)
        
        # Run prune
        res = lifecycle_mod.cmd_prune(None)
        self.assertEqual(res, 0)
        
        # Verify pruned state
        nodes = lifecycle_mod.load_jsonl(self.memory_dir / "nodes.jsonl")
        self.assertEqual(len(nodes), 2)
        self.assertEqual(nodes[0]["id"], "node.active")
        self.assertEqual(nodes[1]["id"], "node.active2")
        
        edges = lifecycle_mod.load_jsonl(self.memory_dir / "edges.jsonl")
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]["target"], "node.active2")

if __name__ == "__main__":
    unittest.main()
