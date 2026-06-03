import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from scripts.memory.audit_memos import audit, to_markdown


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def capsule(task, **extra):
    row = {
        "timestamp": "2026-06-02T00:00:00Z",
        "task": task,
        "files_modified": ["agent_context/HANDSHAKE.md"],
        "hurdles_regression": "none",
        "resolution": "done",
        "lessons_learned": "small steps",
    }
    row.update(extra)
    return json.dumps(row)


class TestMemosAudit(unittest.TestCase):
    def test_audit_summarizes_handoff_capsules_and_roadmap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root / "agent_context" / "HANDSHAKE.md",
                """
## Current Session Status
- Active Agent: Codex
- Budget Tier applied: `memos giant`
## Next Handover
- Target Command: `memos giant`
## Blocked / Pending
- [ ] Keep live DB migrations blocked
""",
            )
            write(root / "agent_context" / "WORKFLOWS.md", "# Workflows\n")
            write(
                root / "agent_context" / "GLOBAL_ROADMAP.md",
                """
### Memory OS Operations
- [x] **Task Experience Log**: done
- [ ] **Periodic Method Log Review**: pending
""",
            )
            write(
                root / "agent_context" / "task_capsules.jsonl",
                capsule("legacy") + "\n" + capsule("audit", workflow="memos", step_score=12, step_name="giant") + "\n",
            )
            write(root / "memory" / "events.jsonl", json.dumps({"event": "created"}) + "\n")

            report = audit(root)

        self.assertEqual(report["handshake"]["active_agent"], "Codex")
        self.assertEqual(report["handshake"]["target_command"], "`memos giant`")
        self.assertEqual(report["capsules"]["total"], 2)
        self.assertEqual(report["capsules"]["missing_metadata_count"], 1)
        self.assertEqual(report["capsules"]["latest_workflow"], "memos")
        self.assertIn("Periodic Method Log Review", report["roadmap"]["open"])
        self.assertEqual(report["capsule_validation_errors"], [])

    def test_markdown_report_contains_core_sections(self):
        report = {
            "generated_at": "2026-06-02T00:00:00Z",
            "handshake": {"active_agent": "Codex", "budget_tier": "memos giant", "target_command": "memos giant"},
            "capsules": {"total": 1, "missing_metadata_count": 0, "latest_task": "audit", "latest_workflow": "memos", "latest_step": "giant"},
            "capsule_validation_errors": [],
            "roadmap": {"open": []},
            "recommendations": ["Memory OS control plane is ready."],
        }

        markdown = to_markdown(report)

        self.assertIn("# Memory OS Audit", markdown)
        self.assertIn("Recommendations", markdown)
        self.assertIn("Memory OS control plane is ready.", markdown)


if __name__ == "__main__":
    unittest.main()
