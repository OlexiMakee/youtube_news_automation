import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from scripts import memos


class TestMemosCli(unittest.TestCase):
    def test_init_creates_missing_control_files_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = root / "agent_context" / "WORKFLOWS.md"
            existing.parent.mkdir(parents=True)
            existing.write_text("custom workflows\n", encoding="utf-8")

            result = _quiet_call(memos.cmd_init, _args(root))

            self.assertEqual(result, 0)
            self.assertEqual(existing.read_text(encoding="utf-8"), "custom workflows\n")
            self.assertTrue((root / "agent_context" / "HANDSHAKE.md").exists())
            self.assertTrue((root / "agent_context" / "task_capsules.jsonl").exists())
            self.assertTrue((root / "memory" / "nodes.jsonl").exists())
            self.assertTrue((root / "workflows" / "chat.nano.toml").exists())
            self.assertTrue((root / "workflows" / "code.small.toml").exists())
            self.assertTrue((root / "workflows" / "architecture.giant.toml").exists())
            config = json.loads((root / "memos.config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["version"], "0.1")

    def test_integrate_appends_agents_block_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agents = root / "AGENTS.md"
            agents.write_text("# Agent Instructions\n", encoding="utf-8")

            self.assertEqual(_quiet_call(memos.cmd_integrate, _args(root)), 0)
            first = agents.read_text(encoding="utf-8")
            self.assertIn("## Memos Integration", first)

            self.assertEqual(_quiet_call(memos.cmd_integrate, _args(root)), 0)
            second = agents.read_text(encoding="utf-8")
            self.assertEqual(first, second)

    def test_validate_accepts_minimal_initialized_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _quiet_call(memos.cmd_init, _args(root))

            result = _quiet_call(memos.cmd_validate, _args(root))

        self.assertEqual(result, 0)

    def test_quantize_returns_12_step_result(self):
        args = _args(Path("."))
        args.task = "architecture refactor with schema migration"
        args.risk = 0.8
        args.volume = 0.0
        args.uncertainty = 0.0
        args.format = "json"
        stdout = StringIO()

        with redirect_stdout(stdout):
            result = memos.cmd_quantize(args)

        payload = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(payload["step_score"], 12)
        self.assertEqual(payload["step_name"], "giant")
        self.assertEqual(payload["workflow_id"], "architecture.giant")

    def test_workflows_command_writes_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflows = root / "workflows"
            workflows.mkdir()
            _write_workflow(workflows / "chat.nano.toml", "chat.nano", 1, 2, 1, 18, "cheap_free")
            _write_workflow(workflows / "code.small.toml", "code.small", 3, 8, 26, 64, "codex")
            _write_workflow(workflows / "architecture.giant.toml", "architecture.giant", 9, 12, 65, 100, "large_reasoning")
            args = _args(root)
            args.format = "json"
            args.write_manifest = True
            args.manifest_path = "memory/workflow_manifest.json"

            result = _quiet_call(memos.cmd_workflows, args)

            self.assertEqual(result, 0)
            manifest = root / "memory" / "workflow_manifest.json"
            self.assertTrue(manifest.exists())
            self.assertTrue(json.loads(manifest.read_text(encoding="utf-8"))["ok"])


def _args(root):
    class Args:
        pass

    args = Args()
    args.root = str(root)
    return args


def _quiet_call(func, args):
    with redirect_stdout(StringIO()):
        return func(args)


def _write_workflow(path, workflow_id, step_min, step_max, level_min, level_max, model_policy):
    path.write_text(
        "\n".join([
            f'id = "{workflow_id}"',
            f"step_min = {step_min}",
            f"step_max = {step_max}",
            f"level_min = {level_min}",
            f"level_max = {level_max}",
            f'model_policy = "{model_policy}"',
            'tools = ["search_memory"]',
            'verification = ["schema_check"]',
            "",
        ]),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
