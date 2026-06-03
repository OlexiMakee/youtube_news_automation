import os
import sys
import unittest
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add root dir to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.services.memory_os.interfaces import IMemosConfig, IMemoryStorage, ILlmProviderService
from app.services.memory_os.compactor import MemoryCompactor
from app.services.memory_os.lifecycle import LifecycleManager
from app.services.memory_os.validator import MemoryValidator
from app.services.memory_os.search import MemorySearcher


class MockMemosConfig(IMemosConfig):
    """Fully mocked Memory OS config."""

    @property
    def profile(self) -> str:
        return "mock-profile"

    @property
    def memory_dir(self) -> Path:
        return Path("/mock/root/memory")

    @property
    def capsules_file(self) -> Path:
        return Path("/mock/root/agent_context/task_capsules.jsonl")

    @property
    def snapshot_file(self) -> Path:
        return Path("/mock/root/agent_context/memory_snapshot.json")

    @property
    def proposals_file(self) -> Path:
        return Path("/mock/root/agent_proposals/admin_proposals.jsonl")

    @property
    def workflows(self) -> List[str]:
        return ["product", "memos"]

    @property
    def step_scale(self) -> str:
        return "1..12"

    @property
    def root_dir(self) -> Path:
        return Path("/mock/root")


class MockMemoryStorage(IMemoryStorage):
    """In-memory mock storage preventing actual disk writes."""

    def __init__(self):
        self.files: Dict[str, List[Dict[str, Any]]] = {}
        self.raw_files: Dict[str, List[str]] = {}

    def load_jsonl(self, filepath: Path) -> List[Dict[str, Any]]:
        return self.files.get(str(filepath), [])

    def save_jsonl(self, filepath: Path, items: List[Dict[str, Any]]) -> None:
        self.files[str(filepath)] = items
        lines = []
        import json
        for item in items:
            lines.append(json.dumps(item) + "\n")
        self.raw_files[str(filepath)] = lines

    def append_jsonl(self, filepath: Path, item: Dict[str, Any]) -> None:
        if str(filepath) not in self.files:
            self.files[str(filepath)] = []
        self.files[str(filepath)].append(item)
        
        if str(filepath) not in self.raw_files:
            self.raw_files[str(filepath)] = []
        import json
        self.raw_files[str(filepath)].append(json.dumps(item) + "\n")

    def load_json(self, filepath: Path) -> Dict[str, Any]:
        items = self.files.get(str(filepath), [])
        if items and isinstance(items, list):
            return items[0]
        return items if isinstance(items, dict) else {}

    def save_json(self, filepath: Path, item: Dict[str, Any]) -> None:
        self.files[str(filepath)] = item

    def read_lines(self, filepath: Path) -> List[str]:
        return self.raw_files.get(str(filepath), [])

    def exists(self, filepath: Path) -> bool:
        return str(filepath) in self.files or str(filepath) in self.raw_files

    def get_sha256(self, filepath: Path) -> str:
        return "mock-sha256-hash-value"


