import json
import os
import sys
import unittest
from io import StringIO
from unittest.mock import patch


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from scripts.memory import quantize_task


class TestQuantizeTaskCli(unittest.TestCase):
    def test_cli_json_exposes_legacy_and_step_scores(self):
        stdout = StringIO()
        argv = [
            "quantize_task.py",
            "--task",
            "architecture refactor with schema migration",
            "--risk",
            "0.8",
            "--json",
        ]
        with patch.object(sys, "argv", argv), patch("sys.stdout", stdout):
            self.assertEqual(quantize_task.main(), 0)

        payload = json.loads(stdout.getvalue())
        self.assertIn("legacy_score", payload)
        self.assertIn("step_score", payload)
        self.assertIn("step_name", payload)
        self.assertGreaterEqual(payload["step_score"], 11)
        self.assertEqual(payload["workflow_id"], "architecture.giant")


if __name__ == "__main__":
    unittest.main()
