import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

class MemosConfig:
    """Manages the configuration and paths for Memory OS."""

    def __init__(self, config_path: Optional[str] = None):
        # 1. Resolve config file path: parameter -> env var -> default project root
        if config_path:
            self.config_path = Path(config_path).resolve()
        else:
            env_path = os.environ.get("MEMOS_CONFIG_PATH")
            if env_path:
                self.config_path = Path(env_path).resolve()
            else:
                # Default to project root memos.config.json
                self.config_path = Path(__file__).resolve().parents[3] / "memos.config.json"

        self.root_dir = self.config_path.parent
        self.data = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            # Fall back to default developer profile values if no config found
            return {
                "version": "0.1",
                "profile": "developer",
                "memory_dir": "memory",
                "capsules_file": "agent_context/task_capsules.jsonl",
                "snapshot_file": "agent_context/memory_snapshot.json",
                "workflows": ["product", "memos"],
                "step_scale": "1..12"
            }
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    @property
    def profile(self) -> str:
        return self.data.get("profile", "developer")

    @property
    def memory_dir(self) -> Path:
        val = self.data.get("memory_dir", "memory")
        return (self.root_dir / val).resolve()

    @property
    def capsules_file(self) -> Path:
        val = self.data.get("capsules_file", "agent_context/task_capsules.jsonl")
        return (self.root_dir / val).resolve()

    @property
    def snapshot_file(self) -> Path:
        val = self.data.get("snapshot_file", "agent_context/memory_snapshot.json")
        return (self.root_dir / val).resolve()

    @property
    def proposals_file(self) -> Path:
        val = self.data.get("proposals_file", "agent_proposals/admin_proposals.jsonl")
        return (self.root_dir / val).resolve()

    @property
    def workflows(self) -> List[str]:
        return self.data.get("workflows", ["product", "memos"])

    @property
    def step_scale(self) -> str:
        return self.data.get("step_scale", "1..12")