class MockLlmProviderService(ILlmProviderService):
    """Mocked LLM provider to return predictable JSON strings for compactor."""

    def __init__(self, response_text: str):
        self.response_text = response_text
        self.called_user_msg: Optional[str] = None
        self.called_system_prompt: Optional[str] = None

    def call_llm(
        self,
        user_message: str,
        system_prompt: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        self.called_user_msg = user_message
        self.called_system_prompt = system_prompt
        return self.response_text


class TestMemoryOsDip(unittest.TestCase):

    def setUp(self):
        self.config = MockMemosConfig()
        self.storage = MockMemoryStorage()

    def test_lifecycle_manager_mocked(self):
        # 1. Setup mock files
        nodes_path = self.config.memory_dir / "nodes.jsonl"
        events_path = self.config.memory_dir / "events.jsonl"
        
        self.storage.files[str(nodes_path)] = []
        self.storage.files[str(events_path)] = []

        lifecycle = LifecycleManager(config=self.config, storage=self.storage)
        
        # Propose a node
        res = lifecycle.propose(
            node_id="provider.ollama.cloud_only",
            node_type="rule",
            summary="Ollama must be cloud only",
            evidence="AGENTS.md",
            validator="test_validator"
        )
        self.assertEqual(res, 0)
        
        # Verify mock storage has been updated
        nodes = self.storage.load_jsonl(nodes_path)
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["id"], "provider.ollama.cloud_only")
        self.assertEqual(nodes[0]["status"], "draft")

        # Fake the file existence check for validation
        evidence_file = self.config.root_dir / "AGENTS.md"
        self.storage.files[str(evidence_file)] = {"exists": True}

        # Transition node
        res_t = lifecycle.transition(validator="test_validator")
        self.assertEqual(res_t, 0)
        
        # Verify transitioned status
        self.assertEqual(nodes[0]["status"], "verified")

    def test_validator_mocked(self):
        nodes_path = self.config.memory_dir / "nodes.jsonl"
        # Seed an invalid node
        invalid_node_json = '{"id": "invalid.node", "type": "wrong_type", "summary": "oops", "evidence": [], "status": "draft", "freshness": "2026-06-03", "trust": "unverified"}\n'
        self.storage.raw_files[str(nodes_path)] = [invalid_node_json]
        self.storage.files[str(nodes_path)] = [{"id": "invalid.node"}]

        validator = MemoryValidator(config=self.config, storage=self.storage)
        errors = validator.validate_nodes()
        self.assertTrue(len(errors) > 0)
        self.assertIn("invalid type", errors[0])

    def test_searcher_mocked(self):
        nodes_path = self.config.memory_dir / "nodes.jsonl"
        edges_path = self.config.memory_dir / "edges.jsonl"
        snapshot_path = self.config.snapshot_file

        self.storage.files[str(nodes_path)] = [
            {
                "id": "provider.ollama.cloud_only",
                "type": "rule",
                "summary": "Ollama cloud only",
                "evidence": ["AGENTS.md"],
                "status": "verified",
                "freshness": "2026-06-03",
                "trust": "verified",
                "related_nodes": []
            }
        ]
        self.storage.files[str(edges_path)] = []
        self.storage.files[str(snapshot_path)] = {"items": [], "generated_at": "2026-06-03"}

        searcher = MemorySearcher(config=self.config, storage=self.storage)
        results = searcher.search_memory("Ollama")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "provider.ollama.cloud_only")

    def test_compactor_mocked(self):
        capsules_path = self.config.capsules_file
        events_path = self.config.memory_dir / "events.jsonl"
        nodes_path = self.config.memory_dir / "nodes.jsonl"
        edges_path = self.config.memory_dir / "edges.jsonl"

        # Seed uncompacted capsule
        self.storage.files[str(capsules_path)] = [
            {
                "timestamp": "2026-06-03T12:00:00Z",
                "task": "Test task",
                "workflow": "product",
                "step_score": 1,
                "step_name": "nano",
                "files_modified": ["app/state.py"],
                "hurdles_regression": "None",
                "resolution": "Done",
                "lessons_learned": "Nothing much"
            }
        ]
        self.storage.files[str(events_path)] = []
        self.storage.files[str(nodes_path)] = []
        self.storage.files[str(edges_path)] = []

        llm_response = """
        {
          "nodes": [
            {
              "id": "provider.gemini.api_usage",
              "type": "rule",
              "summary": "Gemini API usage is allowed",
              "evidence": ["app/state.py"]
            }
          ],
          "edges": []
        }
        """
        llm_service = MockLlmProviderService(response_text=llm_response)
        
        # We need mock file existence for the evidence clean up inside compactor
        evidence_file = self.config.root_dir / "app/state.py"
        self.storage.files[str(evidence_file)] = {"exists": True}

        compactor = MemoryCompactor(config=self.config, storage=self.storage, llm_service=llm_service)
        
        # Run compaction (disable subprocess snapshot rebuild inside test by catching or because scripts/compact_memory.py won't run)
        res = compactor.compact_capsules()
        self.assertEqual(res, 0)
        
        # Verify node was appended to storage
        nodes = self.storage.load_jsonl(nodes_path)
        self.assertTrue(len(nodes) > 0)
        self.assertEqual(nodes[0]["id"], "provider.gemini.api_usage")


if __name__ == "__main__":
    unittest.main()
